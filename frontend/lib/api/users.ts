import apiClient from "../api-client";
import { User, UserCreate, UserUpdate } from "../types";

export const usersApi = {
  list: async (): Promise<User[]> => {
    const { data } = await apiClient.get<{
      items: User[];
      total: number;
      page: number;
      page_size: number;
    }>("/users/");
    return data.items;
  },

  get: async (userId: string): Promise<User> => {
    const { data } = await apiClient.get<User>(`/users/${userId}`);
    return data;
  },

  create: async (user: UserCreate): Promise<User> => {
    const { data } = await apiClient.post<User>("/users/", user);
    return data;
  },

  update: async (userId: string, user: UserUpdate): Promise<User> => {
    const { data } = await apiClient.patch<User>(`/users/${userId}`, user);
    return data;
  },

  delete: async (userId: string): Promise<void> => {
    await apiClient.delete(`/users/${userId}`);
  },
};
