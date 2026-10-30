"use client";

import { AlertCircle, Inbox, Loader2, X } from "lucide-react";
import Link from "next/link";
import { forwardRef, useEffect, useId, useRef, useState } from "react";
import { cn } from "@/lib/utils";
import type { Tone } from "@/lib/format";

// Shared building blocks for the logged-in app. All colours come from the `app-*` tokens in globals.css.

const focusRing =
  "outline-none focus-visible:ring-2 focus-visible:ring-app-accent focus-visible:ring-offset-2 focus-visible:ring-offset-app-bg";

type ButtonVariant = "primary" | "secondary" | "ghost" | "accent" | "danger";
type ButtonSize = "sm" | "md" | "lg";

const buttonVariants: Record<ButtonVariant, string> = {
  primary: "bg-app-ink text-app-card hover:bg-app-ink-2 active:bg-app-dark",
  accent: "bg-app-accent text-app-ink hover:brightness-95 active:brightness-90",
  secondary:
    "bg-app-card text-app-ink shadow-app-ring border border-app-border hover:bg-app-panel active:bg-app-surface",
  ghost: "bg-transparent text-app-ink-2 hover:bg-app-panel hover:text-app-ink active:bg-app-surface",
  danger: "bg-app-card text-app-danger border border-app-border hover:bg-app-panel",
};

const buttonSizes: Record<ButtonSize, string> = {
  sm: "h-8 px-3 text-xs gap-1.5",
  md: "h-10 px-4 text-sm gap-2",
  lg: "h-12 px-5 text-base gap-2",
};

export function buttonClass(variant: ButtonVariant = "primary", size: ButtonSize = "md", className?: string) {
  return cn(
    "inline-flex items-center justify-center rounded-app-md font-medium whitespace-nowrap transition-colors duration-150",
    "disabled:opacity-50 disabled:pointer-events-none",
    focusRing,
    buttonVariants[variant],
    buttonSizes[size],
    className
  );
}

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant = "primary", size = "md", loading, className, children, disabled, type = "button", ...props },
  ref
) {
  return (
    <button
      ref={ref}
      type={type}
      className={buttonClass(variant, size, className)}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      {...props}
    >
      {loading && <Loader2 className="size-4 animate-spin" aria-hidden="true" />}
      {children}
    </button>
  );
});

export function ButtonLink({
  href,
  variant = "primary",
  size = "md",
  className,
  children,
  external,
}: {
  href: string;
  variant?: ButtonVariant;
  size?: ButtonSize;
  className?: string;
  children: React.ReactNode;
  external?: boolean;
}) {
  if (external) {
    return (
      <a href={href} target="_blank" rel="noopener noreferrer" className={buttonClass(variant, size, className)}>
        {children}
      </a>
    );
  }
  return (
    <Link href={href} className={buttonClass(variant, size, className)}>
      {children}
    </Link>
  );
}

export function Card({
  className,
  children,
  as: Tag = "div",
  ...props
}: React.HTMLAttributes<HTMLElement> & { as?: "div" | "section" | "article" | "li" }) {
  return (
    <Tag className={cn("rounded-app-xl bg-app-card border border-app-border", className)} {...props}>
      {children}
    </Tag>
  );
}

export function CardHeader({
  title,
  description,
  action,
  id,
}: {
  title: string;
  description?: string;
  action?: React.ReactNode;
  id?: string;
}) {
  return (
    <div className="flex items-start justify-between gap-4 px-5 pt-5 pb-3">
      <div className="min-w-0">
        <h2 id={id} className="text-base font-medium text-app-ink">
          {title}
        </h2>
        {description && <p className="mt-0.5 text-sm text-app-muted">{description}</p>}
      </div>
      {action && <div className="shrink-0">{action}</div>}
    </div>
  );
}

const toneClasses: Record<Tone, string> = {
  neutral: "bg-app-panel text-app-ink-2",
  info: "bg-app-surface text-app-ink",
  accent: "bg-app-accent/15 text-app-ink",
  success: "bg-app-accent/15 text-app-ink",
  warning: "bg-app-surface text-app-ink",
  danger: "bg-app-danger/10 text-app-danger",
};

export function Badge({ tone = "neutral", children, className }: { tone?: Tone; children: React.ReactNode; className?: string }) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium whitespace-nowrap",
        toneClasses[tone],
        className
      )}
    >
      {children}
    </span>
  );
}

export function PageHeader({
  title,
  description,
  actions,
}: {
  title: string;
  description?: string;
  actions?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between mb-6">
      <div className="min-w-0">
        <h1 className="font-display text-3xl sm:text-4xl leading-tight text-app-ink">{title}</h1>
        {description && <p className="mt-1 text-sm text-app-muted max-w-2xl">{description}</p>}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </div>
  );
}

