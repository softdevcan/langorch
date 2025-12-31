"use client";

import { Document, DocumentStatus } from "@/lib/types";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Trash2, FileText, Loader2, CheckCircle, AlertCircle, XCircle } from "lucide-react";
import { DocumentActions } from "./document-actions";

interface DocumentTableProps {
  documents: Document[];
  onDelete: (document: Document) => void;
  onView?: (document: Document) => void;
}

const getStatusBadge = (status: DocumentStatus) => {
  switch (status) {
    case DocumentStatus.UPLOADING:
      return (
        <Badge className="gap-1 bg-status-pending text-status-pending-foreground">
          <Loader2 className="h-3 w-3 animate-spin" />
          Uploading
        </Badge>
      );
    case DocumentStatus.PROCESSING:
      return (
        <Badge className="gap-1 bg-status-processing text-status-processing-foreground">
          <Loader2 className="h-3 w-3 animate-spin" />
          Processing
        </Badge>
      );
    case DocumentStatus.COMPLETED:
      return (
        <Badge className="gap-1 bg-status-completed text-status-completed-foreground">
          <CheckCircle className="h-3 w-3" />
          Completed
        </Badge>
      );
    case DocumentStatus.FAILED:
      return (
        <Badge className="gap-1 bg-status-failed text-status-failed-foreground">
          <AlertCircle className="h-3 w-3" />
          Failed
        </Badge>
      );
    case DocumentStatus.DELETED:
      return (
        <Badge variant="outline" className="gap-1">
          <XCircle className="h-3 w-3" />
          Deleted
        </Badge>
      );
    default:
      return <Badge variant="outline">{status}</Badge>;
  }
};

const formatFileSize = (bytes: number) => {
  if (bytes === 0) return "0 Bytes";
  const k = 1024;
  const sizes = ["Bytes", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + " " + sizes[i];
};

const formatDate = (dateString: string) => {
  return new Date(dateString).toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
};

export function DocumentTable({ documents, onDelete, onView }: DocumentTableProps) {
  return (
    <div className="rounded-md border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Filename</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Size</TableHead>
            <TableHead>Chunks</TableHead>
            <TableHead>Uploaded</TableHead>
            <TableHead className="text-right">Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {documents.length === 0 ? (
            <TableRow>
              <TableCell colSpan={6} className="text-center py-8 text-muted-foreground">
                No documents found. Upload your first document to get started.
              </TableCell>
            </TableRow>
          ) : (
            documents.map((document) => (
              <TableRow key={document.id}>
                <TableCell className="font-medium">
                  <div className="flex items-center gap-2">
                    <FileText className="h-4 w-4 text-muted-foreground" />
                    <span className="truncate max-w-[300px]" title={document.filename}>
                      {document.filename}
                    </span>
                  </div>
                </TableCell>
                <TableCell>{getStatusBadge(document.status)}</TableCell>
                <TableCell className="text-muted-foreground">
                  {formatFileSize(document.file_size)}
                </TableCell>
                <TableCell>
                  {document.status === DocumentStatus.COMPLETED ? (
                    <Badge variant="outline">{document.chunk_count} chunks</Badge>
                  ) : (
                    <span className="text-muted-foreground text-sm">-</span>
                  )}
                </TableCell>
                <TableCell className="text-muted-foreground text-sm">
                  {formatDate(document.created_at)}
                </TableCell>
                <TableCell className="text-right">
                  <div className="flex justify-end gap-2">
                    {document.status === DocumentStatus.COMPLETED && (
                      <DocumentActions document={document} />
                    )}
                    {onView && document.status === DocumentStatus.COMPLETED && (
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => onView(document)}
                        title="View chunks"
                      >
                        <FileText className="h-4 w-4" />
                      </Button>
                    )}
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => onDelete(document)}
                      className="text-destructive hover:text-destructive"
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </TableCell>
              </TableRow>
            ))
          )}
        </TableBody>
      </Table>

      {documents.length > 0 && documents.some((d) => d.error_message) && (
        <div className="p-4 border-t bg-muted/50">
          <p className="text-sm text-muted-foreground">
            <AlertCircle className="inline h-4 w-4 mr-1" />
            Some documents failed to process. Check individual error messages.
          </p>
        </div>
      )}
    </div>
  );
}
