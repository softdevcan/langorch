"use client";

import { useState, useEffect } from "react";
import { useTranslations } from "next-intl";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { ChatInterface } from "@/components/chat/chat-interface";
import { workflowsApi } from "@/lib/api/workflows";
import { toast } from "sonner";
import { Plus, MessageSquare } from "lucide-react";
import type { ConversationSession } from "@/lib/types";

export default function ChatPage() {
  const t = useTranslations("chat");
  const tCommon = useTranslations("common");

  const [sessions, setSessions] = useState<ConversationSession[]>([]);
  const [currentSession, setCurrentSession] = useState<ConversationSession | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadSessions();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const loadSessions = async () => {
    try {
      setLoading(true);
      const data = await workflowsApi.listSessions();
      setSessions(data);

      // Auto-select first session if available
      if (data.length > 0 && !currentSession) {
        setCurrentSession(data[0]);
      }
    } catch (error) {
      console.error("Failed to load sessions:", error);
      toast.error(t("loadFailed"));
    } finally {
      setLoading(false);
    }
  };

  const createNewSession = async () => {
    try {
      const newSession = await workflowsApi.createSession({
        title: t("untitledChat")
      });
      setSessions([newSession, ...sessions]);
      setCurrentSession(newSession);
      toast.success(t("newChat"));
    } catch (error) {
      console.error("Failed to create session:", error);
      toast.error(t("createFailed"));
    }
  };

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold">{t("title")}</h1>
          <p className="text-muted-foreground mt-1">
            {t("conversations")}
          </p>
        </div>
        <Button onClick={createNewSession}>
          <Plus className="mr-2 h-4 w-4" />
          {t("newChat")}
        </Button>
      </div>

      {/* Main Content */}
      <div className="grid grid-cols-12 gap-6">
        {/* Session List */}
        <div className="col-span-3">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">{t("conversations")}</CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <ScrollArea className="h-[calc(100vh-20rem)]">
                {loading ? (
                  <div className="p-4 text-center text-sm text-muted-foreground">
                    {tCommon("loading")}
                  </div>
                ) : sessions.length === 0 ? (
                  <div className="p-4 text-center text-sm text-muted-foreground">
                    {t("selectConversation")}
                  </div>
                ) : (
                  <div className="space-y-1 p-2">
                    {sessions.map((session) => (
                      <Button
                        key={session.id}
                        variant={currentSession?.id === session.id ? "secondary" : "ghost"}
                        className="w-full justify-start text-left"
                        onClick={() => setCurrentSession(session)}
                      >
                        <MessageSquare className="mr-2 h-4 w-4 shrink-0" />
                        <span className="truncate">
                          {session.title || t("untitledChat")}
                        </span>
                      </Button>
                    ))}
                  </div>
                )}
              </ScrollArea>
            </CardContent>
          </Card>
        </div>

        {/* Chat Interface */}
        <div className="col-span-9">
          {currentSession ? (
            <ChatInterface sessionId={currentSession.id} />
          ) : (
            <Card className="h-[calc(100vh-12rem)] flex items-center justify-center">
              <CardContent className="text-center">
                <MessageSquare className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                <p className="text-muted-foreground">
                  {t("selectConversation")}
                </p>
                <Button onClick={createNewSession} className="mt-4">
                  <Plus className="mr-2 h-4 w-4" />
                  {t("newChat")}
                </Button>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
