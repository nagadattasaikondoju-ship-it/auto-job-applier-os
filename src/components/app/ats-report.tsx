"use client";

import { AlertCircle, AlertTriangle, CheckCircle2, Info, Lock, Sparkles } from "lucide-react";
import type { AtsReport, BulletSuggestion, IssueSeverity } from "@/lib/api/types";
import { cn } from "@/lib/utils";
import { Badge, Card, CardHeader, Checkbox, ScoreRing } from "./ui";

const GRADE_LABEL: Record<AtsReport["grade"], string> = {
  excellent: "Excellent — ready to apply",
  good: "Good — a few quick fixes",
  fair: "Fair — fix the high-priority items",
  needs_work: "Needs work before you apply",
};

const SEVERITY: Record<IssueSeverity, { icon: typeof AlertCircle; label: string; className: string }> = {
  high: { icon: AlertCircle, label: "High priority", className: "text-app-danger" },
  medium: { icon: AlertTriangle, label: "Medium", className: "text-app-dark" },
  low: { icon: Info, label: "Low", className: "text-app-subtle" },
};

export function AtsScoreSummary({ report, previous }: { report: AtsReport; previous?: number | null }) {
  const delta = previous != null ? report.score - previous : null;
  return (
    <Card className="p-5 sm:p-6">
      <div className="flex flex-col gap-6 sm:flex-row sm:items-center">
        <div className="flex items-center gap-4">
          <ScoreRing score={report.score} size={96} />
          <div>
            <p className="text-xs text-app-muted">ATS score</p>
            <p className="text-lg font-medium text-app-ink">{GRADE_LABEL[report.grade]}</p>
            {delta != null && delta !== 0 && (
              <p className={cn("text-sm", delta > 0 ? "text-app-ink" : "text-app-danger")}>
                <span className="font-mono">{delta > 0 ? `+${delta}` : delta}</span> since your last version
              </p>
            )}
            <p className="text-xs text-app-subtle">
              {report.stats.word_count} words · {report.stats.bullet_count} bullets
            </p>
          </div>
        </div>
        <ul className="grid flex-1 gap-2.5 sm:grid-cols-2" aria-label="Score by category">
          {report.categories.map((c) => (
            <li key={c.key}>
              <div className="flex justify-between text-sm">
                <span className="text-app-ink-2">{c.label}</span>
                <span className="font-mono text-app-ink">
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
      </div>
    </Card>
  );
}

export function AtsIssues({ report }: { report: AtsReport }) {
  if (report.issues.length === 0) {
    return (
      <Card className="p-5 flex gap-3">
        <CheckCircle2 className="size-5 text-app-accent" aria-hidden="true" />
        <p>No issues found. Your resume is in great shape for ATS.</p>
      </Card>
    );
  }
  return (
    <Card as="section" aria-labelledby="ats-issues">
      <CardHeader id="ats-issues" title={`What to fix (${report.issues.length})`} description="Most important first." />
      <ul className="divide-y divide-app-border border-t border-app-border">
        {report.issues.map((issue, i) => {
          const sev = SEVERITY[issue.severity];
          const Icon = sev.icon;
          return (
            <li key={i} className="flex gap-3 px-5 py-4">
              <Icon className={cn("mt-0.5 size-4 shrink-0", sev.className)} aria-hidden="true" />
              <div className="min-w-0">
                <p className="font-medium text-app-ink">
                  {issue.title} <span className="sr-only">({sev.label})</span>
                </p>
                <p className="text-app-muted">{issue.detail}</p>
                <p className="mt-1 text-app-ink-2">
                  <span className="font-medium">Fix: </span>
                  {issue.fix}
                </p>
              </div>
            </li>
          );
        })}
      </ul>
    </Card>
  );
}

export function AtsKeywords({ report }: { report: AtsReport }) {
  const { matched, missing, source } = report.keywords;
  return (
    <Card as="section" aria-labelledby="ats-keywords" className="p-5">
      <h2 id="ats-keywords" className="font-medium">
        {source === "job_description" ? "Keywords from the job" : "Skills we recognised"}
      </h2>
      {source === "job_description" && missing.length > 0 && (
        <div className="mt-3">
          <p className="text-xs text-app-muted">Missing — add only the ones you genuinely have</p>
          <div className="mt-1.5 flex flex-wrap gap-1.5">
            {missing.map((k) => (
              <Badge key={k} tone="danger">
                {k}
              </Badge>
            ))}
          </div>
        </div>
      )}
      <div className="mt-3">
        {source === "job_description" && <p className="text-xs text-app-muted">Already in your resume</p>}
        <div className="mt-1.5 flex flex-wrap gap-1.5">
          {matched.length === 0 && <p className="text-app-muted">None yet.</p>}
          {matched.map((k) => (
            <Badge key={k} tone="success">
              {k}
            </Badge>
          ))}
        </div>
      </div>
    </Card>
  );
}

/** AI bullet rewrites with accept checkboxes. Suggestions that added facts arrive pre-blocked. */
export function BulletSuggestions({
  suggestions,
  aiAvailable,
  accepted,
  onToggle,
  onEdit,
}: {
  suggestions: BulletSuggestion[];
  aiAvailable: boolean;
  accepted: Record<string, boolean>;
  onToggle: (bulletId: string, on: boolean) => void;
  onEdit: (bulletId: string, text: string) => void;
}) {
  if (suggestions.length === 0) {
    return <p className="text-app-muted">Your bullets already start with action verbs and show results. Nice.</p>;
  }
  return (
    <ul className="flex flex-col gap-3">
      {!aiAvailable && (
        <li className="flex gap-2 rounded-app-lg bg-app-surface px-4 py-3">
          <Sparkles className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
          <span>
            AI rewriting isn&apos;t configured on this server (no Gemini key), so here are the bullets to improve with
            tips. You can edit them yourself below.
          </span>
        </li>
      )}
      {suggestions.map((s) => {
        const key = s.bullet_id;
        const on = Boolean(accepted[key]);
        return (
          <li key={key} className="rounded-app-lg border border-app-border bg-app-card p-4">
            <p className="text-xs text-app-muted">Before</p>
            <p className="text-app-ink-2 line-through decoration-app-subtle">{s.original}</p>
            {s.blocked_reason ? (
              <p className="mt-2 flex gap-2 text-app-ink">
                <Lock className="mt-0.5 size-4 shrink-0 text-app-danger" aria-hidden="true" />
                Suggestion blocked: it {s.blocked_reason}. We never add facts you didn&apos;t write.
              </p>
            ) : (
              <>
                <p className="mt-2 text-xs text-app-muted">After {s.rewritten ? "(edit if you like)" : "(write your improved version)"}</p>
                <textarea
                  aria-label={`Improved version of: ${s.original}`}
                  defaultValue={s.rewritten ?? s.original}
                  onChange={(e) => onEdit(key, e.target.value)}
                  className="mt-1 w-full rounded-app-md border border-app-border bg-app-bg px-3 py-2 text-sm text-app-ink outline-none focus-visible:border-app-accent focus-visible:ring-2 focus-visible:ring-app-accent/20"
                  rows={2}
                />
                <p className="mt-1 text-xs text-app-muted">{s.reason}</p>
                <div className="mt-2">
                  <Checkbox checked={on} onChange={(v) => onToggle(key, v)} label="Use this version" />
                </div>
              </>
            )}
          </li>
        );
      })}
    </ul>
  );
}
