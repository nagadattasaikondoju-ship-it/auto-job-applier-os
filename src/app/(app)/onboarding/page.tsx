"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, FileText, ShieldCheck, Upload } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { AppLogo } from "@/components/app/logo";
import { QuestionInput } from "@/components/app/question-input";
import { Badge, Button, Card, Checkbox, ErrorState, ProgressBar, Spinner, Textarea } from "@/components/app/ui";
import { ApiError } from "@/lib/api/client";
import { api } from "@/lib/api/endpoints";
import type { ConsentPurpose, ParsedResume, Question, ResumeUploadResult } from "@/lib/api/types";
import { extractResumeText } from "@/lib/pdf-text";
import { cn } from "@/lib/utils";

type Step = "resume" | "questions" | "consent";

const STEPS: { id: Step; label: string }[] = [
  { id: "resume", label: "Resume" },
  { id: "questions", label: "Your preferences" },
  { id: "consent", label: "Consent" },
];

export default function OnboardingPage() {
  const [chosenStep, setStep] = useState<Step | null>(null);

  // Users who already have a profile skip the resume step.
  const profile = useQuery({ queryKey: ["profile"], queryFn: api.profile.get, retry: false });
  const step: Step | null =
    chosenStep ?? (profile.isSuccess ? "questions" : profile.isError ? "resume" : null);

  const stepIndex = STEPS.findIndex((s) => s.id === step);

  return (
    <div className="min-h-screen bg-app-bg text-app-ink text-sm">
      <header className="flex items-center justify-between px-6 py-5">
        <AppLogo />
        <ol className="hidden sm:flex items-center gap-2" aria-label="Onboarding progress">
          {STEPS.map((s, i) => (
            <li key={s.id} className="flex items-center gap-2">
              <span
                aria-current={s.id === step ? "step" : undefined}
                className={cn(
                  "inline-flex items-center gap-1.5 rounded-full px-3 h-7 text-xs",
                  i < stepIndex && "bg-app-accent/15 text-app-ink",
                  s.id === step && "bg-app-ink text-app-card",
                  i > stepIndex && "bg-app-panel text-app-muted"
                )}
              >
                {i < stepIndex && <Check className="size-3" aria-hidden="true" />}
                {s.label}
              </span>
              {i < STEPS.length - 1 && <span className="h-px w-4 bg-app-line" aria-hidden="true" />}
            </li>
          ))}
        </ol>
      </header>

      <main className="mx-auto w-full max-w-2xl px-4 pb-16 pt-4">
        {!step && <Spinner label="Getting things ready" />}
        {step === "resume" && <ResumeStep onDone={() => setStep("questions")} />}
        {step === "questions" && <QuestionsStep onDone={() => setStep("consent")} />}
        {step === "consent" && <ConsentStep />}
      </main>
    </div>
  );
}

// ---------------------------------------------------------------- Resume

