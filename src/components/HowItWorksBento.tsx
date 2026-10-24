"use client";

import React, { useState } from "react";
import { motion } from "framer-motion";
import {
  FileText,
  Sparkles,
  CheckCircle,
  ShieldCheck,
  Briefcase,
  Sliders,
  Send,
  ArrowRight,
  TrendingUp,
  Lock,
} from "lucide-react";

export function HowItWorksBento() {
  const [activeStep, setActiveStep] = useState(0);

  const steps = [
    {
      number: "01",
      title: "Upload your resume",
      desc: "AI turns it into a rich, editable career profile in seconds, extracting verified skills and timeline achievements.",
    },
    {
      number: "02",
      title: "Discover matching roles",
      desc: "Jobs ranked by an objective fit score, with matched and missing skills transparently explained.",
    },
    {
      number: "03",
      title: "Tailor & autofill",
      desc: "A resume tailored to each role and application forms prefilled for you—using strictly your real experience.",
    },
    {
      number: "04",
      title: "Review, apply, track",
      desc: "You review and approve every single application. Manage every stage and follow-up from one central dashboard.",
    },
  ];

  return (
    <section id="features" className="relative w-full bg-background py-24 sm:py-32 border-t border-border/40 overflow-hidden">
      <div className="max-w-7xl mx-auto px-6">
        {/* Section Header */}
        <div className="text-center max-w-3xl mx-auto mb-20">
          <span className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full text-xs font-mono bg-accent/10 text-accent border border-accent/20 mb-4">
            <Sparkles className="w-3.5 h-3.5" />
            Workflow Architecture
          </span>
          <h2 className="text-4xl sm:text-5xl font-display tracking-tight text-foreground">
            From resume to interview in{" "}
            <span className="italic font-normal text-accent">four</span> steps.
          </h2>
          <p className="mt-4 text-base sm:text-lg text-muted-foreground font-body">
            Applyon handles the repetitive heavy lifting while ensuring you retain 100% human oversight on every submission.
          </p>
        </div>

        {/* 4 Steps Interactive Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-24">
          {steps.map((s, idx) => (
            <div
              key={s.number}
              onClick={() => setActiveStep(idx)}
              className={`p-6 rounded-2xl border transition-all cursor-pointer relative ${
                activeStep === idx
                  ? "bg-secondary/90 border-accent shadow-md shadow-accent/5"
                  : "bg-secondary/30 border-border/60 hover:bg-secondary/60 hover:border-border"
              }`}
            >
              <div className="text-2xl font-mono font-bold text-accent mb-3">{s.number}</div>
              <h3 className="text-base font-semibold text-foreground mb-2">{s.title}</h3>
              <p className="text-xs sm:text-sm text-muted-foreground leading-relaxed">{s.desc}</p>
            </div>
          ))}
        </div>

        {/* Bento Grid of Live Animated Mini-UIs */}
        <div className="mb-12">
          <h3 className="text-2xl sm:text-3xl font-display text-center mb-8 text-foreground">
            Your whole job hunt, <span className="italic text-accent">one</span> dashboard.
          </h3>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Bento 1: Smart Job Matching (Large 2-col) */}
            <div className="md:col-span-2 rounded-2xl bg-secondary/30 border border-border/80 p-6 sm:p-8 flex flex-col justify-between overflow-hidden relative group">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <span className="text-xs font-mono text-accent uppercase tracking-wider">
                    Precision Match
                  </span>
                  <h4 className="text-lg sm:text-xl font-semibold text-foreground mt-0.5">
                    Live Fit Score Engine
                  </h4>
                </div>
                <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-500/10 text-emerald-600 text-xs font-semibold border border-emerald-500/20">
                  92% Match
                </div>
              </div>

              {/* Mock Job Card */}
              <div className="p-4 sm:p-5 rounded-xl bg-background border border-border/80 shadow-xs space-y-3">
                <div className="flex items-start justify-between">
                  <div>
                    <h5 className="font-semibold text-foreground text-sm sm:text-base">
                      Senior Frontend Engineer
                    </h5>
                    <p className="text-xs text-muted-foreground">
                      Razorfin Labs · Bengaluru (Hybrid) · ₹28–36 LPA
                    </p>
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
                <span className="text-xs font-mono text-accent uppercase tracking-wider">
                  Zero Hallucinations
                </span>
                <h4 className="text-lg font-semibold text-foreground mt-0.5 mb-2">
                  Line-by-Line Diff
                </h4>
                <p className="text-xs text-muted-foreground leading-relaxed mb-4">
                  Rephrases your truthful impact metrics to match company criteria without inventing experience.
                </p>
              </div>

              <div className="p-3.5 rounded-xl bg-background border border-border/80 font-mono text-[11px] space-y-2">
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
                <span className="text-xs font-mono text-accent uppercase tracking-wider">
                  Zero Friction
                </span>
                <h4 className="text-lg font-semibold text-foreground mt-0.5 mb-2">
                  Portal Autofill
                </h4>
                <p className="text-xs text-muted-foreground leading-relaxed mb-4">
                  Prefills complex Workday, Lever, and Greenhouse forms in under 3 seconds.
                </p>
              </div>

              <div className="space-y-2 bg-background p-3.5 rounded-xl border border-border/80 text-[11px]">
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

            {/* Bento 4: Safety / Our Promise (Large 2-col) */}
            <div className="md:col-span-2 rounded-2xl bg-gradient-to-br from-indigo-950/20 to-secondary/30 border border-accent/30 p-6 sm:p-8 flex flex-col justify-between relative overflow-hidden">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
                <div>
                  <div className="flex items-center gap-2">
                    <ShieldCheck className="w-5 h-5 text-accent" />
                    <span className="text-xs font-mono text-accent uppercase tracking-wider">
                      Our Promise & Ethics
                    </span>
                  </div>
                  <h4 className="text-xl sm:text-2xl font-display text-foreground mt-1">
                    AI that works <span className="italic text-accent">for</span> you — not around you.
                  </h4>
                </div>
                <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-accent/10 border border-accent/20 text-accent text-xs font-semibold shrink-0">
                  <Lock className="w-3.5 h-3.5" /> 100% Encrypted
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div className="p-3.5 rounded-xl bg-background/80 border border-border/80">
                  <div className="font-semibold text-foreground text-xs sm:text-sm mb-1">
                    1. No fake experience
                  </div>
                  <p className="text-[11px] text-muted-foreground">
                    Tailoring strictly rephrases and reorders your genuine achievements. Never invents roles or credentials.
                  </p>
                </div>

                <div className="p-3.5 rounded-xl bg-background/80 border border-border/80">
                  <div className="font-semibold text-foreground text-xs sm:text-sm mb-1">
                    2. No spam bots
                  </div>
                  <p className="text-[11px] text-muted-foreground">
                    We never mass-spray unvetted applications or automate sites that forbid bot submissions.
                  </p>
                </div>

                <div className="p-3.5 rounded-xl bg-background/80 border border-border/80">
                  <div className="font-semibold text-foreground text-xs sm:text-sm mb-1">
                    3. You approve each one
                  </div>
                  <p className="text-[11px] text-muted-foreground">
                    Autofill creates the draft, but nothing is submitted until you click approve. You stay in the driver's seat.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
