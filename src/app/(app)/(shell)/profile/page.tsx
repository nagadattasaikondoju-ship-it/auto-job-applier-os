"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import {
  Badge,
  Button,
  ButtonLink,
  Card,
  CardHeader,
  Checkbox,
  Dialog,
  EmptyState,
  ErrorState,
  Field,
  Input,
  PageHeader,
  ProgressBar,
  Skeleton,
  Textarea,
} from "@/components/app/ui";
import { ApiError } from "@/lib/api/client";
import { api } from "@/lib/api/endpoints";
import type { ExperienceBullet, FullProfile, ProfileUpdate } from "@/lib/api/types";

function bulletText(b: ExperienceBullet | string) {
  return typeof b === "string" ? b : b.text;
}

export default function ProfilePage() {
  const profile = useQuery({ queryKey: ["profile"], queryFn: api.profile.get, retry: false });

  if (profile.isPending) {
    return (
      <div className="flex flex-col gap-4">
        <Skeleton className="h-10 w-48" />
        <Skeleton className="h-96 w-full rounded-app-xl" />
      </div>
    );
  }

  if (profile.isError) {
    if (profile.error instanceof ApiError && profile.error.status === 404) {
      return (
        <>
          <PageHeader title="Profile" />
          <Card>
            <EmptyState
              title="You don't have a profile yet"
              description="Upload your resume and we'll build your profile in about a minute."
              action={<ButtonLink href="/onboarding">Set up my profile</ButtonLink>}
            />
          </Card>
        </>
      );
    }
    return <ErrorState error={profile.error} onRetry={() => profile.refetch()} />;
  }

  return <ProfileView data={profile.data} />;
}

