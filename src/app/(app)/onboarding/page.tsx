"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, ArrowRight, Check, FileText, Rocket, ShieldCheck, Upload } from "lucide-react";
import { useRouter } from "next/navigation";
import { useRef, useState } from "react";
import { toast } from "sonner";
import { AtsOptimizer } from "@/components/app/ats-optimizer";
import { AppLogo } from "@/components/app/logo";
import { EMPTY_PREFERENCES, PREFERENCE_STEPS, type PrefValue } from "@/components/app/preferences-form";
import { Badge, Button, Card, Checkbox, ErrorState, ProgressBar, Spinner, Textarea } from "@/components/app/ui";
import { ApiError } from "@/lib/api/client";
import { api } from "@/lib/api/endpoints";
import type { AtsReport, ConsentPurpose, FullProfile, ParsedResume, Seniority, UploadResumeResult } from "@/lib/api/types";
import { cn } from "@/lib/utils";

type Step = "upload" | "review" | "ats" | "preferences" | "launch";

const STEPS: { id: Step; label: string }[] = [
  { id: "upload", label: "Resume" },
  { id: "review", label: "Your profile" },
  { id: "ats", label: "ATS check" },
  { id: "preferences", label: "What you want" },
  { id: "launch", label: "Start applying" },
];

export default function OnboardingPage() {
  const [chosen, setStep] = useState<Step | null>(null);
  const [upload, setUpload] = useState<UploadResumeResult | null>(null);

  // Resume where the user left off: no profile → upload; no preferences → preferences; else launch.
  const profile = useQuery({ queryKey: ["profile"], queryFn: api.profile.get, retry: false });
  const prefs = useQuery({ queryKey: ["preferences"], queryFn: api.preferences.get, retry: false });
  const inferred: Step | null = profile.isError
    ? "upload"
    : profile.isSuccess && prefs.isSuccess
      ? prefs.data.exists
        ? "launch"
        : "preferences"
      : null;
  const step = chosen ?? inferred;
  const index = STEPS.findIndex((s) => s.id === step);

  return (
    <div className="min-h-screen bg-app-bg text-app-ink text-sm">
      <header className="flex items-center justify-between gap-4 px-4 sm:px-6 py-5">
        <AppLogo />
        <ol className="hidden md:flex items-center gap-2" aria-label="Setup progress">
          {STEPS.map((s, i) => (
            <li key={s.id} className="flex items-center gap-2">
              <span
                aria-current={s.id === step ? "step" : undefined}
                className={cn(
                  "inline-flex items-center gap-1.5 rounded-full px-3 h-7 text-xs",
                  i < index && "bg-app-accent/15 text-app-ink",
                  s.id === step && "bg-app-ink text-app-card",
                  i > index && "bg-app-panel text-app-muted"
                )}
              >
                {i < index && <Check className="size-3" aria-hidden="true" />}
                {s.label}
              </span>
              {i < STEPS.length - 1 && <span className="h-px w-3 bg-app-line" aria-hidden="true" />}
            </li>
          ))}
        </ol>
        <p className="md:hidden text-xs text-app-muted">
          Step {Math.max(1, index + 1)} of {STEPS.length}
        </p>
      </header>

      <main className="mx-auto w-full max-w-3xl px-4 pb-20 pt-2">
        {!step && <Spinner label="Getting things ready" />}
        {step === "upload" && (
          <UploadStep
            onUploaded={(r) => {
              setUpload(r);
              setStep("review");
            }}
            onSkip={() => setStep("preferences")}
          />
        )}
        {step === "review" && upload && (
          <ReviewStep upload={upload} onBack={() => setStep("upload")} onConfirmed={() => setStep("ats")} />
        )}
        {step === "review" && !upload && <Spinner />}
        {step === "ats" && (
          <AtsStep
            initial={upload?.ats ?? null}
            onBack={() => setStep(upload ? "review" : "upload")}
            onNext={() => setStep("preferences")}
          />
        )}
        {step === "preferences" && (
          <PreferencesStep onBack={() => setStep(profile.isSuccess ? "ats" : "upload")} onDone={() => setStep("launch")} />
        )}
        {step === "launch" && <LaunchStep onBack={() => setStep("preferences")} />}
      </main>
    </div>
  );
}

