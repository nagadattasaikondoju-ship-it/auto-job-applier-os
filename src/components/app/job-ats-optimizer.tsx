"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, ArrowRight, CheckCircle2, Download, HelpCircle, ShieldCheck, Sparkles, TrendingUp } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { api } from "@/lib/api/endpoints";
import type { JobAtsResult, JobFitScore, PrintableResume } from "@/lib/api/types";
import { cn } from "@/lib/utils";
import { Badge, Button, Card, CardHeader, Field, Input, ScoreRing, Select, Textarea } from "./ui";

const VERDICT: Record<JobAtsResult["verdict"], { label: string; tone: "success" | "warning" | "danger" }> = {
  ready: { label: "Ready to apply", tone: "success" },
  minor_edits: { label: "Needs minor edits", tone: "warning" },
  needs_info: { label: "Needs more information", tone: "danger" },
};

/** Paste a job description (or pick a matched job) and get a truthful ATS resume made for it. */
export function JobAtsOptimizer() {
  const queryClient = useQueryClient();
  const matches = useQuery({ queryKey: ["matches", "for-ats"], queryFn: () => api.matches.list({ limit: 30 }) });
  const [jobId, setJobId] = useState("");
  const [title, setTitle] = useState("");
  const [company, setCompany] = useState("");
  const [jd, setJd] = useState("");

  const run = useMutation({
    mutationFn: () =>
      api.ats.optimizeForJob(
        jobId ? { job_id: jobId } : { jd_text: jd.trim(), job_title: title.trim(), company: company.trim() }
      ),
    onSuccess: (r) => {
      void queryClient.invalidateQueries({ queryKey: ["resume-versions"] });
      toast.success(r.ai_used ? "Your ATS resume for this job is ready." : "Saved a reordered version. The AI was busy, so wording is unchanged.");
    },
    onError: (e) => toast.error(e.message),
  });

  const canRun = jobId !== "" || jd.trim().length >= 80;

  return (
    <div className="flex flex-col gap-6">
      <Card className="p-5 sm:p-6">
        <h2 className="flex items-center gap-2 font-medium">
          <Sparkles className="size-4" aria-hidden="true" />
          Make an ATS resume for one job
        </h2>
        <p className="mt-1 text-sm text-app-muted">
          We match your resume to the job&apos;s skills, responsibilities and wording, rewrite weak bullets, and put the most
          relevant experience first. Every line stays true to your resume: skills you don&apos;t have are listed as gaps, never added.
        </p>

        {(matches.data?.items.length ?? 0) > 0 && (
          <Field label="Pick one of your matched jobs" htmlFor="ats-job">
            <Select id="ats-job" value={jobId} onChange={(e) => setJobId(e.target.value)}>
              <option value="">Or paste a job description below</option>
              {matches.data!.items.map((m) => (
                <option key={m.id} value={m.job_id}>
                  {m.title} · {m.company} ({m.match_score}% match)
                </option>
              ))}
            </Select>
          </Field>
        )}

        {jobId === "" && (
          <div className="mt-4 grid gap-4 sm:grid-cols-2">
            <Field label="Job title" htmlFor="ats-title">
              <Input id="ats-title" placeholder="e.g. Product Analyst" value={title} onChange={(e) => setTitle(e.target.value)} />
            </Field>
            <Field label="Company" htmlFor="ats-company">
              <Input id="ats-company" placeholder="e.g. Meesho" value={company} onChange={(e) => setCompany(e.target.value)} />
            </Field>
            <div className="sm:col-span-2">
              <Field label="Job description" htmlFor="ats-jd" hint="Paste the full posting: responsibilities and requirements.">
                <Textarea id="ats-jd" className="min-h-40" value={jd} onChange={(e) => setJd(e.target.value)} />
              </Field>
            </div>
          </div>
        )}

        <div className="mt-5 flex flex-wrap items-center gap-3">
          <Button onClick={() => run.mutate()} loading={run.isPending} disabled={!canRun}>
            <Sparkles className="size-4" aria-hidden="true" />
            Create my ATS resume for this job
          </Button>
          {run.isPending && <span className="text-sm text-app-muted">Analysing the job and rewriting your resume… up to a minute.</span>}
        </div>
      </Card>

      {run.data && <JobAtsReport result={run.data} onRetry={() => run.mutate()} retrying={run.isPending} />}
    </div>
  );
}

