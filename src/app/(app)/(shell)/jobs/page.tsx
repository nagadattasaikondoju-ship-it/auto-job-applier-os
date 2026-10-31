"use client";

import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link2, Search, Sparkles } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";
import { toast } from "sonner";
import { JobCard } from "@/components/app/job-card";
import {
  Button,
  Card,
  Dialog,
  EmptyState,
  ErrorState,
  Field,
  Input,
  PageHeader,
  Select,
  SkeletonList,
  Tabs,
  Textarea,
} from "@/components/app/ui";
import { api } from "@/lib/api/endpoints";

const SCORE_FILTERS = [
  { value: "", label: "Any fit score" },
  { value: "60", label: "60+ fit" },
  { value: "70", label: "70+ fit" },
  { value: "80", label: "80+ fit" },
];

export default function JobsPage() {
  const queryClient = useQueryClient();
  const [minScore, setMinScore] = useState("");
  const [search, setSearch] = useState("");
  const [importOpen, setImportOpen] = useState(false);
  const [tab, setTab] = useState<"all" | "saved">("all");
  const saved = useQuery({
    queryKey: ["matches", { status: "saved" }],
    queryFn: () => api.matches.list({ status: "saved", limit: 100 }),
  });
  const savedIds = useMemo(() => new Set((saved.data?.items ?? []).map((m) => m.job_id)), [saved.data]);

  const toggleSave = useMutation({
    mutationFn: ({ id, on }: { id: string; on: boolean }) => api.jobs.save(id, on),
    onSuccess: (_, v) => {
      toast.success(v.on ? "Saved." : "Removed from saved jobs.");
      void queryClient.invalidateQueries({ queryKey: ["matches"] });
    },
    onError: (e) => toast.error(e.message),
  });

  const discover = useMutation({
    mutationFn: api.jobs.discover,
    onSuccess: (r) => {
      toast.success(r.message);
      setTimeout(() => void queryClient.invalidateQueries({ queryKey: ["jobs"] }), 15_000);
    },
    onError: (e) => toast.error(e.message),
  });

  const feed = useInfiniteQuery({
    queryKey: ["jobs", "feed", minScore],
    queryFn: ({ pageParam }) =>
      api.jobs.feed({ cursor: pageParam, limit: 20, min_match_score: minScore ? Number(minScore) : null, matched_only: true }),
    initialPageParam: null as string | null,
    getNextPageParam: (last) => (last.items.length === 20 ? last.next_cursor : null),
  });

  const refresh = useMutation({
    mutationFn: api.matches.refresh,
    onSuccess: (r) => {
      toast.success(r.new_matches_count ? `${r.new_matches_count} new matches found.` : "No new matches right now.");
      void queryClient.invalidateQueries({ queryKey: ["jobs"] });
      void queryClient.invalidateQueries({ queryKey: ["matches"] });
    },
    onError: (e) => toast.error(e.message),
  });

  const jobs = useMemo(() => {
    const all = (feed.data?.pages.flatMap((p) => p.items) ?? []).filter(
      (j) => tab === "all" || savedIds.has(j.id)
    );
    const q = search.trim().toLowerCase();
    if (!q) return all;
    return all.filter((j) => `${j.title} ${j.company} ${j.location ?? ""}`.toLowerCase().includes(q));
  }, [feed.data, search, tab, savedIds]);

  return (
    <>
      <PageHeader
        title="Jobs"
        description="Jobs matched to your profile, scored on how well you fit."
        actions={
          <>
            <Button variant="secondary" onClick={() => setImportOpen(true)}>
              <Link2 className="size-4" aria-hidden="true" />
              Import a job
            </Button>
            <Button variant="secondary" onClick={() => refresh.mutate()} loading={refresh.isPending}>
              <Sparkles className="size-4" aria-hidden="true" />
              Re-score matches
            </Button>
            <Button onClick={() => discover.mutate()} loading={discover.isPending}>
              <Search className="size-4" aria-hidden="true" />
              Find jobs now
            </Button>
          </>
        }
      />

      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <Tabs
          label="Jobs list"
          value={tab}
          onChange={setTab}
          items={[
            { value: "all", label: "Matched for you" },
            { value: "saved", label: "Saved", count: savedIds.size },
          ]}
        />
        <Link href="/preferences" className="text-sm text-app-ink-2 underline-offset-4 hover:underline">
          Edit what you&apos;re looking for
        </Link>
      </div>

      <div className="mb-5 flex flex-col gap-3 sm:flex-row">
        <div className="relative flex-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-app-subtle" aria-hidden="true" />
          <Input
            aria-label="Filter jobs by title, company or city"
            placeholder="Filter by title, company or city"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
          />
        </div>
        <Select aria-label="Minimum fit score" value={minScore} onChange={(e) => setMinScore(e.target.value)} className="sm:w-44">
          {SCORE_FILTERS.map((f) => (
            <option key={f.value} value={f.value}>
              {f.label}
            </option>
          ))}
        </Select>
      </div>

      {feed.isPending ? (
        <SkeletonList rows={5} />
      ) : feed.isError ? (
        <Card>
          <ErrorState error={feed.error} onRetry={() => feed.refetch()} />
        </Card>
      ) : jobs.length === 0 ? (
        <Card>
          <EmptyState
            title={tab === "saved" ? "No saved jobs" : search ? "No jobs match that filter" : "No matches yet"}
            description={
              search
                ? "Try a different search, or lower the minimum fit score."
                : tab === "saved"
                  ? "Use the bookmark on any job to save it for later."
                  : "Only jobs that fit your roles, cities and experience show here. Click “Find jobs now” to search job boards and career pages; new matches appear within a few minutes. You can also import a job you found."
            }
            action={
              !search && tab === "all" && (
                <Button onClick={() => discover.mutate()} loading={discover.isPending}>
                  Find jobs now
                </Button>
              )
            }
          />
        </Card>
      ) : (
        <>
          <ul className="flex flex-col gap-3">
            {jobs.map((j) => (
              <li key={j.id}>
                <JobCard
                  job={{
                    id: j.id,
                    title: j.title,
                    company: j.company,
                    location: j.location,
                    remote_mode: j.remote_mode,
                    salary_min_lpa: j.salary_min_lpa,
                    salary_max_lpa: j.salary_max_lpa,
                    posted_at: j.posted_at,
                    score: j.match?.score,
                    decision: j.match?.decision,
                    fit_reasons: j.match?.fit_reasons,
                    saved: savedIds.has(j.id),
                  }}
                  onToggleSave={(on) => toggleSave.mutate({ id: j.id, on })}
                />
              </li>
            ))}
          </ul>
          {feed.hasNextPage && (
            <div className="mt-6 flex justify-center">
              <Button variant="secondary" onClick={() => feed.fetchNextPage()} loading={feed.isFetchingNextPage}>
                Load more
              </Button>
            </div>
          )}
        </>
      )}

      <ImportJobDialog open={importOpen} onClose={() => setImportOpen(false)} />
    </>
  );
}

function ImportJobDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [url, setUrl] = useState("");
  const [text, setText] = useState("");

  const valid = /^https?:\/\/\S+\.\S+/.test(url.trim());

  const importJob = useMutation({
    mutationFn: () => api.jobs.import(url.trim(), text),
    onSuccess: (r) => {
      toast.success(r.is_new ? `Imported ${r.title} at ${r.company}.` : "You already have this job. Opening it.");
      void queryClient.invalidateQueries({ queryKey: ["jobs"] });
      onClose();
      setUrl("");
      setText("");
      router.push(`/jobs/${r.job_id}`);
    },
    onError: (e) => toast.error(e.message),
  });

  return (
    <Dialog
      open={open}
      onClose={onClose}
      title="Import a job"
      description="Paste a link from Greenhouse, Lever, Ashby or a company careers page."
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={() => importJob.mutate()} loading={importJob.isPending} disabled={!valid}>
            Import job
          </Button>
        </>
      }
    >
      <form
        className="flex flex-col gap-4"
        onSubmit={(e) => {
          e.preventDefault();
          if (valid) importJob.mutate();
        }}
      >
        <Field label="Job link" htmlFor="job-url" error={url && !valid ? "Enter a full link starting with https://" : undefined}>
          <Input
            id="job-url"
            type="url"
            placeholder="https://boards.greenhouse.io/company/jobs/123"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            aria-invalid={Boolean(url && !valid)}
          />
        </Field>
        <Field label="Job description (optional)" htmlFor="job-text" hint="Paste it if the page needs a login or doesn't load.">
          <Textarea id="job-text" value={text} onChange={(e) => setText(e.target.value)} className="min-h-28" />
        </Field>
      </form>
    </Dialog>
  );
}
