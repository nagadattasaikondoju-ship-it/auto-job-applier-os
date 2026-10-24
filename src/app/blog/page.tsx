import type { Metadata } from "next";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";

export const metadata: Metadata = {
  title: "Applyon Career & Job Search Blog",
  description:
    "Actionable guides on passing tech interviews, optimizing resumes for ATS scanners, and career growth strategies in India.",
  alternates: {
    canonical: "/blog",
  },
  robots: {
    index: false,
    follow: true,
  },
};

export default function BlogPage() {
  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col items-center justify-center p-6 text-center">
      <div className="max-w-xl mx-auto space-y-4">
        <span className="text-xs font-mono px-3 py-1 rounded-full bg-accent/10 text-accent border border-accent/20">
          Coming Soon
        </span>
        <h1 className="text-3xl sm:text-4xl font-display font-semibold">
          Applyon Career Blog
        </h1>
        <p className="text-muted-foreground text-sm sm:text-base">
          Articles on tech hiring trends, resume tailoring tactics, and salary benchmarks for Indian tech professionals are coming soon.
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
