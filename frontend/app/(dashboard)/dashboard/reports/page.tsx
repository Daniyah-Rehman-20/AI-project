"use client";

import { useState } from "react";
import Link from "next/link";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { formatDistanceToNow } from "date-fns";
import { FileText, Download, Plus, ExternalLink } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { reportsService } from "@/services/reports";
import { useToast } from "@/components/ui/toast";

export default function ReportsPage() {
  const [incidentId, setIncidentId] = useState("");
  const [generateOpen, setGenerateOpen] = useState(false);
  const { addToast } = useToast();
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ["reports"],
    queryFn: () => reportsService.list({ limit: 50 }),
    retry: false,
  });

  const generateMutation = useMutation({
    mutationFn: (id: string) => reportsService.generate(id, "postmortem"),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["reports"] });
      addToast({ title: "Report generated", type: "success" });
      setGenerateOpen(false);
      setIncidentId("");
    },
    onError: () => addToast({ title: "Generation failed", type: "error" }),
  });

  const handleDownload = async (id: string, title: string) => {
    try {
      const blob = await reportsService.download(id, "markdown");
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${title}.md`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      addToast({ title: "Download failed", type: "error" });
    }
  };

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">Reports</h1>
          <p className="text-muted-foreground text-sm mt-1">
            AI-generated postmortems and incident summaries
          </p>
        </div>
        <Dialog open={generateOpen} onOpenChange={setGenerateOpen}>
          <DialogTrigger>
            <Button variant="cyan">
              <Plus className="h-4 w-4" />
              Generate Report
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Generate Postmortem</DialogTitle>
            </DialogHeader>
            <div className="mt-2">
              <label className="text-sm font-medium">Incident ID</label>
              <Input
                value={incidentId}
                onChange={(e) => setIncidentId(e.target.value)}
                placeholder="Enter incident UUID"
                className="mt-1"
              />
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setGenerateOpen(false)}>
                Cancel
              </Button>
              <Button
                onClick={() => generateMutation.mutate(incidentId)}
                disabled={!incidentId || generateMutation.isPending}
              >
                {generateMutation.isPending ? <Spinner size="sm" /> : "Generate"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      <div className="ops-panel overflow-hidden">
        {isLoading ? (
          <div className="flex justify-center py-16">
            <Spinner size="lg" />
          </div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Title</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>Source</TableHead>
                <TableHead>Version</TableHead>
                <TableHead>Created</TableHead>
                <TableHead className="w-24" />
              </TableRow>
            </TableHeader>
            <TableBody>
              {(data?.items ?? []).length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} className="text-center text-muted-foreground py-12">
                    No reports generated yet
                  </TableCell>
                </TableRow>
              ) : (
                data?.items.map((report) => (
                  <TableRow key={report.id}>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <FileText className="h-4 w-4 text-cyan-accent" />
                        <span className="font-medium">{report.title}</span>
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline" className="capitalize">
                        {report.report_type}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Badge variant={report.generated_by === "ai" ? "info" : "secondary"}>
                        {report.generated_by}
                      </Badge>
                    </TableCell>
                    <TableCell className="font-mono text-sm">v{report.version}</TableCell>
                    <TableCell className="text-muted-foreground text-sm">
                      {formatDistanceToNow(new Date(report.created_at), { addSuffix: true })}
                    </TableCell>
                    <TableCell>
                      <div className="flex gap-1">
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => handleDownload(report.id, report.title)}
                        >
                          <Download className="h-3 w-3" />
                        </Button>
                        <Button variant="ghost" size="icon" asChild>
                          <Link href={`/dashboard/incidents/${report.incident_id}`}>
                            <ExternalLink className="h-3 w-3" />
                          </Link>
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        )}
      </div>
    </div>
  );
}