function ResumeStep({ onDone }: { onDone: () => void }) {
  const queryClient = useQueryClient();
  const fileRef = useRef<HTMLInputElement>(null);
  const [mode, setMode] = useState<"upload" | "paste">("upload");
  const [text, setText] = useState("");
  const [filename, setFilename] = useState("resume.txt");
  const [extracting, setExtracting] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [result, setResult] = useState<ResumeUploadResult | null>(null);

  const upload = useMutation({
    mutationFn: () => api.resumes.upload(text, filename),
    onSuccess: (r) => setResult(r),
    onError: (e) => toast.error(e.message),
  });

  const confirm = useMutation({
    mutationFn: () => api.resumes.confirm(result!.id),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["profile"] });
      toast.success("Profile created from your resume.");
      onDone();
    },
    onError: (e) => toast.error(e.message),
  });

  async function handleFile(file: File) {
    setExtracting(true);
    try {
      const extracted = await extractResumeText(file);
      if (extracted.length < 200) {
        toast.error("We couldn't read much text from that file. If it's a scanned PDF, paste the text instead.");
        setMode("paste");
      }
      setText(extracted);
      setFilename(file.name);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Couldn't read that file.");
    } finally {
      setExtracting(false);
    }
  }

  if (result) return <ParsedReview parsed={result.parsed_profile} onConfirm={() => confirm.mutate()} confirming={confirm.isPending} onRedo={() => setResult(null)} />;

  return (
    <section aria-labelledby="resume-title">
      <h1 id="resume-title" className="font-display text-4xl leading-tight">
        Start with your resume
      </h1>
      <p className="mt-2 text-app-muted max-w-lg">
        We read it once and turn it into your master profile. You review everything before it&apos;s saved, and Applyon
        only ever uses facts from it.
      </p>

      <div className="mt-6 flex gap-1" role="tablist" aria-label="How to add your resume">
        {(["upload", "paste"] as const).map((m) => (
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
            {m === "upload" ? "Upload file" : "Paste text"}
          </button>
        ))}
      </div>

      <Card className="mt-4 p-5">
        {mode === "upload" ? (
          <div
            onDragOver={(e) => {
              e.preventDefault();
              setDragOver(true);
            }}
            onDragLeave={() => setDragOver(false)}
            onDrop={(e) => {
              e.preventDefault();
              setDragOver(false);
              const f = e.dataTransfer.files[0];
              if (f) void handleFile(f);
            }}
            className={cn(
              "flex flex-col items-center justify-center rounded-app-lg border border-dashed px-6 py-12 text-center transition-colors",
              dragOver ? "border-app-accent bg-app-accent/5" : "border-app-line bg-app-bg"
            )}
          >
            {text ? (
              <>
                <FileText className="size-6 text-app-ink-2" aria-hidden="true" />
                <p className="mt-3 font-medium">{filename}</p>
                <p className="text-app-muted">{text.length.toLocaleString("en-IN")} characters read</p>
                <Button variant="ghost" size="sm" className="mt-2" onClick={() => fileRef.current?.click()}>
                  Choose a different file
                </Button>
              </>
            ) : (
              <>
                <Upload className="size-6 text-app-ink-2" aria-hidden="true" />
                <p className="mt-3 font-medium">Drop your resume here</p>
                <p className="text-app-muted">PDF or .txt, up to 5 MB</p>
                <Button variant="secondary" size="sm" className="mt-4" loading={extracting} onClick={() => fileRef.current?.click()}>
                  Choose file
                </Button>
              </>
            )}
            <input
              ref={fileRef}
              type="file"
              accept=".pdf,.txt,.md,application/pdf,text/plain"
              className="sr-only"
              aria-label="Resume file"
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f && f.size > 5 * 1024 * 1024) toast.error("That file is over 5 MB.");
                else if (f) void handleFile(f);
                e.target.value = "";
              }}
            />
          </div>
        ) : (
          <Textarea
            aria-label="Resume text"
            placeholder="Paste the full text of your resume…"
            value={text}
            onChange={(e) => {
              setText(e.target.value);
              setFilename("resume.txt");
            }}
            className="min-h-72 font-mono text-xs"
          />
        )}

        <div className="mt-5 flex flex-col-reverse gap-3 sm:flex-row sm:items-center sm:justify-between">
          <button type="button" onClick={onDone} className="text-sm text-app-muted underline-offset-4 hover:underline hover:text-app-ink">
            Skip, I&apos;ll fill my profile in manually
          </button>
          <Button onClick={() => upload.mutate()} loading={upload.isPending} disabled={text.trim().length < 50 || extracting}>
            {upload.isPending ? "Reading your resume" : "Read my resume"}
          </Button>
        </div>
      </Card>
    </section>
  );
}

