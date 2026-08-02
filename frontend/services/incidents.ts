import api from "@/lib/api";
import type {
  Incident,
  IncidentCreate,
  IncidentFilters,
  IncidentListResponse,
  IncidentUpdate,
  LogEntry,
  MessageResponse,
} from "@/types";

export const incidentsService = {
  async list(filters: IncidentFilters = {}): Promise<IncidentListResponse> {
    const response = await api.get<IncidentListResponse>("/incidents", {
      params: filters,
    });
    return response.data;
  },

  async get(id: string): Promise<Incident> {
    const response = await api.get<Incident>(`/incidents/${id}`);
    return response.data;
  },

  async create(data: IncidentCreate): Promise<Incident> {
    const response = await api.post<Incident>("/incidents", data);
    return response.data;
  },

  async update(id: string, data: IncidentUpdate): Promise<Incident> {
    const response = await api.patch<Incident>(`/incidents/${id}`, data);
    return response.data;
  },

  async delete(id: string): Promise<MessageResponse> {
    const response = await api.delete<MessageResponse>(`/incidents/${id}`);
    return response.data;
  },

  async analyze(id: string, force = false): Promise<Incident> {
    const response = await api.post<Incident>(`/incidents/${id}/analyze`, { force });
    return response.data;
  },

  async getLogs(id: string, params?: { offset?: number; limit?: number }): Promise<LogEntry[]> {
    const response = await api.get<LogEntry[]>(`/incidents/${id}/logs`, { params });
    return response.data;
  },
};
