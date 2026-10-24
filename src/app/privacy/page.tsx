import type { Metadata } from "next";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";

export const metadata: Metadata = {
  title: "Privacy Policy | Applyon",
  description:
    "Learn how Applyon protects candidate privacy, secures career data, and complies with data protection laws.",
  alternates: {
    canonical: "/privacy",
  },
  robots: {
    index: false,
    follow: true,
  },
};

export default function PrivacyPage() {
  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col items-center justify-center p-6 text-center">
      <div className="max-w-xl mx-auto space-y-4">
        <h1 className="text-3xl font-display font-semibold">Privacy Policy</h1>
        <p className="text-muted-foreground text-sm leading-relaxed">
          At Applyon, your data belongs to you. We never sell your resume or personal information to third-party data brokers. All career data is encrypted in transit and at rest.
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