function JobAtsReport({ result: r, onRetry, retrying }: { result: JobAtsResult; onRetry: () => void; retrying: boolean }) {
  const verdict = VERDICT[r.verdict];
  const delta = r.after.score - r.before.score;
  const file = `${r.resume.name.replace(/\s+/g, "_")}_${(r.company || r.job_title || "Resume").replace(/\s+/g, "_")}`;

  return (
    <div className="flex flex-col gap-6" aria-live="polite">
      {!r.ai_used && (
        <Card className="flex flex-col gap-3 border-app-dark/30 p-4 sm:flex-row sm:items-center">
          <AlertTriangle className="size-5 shrink-0 text-app-dark" aria-hidden="true" />
          <p className="flex-1 text-sm">
            The AI is busy right now, so this version only reorders your skills and bullets for the job. Try again in a minute for full rewrites.
          </p>
          <Button variant="secondary" size="sm" onClick={onRetry} loading={retrying}>
            Try again
          </Button>
        </Card>
      )}

      <div className="grid gap-4 lg:grid-cols-[1fr_auto_1fr] lg:items-stretch">
        <ScoreCard title="ATS score before" score={r.before} />
        <div className="hidden items-center justify-center lg:flex" aria-hidden="true">
          <ArrowRight className="size-5 text-app-muted" />
        </div>
        <ScoreCard
          title="ATS score after"
          score={r.after}
          badge={delta !== 0 ? <span className={cn("font-mono text-sm", delta > 0 ? "text-app-ink" : "text-app-danger")}>{delta > 0 ? `+${delta}` : delta}</span> : null}
        />
      </div>

      <Card className="flex flex-col gap-3 p-5 sm:flex-row sm:items-center">
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <Badge tone={verdict.tone}>{verdict.label}</Badge>
            {r.truth_check_status === "passed" && (
              <span className="flex items-center gap-1 text-sm text-app-ink-2">
                <ShieldCheck className="size-4 text-app-accent" aria-hidden="true" />
                Every line is backed by your resume
              </span>
            )}
          </div>
          <p className="mt-2 text-app-ink">{r.final_recommendation}</p>
        </div>
        <div className="flex gap-2">
          <Button variant="secondary" onClick={() => api.documents.downloadResumePdf(r.resume_version_id, `${file}.pdf`)}>
            <Download className="size-4" aria-hidden="true" />
            PDF
          </Button>
          <Button variant="secondary" onClick={() => api.documents.downloadResumeDocx(r.resume_version_id, `${file}.docx`)}>
            <Download className="size-4" aria-hidden="true" />
            DOCX
          </Button>
        </div>
      </Card>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_22rem]">
        <ResumePreview doc={r.resume} />

        <div className="flex flex-col gap-6">
          <Card as="section" aria-labelledby="kw-title">
            <CardHeader id="kw-title" title="Keyword match" description={`${r.keywords.coverage}% of the job's skills covered`} />
            <div className="flex flex-col gap-4 px-5 pb-5">
              <KeywordGroup label="Matched" items={r.keywords.matched} tone="success" />
              <KeywordGroup label="Partly matched" items={r.keywords.partial} tone="warning" />
              <KeywordGroup label="Missing: can't be added truthfully" items={r.keywords.missing} tone="danger" />
            </div>
          </Card>

          {(r.job_analysis.title_variants.length > 0 || r.job_analysis.soft_skills.length > 0 || r.job_analysis.seniority) && (
            <Card as="section" aria-labelledby="jd-title">
              <CardHeader id="jd-title" title="What this job wants" />
              <dl className="flex flex-col gap-3 px-5 pb-5 text-sm">
                {r.job_analysis.title_variants.length > 0 && (
                  <div>
                    <dt className="text-app-muted">Also searched as</dt>
                    <dd>{r.job_analysis.title_variants.join(", ")}</dd>
                  </div>
                )}
                {r.job_analysis.seniority && (
                  <div>
                    <dt className="text-app-muted">Seniority</dt>
                    <dd>{r.job_analysis.seniority}</dd>
                  </div>
                )}
                {r.job_analysis.soft_skills.length > 0 && (
                  <div>
                    <dt className="text-app-muted">Soft skills</dt>
                    <dd>{r.job_analysis.soft_skills.slice(0, 10).join(", ")}</dd>
                  </div>
                )}
                {r.job_analysis.must_have.length > 0 && (
                  <div>
                    <dt className="text-app-muted">Must-haves</dt>
                    <dd>
                      <ul className="list-disc pl-4">
                        {r.job_analysis.must_have.slice(0, 6).map((m) => (
                          <li key={m}>{m}</li>
                        ))}
                      </ul>
                    </dd>
                  </div>
                )}
              </dl>
            </Card>
          )}
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <ListCard icon={TrendingUp} title="Changes made" items={r.changes_made} empty="No changes were needed." />
        <ListCard
          icon={HelpCircle}
          title="Tell us more to improve it"
          items={r.missing_information}
          empty="Nothing else needed."
          hint="Add these on your Profile, then run this again."
        />
        <ListCard
          icon={AlertTriangle}
          title="Development recommendations"
          items={r.development_recommendations}
          empty="No skill gaps for this job."
        />
      </div>

      {(r.guard.reverted_bullets.length > 0 || r.guard.removed_skills.length > 0 || r.guard.rejected_summary) && (
        <Card as="section" aria-labelledby="guard-title">
          <CardHeader
            id="guard-title"
            title="What we kept honest"
            description="Suggestions we didn't use because your resume doesn't back them up."
          />
          <ul className="flex flex-col gap-3 px-5 pb-5 text-sm">
            {r.guard.rejected_summary && (
              <li>
                <p className="text-app-muted">Summary suggestion (kept yours):</p>
                <p className="text-app-ink-2 line-through decoration-app-line">{r.guard.rejected_summary}</p>
              </li>
            )}
            {r.guard.reverted_bullets.map((b) => (
              <li key={b.rejected}>
                <p className="text-app-ink-2 line-through decoration-app-line">{b.rejected}</p>
                <p className="text-app-muted">Kept: {b.original}</p>
              </li>
            ))}
            {r.guard.removed_skills.length > 0 && (
              <li className="text-app-ink-2">Skills not added (not in your resume): {r.guard.removed_skills.join(", ")}</li>
            )}
          </ul>
        </Card>
      )}
    </div>
  );
}

