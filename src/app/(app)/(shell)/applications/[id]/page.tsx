"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Circle, ExternalLink } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";
import { AnswerPlan } from "@/components/app/answer-plan";
import { Badge, Button, ButtonLink, Card, CardHeader, ErrorState, Field, Select, Skeleton, Textarea } from "@/components/app/ui";
import { api } from "@/lib/api/endpoints";
import type { ApplicationStatus } from "@/lib/api/types";
import { formatDateTime, formatSalary, humanize, statusLabel, statusTone } from "@/lib/format";

// Statuses a person can set by hand once an application is out the door.
const MANUAL_STATUSES: ApplicationStatus[] = ["submitted", "interview", "offer", "rejected", "ghosted", "withdrawn"];

export default function ApplicationDetailPage() {
  const { id } = useParams<{ id: string }>();
  const queryClient = useQueryClient();
  const app = useQuery({ queryKey: ["application", id], queryFn: () => api.applications.get(id) });
  const [newStatus, setNewStatus] = useState<ApplicationStatus | "">("");
  const [notes, setNotes] = useState("");

  const update = useMutation({
    mutationFn: () => api.applications.updateStatus(id, newStatus as ApplicationStatus, notes || undefined),
    onSuccess: () => {
      toast.success(`Marked as ${statusLabel(newStatus)}.`);
      setNewStatus("");
      setNotes("");
      void queryClient.invalidateQueries({ queryKey: ["application", id] });
      void queryClient.invalidateQueries({ queryKey: ["applications"] });
      void queryClient.invalidateQueries({ queryKey: ["analytics"] });
    },
    onError: (e) => toast.error(e.message),
  });

  if (app.isPending) {
    return (
      <div className="flex flex-col gap-4">
        <Skeleton className="h-8 w-1/2" />
        <Skeleton className="h-80 w-full rounded-app-xl" />
      </div>
    );
  }
  if (app.isError) return <ErrorState error={app.error} onRetry={() => app.refetch()} />;

  const a = app.data;
  const salary = formatSalary(a.job.salary_min_lpa, a.job.salary_max_lpa);
  const events = [...a.events].sort((x, y) => y.created_at.localeCompare(x.created_at));

  return (
    <>
      <Link href="/applications" className="mb-4 inline-flex items-center gap-1.5 text-sm text-app-muted hover:text-app-ink">
        <ArrowLeft className="size-4" aria-hidden="true" />
        All applications
      </Link>

      <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h1 className="font-display text-3xl sm:text-4xl leading-tight">{a.job.title}</h1>
          <p className="mt-1 text-app-muted">
            <Link href={`/jobs/${a.job.id}`} className="hover:underline underline-offset-4">
              {a.job.company_name}
            </Link>{" "}
            · {a.job.is_remote ? "Remote / hybrid" : a.job.location_city}
            {salary && ` · ${salary}`}
          </p>
          <div className="mt-3 flex flex-wrap gap-1.5">
            <Badge tone={statusTone(a.status)}>{statusLabel(a.status)}</Badge>
            <Badge>{humanize(a.channel)}</Badge>
            {a.job.ats_type && <Badge>{humanize(a.job.ats_type)}</Badge>}
          </div>
        </div>
        {a.application_url && (
          <ButtonLink href={a.application_url} external variant="secondary">
            <ExternalLink className="size-4" aria-hidden="true" />
            Open application page
          </ButtonLink>
        )}
      </div>

      {a.failure_reason && (
        <p role="alert" className="mb-6 rounded-app-lg bg-app-danger/10 px-4 py-3 text-app-ink">
          {a.failure_reason}
        </p>
      )}

      <div className="grid gap-6 lg:grid-cols-3">
        <Card as="section" aria-labelledby="answers-title" className="lg:col-span-2 overflow-hidden">
          <CardHeader
            id="answers-title"
            title="Form answers"
            description="What Applyon will fill in. Edit anything before it's sent."
          />
          <div className="border-t border-app-border">
            <AnswerPlan applicationId={a.id} fields={a.plan.fields ?? []} />
          </div>
        </Card>

        <div className="flex flex-col gap-6">
          <Card as="section" aria-labelledby="status-title">
            <CardHeader id="status-title" title="Update status" description="Heard back? Keep your tracker accurate." />
            <form
              className="px-5 pb-5 flex flex-col gap-3"
              onSubmit={(e) => {
                e.preventDefault();
                if (newStatus) update.mutate();
              }}
            >
              <Field label="New status" htmlFor="new-status">
                <Select id="new-status" value={newStatus} onChange={(e) => setNewStatus(e.target.value as ApplicationStatus)}>
                  <option value="">Choose a status…</option>
                  {MANUAL_STATUSES.filter((s) => s !== a.status).map((s) => (
                    <option key={s} value={s}>
                      {statusLabel(s)}
                    </option>
                  ))}
                </Select>
              </Field>
              <Field label="Note (optional)" htmlFor="status-note">
                <Textarea
                  id="status-note"
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  className="min-h-20"
                  placeholder="e.g. Recruiter call on Monday"
                />
              </Field>
              <Button type="submit" disabled={!newStatus} loading={update.isPending}>
                Save status
              </Button>
            </form>
          </Card>

          <Card as="section" aria-labelledby="timeline-title">
            <CardHeader id="timeline-title" title="Timeline" />
            {events.length === 0 ? (
              <p className="px-5 pb-5 text-app-muted">No activity yet.</p>
            ) : (
              <ol className="px-5 pb-5 flex flex-col gap-4">
                {events.map((ev) => {
                  const to = (ev.payload?.to ?? ev.payload?.status) as string | undefined;
                  const note = ev.payload?.notes as string | undefined;
                  return (
                    <li key={ev.id} className="flex gap-3">
                      <Circle className="mt-1 size-2.5 shrink-0 fill-app-accent text-app-accent" aria-hidden="true" />
                      <div>
                        <p className="text-app-ink">
                          {to ? `Moved to ${statusLabel(to)}` : humanize(ev.type)}
                          <span className="text-app-muted"> · {ev.actor === "user" ? "you" : ev.actor}</span>
                        </p>
                        {note && <p className="text-app-muted">{note}</p>}
                        <p className="text-xs text-app-subtle">{formatDateTime(ev.created_at)}</p>
                      </div>
                    </li>
                  );
                })}
              </ol>
            )}
          </Card>
        </div>
      </div>
    </>
  );
}
