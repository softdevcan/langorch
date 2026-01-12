import apiClient from "../api-client";
import { LoginRequest, LoginResponse, User } from "../types";

export const authApi = {
  login: async (credentials: LoginRequest): Promise<LoginResponse> => {
    const { data } = await apiClient.post<LoginResponse>("/auth/login", credentials);
    return data;
  },

  logout: async (): Promise<void> => {
    await apiClient.post("/auth/logout");
  },

  getCurrentUser: async (): Promise<User> => {
    const { data } = await apiClient.get<User>("/auth/me");
    return data;
  },
};
