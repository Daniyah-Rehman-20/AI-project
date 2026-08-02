"use client";

import { useQuery } from "@tanstack/react-query";
import { formatDistanceToNow } from "date-fns";
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
} from "recharts";
import { Cpu, Zap, DollarSign, Clock } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Spinner } from "@/components/ui/spinner";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { analyticsService } from "@/services/analytics";
import { formatDuration } from "@/lib/utils";

export default function AIUsagePage() {
  const { data, isLoading } = useQuery({
    queryKey: ["analytics", "model-usage", 30],
    queryFn: () => analyticsService.getModelUsage({ days: 30 }),
    retry: false,
  });

  if (isLoading) {
    return (
      <div className="flex justify-center py-20">
        <Spinner size="lg" />
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Cpu className="h-6 w-6 text-cyan-accent" />
          AI Usage
        </h1>
        <p className="text-muted-foreground text-sm mt-1">
          Model consumption, token usage, and cost tracking (30d)
        </p>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          {
            label: "Total Requests",
            value: (data?.total_requests ?? 0).toLocaleString(),
            icon: Zap,
          },
          {
            label: "Total Tokens",
            value: (data?.total_tokens ?? 0).toLocaleString(),
            icon: Cpu,
          },
          {
            label: "Est. Cost",
            value: `$${(data?.total_cost_usd ?? 0).toFixed(2)}`,
            icon: DollarSign,
          },
          {
            label: "Avg Latency",
            value: formatDuration(data?.avg_latency_ms ?? 0),
            icon: Clock,
          },
        ].map((kpi) => (
          <div key={kpi.label} className="ops-panel p-5">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs uppercase tracking-wider text-muted-foreground">
                  {kpi.label}
                </p>
                <p className="text-2xl font-bold font-mono mt-1">{kpi.value}</p>
              </div>
              <kpi.icon className="h-5 w-5 text-cyan-accent" />
            </div>
          </div>
        ))}
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        <div className="ops-panel p-5">
          <h3 className="font-semibold mb-4">Daily Usage</h3>
          <div className="h-64">
            {(data?.daily_usage ?? []).length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={data?.daily_usage}>
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
                    dataKey="tokens"
                    stroke="#22d3ee"
                    fill="#22d3ee20"
                    name="Tokens"
                  />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex h-full items-center justify-center text-muted-foreground text-sm">
                No usage data
              </div>
            )}
          </div>
        </div>

        <div className="ops-panel p-5">
          <h3 className="font-semibold mb-4">By Provider</h3>
          <div className="h-64">
            {(data?.by_provider ?? []).length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={data?.by_provider}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                  <XAxis
                    dataKey="provider"
                    tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
                  />
                  <YAxis tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} />
                  <Tooltip
                    contentStyle={{
                      background: "hsl(var(--card))",
                      border: "1px solid hsl(var(--border))",
                      borderRadius: "8px",
                    }}
                  />
                  <Bar dataKey="requests" fill="#22d3ee" name="Requests" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex h-full items-center justify-center text-muted-foreground text-sm">
                No provider data
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="ops-panel overflow-hidden">
        <div className="p-5 border-b border-border/60">
          <h3 className="font-semibold">Recent Requests</h3>
        </div>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Model</TableHead>
              <TableHead>Operation</TableHead>
              <TableHead>Tokens</TableHead>
              <TableHead>Latency</TableHead>
              <TableHead>Cost</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Time</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {(data?.recent ?? []).length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} className="text-center text-muted-foreground py-12">
                  No recent model usage
                </TableCell>
              </TableRow>
            ) : (
              data?.recent.map((usage) => (
                <TableRow key={usage.id}>
                  <TableCell>
                    <div>
                      <p className="font-medium text-sm">{usage.model_name}</p>
                      <p className="text-xs text-muted-foreground">{usage.provider}</p>
                    </div>
                  </TableCell>
                  <TableCell>
                    <Badge variant="outline">{usage.operation}</Badge>
                  </TableCell>
                  <TableCell className="font-mono text-sm">
                    {usage.total_tokens.toLocaleString()}
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {usage.latency_ms ? formatDuration(usage.latency_ms) : "—"}
                  </TableCell>
                  <TableCell className="font-mono text-sm">
                    {usage.cost_usd != null ? `$${usage.cost_usd.toFixed(4)}` : "—"}
                  </TableCell>
                  <TableCell>
                    <Badge variant={usage.success ? "success" : "critical"}>
                      {usage.success ? "OK" : "Fail"}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-muted-foreground text-sm">
                    {formatDistanceToNow(new Date(usage.created_at), { addSuffix: true })}
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