function ScoreCard({ title, score, badge }: { title: string; score: JobFitScore; badge?: React.ReactNode }) {
  return (
    <Card className="p-5">
      <div className="flex items-center gap-4">
        <ScoreRing score={score.score} size={72} />
        <div>
          <p className="flex items-center gap-2 font-medium">
            {title} {badge}
          </p>
          <p className="text-sm text-app-muted">{score.reason}</p>
        </div>
      </div>
      <ul className="mt-4 flex flex-col gap-2" aria-label={`${title} by category`}>
        {score.categories.map((c) => (
          <li key={c.key}>
            <div className="flex justify-between text-sm">
              <span className="text-app-ink-2">{c.label}</span>
              <span className="font-mono">
                {c.score}/{c.max}
              </span>
            </div>
            <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-app-panel" aria-hidden="true">
              <div
                className={cn("h-full rounded-full", c.score / c.max >= 0.8 ? "bg-app-accent" : c.score / c.max >= 0.5 ? "bg-app-dark" : "bg-app-danger")}
                style={{ width: `${(c.score / c.max) * 100}%` }}
              />
            </div>
          </li>
        ))}
      </ul>
    </Card>
  );
}

function KeywordGroup({ label, items, tone }: { label: string; items: string[]; tone: "success" | "warning" | "danger" }) {
  if (items.length === 0) return null;
  return (
    <div>
      <p className="text-xs text-app-muted">{label}</p>
      <div className="mt-1.5 flex flex-wrap gap-1.5">
        {items.map((k) => (
          <Badge key={k} tone={tone}>
            {k}
          </Badge>
        ))}
      </div>
    </div>
  );
}

