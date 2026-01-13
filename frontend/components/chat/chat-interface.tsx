"use client";

import { useState, useEffect, useRef } from "react";
import { useTranslations } from "next-intl";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Send, Loader2, User, Bot } from "lucide-react";
import { toast } from "sonner";
import ReactMarkdown from "react-markdown";
import { workflowsApi } from "@/lib/api/workflows";
import type { Message } from "@/lib/types";

interface ChatInterfaceProps {
  sessionId: string;
}

export function ChatInterface({ sessionId }: ChatInterfaceProps) {
  const t = useTranslations("chat");
  const tCommon = useTranslations("common");

  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [streaming, setStreaming] = useState(false);
  const [currentStreamContent, setCurrentStreamContent] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);
  const eventSourceRef = useRef<EventSource | null>(null);

  // Load messages on mount
  useEffect(() => {
    loadMessages();
    return () => {
      // Cleanup EventSource on unmount
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, [sessionId]);

  // Auto-scroll to bottom
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, currentStreamContent]);

  const loadMessages = async () => {
    try {
      const data = await workflowsApi.getMessages(sessionId);
      setMessages(data);
    } catch (error) {
      console.error("Failed to load messages:", error);
      toast.error(t("messagesFailed"));
    }
  };

  const handleSend = async () => {
    if (!input.trim() || loading) return;

    const userMessage = input.trim();
    setInput("");
    setLoading(true);
    setStreaming(true);
    setCurrentStreamContent("");

    // Optimistically add user message to UI
    const tempUserMsg: Message = {
      id: `temp-${Date.now()}`,
      session_id: sessionId,
      role: "user",
      content: userMessage,
      metadata: {},
      created_at: new Date().toISOString()
    };
    setMessages(prev => [...prev, tempUserMsg]);

    try {
      // Close any existing EventSource
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }

      // Start streaming (using unified workflow - v0.4.1)
      const eventSource = workflowsApi.streamWorkflow(
        {
          // workflow_config removed - backend uses unified workflow now
          user_input: userMessage,
          session_id: sessionId
        },
        {
          onStart: () => {
            setStreaming(true);
          },
          onUpdate: (data) => {
            console.log("SSE Update event:", data);

            // Extract assistant message from state updates
            if (data.event && typeof data.event === 'object') {
              const eventValues = Object.values(data.event);
              console.log("Event values:", eventValues);

              for (const value of eventValues) {
                if (value && typeof value === 'object' && 'messages' in value) {
                  const stateMessages = (value as { messages: unknown[] }).messages;
                  const lastMsg = stateMessages[stateMessages.length - 1];
                  console.log("Last message:", lastMsg);

                  // Only show AI messages in stream (not user messages)
                  if (lastMsg && typeof lastMsg === 'object' && 'content' in lastMsg && 'type' in lastMsg) {
                    const msgType = (lastMsg as { type: unknown }).type;
                    const content = (lastMsg as { content: unknown }).content;

                    if (msgType === 'AIMessage' && typeof content === 'string') {
                      console.log("Setting AI stream content:", content);
                      console.log("Current streaming state:", streaming);
                      console.log("Current loading state:", loading);
                      setCurrentStreamContent(content);
                    }
                  }
                }
              }
            }
          },
          onDone: (data) => {
            console.log("Stream done, final data:", data);
            setStreaming(false);
            setCurrentStreamContent("");
            setLoading(false);
            // Reload messages after a short delay to ensure DB write completes
            setTimeout(() => {
              loadMessages();
            }, 1000); // Increased delay to 1 second
          },
          onError: (error) => {
            console.error("Streaming error:", error);
            setStreaming(false);
            setCurrentStreamContent("");
            setLoading(false);
            toast.error(t("failed"));
          }
        }
      );

      eventSourceRef.current = eventSource;

    } catch (error) {
      console.error("Failed to send message:", error);
      setLoading(false);
      setStreaming(false);
      toast.error(t("failed"));
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <Card className="flex flex-col h-[calc(100vh-12rem)]">
      {/* Messages */}
      <ScrollArea className="flex-1 p-4">
        <div className="space-y-4">
          {messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex gap-3 ${
                msg.role === "user" ? "justify-end" : "justify-start"
              }`}
            >
              {msg.role === "assistant" && (
                <Avatar className="h-8 w-8 shrink-0">
                  <AvatarFallback className="bg-primary/10">
                    <Bot className="h-4 w-4" />
                  </AvatarFallback>
                </Avatar>
              )}
              <div
                className={`max-w-[70%] rounded-lg px-4 py-2 ${
                  msg.role === "user"
                    ? "bg-primary text-primary-foreground"
                    : "bg-muted"
                }`}
              >
                <div className="prose prose-sm dark:prose-invert max-w-none">
                  <ReactMarkdown>
                    {msg.content}
                  </ReactMarkdown>
                </div>
              </div>
              {msg.role === "user" && (
                <Avatar className="h-8 w-8 shrink-0">
                  <AvatarFallback className="bg-primary">
                    <User className="h-4 w-4 text-primary-foreground" />
                  </AvatarFallback>
                </Avatar>
              )}
            </div>
          ))}

          {/* Streaming content */}
          {streaming && currentStreamContent && (
            <div className="flex gap-3 justify-start">
              <Avatar className="h-8 w-8 shrink-0">
                <AvatarFallback className="bg-primary/10">
                  <Bot className="h-4 w-4" />
                </AvatarFallback>
              </Avatar>
              <div className="max-w-[70%] rounded-lg px-4 py-2 bg-muted">
                <div className="prose prose-sm dark:prose-invert max-w-none">
                  <ReactMarkdown>
                    {currentStreamContent}
                  </ReactMarkdown>
                </div>
                <div className="flex items-center gap-2 mt-2 text-xs text-muted-foreground">
                  <Loader2 className="h-3 w-3 animate-spin" />
                  <span>{t("streaming")}</span>
                </div>
              </div>
            </div>
          )}

          {loading && !currentStreamContent && (
            <div className="flex gap-3 justify-start">
              <Avatar className="h-8 w-8 shrink-0">
                <AvatarFallback className="bg-primary/10">
                  <Bot className="h-4 w-4" />
                </AvatarFallback>
              </Avatar>
              <div className="rounded-lg px-4 py-2 bg-muted">
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span>{t("thinking")}</span>
                </div>
              </div>
            </div>
          )}

          <div ref={scrollRef} />
        </div>
      </ScrollArea>

      {/* Input */}
      <div className="border-t p-4">
        <div className="flex gap-2">
          <Input
            placeholder={t("typeMessage")}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            disabled={loading}
            className="flex-1"
          />
          <Button onClick={handleSend} disabled={loading || !input.trim()}>
            {loading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4" />
            )}
          </Button>
        </div>
      </div>
    </Card>
  );
}
