"use client";

import { useState, useEffect } from "react";
import { useTranslations } from "next-intl";
import Link from "next/link";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Plus, FileText, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { documentsApi } from "@/lib/api/documents";
import { sessionsApi } from "@/lib/api/sessions";
import type { Document, SessionDocument } from "@/lib/types";

interface DocumentPanelProps {
  sessionId: string;
  onDocumentAdded?: () => void;
}

export function DocumentPanel({ sessionId, onDocumentAdded }: DocumentPanelProps) {
  const t = useTranslations("chat.documents");
  const tCommon = useTranslations("common");

  const [documents, setDocuments] = useState<Document[]>([]);
  const [sessionDocuments, setSessionDocuments] = useState<SessionDocument[]>([]);
  const [loading, setLoading] = useState(true);
  const [toggling, setToggling] = useState<Set<string>>(new Set());

  useEffect(() => {
    loadDocuments();
    loadSessionDocuments();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId]);

  const loadDocuments = async () => {
    try {
      const data = await documentsApi.list({ skip: 0, limit: 100 });
      // Filter only completed documents
      const completedDocs = data.items.filter(
        (doc) => doc.status === "completed"
      );
      setDocuments(completedDocs);
    } catch (error) {
      console.error("Failed to load documents:", error);
      toast.error(t("loadFailed"));
    }
  };

  const loadSessionDocuments = async () => {
    try {
      setLoading(true);
      const data = await sessionsApi.listDocuments(sessionId);
      // API returns { items: [...], total: N, session_id: "..." }
      setSessionDocuments(data.items || []);
    } catch (error) {
      console.error("Failed to load session documents:", error);
      setSessionDocuments([]); // Fallback to empty array on error
    } finally {
      setLoading(false);
    }
  };

  const isDocumentActive = (documentId: string): boolean => {
    return sessionDocuments.some(
      (sd) => sd.document_id === documentId && sd.is_active
    );
  };

  const handleToggleDocument = async (documentId: string) => {
    const isActive = isDocumentActive(documentId);

    setToggling((prev) => new Set(prev).add(documentId));

    try {
      if (isActive) {
        // Remove document from session
        await sessionsApi.removeDocument(sessionId, documentId);
      } else {
        // Add document to session
        await sessionsApi.addDocument(sessionId, { document_id: documentId });
      }

      // Reload session documents
      await loadSessionDocuments();
      onDocumentAdded?.();

      toast.success(
        isActive ? t("documentRemoved") : t("documentAdded")
      );
    } catch (error) {
      console.error("Failed to toggle document:", error);
      toast.error(t("toggleFailed"));
    } finally {
      setToggling((prev) => {
        const next = new Set(prev);
        next.delete(documentId);
        return next;
      });
    }
  };

  const activeCount = sessionDocuments.filter((sd) => sd.is_active).length;

  return (
    <Card className="h-full">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-base">{t("title")}</CardTitle>
          <Badge variant="secondary">{t("activeCount", { count: activeCount })}</Badge>
        </div>
      </CardHeader>
      <CardContent className="p-0">
        <ScrollArea className="h-[calc(100vh-20rem)]">
          {loading ? (
            <div className="p-4 text-center text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin mx-auto mb-2" />
              {tCommon("loading")}
            </div>
          ) : documents.length === 0 ? (
            <div className="p-4 text-center text-sm text-muted-foreground space-y-2">
              <FileText className="h-8 w-8 mx-auto mb-2 opacity-50" />
              <p>{t("noDocuments")}</p>
              <Button size="sm" variant="outline" asChild>
                <Link href="/dashboard/documents">
                  <Plus className="mr-2 h-4 w-4" />
                  {t("uploadDocument")}
                </Link>
              </Button>
            </div>
          ) : (
            <div className="space-y-1 p-2">
              {documents.map((doc) => {
                const isActive = isDocumentActive(doc.id);
                const isToggling = toggling.has(doc.id);

                return (
                  <div
                    key={doc.id}
                    className="flex items-center gap-2 p-2 rounded-md hover:bg-accent transition-colors"
                  >
                    <Checkbox
                      id={`doc-${doc.id}`}
                      checked={isActive}
                      onCheckedChange={() => handleToggleDocument(doc.id)}
                      disabled={isToggling}
                    />
                    <label
                      htmlFor={`doc-${doc.id}`}
                      className="flex-1 cursor-pointer text-sm"
                    >
                      <div className="flex items-center gap-2">
                        {isToggling ? (
                          <Loader2 className="h-3 w-3 animate-spin shrink-0" />
                        ) : (
                          <FileText className="h-3 w-3 shrink-0" />
                        )}
                        <span className="truncate">{doc.filename}</span>
                      </div>
                      <div className="text-xs text-muted-foreground mt-0.5">
                        {doc.chunk_count} chunks
                      </div>
                    </label>
                  </div>
                );
              })}
            </div>
          )}
        </ScrollArea>
      </CardContent>
    </Card>
  );
}
