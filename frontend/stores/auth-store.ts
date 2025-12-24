import { create } from "zustand";
import { persist } from "zustand/middleware";
import { User, LoginRequest } from "@/lib/types";
import { authApi } from "@/lib/api/auth";

interface AuthState {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  error: string | null;

  // Actions
  login: (credentials: LoginRequest) => Promise<void>;
  logout: () => Promise<void>;
  setUser: (user: User | null) => void;
  clearError: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      token: null,
      isLoading: false,
      error: null,

      login: async (credentials: LoginRequest) => {
        set({ isLoading: true, error: null });
        try {
          const response = await authApi.login(credentials);

          // Store token in localStorage
          localStorage.setItem("access_token", response.access_token);

          set({
            user: response.user,
            token: response.access_token,
            isLoading: false,
            error: null,
          });
        } catch (error: any) {
          const errorMessage = error.response?.data?.detail || "Login failed";
          set({
            error: errorMessage,
            isLoading: false,
            user: null,
            token: null,
          });
          throw error;
        }
      },

      logout: async () => {
        try {
          await authApi.logout();
        } catch (error) {
          console.error("Logout error:", error);
        } finally {
          // Clear token from localStorage
          localStorage.removeItem("access_token");

          set({
            user: null,
            token: null,
            error: null,
          });
        }
      },

      setUser: (user: User | null) => {
        set({ user });
      },

      clearError: () => {
        set({ error: null });
      },
    }),
    {
      name: "auth-storage",
      partialize: (state) => ({
        user: state.user,
        token: state.token,
      }),
    }
  )
);
