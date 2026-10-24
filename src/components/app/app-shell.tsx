"use client";

import { useQuery } from "@tanstack/react-query";
import {
  Bell,
  BellRing,
  Briefcase,
  ClipboardCheck,
  CreditCard,
  FileCheck2,
  LayoutDashboard,
  ListChecks,
  LogOut,
  Menu,
  MessageSquareText,
  Rocket,
  Settings,
  SlidersHorizontal,
  UserRound,
  X,
} from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { Suspense, useState } from "react";
import { api } from "@/lib/api/endpoints";
import { useAuth } from "@/lib/auth";
import { cn } from "@/lib/utils";
import { AppLogo } from "./logo";

const NAV = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/resume", label: "Resume & ATS", icon: FileCheck2 },
  { href: "/jobs", label: "Jobs", icon: Briefcase },
  { href: "/auto-apply", label: "Auto-apply", icon: Rocket },
  { href: "/review", label: "Review queue", icon: ClipboardCheck, badge: "review" as const },
  { href: "/applications", label: "Applications", icon: ListChecks },
  { href: "/follow-ups", label: "Follow-ups", icon: BellRing },
  { href: "/answers", label: "Answer bank", icon: MessageSquareText },
  { href: "/preferences", label: "Preferences", icon: SlidersHorizontal },
  { href: "/profile", label: "Profile", icon: UserRound },
  { href: "/billing", label: "Plan & credits", icon: CreditCard },
  { href: "/settings", label: "Settings", icon: Settings },
];

function isActive(pathname: string, href: string) {
  return pathname === href || pathname.startsWith(`${href}/`);
}

