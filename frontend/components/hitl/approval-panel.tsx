"use client";

import { useState, useEffect } from "react";
import { useTranslations } from "next-intl";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import { ScrollArea } from "@/components/ui/scroll-area";
import { toast } from "sonner";
import { CheckCircle, XCircle, Clock, X } from "lucide-react";
import { hitlApi } from "@/lib/api/workflows";
import type { HITLApproval } from "@/lib/types";

export function ApprovalPanel() {
  const t = useTranslations("hitl");
  const tCommon = useTranslations("common");

  const [approvals, setApprovals] = useState<HITLApproval[]>([]);
  const [feedback, setFeedback] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState<Record<string, boolean>>({});
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    loadApprovals();

    // Poll for new approvals every 5 seconds
    const interval = setInterval(loadApprovals, 5000);

    return () => clearInterval(interval);
  }, []);

  // Show panel when there are approvals
  useEffect(() => {
    setIsVisible(approvals.length > 0);
  }, [approvals]);

  const loadApprovals = async () => {
    try {
      const data = await hitlApi.listPendingApprovals();
      setApprovals(data);
    } catch (error) {
      // Silent fail for polling - don't spam user with errors
      console.error("Failed to load approvals:", error);
    }
  };

  const handleRespond = async (approvalId: string, approved: boolean) => {
    try {
      setLoading(prev => ({ ...prev, [approvalId]: true }));

      await hitlApi.respondToApproval(approvalId, {
        approved,
        feedback: feedback[approvalId]
      });

      toast.success(approved ? t("approved") : t("rejected"));

      // Remove from list
      setApprovals(prev => prev.filter(a => a.id !== approvalId));
      setFeedback(prev => {
        const newFeedback = { ...prev };
        delete newFeedback[approvalId];
        return newFeedback;
      });
    } catch (error) {
      console.error("Failed to respond:", error);
      toast.error(t("respondFailed"));
    } finally {
      setLoading(prev => ({ ...prev, [approvalId]: false }));
    }
  };

  // Don't render if no approvals
  if (!isVisible || approvals.length === 0) {
    return null;
  }

  return (
    <div className="fixed bottom-4 right-4 w-96 z-50 animate-in slide-in-from-bottom-5">
      <Card className="shadow-2xl border-2">
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2 text-base">
              <Clock className="h-5 w-5 text-orange-500" />
              {t("title")}
              <Badge variant="destructive" className="ml-1">
                {approvals.length}
              </Badge>
            </CardTitle>
            <Button
              variant="ghost"
              size="icon"
              className="h-6 w-6"
              onClick={() => setIsVisible(false)}
            >
              <X className="h-4 w-4" />
            </Button>
          </div>
        </CardHeader>
        <CardContent className="pt-0">
          <ScrollArea className="max-h-[400px]">
            <div className="space-y-3">
              {approvals.map((approval) => (
                <Card key={approval.id} className="border-orange-200 dark:border-orange-900">
                  <CardContent className="pt-4 space-y-3">
                    {/* Prompt */}
                    <div>
                      <p className="text-sm font-medium mb-2">{approval.prompt}</p>

                      {/* Context Data (if available) */}
                      {approval.context_data && Object.keys(approval.context_data).length > 0 && (
                        <div className="mt-2">
                          <details className="text-xs">
                            <summary className="cursor-pointer text-muted-foreground hover:text-foreground">
                              View context
                            </summary>
                            <pre className="mt-2 bg-muted p-2 rounded text-xs overflow-auto max-h-32">
                              {JSON.stringify(approval.context_data, null, 2)}
                            </pre>
                          </details>
                        </div>
                      )}
                    </div>

                    {/* Feedback Input */}
                    <Textarea
                      placeholder={t("feedback")}
                      value={feedback[approval.id] || ""}
                      onChange={(e) => setFeedback({
                        ...feedback,
                        [approval.id]: e.target.value
                      })}
                      rows={2}
                      className="text-sm"
                    />

                    {/* Action Buttons */}
                    <div className="flex gap-2">
                      <Button
                        size="sm"
                        onClick={() => handleRespond(approval.id, true)}
                        disabled={loading[approval.id]}
                        className="flex-1"
                      >
                        <CheckCircle className="mr-2 h-4 w-4" />
                        {t("approve")}
                      </Button>
                      <Button
                        size="sm"
                        variant="destructive"
                        onClick={() => handleRespond(approval.id, false)}
                        disabled={loading[approval.id]}
                        className="flex-1"
                      >
                        <XCircle className="mr-2 h-4 w-4" />
                        {t("reject")}
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </ScrollArea>
        </CardContent>
      </Card>
    </div>
  );
}
