"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { FileText, MessageSquare, Wand2, Loader2 } from "lucide-react";
import { llmApi } from "@/lib/api/llm";
import { settingsApi } from "@/lib/api/settings";
import { toast } from "sonner";
import type { Document } from "@/lib/types";

interface DocumentActionsProps {
  document: Document;
}

export function DocumentActions({ document }: DocumentActionsProps) {
  const [loading, setLoading] = useState(false);
  const [summary, setSummary] = useState<string>("");
  const [summaryOpen, setSummaryOpen] = useState(false);
  const [summaryChecked, setSummaryChecked] = useState(false);

  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<string>("");
  const [askOpen, setAskOpen] = useState(false);

  const [instruction, setInstruction] = useState("");
  const [transformedContent, setTransformedContent] = useState<string>("");
  const [transformOpen, setTransformOpen] = useState(false);

  // LLM model from settings (default: llama3.2)
  const [llmModel, setLlmModel] = useState<string>("llama3.2");

  // Fetch LLM provider settings on component mount
  useEffect(() => {
    const fetchLLMSettings = async () => {
      try {
        const settings = await settingsApi.getLLMProvider();
        setLlmModel(settings.model);
      } catch (error) {
        console.error("Failed to fetch LLM settings:", error);
        // Keep default model if fetch fails
      }
    };
    fetchLLMSettings();
  }, []);

  // Check for existing summary when dialog opens
  useEffect(() => {
    const checkExistingSummary = async () => {
      if (summaryOpen && !summaryChecked && !summary) {
        try {
          const existingSummary = await llmApi.getLatestSummary(document.id);
          if (existingSummary?.output_data?.summary) {
            setSummary(existingSummary.output_data.summary);
            toast.info("Loaded existing summary");
          }
        } catch (error) {
          console.error("Failed to check existing summary:", error);
        } finally {
          setSummaryChecked(true);
        }
      }
    };
    checkExistingSummary();
  }, [summaryOpen, summaryChecked, summary, document.id]);

  // Summarize
  const handleSummarize = async (force: boolean = false) => {
    setLoading(true);
    try {
      const result = await llmApi.summarizeDocument({
        document_id: document.id,
        model: llmModel,
        max_length: 500,
        force
      });
      setSummary(result.summary);
      toast.success(force ? "New summary generated!" : "Summary generated!");
    } catch (error: any) {
      toast.error(error.response?.data?.detail || "Failed to summarize");
    } finally {
      setLoading(false);
    }
  };

  // Ask Question
  const handleAsk = async () => {
    if (!question.trim()) {
      toast.error("Please enter a question");
      return;
    }

    setLoading(true);
    try {
      const result = await llmApi.askQuestion({
        document_id: document.id,
        question,
        model: llmModel,
        max_chunks: 5
      });
      setAnswer(result.answer);
      toast.success("Answer generated!");
    } catch (error: any) {
      toast.error(error.response?.data?.detail || "Failed to answer");
    } finally {
      setLoading(false);
    }
  };

  // Transform
  const handleTransform = async () => {
    if (!instruction.trim()) {
      toast.error("Please enter an instruction");
      return;
    }

    setLoading(true);
    try {
      const result = await llmApi.transformDocument({
        document_id: document.id,
        instruction,
        model: llmModel,
        output_format: "text"
      });
      setTransformedContent(result.transformed_content);
      toast.success("Document transformed!");
    } catch (error: any) {
      toast.error(error.response?.data?.detail || "Failed to transform");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex gap-2">
      {/* Summarize */}
      <Dialog open={summaryOpen} onOpenChange={setSummaryOpen}>
        <DialogTrigger asChild>
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              setSummaryOpen(true);
            }}
          >
            <FileText className="mr-2 h-4 w-4" />
            Summarize
          </Button>
        </DialogTrigger>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Document Summary</DialogTitle>
            <DialogDescription>{document.filename}</DialogDescription>
          </DialogHeader>
          {loading ? (
            <div className="flex justify-center p-8">
              <Loader2 className="h-8 w-8 animate-spin" />
            </div>
          ) : summary ? (
            <>
              <div className="p-4 rounded-lg border bg-muted/50">
                <p className="text-sm whitespace-pre-wrap">{summary}</p>
              </div>
              <DialogFooter>
                <Button
                  variant="outline"
                  onClick={() => handleSummarize(true)}
                  disabled={loading}
                >
                  Regenerate Summary
                </Button>
              </DialogFooter>
            </>
          ) : (
            <div className="space-y-4">
              <p className="text-sm text-muted-foreground">No summary found for this document.</p>
              <Button onClick={() => handleSummarize(false)} disabled={loading}>
                {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                Generate Summary
              </Button>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Ask Question */}
      <Dialog open={askOpen} onOpenChange={setAskOpen}>
        <DialogTrigger asChild>
          <Button variant="outline" size="sm">
            <MessageSquare className="mr-2 h-4 w-4" />
            Ask Question
          </Button>
        </DialogTrigger>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Ask a Question</DialogTitle>
            <DialogDescription>{document.filename}</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label htmlFor="question">Question</Label>
              <Textarea
                id="question"
                placeholder="What is this document about?"
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                rows={3}
              />
            </div>
            <Button onClick={handleAsk} disabled={loading}>
              {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Ask
            </Button>
            {answer && (
              <div className="p-4 mt-4 rounded-lg border bg-muted/50">
                <Label className="mb-2 block font-semibold">Answer:</Label>
                <p className="text-sm whitespace-pre-wrap">{answer}</p>
              </div>
            )}
          </div>
        </DialogContent>
      </Dialog>

      {/* Transform */}
      <Dialog open={transformOpen} onOpenChange={setTransformOpen}>
        <DialogTrigger asChild>
          <Button variant="outline" size="sm">
            <Wand2 className="mr-2 h-4 w-4" />
            Transform
          </Button>
        </DialogTrigger>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Transform Document</DialogTitle>
            <DialogDescription>{document.filename}</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label htmlFor="instruction">Instruction</Label>
              <Textarea
                id="instruction"
                placeholder="e.g., Translate to Turkish, Make it more formal, Extract key points..."
                value={instruction}
                onChange={(e) => setInstruction(e.target.value)}
                rows={3}
              />
            </div>
            <Button onClick={handleTransform} disabled={loading}>
              {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Transform
            </Button>
            {transformedContent && (
              <div className="p-4 mt-4 rounded-lg border border-border bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100">
                <Label className="mb-2 block font-semibold">Result:</Label>
                <p className="text-sm whitespace-pre-wrap">{transformedContent}</p>
              </div>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
