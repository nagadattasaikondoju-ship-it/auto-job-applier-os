"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, ArrowLeft, Copy, Download, FileText, Send, ShieldCheck, Sparkles } from "lucide-react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";
import { Badge, Button, Card, CardHeader, Checkbox, EmptyState, ErrorState, Skeleton, Tabs } from "@/components/app/ui";
import { api } from "@/lib/api/endpoints";
import type { FlaggedClaim, TailorResult } from "@/lib/api/types";

interface TailoredContent {
  summary?: string;
  skills_ordered?: string[];
  experiences?: { experience_id: string; company: string; title: string; bullets: { source_bullet_id: string; text: string }[] }[];
  keywords_used?: string[];
  changes_made?: string[];
}

function claimText(c: FlaggedClaim) {
  return c.claim ?? c.text ?? JSON.stringify(c);
}

export default function TailorPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const queryClient = useQueryClient();
  const job = useQuery({ queryKey: ["job", id], queryFn: () => api.jobs.get(id) });
  const [includeCoverLetter, setIncludeCoverLetter] = useState(true);
  const [result, setResult] = useState<TailorResult | null>(null);
  const [tab, setTab] = useState<"resume" | "cover">("resume");

  const tailor = useMutation({
    mutationFn: () => api.jobs.tailor(id, includeCoverLetter),
    onSuccess: (r) => {
      setResult(r);
      void queryClient.invalidateQueries({ queryKey: ["credits"] });
    },
    onError: (e) => toast.error(e.message),
  });

  const download = useMutation({
    mutationFn: () => api.documents.downloadResumePdf(result!.resume_version.id, "Resume.pdf"),
    onError: (e) => toast.error(e.message),
  });

  const prepare = useMutation({
    mutationFn: () => api.applications.create(id, "extension"),
    onSuccess: (r) => {
      void queryClient.invalidateQueries({ queryKey: ["applications"] });
      router.push(`/applications/${r.id}`);
    },
    onError: (e) => toast.error(e.message),
  });

  const content = (result?.resume_version.content ?? {}) as TailoredContent;
  const flagged = result?.resume_version.flagged_claims ?? [];
  const truth = result?.resume_version.truth_check_status;

  return (
    <>
      <Link href={`/jobs/${id}`} className="mb-4 inline-flex items-center gap-1.5 text-sm text-app-muted hover:text-app-ink">
        <ArrowLeft className="size-4" aria-hidden="true" />
        Back to job
      </Link>

      <div className="mb-6">
        <h1 className="font-display text-3xl sm:text-4xl leading-tight">Tailor your application</h1>
        {job.isPending ? (
          <Skeleton className="mt-2 h-5 w-64" />
        ) : job.data ? (
          <p className="mt-1 text-app-muted">
            {job.data.title} at {job.data.company}
          </p>
        ) : null}
      </div>

      {!result ? (
        <Card className="p-6">
          {tailor.isPending ? (
            <div role="status" className="flex flex-col gap-4">
              <p className="font-medium">Writing your tailored documents…</p>
              <ol className="flex flex-col gap-2 text-app-muted">
                <li>Reading the job description</li>
                <li>Picking your most relevant experience</li>
                <li>Rewriting bullets using only facts from your profile</li>
                <li>Running the truth check</li>
              </ol>
              <Skeleton className="h-2 w-full" />
            </div>
          ) : tailor.isError ? (
            <ErrorState error={tailor.error} onRetry={() => tailor.mutate()} />
          ) : (
            <div className="flex flex-col gap-5 max-w-xl">
              <div className="flex gap-3">
                <Sparkles className="mt-0.5 size-5 shrink-0 text-app-accent" aria-hidden="true" />
                <div>
                  <p className="font-medium">Create a resume tailored to this job</p>
                  <p className="text-app-muted">
                    We reorder and rephrase your real experience to match what this role asks for. Nothing is invented,
                    and every claim is checked against your profile.
                  </p>
                </div>
              </div>
              <Checkbox
                checked={includeCoverLetter}
                onChange={setIncludeCoverLetter}
                label="Also write a cover letter"
                description="Uses one extra AI credit."
              />
              <div>
                <Button onClick={() => tailor.mutate()}>
                  <Sparkles className="size-4" aria-hidden="true" />
                  Generate documents
                </Button>
              </div>
            </div>
          )}
        </Card>
      ) : (
        <div className="flex flex-col gap-6 lg:flex-row lg:items-start">
          <div className="min-w-0 flex-1">
            <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
              <Tabs
                label="Documents"
                value={tab}
                onChange={setTab}
                items={[
                  { value: "resume", label: "Resume" },
                  ...(result.cover_letter ? [{ value: "cover" as const, label: "Cover letter" }] : []),
                ]}
              />
              <div className="flex gap-2">
                <Button variant="secondary" size="sm" onClick={() => tailor.mutate()} loading={tailor.isPending}>
                  Regenerate
                </Button>
              </div>
            </div>

            {tab === "resume" ? (
              <Card className="p-6 sm:p-8">
                {content.summary && (
                  <section aria-labelledby="sum">
                    <h2 id="sum" className="text-xs font-medium text-app-muted">
                      Summary
                    </h2>
                    <p className="mt-2 leading-relaxed text-app-ink-2">{content.summary}</p>
                  </section>
                )}
                {content.skills_ordered && content.skills_ordered.length > 0 && (
                  <section aria-labelledby="sk" className="mt-6">
                    <h2 id="sk" className="text-xs font-medium text-app-muted">
                      Skills
                    </h2>
                    <div className="mt-2 flex flex-wrap gap-1.5">
                      {content.skills_ordered.map((s) => (
                        <Badge key={s} tone={content.keywords_used?.includes(s) ? "success" : "neutral"}>
                          {s}
                        </Badge>
                      ))}
                    </div>
                  </section>
                )}
                {content.experiences && content.experiences.length > 0 && (
                  <section aria-labelledby="ex" className="mt-6">
                    <h2 id="ex" className="text-xs font-medium text-app-muted">
                      Experience
                    </h2>
                    <ul className="mt-3 flex flex-col gap-5">
                      {content.experiences.map((e) => (
                        <li key={e.experience_id}>
                          <p className="font-medium">
                            {e.title} <span className="font-normal text-app-muted">· {e.company}</span>
                          </p>
                          <ul className="mt-2 list-disc pl-5 flex flex-col gap-1.5 text-app-ink-2">
                            {e.bullets.map((b) => (
                              <li key={b.source_bullet_id}>{b.text}</li>
                            ))}
                          </ul>
                        </li>
                      ))}
                    </ul>
                  </section>
                )}
                {!content.summary && !content.experiences?.length && (
                  <EmptyState icon={FileText} title="No resume content returned" description="Try regenerating." />
                )}
              </Card>
            ) : (
              <Card className="p-6 sm:p-8">
                <div className="flex justify-end">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={async () => {
                      await navigator.clipboard.writeText(result.cover_letter?.text ?? "");
                      toast.success("Cover letter copied.");
                    }}
                  >
                    <Copy className="size-3.5" aria-hidden="true" />
                    Copy
                  </Button>
                </div>
                <div className="mt-2 whitespace-pre-line leading-relaxed text-app-ink-2">{result.cover_letter?.text}</div>
              </Card>
            )}
          </div>

          <aside className="w-full lg:w-80 lg:sticky lg:top-20 flex flex-col gap-4" aria-label="Truth check and actions">
            <Card>
              <CardHeader title="Truth check" />
              <div className="px-5 pb-5">
                {truth === "passed" ? (
                  <p className="flex gap-2">
                    <ShieldCheck className="mt-0.5 size-4 shrink-0 text-app-accent" aria-hidden="true" />
                    Every claim matches your profile.
                  </p>
                ) : (
                  <>
                    <p className="flex gap-2">
                      <AlertTriangle className="mt-0.5 size-4 shrink-0 text-app-danger" aria-hidden="true" />
                      {flagged.length} claim{flagged.length === 1 ? "" : "s"} not found in your profile. Check before
                      using this resume.
                    </p>
                    <ul className="mt-3 flex flex-col gap-2">
                      {flagged.map((c, i) => (
                        <li key={i} className="rounded-app-md bg-app-danger/10 px-3 py-2 text-app-ink">
                          {claimText(c)}
                          {c.reason && <span className="block text-xs text-app-muted">{c.reason}</span>}
                        </li>
                      ))}
                    </ul>
                  </>
                )}
              </div>
            </Card>

            {content.changes_made && content.changes_made.length > 0 && (
              <Card>
                <CardHeader title="What changed" />
                <ul className="px-5 pb-5 flex flex-col gap-2 text-app-ink-2 list-disc pl-10">
                  {content.changes_made.map((c) => (
                    <li key={c}>{c}</li>
                  ))}
                </ul>
              </Card>
            )}

            <Card className="p-5 flex flex-col gap-2">
              <Button variant="secondary" onClick={() => download.mutate()} loading={download.isPending}>
                <Download className="size-4" aria-hidden="true" />
                Download PDF
              </Button>
              <Button onClick={() => prepare.mutate()} loading={prepare.isPending} disabled={truth === "failed"}>
                <Send className="size-4" aria-hidden="true" />
                Use for application
              </Button>
              <p className="text-xs text-app-muted">Version {result.resume_version.version_no}</p>
            </Card>
          </aside>
        </div>
      )}
    </>
  );
}
