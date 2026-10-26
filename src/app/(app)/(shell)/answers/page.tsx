"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { MessageSquareText, Pencil, Plus, Search } from "lucide-react";
import { useMemo, useState } from "react";
import { toast } from "sonner";
import { Badge, Button, Card, Dialog, EmptyState, ErrorState, Field, Input, PageHeader, SkeletonList, Textarea } from "@/components/app/ui";
import { api } from "@/lib/api/endpoints";
import type { Answer } from "@/lib/api/types";

const SOURCE_LABEL: Record<string, string> = {
  questionnaire: "From onboarding",
  user_edit: "Edited by you",
  ai_approved: "AI, approved",
};

function toKey(text: string) {
  return text
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_|_$/g, "")
    .slice(0, 60);
}

export default function AnswersPage() {
  const answers = useQuery({ queryKey: ["answers"], queryFn: api.answers.list });
  const [search, setSearch] = useState("");
  const [editing, setEditing] = useState<Answer | "new" | null>(null);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    const list = answers.data ?? [];
    return q ? list.filter((a) => `${a.question_text} ${a.answer_text}`.toLowerCase().includes(q)) : list;
  }, [answers.data, search]);

  return (
    <>
      <PageHeader
        title="Answer bank"
        description="Your saved answers to common application questions. Applyon reuses these so most forms fill in without AI."
        actions={
          <Button onClick={() => setEditing("new")}>
            <Plus className="size-4" aria-hidden="true" />
            Add answer
          </Button>
        }
      />

      <div className="relative mb-5 max-w-md">
        <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-app-subtle" aria-hidden="true" />
        <Input
          aria-label="Search answers"
          placeholder="Search questions and answers"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="pl-9"
        />
      </div>

      {answers.isPending ? (
        <SkeletonList rows={5} />
      ) : answers.isError ? (
        <Card>
          <ErrorState error={answers.error} onRetry={() => answers.refetch()} />
        </Card>
      ) : filtered.length === 0 ? (
        <Card>
          <EmptyState
            icon={MessageSquareText}
            title={search ? "No answers match that search" : "No saved answers yet"}
            description={
              search
                ? "Try a different word."
                : "Answers you give in onboarding or edit in the review queue are saved here automatically."
            }
            action={!search && <Button onClick={() => setEditing("new")}>Add your first answer</Button>}
          />
        </Card>
      ) : (
        <ul className="flex flex-col gap-3">
          {filtered.map((a) => (
            <li key={a.id}>
              <Card className="p-5">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="font-medium">{a.question_text}</p>
                    <p className="mt-1.5 whitespace-pre-line text-app-ink-2 line-clamp-4">{a.answer_text}</p>
                    <div className="mt-3 flex flex-wrap gap-1.5">
                      <Badge>{SOURCE_LABEL[a.source] ?? a.source}</Badge>
                      {a.times_used > 0 && <Badge tone="success">Used {a.times_used}×</Badge>}
                    </div>
                  </div>
                  <Button variant="ghost" size="sm" onClick={() => setEditing(a)} aria-label={`Edit answer: ${a.question_text}`}>
                    <Pencil className="size-3.5" aria-hidden="true" />
                    Edit
                  </Button>
                </div>
              </Card>
            </li>
          ))}
        </ul>
      )}

      {editing && <AnswerDialog answer={editing === "new" ? null : editing} onClose={() => setEditing(null)} />}
    </>
  );
}

function AnswerDialog({ answer, onClose }: { answer: Answer | null; onClose: () => void }) {
  const queryClient = useQueryClient();
  const [question, setQuestion] = useState(answer?.question_text ?? "");
  const [text, setText] = useState(answer?.answer_text ?? "");

  const save = useMutation({
    mutationFn: () =>
      api.answers.upsert({
        question_key: answer?.question_key ?? toKey(question),
        question_text: question.trim(),
        answer_text: text.trim(),
        answer_type: text.length > 120 ? "long" : "short",
      }),
    onSuccess: () => {
      toast.success("Answer saved.");
      void queryClient.invalidateQueries({ queryKey: ["answers"] });
      onClose();
    },
    onError: (e) => toast.error(e.message),
  });

  return (
    <Dialog
      open
      onClose={onClose}
      title={answer ? "Edit answer" : "Add an answer"}
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={() => save.mutate()} loading={save.isPending} disabled={!question.trim() || !text.trim()}>
            Save
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-4">
        <Field label="Question" htmlFor="ans-q">
          <Input
            id="ans-q"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            disabled={Boolean(answer)}
            placeholder="e.g. Why do you want to work here?"
          />
        </Field>
        <Field label="Your answer" htmlFor="ans-a">
          <Textarea id="ans-a" value={text} onChange={(e) => setText(e.target.value)} className="min-h-40" />
        </Field>
      </div>
    </Dialog>
  );
}
