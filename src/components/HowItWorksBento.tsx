"use client";

import React, { useState } from "react";
import {
  Sparkles,
  CheckCircle,
  ShieldCheck,
  Lock,
} from "lucide-react";
import { landingContent } from "@/content/landing";

export function HowItWorksBento() {
  const [activeStep, setActiveStep] = useState(0);
  const steps = landingContent.howItWorks.steps;

  return (
    <>
      {/* SECTION 5: HOW IT WORKS */}
      <section
        id="how-it-works"
        aria-labelledby="how-it-works-heading"
        className="relative w-full bg-background py-20 sm:py-28 border-t border-border/40 overflow-hidden"
      >
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center max-w-3xl mx-auto mb-16">
            <span className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full text-xs font-mono bg-accent/10 text-accent border border-accent/20 mb-4">
              <Sparkles className="w-3.5 h-3.5" aria-hidden="true" />
              Workflow Architecture
            </span>
            <h2
              id="how-it-works-heading"
              className="text-4xl sm:text-5xl font-display tracking-tight text-foreground"
            >
              {landingContent.howItWorks.heading}
            </h2>
            <p className="mt-4 text-base sm:text-lg text-muted-foreground font-body">
              {landingContent.howItWorks.subheading}
            </p>
          </div>

          {/* 4 Steps in an accessible semantic ordered list */}
          <ol className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 list-none p-0 m-0">
            {steps.map((s, idx) => (
              <li key={s.number}>
                <div
                  onClick={() => setActiveStep(idx)}
                  className={`p-6 rounded-2xl border transition-all cursor-pointer h-full flex flex-col justify-between ${
                    activeStep === idx
                      ? "bg-secondary/90 border-accent shadow-md shadow-accent/5"
                      : "bg-secondary/30 border-border/60 hover:bg-secondary/60 hover:border-border"
                  }`}
                >
                  <div>
                    <div
                      className="text-2xl font-mono font-bold text-accent mb-3"
                      aria-hidden="true"
                    >
                      {s.number}
                    </div>
                    <h3 className="text-base font-semibold text-foreground mb-2">
                      {s.title}
                    </h3>
                    <p className="text-xs sm:text-sm text-muted-foreground leading-relaxed">
                      {s.description}
                    </p>
                  </div>
                  <div className="mt-4 pt-3 border-t border-border/40 text-[11px] font-mono text-accent">
                    Step {idx + 1} of 4
                  </div>
                </div>
              </li>
            ))}
          </ol>
        </div>
      </section>

      {/* SECTION 6: FEATURES BENTO GRID (Prepared semantically for Section 6) */}
      <section
        id="features"
        aria-labelledby="features-heading"
        className="relative w-full bg-background pb-24 sm:pb-32 overflow-hidden"
      >
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center max-w-2xl mx-auto mb-14">
            <span className="text-xs font-mono uppercase tracking-widest text-accent font-semibold block mb-2">
              Features
            </span>
            <h2
              id="features-heading"
              className="text-3xl sm:text-4xl font-display text-foreground"
            >
              Your whole job hunt, <span className="italic text-accent">one</span> dashboard.
            </h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Bento 1: Smart Job Matching */}
            <div className="md:col-span-2 rounded-2xl bg-secondary/30 border border-border/80 p-6 sm:p-8 flex flex-col justify-between overflow-hidden relative group">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <span className="text-xs font-mono text-accent uppercase tracking-wider block">
                    Precision Match
                  </span>
                  <h3 className="text-lg sm:text-xl font-semibold text-foreground mt-0.5">
                    Smart job matching
                  </h3>
                </div>
                <div
                  className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-500/10 text-emerald-600 text-xs font-semibold border border-emerald-500/20"
                  aria-label="92% fit score match"
                >
                  92% Match
                </div>
              </div>
              <p className="text-xs sm:text-sm text-muted-foreground leading-relaxed mb-4">
                Matching roles ranked by fit score with matched and missing skills transparently explained.
              </p>

              {/* Mock Job Card (aria-hidden decorative mini UI) */}
              <div
                className="p-4 sm:p-5 rounded-xl bg-background border border-border/80 shadow-xs space-y-3 select-none"
                aria-hidden="true"
              >
                <div className="flex items-start justify-between">
                  <div>
                    <div className="font-semibold text-foreground text-sm sm:text-base">
                      Senior Frontend Engineer
                    </div>
                    <div className="text-xs text-muted-foreground">
                      Razorfin Labs · Bengaluru (Hybrid) · ₹28–36 LPA
                    </div>
                  </div>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-accent/10 text-accent">
                    Full-time
                  </span>
                </div>

                <div className="flex flex-wrap gap-1.5 pt-1">
                  <span className="px-2 py-0.5 rounded-md bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 text-[11px] font-medium flex items-center gap-1">
                    <CheckCircle className="w-3 h-3" /> React 19 & Next.js
                  </span>
                  <span className="px-2 py-0.5 rounded-md bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 text-[11px] font-medium flex items-center gap-1">
                    <CheckCircle className="w-3 h-3" /> TypeScript Strict
                  </span>
                  <span className="px-2 py-0.5 rounded-md bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 text-[11px] font-medium flex items-center gap-1">
                    <CheckCircle className="w-3 h-3" /> Web Performance
                  </span>
                  <span className="px-2 py-0.5 rounded-md bg-amber-500/10 text-amber-600 dark:text-amber-400 text-[11px] font-medium">
                    GraphQL (Learnable)
                  </span>
                </div>

                <div className="pt-2 flex items-center justify-between text-xs text-muted-foreground border-t border-border/30">
                  <span>Autofill coverage: 10/10 fields verified</span>
                  <span className="text-accent font-medium">Ready for review →</span>
                </div>
              </div>
            </div>

            {/* Bento 2: AI Resume Tailoring */}
            <div className="rounded-2xl bg-secondary/30 border border-border/80 p-6 sm:p-8 flex flex-col justify-between">
              <div>
                <span className="text-xs font-mono text-accent uppercase tracking-wider block">
                  Zero Hallucinations
                </span>
                <h3 className="text-lg font-semibold text-foreground mt-0.5 mb-2">
                  AI resume tailoring
                </h3>
                <p className="text-xs text-muted-foreground leading-relaxed mb-4">
                  ATS-friendly resume generated for every job description, rephrasing your truthful metrics without inventing experience.
                </p>
              </div>

              <div
                className="p-3.5 rounded-xl bg-background border border-border/80 font-mono text-[11px] space-y-2 select-none"
                aria-hidden="true"
              >
                <div className="text-rose-500 line-through bg-rose-500/5 p-1.5 rounded">
                  - Worked on frontend UI speed and resolved tickets.
                </div>
                <div className="text-emerald-600 bg-emerald-500/10 p-1.5 rounded font-medium">
                  + Architected Next.js bundle optimizations, reducing LCP by 42% for 1.2M users.
                </div>
              </div>
            </div>

            {/* Bento 3: One-Click Autofill */}
            <div className="rounded-2xl bg-secondary/30 border border-border/80 p-6 sm:p-8 flex flex-col justify-between">
              <div>
                <span className="text-xs font-mono text-accent uppercase tracking-wider block">
                  Zero Friction
                </span>
                <h3 className="text-lg font-semibold text-foreground mt-0.5 mb-2">
                  One-click autofill
                </h3>
                <p className="text-xs text-muted-foreground leading-relaxed mb-4">
                  Autofill job applications in 3 seconds across complex portals, while keeping you in full review control before submit.
                </p>
              </div>

              <div
                className="space-y-2 bg-background p-3.5 rounded-xl border border-border/80 text-[11px] select-none"
                aria-hidden="true"
              >
                <div className="flex justify-between items-center py-1 border-b border-border/30">
                  <span className="text-muted-foreground">Notice Period</span>
                  <span className="font-semibold text-foreground">Immediate / 15 Days</span>
                </div>
                <div className="flex justify-between items-center py-1 border-b border-border/30">
                  <span className="text-muted-foreground">Current CTC</span>
                  <span className="font-semibold text-foreground">₹18,00,000</span>
                </div>
                <div className="flex justify-between items-center py-1">
                  <span className="text-muted-foreground">Approval Status</span>
                  <span className="text-emerald-600 font-semibold flex items-center gap-1">
                    <CheckCircle className="w-3 h-3" /> Approved by You
                  </span>
                </div>
              </div>
            </div>

            {/* Bento 4: Safety / Our Promise */}
            <div
              id="our-promise"
              aria-labelledby="promise-heading"
              className="md:col-span-2 rounded-2xl bg-gradient-to-br from-indigo-950/20 to-secondary/30 border border-accent/30 p-6 sm:p-8 flex flex-col justify-between relative overflow-hidden"
            >
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
                <div>
                  <div className="flex items-center gap-2">
                    <ShieldCheck className="w-5 h-5 text-accent" aria-hidden="true" />
                    <span className="text-xs font-mono text-accent uppercase tracking-wider">
                      Our Promise & Ethics
                    </span>
                  </div>
                  <h3 id="promise-heading" className="text-xl sm:text-2xl font-display text-foreground mt-1">
                    AI that works <span className="italic text-accent">for</span> you — not around you.
                  </h3>
                </div>
                <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-accent/10 border border-accent/20 text-accent text-xs font-semibold shrink-0">
                  <Lock className="w-3.5 h-3.5" aria-hidden="true" /> 100% Encrypted
                </div>
              </div>

              <p className="text-xs sm:text-sm text-muted-foreground mb-4">
                We guarantee a truthful resume, no spam bots, and strict candidate data privacy. Your information is never sold.
              </p>

              <ul className="grid grid-cols-1 sm:grid-cols-3 gap-4 list-none p-0 m-0">
                <li className="p-3.5 rounded-xl bg-background/80 border border-border/80">
                  <h4 className="font-semibold text-foreground text-xs sm:text-sm mb-1">
                    1. No fake experience
                  </h4>
                  <p className="text-[11px] text-muted-foreground m-0">
                    Tailoring strictly rephrases and reorders your genuine achievements. Never invents roles or credentials.
                  </p>
                </li>

                <li className="p-3.5 rounded-xl bg-background/80 border border-border/80">
                  <h4 className="font-semibold text-foreground text-xs sm:text-sm mb-1">
                    2. No spam bots
                  </h4>
                  <p className="text-[11px] text-muted-foreground m-0">
                    We never mass-spray unvetted applications or automate sites that forbid bot submissions.
                  </p>
                </li>

                <li className="p-3.5 rounded-xl bg-background/80 border border-border/80">
                  <h4 className="font-semibold text-foreground text-xs sm:text-sm mb-1">
                    3. You approve each one
                  </h4>
                  <p className="text-[11px] text-muted-foreground m-0">
                    Autofill creates the draft, but nothing is submitted until you click approve. You stay in the driver's seat.
                  </p>
                </li>
              </ul>
            </div>
          </div>
        </div>
      </section>
    </>
  );
}