// ---------------------------------------------------------------- 1. Upload

function UploadStep({ onUploaded, onSkip }: { onUploaded: (r: UploadResumeResult) => void; onSkip: () => void }) {
  const fileRef = useRef<HTMLInputElement>(null);
  const [mode, setMode] = useState<"file" | "paste">("file");
  const [text, setText] = useState("");
  const [dragOver, setDragOver] = useState(false);

  const uploadFile = useMutation({
    mutationFn: (file: File) => api.resumes.uploadFile(file),
    onSuccess: onUploaded,
    onError: (e) => toast.error(e.message),
  });
  const uploadText = useMutation({
    mutationFn: () => api.resumes.upload(text, "resume.txt"),
    onSuccess: onUploaded,
    onError: (e) => toast.error(e.message),
  });

  function pick(file: File | undefined) {
    if (!file) return;
    if (file.size > 5 * 1024 * 1024) return toast.error("That file is over 5 MB.");
    if (!/\.(pdf|docx|txt)$/i.test(file.name)) return toast.error("Upload a PDF, DOCX or .txt file.");
    uploadFile.mutate(file);
  }

  const busy = uploadFile.isPending || uploadText.isPending;

  return (
    <section aria-labelledby="upload-title">
      <h1 id="upload-title" className="font-display text-4xl sm:text-5xl leading-tight">
        Let&apos;s start with your resume
      </h1>
      <p className="mt-3 text-app-muted max-w-xl">
        We&apos;ll read it, build your profile, and score it the way applicant tracking systems do. Then we fix what&apos;s
        holding it back, and start finding jobs that fit.
      </p>

      <div className="mt-6 flex gap-1" role="tablist" aria-label="How to add your resume">
        {(["file", "paste"] as const).map((m) => (
          <button
            key={m}
            role="tab"
            type="button"
            aria-selected={mode === m}
            onClick={() => setMode(m)}
            className={cn(
              "rounded-full px-3 h-8 text-sm outline-none focus-visible:ring-2 focus-visible:ring-app-accent",
              mode === m ? "bg-app-ink text-app-card" : "text-app-ink-2 hover:bg-app-panel"
            )}
          >
            {m === "file" ? "Upload a file" : "Paste text"}
          </button>
        ))}
      </div>

      <Card className="mt-4 p-5">
        {busy ? (
          <div role="status" className="flex flex-col items-center py-12 text-center">
            <Spinner label="Reading your resume" />
            <ol className="mt-2 flex flex-col gap-1 text-app-muted">
              <li>Extracting your experience, education and skills</li>
              <li>Scoring it like an ATS would</li>
            </ol>
          </div>
        ) : mode === "file" ? (
          <div
            onDragOver={(e) => {
              e.preventDefault();
              setDragOver(true);
            }}
            onDragLeave={() => setDragOver(false)}
            onDrop={(e) => {
              e.preventDefault();
              setDragOver(false);
              pick(e.dataTransfer.files[0]);
            }}
            className={cn(
              "flex flex-col items-center justify-center rounded-app-lg border border-dashed px-6 py-14 text-center transition-colors",
              dragOver ? "border-app-accent bg-app-accent/5" : "border-app-line bg-app-bg"
            )}
          >
            <Upload className="size-7 text-app-ink-2" aria-hidden="true" />
            <p className="mt-3 text-base font-medium">Drop your resume here</p>
            <p className="text-app-muted">PDF, DOCX or TXT · up to 5 MB</p>
            <Button className="mt-5" onClick={() => fileRef.current?.click()}>
              Choose file
            </Button>
            <input
              ref={fileRef}
              type="file"
              accept=".pdf,.docx,.txt,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain"
              className="sr-only"
              aria-label="Resume file"
              onChange={(e) => {
                pick(e.target.files?.[0]);
                e.target.value = "";
              }}
            />
          </div>
        ) : (
          <>
            <Textarea
              aria-label="Resume text"
              placeholder="Paste the full text of your resume…"
              value={text}
              onChange={(e) => setText(e.target.value)}
              className="min-h-72 font-mono text-xs"
            />
            <div className="mt-4 flex justify-end">
              <Button onClick={() => uploadText.mutate()} disabled={text.trim().length < 100}>
                Read my resume
              </Button>
            </div>
          </>
        )}
      </Card>

      <button
        type="button"
        onClick={onSkip}
        className="mt-4 text-sm text-app-muted underline-offset-4 hover:underline hover:text-app-ink"
      >
        I don&apos;t have a resume yet. Set my job preferences first.
      </button>
    </section>
  );
}

