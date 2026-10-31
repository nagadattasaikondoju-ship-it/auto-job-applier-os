"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  ArrowLeft,
  Bookmark,
  BookmarkCheck,
  Building2,
  CheckCircle2,
  ExternalLink,
  FileText,
  MapPin,
  Send,
  ThumbsDown,
  ThumbsUp,
  XCircle,
} from "lucide-react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { toast } from "sonner";
import {
  Badge,
  Button,
  ButtonLink,
  Card,
  CardHeader,
  ErrorState,
  ScoreRing,
  Skeleton,
} from "@/components/app/ui";
import { api } from "@/lib/api/endpoints";
import type { JobFeedback } from "@/lib/api/types";
import { formatSalary, humanize, timeAgo } from "@/lib/format";

export default function JobDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const queryClient = useQueryClient();
  const job = useQuery({ queryKey: ["job", id], queryFn: () => api.jobs.get(id) });

  const feedback = useMutation({
    mutationFn: (f: JobFeedback) => api.jobs.feedback(id, f),
    onSuccess: (_, f) => {
      void queryClient.invalidateQueries({ queryKey: ["job", id] });
      void queryClient.invalidateQueries({ queryKey: ["jobs"] });
      void queryClient.invalidateQueries({ queryKey: ["matches"] });
      if (f === "dismissed") {
        toast.success("Job hidden. We'll show fewer like it.");
        router.push("/jobs");
      } else {
        toast.success("Thanks, this improves your future matches.");
      }
    },
    onError: (e) => toast.error(e.message),
  });

  const save = useMutation({
    mutationFn: (on: boolean) => api.jobs.save(id, on),
    onSuccess: (_, on) => {
      toast.success(on ? "Saved for later." : "Removed from saved jobs.");
      void queryClient.invalidateQueries({ queryKey: ["job", id] });
      void queryClient.invalidateQueries({ queryKey: ["matches"] });
    },
    onError: (e) => toast.error(e.message),
  });

  const prepare = useMutation({
    mutationFn: () => api.applications.create(id, "extension"),
    onSuccess: (r) => {
      void queryClient.invalidateQueries({ queryKey: ["applications"] });
      toast.success(
        r.unresolved_count
          ? `Application prepared. ${r.unresolved_count} question${r.unresolved_count === 1 ? "" : "s"} need your answer.`
          : "Application prepared and ready to review."
      );
      router.push(`/applications/${r.id}`);
    },
    onError: (e) => toast.error(e.message),
  });

  if (job.isPending) {
    return (
      <div className="flex flex-col gap-4">
        <Skeleton className="h-8 w-2/3" />
        <Skeleton className="h-5 w-1/3" />
        <Skeleton className="h-96 w-full rounded-app-xl" />
      </div>
    );
  }
  if (job.isError) return <ErrorState error={job.error} onRetry={() => job.refetch()} />;

  const j = job.data;
  const m = j.match;
  const salary = formatSalary(j.salary_min_lpa, j.salary_max_lpa);
  const experience =
    j.experience_min != null || j.experience_max != null
      ? `${j.experience_min ?? 0}–${j.experience_max ?? "+"} yrs experience`
      : null;

  return (
    <>
      <Link href="/jobs" className="mb-4 inline-flex items-center gap-1.5 text-sm text-app-muted hover:text-app-ink">
        <ArrowLeft className="size-4" aria-hidden="true" />
        Back to jobs
      </Link>

      <div className="flex flex-col gap-6 lg:flex-row lg:items-start">
        <div className="min-w-0 flex-1 flex flex-col gap-6">
          <div>
            <h1 className="font-display text-3xl sm:text-4xl leading-tight">{j.title}</h1>
            <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-app-muted">
              <span className="inline-flex items-center gap-1.5">
                <Building2 className="size-4" aria-hidden="true" />
                {j.company}
              </span>
              {j.location && (
                <span className="inline-flex items-center gap-1.5">
                  <MapPin className="size-4" aria-hidden="true" />
                  {j.location}
                </span>
              )}
              {j.posted_at && <span>Posted {timeAgo(j.posted_at)}</span>}
            </div>
            <div className="mt-3 flex flex-wrap gap-1.5">
              {salary && <Badge tone="info">{salary}</Badge>}
              {j.remote_mode && <Badge>{humanize(j.remote_mode)}</Badge>}
              {j.employment_type && <Badge>{humanize(j.employment_type)}</Badge>}
              {experience && <Badge>{experience}</Badge>}
              {j.ats_type && <Badge>via {humanize(j.ats_type)}</Badge>}
              {j.is_active === false && <Badge tone="danger">Closed by the employer</Badge>}
              {j.apply_mode && (
                <Badge tone={j.apply_mode === "auto" ? "success" : "neutral"}>
                  {j.apply_mode === "auto" ? "Auto-apply" : "Assisted apply"}
                </Badge>
              )}
            </div>
          </div>

          <div className="flex flex-wrap gap-2">
            <ButtonLink href={`/jobs/${id}/tailor`}>
              <FileText className="size-4" aria-hidden="true" />
              Tailor resume & cover letter
            </ButtonLink>
            <Button variant="accent" onClick={() => prepare.mutate()} loading={prepare.isPending}>
              <Send className="size-4" aria-hidden="true" />
              Prepare application
            </Button>
            <ButtonLink href={j.application_url} variant="secondary" external>
              <ExternalLink className="size-4" aria-hidden="true" />
              Open posting
            </ButtonLink>
            <Button
              variant="ghost"
              onClick={() => save.mutate(j.match?.status !== "saved")}
              loading={save.isPending}
              aria-pressed={j.match?.status === "saved"}
            >
              {j.match?.status === "saved" ? (
                <BookmarkCheck className="size-4 text-app-accent" aria-hidden="true" />
              ) : (
                <Bookmark className="size-4" aria-hidden="true" />
              )}
              {j.match?.status === "saved" ? "Saved" : "Save"}
            </Button>
          </div>

          {j.required_skills && j.required_skills.length > 0 && (
            <Card as="section" aria-labelledby="skills-title" className="p-5">
              <h2 id="skills-title" className="font-medium">
                Skills they ask for
              </h2>
              <div className="mt-3 flex flex-wrap gap-1.5">
                {j.required_skills.map((s) => (
                  <Badge key={s}>{s}</Badge>
                ))}
              </div>
            </Card>
          )}

          <Card as="section" aria-labelledby="desc-title" className="p-5">
            <h2 id="desc-title" className="font-medium">
              Job description
            </h2>
            {/* Plain text only: job descriptions come from third-party sites, so we never inject their HTML. */}
            <div className="mt-3 whitespace-pre-line leading-relaxed text-app-ink-2">
              {j.description_text || "No description available. Open the posting to read it."}
            </div>
          </Card>
        </div>

        <aside className="w-full lg:w-80 lg:sticky lg:top-20 flex flex-col gap-4" aria-label="Fit analysis">
          <Card>
            <CardHeader title="Your fit" />
            <div className="px-5 pb-5">
              {!m ? (
                <p className="text-app-muted">
                  This job hasn&apos;t been scored against your profile yet. Run &ldquo;Find new matches&rdquo; on the Jobs
                  page.
                </p>
              ) : (
                <>
                  <div className="flex items-center gap-4">
                    <ScoreRing score={m.score} size={88} />
                    <div>
                      <p className="font-medium">
                        {m.decision === "apply" ? "Strong fit" : m.decision === "maybe" ? "Worth a look" : "Weak fit"}
                      </p>
                      <p className="text-app-muted">out of 100</p>
                    </div>
                  </div>

                  {m.fit_reasons.length > 0 && (
                    <div className="mt-5">
                      <h3 className="text-xs font-medium text-app-muted">Why you fit</h3>
                      <ul className="mt-2 flex flex-col gap-2">
                        {m.fit_reasons.map((r) => (
                          <li key={r} className="flex gap-2">
                            <CheckCircle2 className="mt-0.5 size-4 shrink-0 text-app-accent" aria-hidden="true" />
                            {r}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {m.gaps.length > 0 && (
                    <div className="mt-5">
                      <h3 className="text-xs font-medium text-app-muted">Gaps</h3>
                      <ul className="mt-2 flex flex-col gap-2">
                        {m.gaps.map((g) => (
                          <li key={g} className="flex gap-2">
                            <XCircle className="mt-0.5 size-4 shrink-0 text-app-subtle" aria-hidden="true" />
                            {g}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {m.risk_flags && m.risk_flags.length > 0 && (
                    <div className="mt-5">
                      <h3 className="text-xs font-medium text-app-muted">Watch out for</h3>
                      <ul className="mt-2 flex flex-col gap-2">
                        {m.risk_flags.map((r) => (
                          <li key={r} className="flex gap-2">
                            <AlertTriangle className="mt-0.5 size-4 shrink-0 text-app-danger" aria-hidden="true" />
                            {r}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {m.resume_focus && m.resume_focus.length > 0 && (
                    <div className="mt-5">
                      <h3 className="text-xs font-medium text-app-muted">Your tailored resume will highlight</h3>
                      <div className="mt-2 flex flex-wrap gap-1.5">
                        {m.resume_focus.map((f) => (
                          <Badge key={f} tone="success">
                            {f}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  )}
                </>
              )}
            </div>
          </Card>

          <Card className="p-5">
            <p className="text-sm font-medium">Is this a good match?</p>
            <div className="mt-3 flex gap-2">
              <Button
                variant={m?.user_feedback === "good" ? "primary" : "secondary"}
                size="sm"
                aria-pressed={m?.user_feedback === "good"}
                onClick={() => feedback.mutate("good")}
              >
                <ThumbsUp className="size-3.5" aria-hidden="true" />
                Yes
              </Button>
              <Button
                variant={m?.user_feedback === "bad" ? "primary" : "secondary"}
                size="sm"
                aria-pressed={m?.user_feedback === "bad"}
                onClick={() => feedback.mutate("bad")}
              >
                <ThumbsDown className="size-3.5" aria-hidden="true" />
                No
              </Button>
              <Button variant="ghost" size="sm" onClick={() => feedback.mutate("dismissed")}>
                Hide job
              </Button>
            </div>
          </Card>
        </aside>
      </div>
    </>
  );
}