function ProfileView({ data }: { data: FullProfile }) {
  const queryClient = useQueryClient();
  const p = data.profile;
  // Form state starts from the loaded profile; later refetches don't overwrite unsaved edits.
  const [form, setForm] = useState<ProfileUpdate>(() => ({
    full_name: p.full_name,
    phone: p.phone,
    city: p.city,
    state: p.state,
    headline: p.headline,
    summary: p.summary,
    current_title: p.current_title,
    current_company: p.current_company,
    current_ctc_lpa: p.current_ctc_lpa,
    expected_ctc_lpa: p.expected_ctc_lpa,
    notice_period_days: p.notice_period_days,
    currently_serving_notice: p.currently_serving_notice,
    willing_to_relocate: p.willing_to_relocate,
  }));
  const [links, setLinks] = useState<Record<string, string>>(() => ({
    linkedin: "",
    github: "",
    portfolio: "",
    ...(p.links ?? {}),
  }));
  const [expOpen, setExpOpen] = useState(false);
  const [newSkill, setNewSkill] = useState("");

  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: ["profile"] });
    void queryClient.invalidateQueries({ queryKey: ["analytics"] });
  };

  const save = useMutation({
    mutationFn: () => api.profile.update({ ...form, links: Object.fromEntries(Object.entries(links).filter(([, v]) => v)) }),
    onSuccess: () => {
      toast.success("Profile saved.");
      invalidate();
    },
    onError: (e) => toast.error(e.message),
  });

  const addSkill = useMutation({
    mutationFn: (name: string) => api.profile.addSkill({ name }),
    onSuccess: () => {
      setNewSkill("");
      invalidate();
    },
    onError: (e) => toast.error(e.message),
  });

  const set = <K extends keyof ProfileUpdate>(k: K, v: ProfileUpdate[K]) => setForm((f) => ({ ...f, [k]: v }));
  const num = (v: string) => (v === "" ? null : Number(v));
  const c = data.completeness;

  return (
    <>
      <PageHeader
        title="Profile"
        description="Your master profile. Every tailored resume and form answer comes only from what's here."
        actions={
          <Button onClick={() => save.mutate()} loading={save.isPending}>
            Save changes
          </Button>
        }
      />

      <Card className="mb-6 p-5 flex flex-col gap-3 sm:flex-row sm:items-center">
        <div className="flex-1">
          <p className="font-medium">Profile {c.score}% complete</p>
          <p className="text-app-muted">
            {c.can_start_autopilot ? "Ready for Autopilot." : "Reach 80% to unlock Autopilot."}
            {c.missing && c.missing.length > 0 && ` Missing: ${c.missing.join(", ")}.`}
          </p>
        </div>
        <div className="sm:w-56">
          <ProgressBar value={c.score} label="Profile completeness" />
        </div>
      </Card>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2 flex flex-col gap-6">
          <Card as="section" aria-labelledby="basics">
            <CardHeader id="basics" title="Basics" />
            <form
              className="grid gap-4 px-5 pb-5 sm:grid-cols-2"
              onSubmit={(e) => {
                e.preventDefault();
                save.mutate();
              }}
            >
              <Field label="Full name" htmlFor="p-name">
                <Input id="p-name" value={form.full_name ?? ""} onChange={(e) => set("full_name", e.target.value)} />
              </Field>
              <Field label="Phone" htmlFor="p-phone">
                <Input id="p-phone" type="tel" value={form.phone ?? ""} onChange={(e) => set("phone", e.target.value)} />
              </Field>
              <Field label="Email" htmlFor="p-email" hint="Comes from your login.">
                <Input id="p-email" value={p.email} disabled />
              </Field>
              <Field label="City" htmlFor="p-city">
                <Input id="p-city" value={form.city ?? ""} onChange={(e) => set("city", e.target.value)} />
              </Field>
              <div className="sm:col-span-2">
                <Field label="Headline" htmlFor="p-headline">
                  <Input
                    id="p-headline"
                    value={form.headline ?? ""}
                    onChange={(e) => set("headline", e.target.value)}
                    placeholder="e.g. Frontend engineer · React, TypeScript"
                  />
                </Field>
              </div>
              <div className="sm:col-span-2">
                <Field label="Summary" htmlFor="p-summary">
                  <Textarea id="p-summary" value={form.summary ?? ""} onChange={(e) => set("summary", e.target.value)} />
                </Field>
              </div>
              <Field label="Current title" htmlFor="p-title">
                <Input id="p-title" value={form.current_title ?? ""} onChange={(e) => set("current_title", e.target.value)} />
              </Field>
              <Field label="Current company" htmlFor="p-company">
                <Input id="p-company" value={form.current_company ?? ""} onChange={(e) => set("current_company", e.target.value)} />
              </Field>
              <button type="submit" className="sr-only">
                Save
              </button>
            </form>
          </Card>

          <Card as="section" aria-labelledby="experience">
            <CardHeader
              id="experience"
              title="Experience"
              action={
                <Button variant="secondary" size="sm" onClick={() => setExpOpen(true)}>
                  <Plus className="size-3.5" aria-hidden="true" />
                  Add
                </Button>
              }
            />
            {data.experiences.length === 0 ? (
              <p className="px-5 pb-5 text-app-muted">No experience added yet.</p>
            ) : (
              <ul className="divide-y divide-app-border border-t border-app-border">
                {data.experiences.map((e) => (
                  <li key={e.id} className="px-5 py-4">
                    <p className="font-medium">
                      {e.title} <span className="font-normal text-app-muted">at {e.company}</span>
                    </p>
                    <p className="text-xs text-app-subtle">
                      {e.start_date} – {e.is_current ? "Present" : e.end_date || "—"}
                    </p>
                    {e.bullets.length > 0 && (
                      <ul className="mt-2 list-disc pl-5 flex flex-col gap-1 text-app-ink-2">
                        {e.bullets.map((b, i) => (
                          <li key={i}>{bulletText(b)}</li>
                        ))}
                      </ul>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </Card>

          <Card as="section" aria-labelledby="education">
            <CardHeader id="education" title="Education" />
            {data.educations.length === 0 ? (
              <p className="px-5 pb-5 text-app-muted">No education added yet.</p>
            ) : (
              <ul className="px-5 pb-5 flex flex-col gap-2">
                {data.educations.map((ed) => (
                  <li key={ed.id}>
                    <p className="font-medium">{[ed.degree, ed.field].filter(Boolean).join(", ")}</p>
                    <p className="text-app-muted">
                      {ed.institution}
                      {ed.grade && ` · ${ed.grade}`}
                    </p>
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </div>

        <div className="flex flex-col gap-6">
          <Card as="section" aria-labelledby="comp">
            <CardHeader id="comp" title="Compensation & notice" description="Used to fill Indian application forms." />
            <div className="px-5 pb-5 flex flex-col gap-4">
              <Field label="Current CTC (LPA)" htmlFor="p-ctc">
                <Input
                  id="p-ctc"
                  type="number"
                  min={0}
                  step="0.1"
                  value={form.current_ctc_lpa ?? ""}
                  onChange={(e) => set("current_ctc_lpa", num(e.target.value))}
                />
              </Field>
              <Field label="Expected CTC (LPA)" htmlFor="p-ectc">
                <Input
                  id="p-ectc"
                  type="number"
                  min={0}
                  step="0.1"
                  value={form.expected_ctc_lpa ?? ""}
                  onChange={(e) => set("expected_ctc_lpa", num(e.target.value))}
                />
              </Field>
              <Field label="Notice period (days)" htmlFor="p-notice">
                <Input
                  id="p-notice"
                  type="number"
                  min={0}
                  value={form.notice_period_days ?? ""}
                  onChange={(e) => set("notice_period_days", num(e.target.value))}
                />
              </Field>
              <Checkbox
                checked={Boolean(form.currently_serving_notice)}
                onChange={(v) => set("currently_serving_notice", v)}
                label="Currently serving notice"
              />
              <Checkbox
                checked={Boolean(form.willing_to_relocate)}
                onChange={(v) => set("willing_to_relocate", v)}
                label="Willing to relocate"
              />
            </div>
          </Card>

          <Card as="section" aria-labelledby="links">
            <CardHeader id="links" title="Links" />
            <div className="px-5 pb-5 flex flex-col gap-4">
              {(["linkedin", "github", "portfolio"] as const).map((k) => (
                <Field key={k} label={k === "linkedin" ? "LinkedIn" : k === "github" ? "GitHub" : "Portfolio"} htmlFor={`l-${k}`}>
                  <Input
                    id={`l-${k}`}
                    type="url"
                    placeholder="https://"
                    value={links[k] ?? ""}
                    onChange={(e) => setLinks((l) => ({ ...l, [k]: e.target.value }))}
                  />
                </Field>
              ))}
            </div>
          </Card>

          <Card as="section" aria-labelledby="skills">
            <CardHeader id="skills" title="Skills" />
            <div className="px-5 pb-5">
              <div className="flex flex-wrap gap-1.5">
                {data.skills.map((s) => (
                  <Badge key={s.id}>{s.name}</Badge>
                ))}
                {data.skills.length === 0 && <p className="text-app-muted">No skills yet.</p>}
              </div>
              <form
                className="mt-4 flex gap-2"
                onSubmit={(e) => {
                  e.preventDefault();
                  if (newSkill.trim()) addSkill.mutate(newSkill.trim());
                }}
              >
                <Input aria-label="New skill" placeholder="Add a skill" value={newSkill} onChange={(e) => setNewSkill(e.target.value)} />
                <Button type="submit" variant="secondary" loading={addSkill.isPending} disabled={!newSkill.trim()}>
                  Add
                </Button>
              </form>
            </div>
          </Card>
        </div>
      </div>

      {expOpen && <ExperienceDialog onClose={() => setExpOpen(false)} onSaved={invalidate} />}
    </>
  );
}

function ExperienceDialog({ onClose, onSaved }: { onClose: () => void; onSaved: () => void }) {
  const [company, setCompany] = useState("");
  const [title, setTitle] = useState("");
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [current, setCurrent] = useState(false);
  const [bullets, setBullets] = useState("");

  const save = useMutation({
    mutationFn: () =>
      api.profile.addExperience({
        company: company.trim(),
        title: title.trim(),
        start_date: start,
        end_date: current ? null : end || null,
        is_current: current,
        bullets: bullets
          .split("\n")
          .map((b) => b.replace(/^[-•*]\s*/, "").trim())
          .filter(Boolean)
          .map((text) => ({ text })),
      }),
    onSuccess: () => {
      toast.success("Experience added.");
      onSaved();
      onClose();
    },
    onError: (e) => toast.error(e.message),
  });

  return (
    <Dialog
      open
      onClose={onClose}
      title="Add experience"
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={() => save.mutate()} loading={save.isPending} disabled={!company.trim() || !title.trim() || !start}>
            Add experience
          </Button>
        </>
      }
    >
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Job title" htmlFor="x-title">
          <Input id="x-title" value={title} onChange={(e) => setTitle(e.target.value)} />
        </Field>
        <Field label="Company" htmlFor="x-company">
          <Input id="x-company" value={company} onChange={(e) => setCompany(e.target.value)} />
        </Field>
        <Field label="Start" htmlFor="x-start">
          <Input id="x-start" type="month" value={start} onChange={(e) => setStart(e.target.value)} />
        </Field>
        <Field label="End" htmlFor="x-end">
          <Input id="x-end" type="month" value={end} onChange={(e) => setEnd(e.target.value)} disabled={current} />
        </Field>
        <div className="sm:col-span-2">
          <Checkbox checked={current} onChange={setCurrent} label="I currently work here" />
        </div>
        <div className="sm:col-span-2">
          <Field label="What you did" htmlFor="x-bullets" hint="One achievement per line. Include real numbers where you have them.">
            <Textarea id="x-bullets" value={bullets} onChange={(e) => setBullets(e.target.value)} className="min-h-32" />
          </Field>
        </div>
      </div>
    </Dialog>
  );
}
