"use client";

import React, { useState } from "react";
import { ArrowRight, Check, Sparkles } from "lucide-react";
import { submitToWaitlist } from "@/lib/waitlist";
import { landingContent } from "@/content/landing";

export function FinalCtaSection() {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [feedback, setFeedback] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !email.includes("@")) {
      setFeedback("Please enter a valid email address.");
      return;
    }
    setLoading(true);
    const res = await submitToWaitlist(email, "final-cta");
    setLoading(false);
    setSubmitted(true);
    setFeedback(res.message);
  };

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
          Early Access Waitlist
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

        {/* Waitlist Form */}
        <div className="mt-8 w-full max-w-md">
          {!submitted ? (
            <form
              onSubmit={handleSubmit}
              aria-label="Bottom waitlist subscription"
              className="flex items-center gap-2 p-1.5 rounded-full bg-white/[0.08] border border-white/20 backdrop-blur-xl shadow-xl focus-within:border-indigo-400 transition-all"
            >
              <label htmlFor="final-cta-email" className="sr-only">
                Email address
              </label>
              <input
                id="final-cta-email"
                name="email"
                type="email"
                autoComplete="email"
                required
                suppressHydrationWarning
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="Enter your email for early access..."
                className="flex-1 bg-transparent px-4 py-2 text-sm text-white placeholder:text-white/40 focus:outline-hidden font-body"
              />
              <button
                type="submit"
                disabled={loading}
                className="rounded-full px-5 py-2.5 text-sm font-medium font-body bg-white text-black hover:bg-white/90 transition-opacity flex items-center gap-2 shrink-0 cursor-pointer disabled:opacity-50"
              >
                {loading ? (
                  <span className="animate-spin text-xs">●</span>
                ) : (
                  <>
                    <span>{landingContent.finalCta.cta}</span>
                    <ArrowRight className="w-3.5 h-3.5" aria-hidden="true" />
                  </>
                )}
              </button>
            </form>
          ) : (
            <div
              role="status"
              className="flex items-center justify-center gap-2 px-5 py-3 rounded-full bg-emerald-950/80 border border-emerald-800 text-emerald-300 text-sm font-medium animate-in fade-in"
            >
              <Check className="w-4 h-4 text-emerald-400" aria-hidden="true" />
              <span>{feedback}</span>
            </div>
          )}
        </div>

        <p className="mt-4 text-xs text-white/40 font-mono">
          Free during beta · Instant priority activation · Zero credit card required
        </p>
      </div>
    </section>
  );
}