// ---------------------------------------------------------------- 2. Review extracted profile

function ReviewStep({
  upload,
  onBack,
  onConfirmed,
}: {
  upload: UploadResumeResult;
  onBack: () => void;
  onConfirmed: () => void;
}) {
  const queryClient = useQueryClient();
  const parsed: ParsedResume = upload.parsed_profile;
  const skills = (parsed.skills ?? []).map((s) => s.name).filter(Boolean) as string[];

  const confirm = useMutation({
    mutationFn: () => api.resumes.confirm(upload.id),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["profile"] });
      onConfirmed();
    },
    onError: (e) => toast.error(e.message),
  });

  return (
    <section aria-labelledby="review-title">
      <h1 id="review-title" className="font-display text-4xl leading-tight">
        Here&apos;s what we read
      </h1>
      <p className="mt-2 text-app-muted">
        Check it&apos;s right. This becomes your master profile, and Applyon only ever uses facts from it. You can edit
        anything later on your Profile page.
      </p>

      <Card className="mt-6 divide-y divide-app-border">
        <div className="p-5">
          <p className="text-lg font-medium">{parsed.full_name || "Name not found"}</p>
          <p className="text-app-muted">{[parsed.headline || parsed.current_title, parsed.city].filter(Boolean).join(" · ") || "No headline found"}</p>
          <p className="mt-1 text-app-muted">{[parsed.email, parsed.phone].filter(Boolean).join(" · ") || "No contact details found"}</p>
          {parsed.summary && <p className="mt-3 leading-relaxed text-app-ink-2">{parsed.summary}</p>}
        </div>
        <div className="p-5">
          <h2 className="font-medium">Experience</h2>
          {(parsed.experiences ?? []).length === 0 && <p className="mt-2 text-app-muted">No experience found.</p>}
          <ul className="mt-3 flex flex-col gap-4">
            {(parsed.experiences ?? []).map((exp, i) => (
              <li key={i}>
                <p className="font-medium">
                  {exp.title} {exp.company && <span className="font-normal text-app-muted">at {exp.company}</span>}
                </p>
                <p className="text-xs text-app-subtle">
                  {exp.start_date} – {exp.is_current ? "Present" : exp.end_date || "—"}
                </p>
                <ul className="mt-1.5 list-disc space-y-1 pl-5 text-app-ink-2">
                  {(exp.bullets ?? []).slice(0, 5).map((b, j) => (
                    <li key={j}>{typeof b === "string" ? b : b.text}</li>
                  ))}
                </ul>
              </li>
            ))}
          </ul>
        </div>
        <div className="p-5">
          <h2 className="font-medium">Education</h2>
          <ul className="mt-2 flex flex-col gap-1 text-app-ink-2">
            {(parsed.educations ?? []).map((ed, i) => (
              <li key={i}>
                {[ed.degree, ed.field].filter(Boolean).join(", ")} {ed.institution}
                {ed.grade && <span className="text-app-muted"> · {ed.grade}</span>}
              </li>
            ))}
            {(parsed.educations ?? []).length === 0 && <li className="text-app-muted">No education found.</li>}
          </ul>
        </div>
        <div className="p-5">
          <h2 className="font-medium">Skills</h2>
          <div className="mt-2 flex flex-wrap gap-1.5">
            {skills.map((s) => (
              <Badge key={s}>{s}</Badge>
            ))}
            {skills.length === 0 && <p className="text-app-muted">No skills found.</p>}
          </div>
        </div>
      </Card>

      <div className="mt-5 flex flex-col-reverse gap-3 sm:flex-row sm:justify-between">
        <Button variant="ghost" onClick={onBack}>
          <ArrowLeft className="size-4" aria-hidden="true" />
          Upload a different resume
        </Button>
        <Button onClick={() => confirm.mutate()} loading={confirm.isPending}>
          Looks right, check my ATS score
          <ArrowRight className="size-4" aria-hidden="true" />
        </Button>
      </div>
    </section>
  );
}

