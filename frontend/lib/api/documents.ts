import apiClient from "../api-client";
import {
  Document,
  DocumentUploadResponse,
  DocumentSearchRequest,
  DocumentSearchResponse,
  DocumentChunk,
  DocumentStatus,
} from "../types";

export const documentsApi = {
  /**
   * Upload a document file
   */
  upload: async (file: File): Promise<DocumentUploadResponse> => {
    const formData = new FormData();
    formData.append("file", file);

    const { data } = await apiClient.post<DocumentUploadResponse>(
      "/documents/upload",
      formData,
      {
        headers: {
          "Content-Type": "multipart/form-data",
        },
      }
    );
    return data;
  },

  /**
   * List documents with pagination and optional status filter
   */
  list: async (params?: {
    skip?: number;
    limit?: number;
    status_filter?: DocumentStatus;
  }): Promise<{
    items: Document[];
    total: number;
    page: number;
    page_size: number;
  }> => {
    const { data } = await apiClient.get<{
      items: Document[];
      total: number;
      page: number;
      page_size: number;
    }>("/documents/", {
      params,
    });
    return data;
  },

  /**
   * Get a document by ID
   */
  get: async (documentId: string): Promise<Document> => {
    const { data } = await apiClient.get<Document>(
      `/documents/${documentId}`
    );
    return data;
  },

  /**
   * Search documents semantically
   */
  search: async (
    searchRequest: DocumentSearchRequest
  ): Promise<DocumentSearchResponse> => {
    const { data } = await apiClient.post<DocumentSearchResponse>(
      "/documents/search",
      searchRequest
    );
    return data;
  },

  /**
   * Delete a document
   */
  delete: async (documentId: string): Promise<void> => {
    await apiClient.delete(`/documents/${documentId}`);
  },

  /**
   * Get document chunks
   */
  getChunks: async (
    documentId: string
  ): Promise<{
    items: DocumentChunk[];
    total: number;
    document_id: string;
  }> => {
    const { data } = await apiClient.get<{
      items: DocumentChunk[];
      total: number;
      document_id: string;
    }>(`/documents/${documentId}/chunks`);
    return data;
  },
};
