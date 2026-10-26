"use client";

import type { ApplyMode, Preferences, Seniority, WorkMode } from "@/lib/api/types";
import { cn } from "@/lib/utils";
import { isSalaryValid, salaryWarnings } from "@/lib/salary";
import { SalaryInput } from "./salary-input";
import { ChipGroup, TagInput } from "./tag-input";
import { Checkbox, Field } from "./ui";

export const ROLE_SUGGESTIONS = [
  "Software Engineer",
  "Frontend Engineer",
  "Backend Engineer",
  "Full Stack Developer",
  "Data Analyst",
  "Data Scientist",
  "Data Engineer",
  "AI / ML Engineer",
  "DevOps Engineer",
  "QA Engineer",
  "Product Manager",
  "UI/UX Designer",
  "Business Analyst",
  "Digital Marketing",
];
export const CITY_SUGGESTIONS = ["Bengaluru", "Hyderabad", "Pune", "Mumbai", "Delhi NCR", "Chennai", "Kolkata", "Ahmedabad", "Remote"];

const SENIORITY: { value: Seniority; label: string; description: string }[] = [
  { value: "intern", label: "Internship", description: "Student or final year" },
  { value: "fresher", label: "Fresher", description: "0–1 years" },
  { value: "junior", label: "Junior", description: "1–3 years" },
  { value: "mid", label: "Mid-level", description: "3–6 years" },
  { value: "senior", label: "Senior", description: "5–10 years" },
  { value: "lead", label: "Lead / Manager", description: "8+ years" },
];
const WORK_MODES: { value: WorkMode; label: string }[] = [
  { value: "remote", label: "Remote" },
  { value: "hybrid", label: "Hybrid" },
  { value: "onsite", label: "On-site" },
];
const COMPANY_SIZES = [
  { value: "startup", label: "Startup", description: "< 50" },
  { value: "growth", label: "Growth", description: "50–500" },
  { value: "large", label: "Large", description: "500–5,000" },
  { value: "enterprise", label: "Enterprise / MNC", description: "5,000+" },
];

export const EMPTY_PREFERENCES: Omit<Preferences, "exists"> = {
  target_roles: [],
  role_keywords: [],
  industries: [],
  seniority: "fresher",
  locations: [],
  remote_mode: ["remote", "hybrid", "onsite"],
  min_salary_lpa: 0,
  company_size: [],
  excluded_companies: [],
  excluded_keywords: [],
  employment_types: ["full-time"],
  visa_sponsorship_needed: false,
  daily_application_limit: 10,
  min_match_score: 70,
  apply_mode: "review",
  notice_period_days: null,
  current_ctc_lpa: null,
  expected_ctc_lpa: null,
  willing_to_relocate: null,
};

export type PrefValue = Omit<Preferences, "exists">;
type Set = <K extends keyof PrefValue>(key: K, value: PrefValue[K]) => void;

export interface PrefStep {
  id: string;
  title: string;
  description: string;
  valid: (v: PrefValue) => boolean;
  render: (v: PrefValue, set: Set) => React.ReactNode;
}


