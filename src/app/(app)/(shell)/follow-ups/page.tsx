"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { BellRing, Copy, Mail, Send } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { toast } from "sonner";
import { Badge, Button, Card, Dialog, EmptyState, ErrorState, Field, Input, PageHeader, Select, SkeletonList, Textarea } from "@/components/app/ui";
import { api } from "@/lib/api/endpoints";
import type { ApplicationListItem } from "@/lib/api/types";
import { formatDate, statusLabel, statusTone } from "@/lib/format";

type Tone = "professional" | "friendly" | "direct";

export default function FollowUpsPage() {
  const list = useQuery({ queryKey: ["follow-ups"], queryFn: api.applications.followUps });
  const [drafting, setDrafting] = useState<ApplicationListItem | null>(null);

  return (
    <>
      <PageHeader
        title="Follow-ups"
        description="A short, polite follow-up after a week of silence noticeably improves response rates. We remind you and draft it; you send it."
      />
      {list.isPending ? (
        <SkeletonList rows={4} />
      ) : list.isError ? (
        <Card>
          <ErrorState error={list.error} onRetry={() => list.refetch()} />
        </Card>
      ) : list.data.due.length === 0 && list.data.upcoming.length === 0 ? (
        <Card>
          <EmptyState
            icon={BellRing}
            title="No follow-ups yet"
            description="When you submit an application, we schedule a follow-up reminder 6 days later."
          />
        </Card>
      ) : (
        <div className="flex flex-col gap-6">
          <Section title="Due now" items={list.data.due} onDraft={setDrafting} empty="Nothing due today." />
          <Section title="Coming up" items={list.data.upcoming} onDraft={setDrafting} empty="No upcoming follow-ups." />
        </div>
      )}
      {drafting && <DraftDialog app={drafting} onClose={() => setDrafting(null)} />}
    </>
  );
}

function Section({
  title,
  items,
  onDraft,
  empty,
}: {
  title: string;
  items: ApplicationListItem[];
  onDraft: (a: ApplicationListItem) => void;
  empty: string;
}) {
  return (
    <Card as="section" aria-label={title}>
      <div className="px-5 pt-5 pb-3">
        <h2 className="text-base font-medium">
          {title} <span className="font-mono text-app-muted">{items.length}</span>
        </h2>
      </div>
      {items.length === 0 ? (
        <p className="px-5 pb-5 text-app-muted">{empty}</p>
      ) : (
        <ul className="divide-y divide-app-border border-t border-app-border">
          {items.map((a) => (
            <li key={a.id} className="flex flex-col gap-3 px-5 py-4 sm:flex-row sm:items-center">
              <div className="min-w-0 flex-1">
                <Link href={`/applications/${a.id}`} className="font-medium hover:underline underline-offset-4">
                  {a.job_title}
                </Link>
                <p className="text-app-muted">
                  {a.company_name} · applied {formatDate(a.submitted_at)} · follow up {formatDate(a.follow_up_at)}
                </p>
              </div>
              <div className="flex items-center gap-2">
                <Badge tone={statusTone(a.status)}>{statusLabel(a.status)}</Badge>
                <Button size="sm" onClick={() => onDraft(a)}>
                  <Mail className="size-3.5" aria-hidden="true" />
                  Draft follow-up
                </Button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

function DraftDialog({ app, onClose }: { app: ApplicationListItem; onClose: () => void }) {
  const queryClient = useQueryClient();
  const [tone, setTone] = useState<Tone>("professional");
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [to, setTo] = useState("");

  const draft = useMutation({
    mutationFn: () => api.applications.draftFollowUp(app.id, tone),
    onSuccess: (d) => {
      setSubject(d.subject);
      setBody(d.body);
    },
    onError: (e) => toast.error(e.message),
  });
  const sent = useMutation({
    mutationFn: () => api.applications.followUpSent(app.id),
    onSuccess: (r) => {
      toast.success(r.follow_up_at ? `Marked as sent. We'll remind you again on ${formatDate(r.follow_up_at)}.` : "Marked as sent.");
      void queryClient.invalidateQueries({ queryKey: ["follow-ups"] });
      void queryClient.invalidateQueries({ queryKey: ["application", app.id] });
      onClose();
    },
    onError: (e) => toast.error(e.message),
  });

  const mailto = `mailto:${encodeURIComponent(to)}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;

  return (
    <Dialog
      open
      onClose={onClose}
      title={`Follow up: ${app.job_title}`}
      description={`${app.company_name}. Review and edit before sending from your own email.`}
      footer={
        <>
          <Button variant="ghost" onClick={() => sent.mutate()} loading={sent.isPending} disabled={!body}>
            <Send className="size-4" aria-hidden="true" />
            I&apos;ve sent it
          </Button>
          <a
            href={mailto}
            aria-disabled={!body}
            className="inline-flex h-10 items-center gap-2 rounded-app-md bg-app-ink px-4 text-sm font-medium text-app-card hover:bg-app-ink-2 aria-disabled:pointer-events-none aria-disabled:opacity-50"
          >
            <Mail className="size-4" aria-hidden="true" />
            Open in email
          </a>
        </>
      }
    >
      <div className="flex flex-col gap-4">
        <div className="flex items-end gap-2">
          <Field label="Tone" htmlFor="fu-tone">
            <Select id="fu-tone" value={tone} onChange={(e) => setTone(e.target.value as Tone)}>
              <option value="professional">Professional</option>
              <option value="friendly">Friendly</option>
              <option value="direct">Direct</option>
            </Select>
          </Field>
          <Button variant="secondary" onClick={() => draft.mutate()} loading={draft.isPending}>
            {body ? "Redraft" : "Write draft"}
          </Button>
        </div>
        <Field label="Recruiter email (optional)" htmlFor="fu-to">
          <Input id="fu-to" type="email" value={to} onChange={(e) => setTo(e.target.value)} placeholder="recruiter@company.com" />
        </Field>
        <Field label="Subject" htmlFor="fu-subject">
          <Input id="fu-subject" value={subject} onChange={(e) => setSubject(e.target.value)} />
        </Field>
        <Field label="Message" htmlFor="fu-body">
          <Textarea id="fu-body" value={body} onChange={(e) => setBody(e.target.value)} className="min-h-48" />
        </Field>
        {body && (
          <Button
            variant="ghost"
            size="sm"
            onClick={async () => {
              await navigator.clipboard.writeText(`${subject}\n\n${body}`);
              toast.success("Copied.");
            }}
          >
            <Copy className="size-3.5" aria-hidden="true" />
            Copy
          </Button>
        )}
      </div>
    </Dialog>
  );
}
