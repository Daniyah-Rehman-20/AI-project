import api from "@/lib/api";
import type {
  LoginRequest,
  MessageResponse,
  RegisterRequest,
  TokenResponse,
  User,
} from "@/types";

export const authService = {
  async login(data: LoginRequest): Promise<TokenResponse> {
    const response = await api.post<TokenResponse>("/auth/login", data);
    return response.data;
  },

  async register(data: RegisterRequest): Promise<User> {
    const response = await api.post<User>("/auth/register", data);
    return response.data;
  },

  async refresh(refreshToken: string): Promise<TokenResponse> {
    const response = await api.post<TokenResponse>("/auth/refresh", {
      refresh_token: refreshToken,
    });
    return response.data;
  },

  async logout(refreshToken: string): Promise<MessageResponse> {
    const response = await api.post<MessageResponse>("/auth/logout", {
      refresh_token: refreshToken,
    });
    return response.data;
  },

  async me(): Promise<User> {
    const response = await api.get<User>("/auth/me");
    return response.data;
  },

  getGoogleOAuthUrl(): string {
    const baseUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";
    return `${baseUrl}/auth/oauth/google`;
  },
};
