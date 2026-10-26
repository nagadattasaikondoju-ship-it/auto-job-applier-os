"use client";

import { Plus, X } from "lucide-react";
import { useId, useState } from "react";
import { cn } from "@/lib/utils";

/** Chips with suggestions plus free-text entry (Enter or comma adds a tag). */
export function TagInput({
  label,
  value,
  onChange,
  suggestions = [],
  placeholder = "Type and press Enter",
  max = 20,
}: {
  label: string;
  value: string[];
  onChange: (v: string[]) => void;
  suggestions?: string[];
  placeholder?: string;
  max?: number;
}) {
  const [draft, setDraft] = useState("");
  const inputId = useId();
  const has = (t: string) => value.some((v) => v.toLowerCase() === t.toLowerCase());

  function add(raw: string) {
    const t = raw.trim().replace(/,$/, "");
    if (!t || has(t) || value.length >= max) return;
    onChange([...value, t]);
    setDraft("");
  }

  const remaining = suggestions.filter((s) => !has(s));

  return (
    <div className="flex flex-col gap-3">
      <div
        className="flex min-h-11 flex-wrap items-center gap-1.5 rounded-app-md border border-app-border bg-app-card px-2 py-1.5 focus-within:border-app-accent focus-within:ring-2 focus-within:ring-app-accent/20"
        onClick={() => document.getElementById(inputId)?.focus()}
      >
        {value.map((t) => (
          <span key={t} className="inline-flex items-center gap-1 rounded-full bg-app-ink px-2.5 py-1 text-xs text-app-card">
            {t}
            <button
              type="button"
              aria-label={`Remove ${t}`}
              onClick={(e) => {
                e.stopPropagation();
                onChange(value.filter((v) => v !== t));
              }}
              className="rounded-full outline-none focus-visible:ring-2 focus-visible:ring-app-accent"
            >
              <X className="size-3" aria-hidden="true" />
            </button>
          </span>
        ))}
        <input
          id={inputId}
          aria-label={label}
          value={draft}
          placeholder={value.length ? "" : placeholder}
          onChange={(e) => {
            const v = e.target.value;
            if (v.endsWith(",")) add(v);
            else setDraft(v);
          }}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              add(draft);
            } else if (e.key === "Backspace" && !draft && value.length) {
              onChange(value.slice(0, -1));
            }
          }}
          onBlur={() => draft && add(draft)}
          className="min-w-32 flex-1 bg-transparent px-1 py-1 text-sm text-app-ink outline-none placeholder:text-app-subtle"
        />
      </div>
      {remaining.length > 0 && (
        <div className="flex flex-wrap gap-1.5" aria-label={`Suggested ${label.toLowerCase()}`}>
          {remaining.slice(0, 14).map((s) => (
            <button
              key={s}
              type="button"
              onClick={() => add(s)}
              disabled={value.length >= max}
              className={cn(
                "inline-flex items-center gap-1 rounded-full border border-app-border bg-app-card px-3 h-8 text-sm text-app-ink-2",
                "hover:bg-app-panel outline-none focus-visible:ring-2 focus-visible:ring-app-accent disabled:opacity-50"
              )}
            >
              <Plus className="size-3" aria-hidden="true" />
              {s}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

/** Toggle chips for a fixed set of options. */
export function ChipGroup<T extends string>({
  label,
  options,
  value,
  onChange,
  multiple = true,
}: {
  label: string;
  options: { value: T; label: string; description?: string }[];
  value: T[];
  onChange: (v: T[]) => void;
  multiple?: boolean;
}) {
  return (
    <div role={multiple ? "group" : "radiogroup"} aria-label={label} className="flex flex-wrap gap-2">
      {options.map((o) => {
        const on = value.includes(o.value);
        return (
          <button
            key={o.value}
            type="button"
            role={multiple ? undefined : "radio"}
            aria-pressed={multiple ? on : undefined}
            aria-checked={multiple ? undefined : on}
            onClick={() => onChange(multiple ? (on ? value.filter((v) => v !== o.value) : [...value, o.value]) : [o.value])}
            className={cn(
              "rounded-app-lg border px-4 py-2.5 text-left text-sm transition-colors outline-none focus-visible:ring-2 focus-visible:ring-app-accent",
              on ? "border-app-ink bg-app-ink text-app-card" : "border-app-border bg-app-card text-app-ink-2 hover:bg-app-panel"
            )}
          >
            <span className="block font-medium">{o.label}</span>
            {o.description && <span className={cn("block text-xs", on ? "text-app-line" : "text-app-muted")}>{o.description}</span>}
          </button>
        );
      })}
    </div>
  );
}
