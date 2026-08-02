import api from "@/lib/api";
import type { SearchResponse } from "@/types";

export interface SearchParams {
  query: string;
  limit?: number;
  min_score?: number;
  document_ids?: string[];
}

export const searchService = {
  async semantic(params: SearchParams): Promise<SearchResponse> {
    const response = await api.post<SearchResponse>("/search/semantic", params);
    return response.data;
  },

  async hybrid(params: SearchParams): Promise<SearchResponse> {
    const response = await api.post<SearchResponse>("/search/hybrid", params);
    return response.data;
  },
};
