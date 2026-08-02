"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { formatDistanceToNow } from "date-fns";
import {
  AlertTriangle,
  CheckCircle2,
  Clock,
  TrendingUp,
  ArrowRight,
  Activity,
} from "lucide-react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
} from "recharts";
import { Badge, severityBadgeVariant, statusBadgeVariant } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { useIncidents } from "@/hooks/use-incidents";
import { analyticsService } from "@/services/analytics";

function KpiStat({
  label,
  value,
  icon: Icon,
  trend,
  accent,
}: {
  label: string;
  value: string | number;
  icon: React.ElementType;
  trend?: string;
  accent?: string;
}) {
  return (
    <div className="ops-panel p-5 transition-all duration-200 hover:border-cyan-accent/30">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs uppercase tracking-wider text-muted-foreground mb-1">{label}</p>
          <p className={`text-3xl font-bold font-mono ${accent ?? ""}`}>{value}</p>
          {trend && <p className="text-xs text-muted-foreground mt-1">{trend}</p>}
        </div>
        <div className="flex h-10 w-10 items-center justify-center rounded-md bg-cyan-accent/10 border border-cyan-accent/20">
          <Icon className="h-5 w-5 text-cyan-accent" />
        </div>
      </div>
    </div>
  );
}

export default function DashboardPage() {
  const { data: incidents, isLoading: incidentsLoading } = useIncidents({ limit: 5 });
  const { data: analytics, isLoading: analyticsLoading } = useQuery({
    queryKey: ["analytics", "overview"],
    queryFn: () => analyticsService.getOverview({ days: 30 }),
    retry: false,
  });

  const isLoading = incidentsLoading || analyticsLoading;

  const severityData = analytics
    ? Object.entries(analytics.incidents_by_severity).map(([name, value]) => ({
        name: name.charAt(0).toUpperCase() + name.slice(1),
        value,
      }))
    : [];

  const trendData = analytics?.incidents_trend ?? [];

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Hero command center header */}
      <div className="relative overflow-hidden rounded-xl border border-border/60 bg-gradient-to-br from-steel-900/80 via-card/60 to-steel-950/80 p-6 md:p-8">
        <div className="absolute inset-0 bg-grid-pattern bg-grid opacity-[0.03]" />
        <div className="relative z-10 flex flex-col md:flex-row md:items-end md:justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <Activity className="h-4 w-4 text-cyan-accent animate-pulse-glow" />
              <span className="text-xs uppercase tracking-[0.2em] text-cyan-accent font-medium">
                Live Operations
              </span>
            </div>
            <h1 className="text-2xl md:text-3xl font-bold tracking-tight">
              Command Center
            </h1>
            <p className="text-muted-foreground mt-1 max-w-xl">
              Real-time incident intelligence across your infrastructure. Monitor, triage, and resolve with AI-assisted insights.
            </p>
          </div>
          <div className="flex gap-2">
            <Button variant="cyan" asChild>
              <Link href="/dashboard/incidents">View All Incidents</Link>
            </Button>
            <Button variant="outline" asChild>
              <Link href="/dashboard/knowledge">Search Knowledge</Link>
            </Button>
          </div>
        </div>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-20">
          <Spinner size="lg" />
        </div>
      ) : (
        <>
          {/* KPI row */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <KpiStat
              label="Open Incidents"
              value={analytics?.open_incidents ?? 0}
              icon={AlertTriangle}
              accent="text-amber-400"
            />
            <KpiStat
              label="Critical"
              value={analytics?.critical_incidents ?? 0}
              icon={AlertTriangle}
              accent="text-red-400"
            />
            <KpiStat
              label="Resolved (30d)"
              value={analytics?.resolved_incidents ?? 0}
              icon={CheckCircle2}
              accent="text-emerald-400"
            />
            <KpiStat
              label="MTTR"
              value={`${(analytics?.mean_time_to_resolve_hours ?? 0).toFixed(1)}h`}
              icon={Clock}
              trend="Mean time to resolve"
            />
          </div>

          {/* Charts + recent incidents */}
          <div className="grid lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2 ops-panel p-5">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-semibold flex items-center gap-2">
                  <TrendingUp className="h-4 w-4 text-cyan-accent" />
                  Incident Trend (30d)
                </h3>
              </div>
              <div className="h-64">
                {trendData.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={trendData}>
                      <defs>
                        <linearGradient id="cyanGrad" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#22d3ee" stopOpacity={0.3} />
                          <stop offset="95%" stopColor="#22d3ee" stopOpacity={0} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                      <XAxis
                        dataKey="date"
                        tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
                        tickFormatter={(v: string) => v.slice(5)}
                      />
                      <YAxis tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} />
                      <Tooltip
                        contentStyle={{
                          background: "hsl(var(--card))",
                          border: "1px solid hsl(var(--border))",
                          borderRadius: "8px",
                        }}
                      />
                      <Area
                        type="monotone"
                        dataKey="count"
                        stroke="#22d3ee"
                        fill="url(#cyanGrad)"
                        strokeWidth={2}
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="flex h-full items-center justify-center text-muted-foreground text-sm">
                    No trend data available
                  </div>
                )}
              </div>
            </div>

            <div className="ops-panel p-5">
              <h3 className="font-semibold mb-4">By Severity</h3>
              <div className="h-64">
                {severityData.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={severityData} layout="vertical">
                      <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                      <XAxis type="number" tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} />
                      <YAxis
                        type="category"
                        dataKey="name"
                        tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
                        width={70}
                      />
                      <Tooltip
                        contentStyle={{
                          background: "hsl(var(--card))",
                          border: "1px solid hsl(var(--border))",
                          borderRadius: "8px",
                        }}
                      />
                      <Bar dataKey="value" fill="#22d3ee" radius={[0, 4, 4, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="flex h-full items-center justify-center text-muted-foreground text-sm">
                    No severity data
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Recent incidents */}
          <div className="ops-panel">
            <div className="flex items-center justify-between p-5 border-b border-border/60">
              <h3 className="font-semibold">Recent Incidents</h3>
              <Button variant="ghost" size="sm" asChild>
                <Link href="/dashboard/incidents">
                  View all <ArrowRight className="h-3 w-3 ml-1" />
                </Link>
              </Button>
            </div>
            <div className="divide-y divide-border/40">
              {(incidents?.items ?? []).length === 0 ? (
                <p className="p-5 text-sm text-muted-foreground">No incidents found</p>
              ) : (
                incidents?.items.map((incident) => (
                  <Link
                    key={incident.id}
                    href={`/dashboard/incidents/${incident.id}`}
                    className="flex items-center justify-between p-4 hover:bg-muted/20 transition-colors"
                  >
                    <div className="min-w-0 flex-1">
                      <p className="font-medium truncate">{incident.title}</p>
                      <p className="text-xs text-muted-foreground mt-0.5">
                        {formatDistanceToNow(new Date(incident.created_at), { addSuffix: true })}
                        {incident.affected_services.length > 0 &&
                          ` · ${incident.affected_services.join(", ")}`}
                      </p>
                    </div>
                    <div className="flex items-center gap-2 ml-4 shrink-0">
                      <Badge variant={severityBadgeVariant(incident.severity)}>
                        {incident.severity}
                      </Badge>
                      <Badge variant={statusBadgeVariant(incident.status)}>
                        {incident.status}
                      </Badge>
                    </div>
                  </Link>
                ))
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