function ParsedReview({
  parsed,
  onConfirm,
  confirming,
  onRedo,
}: {
  parsed: ParsedResume;
  onConfirm: () => void;
  confirming: boolean;
  onRedo: () => void;
}) {
  const skills = (parsed.skills ?? []).map((s) => s.name).filter(Boolean) as string[];
  return (
    <section aria-labelledby="review-title">
      <h1 id="review-title" className="font-display text-4xl leading-tight">
        Does this look right?
      </h1>
      <p className="mt-2 text-app-muted">
        This is what we read from your resume. Confirm it to create your profile. You can edit any detail later on your
        Profile page.
      </p>

      <Card className="mt-6 divide-y divide-app-border">
        <div className="p-5">
          <p className="text-lg font-medium">{parsed.full_name || "Name not found"}</p>
          <p className="text-app-muted">
            {[parsed.headline || parsed.current_title, parsed.city].filter(Boolean).join(" · ") || "No headline found"}
          </p>
          <p className="mt-1 text-app-muted">{[parsed.email, parsed.phone].filter(Boolean).join(" · ")}</p>
          {parsed.summary && <p className="mt-3 text-app-ink-2 leading-relaxed">{parsed.summary}</p>}
        </div>

        <div className="p-5">
          <h2 className="font-medium">Experience</h2>
          {(parsed.experiences ?? []).length === 0 && <p className="mt-2 text-app-muted">No experience found.</p>}
          <ul className="mt-3 flex flex-col gap-4">
            {(parsed.experiences ?? []).map((exp, i) => (
              <li key={i}>
                <p className="font-medium">
                  {exp.title} <span className="text-app-muted font-normal">at {exp.company}</span>
                </p>
                <p className="text-xs text-app-subtle">
                  {exp.start_date} – {exp.is_current ? "Present" : exp.end_date || "—"}
                </p>
                <ul className="mt-1.5 list-disc pl-5 text-app-ink-2 space-y-1">
                  {(exp.bullets ?? []).slice(0, 4).map((b, j) => (
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
                {[ed.degree, ed.field].filter(Boolean).join(", ")} — {ed.institution}
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
        <Button variant="ghost" onClick={onRedo}>
          Upload a different resume
        </Button>
        <Button onClick={onConfirm} loading={confirming}>
          Looks good, create my profile
        </Button>
      </div>
    </section>
  );
}

// ---------------------------------------------------------------- Questionnaire

function QuestionsStep({ onDone }: { onDone: () => void }) {
  const queryClient = useQueryClient();
  const next = useQuery({ queryKey: ["onboarding", "next"], queryFn: api.onboarding.nextQuestion });

  useEffect(() => {
    if (next.data?.completed) onDone();
  }, [next.data?.completed, onDone]);

  if (next.isPending) return <Spinner label="Loading your next question" />;
  if (next.isError) return <ErrorState error={next.error} onRetry={() => next.refetch()} />;
  if (!next.data.question) return <Spinner label="Finishing up" />;

  return (
    <section aria-labelledby="question-title">
      <div className="flex items-center justify-between gap-4">
        <p className="text-xs text-app-muted">About you</p>
        <p className="font-mono text-xs text-app-muted">{next.data.progress_percent}%</p>
      </div>
      <div className="mt-2">
        <ProgressBar value={next.data.progress_percent} label="Questionnaire progress" />
      </div>
      {/* Keyed by question so the input resets for every new question. */}
      <QuestionForm
        key={next.data.question.id}
        question={next.data.question}
        onAnswered={() => queryClient.invalidateQueries({ queryKey: ["onboarding", "next"] })}
      />
    </section>
  );
}

function QuestionForm({ question, onAnswered }: { question: Question; onAnswered: () => Promise<void> }) {
  const [value, setValue] = useState<unknown>(question.type === "multi_select" ? [] : question.type === "boolean" ? undefined : "");

  const answer = useMutation({
    mutationFn: (v: unknown) => api.onboarding.answer(question.id, v),
    onSuccess: onAnswered,
    onError: (e) => toast.error(e.message),
  });

  const isEmpty =
    value === undefined || value === "" || value === null || (Array.isArray(value) && value.length === 0);

  function submit(e?: React.FormEvent) {
    e?.preventDefault();
    let v = value;
    if (question.type === "number" && typeof v === "string") v = v === "" ? null : Number(v);
    answer.mutate(v);
  }

  return (
    <form onSubmit={submit} className="mt-10">
      <h1 id="question-title" className="font-display text-3xl sm:text-4xl leading-tight">
        {question.text}
      </h1>
      {question.help_text && <p className="mt-2 text-app-muted">{question.help_text}</p>}
      <div className="mt-6">
        <QuestionInput question={question} value={value} onChange={setValue} autoFocus />
      </div>
      <div className="mt-8 flex items-center justify-between gap-3">
        {!question.required ? (
          <Button variant="ghost" onClick={() => answer.mutate(null)} disabled={answer.isPending}>
            Skip
          </Button>
        ) : (
          <span />
        )}
        <Button type="submit" loading={answer.isPending} disabled={question.required && isEmpty}>
          Continue
        </Button>
      </div>
    </form>
  );
}

// ---------------------------------------------------------------- Consent

const CONSENTS: { purpose: ConsentPurpose; label: string; description: string; required: boolean }[] = [
  {
    purpose: "profile_matching",
    label: "Use my profile to find matching jobs",
    description: "We compare your profile and preferences with job postings to score how well each one fits.",
    required: true,
  },
  {
    purpose: "document_generation",
    label: "Generate tailored resumes, cover letters and answers",
    description: "AI rewrites using only facts from your profile. Nothing is invented, and you review it first.",
    required: true,
  },
  {
    purpose: "auto_submit",
    label: "Allow auto-submit (optional)",
    description:
      "Lets Autopilot submit applications without asking each time, only on reliable job sites and within your daily limit. You can turn this off any time in Settings.",
    required: false,
  },
];

function ConsentStep() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [checked, setChecked] = useState<Record<ConsentPurpose, boolean>>({
    profile_matching: false,
    document_generation: false,
    auto_submit: false,
  });

  const save = useMutation({
    mutationFn: async () => {
      for (const c of CONSENTS) await api.consents.set(c.purpose, checked[c.purpose]);
    },
    onSuccess: async () => {
      // Kick off the first round of matching so the dashboard isn't empty.
      api.matches.refresh().catch(() => undefined);
      await queryClient.invalidateQueries();
      toast.success("You're all set. Finding your first matches now.");
      router.replace("/dashboard");
    },
    onError: (e) => toast.error(e instanceof ApiError ? e.message : "Couldn't save your choices."),
  });

  const canContinue = CONSENTS.filter((c) => c.required).every((c) => checked[c.purpose]);

  return (
    <section aria-labelledby="consent-title">
      <ShieldCheck className="size-6 text-app-accent" aria-hidden="true" />
      <h1 id="consent-title" className="mt-3 font-display text-4xl leading-tight">
        You stay in control
      </h1>
      <p className="mt-2 text-app-muted max-w-lg">
        Under India&apos;s DPDP Act we ask for your permission for each use of your data. You can withdraw any of these
        later in Settings.
      </p>
      <Card className="mt-6 p-5 flex flex-col gap-5">
        {CONSENTS.map((c) => (
          <Checkbox
            key={c.purpose}
            checked={checked[c.purpose]}
            onChange={(v) => setChecked((s) => ({ ...s, [c.purpose]: v }))}
            label={c.label}
            description={c.description}
          />
        ))}
      </Card>
      <div className="mt-5 flex justify-end">
        <Button onClick={() => save.mutate()} loading={save.isPending} disabled={!canContinue}>
          Finish setup
        </Button>
      </div>
    </section>
  );
}