function ListCard({
  icon: Icon,
  title,
  items,
  empty,
  hint,
}: {
  icon: typeof CheckCircle2;
  title: string;
  items: string[];
  empty: string;
  hint?: string;
}) {
  return (
    <Card className="p-5">
      <h3 className="flex items-center gap-2 font-medium">
        <Icon className="size-4" aria-hidden="true" />
        {title}
      </h3>
      {items.length === 0 ? (
        <p className="mt-2 text-sm text-app-muted">{empty}</p>
      ) : (
        <ul className="mt-2 flex list-disc flex-col gap-1.5 pl-4 text-sm text-app-ink-2">
          {items.map((i) => (
            <li key={i}>{i}</li>
          ))}
        </ul>
      )}
      {hint && items.length > 0 && <p className="mt-3 text-xs text-app-muted">{hint}</p>}
    </Card>
  );
}

/** The optimized resume as it will print: single column, standard sections. */
function ResumePreview({ doc }: { doc: PrintableResume }) {
  return (
    <Card as="article" aria-label="Optimized resume" className="p-6 sm:p-8">
      <h2 className="text-xl font-semibold text-app-ink">{doc.name}</h2>
      {doc.headline && <p className="text-app-ink-2">{doc.headline}</p>}
      <p className="mt-1 break-words text-sm text-app-muted">{doc.contact.join(" | ")}</p>

      <Section title="Professional Summary">
        <p>{doc.summary}</p>
      </Section>
      <Section title="Core Skills">
        <p>{doc.skills.join(", ")}</p>
      </Section>
      <Section title="Professional Experience">
        {doc.experiences.map((e) => (
          <div key={`${e.title}-${e.company}-${e.dates}`} className="mt-3 first:mt-0">
            <p className="font-medium text-app-ink">{e.title}</p>
            <p className="text-sm text-app-muted">{[e.company, e.location, e.dates].filter(Boolean).join(" | ")}</p>
            <ul className="mt-1 list-disc pl-5">
              {e.bullets.map((b) => (
                <li key={b}>{b}</li>
              ))}
            </ul>
          </div>
        ))}
      </Section>
      {doc.projects.length > 0 && (
        <Section title="Projects">
          {doc.projects.map((p) => (
            <p key={p.title}>
              <span className="font-medium text-app-ink">{p.title}</span>
              {p.description && ` – ${p.description}`}
            </p>
          ))}
        </Section>
      )}
      {doc.educations.length > 0 && (
        <Section title="Education">
          {doc.educations.map((e) => (
            <p key={`${e.line}-${e.institution}`}>
              <span className="text-app-ink">{e.line}</span>
              <span className="text-app-muted"> · {[e.institution, e.dates, e.grade].filter(Boolean).join(" | ")}</span>
            </p>
          ))}
        </Section>
      )}
      {doc.certifications.length > 0 && (
        <Section title="Certifications">
          <ul className="list-disc pl-5">
            {doc.certifications.map((c) => (
              <li key={c}>{c}</li>
            ))}
          </ul>
        </Section>
      )}
    </Card>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="mt-5">
      <h3 className="border-b border-app-border pb-1 text-xs font-semibold tracking-wider text-app-ink uppercase">{title}</h3>
      <div className="mt-2 text-sm leading-relaxed text-app-ink-2">{children}</div>
    </section>
  );
}
