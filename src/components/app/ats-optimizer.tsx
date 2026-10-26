"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Download, FileText, Sparkles, Wand2 } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { api } from "@/lib/api/endpoints";
import type { ApplyAtsResult, AtsReport, RewriteResult } from "@/lib/api/types";
import { AtsIssues, AtsKeywords, AtsScoreSummary, BulletSuggestions } from "./ats-report";
import { Button, Card, CardHeader, Checkbox } from "./ui";

/**
 * Scan → fix → save loop shared by onboarding and the Resume & ATS page.
 * Improvements are applied to the master profile; every new version can be downloaded.
 */
export function AtsOptimizer({
  report,
  jobId,
  jdText,
  onSaved,
  compact = false,
}: {
  report: AtsReport;
  jobId?: string;
  jdText?: string;
  onSaved?: (result: ApplyAtsResult) => void;
  compact?: boolean;
}) {
  const queryClient = useQueryClient();
  const [current, setCurrent] = useState(report);
  const [previousScore, setPreviousScore] = useState<number | null>(null);
  const [rewrite, setRewrite] = useState<RewriteResult | null>(null);
  const [accepted, setAccepted] = useState<Record<string, boolean>>({});
  const [edits, setEdits] = useState<Record<string, string>>({});
  const [skillsToAdd, setSkillsToAdd] = useState<Record<string, boolean>>({});
  const [saved, setSaved] = useState<ApplyAtsResult | null>(null);

  const suggest = useMutation({
    mutationFn: () => api.ats.rewriteBullets({ job_id: jobId, jd_text: jdText }),
    onSuccess: (r) => {
      setRewrite(r);
      // Pre-accept AI rewrites that passed the fact check
      setAccepted(Object.fromEntries(r.suggestions.filter((s) => s.rewritten && !s.blocked_reason).map((s) => [s.bullet_id, true])));
    },
    onError: (e) => toast.error(e.message),
  });

  const apply = useMutation({
    mutationFn: () => {
      const updates = (rewrite?.suggestions ?? [])
        .filter((s) => accepted[s.bullet_id] && !s.blocked_reason)
        .map((s) => ({
          experience_id: s.experience_id,
          bullet_id: s.bullet_id,
          text: (edits[s.bullet_id] ?? s.rewritten ?? s.original).trim(),
        }))
        .filter((u) => u.text.length > 0);
      return api.ats.apply({
        bullet_updates: updates,
        add_skills: Object.entries(skillsToAdd).filter(([, v]) => v).map(([k]) => k),
      });
    },
    onSuccess: (r) => {
      setPreviousScore(current.score);
      setSaved(r);
      setRewrite(null);
      setSkillsToAdd({});
      void queryClient.invalidateQueries({ queryKey: ["profile"] });
      void queryClient.invalidateQueries({ queryKey: ["resume-versions"] });
      if (r.rejected.length) toast.warning(`${r.rejected.length} change(s) were rejected because they added new facts.`);
      toast.success(r.changes.length ? `Saved version ${r.version_no} with ${r.changes.length} improvement(s).` : `Saved version ${r.version_no}.`);
      // Re-scan against the same job (if any) so the score reflects the saved profile
      api.ats
        .scan({ use_profile: true, job_id: jobId, jd_text: jdText })
        .then(setCurrent)
        .catch(() => setCurrent(r.ats));
      onSaved?.(r);
    },
    onError: (e) => toast.error(e.message),
  });

  const missing = current.keywords.source === "job_description" ? current.keywords.missing : [];
  const acceptedCount =
    Object.values(accepted).filter(Boolean).length + Object.values(skillsToAdd).filter(Boolean).length;

  return (
    <div className="flex flex-col gap-5">
      <AtsScoreSummary report={current} previous={previousScore} />

      <div className={compact ? "flex flex-col gap-5" : "grid gap-5 lg:grid-cols-3"}>
        <div className={compact ? "flex flex-col gap-5" : "lg:col-span-2 flex flex-col gap-5"}>
          <Card as="section" aria-labelledby="improve-bullets">
            <CardHeader
              id="improve-bullets"
              title="Improve your bullet points"
              description="Stronger verbs and clearer impact, using only facts you wrote."
              action={
                <Button variant="secondary" size="sm" onClick={() => suggest.mutate()} loading={suggest.isPending}>
                  <Wand2 className="size-3.5" aria-hidden="true" />
                  {rewrite ? "Suggest again" : "Suggest improvements"}
                </Button>
              }
            />
            <div className="px-5 pb-5">
              {rewrite ? (
                <BulletSuggestions
                  suggestions={rewrite.suggestions}
                  aiAvailable={rewrite.ai_available}
                  accepted={accepted}
                  onToggle={(id, on) => setAccepted((a) => ({ ...a, [id]: on }))}
                  onEdit={(id, text) => setEdits((e) => ({ ...e, [id]: text }))}
                />
              ) : (
                <p className="text-app-muted">
                  {current.weak_bullets.length
                    ? `${current.weak_bullets.length} bullet(s) could be stronger. Click “Suggest improvements”.`
                    : "Click “Suggest improvements” to review your bullets."}
                </p>
              )}
            </div>
          </Card>

          {missing.length > 0 && (
            <Card as="section" aria-labelledby="add-skills" className="p-5">
              <h2 id="add-skills" className="font-medium">
                Add missing skills you actually have
              </h2>
              <p className="text-app-muted">Only tick skills you can talk about in an interview.</p>
              <div className="mt-3 grid gap-2 sm:grid-cols-2">
                {missing.map((k) => (
                  <Checkbox
                    key={k}
                    checked={Boolean(skillsToAdd[k])}
                    onChange={(v) => setSkillsToAdd((s) => ({ ...s, [k]: v }))}
                    label={k}
                  />
                ))}
              </div>
            </Card>
          )}

          <div className="flex flex-wrap items-center gap-3">
            <Button onClick={() => apply.mutate()} loading={apply.isPending} disabled={acceptedCount === 0 && !!saved}>
              <Sparkles className="size-4" aria-hidden="true" />
              {acceptedCount ? `Apply ${acceptedCount} change(s) and save version` : "Save optimized version"}
            </Button>
            {saved && (
              <>
                <Button
                  variant="secondary"
                  onClick={() =>
                    api.documents.downloadResumePdf(saved.resume_version_id).catch((e: Error) => toast.error(e.message))
                  }
                >
                  <Download className="size-4" aria-hidden="true" />
                  PDF
                </Button>
                <Button
                  variant="secondary"
                  onClick={() =>
                    api.documents.downloadResumeDocx(saved.resume_version_id).catch((e: Error) => toast.error(e.message))
                  }
                >
                  <FileText className="size-4" aria-hidden="true" />
                  DOCX
                </Button>
              </>
            )}
          </div>
        </div>

        <div className="flex flex-col gap-5">
          <AtsKeywords report={current} />
          {!compact && <AtsIssues report={current} />}
        </div>
      </div>
      {compact && <AtsIssues report={current} />}
    </div>
  );
}
