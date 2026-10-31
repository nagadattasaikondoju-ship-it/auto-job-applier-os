"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, Check, ChevronDown, ClipboardCheck, ExternalLink, X } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";
import { AnswerPlan } from "@/components/app/answer-plan";
import { Badge, Button, ButtonLink, Card, EmptyState, ErrorState, PageHeader, SkeletonList } from "@/components/app/ui";
import { api } from "@/lib/api/endpoints";
import type { ApplicationDetail } from "@/lib/api/types";
import { formatSalary, statusLabel, statusTone, timeAgo } from "@/lib/format";
import { cn } from "@/lib/utils";

export default function ReviewQueuePage() {
  const queue = useQuery({ queryKey: ["review-queue", 1], queryFn: () => api.reviewQueue.list(1) });

  return (
    <>
      <PageHeader
        title="Review queue"
        description="Applications Applyon prepared for you. Check the answers, fix anything, then approve. Nothing is sent without your approval."
      />
      {queue.isPending ? (
        <SkeletonList rows={3} />
      ) : queue.isError ? (
        <Card>
          <ErrorState error={queue.error} onRetry={() => queue.refetch()} />
        </Card>
      ) : queue.data.items.length === 0 ? (
        <Card>
          <EmptyState
            icon={ClipboardCheck}
            title="You're all caught up"
            description="When Applyon prepares an application, it'll wait here for your approval."
            action={<ButtonLink href="/jobs">Find jobs to apply to</ButtonLink>}
          />
        </Card>
      ) : (
        <ul className="flex flex-col gap-4">
          {queue.data.items.map((app, i) => (
            <li key={app.id}>
              <ReviewCard app={app} defaultOpen={i === 0} />
            </li>
          ))}
        </ul>
      )}
    </>
  );
}

function ReviewCard({ app, defaultOpen }: { app: ApplicationDetail; defaultOpen: boolean }) {
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(defaultOpen);
  const fields = app.plan.fields ?? [];
  // Only required questions block approval; optional ones can be left blank
  const unresolved = fields.filter((f) => f.required && (f.source === "unresolved" || f.value === null || f.value === "")).length;
  const needsAction = app.status === "needs_user_action";
  const assisted = app.apply_mode === "assisted";
  const router = useRouter();

  const done = (msg: string) => {
    toast.success(msg);
    void queryClient.invalidateQueries({ queryKey: ["review-queue"] });
    void queryClient.invalidateQueries({ queryKey: ["applications"] });
  };

  const approve = useMutation({
    mutationFn: () => api.reviewQueue.approve(app.id),
    onSuccess: (r) => {
      if (r.apply_mode === "assisted") {
        // Sites we can't submit to (CAPTCHA, login): go straight to the prepared answers
        done(`Approved. Your answers for ${app.job.company_name} are ready.`);
        router.push(`/apply/${app.id}`);
        return;
      }
      done(
        r.submission_queued
          ? `Approved. We're submitting your ${app.job.company_name} application.`
          : `Approved. Open the application page with the Applyon extension to submit it.`
      );
    },
    onError: (e) => toast.error(e.message),
  });
  const reject = useMutation({
    mutationFn: () => api.reviewQueue.reject(app.id),
    onSuccess: () => done("Removed from your queue."),
    onError: (e) => toast.error(e.message),
  });

  const salary = formatSalary(app.job.salary_min_lpa, app.job.salary_max_lpa);
  const panelId = `review-${app.id}`;

  return (
    <Card as="article">
      <div className="flex flex-col gap-4 p-5 sm:flex-row sm:items-center">
        <button
          type="button"
          onClick={() => setOpen((o) => !o)}
          aria-expanded={open}
          aria-controls={panelId}
          className="flex min-w-0 flex-1 items-start gap-3 text-left rounded-app-md outline-none focus-visible:ring-2 focus-visible:ring-app-accent"
        >
          <ChevronDown
            className={cn("mt-1 size-4 shrink-0 text-app-muted transition-transform duration-150", open && "rotate-180")}
            aria-hidden="true"
          />
          <span className="min-w-0">
            <span className="block text-base font-medium text-app-ink">{app.job.title}</span>
            <span className="block text-app-muted">
              {app.job.company_name} · {app.job.is_remote ? "Remote / hybrid" : app.job.location_city}
              {salary && ` · ${salary}`}
            </span>
            <span className="mt-2 flex flex-wrap gap-1.5">
              <Badge tone={statusTone(app.status)}>{statusLabel(app.status)}</Badge>
              {unresolved > 0 && (
                <Badge tone="danger">
                  {unresolved} required question{unresolved === 1 ? "" : "s"} need answers
                </Badge>
              )}
              <Badge tone={assisted ? "neutral" : "success"}>{assisted ? "Assisted apply" : "Auto-apply"}</Badge>
              <Badge>Prepared {timeAgo(app.created_at)}</Badge>
            </span>
          </span>
        </button>
        <div className="flex gap-2 sm:shrink-0">
          <Button variant="ghost" size="sm" onClick={() => reject.mutate()} loading={reject.isPending}>
            <X className="size-3.5" aria-hidden="true" />
            Skip
          </Button>
          {needsAction ? (
            <ButtonLink href={`/apply/${app.id}`} size="sm">
              <ExternalLink className="size-3.5" aria-hidden="true" />
              Finish applying
            </ButtonLink>
          ) : (
            <Button
              size="sm"
              variant="accent"
              onClick={() => approve.mutate()}
              loading={approve.isPending}
              // Assisted applications can be approved with gaps: the user answers those on the form
              disabled={unresolved > 0 && !assisted}
            >
              <Check className="size-3.5" aria-hidden="true" />
              {assisted ? "Approve & apply" : "Approve"}
            </Button>
          )}
        </div>
      </div>

      {open && (
        <div id={panelId} className="border-t border-app-border">
          {needsAction && (
            <p className="flex gap-2 bg-app-surface px-5 py-3 text-app-ink">
              <AlertTriangle className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
              {app.failure_reason ||
                "This site needs you to finish the application yourself (for example a login or verification step). Open it with the Applyon extension and your answers will be filled in."}
            </p>
          )}
          {unresolved > 0 && !needsAction && (
            <p className="bg-app-surface px-5 py-3 text-app-ink">Answer the required questions (marked *) to approve this application.</p>
          )}
          <AnswerPlan applicationId={app.id} fields={fields} />
          <div className="border-t border-app-border px-5 py-3">
            <Link href={`/applications/${app.id}`} className="text-sm text-app-ink-2 underline-offset-4 hover:underline">
              View full application and timeline
            </Link>
          </div>
        </div>
      )}
    </Card>
  );
}
