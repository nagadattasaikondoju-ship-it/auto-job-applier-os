"use client";

import React, { useState } from "react";
import { motion } from "framer-motion";
import {
  Play,
  Search,
  Bell,
  ChevronDown,
  CheckCircle2,
  Plus,
  MoreVertical,
  Check,
  ArrowRight,
} from "lucide-react";
import { submitToWaitlist } from "@/lib/waitlist";
import { landingContent } from "@/content/landing";

export function HeroSection() {
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
    const res = await submitToWaitlist(email, "hero");
    setLoading(false);
    setSubmitted(true);
    setFeedback(res.message);
  };

  return (
    <section
      id="hero"
      aria-labelledby="hero-heading"
      className="relative w-full min-h-screen flex flex-col bg-background overflow-hidden pt-24 lg:pt-28 pb-12"
    >
      {/* Background Video */}
      <video
        className="absolute inset-0 w-full h-full object-cover z-0 pointer-events-none"
        src="https://d8j0ntlcm91z4.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/hf_20260319_015952_e1deeb12-8fb7-4071-a42a-60779fc64ab6.mp4"
        autoPlay
        muted
        loop
        playsInline
        aria-hidden="true"
      />

      {/* Gentle frosted overlay */}
      <div
        className="absolute inset-0 bg-white/70 dark:bg-black/60 backdrop-blur-[2px] z-[1] pointer-events-none"
        aria-hidden="true"
      />

      {/* Content wrapper */}
      <div className="relative z-10 flex flex-col items-center w-full px-4 sm:px-6 max-w-7xl mx-auto flex-1 justify-between">
        <div className="flex flex-col items-center text-center max-w-4xl mx-auto">
          {/* Sole H1 on the entire page: Semantic, SSR visible, with eyebrow badge */}
          <h1 id="hero-heading" className="flex flex-col items-center">
            {/* 1. Badge / Eyebrow */}
            <motion.span
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5 }}
              className="eyebrow inline-flex items-center gap-1.5 rounded-full border border-border bg-background/90 px-4 py-1.5 text-xs sm:text-sm font-body text-muted-foreground mb-5 shadow-xs backdrop-blur-xs"
            >
              <span>{landingContent.hero.eyebrow}</span>
            </motion.span>

            {/* Tagline Heading */}
            <motion.span
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.1 }}
              className="block font-display text-4xl sm:text-5xl md:text-6xl lg:text-[4.75rem] leading-[0.96] tracking-tight text-foreground max-w-2xl"
            >
              {landingContent.hero.titleLine1}{" "}
              <span className="italic font-normal font-display text-accent dark:text-indigo-400">
                {landingContent.hero.titleLine2}
              </span>
            </motion.span>
          </h1>

          {/* 3. Subheadline (Brand Description) */}
          <motion.p
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.2 }}
            className="mt-5 text-center text-sm sm:text-base md:text-lg text-muted-foreground max-w-[650px] leading-relaxed font-body"
          >
            {landingContent.hero.subtext}
          </motion.p>

          {/* 4. CTA Buttons & Waitlist Form */}
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.3 }}
            className="mt-6 flex flex-col sm:flex-row items-center justify-center gap-3 w-full max-w-md"
          >
            {!submitted ? (
              <form
                onSubmit={handleSubmit}
                aria-label="Waitlist email submission"
                className="flex items-center gap-2 p-1.5 rounded-full bg-background/95 border border-border shadow-md w-full backdrop-blur-md"
              >
                <label htmlFor="hero-email-input" className="sr-only">
                  Email address
                </label>
                <input
                  id="hero-email-input"
                  name="email"
                  type="email"
                  autoComplete="email"
                  required
                  suppressHydrationWarning
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder={landingContent.hero.inputPlaceholder}
                  className="flex-1 bg-transparent px-4 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-hidden"
                />
                <button
                  type="submit"
                  disabled={loading}
                  className="rounded-full px-5 py-2.5 text-sm font-medium font-body bg-foreground text-background hover:opacity-90 transition-opacity flex items-center gap-2 shrink-0 cursor-pointer disabled:opacity-50"
                >
                  {loading ? (
                    <span className="animate-spin text-xs">●</span>
                  ) : (
                    <>
                      <span>{landingContent.hero.cta}</span>
                      <ArrowRight className="w-3.5 h-3.5" aria-hidden="true" />
                    </>
                  )}
                </button>
              </form>
            ) : (
              <div
                role="status"
                className="flex items-center gap-2 px-5 py-2.5 rounded-full bg-emerald-50 dark:bg-emerald-950/60 border border-emerald-200 dark:border-emerald-800 text-emerald-800 dark:text-emerald-300 text-sm font-medium animate-in fade-in"
              >
                <Check className="w-4 h-4 text-emerald-600 dark:text-emerald-400" aria-hidden="true" />
                <span>{feedback}</span>
              </div>
            )}

            {/* Play Button */}
            <a
              href="#how-it-works"
              title="Watch preview"
              aria-label="Watch how Applyon works"
              className="h-11 w-11 rounded-full border-0 bg-background shadow-[0_2px_12px_rgba(0,0,0,0.08)] hover:bg-background/80 flex items-center justify-center shrink-0 transition-transform hover:scale-105 cursor-pointer"
            >
              <Play className="h-4 w-4 fill-foreground text-foreground ml-0.5" aria-hidden="true" />
            </a>
          </motion.div>
        </div>

        {/* 5. Dashboard Preview wrapped in semantic <figure> with accessible <figcaption> */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.5 }}
          className="mt-8 lg:mt-10 w-full max-w-5xl"
        >
          <figure className="m-0 p-0">
            <figcaption className="sr-only">
              {landingContent.hero.dashboardFigcaption}
            </figcaption>

            <div
              className="rounded-2xl overflow-hidden p-3 md:p-4 select-none pointer-events-none"
              style={{
                background: "rgba(255, 255, 255, 0.55)",
                border: "1px solid rgba(255, 255, 255, 0.65)",
                boxShadow: "var(--shadow-dashboard)",
                backdropFilter: "blur(16px)",
              }}
              aria-hidden="true"
            >
              {/* Top Bar */}
              <div className="flex items-center justify-between pb-3 border-b border-border/40 text-[11px] text-foreground font-body">
                <div className="flex items-center gap-2">
                  <div className="w-6 h-6 rounded-md bg-foreground text-background flex items-center justify-center font-bold text-xs">
                    ✦
                  </div>
                  <span className="font-semibold text-xs tracking-tight">Applyon Copilot</span>
                  <ChevronDown className="w-3.5 h-3.5 text-muted-foreground" />
                </div>

                <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-lg bg-secondary/80 border border-border/50 text-muted-foreground w-64 justify-between">
                  <div className="flex items-center gap-1.5">
                    <Search className="w-3 h-3" />
                    <span>Search tech roles in India...</span>
                  </div>
                  <span className="text-[9px] font-mono bg-background/80 px-1.5 py-0.5 rounded border border-border/60">
                    ⌘K
                  </span>
                </div>

                <div className="flex items-center gap-2">
                  <div className="px-2.5 py-1 rounded-md bg-accent text-accent-foreground font-medium text-[10px]">
                    Tailor Resume
                  </div>
                  <div className="p-1.5 rounded-full hover:bg-secondary">
                    <Bell className="w-3.5 h-3.5 text-muted-foreground" />
                  </div>
                  <div className="w-6 h-6 rounded-full bg-indigo-600 text-white flex items-center justify-center font-semibold text-[10px]">
                    AR
                  </div>
                </div>
              </div>

              {/* Dashboard Body */}
              <div className="flex gap-3 pt-3">
                {/* Sidebar */}
                <div className="hidden md:flex flex-col w-40 text-[11px] font-body text-muted-foreground shrink-0 border-r border-border/30 pr-2">
                  <div className="space-y-1">
                    <div className="px-2.5 py-1.5 rounded-md bg-secondary/80 text-foreground font-medium flex items-center justify-between">
                      <span>Matches</span>
                      <span className="w-1.5 h-1.5 rounded-full bg-accent" />
                    </div>
                    <div className="px-2.5 py-1.5 rounded-md hover:bg-secondary/40 flex items-center justify-between">
                      <span>Active Queue</span>
                      <span className="px-1.5 py-0.2 rounded-full bg-accent/20 text-accent font-semibold text-[9px]">
                        12
                      </span>
                    </div>
                    <div className="px-2.5 py-1.5 rounded-md hover:bg-secondary/40">
                      <span>Tailored CVs</span>
                    </div>
                    <div className="px-2.5 py-1.5 rounded-md hover:bg-secondary/40 flex items-center justify-between">
                      <span>Interviews</span>
                      <ChevronDown className="w-3 h-3 text-muted-foreground" />
                    </div>
                    <div className="px-2.5 py-1.5 rounded-md hover:bg-secondary/40">
                      <span>Autofill Logs</span>
                    </div>
                    <div className="px-2.5 py-1.5 rounded-md hover:bg-secondary/40">
                      <span>Salary Insights</span>
                    </div>
                  </div>

                  <div className="mt-4 pt-3 border-t border-border/30">
                    <div className="text-[10px] uppercase font-semibold text-muted-foreground/70 px-2.5 mb-1 tracking-wider">
                      Target Hubs
                    </div>
                    <div className="space-y-0.5 text-[10px]">
                      <div className="px-2.5 py-1 text-muted-foreground">Bengaluru (Tier 1)</div>
                      <div className="px-2.5 py-1 text-muted-foreground">Hyderabad Tech</div>
                      <div className="px-2.5 py-1 text-muted-foreground">Pune & Mumbai</div>
                      <div className="px-2.5 py-1 text-muted-foreground">Remote Global</div>
                    </div>
                  </div>
                </div>

                {/* Main content */}
                <div className="flex-1 bg-secondary/30 rounded-xl p-3 md:p-4 text-[11px] font-body space-y-4">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                    <div>
                      <h2 className="text-sm font-semibold text-foreground m-0 p-0">Welcome back, Arjun</h2>
                      <p className="text-[10px] text-muted-foreground">
                        3 new roles match your verified background with &gt;90% fit score
                      </p>
                    </div>
                    <div className="flex flex-wrap items-center gap-1.5">
                      {["Tailor", "Autofill", "Review", "Track", "Export PDF"].map(
                        (action, i) => (
                          <span
                            key={action}
                            className={`rounded-full px-2.5 py-1 text-[10px] font-medium transition-colors ${
                              i === 0
                                ? "bg-accent text-accent-foreground shadow-xs"
                                : "bg-background/90 text-foreground border border-border/60 hover:bg-secondary"
                            }`}
                          >
                            {action}
                          </span>
                        )
                      )}
                    </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {/* Fit Score Card with SVG Bézier Chart */}
                    <div className="rounded-xl bg-background/90 p-3.5 border border-border/60 shadow-xs flex flex-col justify-between">
                      <div>
                        <div className="flex items-center justify-between text-muted-foreground">
                          <div className="flex items-center gap-1.5">
                            <span className="font-medium text-foreground">Top Match Fit Score</span>
                            <CheckCircle2 className="w-3.5 h-3.5 text-accent" />
                          </div>
                          <span className="text-[10px] font-mono">92% MATCH</span>
                        </div>
                        <div className="mt-1 flex items-baseline gap-1">
                          <span className="text-xl font-bold tracking-tight text-foreground">
                            Frontend Engineer
                          </span>
                          <span className="text-xs text-muted-foreground font-semibold">· Razorfin</span>
                        </div>
                        <div className="mt-1 flex items-center gap-3 text-[10px]">
                          <span className="text-muted-foreground">Bengaluru:</span>
                          <span className="text-emerald-600 font-semibold">₹18–24 LPA</span>
                          <span className="text-accent font-semibold">Ready for review ✓</span>
                        </div>
                      </div>

                      {/* Smooth Bézier Chart */}
                      <div className="mt-2 h-16 w-full relative">
                        <svg
                          viewBox="0 0 300 70"
                          preserveAspectRatio="none"
                          className="w-full h-full overflow-visible"
                        >
                          <defs>
                            <linearGradient id="heroChartGradient" x1="0" y1="0" x2="0" y2="1">
                              <stop offset="0%" stopColor="hsl(var(--accent))" stopOpacity="0.25" />
                              <stop offset="100%" stopColor="hsl(var(--accent))" stopOpacity="0.0" />
                            </linearGradient>
                          </defs>
                          <path
                            d="M 0,55 C 30,50 60,62 90,45 C 120,28 150,38 180,24 C 210,12 240,22 270,14 C 285,10 300,8 300,8 L 300,70 L 0,70 Z"
                            fill="url(#heroChartGradient)"
                          />
                          <path
                            d="M 0,55 C 30,50 60,62 90,45 C 120,28 150,38 180,24 C 210,12 240,22 270,14 C 285,10 300,8 300,8"
                            fill="none"
                            stroke="hsl(var(--accent))"
                            strokeWidth="1.5"
                            strokeLinecap="round"
                          />
                          <circle cx="300" cy="8" r="3" fill="hsl(var(--accent))" />
                        </svg>
                      </div>
                    </div>

                    {/* Applications Queue */}
                    <div className="rounded-xl bg-background/90 p-3.5 border border-border/60 shadow-xs flex flex-col justify-between">
                      <div className="flex items-center justify-between text-muted-foreground border-b border-border/30 pb-2">
                        <span className="font-semibold text-foreground">Autofill Verification</span>
                        <div className="flex items-center gap-1.5">
                          <Plus className="w-3.5 h-3.5 text-muted-foreground" />
                          <MoreVertical className="w-3.5 h-3.5 text-muted-foreground" />
                        </div>
                      </div>
                      <div className="divide-y divide-border/20 text-xs">
                        <div className="py-2 flex items-center justify-between">
                          <div>
                            <div className="font-medium text-foreground">Workday Portal Autofill</div>
                            <div className="text-[10px] text-muted-foreground">8/10 fields prefilled accurately</div>
                          </div>
                          <span className="text-emerald-600 font-semibold text-[11px]">Approved ✓</span>
                        </div>
                        <div className="py-2 flex items-center justify-between">
                          <div>
                            <div className="font-medium text-foreground">ATS Tailoring Score</div>
                            <div className="text-[10px] text-muted-foreground">Keywords aligned with role</div>
                          </div>
                          <span className="text-accent font-semibold text-[11px]">96% Match</span>
                        </div>
                        <div className="py-2 flex items-center justify-between">
                          <div>
                            <div className="font-medium text-foreground">Interview Tracker</div>
                            <div className="text-[10px] text-muted-foreground">Round 1 scheduled (Razorfin)</div>
                          </div>
                          <span className="text-foreground font-semibold text-[11px]">Tomorrow</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </figure>
        </motion.div>
      </div>
    </section>
  );
}