function NavList({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();
  const review = useQuery({ queryKey: ["review-queue", 1], queryFn: () => api.reviewQueue.list(1), staleTime: 60_000 });
  const reviewCount = review.data?.total ?? 0;

  return (
    <nav aria-label="Main" className="flex flex-col gap-0.5">
      {NAV.map(({ href, label, icon: Icon, badge }) => {
        const active = isActive(pathname, href);
        return (
          <Link
            key={href}
            href={href}
            onClick={onNavigate}
            aria-current={active ? "page" : undefined}
            className={cn(
              "flex items-center gap-3 rounded-app-md px-3 h-9 text-sm transition-colors duration-150",
              "outline-none focus-visible:ring-2 focus-visible:ring-app-accent",
              active ? "bg-app-card text-app-ink font-medium shadow-app-ring" : "text-app-ink-2 hover:bg-app-panel hover:text-app-ink"
            )}
          >
            <Icon className="size-4 shrink-0" aria-hidden="true" />
            <span className="flex-1">{label}</span>
            {badge === "review" && reviewCount > 0 && (
              <span className="rounded-full bg-app-accent px-1.5 font-mono text-xs text-app-ink" aria-label={`${reviewCount} waiting`}>
                {reviewCount}
              </span>
            )}
          </Link>
        );
      })}
    </nav>
  );
}

/** NavList reads the URL, so under Cache Components it renders inside Suspense with this as the fallback. */
function Nav({ onNavigate }: { onNavigate?: () => void }) {
  return (
    <Suspense
      fallback={
        <nav aria-label="Main" className="flex flex-col gap-0.5">
          {NAV.map(({ href, label, icon: Icon }) => (
            <Link key={href} href={href} className="flex items-center gap-3 rounded-app-md px-3 h-9 text-sm text-app-ink-2">
              <Icon className="size-4 shrink-0" aria-hidden="true" />
              {label}
            </Link>
          ))}
        </nav>
      }
    >
      <NavList onNavigate={onNavigate} />
    </Suspense>
  );
}

function CreditsPill() {
  const { data } = useQuery({ queryKey: ["credits"], queryFn: api.billing.balance, staleTime: 60_000 });
  if (!data?.apply_credits || !data.ai_credits) return null;
  return (
    <Link
      href="/billing"
      className="hidden sm:inline-flex items-center gap-1.5 rounded-full bg-app-card border border-app-border h-8 px-3 text-xs text-app-ink-2 hover:bg-app-panel outline-none focus-visible:ring-2 focus-visible:ring-app-accent"
    >
      <span className="size-1.5 rounded-full bg-app-accent" aria-hidden="true" />
      <span className="font-mono">{data.apply_credits.available}</span> apply ·{" "}
      <span className="font-mono">{data.ai_credits.available}</span> AI credits
    </Link>
  );
}

function NotificationsButton() {
  const { data } = useQuery({
    queryKey: ["notifications", "unread"],
    queryFn: () => api.notifications.list(true),
    refetchInterval: 60_000,
  });
  const unread = data?.unread_count ?? 0;
  return (
    <Link
      href="/notifications"
      aria-label={unread ? `Notifications, ${unread} unread` : "Notifications"}
      className="relative inline-flex size-9 items-center justify-center rounded-app-md text-app-ink-2 hover:bg-app-panel hover:text-app-ink outline-none focus-visible:ring-2 focus-visible:ring-app-accent"
    >
      <Bell className="size-4" aria-hidden="true" />
      {unread > 0 && (
        <span className="absolute right-1.5 top-1.5 size-2 rounded-full bg-app-accent ring-2 ring-app-bg" aria-hidden="true" />
      )}
    </Link>
  );
}

function UserMenu() {
  const { user, signOut } = useAuth();
  const router = useRouter();
  const initials = (user?.displayName || user?.email || "?").slice(0, 1).toUpperCase();
  return (
    <div className="flex items-center gap-2">
      <span
        className="size-8 rounded-full bg-app-surface text-app-ink flex items-center justify-center text-sm font-medium"
        aria-hidden="true"
      >
        {initials}
      </span>
      <span className="hidden md:block max-w-40 truncate text-sm text-app-ink-2">{user?.email}</span>
      <button
        type="button"
        onClick={async () => {
          await signOut();
          router.replace("/login");
        }}
        aria-label="Sign out"
        className="inline-flex size-9 items-center justify-center rounded-app-md text-app-ink-2 hover:bg-app-panel hover:text-app-ink outline-none focus-visible:ring-2 focus-visible:ring-app-accent"
      >
        <LogOut className="size-4" aria-hidden="true" />
      </button>
    </div>
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const { user } = useAuth();

  return (
    <div className="min-h-screen bg-app-bg text-app-ink text-sm font-body">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-app-md focus:bg-app-card focus:px-3 focus:py-2"
      >
        Skip to content
      </a>

      {/* Desktop sidebar */}
      <aside className="hidden lg:flex fixed inset-y-0 left-0 w-60 flex-col gap-6 border-r border-app-border bg-app-bg px-3 py-5">
        <AppLogo className="px-3" />
        <Nav />
      </aside>

      {/* Mobile drawer */}
      {mobileOpen && (
        <div className="lg:hidden fixed inset-0 z-40">
          <button
            type="button"
            aria-label="Close menu"
            className="absolute inset-0 bg-app-ink/30"
            onClick={() => setMobileOpen(false)}
          />
          <aside className="absolute inset-y-0 left-0 w-72 max-w-[85vw] flex flex-col gap-6 bg-app-bg px-3 py-5 shadow-app-side">
            <div className="flex items-center justify-between px-3">
              <AppLogo />
              <button
                type="button"
                aria-label="Close menu"
                onClick={() => setMobileOpen(false)}
                className="inline-flex size-9 items-center justify-center rounded-app-md hover:bg-app-panel outline-none focus-visible:ring-2 focus-visible:ring-app-accent"
              >
                <X className="size-4" aria-hidden="true" />
              </button>
            </div>
            <Nav onNavigate={() => setMobileOpen(false)} />
          </aside>
        </div>
      )}

      <div className="lg:pl-60">
        <header className="sticky top-0 z-30 flex h-14 items-center gap-2 border-b border-app-border bg-app-bg/90 backdrop-blur px-4 sm:px-6">
          <button
            type="button"
            aria-label="Open menu"
            onClick={() => setMobileOpen(true)}
            className="lg:hidden inline-flex size-9 items-center justify-center rounded-app-md hover:bg-app-panel outline-none focus-visible:ring-2 focus-visible:ring-app-accent"
          >
            <Menu className="size-4" aria-hidden="true" />
          </button>
          <AppLogo className="lg:hidden" />
          <div className="flex-1" />
          {user?.isDevUser && (
            <span className="hidden sm:inline rounded-full bg-app-surface px-2.5 py-1 text-xs text-app-ink-2">Dev login</span>
          )}
          <CreditsPill />
          <NotificationsButton />
          <UserMenu />
        </header>
        <main id="main" className="mx-auto w-full max-w-6xl px-4 sm:px-6 py-6 sm:py-8">
          {children}
        </main>
      </div>
    </div>
  );
}
