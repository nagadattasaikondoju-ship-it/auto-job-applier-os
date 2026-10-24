import type { Metadata } from "next";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";

export const metadata: Metadata = {
  title: "AI Resume Tailoring for Indian Tech Jobs",
  description:
    "Tailor your resume for every job application using AI. Highlight matching skills and pass ATS filters without fabricating experience.",
  alternates: {
    canonical: "/resume-tailoring",
  },
  robots: {
    index: false,
    follow: true,
  },
};

export default function ResumeTailoringPage() {
  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col items-center justify-center p-6 text-center">
      <div className="max-w-xl mx-auto space-y-4">
        <span className="text-xs font-mono px-3 py-1 rounded-full bg-accent/10 text-accent border border-accent/20">
          Coming Soon
        </span>
        <h1 className="text-3xl sm:text-4xl font-display font-semibold">
          AI Resume Tailoring
        </h1>
        <p className="text-muted-foreground text-sm sm:text-base">
          This comprehensive guide and deep-dive into ATS-friendly resume tailoring is currently in preparation for our public launch.
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
