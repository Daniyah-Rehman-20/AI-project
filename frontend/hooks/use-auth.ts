"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useCallback } from "react";
import { authService } from "@/services/auth";
import { useAuthStore } from "@/store/auth-store";
import type { LoginRequest, RegisterRequest } from "@/types";

export function useAuth() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { user, isAuthenticated, login: storeLogin, logout: storeLogout, setUser } = useAuthStore();

  const meQuery = useQuery({
    queryKey: ["auth", "me"],
    queryFn: () => authService.me(),
    enabled: isAuthenticated,
    retry: false,
    staleTime: 5 * 60 * 1000,
  });

  const loginMutation = useMutation({
    mutationFn: async (credentials: LoginRequest) => {
      const tokens = await authService.login(credentials);
      useAuthStore.getState().setTokens(tokens.access_token, tokens.refresh_token);
      const userData = await authService.me();
      return { tokens, user: userData };
    },
    onSuccess: async ({ tokens, user: userData }) => {
      storeLogin(tokens.access_token, tokens.refresh_token, userData);
      queryClient.setQueryData(["auth", "me"], userData);
      router.push("/dashboard");
    },
  });

  const registerMutation = useMutation({
    mutationFn: (data: RegisterRequest) => authService.register(data),
    onSuccess: () => {
      router.push("/login");
    },
  });

  const logout = useCallback(async () => {
    const refreshToken = useAuthStore.getState().refreshToken;
    if (refreshToken) {
      try {
        await authService.logout(refreshToken);
      } catch {
        // Ignore logout errors
      }
    }
    storeLogout();
    queryClient.clear();
    router.push("/login");
  }, [storeLogout, queryClient, router]);

  return {
    user: meQuery.data ?? user,
    isAuthenticated,
    isLoading: meQuery.isLoading,
    isLoggingIn: loginMutation.isPending,
    loginError: loginMutation.error,
    login: loginMutation.mutate,
    register: registerMutation.mutate,
    isRegistering: registerMutation.isPending,
    logout,
    setUser,
  };
}
