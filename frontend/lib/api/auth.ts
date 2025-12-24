import apiClient from "../api-client";
import { LoginRequest, LoginResponse, User } from "../types";

export const authApi = {
  login: async (credentials: LoginRequest): Promise<LoginResponse> => {
    const formData = new FormData();
    formData.append("username", credentials.email);
    formData.append("password", credentials.password);

    const { data } = await apiClient.post<LoginResponse>("/api/v1/auth/login", formData, {
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
      },
    });
    return data;
  },

  logout: async (): Promise<void> => {
    await apiClient.post("/api/v1/auth/logout");
  },

  getCurrentUser: async (): Promise<User> => {
    const { data } = await apiClient.get<User>("/api/v1/auth/me");
    return data;
  },
};