// ---------------------------------------------------------------- 3. ATS check & fixes

function AtsStep({ initial, onBack, onNext }: { initial: AtsReport | null; onBack: () => void; onNext: () => void }) {
  const scan = useQuery({
    queryKey: ["ats", "onboarding"],
    queryFn: () => api.ats.scan({}),
    enabled: !initial,
  });
  const report = initial ?? scan.data;

  return (
    <section aria-labelledby="ats-title">
      <h1 id="ats-title" className="font-display text-4xl leading-tight">
        Your ATS score
      </h1>
      <p className="mt-2 text-app-muted max-w-2xl">
        Most companies use an applicant tracking system that ranks resumes before a person sees them. Here&apos;s how
        yours scores, and what to fix. Every suggestion uses only facts you wrote.
      </p>
      <div className="mt-6">
        {report ? (
          <AtsOptimizer report={report} compact />
        ) : scan.isError ? (
          <ErrorState error={scan.error} onRetry={() => scan.refetch()} />
        ) : (
          <Spinner label="Scoring your resume" />
        )}
      </div>
      <div className="mt-8 flex flex-col-reverse gap-3 sm:flex-row sm:justify-between">
        <Button variant="ghost" onClick={onBack}>
          <ArrowLeft className="size-4" aria-hidden="true" />
          Back
        </Button>
        <Button onClick={onNext}>
          Next: tell us what you want
          <ArrowRight className="size-4" aria-hidden="true" />
        </Button>
      </div>
    </section>
  );
}

// ---------------------------------------------------------------- 4. Preferences (7 questions)

