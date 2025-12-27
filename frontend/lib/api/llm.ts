import apiClient from '../api-client';
import type {
  DocumentSummarizeRequest,
  DocumentSummarizeResponse,
  DocumentAskRequest,
  DocumentAskResponse,
  DocumentTransformRequest,
  DocumentTransformResponse,
  LLMOperation
} from '../types';

export const llmApi = {
  // Summarize document
  summarizeDocument: async (data: DocumentSummarizeRequest): Promise<DocumentSummarizeResponse> => {
    const response = await apiClient.post('/llm/documents/summarize', data);
    return response.data;
  },

  // Ask question
  askQuestion: async (data: DocumentAskRequest): Promise<DocumentAskResponse> => {
    const response = await apiClient.post('/llm/documents/ask', data);
    return response.data;
  },

  // Transform document
  transformDocument: async (data: DocumentTransformRequest): Promise<DocumentTransformResponse> => {
    const response = await apiClient.post('/llm/documents/transform', data);
    return response.data;
  },

  // List operations
  listOperations: async (skip = 0, limit = 100): Promise<LLMOperation[]> => {
    const response = await apiClient.get('/llm/operations', {
      params: { skip, limit }
    });
    return response.data;
  },

  // Get operation
  getOperation: async (operationId: string): Promise<LLMOperation> => {
    const response = await apiClient.get(`/llm/operations/${operationId}`);
    return response.data;
  }
};
