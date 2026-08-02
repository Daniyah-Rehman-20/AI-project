export type UserRole = "admin" | "analyst" | "engineer" | "viewer";

export type IncidentSeverity = "critical" | "high" | "medium" | "low" | "info";

export type IncidentStatus =
  | "open"
  | "triaged"
  | "investigating"
  | "identified"
  | "mitigating"
  | "resolved"
  | "closed";

export type IncidentCategory =
  | "infrastructure"
  | "application"
  | "database"
  | "network"
  | "security"
  | "deployment"
  | "third_party"
  | "unknown";

export type AnalysisStatus = "queued" | "running" | "completed" | "failed";

export type DocumentStatus = "pending" | "processing" | "indexed" | "failed";

export type NotificationChannel = "email" | "slack" | "in_app" | "webhook";

export type NotificationStatus = "pending" | "sent" | "failed" | "read";

export interface User {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
  is_verified: boolean;
  role: UserRole;
  avatar_url: string | null;
  created_at: string;
  last_login_at: string | null;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  full_name: string;
}

export interface TimelineEvent {
  id?: string;
  timestamp: string;
  event_type: string;
  title: string;
  description?: string;
  actor?: string;
  metadata?: Record<string, unknown>;
}

export interface Citation {
  id?: string;
  source_type: string;
  source_id: string;
  title: string;
  excerpt?: string;
  url?: string;
  relevance_score?: number;
}

export interface Incident {
  id: string;
  title: string;
  description: string | null;
  status: IncidentStatus;
  severity: IncidentSeverity;
  category: IncidentCategory;
  source: string | null;
  external_id: string | null;
  assignee_id: string | null;
  reporter_id: string | null;
  affected_services: string[];
  tags: string[];
  analysis_status: AnalysisStatus;
  root_cause: string | null;
  recommended_fix: string | null;
  classification_confidence: number | null;
  ai_summary: string | null;
  citations: Citation[];
  timeline: TimelineEvent[];
  resolved_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface IncidentCreate {
  title: string;
  description?: string;
  severity?: IncidentSeverity;
  category?: IncidentCategory;
  source?: string;
  external_id?: string;
  affected_services?: string[];
  tags?: string[];
  metadata_json?: Record<string, unknown>;
}

export interface IncidentUpdate {
  title?: string;
  description?: string;
  status?: IncidentStatus;
  severity?: IncidentSeverity;
  category?: IncidentCategory;
  assignee_id?: string;
  affected_services?: string[];
  tags?: string[];
  root_cause?: string;
  recommended_fix?: string;
}

export interface IncidentListResponse {
  items: Incident[];
  total: number;
  offset: number;
  limit: number;
}

export interface IncidentFilters {
  status?: IncidentStatus;
  severity?: IncidentSeverity;
  category?: IncidentCategory;
  search?: string;
  assignee_id?: string;
  offset?: number;
  limit?: number;
}

export interface LogEntry {
  id: string;
  incident_id: string | null;
  source: string;
  level: string;
  message: string;
  service_name: string | null;
  host: string | null;
  timestamp: string;
  raw_payload: Record<string, unknown>;
  fingerprint: string | null;
  created_at: string;
  updated_at: string;
}

export interface Document {
  id: string;
  title: string;
  filename: string;
  content_type: string;
  size_bytes: number;
  storage_key: string;
  status: DocumentStatus;
  uploaded_by: string | null;
  source: string;
  checksum: string | null;
  page_count: number | null;
  chunk_count: number;
  error_message: string | null;
  metadata_json: Record<string, unknown>;
  tags: string[];
  created_at: string;
  updated_at: string;
}

export interface DocumentListResponse {
  items: Document[];
  total: number;
  offset: number;
  limit: number;
}

export interface Report {
  id: string;
  incident_id: string;
  title: string;
  report_type: "postmortem" | "summary";
  content_markdown: string;
  content_html: string | null;
  generated_by: "ai" | "manual";
  author_id: string | null;
  version: number;
  citations: Citation[];
  metadata_json: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface ReportListResponse {
  items: Report[];
  total: number;
  offset: number;
  limit: number;
}

export interface Notification {
  id: string;
  user_id: string | null;
  channel: NotificationChannel;
  status: NotificationStatus;
  subject: string;
  body: string;
  payload: Record<string, unknown>;
  incident_id: string | null;
  sent_at: string | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface NotificationListResponse {
  items: Notification[];
  total: number;
  offset: number;
  limit: number;
  unread_count: number;
}

export interface AnalyticsOverview {
  total_incidents: number;
  open_incidents: number;
  critical_incidents: number;
  analysis_pending: number;
  analysis_completed: number;
  incidents_by_severity: Record<string, number>;
  incidents_by_status: Record<string, number>;
  recent_incidents_7d: number;
  /** Optional enriched fields when available */
  resolved_incidents?: number;
  mean_time_to_resolve_hours?: number;
  incidents_by_category?: Record<string, number>;
  incidents_trend?: Array<{ date: string; count: number }>;
  resolution_trend?: Array<{ date: string; resolved: number; opened: number }>;
}

export interface ModelUsage {
  id: string;
  provider: string;
  model_name: string;
  operation: "chat" | "embed" | "classify";
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  latency_ms: number | null;
  cost_usd: number | null;
  user_id: string | null;
  incident_id: string | null;
  success: boolean;
  error_message: string | null;
  metadata_json: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface ModelUsageStats {
  total_requests: number;
  total_tokens: number;
  total_cost_usd: number;
  avg_latency_ms: number;
  by_provider: Array<{ provider: string; requests: number; tokens: number; cost_usd: number }>;
  by_model: Array<{ model_name: string; requests: number; tokens: number; cost_usd: number }>;
  by_operation: Array<{ operation: string; requests: number; tokens: number }>;
  daily_usage: Array<{ date: string; requests: number; tokens: number; cost_usd: number }>;
  recent: ModelUsage[];
}

export interface SearchResult {
  id: string;
  score: number;
  content: string;
  document_id: string;
  document_title: string;
  chunk_index: number;
  metadata: Record<string, unknown>;
}

export interface SearchResponse {
  query: string;
  results: SearchResult[];
  total: number;
  latency_ms: number;
}

export interface MessageResponse {
  message: string;
}

export interface PaginatedParams {
  offset?: number;
  limit?: number;
}
