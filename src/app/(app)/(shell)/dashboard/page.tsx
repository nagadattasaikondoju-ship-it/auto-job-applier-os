"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowRight, BellRing, Check, ClipboardCheck, Rocket, Search } from "lucide-react";
import Link from "next/link";
import { toast } from "sonner";
import { JobCard } from "@/components/app/job-card";
import { Button, ButtonLink, Card, CardHeader, EmptyState, ErrorState, PageHeader, Skeleton, SkeletonList, Stat } from "@/components/app/ui";
import { api } from "@/lib/api/endpoints";
import { useAuth } from "@/lib/auth";
import { formatDate, humanize } from "@/lib/format";
import { cn } from "@/lib/utils";

const FUNNEL_LABEL: Record<string, string> = {
  matched: "Matched",
  reviewed: "Ready to review",
  submitted: "Applied",
  interview: "Interview",
  offer: "Offer",
};

function greeting() {
  const h = new Date().getHours();
  return h < 12 ? "Good morning" : h < 17 ? "Good afternoon" : "Good evening";
}

export default function DashboardPage() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const overview = useQuery({ queryKey: ["analytics", "overview"], queryFn: api.analytics.overview });
  const funnel = useQuery({ queryKey: ["analytics", "funnel"], queryFn: api.analytics.funnel });
  const matches = useQuery({ queryKey: ["matches", { limit: 5 }], queryFn: () => api.matches.list({ limit: 5 }) });
  const review = useQuery({ queryKey: ["review-queue", 1], queryFn: () => api.reviewQueue.list(1) });
  const autopilot = useQuery({ queryKey: ["autopilot"], queryFn: api.autopilot.get });
  const profile = useQuery({ queryKey: ["profile"], queryFn: api.profile.get, retry: false });
  const prefs = useQuery({ queryKey: ["preferences"], queryFn: api.preferences.get });
  const versions = useQuery({ queryKey: ["resume-versions"], queryFn: api.documents.resumeVersions });
  const followUps = useQuery({ queryKey: ["follow-ups"], queryFn: api.applications.followUps });

  const discover = useMutation({
    mutationFn: api.jobs.discover,
    onSuccess: (r) => {
      toast.success(r.message);
      setTimeout(() => void queryClient.invalidateQueries({ queryKey: ["matches"] }), 15_000);
    },
    onError: (e) => toast.error(e.message),
  });

  const firstName = (user?.displayName || "").split(" ")[0];
  const o = overview.data;
  const campaign = autopilot.data?.campaign ?? null;

  const steps = [
    { label: "Upload your resume", done: profile.isSuccess, href: "/onboarding" },
    { label: "Fix it for ATS", done: (versions.data?.items ?? []).some((v) => v.kind === "optimized"), href: "/resume" },
    { label: "Tell us what you want", done: Boolean(prefs.data?.exists), href: "/preferences" },
    { label: "Turn on auto-apply", done: Boolean(campaign), href: "/auto-apply" },
  ];
  const setupDone = steps.every((s) => s.done);
  const loadingSetup = profile.isPending || prefs.isPending || versions.isPending || autopilot.isPending;

  return (
    <>
      <PageHeader
        title={`${greeting()}${firstName ? `, ${firstName}` : ""}`}
        description="Here's where your job search stands today."
        actions={
          <Button variant="secondary" onClick={() => discover.mutate()} loading={discover.isPending}>
            <Search className="size-4" aria-hidden="true" />
            Find jobs now
          </Button>
        }
      />

      {!loadingSetup && !setupDone && (
        <Card as="section" aria-labelledby="setup-title" className="mb-6 p-5">
          <div className="flex flex-col gap-4 md:flex-row md:items-center">
            <div className="md:w-56">
              <h2 id="setup-title" className="font-medium">
                Finish setting up
              </h2>
              <p className="text-app-muted">
                {steps.filter((s) => s.done).length} of {steps.length} done
              </p>
            </div>
            <ol className="grid flex-1 gap-2 sm:grid-cols-2 lg:grid-cols-4">
              {steps.map((s, i) => (
                <li key={s.label}>
                  <Link
                    href={s.href}
                    className={cn(
                      "flex h-full items-center gap-2 rounded-app-lg border px-3 py-2.5 outline-none focus-visible:ring-2 focus-visible:ring-app-accent",
                      s.done ? "border-app-border bg-app-bg text-app-muted" : "border-app-ink bg-app-card text-app-ink hover:bg-app-panel"
                    )}
                  >
                    <span
                      className={cn(
                        "flex size-6 shrink-0 items-center justify-center rounded-full text-xs",
                        s.done ? "bg-app-accent text-app-ink" : "bg-app-ink text-app-card"
                      )}
                    >
                      {s.done ? <Check className="size-3.5" aria-hidden="true" /> : i + 1}
                    </span>
                    <span className={cn(s.done && "line-through")}>{s.label}</span>
                    <span className="sr-only">{s.done ? "(done)" : "(to do)"}</span>
                  </Link>
                </li>
              ))}
            </ol>
          </div>
        </Card>
      )}

      {overview.isError ? (
        <Card className="mb-6">
          <ErrorState error={overview.error} onRetry={() => overview.refetch()} />
        </Card>
      ) : (
        <div className="mb-6 grid grid-cols-2 gap-3 lg:grid-cols-4">
          {overview.isPending ? (
            Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-28 rounded-app-xl" />)
          ) : (
            <>
              <Stat label="Applications" value={o!.total_applications} />
              <Stat label="Submitted" value={o!.total_submitted} />
              <Stat label="Interviews" value={o!.total_interviews} />
              <Stat label="Offers" value={o!.total_offers} />
            </>
          )}
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="flex flex-col gap-6 lg:col-span-2">
          <section aria-labelledby="top-matches">
            <div className="mb-3 flex items-center justify-between">
              <h2 id="top-matches" className="text-base font-medium">
                Top matches for you
              </h2>
              <Link href="/jobs" className="inline-flex items-center gap-1 text-sm text-app-ink-2 hover:text-app-ink">
                All jobs <ArrowRight className="size-3.5" aria-hidden="true" />
              </Link>
            </div>
            {matches.isPending ? (
              <SkeletonList rows={3} />
            ) : matches.isError ? (
              <Card>
                <ErrorState error={matches.error} onRetry={() => matches.refetch()} />
              </Card>
            ) : matches.data.items.length === 0 ? (
              <Card>
                <EmptyState
                  title="No matches yet"
                  description={
                    prefs.data?.exists
                      ? "We're searching job sources for your roles. Click “Find jobs now” to search immediately."
                      : "Tell us what roles you want and we'll start finding matches."
                  }
                  action={
                    prefs.data?.exists ? (
                      <Button onClick={() => discover.mutate()} loading={discover.isPending}>
                        Find jobs now
                      </Button>
                    ) : (
                      <ButtonLink href="/preferences">Set preferences</ButtonLink>
                    )
                  }
                />
              </Card>
            ) : (
              <div className="flex flex-col gap-3">
                {matches.data.items.map((m) => (
                  <JobCard
                    key={m.id}
                    job={{
                      id: m.job_id,
                      title: m.title,
                      company: m.company,
                      location: m.location,
                      score: m.match_score,
                      decision: m.decision,
                      fit_reasons: m.fit_reasons,
                    }}
                  />
                ))}
              </div>
            )}
          </section>
        </div>

        <div className="flex flex-col gap-6">
          <Card as="section" aria-labelledby="autopilot-card">
            <CardHeader
              id="autopilot-card"
              title="Auto-apply"
              description={
                campaign
                  ? campaign.status === "active"
                    ? `On · ${campaign.mode === "hybrid" ? "Hybrid" : "Review first"}`
                    : "Paused"
                  : "Off. Prepares applications for your best matches every day."
              }
            />
            <div className="px-5 pb-5">
              {autopilot.isPending ? (
                <Skeleton className="h-12" />
              ) : campaign ? (
                <p className="text-app-ink-2">
                  <span className="font-mono text-2xl text-app-ink">{autopilot.data!.today.prepared}</span> of{" "}
                  <span className="font-mono">{campaign.daily_limit}</span> prepared today
                </p>
              ) : null}
              <ButtonLink href="/auto-apply" variant={campaign ? "secondary" : "accent"} className="mt-3 w-full">
                <Rocket className="size-4" aria-hidden="true" />
                {campaign ? "Manage auto-apply" : "Turn on auto-apply"}
              </ButtonLink>
            </div>
          </Card>

          <Card as="section" aria-labelledby="review-card">
            <CardHeader id="review-card" title="Waiting for your review" />
            <div className="px-5 pb-5">
              {review.isPending ? (
                <Skeleton className="h-16" />
              ) : (review.data?.total ?? 0) === 0 ? (
                <p className="text-app-muted">Nothing to review. Prepared applications will show up here.</p>
              ) : (
                <>
                  <p className="font-mono text-3xl">{review.data!.total}</p>
                  <p className="text-app-muted">applications ready to approve</p>
                  <ButtonLink href="/review" className="mt-4 w-full">
                    <ClipboardCheck className="size-4" aria-hidden="true" />
                    Open review queue
                  </ButtonLink>
                </>
              )}
            </div>
          </Card>

          {(followUps.data?.due.length ?? 0) > 0 && (
            <Card as="section" aria-labelledby="fu-card">
              <CardHeader id="fu-card" title="Follow-ups due" />
              <ul className="flex flex-col gap-2 px-5 pb-3">
                {followUps.data!.due.slice(0, 3).map((a) => (
                  <li key={a.id} className="text-app-ink-2">
                    {a.job_title} <span className="text-app-muted">· {a.company_name} · {formatDate(a.follow_up_at)}</span>
                  </li>
                ))}
              </ul>
              <div className="px-5 pb-5">
                <ButtonLink href="/follow-ups" variant="secondary" className="w-full">
                  <BellRing className="size-4" aria-hidden="true" />
                  Draft follow-ups
                </ButtonLink>
              </div>
            </Card>
          )}

          <Card as="section" aria-labelledby="funnel-card">
            <CardHeader id="funnel-card" title="Your funnel" description="From match to offer." />
            <div className="px-5 pb-5">
              {funnel.isPending ? (
                <Skeleton className="h-32" />
              ) : funnel.isError ? (
                <p className="text-app-muted">Funnel data isn&apos;t available right now.</p>
              ) : (
                <ul className="flex flex-col gap-3">
                  {funnel.data.stages.map((s) => {
                    const max = Math.max(1, ...funnel.data.stages.map((x) => x.count));
                    return (
                      <li key={s.stage}>
                        <div className="flex justify-between text-sm">
                          <span className="text-app-ink-2">{FUNNEL_LABEL[s.stage] ?? humanize(s.stage)}</span>
                          <span className="font-mono">{s.count}</span>
                        </div>
                        <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-app-panel" aria-hidden="true">
                          <div className="h-full rounded-full bg-app-accent" style={{ width: `${(s.count / max) * 100}%` }} />
                        </div>
                      </li>
                    );
                  })}
                </ul>
              )}
            </div>
          </Card>
        </div>
      </div>
    </>
  );
}
