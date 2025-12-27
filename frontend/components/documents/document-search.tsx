"use client";

import { useState } from "react";
import { documentsApi } from "@/lib/api/documents";
import { SearchResult } from "@/lib/types";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Search, Loader2, FileText, X } from "lucide-react";
import { cn } from "@/lib/utils";

interface DocumentSearchProps {
  onResultClick?: (result: SearchResult) => void;
}

export function DocumentSearch({ onResultClick }: DocumentSearchProps) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [searchTime, setSearchTime] = useState<number | null>(null);
  const [hasSearched, setHasSearched] = useState(false);

  const handleSearch = async (e?: React.FormEvent) => {
    e?.preventDefault();

    if (!query.trim()) {
      toast.error("Please enter a search query");
      return;
    }

    setIsSearching(true);
    setHasSearched(true);

    try {
      const response = await documentsApi.search({
        query: query.trim(),
        limit: 10,
        score_threshold: 0.5,
      });

      setResults(response.results);
      setSearchTime(response.search_time_ms);

      if (response.results.length === 0) {
        toast.info("No results found", {
          description: "Try a different search query",
        });
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "Search failed";
      toast.error(errorMessage);
      setResults([]);
      setSearchTime(null);
    } finally {
      setIsSearching(false);
    }
  };

  const handleClear = () => {
    setQuery("");
    setResults([]);
    setSearchTime(null);
    setHasSearched(false);
  };

  const getScoreColor = (score: number) => {
    if (score >= 0.8) return "text-green-600";
    if (score >= 0.6) return "text-yellow-600";
    return "text-orange-600";
  };

  return (
    <div className="space-y-4">
      {/* Search Input */}
      <Card>
        <CardHeader>
          <CardTitle>Semantic Search</CardTitle>
          <CardDescription>
            Search across all your documents using natural language
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSearch} className="flex gap-2">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="e.g., What is the company's revenue policy?"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                className="pl-10"
                disabled={isSearching}
              />
              {query && (
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className="absolute right-1 top-1/2 -translate-y-1/2 h-7 w-7"
                  onClick={handleClear}
                >
                  <X className="h-4 w-4" />
                </Button>
              )}
            </div>
            <Button type="submit" disabled={isSearching || !query.trim()}>
              {isSearching ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Searching...
                </>
              ) : (
                <>
                  <Search className="mr-2 h-4 w-4" />
                  Search
                </>
              )}
            </Button>
          </form>
        </CardContent>
      </Card>

      {/* Search Results */}
      {hasSearched && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <p className="text-sm text-muted-foreground">
              {results.length > 0 ? (
                <>
                  Found <span className="font-medium text-foreground">{results.length}</span> results
                  {searchTime && (
                    <span> in {searchTime.toFixed(0)}ms</span>
                  )}
                </>
              ) : (
                "No results found"
              )}
            </p>
          </div>

          {results.length > 0 && (
            <div className="space-y-3">
              {results.map((result) => (
                <Card
                  key={result.chunk_id}
                  className={cn(
                    "cursor-pointer transition-colors hover:bg-muted/50",
                    onResultClick && "hover:shadow-md"
                  )}
                  onClick={() => onResultClick?.(result)}
                >
                  <CardContent className="p-4">
                    <div className="space-y-2">
                      {/* Header */}
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex items-center gap-2 flex-1 min-w-0">
                          <FileText className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                          <span className="font-medium truncate" title={result.document_filename}>
                            {result.document_filename}
                          </span>
                          <Badge variant="outline" className="flex-shrink-0">
                            Chunk {result.chunk_index + 1}
                          </Badge>
                        </div>
                        <Badge
                          variant="secondary"
                          className={cn("flex-shrink-0", getScoreColor(result.score))}
                        >
                          {(result.score * 100).toFixed(0)}% match
                        </Badge>
                      </div>

                      {/* Content Preview */}
                      <p className="text-sm text-muted-foreground line-clamp-3">
                        {result.content}
                      </p>

                      {/* Metadata */}
                      {result.doc_metadata && Object.keys(result.doc_metadata).length > 0 && (
                        <div className="flex flex-wrap gap-2 pt-2">
                          {Object.entries(result.doc_metadata).slice(0, 3).map(([key, value]) => (
                            <Badge key={key} variant="outline" className="text-xs">
                              {key}: {String(value)}
                            </Badge>
                          ))}
                        </div>
                      )}
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
