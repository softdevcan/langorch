"use client";

import { useEffect, useState, useRef } from "react";
import { useRouter, usePathname } from "next/navigation";
import { useAuthStore } from "@/stores/auth-store";

interface ProtectedRouteProps {
  children: React.ReactNode;
}

// Helper function to check if token is expired
function isTokenExpired(token: string): boolean {
  try {
    // Decode JWT payload (base64)
    const payload = JSON.parse(atob(token.split(".")[1]));
    const exp = payload.exp;

    if (!exp) return true;

    // Check if token is expired (with 30 second buffer)
    const now = Math.floor(Date.now() / 1000);
    return exp < now + 30;
  } catch (error) {
    console.error("Error decoding token:", error);
    return true; // If we can't decode, consider it expired
  }
}

export function ProtectedRoute({ children }: ProtectedRouteProps) {
  const router = useRouter();
  const pathname = usePathname();
  const { user, token } = useAuthStore();
  const [isChecking, setIsChecking] = useState(true);
  const hasCheckedInitial = useRef(false);

  useEffect(() => {
    const checkAuth = () => {
      const publicPaths = ["/login", "/register", "/forgot-password"];
      const isPublicPath = publicPaths.some((path) => pathname.startsWith(path));

      // If we have a token, validate it
      if (token) {
        if (isTokenExpired(token)) {
          console.log("Token expired, clearing auth and redirecting to login...");
          // Clear auth state and redirect to login
          localStorage.removeItem("access_token");
          localStorage.removeItem("auth-storage");

          // Force page reload to clear zustand state
          if (!isPublicPath) {
            window.location.href = "/login";
            return;
          }
        }
      }

      // If on public path and authenticated with valid token, redirect to dashboard
      if (isPublicPath && token && user) {
        router.replace("/dashboard");
        return;
      }

      // If on protected path and not authenticated, redirect to login
      if (!isPublicPath && !token) {
        router.replace("/login");
        return;
      }

      // Only show loading on initial check, not on subsequent navigation
      if (!hasCheckedInitial.current) {
        hasCheckedInitial.current = true;
      }
      setIsChecking(false);
    };

    checkAuth();
  }, [token, user, pathname, router]);

  // Show loading state only during initial authentication check
  if (isChecking && !hasCheckedInitial.current) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-gray-900 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading...</p>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}
