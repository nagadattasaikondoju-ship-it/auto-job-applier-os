"use client";

import { Check } from "lucide-react";
import type { Question } from "@/lib/api/types";
import { humanize } from "@/lib/format";
import { cn } from "@/lib/utils";
import { Input, Textarea } from "./ui";

const chip =
  "inline-flex items-center gap-1.5 rounded-full border px-3.5 h-9 text-sm transition-colors duration-150 outline-none focus-visible:ring-2 focus-visible:ring-app-accent";

function optionLabel(o: string) {
  // Options like "fresher" or "remote" read better capitalised; leave proper names alone.
  return /^[a-z_]+$/.test(o) ? humanize(o) : o;
}

/** Renders the right control for an onboarding / screening question type. */
export function QuestionInput({
  question,
  value,
  onChange,
  autoFocus,
}: {
  question: Question;
  value: unknown;
  onChange: (v: unknown) => void;
  autoFocus?: boolean;
}) {
  const { type, options = [] } = question;
  const label = question.text;

  if (type === "multi_select") {
    const selected = Array.isArray(value) ? (value as string[]) : [];
    return (
      <div role="group" aria-label={label} className="flex flex-wrap gap-2">
        {options.map((o) => {
          const on = selected.includes(o);
          return (
            <button
              key={o}
              type="button"
              aria-pressed={on}
              onClick={() => onChange(on ? selected.filter((s) => s !== o) : [...selected, o])}
              className={cn(
                chip,
                on ? "border-app-ink bg-app-ink text-app-card" : "border-app-border bg-app-card text-app-ink-2 hover:bg-app-panel"
              )}
            >
              {on && <Check className="size-3.5" aria-hidden="true" />}
              {optionLabel(o)}
            </button>
          );
        })}
      </div>
    );
  }

  if (type === "choice") {
    return (
      <div role="radiogroup" aria-label={label} className="flex flex-wrap gap-2">
        {options.map((o) => {
          const on = value === o;
          return (
            <button
              key={o}
              type="button"
              role="radio"
              aria-checked={on}
              onClick={() => onChange(o)}
              className={cn(
                chip,
                on ? "border-app-ink bg-app-ink text-app-card" : "border-app-border bg-app-card text-app-ink-2 hover:bg-app-panel"
              )}
            >
              {optionLabel(o)}
            </button>
          );
        })}
      </div>
    );
  }

  if (type === "boolean") {
    return (
      <div role="radiogroup" aria-label={label} className="flex gap-2">
        {[
          { v: true, l: "Yes" },
          { v: false, l: "No" },
        ].map(({ v, l }) => {
          const on = value === v;
          return (
            <button
              key={l}
              type="button"
              role="radio"
              aria-checked={on}
              onClick={() => onChange(v)}
              className={cn(
                chip,
                "min-w-20 justify-center",
                on ? "border-app-ink bg-app-ink text-app-card" : "border-app-border bg-app-card text-app-ink-2 hover:bg-app-panel"
              )}
            >
              {l}
            </button>
          );
        })}
      </div>
    );
  }

  if (type === "long_text") {
    return (
      <Textarea
        aria-label={label}
        autoFocus={autoFocus}
        value={(value as string) ?? ""}
        onChange={(e) => onChange(e.target.value)}
        className="min-h-40"
        placeholder={question.placeholder ?? "Write a few sentences. You can edit this any time in your answer bank."}
      />
    );
  }

  const isNumber = type === "number";
  const isMoney = /ctc|salary/i.test(question.id);
  return (
    <div className="flex items-center gap-2 max-w-sm">
      <Input
        aria-label={label}
        autoFocus={autoFocus}
        type={isNumber ? "number" : type === "date" ? "date" : "text"}
        inputMode={isNumber ? "decimal" : undefined}
        min={isNumber ? 0 : undefined}
        value={(value as string | number | undefined) ?? ""}
        onChange={(e) => onChange(e.target.value)}
        placeholder={question.placeholder}
      />
      {isNumber && <span className="text-sm text-app-muted whitespace-nowrap">{isMoney ? "LPA" : /notice/i.test(question.id) ? "days" : ""}</span>}
    </div>
  );
}
