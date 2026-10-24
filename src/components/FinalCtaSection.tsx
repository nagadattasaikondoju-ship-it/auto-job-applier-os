"use client";

import Link from "next/link";
import { ArrowRight, Sparkles } from "lucide-react";
import { landingContent } from "@/content/landing";

export function FinalCtaSection() {
  return (
    <section
      id="get-started"
      aria-labelledby="cta-heading"
      className="relative w-full bg-[#07070A] text-white py-24 sm:py-32 px-4 sm:px-6 overflow-hidden border-t border-white/10"
    >
      {/* Big glowing aurora background */}
      <div
        className="absolute inset-0 pointer-events-none opacity-40"
        aria-hidden="true"
        style={{
          background:
            "radial-gradient(circle at 50% 50%, rgba(79, 70, 229, 0.35) 0%, rgba(139, 92, 246, 0.15) 40%, transparent 70%)",
        }}
      />

      <div className="relative z-10 max-w-3xl mx-auto text-center flex flex-col items-center">
        <span className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full text-xs font-mono bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 mb-6">
          <Sparkles className="w-3.5 h-3.5 text-amber-400" aria-hidden="true" />
          Start in under a minute
        </span>

        <h2
          id="cta-heading"
          className="text-4xl sm:text-5xl md:text-6xl font-display font-medium tracking-tight text-white leading-tight"
        >
          {landingContent.finalCta.heading}
        </h2>

        <p className="mt-5 text-base sm:text-lg text-white/70 max-w-xl font-body leading-relaxed">
          {landingContent.finalCta.subheading}
        </p>

        <Link
          href="/signup"
          className="mt-8 rounded-full px-7 py-3.5 text-base font-medium font-body bg-white text-black hover:bg-white/90 transition-colors flex items-center gap-2 shadow-xl"
        >
          <span>{landingContent.finalCta.cta}</span>
          <ArrowRight className="w-4 h-4" aria-hidden="true" />
        </Link>

        <p className="mt-4 text-xs text-white/40 font-mono">
          Free ATS check · You approve every application · No credit card required
        </p>
      </div>
    </section>
  );
}
