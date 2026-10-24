import type { Metadata } from "next";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";

export const metadata: Metadata = {
  title: "Terms of Service | Applyon",
  description:
    "Review Applyon terms of service, acceptable use guidelines, and platform policies.",
  alternates: {
    canonical: "/terms",
  },
  robots: {
    index: false,
    follow: true,
  },
};

export default function TermsPage() {
  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col items-center justify-center p-6 text-center">
      <div className="max-w-xl mx-auto space-y-4">
        <h1 className="text-3xl font-display font-semibold">Terms of Service</h1>
        <p className="text-muted-foreground text-sm leading-relaxed">
          By accessing Applyon, you agree to our fair use policies. Applyon assists you in preparing and submitting job applications with your explicit consent and approval.
        </p>
        <Link
          href="/"
          className="inline-flex items-center gap-2 text-sm font-medium text-accent hover:underline pt-4"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Applyon Home</span>
        </Link>
      </div>
    </div>
  );
}
