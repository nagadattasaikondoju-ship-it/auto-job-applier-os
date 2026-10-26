import type { ApplicationStatus } from "@/lib/api/types";

export function formatSalary(min: number | null | undefined, max: number | null | undefined): string | null {
  if (!min && !max) return null;
  if (min && max) return min === max ? `₹${min} LPA` : `₹${min}–${max} LPA`;
  return `₹${min ?? max} LPA`;
}

export function timeAgo(iso: string | null | undefined): string {
  if (!iso) return "";
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.round(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.round(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.round(hrs / 24);
  if (days < 30) return `${days}d ago`;
  return new Date(iso).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });
}

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });
}

export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("en-IN", {
    day: "numeric",
    month: "short",
    hour: "numeric",
    minute: "2-digit",
  });
}

export const STATUS_META: Record<ApplicationStatus, { label: string; tone: Tone }> = {
  draft: { label: "Draft", tone: "neutral" },
  preparing: { label: "Preparing", tone: "info" },
  ready_for_review: { label: "Ready for review", tone: "accent" },
  approved: { label: "Approved", tone: "info" },
  submitting: { label: "Submitting", tone: "info" },
  submitted: { label: "Applied", tone: "success" },
  needs_user_action: { label: "Needs your action", tone: "warning" },
  failed: { label: "Failed", tone: "danger" },
  withdrawn: { label: "Withdrawn", tone: "neutral" },
  interview: { label: "Interview", tone: "accent" },
  offer: { label: "Offer", tone: "success" },
  rejected: { label: "Rejected", tone: "danger" },
  ghosted: { label: "No response", tone: "neutral" },
};

export type Tone = "neutral" | "info" | "accent" | "success" | "warning" | "danger";

export function statusLabel(status: string): string {
  return STATUS_META[status as ApplicationStatus]?.label ?? status.replace(/_/g, " ");
}

export function statusTone(status: string): Tone {
  return STATUS_META[status as ApplicationStatus]?.tone ?? "neutral";
}

export function scoreTone(score: number): Tone {
  if (score >= 80) return "success";
  if (score >= 60) return "warning";
  return "danger";
}

export function humanize(key: string): string {
  return key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}