const fieldBase = cn(
  "w-full rounded-app-md bg-app-card border border-app-border text-sm text-app-ink placeholder:text-app-subtle",
  "transition-colors duration-150 hover:border-app-line disabled:opacity-50 disabled:cursor-not-allowed",
  "outline-none focus-visible:border-app-accent focus-visible:ring-2 focus-visible:ring-app-accent/20",
  "aria-[invalid=true]:border-app-danger"
);

export const Input = forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(function Input(
  { className, ...props },
  ref
) {
  return <input ref={ref} className={cn(fieldBase, "h-10 px-3", className)} {...props} />;
});

export const Textarea = forwardRef<HTMLTextAreaElement, React.TextareaHTMLAttributes<HTMLTextAreaElement>>(
  function Textarea({ className, ...props }, ref) {
    return <textarea ref={ref} className={cn(fieldBase, "px-3 py-2.5 min-h-24 leading-relaxed", className)} {...props} />;
  }
);

export const Select = forwardRef<HTMLSelectElement, React.SelectHTMLAttributes<HTMLSelectElement>>(function Select(
  { className, children, ...props },
  ref
) {
  return (
    <select ref={ref} className={cn(fieldBase, "h-10 px-3 pr-8", className)} {...props}>
      {children}
    </select>
  );
});

export function Field({
  label,
  hint,
  error,
  children,
  htmlFor,
}: {
  label: string;
  hint?: string;
  error?: string;
  children: React.ReactNode;
  htmlFor?: string;
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={htmlFor} className="text-sm font-medium text-app-ink">
        {label}
      </label>
      {children}
      {error ? (
        <p className="text-xs text-app-danger" role="alert">
          {error}
        </p>
      ) : (
        hint && <p className="text-xs text-app-muted">{hint}</p>
      )}
    </div>
  );
}

/** Shown on page loads that wait on the API, once they take longer than a few seconds. */
export const SERVER_WAKING_HINT =
  "Waking up the server. After a quiet spell the first load can take up to a minute; it's quick after that.";

export function Spinner({
  label = "Loading",
  slowHint,
  slowAfterMs = 6000,
}: {
  label?: string;
  /** Extra line shown once loading takes longer than slowAfterMs. */
  slowHint?: string;
  slowAfterMs?: number;
}) {
  const [slow, setSlow] = useState(false);
  useEffect(() => {
    if (!slowHint) return;
    const t = setTimeout(() => setSlow(true), slowAfterMs);
    return () => clearTimeout(t);
  }, [slowHint, slowAfterMs]);
  return (
    <div role="status" className="flex flex-col items-center justify-center gap-2 py-12 text-sm text-app-muted">
      <span className="flex items-center gap-2">
        <Loader2 className="size-4 animate-spin" aria-hidden="true" />
        {label}…
      </span>
      {slow && slowHint && <span className="max-w-sm text-center text-xs text-app-subtle">{slowHint}</span>}
    </div>
  );
}

export function Skeleton({ className }: { className?: string }) {
  return <div aria-hidden="true" className={cn("animate-pulse rounded-app-md bg-app-panel", className)} />;
}

export function SkeletonList({ rows = 4 }: { rows?: number }) {
  return (
    <div className="flex flex-col gap-3" role="status" aria-label="Loading">
      {Array.from({ length: rows }).map((_, i) => (
        <Skeleton key={i} className="h-20 w-full rounded-app-xl" />
      ))}
    </div>
  );
}

