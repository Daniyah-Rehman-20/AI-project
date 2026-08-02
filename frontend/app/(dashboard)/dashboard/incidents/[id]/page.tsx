"use client";

import { useParams } from "next/navigation";
import Link from "next/link";
import { format } from "date-fns";
import ReactMarkdown from "react-markdown";
import {
  ArrowLeft,
  Brain,
  Clock,
  FileText,
  RefreshCw,
  Terminal,
} from "lucide-react";
import { Badge, severityBadgeVariant, statusBadgeVariant } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Spinner, PageLoader } from "@/components/ui/spinner";
import { Select } from "@/components/ui/select";
import {
  useIncident,
  useIncidentLogs,
  useAnalyzeIncident,
  useUpdateIncident,
} from "@/hooks/use-incidents";
import { useToast } from "@/components/ui/toast";
import type { IncidentStatus } from "@/types";

const statusOptions = [
  { value: "open", label: "Open" },
  { value: "triaged", label: "Triaged" },
  { value: "investigating", label: "Investigating" },
  { value: "identified", label: "Identified" },
  { value: "mitigating", label: "Mitigating" },
  { value: "resolved", label: "Resolved" },
  { value: "closed", label: "Closed" },
];

export default function IncidentDetailPage() {
  const params = useParams();
  const id = params.id as string;
  const { addToast } = useToast();

  const { data: incident, isLoading } = useIncident(id);
  const { data: logs, isLoading: logsLoading } = useIncidentLogs(id);
  const analyze = useAnalyzeIncident(id);
  const update = useUpdateIncident(id);

  if (isLoading) return <PageLoader />;
  if (!incident) {
    return (
      <div className="text-center py-20">
        <p className="text-muted-foreground">Incident not found</p>
        <Button variant="outline" className="mt-4" asChild>
          <Link href="/dashboard/incidents">Back to incidents</Link>
        </Button>
      </div>
    );
  }

  const handleAnalyze = async () => {
    try {
      await analyze.mutateAsync(true);
      addToast({ title: "Analysis started", type: "success" });
    } catch {
      addToast({ title: "Analysis failed", type: "error" });
    }
  };

  const handleStatusChange = async (status: string) => {
    try {
      await update.mutateAsync({ status: status as IncidentStatus });
      addToast({ title: "Status updated", type: "success" });
    } catch {
      addToast({ title: "Update failed", type: "error" });
    }
  };

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-start gap-4">
        <Button variant="ghost" size="icon" asChild>
          <Link href="/dashboard/incidents">
            <ArrowLeft className="h-4 w-4" />
          </Link>
        </Button>
        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap items-center gap-2 mb-2">
            <Badge variant={severityBadgeVariant(incident.severity)}>
              {incident.severity}
            </Badge>
            <Badge variant={statusBadgeVariant(incident.status)}>{incident.status}</Badge>
            <Badge variant="outline" className="capitalize">
              {incident.category}
            </Badge>
            {incident.analysis_status && (
              <Badge variant="info">{incident.analysis_status}</Badge>
            )}
          </div>
          <h1 className="text-2xl font-bold">{incident.title}</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Created {format(new Date(incident.created_at), "PPpp")}
            {incident.affected_services.length > 0 &&
              ` · Services: ${incident.affected_services.join(", ")}`}
          </p>
        </div>
        <div className="flex gap-2 shrink-0">
          <Select
            value={incident.status}
            onChange={(e) => handleStatusChange(e.target.value)}
            options={statusOptions}
            className="w-40"
          />
          <Button variant="cyan" onClick={handleAnalyze} disabled={analyze.isPending}>
            {analyze.isPending ? (
              <Spinner size="sm" />
            ) : (
              <>
                <Brain className="h-4 w-4" />
                Analyze
              </>
            )}
          </Button>
        </div>
      </div>

      {incident.description && (
        <div className="ops-panel p-5">
          <h3 className="font-semibold mb-2">Description</h3>
          <p className="text-muted-foreground whitespace-pre-wrap">{incident.description}</p>
        </div>
      )}

      <div className="grid lg:grid-cols-2 gap-6">
        {/* AI Analysis */}
        <div className="ops-panel p-5">
          <div className="flex items-center gap-2 mb-4">
            <Brain className="h-5 w-5 text-cyan-accent" />
            <h3 className="font-semibold">AI Analysis</h3>
            {incident.classification_confidence != null && (
              <Badge variant="info" className="ml-auto">
                {(incident.classification_confidence * 100).toFixed(0)}% confidence
              </Badge>
            )}
          </div>

          {incident.ai_summary ? (
            <div className="prose prose-invert prose-sm max-w-none text-muted-foreground">
              <ReactMarkdown>{incident.ai_summary}</ReactMarkdown>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">
              No AI analysis yet. Click Analyze to generate insights.
            </p>
          )}

          {incident.root_cause && (
            <div className="mt-4 pt-4 border-t border-border/60">
              <h4 className="text-sm font-medium text-red-400 mb-1">Root Cause</h4>
              <p className="text-sm text-muted-foreground">{incident.root_cause}</p>
            </div>
          )}

          {incident.recommended_fix && (
            <div className="mt-4 pt-4 border-t border-border/60">
              <h4 className="text-sm font-medium text-emerald-400 mb-1">Recommended Fix</h4>
              <p className="text-sm text-muted-foreground">{incident.recommended_fix}</p>
            </div>
          )}

          {incident.citations.length > 0 && (
            <div className="mt-4 pt-4 border-t border-border/60">
              <h4 className="text-sm font-medium mb-2 flex items-center gap-1">
                <FileText className="h-3 w-3" /> Citations
              </h4>
              <ul className="space-y-2">
                {incident.citations.map((c, i) => (
                  <li key={i} className="text-sm text-muted-foreground border-l-2 border-cyan-accent/30 pl-3">
                    <span className="font-medium text-foreground">{c.title}</span>
                    {c.excerpt && <p className="text-xs mt-0.5">{c.excerpt}</p>}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>

        {/* Timeline */}
        <div className="ops-panel p-5">
          <div className="flex items-center gap-2 mb-4">
            <Clock className="h-5 w-5 text-cyan-accent" />
            <h3 className="font-semibold">Timeline</h3>
          </div>
          {incident.timeline.length > 0 ? (
            <div className="space-y-4">
              {incident.timeline.map((event, i) => (
                <div key={i} className="flex gap-3">
                  <div className="flex flex-col items-center">
                    <div className="h-2 w-2 rounded-full bg-cyan-accent mt-2" />
                    {i < incident.timeline.length - 1 && (
                      <div className="w-px flex-1 bg-border/60 mt-1" />
                    )}
                  </div>
                  <div className="pb-4">
                    <p className="text-sm font-medium">{event.title}</p>
                    {event.description && (
                      <p className="text-xs text-muted-foreground mt-0.5">{event.description}</p>
                    )}
                    <p className="text-xs text-muted-foreground mt-1 font-mono">
                      {format(new Date(event.timestamp), "PPp")}
                      {event.actor && ` · ${event.actor}`}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">No timeline events recorded</p>
          )}
        </div>
      </div>

      {/* Logs */}
      <div className="ops-panel">
        <div className="flex items-center gap-2 p-5 border-b border-border/60">
          <Terminal className="h-5 w-5 text-cyan-accent" />
          <h3 className="font-semibold">Related Logs</h3>
          <Button variant="ghost" size="sm" className="ml-auto">
            <RefreshCw className="h-3 w-3" />
          </Button>
        </div>
        <div className="p-4 font-mono text-xs max-h-96 overflow-y-auto">
          {logsLoading ? (
            <div className="flex justify-center py-8">
              <Spinner />
            </div>
          ) : (logs ?? []).length === 0 ? (
            <p className="text-muted-foreground text-center py-8">No logs associated</p>
          ) : (
            <div className="space-y-1">
              {logs?.map((log) => (
                <div
                  key={log.id}
                  className="flex gap-3 py-1 hover:bg-muted/20 rounded px-2 -mx-2"
                >
                  <span className="text-muted-foreground shrink-0">
                    {format(new Date(log.timestamp), "HH:mm:ss")}
                  </span>
                  <span
                    className={`shrink-0 uppercase w-12 ${
                      log.level === "error"
                        ? "text-red-400"
                        : log.level === "warn"
                          ? "text-amber-400"
                          : "text-cyan-accent"
                    }`}
                  >
                    {log.level}
                  </span>
                  <span className="text-muted-foreground shrink-0">
                    [{log.service_name ?? log.source}]
                  </span>
                  <span className="text-foreground">{log.message}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
