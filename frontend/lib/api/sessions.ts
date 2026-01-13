/**
 * Session API client for LangOrch v0.4.1
 *
 * Provides methods for managing session documents and context.
 */
import apiClient from '../api-client';
import type {
  SessionDocument,
  SessionDocumentCreate,
  SessionDocumentListResponse,
  SessionDocumentAddResponse,
  SessionContext,
  SessionModeUpdate,
  SessionMode,
} from '../types';

export const sessionsApi = {
  // ========== Document Management ==========

  /**
   * Add document to session
   */
  addDocument: async (
    sessionId: string,
    data: SessionDocumentCreate
  ): Promise<SessionDocument> => {
    const response = await apiClient.post<SessionDocumentAddResponse>(
      `/sessions/${sessionId}/documents`,
      data
    );
    // API returns { session_document: {...}, message: "..." }
    return response.data.session_document;
  },

  /**
   * Remove document from session
   */
  removeDocument: async (
    sessionId: string,
    documentId: string
  ): Promise<void> => {
    await apiClient.delete(`/sessions/${sessionId}/documents/${documentId}`);
  },

  /**
   * List active documents for session
   */
  listDocuments: async (sessionId: string): Promise<SessionDocumentListResponse> => {
    const response = await apiClient.get(`/sessions/${sessionId}/documents`);
    return response.data;
  },

  // ========== Session Mode ==========

  /**
   * Update session mode (auto/chat_only/rag_only)
   */
  updateMode: async (
    sessionId: string,
    data: SessionModeUpdate
  ): Promise<void> => {
    await apiClient.put(`/sessions/${sessionId}/mode`, data);
  },

  // ========== Session Context ==========

  /**
   * Get full session context (mode, documents, metadata)
   */
  getContext: async (sessionId: string): Promise<SessionContext> => {
    const response = await apiClient.get(`/sessions/${sessionId}/context`);
    return response.data;
  },
};
