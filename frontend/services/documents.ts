import api from "@/lib/api";
import type { Document, DocumentListResponse, MessageResponse, PaginatedParams } from "@/types";

export const documentsService = {
  async list(params: PaginatedParams = {}): Promise<DocumentListResponse> {
    const response = await api.get<DocumentListResponse>("/documents", { params });
    return response.data;
  },

  async get(id: string): Promise<Document> {
    const response = await api.get<Document>(`/documents/${id}`);
    return response.data;
  },

  async upload(file: File, title?: string, tags?: string[]): Promise<Document> {
    const formData = new FormData();
    formData.append("file", file);
    if (title) formData.append("title", title);
    if (tags?.length) formData.append("tags", JSON.stringify(tags));

    const response = await api.post<Document>("/documents/upload", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    return response.data;
  },

  async delete(id: string): Promise<MessageResponse> {
    const response = await api.delete<MessageResponse>(`/documents/${id}`);
    return response.data;
  },

  async reindex(id: string): Promise<Document> {
    const response = await api.post<Document>(`/documents/${id}/reindex`);
    return response.data;
  },
};
