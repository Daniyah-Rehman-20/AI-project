import api from "@/lib/api";
import type { MessageResponse, NotificationListResponse, PaginatedParams } from "@/types";

export const notificationsService = {
  async list(params: PaginatedParams = {}): Promise<NotificationListResponse> {
    const response = await api.get<NotificationListResponse>("/notifications", { params });
    return response.data;
  },

  async markRead(id: string): Promise<MessageResponse> {
    const response = await api.patch<MessageResponse>(`/notifications/${id}/read`);
    return response.data;
  },

  async markAllRead(): Promise<MessageResponse> {
    const response = await api.post<MessageResponse>("/notifications/read-all");
    return response.data;
  },
};
