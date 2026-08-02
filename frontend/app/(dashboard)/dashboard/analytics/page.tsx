"use client";

import { useQuery } from "@tanstack/react-query";
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from "recharts";
import { BarChart3, TrendingUp, AlertTriangle, CheckCircle2 } from "lucide-react";
import { Spinner } from "@/components/ui/spinner";
import { analyticsService } from "@/services/analytics";

const SEVERITY_COLORS = ["#ef4444", "#f59e0b", "#22d3ee", "#7489a3", "#566b84"];

export default function AnalyticsPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["analytics", "incidents", 90],
    queryFn: () => analyticsService.getIncidentMetrics({ days: 90 }),
    retry: false,
  });

  if (isLoading) {
    return (
      <div className="flex justify-center py-20">
        <Spinner size="lg" />
      </div>
    );
  }

  const severityData = data
    ? Object.entries(data.incidents_by_severity).map(([name, value]) => ({
        name: name.charAt(0).toUpperCase() + name.slice(1),
        value,
      }))
    : [];

  const statusData = data
    ? Object.entries(data.incidents_by_status).map(([name, value]) => ({
        name: name.charAt(0).toUpperCase() + name.slice(1),
        value,
      }))
    : [];

  const categoryData = data
    ? Object.entries(data.incidents_by_category).map(([name, value]) => ({
        name: name.replace("_", " "),
        value,
      }))
    : [];

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <BarChart3 className="h-6 w-6 text-cyan-accent" />
          Analytics
        </h1>
        <p className="text-muted-foreground text-sm mt-1">90-day incident metrics and trends</p>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: "Total Incidents", value: data?.total_incidents ?? 0, icon: AlertTriangle },
          { label: "Open", value: data?.open_incidents ?? 0, icon: TrendingUp },
          { label: "Resolved", value: data?.resolved_incidents ?? 0, icon: CheckCircle2 },
          {
            label: "MTTR",
            value: `${(data?.mean_time_to_resolve_hours ?? 0).toFixed(1)}h`,
            icon: BarChart3,
          },
        ].map((kpi) => (
          <div key={kpi.label} className="ops-panel p-5">
            <p className="text-xs uppercase tracking-wider text-muted-foreground">{kpi.label}</p>
            <p className="text-2xl font-bold font-mono mt-1">{kpi.value}</p>
          </div>
        ))}
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        <div className="ops-panel p-5">
          <h3 className="font-semibold mb-4">Resolution Trend</h3>
          <div className="h-64">
            {(data?.resolution_trend ?? []).length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={data?.resolution_trend}>
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
                    dataKey="opened"
                    stroke="#f59e0b"
                    fill="#f59e0b20"
                    name="Opened"
                  />
                  <Area
                    type="monotone"
                    dataKey="resolved"
                    stroke="#22d3ee"
                    fill="#22d3ee20"
                    name="Resolved"
                  />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex h-full items-center justify-center text-muted-foreground text-sm">
                No resolution trend data
              </div>
            )}
          </div>
        </div>

        <div className="ops-panel p-5">
          <h3 className="font-semibold mb-4">By Severity</h3>
          <div className="h-64">
            {severityData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={severityData}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={90}
                    dataKey="value"
                    label={({ name, value }) => `${name}: ${value}`}
                  >
                    {severityData.map((_, i) => (
                      <Cell key={i} fill={SEVERITY_COLORS[i % SEVERITY_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{
                      background: "hsl(var(--card))",
                      border: "1px solid hsl(var(--border))",
                      borderRadius: "8px",
                    }}
                  />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex h-full items-center justify-center text-muted-foreground text-sm">
                No severity data
              </div>
            )}
          </div>
        </div>

        <div className="ops-panel p-5">
          <h3 className="font-semibold mb-4">By Status</h3>
          <div className="h-64">
            {statusData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={statusData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                  <XAxis
                    dataKey="name"
                    tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }}
                  />
                  <YAxis tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} />
                  <Tooltip
                    contentStyle={{
                      background: "hsl(var(--card))",
                      border: "1px solid hsl(var(--border))",
                      borderRadius: "8px",
                    }}
                  />
                  <Bar dataKey="value" fill="#22d3ee" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex h-full items-center justify-center text-muted-foreground text-sm">
                No status data
              </div>
            )}
          </div>
        </div>

        <div className="ops-panel p-5">
          <h3 className="font-semibold mb-4">By Category</h3>
          <div className="h-64">
            {categoryData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={categoryData} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                  <XAxis type="number" tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} />
                  <YAxis
                    type="category"
                    dataKey="name"
                    tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }}
                    width={90}
                  />
                  <Tooltip
                    contentStyle={{
                      background: "hsl(var(--card))",
                      border: "1px solid hsl(var(--border))",
                      borderRadius: "8px",
                    }}
                  />
                  <Bar dataKey="value" fill="#566b84" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex h-full items-center justify-center text-muted-foreground text-sm">
                No category data
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
