"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Card } from "@/components/ui/card";
import { FileText, MessageSquare, Wand2, Loader2 } from "lucide-react";
import { llmApi } from "@/lib/api/llm";
import { toast } from "sonner";
import type { Document } from "@/lib/types";

interface DocumentActionsProps {
  document: Document;
}

export function DocumentActions({ document }: DocumentActionsProps) {
  const [loading, setLoading] = useState(false);
  const [summary, setSummary] = useState<string>("");
  const [summaryOpen, setSummaryOpen] = useState(false);

  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<string>("");
  const [askOpen, setAskOpen] = useState(false);

  const [instruction, setInstruction] = useState("");
  const [transformedContent, setTransformedContent] = useState<string>("");
  const [transformOpen, setTransformOpen] = useState(false);

  // Summarize
  const handleSummarize = async () => {
    setLoading(true);
    try {
      const result = await llmApi.summarizeDocument({
        document_id: document.id,
        model: "gpt-4",
        max_length: 500
      });
      setSummary(result.summary);
      toast.success("Summary generated!");
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
        model: "gpt-4",
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
        model: "gpt-4",
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
              if (!summary) handleSummarize();
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
            <Card className="p-4">
              <p className="text-sm whitespace-pre-wrap">{summary}</p>
            </Card>
          ) : (
            <p className="text-sm text-muted-foreground">Click "Summarize" to generate summary</p>
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
              <Card className="p-4 mt-4">
                <Label className="mb-2 block">Answer:</Label>
                <p className="text-sm whitespace-pre-wrap">{answer}</p>
              </Card>
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
              <Card className="p-4 mt-4">
                <Label className="mb-2 block">Result:</Label>
                <p className="text-sm whitespace-pre-wrap">{transformedContent}</p>
              </Card>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
