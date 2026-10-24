"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, Pause, Play, RotateCcw, Search, Zap } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { toast } from "sonner";
import { Badge, Button, ButtonLink, Card, CardHeader, ErrorState, PageHeader, ProgressBar, Spinner } from "@/components/app/ui";
import { ApiError } from "@/lib/api/client";
import { api } from "@/lib/api/endpoints";
import type { ApplyMode, AutopilotState } from "@/lib/api/types";
import { statusLabel, statusTone, timeAgo } from "@/lib/format";
import { cn } from "@/lib/utils";

export default function AutoApplyPage() {
  const state = useQuery({ queryKey: ["autopilot"], queryFn: api.autopilot.get, refetchInterval: 30_000 });
  if (state.isPending) return <Spinner label="Loading auto-apply" />;
  if (state.isError) return <ErrorState error={state.error} onRetry={() => state.refetch()} />;
  return <AutoApply data={state.data} />;
}

const MODES: { value: ApplyMode; label: string; description: string }[] = [
  {
    value: "review",
    label: "Review first",
    description: "Applyon prepares each application and waits for your approval in the Review queue.",
  },
  {
    value: "hybrid",
    label: "Hybrid",
    description: "Very high-fit jobs (90+, no open questions) are submitted automatically. Everything else waits for you.",
  },
];

