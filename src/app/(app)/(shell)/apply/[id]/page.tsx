"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, Check, CheckCircle2, Copy, Download, ExternalLink, ShieldCheck } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";
import { Badge, Button, ButtonLink, Card, CardHeader, ErrorState, PageHeader, SERVER_WAKING_HINT, Spinner } from "@/components/app/ui";
import { api } from "@/lib/api/endpoints";
import type { ResolvedField } from "@/lib/api/types";
import { humanize } from "@/lib/format";

/**
 * Assisted apply: for sites Applyon can't submit itself (CAPTCHA, login walls, Workday, LinkedIn,
 * Naukri, company sites). Everything is prepared here; the user submits on the employer's site in
 * their own browser, then confirms. Applyon never solves or bypasses a CAPTCHA.
 */
export default function AssistedApplyPage() {
  const { id } = useParams<{ id: string }>();
  const queryClient = useQueryClient();
  const app = useQuery({ queryKey: ["application", id], queryFn: () => api.applications.get(id) });

  const confirm = useMutation({
    mutationFn: () => api.applications.updateStatus(id, "submitted", "Submitted by the candidate (assisted apply)"),
    onSuccess: () => {
      toast.success("Marked as submitted. We'll remind you to follow up.");
      void queryClient.invalidateQueries({ queryKey: ["application", id] });
      void queryClient.invalidateQueries({ queryKey: ["review-queue"] });
      void queryClient.invalidateQueries({ queryKey: ["applications"] });
    },
    onError: (e) => toast.error(e.message),
  });

  if (app.isPending) return <Spinner label="Loading your application" slowHint={SERVER_WAKING_HINT} />;
  if (app.isError) return <ErrorState error={app.error} onRetry={() => app.refetch()} />;

  const a = app.data;
  const fields = a.plan.fields ?? [];
  const yours = fields.filter((f) => needsYou(f));
  const ready = fields.filter((f) => !needsYou(f));
  const submitted = a.status === "submitted";
  const site = a.apply_ats && a.apply_ats !== "unknown" ? humanize(a.apply_ats) : "the employer's site";

  return (
    <>
      <PageHeader
        title={`Apply to ${a.job.company_name}`}
        description={`${a.job.title}. Your answers are ready: open the application on ${site}, paste them in, and submit it yourself.`}
      />

      {submitted ? (
        <Card className="mb-6 flex items-center gap-3 p-5" role="status">
          <CheckCircle2 className="size-5 text-app-accent" aria-hidden="true" />
          <p className="flex-1">
            Submitted{a.submitted_at ? ` on ${new Date(a.submitted_at).toLocaleDateString("en-IN")}` : ""}. It&apos;s in your{" "}
            <Link href="/applications" className="underline underline-offset-4">
              applications tracker
            </Link>
            .
          </p>
        </Card>
      ) : (
        <Card className="mb-6 p-5">
          <ol className="flex flex-col gap-4">
            <Step n={1} title="Download your tailored documents">
              <div className="mt-2 flex flex-wrap gap-2">
                {a.resume_version_id ? (
                  <Button size="sm" variant="secondary" onClick={() => api.documents.downloadResumePdf(a.resume_version_id as string)}>
                    <Download className="size-3.5" aria-hidden="true" />
                    Resume (PDF)
                  </Button>
                ) : (
                  <Badge>Using your master resume</Badge>
                )}
                {a.cover_letter_id && (
                  <Button size="sm" variant="secondary" onClick={() => api.documents.downloadCoverLetterPdf(a.cover_letter_id as string)}>
                    <Download className="size-3.5" aria-hidden="true" />
                    Cover letter (PDF)
                  </Button>
                )}
              </div>
            </Step>
            <Step n={2} title={`Open the application on ${site}`}>
              {a.application_url ? (
                <div className="mt-2">
                  <ButtonLink href={a.application_url} external size="sm">
                    <ExternalLink className="size-3.5" aria-hidden="true" />
                    Open application
                  </ButtonLink>
                </div>
              ) : (
                <p className="mt-1 text-app-muted">No application link was found for this job.</p>
              )}
            </Step>
            <Step n={3} title="Copy your answers into the form, then solve any CAPTCHA and submit">
              <p className="mt-1 text-sm text-app-muted">
                <ShieldCheck className="mr-1 inline size-3.5" aria-hidden="true" />
                You submit it yourself in your browser. Applyon never fills in CAPTCHAs or signs in for you.
              </p>
            </Step>
            <Step n={4} title="Tell us you've applied">
              <div className="mt-2">
                <Button size="sm" variant="accent" onClick={() => confirm.mutate()} loading={confirm.isPending}>
                  <Check className="size-3.5" aria-hidden="true" />
                  I submitted it
                </Button>
              </div>
            </Step>
          </ol>
        </Card>
      )}

      {yours.length > 0 && (
        <Card as="section" aria-labelledby="yours" className="mb-6">
          <CardHeader
            id="yours"
            title={`Only you can answer these (${yours.length})`}
            description="Visa, relocation, notice and similar questions are never answered for you. Missing answers are marked."
          />
          <AnswerList fields={yours} />
        </Card>
      )}

      <Card as="section" aria-labelledby="ready">
        <CardHeader id="ready" title={`Prepared answers (${ready.length})`} description="Copy each one into the matching question on the form." />
        {ready.length ? <AnswerList fields={ready} /> : <p className="px-5 pb-5 text-app-muted">No form questions were read for this job. Use your profile details.</p>}
      </Card>
    </>
  );
}

