import apiClient from "../api-client";
import type {
  EmbeddingProviderUpdate,
  EmbeddingProviderResponse,
  EmbeddingProviderTest,
  EmbeddingProviderTestResponse,
  LLMProviderUpdate,
  LLMProviderResponse,
} from "../types";

export const settingsApi = {
  /**
   * Get current tenant's embedding provider settings
   */
  getEmbeddingProvider: async (): Promise<EmbeddingProviderResponse> => {
    const response = await apiClient.get<EmbeddingProviderResponse>(
      "/settings/embedding-provider"
    );
    return response.data;
  },

  /**
   * Update tenant's embedding provider settings
   */
  updateEmbeddingProvider: async (
    data: EmbeddingProviderUpdate
  ): Promise<EmbeddingProviderResponse> => {
    const response = await apiClient.put<EmbeddingProviderResponse>(
      "/settings/embedding-provider",
      data
    );
    return response.data;
  },

  /**
   * Test embedding provider connection
   */
  testEmbeddingProvider: async (
    data: EmbeddingProviderTest
  ): Promise<EmbeddingProviderTestResponse> => {
    const response = await apiClient.post<EmbeddingProviderTestResponse>(
      "/settings/embedding-provider/test",
      data
    );
    return response.data;
  },

  /**
   * Get current tenant's LLM provider settings
   */
  getLLMProvider: async (): Promise<LLMProviderResponse> => {
    const response = await apiClient.get<LLMProviderResponse>(
      "/settings/llm-provider"
    );
    return response.data;
  },

  /**
   * Update tenant's LLM provider settings
   */
  updateLLMProvider: async (
    data: LLMProviderUpdate
  ): Promise<LLMProviderResponse> => {
    const response = await apiClient.put<LLMProviderResponse>(
      "/settings/llm-provider",
      data
    );
    return response.data;
  },
};
