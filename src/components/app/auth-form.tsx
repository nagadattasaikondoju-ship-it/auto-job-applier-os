"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { authErrorMessage, useAuth } from "@/lib/auth";
import { AppLogo } from "./logo";
import { Button, Field, Input } from "./ui";

function nextPath(fallback: string) {
  if (typeof window === "undefined") return fallback;
  const next = new URLSearchParams(window.location.search).get("next");
  // Only allow internal paths
  return next && next.startsWith("/") && !next.startsWith("//") ? next : fallback;
}

export function AuthForm({ mode }: { mode: "login" | "signup" }) {
  const { user, loading, firebaseEnabled, signInWithGoogle, signInWithEmail, signUpWithEmail, resetPassword, signInAsDevUser } =
    useAuth();
  const router = useRouter();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState<"email" | "google" | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!loading && user) router.replace(nextPath(mode === "signup" ? "/onboarding" : "/dashboard"));
  }, [loading, user, router, mode]);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy("email");
    try {
      if (mode === "signup") await signUpWithEmail(name.trim(), email.trim(), password);
      else await signInWithEmail(email.trim(), password);
    } catch (err) {
      setError(authErrorMessage(err));
    } finally {
      setBusy(null);
    }
  }

  async function onGoogle() {
    setError(null);
    setBusy("google");
    try {
      await signInWithGoogle();
    } catch (err) {
      setError(authErrorMessage(err));
    } finally {
      setBusy(null);
    }
  }

  async function onReset() {
    if (!email) {
      setError("Enter your email first, then click “Forgot password”.");
      return;
    }
    try {
      await resetPassword(email.trim());
      toast.success("Password reset email sent.");
    } catch (err) {
      setError(authErrorMessage(err));
    }
  }

  const isSignup = mode === "signup";

  return (
    <div className="min-h-screen bg-app-bg text-app-ink text-sm flex flex-col">
      <header className="px-6 py-5">
        <AppLogo href="/" />
      </header>
      <main className="flex-1 flex items-center justify-center px-4 pb-16">
        <div className="w-full max-w-sm">
          <h1 className="font-display text-4xl leading-tight">{isSignup ? "Create your account" : "Welcome back"}</h1>
          <p className="mt-2 text-app-muted">
            {isSignup
              ? "Set up your profile once. Applyon finds matching jobs and prepares every application for your review."
              : "Log in to see your matches, review queue and applications."}
          </p>

          {firebaseEnabled ? (
            <>
              <Button variant="secondary" size="lg" className="mt-8 w-full" onClick={onGoogle} loading={busy === "google"}>
                <GoogleIcon />
                Continue with Google
              </Button>

              <div className="my-6 flex items-center gap-3 text-xs text-app-subtle" aria-hidden="true">
                <span className="h-px flex-1 bg-app-border" />
                or
                <span className="h-px flex-1 bg-app-border" />
              </div>

              <form onSubmit={onSubmit} className="flex flex-col gap-4" noValidate>
                {isSignup && (
                  <Field label="Full name" htmlFor="name">
                    <Input id="name" autoComplete="name" value={name} onChange={(e) => setName(e.target.value)} required />
                  </Field>
                )}
                <Field label="Email" htmlFor="email">
                  <Input
                    id="email"
                    type="email"
                    autoComplete="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                  />
                </Field>
                <Field label="Password" htmlFor="password" hint={isSignup ? "At least 6 characters." : undefined}>
                  <Input
                    id="password"
                    type="password"
                    autoComplete={isSignup ? "new-password" : "current-password"}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    minLength={6}
                  />
                </Field>
                {error && (
                  <p role="alert" className="text-sm text-app-danger">
                    {error}
                  </p>
                )}
                <Button type="submit" size="lg" className="w-full" loading={busy === "email"} disabled={!email || !password}>
                  {isSignup ? "Create account" : "Log in"}
                </Button>
              </form>

              {!isSignup && (
                <button
                  type="button"
                  onClick={onReset}
                  className="mt-3 text-sm text-app-muted underline-offset-4 hover:underline hover:text-app-ink"
                >
                  Forgot password?
                </button>
              )}
            </>
          ) : (
            <DevLogin onLogin={signInAsDevUser} />
          )}

          <p className="mt-8 text-sm text-app-muted">
            {isSignup ? "Already have an account? " : "New to Applyon? "}
            <Link href={isSignup ? "/login" : "/signup"} className="text-app-ink underline underline-offset-4">
              {isSignup ? "Log in" : "Create an account"}
            </Link>
          </p>
          {isSignup && (
            <p className="mt-4 text-xs text-app-subtle">
              By continuing you agree to our{" "}
              <Link href="/terms" className="underline underline-offset-2">
                Terms
              </Link>{" "}
              and{" "}
              <Link href="/privacy" className="underline underline-offset-2">
                Privacy Policy
              </Link>
              .
            </p>
          )}
        </div>
      </main>
    </div>
  );
}

function DevLogin({ onLogin }: { onLogin: (uid: string) => void }) {
  const [uid, setUid] = useState("dev-user-001");
  return (
    <div className="mt-8 rounded-app-xl border border-app-border bg-app-card p-5">
      <p className="text-sm font-medium">Local development login</p>
      <p className="mt-1 text-sm text-app-muted">
        Firebase isn&apos;t configured (no <code className="font-mono text-xs">NEXT_PUBLIC_FIREBASE_*</code> env vars). This
        signs you in with a dev token that only works when the backend runs with{" "}
        <code className="font-mono text-xs">APP_ENV=development</code>.
      </p>
      <form
        className="mt-4 flex flex-col gap-3"
        onSubmit={(e) => {
          e.preventDefault();
          if (uid.trim()) onLogin(uid.trim());
        }}
      >
        <Field label="Dev user ID" htmlFor="dev-uid">
          <Input id="dev-uid" value={uid} onChange={(e) => setUid(e.target.value)} />
        </Field>
        <Button type="submit" className="w-full">
          Continue as dev user
        </Button>
      </form>
    </div>
  );
}

function GoogleIcon() {
  return (
    <svg viewBox="0 0 24 24" className="size-4" aria-hidden="true">
      <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.27-4.74 3.27-8.1z" />
      <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84A11 11 0 0 0 12 23z" />
      <path fill="#FBBC05" d="M5.84 14.1a6.6 6.6 0 0 1 0-4.2V7.07H2.18a11 11 0 0 0 0 9.86l3.66-2.84z" />
      <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1A11 11 0 0 0 2.18 7.07l3.66 2.84C6.71 7.31 9.14 5.38 12 5.38z" />
    </svg>
  );
}
