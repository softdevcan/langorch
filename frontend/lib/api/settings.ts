import apiClient from "../api-client";
import type {
  EmbeddingProviderUpdate,
  EmbeddingProviderResponse,
  EmbeddingProviderTest,
  EmbeddingProviderTestResponse,
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
};
