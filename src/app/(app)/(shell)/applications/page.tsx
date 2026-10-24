"use client";

import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Download, KanbanSquare, ListChecks, Search, Table2 } from "lucide-react";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { Badge, Button, ButtonLink, Card, EmptyState, ErrorState, Input, PageHeader, SkeletonList, Tabs } from "@/components/app/ui";
import { api } from "@/lib/api/endpoints";
import type { ApplicationListItem, ApplicationStatus } from "@/lib/api/types";
import { formatDate, formatSalary, statusLabel, statusTone, timeAgo } from "@/lib/format";
import { cn } from "@/lib/utils";

type View = "board" | "table";

const COLUMNS: { id: string; title: string; statuses: ApplicationStatus[]; dropStatus?: ApplicationStatus }[] = [
  { id: "review", title: "To review", statuses: ["draft", "preparing", "ready_for_review", "needs_user_action"] },
  { id: "approved", title: "Approved", statuses: ["approved", "submitting"] },
  { id: "applied", title: "Applied", statuses: ["submitted"], dropStatus: "submitted" },
  { id: "interview", title: "Interview", statuses: ["interview"], dropStatus: "interview" },
  { id: "offer", title: "Offer", statuses: ["offer"], dropStatus: "offer" },
  { id: "closed", title: "Closed", statuses: ["rejected", "withdrawn", "ghosted", "failed"], dropStatus: "rejected" },
];

const MOVE_TO: ApplicationStatus[] = ["submitted", "interview", "offer", "rejected", "ghosted", "withdrawn"];

export default function ApplicationsPage() {
  const [view, setView] = useState<View>("board");
  const [search, setSearch] = useState("");
  const [debounced, setDebounced] = useState("");

  useEffect(() => {
    const t = setTimeout(() => setDebounced(search.trim()), 300);
    return () => clearTimeout(t);
  }, [search]);

  const list = useQuery({
    queryKey: ["applications", { search: debounced, all: true }],
    queryFn: () => api.applications.list({ search: debounced || undefined, page: 1, page_size: 100 }),
    placeholderData: keepPreviousData,
  });

  const exportCsv = useMutation({
    mutationFn: api.applications.exportCsv,
    onError: (e) => toast.error(e.message),
  });

  return (
    <>
      <PageHeader
        title="Applications"
        description="Every application, the resume version used, and where it stands."
        actions={
          <>
            <Tabs
              label="View"
              value={view}
              onChange={setView}
              items={[
                { value: "board", label: "Board" },
                { value: "table", label: "Table" },
              ]}
            />
            <Button variant="secondary" onClick={() => exportCsv.mutate()} loading={exportCsv.isPending}>
              <Download className="size-4" aria-hidden="true" />
              Export CSV
            </Button>
          </>
        }
      />

      <div className="relative mb-5 max-w-md">
        <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-app-subtle" aria-hidden="true" />
        <Input
          aria-label="Search by job title or company"
          placeholder="Search by job title or company"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="pl-9"
        />
      </div>

      {list.isPending ? (
        <SkeletonList rows={6} />
      ) : list.isError ? (
        <Card>
          <ErrorState error={list.error} onRetry={() => list.refetch()} />
        </Card>
      ) : list.data.items.length === 0 ? (
        <Card>
          <EmptyState
            icon={ListChecks}
            title={debounced ? "Nothing matches your search" : "No applications yet"}
            description={debounced ? "Try another search." : "Turn on auto-apply, or open a job and choose “Prepare application”."}
            action={!debounced && <ButtonLink href="/auto-apply">Set up auto-apply</ButtonLink>}
          />
        </Card>
      ) : view === "board" ? (
        <Board items={list.data.items} />
      ) : (
        <TableView items={list.data.items} />
      )}
      {list.data && list.data.total > list.data.items.length && (
        <p className="mt-3 text-xs text-app-muted">
          Showing the {list.data.items.length} most recent of {list.data.total}. Export CSV for the full list.
        </p>
      )}
    </>
  );
}

function useMove() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, status }: { id: string; status: ApplicationStatus }) => api.applications.updateStatus(id, status),
    onSuccess: (_, v) => {
      toast.success(`Moved to ${statusLabel(v.status)}.`);
      void queryClient.invalidateQueries({ queryKey: ["applications"] });
      void queryClient.invalidateQueries({ queryKey: ["analytics"] });
      void queryClient.invalidateQueries({ queryKey: ["follow-ups"] });
    },
    onError: (e) => toast.error(e.message),
  });
}

