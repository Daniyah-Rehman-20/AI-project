import api from "@/lib/api";
import type { AnalyticsOverview, ModelUsageStats } from "@/types";

export const analyticsService = {
  async getOverview(params?: { days?: number }): Promise<AnalyticsOverview> {
    const response = await api.get<AnalyticsOverview>("/analytics/overview", { params });
    return response.data;
  },

  async getModelUsage(params?: { days?: number }): Promise<ModelUsageStats> {
    const response = await api.get<ModelUsageStats>("/analytics/model-usage", { params });
    return response.data;
  },

  async getIncidentMetrics(params?: { days?: number }): Promise<AnalyticsOverview> {
    const response = await api.get<AnalyticsOverview>("/analytics/incidents", { params });
    return response.data;
  },
};
