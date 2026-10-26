"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Download, FileText, Target, Upload } from "lucide-react";
import Link from "next/link";
import { useRef, useState } from "react";
import { toast } from "sonner";
import { AtsOptimizer } from "@/components/app/ats-optimizer";
import { JobAtsOptimizer } from "@/components/app/job-ats-optimizer";
import { Badge, Button, ButtonLink, Card, CardHeader, EmptyState, ErrorState, PageHeader, Spinner, Tabs } from "@/components/app/ui";
import { ApiError } from "@/lib/api/client";
import { api } from "@/lib/api/endpoints";
import { formatDate } from "@/lib/format";

type Mode = "check" | "job";

export default function ResumePage() {
  const queryClient = useQueryClient();
  const fileRef = useRef<HTMLInputElement>(null);
  const [mode, setMode] = useState<Mode>("check");
  const [scanKey, setScanKey] = useState(0);

  const scan = useQuery({
    queryKey: ["ats", "scan", scanKey],
    queryFn: () => api.ats.scan({ use_profile: true }),
    retry: false,
  });
  const versions = useQuery({ queryKey: ["resume-versions"], queryFn: api.documents.resumeVersions });

  const reupload = useMutation({
    mutationFn: async (file: File) => {
      const r = await api.resumes.uploadFile(file);
      await api.resumes.confirm(r.id);
      return r;
    },
    onSuccess: () => {
      toast.success("New resume uploaded and your profile updated.");
      void queryClient.invalidateQueries({ queryKey: ["profile"] });
      setScanKey((k) => k + 1);
    },
    onError: (e) => toast.error(e.message),
  });

  const noProfile = scan.isError && scan.error instanceof ApiError && scan.error.status === 404;

  return (
    <>
      <PageHeader
        title="Resume & ATS"
        description="See how applicant tracking systems read your resume, fix what's holding it back, and download ATS-friendly versions."
        actions={
          <>
            <Button variant="secondary" onClick={() => fileRef.current?.click()} loading={reupload.isPending}>
              <Upload className="size-4" aria-hidden="true" />
              Upload new resume
            </Button>
            <input
              ref={fileRef}
              type="file"
              accept=".pdf,.docx,.txt"
              className="sr-only"
              aria-label="Upload a new resume"
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) reupload.mutate(f);
                e.target.value = "";
              }}
            />
          </>
        }
      />

      {noProfile ? (
        <Card>
          <EmptyState
            icon={FileText}
            title="Upload your resume to get your ATS score"
            description="We'll read it, build your profile and show you exactly what to fix."
            action={<ButtonLink href="/onboarding">Upload resume</ButtonLink>}
          />
        </Card>
      ) : (
        <>
          <div className="mb-6">
            <Tabs
              label="Resume tools"
              value={mode}
              onChange={setMode}
              items={[
                { value: "check", label: "ATS check & fixes" },
                { value: "job", label: "Optimize for a job" },
              ]}
            />
          </div>

          {mode === "job" ? (
            <JobAtsOptimizer />
          ) : (
            <>
              <Card className="mb-6 flex flex-col gap-3 p-5 sm:flex-row sm:items-center">
                <p className="flex flex-1 items-center gap-2 text-sm text-app-ink-2">
                  <Target className="size-4 shrink-0" aria-hidden="true" />
                  Your resume scored against ATS best practice. To tailor it to a specific job, use “Optimize for a job”.
                </p>
                <Button variant="secondary" onClick={() => setScanKey((k) => k + 1)} loading={scan.isFetching}>
                  Re-scan
                </Button>
              </Card>

          {scan.isPending ? (
            <Spinner label="Scoring your resume" />
          ) : scan.isError ? (
            <ErrorState error={scan.error} onRetry={() => scan.refetch()} />
          ) : (
            <AtsOptimizer key={`${scanKey}-${scan.dataUpdatedAt}`} report={scan.data} />
          )}
            </>
          )}

          <Card as="section" aria-labelledby="versions-title" className="mt-8">
            <CardHeader id="versions-title" title="Resume versions" description="Every optimized and job-tailored version you've created." />
            {versions.isPending ? (
              <div className="px-5 pb-5">
                <Spinner />
              </div>
            ) : versions.isError ? (
              <ErrorState error={versions.error} onRetry={() => versions.refetch()} />
            ) : versions.data.items.length === 0 ? (
              <p className="px-5 pb-5 text-app-muted">No versions yet. Save an optimized version above, or tailor one for a job.</p>
            ) : (
              <ul className="divide-y divide-app-border border-t border-app-border">
                {versions.data.items.map((v) => (
                  <li key={v.id} className="flex flex-col gap-3 px-5 py-4 sm:flex-row sm:items-center">
                    <div className="min-w-0 flex-1">
                      <p className="font-medium">
                        {v.kind === "tailored" && !v.job_id ? (
                          `Optimized for ${v.job_title ?? "a job"}${v.company ? ` at ${v.company}` : ""}`
                        ) : v.kind === "tailored" ? (
                          <>
                            Tailored for{" "}
                            <Link href={`/jobs/${v.job_id}/tailor`} className="underline-offset-4 hover:underline">
                              {v.job_title ?? "a job"}
                              {v.company && ` at ${v.company}`}
                            </Link>
                          </>
                        ) : (
                          `ATS-optimized master resume`
                        )}
                      </p>
                      <p className="text-xs text-app-muted">
                        Version {v.version_no} · {formatDate(v.created_at)}
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      {v.truth_check_status !== "passed" && <Badge tone="warning">Check flagged claims</Badge>}
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => api.documents.downloadResumePdf(v.id).catch((e: Error) => toast.error(e.message))}
                      >
                        <Download className="size-3.5" aria-hidden="true" />
                        PDF
                      </Button>
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => api.documents.downloadResumeDocx(v.id).catch((e: Error) => toast.error(e.message))}
                      >
                        DOCX
                      </Button>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </>
      )}
    </>
  );
}
