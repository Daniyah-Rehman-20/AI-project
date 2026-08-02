import api from "@/lib/api";
import type { PaginatedParams, Report, ReportListResponse } from "@/types";

export const reportsService = {
  async list(params: PaginatedParams & { incident_id?: string } = {}): Promise<ReportListResponse> {
    const response = await api.get<ReportListResponse>("/reports", { params });
    return response.data;
  },

  async get(id: string): Promise<Report> {
    const response = await api.get<Report>(`/reports/${id}`);
    return response.data;
  },

  async generate(incidentId: string, reportType: "postmortem" | "summary" = "postmortem"): Promise<Report> {
    const response = await api.post<Report>("/reports/generate", {
      incident_id: incidentId,
      report_type: reportType,
    });
    return response.data;
  },

  async download(id: string, format: "markdown" | "pdf" = "markdown"): Promise<Blob> {
    const response = await api.get(`/reports/${id}/download`, {
      params: { format },
      responseType: "blob",
    });
    return response.data;
  },
};
