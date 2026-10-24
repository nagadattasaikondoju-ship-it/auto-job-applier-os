"use client";

import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { ListChecks, Search } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { Badge, Button, ButtonLink, Card, EmptyState, ErrorState, Input, PageHeader, SkeletonList, Tabs } from "@/components/app/ui";
import { api } from "@/lib/api/endpoints";
import { formatDate, formatSalary, statusLabel, statusTone } from "@/lib/format";

const FILTERS = [
  { value: "", label: "All" },
  { value: "ready_for_review", label: "To review" },
  { value: "needs_user_action", label: "Needs action" },
  { value: "submitted", label: "Applied" },
  { value: "interview", label: "Interview" },
  { value: "offer", label: "Offer" },
  { value: "rejected", label: "Rejected" },
  { value: "withdrawn", label: "Withdrawn" },
] as const;

type Filter = (typeof FILTERS)[number]["value"];

const PAGE_SIZE = 20;

export default function ApplicationsPage() {
  const [status, setStatus] = useState<Filter>("");
  const [search, setSearch] = useState("");
  const [debounced, setDebounced] = useState("");
  const [page, setPage] = useState(1);

  useEffect(() => {
    const t = setTimeout(() => {
      setDebounced(search.trim());
      setPage(1);
    }, 300);
    return () => clearTimeout(t);
  }, [search]);

  const changeStatus = (s: Filter) => {
    setStatus(s);
    setPage(1);
  };

  const list = useQuery({
    queryKey: ["applications", { status, search: debounced, page }],
    queryFn: () => api.applications.list({ status: status || undefined, search: debounced || undefined, page, page_size: PAGE_SIZE }),
    placeholderData: keepPreviousData,
  });

  const totalPages = list.data ? Math.max(1, Math.ceil(list.data.total / PAGE_SIZE)) : 1;

  return (
    <>
      <PageHeader title="Applications" description="Every application, its status and what happened, in one place." />

      <div className="mb-5 flex flex-col gap-3">
        <div className="relative max-w-md">
          <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-app-subtle" aria-hidden="true" />
          <Input
            aria-label="Search by job title or company"
            placeholder="Search by job title or company"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
          />
        </div>
        <Tabs label="Filter by status" value={status} onChange={changeStatus} items={FILTERS.map((f) => ({ value: f.value, label: f.label }))} />
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
            title={status || debounced ? "Nothing matches this filter" : "No applications yet"}
            description={
              status || debounced
                ? "Try another status or search."
                : "Open a job and choose “Prepare application” to start tracking it here."
            }
            action={!status && !debounced && <ButtonLink href="/jobs">Browse jobs</ButtonLink>}
          />
        </Card>
      ) : (
        <Card className="overflow-hidden">
          {/* Table on wide screens */}
          <table className="hidden md:table w-full text-left">
            <caption className="sr-only">Your applications</caption>
            <thead className="border-b border-app-border bg-app-bg text-xs text-app-muted">
              <tr>
                <th scope="col" className="px-5 py-3 font-medium">Role</th>
                <th scope="col" className="px-5 py-3 font-medium">Status</th>
                <th scope="col" className="px-5 py-3 font-medium">Salary</th>
                <th scope="col" className="px-5 py-3 font-medium">Channel</th>
                <th scope="col" className="px-5 py-3 font-medium">Applied</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-app-border">
              {list.data.items.map((a) => (
                <tr key={a.id} className="hover:bg-app-bg">
                  <td className="px-5 py-3.5">
                    <Link href={`/applications/${a.id}`} className="font-medium text-app-ink hover:underline underline-offset-4">
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
                  <td className="px-5 py-3.5 text-app-ink-2">{formatSalary(a.salary_min_lpa, a.salary_max_lpa) ?? "—"}</td>
                  <td className="px-5 py-3.5 text-app-ink-2 capitalize">{a.channel}</td>
                  <td className="px-5 py-3.5 text-app-ink-2">{formatDate(a.submitted_at ?? a.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>

          {/* Cards on small screens */}
          <ul className="md:hidden divide-y divide-app-border">
            {list.data.items.map((a) => (
              <li key={a.id}>
                <Link href={`/applications/${a.id}`} className="block px-4 py-4 hover:bg-app-bg">
                  <span className="block font-medium">{a.job_title}</span>
                  <span className="block text-app-muted">{a.company_name}</span>
                  <span className="mt-2 flex items-center gap-2">
                    <Badge tone={statusTone(a.status)}>{statusLabel(a.status)}</Badge>
                    <span className="text-xs text-app-subtle">{formatDate(a.submitted_at ?? a.created_at)}</span>
                  </span>
                </Link>
              </li>
            ))}
          </ul>

          {totalPages > 1 && (
            <div className="flex items-center justify-between border-t border-app-border px-5 py-3">
              <p className="text-xs text-app-muted">
                Page {page} of {totalPages} · {list.data.total} applications
              </p>
              <div className="flex gap-2">
                <Button variant="secondary" size="sm" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
                  Previous
                </Button>
                <Button variant="secondary" size="sm" disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)}>
                  Next
                </Button>
              </div>
            </div>
          )}
        </Card>
      )}
    </>
  );
}
