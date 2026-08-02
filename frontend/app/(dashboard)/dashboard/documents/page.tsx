"use client";

import { useState, useRef } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { formatDistanceToNow } from "date-fns";
import { Upload, FileText, Trash2, RefreshCw } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { documentsService } from "@/services/documents";
import { useToast } from "@/components/ui/toast";
import { formatBytes } from "@/lib/utils";

function statusVariant(status: string) {
  switch (status) {
    case "indexed":
      return "success" as const;
    case "processing":
      return "warning" as const;
    case "failed":
      return "critical" as const;
    default:
      return "outline" as const;
  }
}

export default function DocumentsPage() {
  const [title, setTitle] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);
  const { addToast } = useToast();
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ["documents"],
    queryFn: () => documentsService.list({ limit: 50 }),
    retry: false,
  });

  const uploadMutation = useMutation({
    mutationFn: ({ file, title }: { file: File; title?: string }) =>
      documentsService.upload(file, title),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documents"] });
      addToast({ title: "Document uploaded", type: "success" });
      setTitle("");
      if (fileRef.current) fileRef.current.value = "";
    },
    onError: () => addToast({ title: "Upload failed", type: "error" }),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => documentsService.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documents"] });
      addToast({ title: "Document deleted", type: "success" });
    },
  });

  const handleUpload = () => {
    const file = fileRef.current?.files?.[0];
    if (!file) {
      addToast({ title: "Select a file first", type: "error" });
      return;
    }
    uploadMutation.mutate({ file, title: title || undefined });
  };

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h1 className="text-2xl font-bold">Documents</h1>
        <p className="text-muted-foreground text-sm mt-1">
          Upload runbooks, postmortems, and operational docs for RAG indexing
        </p>
      </div>

      <div className="ops-panel p-6">
        <h3 className="font-semibold mb-4 flex items-center gap-2">
          <Upload className="h-4 w-4 text-cyan-accent" />
          Upload Document
        </h3>
        <div className="flex flex-col sm:flex-row gap-3">
          <Input
            placeholder="Document title (optional)"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className="sm:flex-1"
          />
          <Input ref={fileRef} type="file" accept=".pdf,.md,.txt,.doc,.docx" className="sm:flex-1" />
          <Button variant="cyan" onClick={handleUpload} disabled={uploadMutation.isPending}>
            {uploadMutation.isPending ? <Spinner size="sm" /> : "Upload"}
          </Button>
        </div>
        <p className="text-xs text-muted-foreground mt-2">
          Supported: PDF, Markdown, TXT, DOC/DOCX
        </p>
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
                <TableHead>Status</TableHead>
                <TableHead>Size</TableHead>
                <TableHead>Chunks</TableHead>
                <TableHead>Uploaded</TableHead>
                <TableHead className="w-20" />
              </TableRow>
            </TableHeader>
            <TableBody>
              {(data?.items ?? []).length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} className="text-center text-muted-foreground py-12">
                    No documents uploaded yet
                  </TableCell>
                </TableRow>
              ) : (
                data?.items.map((doc) => (
                  <TableRow key={doc.id}>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <FileText className="h-4 w-4 text-cyan-accent shrink-0" />
                        <div>
                          <p className="font-medium">{doc.title}</p>
                          <p className="text-xs text-muted-foreground">{doc.filename}</p>
                        </div>
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge variant={statusVariant(doc.status)}>{doc.status}</Badge>
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {formatBytes(doc.size_bytes)}
                    </TableCell>
                    <TableCell className="font-mono text-sm">{doc.chunk_count}</TableCell>
                    <TableCell className="text-muted-foreground text-sm">
                      {formatDistanceToNow(new Date(doc.created_at), { addSuffix: true })}
                    </TableCell>
                    <TableCell>
                      <div className="flex gap-1">
                        {doc.status === "failed" && (
                          <Button variant="ghost" size="icon" title="Reindex">
                            <RefreshCw className="h-3 w-3" />
                          </Button>
                        )}
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => deleteMutation.mutate(doc.id)}
                        >
                          <Trash2 className="h-3 w-3 text-red-400" />
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