function PreferencesStep({ onBack, onDone }: { onBack: () => void; onDone: () => void }) {
  const queryClient = useQueryClient();
  const existing = useQuery({ queryKey: ["preferences"], queryFn: api.preferences.get });
  const profile = useQuery({ queryKey: ["profile"], queryFn: api.profile.get });
  const [value, setValue] = useState<PrefValue | null>(null);
  const [i, setI] = useState(0);

  const save = useMutation({
    mutationFn: (v: PrefValue) => api.preferences.save(v),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["preferences"] });
      onDone();
    },
    onError: (e) => toast.error(e.message),
  });

  if (existing.isPending || profile.isPending) return <Spinner />;
  if (existing.isError) return <ErrorState error={existing.error} onRetry={() => existing.refetch()} />;

  // First time through, start from what the resume already tells us
  const initial = existing.data.exists
    ? stripExists(existing.data)
    : { ...stripExists(existing.data), ...(profile.data ? defaultsFromProfile(profile.data) : {}) };
  const v: PrefValue = value ?? { ...EMPTY_PREFERENCES, ...initial };
  const set = <K extends keyof PrefValue>(k: K, val: PrefValue[K]) => setValue({ ...v, [k]: val });
  const q = PREFERENCE_STEPS[i];
  const last = i === PREFERENCE_STEPS.length - 1;

  return (
    <section aria-labelledby="pref-title">
      <div className="flex items-center justify-between">
        <p className="text-xs text-app-muted">
          Question {i + 1} of {PREFERENCE_STEPS.length}
        </p>
        <p className="font-mono text-xs text-app-muted">{Math.round((i / PREFERENCE_STEPS.length) * 100)}%</p>
      </div>
      <div className="mt-2">
        <ProgressBar value={(i / PREFERENCE_STEPS.length) * 100} label="Questions progress" />
      </div>
      <form
        className="mt-10"
        onSubmit={(e) => {
          e.preventDefault();
          if (!q.valid(v)) return;
          if (last) save.mutate(v);
          else setI(i + 1);
        }}
      >
        <h1 id="pref-title" className="font-display text-3xl sm:text-4xl leading-tight">
          {q.title}
        </h1>
        <p className="mt-2 text-app-muted">{q.description}</p>
        <div className="mt-6">{q.render(v, set)}</div>
        <div className="mt-10 flex items-center justify-between gap-3">
          <Button variant="ghost" onClick={() => (i === 0 ? onBack() : setI(i - 1))}>
            <ArrowLeft className="size-4" aria-hidden="true" />
            Back
          </Button>
          <Button type="submit" disabled={!q.valid(v)} loading={save.isPending}>
            {last ? "Save and continue" : "Continue"}
            <ArrowRight className="size-4" aria-hidden="true" />
          </Button>
        </div>
      </form>
    </section>
  );
}

function defaultsFromProfile(p: FullProfile): Partial<PrefValue> {
  const months = experienceMonths(p.experiences) || p.profile.total_experience_months || 0;
  const years = months / 12;
  const seniority: Seniority = years < 1 ? "fresher" : years < 3 ? "junior" : years < 6 ? "mid" : years < 10 ? "senior" : "lead";
  const out: Partial<PrefValue> = { seniority };
  if (p.profile.current_title) out.target_roles = [p.profile.current_title];
  if (p.profile.city) out.locations = [p.profile.city];
  return out;
}

/** Months of non-internship experience, from start/end dates like "Jan 2022" or "2021-06". */
function experienceMonths(experiences: FullProfile["experiences"]): number {
  const toMonth = (d: string | null | undefined): number | null => {
    if (!d) return null;
    const year = d.match(/(19|20)\d{2}/);
    if (!year) return null;
    const names = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"];
    const named = names.indexOf(d.slice(0, 3).toLowerCase());
    const numeric = d.match(/-(\d{1,2})/);
    const month = named >= 0 ? named : numeric ? Number(numeric[1]) - 1 : 5;
    return Number(year[0]) * 12 + month;
  };
  const now = new Date();
  let total = 0;
  for (const e of experiences) {
    if (/intern|trainee/i.test(e.title ?? "")) continue;
    const start = toMonth(e.start_date);
    const end = e.is_current ? now.getFullYear() * 12 + now.getMonth() : toMonth(e.end_date);
    if (start !== null && end !== null && end > start) total += end - start;
  }
  return total;
}

function stripExists(p: PrefValue & { exists?: boolean }): PrefValue {
  const { exists: _exists, ...rest } = p;
  void _exists;
  return rest;
}

// ---------------------------------------------------------------- 5. Consent & launch

const CONSENTS: { purpose: ConsentPurpose; label: string; description: string; required: boolean }[] = [
  {
    purpose: "profile_matching",
    label: "Use my profile to find and score jobs",
    description: "We compare your profile and preferences with job postings.",
    required: true,
  },
  {
    purpose: "document_generation",
    label: "Prepare tailored resumes, cover letters and form answers",
    description: "AI rewrites using only facts from your profile. You review everything.",
    required: true,
  },
  {
    purpose: "auto_submit",
    label: "Allow Hybrid mode to submit very high-fit jobs (optional)",
    description: "Only for 90+ matches with no open questions, within your daily limit. Needs the Pro plan.",
    required: false,
  },
];

