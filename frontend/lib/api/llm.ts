import apiClient from '../api-client';
import type {
  DocumentSummarizeRequest,
  DocumentSummarizeResponse,
  DocumentOperationStartResponse,
  DocumentAskRequest,
  DocumentAskResponse,
  DocumentTransformRequest,
  DocumentTransformResponse,
  LLMOperation
} from '../types';

// Sleep utility for polling
const sleep = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

// Poll operation until completion
const pollOperation = async (
  operationId: string,
  pollInterval = 2000,
  maxAttempts = 300 // 10 minutes max (300 * 2 seconds) - increased for long operations like transform
): Promise<LLMOperation> => {
  let attempts = 0;

  while (attempts < maxAttempts) {
    const operation = await llmApi.getOperation(operationId);

    if (operation.status === 'completed') {
      return operation;
    }

    if (operation.status === 'failed') {
      throw new Error(operation.error_message || 'Operation failed');
    }

    // Still processing, wait and try again
    await sleep(pollInterval);
    attempts++;
  }

  throw new Error('Operation timed out - exceeded maximum polling attempts');
};

export const llmApi = {
  // Summarize document (with polling)
  summarizeDocument: async (data: DocumentSummarizeRequest): Promise<DocumentSummarizeResponse> => {
    // Start the operation
    const startResponse = await apiClient.post<DocumentOperationStartResponse>(
      '/llm/documents/summarize',
      data
    );

    // Poll until completion
    const operation = await pollOperation(startResponse.data.operation_id);

    // Return the result in the expected format
    return {
      operation_id: operation.id,
      summary: operation.output_data?.summary || '',
      model_used: operation.model_used || '',
      tokens_used: operation.tokens_used || 0,
      cost_estimate: operation.cost_estimate || 0
    };
  },

  // Ask question (with polling)
  askQuestion: async (data: DocumentAskRequest): Promise<DocumentAskResponse> => {
    // Start the operation
    const startResponse = await apiClient.post<DocumentOperationStartResponse>(
      '/llm/documents/ask',
      data
    );

    // Poll until completion
    const operation = await pollOperation(startResponse.data.operation_id);

    // Return the result in the expected format
    return {
      operation_id: operation.id,
      answer: operation.output_data?.answer || '',
      sources: operation.output_data?.sources || [],
      model_used: operation.model_used || '',
      tokens_used: operation.tokens_used || 0,
      cost_estimate: operation.cost_estimate || 0
    };
  },

  // Transform document (with polling)
  transformDocument: async (data: DocumentTransformRequest): Promise<DocumentTransformResponse> => {
    // Start the operation
    const startResponse = await apiClient.post<DocumentOperationStartResponse>(
      '/llm/documents/transform',
      data
    );

    // Poll until completion
    const operation = await pollOperation(startResponse.data.operation_id);

    // Return the result in the expected format
    return {
      operation_id: operation.id,
      transformed_content: operation.output_data?.transformed_content || '',
      model_used: operation.model_used || '',
      tokens_used: operation.tokens_used || 0,
      cost_estimate: operation.cost_estimate || 0
    };
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
  },

  // Get latest summary for a document
  getLatestSummary: async (documentId: string): Promise<LLMOperation | null> => {
    try {
      const response = await apiClient.get(`/llm/documents/${documentId}/summarize/latest`);
      return response.data;
    } catch (error: any) {
      if (error.response?.status === 404) {
        return null; // No summary exists
      }
      throw error;
    }
  }
};
