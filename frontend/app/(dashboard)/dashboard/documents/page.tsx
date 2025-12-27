"use client";

import { useState, useEffect, useRef } from "react";
import { Document, DocumentStatus } from "@/lib/types";
import { documentsApi } from "@/lib/api/documents";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { DocumentUpload } from "@/components/documents/document-upload";
import { DocumentTable } from "@/components/documents/document-table";
import { DocumentSearch } from "@/components/documents/document-search";
import { RefreshCw, Upload, Search as SearchIcon } from "lucide-react";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs";

export default function DocumentsPage() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [selectedDocument, setSelectedDocument] = useState<Document | null>(null);
  const [activeTab, setActiveTab] = useState("upload");
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  const fetchDocuments = async () => {
    setIsLoading(true);
    try {
      const data = await documentsApi.list({ limit: 100 });
      setDocuments(data.items);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "Failed to fetch documents";
      toast.error(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchDocuments();

    // Auto-refresh interval
    intervalRef.current = setInterval(() => {
      fetchDocuments();
    }, 5000);

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, []);

  const handleDelete = (document: Document) => {
    setSelectedDocument(document);
    setDeleteDialogOpen(true);
  };

  const confirmDelete = async () => {
    if (!selectedDocument) return;

    try {
      await documentsApi.delete(selectedDocument.id);
      toast.success("Document deleted successfully!");
      fetchDocuments();
      setDeleteDialogOpen(false);
      setSelectedDocument(null);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "Failed to delete document";
      toast.error(errorMessage);
    }
  };

  const handleUploadSuccess = () => {
    fetchDocuments();
    // Switch to documents tab to see the uploaded file
    setTimeout(() => setActiveTab("documents"), 500);
  };

  const processingCount = documents.filter(
    (doc) =>
      doc.status === DocumentStatus.UPLOADING ||
      doc.status === DocumentStatus.PROCESSING
  ).length;

  const completedCount = documents.filter(
    (doc) => doc.status === DocumentStatus.COMPLETED
  ).length;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">Documents</h2>
          <p className="text-muted-foreground">
            Upload, manage, and search your documents
          </p>
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="icon"
            onClick={fetchDocuments}
            disabled={isLoading}
            title="Refresh"
          >
            <RefreshCw className={`h-4 w-4 ${isLoading ? "animate-spin" : ""}`} />
          </Button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Documents</CardTitle>
            <Upload className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{documents.length}</div>
            <p className="text-xs text-muted-foreground">
              {documents.length === 1 ? "document" : "documents"} uploaded
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Processing</CardTitle>
            <RefreshCw className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{processingCount}</div>
            <p className="text-xs text-muted-foreground">
              {processingCount === 1 ? "document" : "documents"} being processed
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Ready for Search</CardTitle>
            <SearchIcon className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{completedCount}</div>
            <p className="text-xs text-muted-foreground">
              {completedCount === 1 ? "document" : "documents"} searchable
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Main Content Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="upload">
            <Upload className="mr-2 h-4 w-4" />
            Upload
          </TabsTrigger>
          <TabsTrigger value="documents">
            Documents ({documents.length})
          </TabsTrigger>
          <TabsTrigger value="search">
            <SearchIcon className="mr-2 h-4 w-4" />
            Search
          </TabsTrigger>
        </TabsList>

        <TabsContent value="upload" className="space-y-4">
          <DocumentUpload onUploadSuccess={handleUploadSuccess} />

          {processingCount > 0 && (
            <Card className="border-yellow-200 bg-yellow-50">
              <CardContent className="p-4">
                <p className="text-sm text-yellow-800">
                  <RefreshCw className="inline h-4 w-4 mr-1 animate-spin" />
                  {processingCount} {processingCount === 1 ? "document is" : "documents are"} being
                  processed. This may take a few moments.
                </p>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="documents" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Your Documents</CardTitle>
              <CardDescription>
                Manage your uploaded documents and view processing status
              </CardDescription>
            </CardHeader>
            <CardContent>
              <DocumentTable documents={documents} onDelete={handleDelete} />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="search" className="space-y-4">
          {completedCount === 0 ? (
            <Card>
              <CardContent className="p-8 text-center">
                <SearchIcon className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                <h3 className="text-lg font-medium mb-2">No documents ready for search</h3>
                <p className="text-sm text-muted-foreground mb-4">
                  Upload and process documents before you can search them
                </p>
                <Button onClick={() => setActiveTab("upload")}>
                  <Upload className="mr-2 h-4 w-4" />
                  Upload Document
                </Button>
              </CardContent>
            </Card>
          ) : (
            <DocumentSearch />
          )}
        </TabsContent>
      </Tabs>

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Document</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete <strong>{selectedDocument?.filename}</strong>?
              This action cannot be undone. All chunks and vectors will be permanently removed.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={confirmDelete} className="bg-destructive text-destructive-foreground hover:bg-destructive/90">
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