function LaunchStep({ onBack }: { onBack: () => void }) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const prefs = useQuery({ queryKey: ["preferences"], queryFn: api.preferences.get });
  const [checked, setChecked] = useState<Record<ConsentPurpose, boolean>>({
    profile_matching: true,
    document_generation: true,
    auto_submit: false,
  });
  const [blockers, setBlockers] = useState<string[]>([]);

  const launch = useMutation({
    mutationFn: async () => {
      for (const c of CONSENTS) await api.consents.set(c.purpose, checked[c.purpose]);
      const p = prefs.data!;
      const mode = p.apply_mode === "hybrid" && checked.auto_submit ? "hybrid" : "review";
      return api.autopilot.start({ mode, daily_limit: p.daily_application_limit, min_match_score: p.min_match_score });
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries();
      toast.success("Auto-apply is on. We're finding your best matches and preparing applications now.");
      router.replace("/auto-apply");
    },
    onError: (e) => {
      if (e instanceof ApiError && e.code === "AUTOPILOT_NOT_READY") {
        setBlockers(Array.isArray(e.details) ? (e.details as string[]) : [e.message]);
      } else {
        toast.error(e.message);
      }
    },
  });

  const canLaunch = CONSENTS.filter((c) => c.required).every((c) => checked[c.purpose]);

  return (
    <section aria-labelledby="launch-title">
      <Rocket className="size-7 text-app-accent" aria-hidden="true" />
      <h1 id="launch-title" className="mt-3 font-display text-4xl leading-tight">
        Ready to start applying
      </h1>
      <p className="mt-2 text-app-muted max-w-xl">
        Applyon will search job boards and company career pages for your roles, score every job against your profile,
        and prepare applications for the best matches. Nothing is sent without your approval
        {prefs.data?.apply_mode === "hybrid" ? " (except 90+ matches in Hybrid mode)" : ""}.
      </p>

      <Card className="mt-6 p-5">
        <div className="flex items-center gap-2">
          <ShieldCheck className="size-4 text-app-accent" aria-hidden="true" />
          <p className="font-medium">Your permissions (India&apos;s DPDP Act)</p>
        </div>
        <div className="mt-4 flex flex-col gap-4">
          {CONSENTS.map((c) => (
            <Checkbox
              key={c.purpose}
              checked={checked[c.purpose]}
              onChange={(on) => setChecked((s) => ({ ...s, [c.purpose]: on }))}
              label={c.label}
              description={c.description}
            />
          ))}
        </div>
      </Card>

      {blockers.length > 0 && (
        <Card className="mt-4 p-5" role="alert">
          <p className="font-medium">Almost there. Fix these to start auto-apply:</p>
          <ul className="mt-2 list-disc pl-5 text-app-ink-2">
            {blockers.map((b) => (
              <li key={b}>{b}</li>
            ))}
          </ul>
          <div className="mt-4 flex flex-wrap gap-2">
            <Button variant="secondary" onClick={() => router.push("/profile")}>
              <FileText className="size-4" aria-hidden="true" />
              Complete profile
            </Button>
            <Button variant="ghost" onClick={() => router.push("/dashboard")}>
              Go to dashboard
            </Button>
          </div>
        </Card>
      )}

      <div className="mt-8 flex flex-col-reverse gap-3 sm:flex-row sm:justify-between">
        <Button variant="ghost" onClick={onBack}>
          <ArrowLeft className="size-4" aria-hidden="true" />
          Back
        </Button>
        <Button size="lg" variant="accent" onClick={() => launch.mutate()} loading={launch.isPending} disabled={!canLaunch || !prefs.data}>
          <Rocket className="size-4" aria-hidden="true" />
          Start auto-apply
        </Button>
      </div>
    </section>
  );
}
