"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Pencil } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { api } from "@/lib/api/endpoints";
import type { ResolvedField } from "@/lib/api/types";
import { cn } from "@/lib/utils";
import { Badge, Button, Checkbox, Input, Textarea } from "./ui";

const SOURCE_LABEL: Record<string, string> = {
  profile: "From profile",
  answer_bank: "Saved answer",
  ai: "AI draft",
  user: "Your edit",
  unresolved: "Needs answer",
};

function displayValue(v: unknown): string {
  if (v === null || v === undefined || v === "") return "";
  if (typeof v === "boolean") return v ? "Yes" : "No";
  if (Array.isArray(v)) return v.join(", ");
  return String(v);
}

/** The resolved form answers for one application, with inline editing. */
export function AnswerPlan({ applicationId, fields }: { applicationId: string; fields: ResolvedField[] }) {
  if (fields.length === 0) {
    return <p className="px-5 pb-5 text-app-muted">No form questions were detected for this application.</p>;
  }
  // Fields needing attention first
  const sorted = [...fields].sort((a, b) => Number(b.needs_review) - Number(a.needs_review));
  return (
    <ul className="divide-y divide-app-border">
      {sorted.map((f) => (
        <AnswerRow key={f.field_id} applicationId={applicationId} field={f} />
      ))}
    </ul>
  );
}

function AnswerRow({ applicationId, field }: { applicationId: string; field: ResolvedField }) {
  const queryClient = useQueryClient();
  const [editing, setEditing] = useState(false);
  const [value, setValue] = useState(displayValue(field.value));
  const [saveToBank, setSaveToBank] = useState(true);

  const save = useMutation({
    mutationFn: () => api.reviewQueue.editAnswer(applicationId, field.field_id, value, saveToBank),
    onSuccess: () => {
      toast.success(saveToBank ? "Saved and added to your answer bank." : "Answer saved.");
      setEditing(false);
      void queryClient.invalidateQueries({ queryKey: ["review-queue"] });
      void queryClient.invalidateQueries({ queryKey: ["application", applicationId] });
      if (saveToBank) void queryClient.invalidateQueries({ queryKey: ["answers"] });
    },
    onError: (e) => toast.error(e.message),
  });

  const current = displayValue(field.value);
  const isLong = field.field_type === "textarea" || current.length > 80;
  const isFile = field.field_type === "file";
  const unresolved = field.source === "unresolved" || current === "";

  return (
    <li className={cn("px-5 py-4", field.needs_review && "bg-app-bg")}>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <p className="font-medium text-app-ink">
            {field.label}
            {field.required && (
              <span className="text-app-danger" aria-label="required">
                {" "}
                *
              </span>
            )}
          </p>
          {!editing && (
            <p className={cn("mt-1 whitespace-pre-line", unresolved ? "text-app-muted italic" : "text-app-ink-2")}>
              {unresolved ? (field.required ? "No answer yet" : "Left blank (optional)") : current}
            </p>
          )}
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <Badge tone={unresolved ? (field.required ? "danger" : "neutral") : field.source === "ai" ? "warning" : "success"}>
            {unresolved && !field.required ? "Optional" : SOURCE_LABEL[field.source] ?? field.source}
            {field.source === "ai" && field.confidence > 0 && (
              <span className="font-mono">{Math.round(field.confidence * 100)}%</span>
            )}
          </Badge>
          {!editing && !isFile && (
            <Button variant="ghost" size="sm" onClick={() => setEditing(true)} aria-label={`Edit answer for ${field.label}`}>
              <Pencil className="size-3.5" aria-hidden="true" />
            </Button>
          )}
        </div>
      </div>

      {editing && (
        <form
          className="mt-3 flex flex-col gap-3"
          onSubmit={(e) => {
            e.preventDefault();
            save.mutate();
          }}
        >
          {field.options.length > 0 ? (
            <select
              aria-label={field.label}
              value={value}
              onChange={(e) => setValue(e.target.value)}
              className="h-10 rounded-app-md border border-app-border bg-app-card px-3 text-sm"
            >
              <option value="">Choose…</option>
              {field.options.map((o) => (
                <option key={o}>{o}</option>
              ))}
            </select>
          ) : isLong ? (
            <Textarea aria-label={field.label} value={value} onChange={(e) => setValue(e.target.value)} autoFocus />
          ) : (
            <Input aria-label={field.label} value={value} onChange={(e) => setValue(e.target.value)} autoFocus />
          )}
          <Checkbox checked={saveToBank} onChange={setSaveToBank} label="Remember this answer for future applications" />
          <div className="flex gap-2">
            <Button type="submit" size="sm" loading={save.isPending}>
              Save answer
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                setValue(current);
                setEditing(false);
              }}
            >
              Cancel
            </Button>
          </div>
        </form>
      )}
    </li>
  );
}
