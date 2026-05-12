import { useEffect, useState, type FormEvent } from "react";
import { Header } from "@/components/Header";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { fetchHistory, type HistoryFilters, type HistoryItem } from "@/services/api";

const PAGE_SIZE = 10;

function formatTimestamp(value: string | undefined) {
  if (!value) {
    return "-";
  }

  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleString();
}

export function HistoryPage() {
  const [items, setItems] = useState<HistoryItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchInput, setSearchInput] = useState("");
  const [filters, setFilters] = useState<HistoryFilters>({
    limit: PAGE_SIZE,
    offset: 0,
    search: "",
    result: "",
    sort: "newest",
  });

  async function loadHistory(nextFilters: HistoryFilters = filters) {
    setLoading(true);
    setError(null);

    try {
      const payload = await fetchHistory(nextFilters);
      setItems(payload.items);
      setTotal(payload.total);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Failed to load scan history.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadHistory(filters);
  }, [filters]);

  function onApplyFilters(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFilters((current) => ({
      ...current,
      offset: 0,
      search: searchInput.trim(),
    }));
  }

  const showingFrom = total === 0 ? 0 : filters.offset + 1;
  const showingTo = Math.min(filters.offset + items.length, total);
  const canGoPrevious = filters.offset > 0 && !loading;
  const canGoNext = filters.offset + filters.limit < total && !loading;

  return (
    <div className="min-h-screen bg-background">
      <Header />
      <main className="mx-auto max-w-6xl px-6 py-12">
        <ProtectedRoute>
          <div className="space-y-6">
            <div className="flex flex-wrap items-end justify-between gap-4">
              <div>
                <h1 className="text-3xl font-bold tracking-tight">History</h1>
                <p className="mt-2 text-sm text-muted-foreground">
                  Review the URLs you scanned and the Perdicts returned by the backend.
                </p>
              </div>
              <Button variant="outline" onClick={() => void loadHistory()} disabled={loading}>
                {loading ? "Refreshing..." : "Refresh"}
              </Button>
            </div>

            <Card>
              <CardHeader>
                <CardTitle>Filters</CardTitle>
                <CardDescription>Search, filter, and sort your scan history.</CardDescription>
              </CardHeader>
              <CardContent>
                <form onSubmit={onApplyFilters} className="grid gap-4 md:grid-cols-4">
                  <Input
                    type="text"
                    placeholder="Search scanned URL"
                    value={searchInput}
                    onChange={(event) => setSearchInput(event.target.value)}
                    className="md:col-span-2"
                  />
                  <select
                    value={filters.result}
                    onChange={(event) =>
                      setFilters((current) => ({
                        ...current,
                        offset: 0,
                        result: event.target.value as HistoryFilters["result"],
                      }))
                    }
                    className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                  >
                    <option value="">All results</option>
                    <option value="phishing">Phishing</option>
                    <option value="legit">Legit</option>
                  </select>
                  <select
                    value={filters.sort}
                    onChange={(event) =>
                      setFilters((current) => ({
                        ...current,
                        offset: 0,
                        sort: event.target.value as HistoryFilters["sort"],
                      }))
                    }
                    className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                  >
                    <option value="newest">Newest first</option>
                    <option value="oldest">Oldest first</option>
                    <option value="confidence_desc">Confidence high to low</option>
                    <option value="confidence_asc">Confidence low to high</option>
                  </select>
                  <div className="md:col-span-4 flex flex-wrap justify-end gap-2">
                    <Button
                      type="button"
                      variant="ghost"
                      onClick={() => {
                        setSearchInput("");
                        setFilters({
                          limit: PAGE_SIZE,
                          offset: 0,
                          search: "",
                          result: "",
                          sort: "newest",
                        });
                      }}
                    >
                      Reset
                    </Button>
                    <Button type="submit">Apply</Button>
                  </div>
                </form>
              </CardContent>
            </Card>

            {error ? (
              <Card className="border-destructive/40">
                <CardContent className="p-6">
                  <p className="text-sm text-destructive">{error}</p>
                </CardContent>
              </Card>
            ) : null}

            <Card>
              <CardHeader>
                <CardTitle>Your scans</CardTitle>
                <CardDescription>
                  {total > 0
                    ? `Showing ${showingFrom}-${showingTo} of ${total} scans.`
                    : "Your scan history will appear here after you submit URLs."}
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>URL</TableHead>
                      <TableHead>Perdict</TableHead>
                      <TableHead>Confidence</TableHead>
                      <TableHead>Scanned at</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {items.length > 0 ? (
                      items.map((item) => (
                        <TableRow key={item.id ?? `${item.url}-${item.created_at}`}>
                          <TableCell className="max-w-md break-all">{item.url}</TableCell>
                          <TableCell className="capitalize">{item.result}</TableCell>
                          <TableCell>
                            {typeof item.confidence === "number"
                              ? `${(item.confidence * 100).toFixed(2)}%`
                              : "-"}
                          </TableCell>
                          <TableCell>{formatTimestamp(item.created_at)}</TableCell>
                        </TableRow>
                      ))
                    ) : (
                      <TableRow>
                        <TableCell colSpan={4} className="text-center text-muted-foreground">
                          {loading ? "Loading history..." : "No scans found."}
                        </TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>

                <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
                  <p className="text-sm text-muted-foreground">
                    Page {Math.floor(filters.offset / filters.limit) + 1}
                  </p>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      onClick={() =>
                        setFilters((current) => ({
                          ...current,
                          offset: Math.max(0, current.offset - current.limit),
                        }))
                      }
                      disabled={!canGoPrevious}
                    >
                      Previous
                    </Button>
                    <Button
                      variant="outline"
                      onClick={() =>
                        setFilters((current) => ({
                          ...current,
                          offset: current.offset + current.limit,
                        }))
                      }
                      disabled={!canGoNext}
                    >
                      Next
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </ProtectedRoute>
      </main>
    </div>
  );
}