export function EmptyState({
  icon: Icon = Inbox,
  title,
  description,
  action,
}: {
  icon?: React.ComponentType<{ className?: string }>;
  title: string;
  description?: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col items-center text-center py-14 px-6">
      <div className="size-12 rounded-app-lg bg-app-surface flex items-center justify-center mb-4">
        <Icon className="size-5 text-app-ink-2" aria-hidden="true" />
      </div>
      <h3 className="text-base font-medium text-app-ink">{title}</h3>
      {description && <p className="mt-1 text-sm text-app-muted max-w-sm">{description}</p>}
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}

export function ErrorState({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const message = error instanceof Error ? error.message : "Something went wrong.";
  return (
    <div role="alert" className="flex flex-col items-center text-center py-12 px-6">
      <AlertCircle className="size-6 text-app-danger mb-3" aria-hidden="true" />
      <p className="text-sm font-medium text-app-ink">Couldn&apos;t load this</p>
      <p className="mt-1 text-sm text-app-muted max-w-md">{message}</p>
      {onRetry && (
        <Button variant="secondary" size="sm" className="mt-4" onClick={onRetry}>
          Try again
        </Button>
      )}
    </div>
  );
}

export function ScoreRing({ score, size = 56 }: { score: number; size?: number }) {
  const stroke = size >= 80 ? 7 : 5;
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const clamped = Math.max(0, Math.min(100, score));
  const color = clamped >= 80 ? "stroke-app-accent" : clamped >= 60 ? "stroke-app-dark" : "stroke-app-subtle";
  return (
    <div
      className="relative shrink-0"
      style={{ width: size, height: size }}
      role="img"
      aria-label={`Fit score ${clamped} out of 100`}
    >
      <svg width={size} height={size} className="-rotate-90" aria-hidden="true">
        <circle cx={size / 2} cy={size / 2} r={r} strokeWidth={stroke} className="fill-none stroke-app-panel" />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={c}
          strokeDashoffset={c - (clamped / 100) * c}
          className={cn("fill-none transition-[stroke-dashoffset] duration-500", color)}
        />
      </svg>
      <span
        className={cn(
          "absolute inset-0 flex items-center justify-center font-mono font-medium text-app-ink",
          size >= 80 ? "text-xl" : "text-sm"
        )}
      >
        {clamped}
      </span>
    </div>
  );
}

export function ProgressBar({ value, label }: { value: number; label?: string }) {
  const v = Math.max(0, Math.min(100, value));
  return (
    <div
      role="progressbar"
      aria-valuenow={v}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-label={label}
      className="h-1.5 w-full rounded-full bg-app-panel overflow-hidden"
    >
      <div className="h-full rounded-full bg-app-accent transition-[width] duration-300" style={{ width: `${v}%` }} />
    </div>
  );
}

export function Stat({ label, value, hint }: { label: string; value: React.ReactNode; hint?: string }) {
  return (
    <Card className="p-5">
      <p className="text-sm text-app-muted">{label}</p>
      <p className="mt-2 font-mono text-3xl text-app-ink">{value}</p>
      {hint && <p className="mt-1 text-xs text-app-subtle">{hint}</p>}
    </Card>
  );
}

/** Accessible modal dialog using the native <dialog> element (focus trap + Escape for free). */
export function Dialog({
  open,
  onClose,
  title,
  description,
  children,
  footer,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  description?: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  const titleId = useId();

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (open && !el.open) el.showModal();
    if (!open && el.open) el.close();
  }, [open]);

  return (
    <dialog
      ref={ref}
      aria-labelledby={titleId}
      onClose={onClose}
      onClick={(e) => {
        if (e.target === ref.current) onClose();
      }}
      className="m-auto w-[calc(100%-2rem)] max-w-lg rounded-app-xl bg-app-card p-0 text-app-ink shadow-app-side backdrop:bg-app-ink/30"
    >
      <div className="flex items-start justify-between gap-4 px-5 pt-5">
        <div>
          <h2 id={titleId} className="text-lg font-medium">
            {title}
          </h2>
          {description && <p className="mt-1 text-sm text-app-muted">{description}</p>}
        </div>
        <button
          type="button"
          onClick={onClose}
          aria-label="Close"
          className={cn("rounded-app-sm p-1 text-app-muted hover:bg-app-panel hover:text-app-ink", focusRing)}
        >
          <X className="size-4" aria-hidden="true" />
        </button>
      </div>
      <div className="px-5 py-4">{children}</div>
      {footer && <div className="flex justify-end gap-2 border-t border-app-border px-5 py-4">{footer}</div>}
    </dialog>
  );
}

export function Tabs<T extends string>({
  value,
  onChange,
  items,
  label,
}: {
  value: T;
  onChange: (v: T) => void;
  items: { value: T; label: string; count?: number }[];
  label: string;
}) {
  return (
    <div role="tablist" aria-label={label} className="flex gap-1 overflow-x-auto pb-1 -mb-1">
      {items.map((item) => {
        const active = item.value === value;
        return (
          <button
            key={item.value}
            role="tab"
            type="button"
            aria-selected={active}
            onClick={() => onChange(item.value)}
            className={cn(
              "inline-flex items-center gap-1.5 rounded-full px-3 h-8 text-sm whitespace-nowrap transition-colors duration-150",
              focusRing,
              active ? "bg-app-ink text-app-card" : "text-app-ink-2 hover:bg-app-panel"
            )}
          >
            {item.label}
            {item.count !== undefined && (
              <span className={cn("font-mono text-xs", active ? "text-app-line" : "text-app-subtle")}>{item.count}</span>
            )}
          </button>
        );
      })}
    </div>
  );
}

export function Checkbox({
  checked,
  onChange,
  label,
  description,
  id,
  disabled,
}: {
  checked: boolean;
  onChange: (v: boolean) => void;
  label: string;
  description?: string;
  id?: string;
  disabled?: boolean;
}) {
  const autoId = useId();
  const inputId = id ?? autoId;
  return (
    <label htmlFor={inputId} className={cn("flex gap-3 items-start cursor-pointer", disabled && "opacity-50 cursor-not-allowed")}>
      <input
        id={inputId}
        type="checkbox"
        checked={checked}
        disabled={disabled}
        onChange={(e) => onChange(e.target.checked)}
        className="mt-0.5 size-4 shrink-0 rounded-app-sm accent-app-accent"
      />
      <span>
        <span className="block text-sm font-medium text-app-ink">{label}</span>
        {description && <span className="block text-sm text-app-muted">{description}</span>}
      </span>
    </label>
  );
}
