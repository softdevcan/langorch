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
      "/api/v1/settings/embedding-provider"
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
      "/api/v1/settings/embedding-provider",
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
      "/api/v1/settings/embedding-provider/test",
      data
    );
    return response.data;
  },

  /**
   * Get current tenant's LLM provider settings
   */
  getLLMProvider: async (): Promise<LLMProviderResponse> => {
    const response = await apiClient.get<LLMProviderResponse>(
      "/api/v1/settings/llm-provider"
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
      "/api/v1/settings/llm-provider",
      data
    );
    return response.data;
  },
};
