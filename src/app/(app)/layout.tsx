import type { Metadata } from "next";
import { AppProviders } from "@/components/app/providers";
import { DynamicMarker } from "@/components/app/dynamic-marker";
import { RequireAuth } from "@/components/app/require-auth";

export const metadata: Metadata = {
  title: "App",
  robots: { index: false, follow: false },
};

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <AppProviders>
      <RequireAuth>{children}</RequireAuth>
      {/* RequireAuth renders only a spinner on the server, so pages never prerender; this marks the app routes as intentionally dynamic. */}
      <DynamicMarker />
    </AppProviders>
  );
}
