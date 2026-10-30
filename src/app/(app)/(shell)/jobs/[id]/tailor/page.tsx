"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, ArrowLeft, Columns2, Copy, Download, FileText, Send, ShieldCheck, Sparkles } from "lucide-react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";
import { AtsKeywords } from "@/components/app/ats-report";
import { Badge, Button, Card, CardHeader, Checkbox, EmptyState, ErrorState, ScoreRing, Select, SERVER_WAKING_HINT, Skeleton, Spinner, Tabs } from "@/components/app/ui";
import { api } from "@/lib/api/endpoints";
import type { CoverLetterDoc, Experience, FlaggedClaim, ResumeVersion } from "@/lib/api/types";

type Tone = "professional" | "friendly" | "direct";

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

function bulletText(b: unknown) {
  return typeof b === "string" ? b : ((b as { text?: string })?.text ?? "");
}

export default function TailorPage() {
  const { id } = useParams<{ id: string }>();
  const queryClient = useQueryClient();
  const job = useQuery({ queryKey: ["job", id], queryFn: () => api.jobs.get(id) });
  const existing = useQuery({ queryKey: ["job-documents", id], queryFn: () => api.jobs.documents(id) });
  const [includeCoverLetter, setIncludeCoverLetter] = useState(true);
  const [tone, setTone] = useState<Tone>("professional");

  const tailor = useMutation({
    mutationFn: () => api.jobs.tailor(id, includeCoverLetter, tone),
    onSuccess: (r) => {
      queryClient.setQueryData(["job-documents", id], { resume_version: r.resume_version, cover_letter: r.cover_letter });
      void queryClient.invalidateQueries({ queryKey: ["credits"] });
      void queryClient.invalidateQueries({ queryKey: ["resume-versions"] });
    },
    onError: (e) => toast.error(e.message),
  });

  const resume = existing.data?.resume_version ?? null;

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

      {existing.isPending ? (
        <Spinner label="Loading your documents" slowHint={SERVER_WAKING_HINT} />
      ) : existing.isError ? (
        <ErrorState error={existing.error} onRetry={() => existing.refetch()} />
      ) : !resume ? (
        <Card className="p-6">
          {tailor.isPending ? (
            <div role="status" className="flex flex-col gap-4">
              <p className="font-medium">Writing your tailored documents…</p>
              <ol className="flex flex-col gap-2 text-app-muted">
                <li>Reading the job description</li>
                <li>Picking your most relevant experience</li>
                <li>Rewriting bullets using only facts from your profile</li>
                <li>Running the truth check and ATS score</li>
              </ol>
              <Skeleton className="h-2 w-full" />
            </div>
          ) : tailor.isError ? (
            <ErrorState error={tailor.error} onRetry={() => tailor.mutate()} />
          ) : (
            <div className="flex max-w-xl flex-col gap-5">
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
              <Checkbox checked={includeCoverLetter} onChange={setIncludeCoverLetter} label="Also write a cover letter" description="Uses one extra AI credit." />
              {includeCoverLetter && <ToneSelect value={tone} onChange={setTone} />}
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
        <TailoredView
          jobId={id}
          resume={resume}
          coverLetter={existing.data?.cover_letter ?? null}
          onRegenerate={() => tailor.mutate()}
          regenerating={tailor.isPending}
        />
      )}
    </>
  );
}

function ToneSelect({ value, onChange }: { value: Tone; onChange: (t: Tone) => void }) {
  return (
    <label className="flex max-w-xs flex-col gap-1.5">
      <span className="text-sm font-medium">Cover letter tone</span>
      <Select value={value} onChange={(e) => onChange(e.target.value as Tone)}>
        <option value="professional">Professional</option>
        <option value="friendly">Friendly</option>
        <option value="direct">Direct</option>
      </Select>
    </label>
  );
}

function TailoredView({
  jobId,
  resume,
  coverLetter,
  onRegenerate,
  regenerating,
}: {
  jobId: string;
  resume: ResumeVersion;
  coverLetter: CoverLetterDoc | null;
  onRegenerate: () => void;
  regenerating: boolean;
}) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [tab, setTab] = useState<"resume" | "compare" | "cover">("resume");
  const [tone, setTone] = useState<Tone>("professional");
  const profile = useQuery({ queryKey: ["profile"], queryFn: api.profile.get, enabled: tab === "compare" });

  const content = (resume.content ?? {}) as TailoredContent;
  const flagged = resume.flagged_claims ?? [];
  const truth = resume.truth_check_status;

  const cover = useMutation({
    mutationFn: () => api.jobs.coverLetter(jobId, tone),
    onSuccess: (cl) => {
      queryClient.setQueryData(["job-documents", jobId], { resume_version: resume, cover_letter: cl });
      setTab("cover");
      toast.success("New cover letter written.");
    },
    onError: (e) => toast.error(e.message),
  });

  const prepare = useMutation({
    mutationFn: () => api.applications.create(jobId, "extension"),
    onSuccess: (r) => {
      void queryClient.invalidateQueries({ queryKey: ["applications"] });
      router.push(`/applications/${r.id}`);
    },
    onError: (e) => toast.error(e.message),
  });

  const download = (fn: () => Promise<void>) => fn().catch((e: Error) => toast.error(e.message));
  const masterById = new Map<string, Experience>((profile.data?.experiences ?? []).map((e) => [e.id, e]));

  return (
    <div className="flex flex-col gap-6 lg:flex-row lg:items-start">
      <div className="min-w-0 flex-1">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <Tabs
            label="Documents"
            value={tab}
            onChange={setTab}
            items={[
              { value: "resume", label: "Tailored resume" },
              { value: "compare", label: "Compare with master" },
              { value: "cover", label: "Cover letter" },
            ]}
          />
          <Button variant="secondary" size="sm" onClick={onRegenerate} loading={regenerating}>
            Regenerate resume
          </Button>
        </div>

        {tab === "resume" && (
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
                      <ul className="mt-2 flex list-disc flex-col gap-1.5 pl-5 text-app-ink-2">
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
        )}

        {tab === "compare" && (
          <Card className="p-5">
            <p className="mb-4 flex items-center gap-2 text-app-muted">
              <Columns2 className="size-4" aria-hidden="true" />
              Your master resume on the left, the version tailored for this job on the right.
            </p>
            {profile.isPending ? (
              <Spinner />
            ) : (
              <div className="flex flex-col gap-6">
                {(content.experiences ?? []).map((e) => {
                  const master = masterById.get(e.experience_id);
                  return (
                    <div key={e.experience_id}>
                      <p className="font-medium">
                        {e.title} <span className="font-normal text-app-muted">· {e.company}</span>
                      </p>
                      <div className="mt-2 grid gap-3 md:grid-cols-2">
                        <ul className="list-disc space-y-1.5 rounded-app-lg bg-app-bg p-4 pl-8 text-app-muted">
                          {(master?.bullets ?? []).map((b, i) => (
                            <li key={i}>{bulletText(b)}</li>
                          ))}
                          {!master && <li>Not in your current profile.</li>}
                        </ul>
                        <ul className="list-disc space-y-1.5 rounded-app-lg border border-app-accent/40 bg-app-card p-4 pl-8 text-app-ink">
                          {e.bullets.map((b) => (
                            <li key={b.source_bullet_id}>{b.text}</li>
                          ))}
                        </ul>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </Card>
        )}

        {tab === "cover" && (
          <Card className="p-6 sm:p-8">
            <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
              <ToneSelect value={tone} onChange={setTone} />
              <div className="flex gap-2">
                <Button variant="secondary" size="sm" onClick={() => cover.mutate()} loading={cover.isPending}>
                  {coverLetter ? "Rewrite in this tone" : "Write cover letter"}
                </Button>
                {coverLetter && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={async () => {
                      await navigator.clipboard.writeText(coverLetter.text);
                      toast.success("Cover letter copied.");
                    }}
                  >
                    <Copy className="size-3.5" aria-hidden="true" />
                    Copy
                  </Button>
                )}
              </div>
            </div>
            {coverLetter ? (
              <div className="whitespace-pre-line leading-relaxed text-app-ink-2">{coverLetter.text}</div>
            ) : (
              <p className="text-app-muted">No cover letter yet.</p>
            )}
          </Card>
        )}
      </div>

      <aside className="flex w-full flex-col gap-4 lg:sticky lg:top-20 lg:w-80" aria-label="Score, truth check and actions">
        {resume.ats && (
          <Card className="p-5">
            <div className="flex items-center gap-4">
              <ScoreRing score={resume.ats.score} size={72} />
              <div>
                <p className="font-medium">ATS score for this job</p>
                <p className="text-app-muted">
                  {resume.ats.keywords.missing.length
                    ? `${resume.ats.keywords.missing.length} job keyword(s) missing`
                    : "Covers the job's keywords"}
                </p>
              </div>
            </div>
          </Card>
        )}
        {resume.ats && resume.ats.keywords.source === "job_description" && <AtsKeywords report={resume.ats} />}

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
                  {flagged.length} claim{flagged.length === 1 ? "" : "s"} not found in your profile. Check before using this resume.
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
            <ul className="flex list-disc flex-col gap-2 px-5 pb-5 pl-10 text-app-ink-2">
              {content.changes_made.map((c) => (
                <li key={c}>{c}</li>
              ))}
            </ul>
          </Card>
        )}

        <Card className="flex flex-col gap-2 p-5">
          <div className="grid grid-cols-2 gap-2">
            <Button variant="secondary" onClick={() => download(() => api.documents.downloadResumePdf(resume.id))}>
              <Download className="size-4" aria-hidden="true" />
              PDF
            </Button>
            <Button variant="secondary" onClick={() => download(() => api.documents.downloadResumeDocx(resume.id))}>
              <FileText className="size-4" aria-hidden="true" />
              DOCX
            </Button>
          </div>
          {coverLetter && (
            <Button variant="secondary" onClick={() => download(() => api.documents.downloadCoverLetterPdf(coverLetter.id))}>
              <Download className="size-4" aria-hidden="true" />
              Cover letter PDF
            </Button>
          )}
          <Button onClick={() => prepare.mutate()} loading={prepare.isPending} disabled={truth === "failed"}>
            <Send className="size-4" aria-hidden="true" />
            Use for application
          </Button>
          <p className="text-xs text-app-muted">Version {resume.version_no}</p>
        </Card>
      </aside>
    </div>
  );
}