/** Compliance questions and anything without a confident answer stay with the user. */
function needsYou(f: ResolvedField): boolean {
  return f.source === "unresolved" || f.value === null || f.value === "" || f.needs_review;
}

function Step({ n, title, children }: { n: number; title: string; children?: React.ReactNode }) {
  return (
    <li className="flex gap-3">
      <span className="flex size-6 shrink-0 items-center justify-center rounded-full bg-app-panel text-xs font-medium" aria-hidden="true">
        {n}
      </span>
      <div className="min-w-0 flex-1">
        <p className="font-medium text-app-ink">{title}</p>
        {children}
      </div>
    </li>
  );
}

function AnswerList({ fields }: { fields: ResolvedField[] }) {
  return (
    <ul className="divide-y divide-app-border border-t border-app-border">
      {fields.map((f) => (
        <AnswerRow key={f.field_id} field={f} />
      ))}
    </ul>
  );
}

function AnswerRow({ field }: { field: ResolvedField }) {
  const [copied, setCopied] = useState(false);
  const text = answerText(field.value);
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      toast.error("Couldn't copy. Select the text and copy it instead.");
    }
  };
  return (
    <li className="flex flex-col gap-2 px-5 py-3 sm:flex-row sm:items-start">
      <div className="min-w-0 flex-1">
        <p className="text-sm text-app-muted">
          {field.label}
          {field.required && <span aria-label="required"> *</span>}
        </p>
        {text ? (
          <p className="mt-0.5 whitespace-pre-wrap break-words text-app-ink">{text}</p>
        ) : (
          <p className="mt-0.5 flex items-center gap-1.5 text-app-ink">
            <AlertTriangle className="size-3.5 text-app-danger" aria-hidden="true" />
            Answer this yourself on the form
          </p>
        )}
      </div>
      {text && (
        <Button size="sm" variant="ghost" onClick={copy} aria-label={`Copy answer for ${field.label}`}>
          {copied ? <Check className="size-3.5" aria-hidden="true" /> : <Copy className="size-3.5" aria-hidden="true" />}
          {copied ? "Copied" : "Copy"}
        </Button>
      )}
    </li>
  );
}

function answerText(value: unknown): string {
  if (value === null || value === undefined) return "";
  if (Array.isArray(value)) return value.join(", ");
  if (typeof value === "boolean") return value ? "Yes" : "No";
  return String(value);
}
