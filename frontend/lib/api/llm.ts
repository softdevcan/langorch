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
  maxAttempts = 150 // 5 minutes max (150 * 2 seconds)
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
      '/api/v1/llm/documents/summarize',
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

  // Ask question
  askQuestion: async (data: DocumentAskRequest): Promise<DocumentAskResponse> => {
    const response = await apiClient.post('/api/v1/llm/documents/ask', data);
    return response.data;
  },

  // Transform document
  transformDocument: async (data: DocumentTransformRequest): Promise<DocumentTransformResponse> => {
    const response = await apiClient.post('/api/v1/llm/documents/transform', data);
    return response.data;
  },

  // List operations
  listOperations: async (skip = 0, limit = 100): Promise<LLMOperation[]> => {
    const response = await apiClient.get('/api/v1/llm/operations', {
      params: { skip, limit }
    });
    return response.data;
  },

  // Get operation
  getOperation: async (operationId: string): Promise<LLMOperation> => {
    const response = await apiClient.get(`/api/v1/llm/operations/${operationId}`);
    return response.data;
  }
};
