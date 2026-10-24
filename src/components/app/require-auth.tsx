"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { useAuth } from "@/lib/auth";
import { Spinner } from "./ui";

/** Sends signed-out visitors to /login and brings them back afterwards. */
export function RequireAuth({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    // Read the path from window, not usePathname(): a URL hook here would postpone the whole app tree under Cache Components.
    if (!loading && !user) router.replace(`/login?next=${encodeURIComponent(window.location.pathname)}`);
  }, [loading, user, router]);

  if (loading || !user) {
    return (
      <div className="min-h-screen bg-app-bg flex items-center justify-center">
        <Spinner label="Checking your session" />
      </div>
    );
  }
  return <>{children}</>;
}