function AutoApply({ data }: { data: AutopilotState }) {
  const queryClient = useQueryClient();
  const c = data.campaign;
  const [mode, setMode] = useState<ApplyMode>(c?.mode ?? "review");
  const [limit, setLimit] = useState(Math.min(c?.daily_limit ?? 10, data.readiness.review.plan_daily_limit));
  const [blockers, setBlockers] = useState<string[]>([]);
  const ready = data.readiness[mode];

  const refresh = () => {
    void queryClient.invalidateQueries({ queryKey: ["autopilot"] });
    void queryClient.invalidateQueries({ queryKey: ["review-queue"] });
    void queryClient.invalidateQueries({ queryKey: ["applications"] });
  };
  const onError = (e: Error) => {
    if (e instanceof ApiError && e.code === "AUTOPILOT_NOT_READY") {
      setBlockers(Array.isArray(e.details) ? (e.details as string[]) : [e.message]);
    } else toast.error(e.message);
  };

  const start = useMutation({
    mutationFn: () => api.autopilot.start({ mode, daily_limit: limit }),
    onSuccess: (r) => {
      setBlockers([]);
      toast.success(
        r.first_batch.prepared
          ? `Auto-apply is on. ${r.first_batch.prepared} application(s) prepared.`
          : `Auto-apply is on. ${r.first_batch.stopped_reason ?? "Applications will be prepared as matches come in."}`
      );
      refresh();
    },
    onError,
  });
  const pause = useMutation({ mutationFn: api.autopilot.pause, onSuccess: () => (toast.success("Auto-apply paused."), refresh()), onError });
  const resume = useMutation({ mutationFn: api.autopilot.resume, onSuccess: () => (toast.success("Auto-apply resumed."), refresh()), onError });
  const runNow = useMutation({
    mutationFn: api.autopilot.runNow,
    onSuccess: (r) => {
      toast[r.prepared ? "success" : "info"](
        r.prepared ? `${r.prepared} application(s) prepared for review.` : r.stopped_reason ?? "Nothing new to prepare."
      );
      refresh();
    },
    onError,
  });
  const discover = useMutation({
    mutationFn: api.jobs.discover,
    onSuccess: (r) => toast.success(r.message),
    onError: (e) => toast.error(e.message),
  });
  const retry = useMutation({
    mutationFn: (id: string) => api.autopilot.retry(id),
    onSuccess: () => (toast.success("Moved back to your review queue."), refresh()),
    onError: (e) => toast.error(e.message),
  });

  const active = c?.status === "active";
  const changed = c && (c.mode !== mode || c.daily_limit !== limit);
  const prepared = data.today.prepared;
  const by = data.today.by_status;

  return (
    <>
      <PageHeader
        title="Auto-apply"
        description="Applyon finds jobs above your match threshold, tailors your documents, fills the forms and queues each application."
        actions={
          <>
            <Button variant="secondary" onClick={() => discover.mutate()} loading={discover.isPending}>
              <Search className="size-4" aria-hidden="true" />
              Find jobs now
            </Button>
            {c && (
              <Button variant="secondary" onClick={() => runNow.mutate()} loading={runNow.isPending} disabled={!active}>
                <Zap className="size-4" aria-hidden="true" />
                Prepare applications now
              </Button>
            )}
          </>
        }
      />

      <Card className="mb-6 p-5 sm:p-6">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
          <div className="flex-1">
            <div className="flex items-center gap-2">
              <span className={cn("size-2.5 rounded-full", active ? "bg-app-accent" : "bg-app-line")} aria-hidden="true" />
              <p className="text-lg font-medium">
                {!c ? "Auto-apply is off" : active ? `On · ${c.mode === "hybrid" ? "Hybrid" : "Review first"}` : "Paused"}
              </p>
            </div>
            {c?.paused_reason && <p className="mt-1 text-app-danger">{c.paused_reason}</p>}
            {c && (
              <div className="mt-3 max-w-md">
                <div className="flex justify-between text-xs text-app-muted">
                  <span>Prepared today</span>
                  <span className="font-mono">
                    {prepared} / {c.daily_limit}
                  </span>
                </div>
                <div className="mt-1">
                  <ProgressBar value={(prepared / Math.max(1, c.daily_limit)) * 100} label="Applications prepared today" />
                </div>
              </div>
            )}
          </div>
          <div className="flex gap-2">
            {c && active && (
              <Button variant="secondary" onClick={() => pause.mutate()} loading={pause.isPending}>
                <Pause className="size-4" aria-hidden="true" />
                Pause
              </Button>
            )}
            {c && !active && !changed && (
              <Button onClick={() => resume.mutate()} loading={resume.isPending}>
                <Play className="size-4" aria-hidden="true" />
                Resume
              </Button>
            )}
          </div>
        </div>
      </Card>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2 flex flex-col gap-6">
          <Card as="section" aria-labelledby="mode-title">
            <CardHeader id="mode-title" title="Settings" />
            <div className="flex flex-col gap-5 px-5 pb-5">
              <div role="radiogroup" aria-label="Apply mode" className="grid gap-3 sm:grid-cols-2">
                {MODES.map((m) => {
                  const r = data.readiness[m.value];
                  return (
                    <button
                      key={m.value}
                      type="button"
                      role="radio"
                      aria-checked={mode === m.value}
                      onClick={() => setMode(m.value)}
                      className={cn(
                        "rounded-app-lg border p-4 text-left outline-none focus-visible:ring-2 focus-visible:ring-app-accent",
                        mode === m.value ? "border-app-ink shadow-app-ring" : "border-app-border hover:bg-app-panel"
                      )}
                    >
                      <span className="flex items-center justify-between gap-2 font-medium">
                        {m.label}
                        {m.value === "hybrid" && !r.auto_submit_allowed && <Badge>Pro</Badge>}
                      </span>
                      <span className="mt-1 block text-sm text-app-muted">{m.description}</span>
                    </button>
                  );
                })}
              </div>
              <label className="flex flex-col gap-1.5" htmlFor="daily-limit">
                <span className="text-sm font-medium">
                  Applications per day: <span className="font-mono">{limit}</span>
                  <span className="font-normal text-app-muted"> (your plan allows up to {ready.plan_daily_limit})</span>
                </span>
                <input
                  id="daily-limit"
                  type="range"
                  min={1}
                  max={ready.plan_daily_limit}
                  value={Math.min(limit, ready.plan_daily_limit)}
                  onChange={(e) => setLimit(Number(e.target.value))}
                  className="accent-app-accent max-w-md"
                />
              </label>
              <p className="text-app-muted">
                Minimum match score and target roles come from your{" "}
                <Link href="/preferences" className="text-app-ink underline underline-offset-4">
                  job preferences
                </Link>
                .
              </p>

              {(blockers.length > 0 || !ready.can_start) && (
                <div role="alert" className="rounded-app-lg bg-app-surface p-4">
                  <p className="flex items-center gap-2 font-medium">
                    <AlertTriangle className="size-4" aria-hidden="true" />
                    To use {mode === "hybrid" ? "Hybrid" : "Review"} mode:
                  </p>
                  <ul className="mt-2 list-disc pl-5 text-app-ink-2">
                    {(blockers.length ? blockers : ready.blockers).map((b) => (
                      <li key={b}>{b}</li>
                    ))}
                  </ul>
                </div>
              )}

              <div>
                <Button
                  variant="accent"
                  onClick={() => start.mutate()}
                  loading={start.isPending}
                  disabled={!ready.can_start || (active && !changed)}
                >
                  <Play className="size-4" aria-hidden="true" />
                  {!c ? "Start auto-apply" : changed ? "Save and apply changes" : active ? "Running" : "Start with these settings"}
                </Button>
              </div>
            </div>
          </Card>

          <Card as="section" aria-labelledby="activity-title">
            <CardHeader id="activity-title" title="Recent activity" description="Applications prepared or sent by auto-apply." />
            {data.activity.length === 0 ? (
              <p className="px-5 pb-5 text-app-muted">Nothing yet. Prepared applications will appear here.</p>
            ) : (
              <ul className="divide-y divide-app-border border-t border-app-border">
                {data.activity.map((a) => (
                  <li key={a.id} className="flex flex-col gap-2 px-5 py-3.5 sm:flex-row sm:items-center">
                    <div className="min-w-0 flex-1">
                      <Link href={`/applications/${a.id}`} className="font-medium hover:underline underline-offset-4">
                        {a.job_title}
                      </Link>
                      <p className="text-app-muted">
                        {a.company_name} · {timeAgo(a.updated_at)}
                      </p>
                      {a.failure_reason && <p className="text-xs text-app-danger">{a.failure_reason}</p>}
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge tone={statusTone(a.status)}>{statusLabel(a.status)}</Badge>
                      {(a.status === "failed" || a.status === "needs_user_action") && (
                        <Button variant="ghost" size="sm" onClick={() => retry.mutate(a.id)} loading={retry.isPending && retry.variables === a.id}>
                          <RotateCcw className="size-3.5" aria-hidden="true" />
                          Retry
                        </Button>
                      )}
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </div>

        <div className="flex flex-col gap-6">
          <Card as="section" aria-labelledby="today-title" className="p-5">
            <h2 id="today-title" className="font-medium">
              Today
            </h2>
            <dl className="mt-3 grid grid-cols-2 gap-3">
              {[
                ["Waiting for review", (by.ready_for_review ?? 0) + (by.needs_user_action ?? 0)],
                ["Approved", by.approved ?? 0],
                ["Submitted", by.submitted ?? 0],
                ["Failed", by.failed ?? 0],
              ].map(([label, n]) => (
                <div key={label as string} className="rounded-app-lg bg-app-bg p-3">
                  <dt className="text-xs text-app-muted">{label}</dt>
                  <dd className="font-mono text-2xl">{n}</dd>
                </div>
              ))}
            </dl>
            <ButtonLink href="/review" className="mt-4 w-full">
              Open review queue
            </ButtonLink>
          </Card>
          <Card className="p-5">
            <h2 className="font-medium">How it works</h2>
            <ol className="mt-2 list-decimal space-y-1.5 pl-5 text-app-ink-2">
              <li>We search job boards and company career pages every hour.</li>
              <li>Each job is scored against your profile; only jobs above your minimum score are used.</li>
              <li>Answers are filled from your profile and answer bank, never invented.</li>
              <li>Applications wait in your review queue (or, in Hybrid, 90+ matches are sent).</li>
              <li>Sites with CAPTCHAs or logins are handed back to you to finish.</li>
            </ol>
          </Card>
        </div>
      </div>
    </>
  );
}
