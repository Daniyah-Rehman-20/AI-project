"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Search, Sparkles, BookOpen } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Spinner } from "@/components/ui/spinner";
import { searchService } from "@/services/search";
import type { SearchResponse } from "@/types";

export default function KnowledgePage() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResponse | null>(null);

  const searchMutation = useMutation({
    mutationFn: (q: string) => searchService.semantic({ query: q, limit: 10 }),
    onSuccess: (data) => setResults(data),
  });

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    searchMutation.mutate(query.trim());
  };

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="relative overflow-hidden rounded-xl border border-border/60 bg-gradient-to-br from-steel-900/80 via-card/60 to-steel-950/80 p-6 md:p-8">
        <div className="absolute inset-0 bg-grid-pattern bg-grid opacity-[0.03]" />
        <div className="relative z-10 max-w-2xl">
          <div className="flex items-center gap-2 mb-3">
            <BookOpen className="h-5 w-5 text-cyan-accent" />
            <span className="text-xs uppercase tracking-[0.2em] text-cyan-accent font-medium">
              Knowledge Base
            </span>
          </div>
          <h1 className="text-2xl md:text-3xl font-bold mb-2">Semantic Search</h1>
          <p className="text-muted-foreground mb-6">
            Search across indexed runbooks, postmortems, and operational documentation using natural language.
          </p>

          <form onSubmit={handleSearch} className="flex gap-2">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="How do I restart the payment service safely?"
                className="pl-9 h-12 text-base"
              />
            </div>
            <Button type="submit" variant="cyan" className="h-12 px-6" disabled={searchMutation.isPending}>
              {searchMutation.isPending ? <Spinner size="sm" /> : <Sparkles className="h-4 w-4" />}
              Search
            </Button>
          </form>
        </div>
      </div>

      {searchMutation.isError && (
        <div className="ops-panel p-4 border-red-500/30 text-red-400 text-sm">
          Search failed. Ensure the knowledge base API is available.
        </div>
      )}

      {results && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <p className="text-sm text-muted-foreground">
              {results.total} results for &ldquo;{results.query}&rdquo;
              <span className="font-mono ml-2">({results.latency_ms}ms)</span>
            </p>
          </div>

          {results.results.length === 0 ? (
            <div className="ops-panel p-8 text-center text-muted-foreground">
              No matching documents found. Try rephrasing your query.
            </div>
          ) : (
            results.results.map((result) => (
              <div
                key={result.id}
                className="ops-panel p-5 transition-all duration-200 hover:border-cyan-accent/30"
              >
                <div className="flex items-start justify-between gap-4 mb-2">
                  <div>
                    <h3 className="font-medium">{result.document_title}</h3>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      Chunk {result.chunk_index + 1}
                    </p>
                  </div>
                  <Badge variant="info">{(result.score * 100).toFixed(0)}% match</Badge>
                </div>
                <p className="text-sm text-muted-foreground leading-relaxed">{result.content}</p>
              </div>
            ))
          )}
        </div>
      )}

      {!results && !searchMutation.isPending && (
        <div className="grid sm:grid-cols-3 gap-4">
          {[
            "Database failover procedure",
            "Kubernetes pod crash loop debugging",
            "Payment gateway timeout escalation",
          ].map((suggestion) => (
            <button
              key={suggestion}
              onClick={() => {
                setQuery(suggestion);
                searchMutation.mutate(suggestion);
              }}
              className="ops-panel p-4 text-left text-sm text-muted-foreground hover:text-foreground hover:border-cyan-accent/30 transition-all duration-200"
            >
              <Sparkles className="h-3 w-3 text-cyan-accent mb-2" />
              {suggestion}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