function Board({ items }: { items: ApplicationListItem[] }) {
  const move = useMove();
  const [dragOver, setDragOver] = useState<string | null>(null);
  const columns = useMemo(
    () => COLUMNS.map((c) => ({ ...c, items: items.filter((i) => c.statuses.includes(i.status)) })),
    [items]
  );

  return (
    <div className="-mx-4 overflow-x-auto px-4 pb-4 sm:mx-0 sm:px-0">
      <div className="grid min-w-[1080px] grid-cols-6 gap-3">
        {columns.map((col) => (
          <section
            key={col.id}
            aria-label={`${col.title}, ${col.items.length} applications`}
            onDragOver={(e) => {
              if (!col.dropStatus) return;
              e.preventDefault();
              setDragOver(col.id);
            }}
            onDragLeave={() => setDragOver(null)}
            onDrop={(e) => {
              setDragOver(null);
              const id = e.dataTransfer.getData("text/plain");
              const item = items.find((i) => i.id === id);
              if (col.dropStatus && item && !col.statuses.includes(item.status)) move.mutate({ id, status: col.dropStatus });
            }}
            className={cn(
              "flex min-h-64 flex-col gap-2 rounded-app-xl bg-app-panel/60 p-2 transition-colors",
              dragOver === col.id && "bg-app-accent/10 ring-2 ring-app-accent/40"
            )}
          >
            <h2 className="flex items-center justify-between px-2 pt-1 text-sm font-medium">
              {col.title}
              <span className="font-mono text-xs text-app-muted">{col.items.length}</span>
            </h2>
            {col.items.map((a) => (
              <article
                key={a.id}
                draggable
                onDragStart={(e) => e.dataTransfer.setData("text/plain", a.id)}
                className="cursor-grab rounded-app-lg border border-app-border bg-app-card p-3 active:cursor-grabbing"
              >
                <Link href={`/applications/${a.id}`} className="block font-medium leading-snug hover:underline underline-offset-4">
                  {a.job_title}
                </Link>
                <p className="mt-0.5 text-xs text-app-muted">{a.company_name}</p>
                <div className="mt-2 flex flex-wrap items-center gap-1">
                  {a.match_score != null && a.match_score > 0 && <Badge tone="success">{a.match_score} fit</Badge>}
                  {col.id === "review" || col.id === "closed" ? <Badge tone={statusTone(a.status)}>{statusLabel(a.status)}</Badge> : null}
                </div>
                <p className="mt-2 text-xs text-app-subtle">
                  {a.submitted_at ? `Applied ${formatDate(a.submitted_at)}` : `Updated ${timeAgo(a.updated_at ?? a.created_at)}`}
                </p>
                {a.follow_up_at && <p className="text-xs text-app-ink-2">Follow up {formatDate(a.follow_up_at)}</p>}
                {col.id !== "review" && col.id !== "approved" && (
                  <label className="mt-2 block">
                    <span className="sr-only">Move {a.job_title} to</span>
                    <select
                      value=""
                      onChange={(e) => e.target.value && move.mutate({ id: a.id, status: e.target.value as ApplicationStatus })}
                      className="h-7 w-full rounded-app-sm border border-app-border bg-app-bg px-1.5 text-xs text-app-ink-2"
                    >
                      <option value="">Move to…</option>
                      {MOVE_TO.filter((s) => s !== a.status).map((s) => (
                        <option key={s} value={s}>
                          {statusLabel(s)}
                        </option>
                      ))}
                    </select>
                  </label>
                )}
                {col.id === "review" && (
                  <Link href="/review" className="mt-2 inline-block text-xs text-app-ink underline underline-offset-2">
                    Review now
                  </Link>
                )}
              </article>
            ))}
            {col.items.length === 0 && (
              <p className="px-2 py-4 text-center text-xs text-app-subtle">
                {col.dropStatus ? "Drag applications here" : "Empty"}
              </p>
            )}
          </section>
        ))}
      </div>
      <p className="mt-2 flex items-center gap-1.5 text-xs text-app-muted">
        <KanbanSquare className="size-3.5" aria-hidden="true" />
        Drag cards between Applied, Interview, Offer and Closed, or use “Move to”.
      </p>
    </div>
  );
}

function TableView({ items }: { items: ApplicationListItem[] }) {
  return (
    <Card className="overflow-x-auto">
      <table className="w-full min-w-[760px] text-left">
        <caption className="sr-only">Your applications</caption>
        <thead className="border-b border-app-border bg-app-bg text-xs text-app-muted">
          <tr>
            <th scope="col" className="px-5 py-3 font-medium">Role</th>
            <th scope="col" className="px-5 py-3 font-medium">Status</th>
            <th scope="col" className="px-5 py-3 font-medium">Fit</th>
            <th scope="col" className="px-5 py-3 font-medium">Salary</th>
            <th scope="col" className="px-5 py-3 font-medium">Source</th>
            <th scope="col" className="px-5 py-3 font-medium">Applied</th>
            <th scope="col" className="px-5 py-3 font-medium">Follow up</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-app-border">
          {items.map((a) => (
            <tr key={a.id} className="hover:bg-app-bg">
              <td className="px-5 py-3.5">
                <Link href={`/applications/${a.id}`} className="font-medium hover:underline underline-offset-4">
                  {a.job_title}
                </Link>
                <span className="block text-app-muted">
                  {a.company_name}
                  {a.location && ` · ${a.location}`}
                </span>
              </td>
              <td className="px-5 py-3.5">
                <Badge tone={statusTone(a.status)}>{statusLabel(a.status)}</Badge>
              </td>
              <td className="px-5 py-3.5 font-mono">{a.match_score || "—"}</td>
              <td className="px-5 py-3.5 text-app-ink-2">{formatSalary(a.salary_min_lpa, a.salary_max_lpa) ?? "—"}</td>
              <td className="px-5 py-3.5 text-app-ink-2 capitalize">{a.source ?? a.channel}</td>
              <td className="px-5 py-3.5 text-app-ink-2">{formatDate(a.submitted_at)}</td>
              <td className="px-5 py-3.5 text-app-ink-2">{formatDate(a.follow_up_at)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="flex items-center gap-1.5 px-5 py-3 text-xs text-app-muted">
        <Table2 className="size-3.5" aria-hidden="true" />
        Open an application to add notes, interview details or rejection reasons.
      </p>
    </Card>
  );
}