/** The 7 questions, in order. Used one-per-screen in onboarding and all together on the Preferences page. */
export const PREFERENCE_STEPS: PrefStep[] = [
  {
    id: "roles",
    title: "What roles do you want?",
    description: "Pick up to 5. We search job boards and company career pages for these titles.",
    valid: (v) => v.target_roles.length > 0,
    render: (v, set) => (
      <TagInput
        label="Target roles"
        value={v.target_roles}
        onChange={(x) => set("target_roles", x)}
        suggestions={ROLE_SUGGESTIONS}
        placeholder="e.g. Frontend Engineer"
        max={5}
      />
    ),
  },
  {
    id: "level",
    title: "What's your experience level?",
    description: "We only show jobs whose experience range fits you.",
    valid: () => true,
    render: (v, set) => (
      <ChipGroup label="Experience level" options={SENIORITY} value={[v.seniority]} onChange={(x) => set("seniority", x[0] ?? "fresher")} multiple={false} />
    ),
  },
  {
    id: "where",
    title: "Where do you want to work?",
    description: "Choose cities and the work styles you're open to.",
    valid: (v) => v.locations.length > 0 && v.remote_mode.length > 0,
    render: (v, set) => (
      <div className="flex flex-col gap-6">
        <TagInput label="Cities" value={v.locations} onChange={(x) => set("locations", x)} suggestions={CITY_SUGGESTIONS} placeholder="Add a city" max={10} />
        <div>
          <p className="mb-2 text-sm font-medium">Work style</p>
          <ChipGroup label="Work style" options={WORK_MODES} value={v.remote_mode} onChange={(x) => set("remote_mode", x)} />
        </div>
        <Checkbox checked={Boolean(v.willing_to_relocate)} onChange={(x) => set("willing_to_relocate", x)} label="I'm willing to relocate for the right role" />
      </div>
    ),
  },
  {
    id: "salary",
    title: "What salary are you looking for?",
    description:
      "Indian application forms ask for current and expected CTC (yearly, before tax). Type it the way you know it: 6.5 LPA, 6,50,000 a year or 54,000 a month.",
    valid: (v) => isSalaryValid(v.current_ctc_lpa) && isSalaryValid(v.expected_ctc_lpa) && Number.isFinite(v.min_salary_lpa),
    render: (v, set) => {
      const cross = salaryWarnings(v);
      const fresher = v.current_ctc_lpa === 0;
      return (
        <div className="flex flex-col gap-5">
          <div className="grid gap-5 sm:grid-cols-2">
            <div className="flex flex-col gap-2">
              <SalaryInput
                id="pref-ctc"
                label="Current CTC"
                value={v.current_ctc_lpa}
                onChange={(n) => set("current_ctc_lpa", n)}
                disabled={fresher}
              />
              <Checkbox
                checked={fresher}
                onChange={(x) => set("current_ctc_lpa", x ? 0 : null)}
                label="I don't have a current salary (fresher or between jobs)"
              />
            </div>
            <SalaryInput
              id="pref-ectc"
              label="Expected CTC"
              hint="Optional. If you leave it blank, we'll ask you whenever an application form needs it."
              value={v.expected_ctc_lpa}
              onChange={(n) => set("expected_ctc_lpa", n)}
              crossFieldWarning={cross.expected}
            />
          </div>
          <div className="sm:max-w-[calc(50%-0.625rem)]">
            <SalaryInput
              id="pref-floor"
              label="Hide jobs that pay less than"
              hint="Optional. Jobs without a listed salary are always shown."
              value={v.min_salary_lpa || null}
              onChange={(n) => set("min_salary_lpa", n ?? 0)}
              crossFieldWarning={cross.floor}
            />
          </div>
        </div>
      );
    },
  },
  {
    id: "notice",
    title: "When can you join?",
    description: "Your notice period. 0 if you can join immediately.",
    valid: (v) => v.notice_period_days !== null,
    render: (v, set) => (
      <div className="flex flex-col gap-4">
        <ChipGroup
          label="Notice period"
          multiple={false}
          options={[
            { value: "0", label: "Immediately" },
            { value: "15", label: "15 days" },
            { value: "30", label: "30 days" },
            { value: "60", label: "60 days" },
            { value: "90", label: "90 days" },
          ]}
          value={v.notice_period_days === null ? [] : [String(v.notice_period_days)]}
          onChange={(x) => set("notice_period_days", Number(x[0] ?? 0))}
        />
      </div>
    ),
  },
  {
    id: "companies",
    title: "Any companies to avoid?",
    description: "Optional. Your current employer, companies you've already applied to, or anywhere you'd rather not work.",
    valid: () => true,
    render: (v, set) => (
      <div className="flex flex-col gap-6">
        <TagInput label="Excluded companies" value={v.excluded_companies} onChange={(x) => set("excluded_companies", x)} placeholder="Company name" max={100} />
        <div>
          <p className="mb-2 text-sm font-medium">Company size (optional)</p>
          <ChipGroup label="Company size" options={COMPANY_SIZES} value={v.company_size} onChange={(x) => set("company_size", x)} />
        </div>
      </div>
    ),
  },
  {
    id: "mode",
    title: "How should Applyon apply for you?",
    description: "You can change this any time from Auto-apply.",
    valid: () => true,
    render: (v, set) => <ApplyModeFields value={v} set={set} />,
  },
];

export function ApplyModeFields({ value: v, set }: { value: PrefValue; set: Set }) {
  const modes: { value: ApplyMode; label: string; description: string }[] = [
    {
      value: "review",
      label: "Review first (recommended)",
      description: "Applyon finds jobs, tailors your resume and fills the forms. You approve every application before it's sent.",
    },
    {
      value: "hybrid",
      label: "Hybrid",
      description: "Same as review, but very high-fit jobs (90+ match, no open questions) are submitted automatically. Needs Pro and your permission.",
    },
  ];
  return (
    <div className="flex flex-col gap-6">
      <div role="radiogroup" aria-label="Apply mode" className="grid gap-3">
        {modes.map((m) => (
          <button
            key={m.value}
            type="button"
            role="radio"
            aria-checked={v.apply_mode === m.value}
            onClick={() => set("apply_mode", m.value)}
            className={cn(
              "rounded-app-lg border p-4 text-left outline-none focus-visible:ring-2 focus-visible:ring-app-accent",
              v.apply_mode === m.value ? "border-app-ink bg-app-card shadow-app-ring" : "border-app-border bg-app-card hover:bg-app-panel"
            )}
          >
            <span className="flex items-center gap-2 font-medium">
              <span className={cn("size-3 rounded-full border", v.apply_mode === m.value ? "border-app-accent bg-app-accent" : "border-app-line")} aria-hidden="true" />
              {m.label}
            </span>
            <span className="mt-1 block text-sm text-app-muted">{m.description}</span>
          </button>
        ))}
      </div>
      <div className="grid gap-5 sm:grid-cols-2">
        <Field label={`Applications per day: ${v.daily_application_limit}`} htmlFor="pref-daily" hint="Quality beats volume. 5–15 a day works well.">
          <input
            id="pref-daily"
            type="range"
            min={1}
            max={30}
            value={v.daily_application_limit}
            onChange={(e) => set("daily_application_limit", Number(e.target.value))}
            className="accent-app-accent"
          />
        </Field>
        <Field label={`Minimum match score: ${v.min_match_score}`} htmlFor="pref-score" hint="Only jobs at or above this fit score are prepared.">
          <input
            id="pref-score"
            type="range"
            min={40}
            max={95}
            step={5}
            value={v.min_match_score}
            onChange={(e) => set("min_match_score", Number(e.target.value))}
            className="accent-app-accent"
          />
        </Field>
      </div>
    </div>
  );
}
