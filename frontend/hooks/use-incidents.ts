"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { incidentsService } from "@/services/incidents";
import type { IncidentCreate, IncidentFilters, IncidentUpdate } from "@/types";

export function useIncidents(filters: IncidentFilters = {}) {
  return useQuery({
    queryKey: ["incidents", filters],
    queryFn: () => incidentsService.list(filters),
    staleTime: 30 * 1000,
  });
}

export function useIncident(id: string) {
  return useQuery({
    queryKey: ["incidents", id],
    queryFn: () => incidentsService.get(id),
    enabled: !!id,
    staleTime: 15 * 1000,
  });
}

export function useIncidentLogs(id: string) {
  return useQuery({
    queryKey: ["incidents", id, "logs"],
    queryFn: () => incidentsService.getLogs(id),
    enabled: !!id,
    staleTime: 15 * 1000,
  });
}

export function useCreateIncident() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: IncidentCreate) => incidentsService.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["incidents"] });
    },
  });
}

export function useUpdateIncident(id: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: IncidentUpdate) => incidentsService.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["incidents"] });
      queryClient.invalidateQueries({ queryKey: ["incidents", id] });
    },
  });
}

export function useAnalyzeIncident(id: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (force?: boolean) => incidentsService.analyze(id, force),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["incidents", id] });
    },
  });
}

export function useDeleteIncident() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => incidentsService.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["incidents"] });
    },
  });
}
