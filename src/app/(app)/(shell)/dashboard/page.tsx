"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowRight, ClipboardCheck, Rocket, Sparkles } from "lucide-react";
import Link from "next/link";
import { toast } from "sonner";
import { JobCard } from "@/components/app/job-card";
import {
  Badge,
  Button,
  ButtonLink,
  Card,
  CardHeader,
  EmptyState,
  ErrorState,
  PageHeader,
  ProgressBar,
  Skeleton,
  SkeletonList,
  Stat,
} from "@/components/app/ui";
import { api } from "@/lib/api/endpoints";
import { useAuth } from "@/lib/auth";
import { humanize } from "@/lib/format";

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
  const matches = useQuery({
    queryKey: ["matches", { limit: 5 }],
    queryFn: () => api.matches.list({ limit: 5 }),
  });
  const review = useQuery({ queryKey: ["review-queue", 1], queryFn: () => api.reviewQueue.list(1) });

  const refresh = useMutation({
    mutationFn: api.matches.refresh,
    onSuccess: (r) => {
      toast.success(r.new_matches_count ? `${r.new_matches_count} new matches found.` : "No new matches right now.");
      void queryClient.invalidateQueries({ queryKey: ["matches"] });
      void queryClient.invalidateQueries({ queryKey: ["jobs"] });
    },
    onError: (e) => toast.error(e.message),
  });

  const firstName = (user?.displayName || "").split(" ")[0];
  const o = overview.data;

  return (
    <>
      <PageHeader
        title={`${greeting()}${firstName ? `, ${firstName}` : ""}`}
        description="Here's where your job search stands today."
        actions={
          <Button variant="secondary" onClick={() => refresh.mutate()} loading={refresh.isPending}>
            <Sparkles className="size-4" aria-hidden="true" />
            Find new matches
          </Button>
        }
      />

      {o && o.profile_completeness_score < 80 && (
        <Card className="mb-6 p-5 flex flex-col gap-4 sm:flex-row sm:items-center">
          <div className="flex-1">
            <p className="font-medium">Your profile is {o.profile_completeness_score}% complete</p>
            <p className="text-app-muted">Reach 80% to get better matches and unlock Autopilot.</p>
            <div className="mt-3 max-w-sm">
              <ProgressBar value={o.profile_completeness_score} label="Profile completeness" />
            </div>
          </div>
          <ButtonLink href="/onboarding" variant="primary">
            Finish setup
          </ButtonLink>
        </Card>
      )}

      {overview.isError ? (
        <Card className="mb-6">
          <ErrorState error={overview.error} onRetry={() => overview.refetch()} />
        </Card>
      ) : (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-6">
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
        <div className="lg:col-span-2 flex flex-col gap-6">
          <section aria-labelledby="top-matches">
            <div className="flex items-center justify-between mb-3">
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
                  description="We're scanning new jobs for you. Check back soon, or import a job you found yourself."
                  action={<ButtonLink href="/jobs">Browse jobs</ButtonLink>}
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

          <Card as="section" aria-labelledby="autopilot-card">
            <CardHeader
              id="autopilot-card"
              title="Autopilot"
              description="Prepares applications for your best matches every day."
              action={<Badge>Coming soon</Badge>}
            />
            <div className="px-5 pb-5">
              <div className="flex items-center gap-2 text-app-ink-2">
                <Rocket className="size-4" aria-hidden="true" />
                {o?.can_start_autopilot
                  ? "Your profile is ready for Autopilot."
                  : "Complete your profile to 80% to be ready for Autopilot."}
              </div>
              {o && (
                <p className="mt-2 text-xs text-app-muted">
                  Daily limit: <span className="font-mono">{o.credits.daily_remaining}</span> of{" "}
                  <span className="font-mono">{o.credits.daily_limit}</span> applications left today
                </p>
              )}
            </div>
          </Card>

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
                        <div className="mt-1 h-1.5 rounded-full bg-app-panel overflow-hidden" aria-hidden="true">
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
