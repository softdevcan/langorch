import apiClient from "../api-client";
import { User, UserCreate, UserUpdate } from "../types";

export const usersApi = {
  list: async (): Promise<User[]> => {
    const { data } = await apiClient.get<{
      items: User[];
      total: number;
      page: number;
      page_size: number;
    }>("/api/v1/users/");
    return data.items;
  },

  get: async (userId: string): Promise<User> => {
    const { data } = await apiClient.get<User>(`/api/v1/users/${userId}`);
    return data;
  },

  create: async (user: UserCreate): Promise<User> => {
    const { data } = await apiClient.post<User>("/api/v1/users/", user);
    return data;
  },

  update: async (userId: string, user: UserUpdate): Promise<User> => {
    const { data } = await apiClient.patch<User>(`/api/v1/users/${userId}`, user);
    return data;
  },

  delete: async (userId: string): Promise<void> => {
    await apiClient.delete(`/api/v1/users/${userId}`);
  },
};
