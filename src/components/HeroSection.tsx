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
  Send,
  Sparkles,
  ArrowRight,
} from "lucide-react";
import { submitToWaitlist } from "@/lib/waitlist";

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
    <section className="relative w-full min-h-screen lg:h-screen flex flex-col bg-background overflow-hidden pt-20 lg:pt-24 pb-8">
      {/* Background Video */}
      <video
        className="absolute inset-0 w-full h-full object-cover z-0 pointer-events-none"
        src="https://d8j0ntlcm91z4.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/hf_20260319_015952_e1deeb12-8fb7-4071-a42a-60779fc64ab6.mp4"
        autoPlay
        muted
        loop
        playsInline
      />

      {/* Gentle frosted overlay so text stays razor sharp and readable */}
      <div className="absolute inset-0 bg-white/70 dark:bg-black/60 backdrop-blur-[2px] z-[1] pointer-events-none" />

      {/* Content wrapper */}
      <div className="relative z-10 flex flex-col items-center w-full px-4 sm:px-6 max-w-7xl mx-auto flex-1 justify-between">
        <div className="flex flex-col items-center text-center max-w-4xl mx-auto">
          {/* 1. Badge */}
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="inline-flex items-center gap-1.5 rounded-full border border-border bg-background/90 px-4 py-1.5 text-sm text-muted-foreground font-body mb-5 shadow-xs backdrop-blur-sm"
          >
            <span>Now with GPT-5 support ✨</span>
          </motion.div>

          {/* 2. Headline */}
          <motion.h1
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.1 }}
            className="text-center font-display text-4xl sm:text-5xl md:text-6xl lg:text-[4.75rem] leading-[0.96] tracking-tight text-foreground max-w-2xl"
          >
            The Future of{" "}
            <span className="italic font-normal font-display text-accent dark:text-indigo-400">
              Smarter
            </span>{" "}
            Automation
          </motion.h1>

          {/* 3. Subheadline */}
          <motion.p
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.2 }}
            className="mt-4 text-center text-sm sm:text-base md:text-lg text-muted-foreground max-w-[650px] leading-relaxed font-body"
          >
            Automate your busywork with intelligent agents that learn, adapt, and execute—so your team can focus on what matters most.
          </motion.p>

          {/* 4. CTA Buttons & Waitlist Form */}
          <motion.div
            id="hero-waitlist"
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.3 }}
            className="mt-6 flex flex-col sm:flex-row items-center justify-center gap-3 w-full max-w-md"
          >
            {!submitted ? (
              <form
                onSubmit={handleSubmit}
                className="flex items-center gap-2 p-1.5 rounded-full bg-background/95 border border-border shadow-md w-full backdrop-blur-md"
              >
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="Enter your email..."
                  required
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
                      <span>Book a demo</span>
                      <ArrowRight className="w-3.5 h-3.5" />
                    </>
                  )}
                </button>
              </form>
            ) : (
              <div className="flex items-center gap-2 px-5 py-2.5 rounded-full bg-emerald-50 dark:bg-emerald-950/60 border border-emerald-200 dark:border-emerald-800 text-emerald-800 dark:text-emerald-300 text-sm font-medium animate-in fade-in">
                <Check className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
                <span>{feedback}</span>
              </div>
            )}

            {/* Play Button */}
            <button
              type="button"
              onClick={() => {
                document.getElementById("capabilities")?.scrollIntoView({ behavior: "smooth" });
              }}
              title="Watch preview"
              className="h-11 w-11 rounded-full border-0 bg-background shadow-[0_2px_12px_rgba(0,0,0,0.08)] hover:bg-background/80 flex items-center justify-center shrink-0 transition-transform hover:scale-105 cursor-pointer"
            >
              <Play className="h-4 w-4 fill-foreground text-foreground ml-0.5" />
            </button>
          </motion.div>
        </div>

        {/* 5. Dashboard Preview (Custom coded in React, NOT an image) */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.5 }}
          className="mt-6 lg:mt-8 w-full max-w-5xl"
        >
          <div
            className="rounded-2xl overflow-hidden p-3 md:p-4 select-none pointer-events-none"
            style={{
              background: "rgba(255, 255, 255, 0.55)",
              border: "1px solid rgba(255, 255, 255, 0.65)",
              boxShadow: "var(--shadow-dashboard)",
              backdropFilter: "blur(16px)",
            }}
          >
            {/* Top Bar */}
            <div className="flex items-center justify-between pb-3 border-b border-border/40 text-[11px] text-foreground font-body">
              <div className="flex items-center gap-2">
                <div className="w-6 h-6 rounded-md bg-foreground text-background flex items-center justify-center font-bold text-xs">
                  N
                </div>
                <span className="font-semibold text-xs tracking-tight">Nexora</span>
                <ChevronDown className="w-3.5 h-3.5 text-muted-foreground" />
              </div>

              {/* Search bar */}
              <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-lg bg-secondary/80 border border-border/50 text-muted-foreground w-64 justify-between">
                <div className="flex items-center gap-1.5">
                  <Search className="w-3 h-3" />
                  <span>Search across workflows...</span>
                </div>
                <span className="text-[9px] font-mono bg-background/80 px-1.5 py-0.5 rounded border border-border/60">
                  ⌘K
                </span>
              </div>

              {/* Actions & Avatar */}
              <div className="flex items-center gap-2">
                <div className="px-2.5 py-1 rounded-md bg-accent text-accent-foreground font-medium text-[10px]">
                  Move Money
                </div>
                <div className="p-1.5 rounded-full hover:bg-secondary">
                  <Bell className="w-3.5 h-3.5 text-muted-foreground" />
                </div>
                <div className="w-6 h-6 rounded-full bg-indigo-600 text-white flex items-center justify-center font-semibold text-[10px]">
                  JB
                </div>
              </div>
            </div>

            {/* Dashboard Body (Sidebar + Content) */}
            <div className="flex gap-3 pt-3">
              {/* Sidebar (w-40) */}
              <div className="hidden md:flex flex-col w-40 text-[11px] font-body text-muted-foreground shrink-0 border-r border-border/30 pr-2">
                <div className="space-y-1">
                  <div className="px-2.5 py-1.5 rounded-md bg-secondary/80 text-foreground font-medium flex items-center justify-between">
                    <span>Home</span>
                    <span className="w-1.5 h-1.5 rounded-full bg-accent" />
                  </div>
                  <div className="px-2.5 py-1.5 rounded-md hover:bg-secondary/40 flex items-center justify-between">
                    <span>Tasks</span>
                    <span className="px-1.5 py-0.2 rounded-full bg-accent/20 text-accent font-semibold text-[9px]">
                      10
                    </span>
                  </div>
                  <div className="px-2.5 py-1.5 rounded-md hover:bg-secondary/40">
                    <span>Transactions</span>
                  </div>
                  <div className="px-2.5 py-1.5 rounded-md hover:bg-secondary/40 flex items-center justify-between">
                    <span>Payments</span>
                    <ChevronDown className="w-3 h-3 text-muted-foreground" />
                  </div>
                  <div className="px-2.5 py-1.5 rounded-md hover:bg-secondary/40">
                    <span>Cards</span>
                  </div>
                  <div className="px-2.5 py-1.5 rounded-md hover:bg-secondary/40">
                    <span>Capital</span>
                  </div>
                  <div className="px-2.5 py-1.5 rounded-md hover:bg-secondary/40 flex items-center justify-between">
                    <span>Accounts</span>
                    <ChevronDown className="w-3 h-3 text-muted-foreground" />
                  </div>
                </div>

                <div className="mt-4 pt-3 border-t border-border/30">
                  <div className="text-[10px] uppercase font-semibold text-muted-foreground/70 px-2.5 mb-1 tracking-wider">
                    Workflows
                  </div>
                  <div className="space-y-0.5 text-[10px]">
                    <div className="px-2.5 py-1 text-muted-foreground">Trade rules</div>
                    <div className="px-2.5 py-1 text-muted-foreground">Payments</div>
                    <div className="px-2.5 py-1 text-muted-foreground">Notifications</div>
                    <div className="px-2.5 py-1 text-muted-foreground">Settings</div>
                  </div>
                </div>
              </div>

              {/* Main content */}
              <div className="flex-1 bg-secondary/30 rounded-xl p-3 md:p-4 text-[11px] font-body space-y-4">
                {/* Greeting & Action buttons row */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                  <div>
                    <h3 className="text-sm font-semibold text-foreground">Welcome, Jane</h3>
                    <p className="text-[10px] text-muted-foreground">
                      All autonomous pipelines are operational
                    </p>
                  </div>
                  <div className="flex flex-wrap items-center gap-1.5">
                    {["Send", "Request", "Transfer", "Deposit", "Pay Bill", "Create Invoice"].map(
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
                    <span className="text-[10px] text-muted-foreground font-medium ml-1 cursor-pointer">
                      + Customize
                    </span>
                  </div>
                </div>

                {/* Two equal-width cards */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {/* Balance Card with Handcrafted Cubic Bézier SVG Area Chart */}
                  <div className="rounded-xl bg-background/90 p-3.5 border border-border/60 shadow-xs flex flex-col justify-between">
                    <div>
                      <div className="flex items-center justify-between text-muted-foreground">
                        <div className="flex items-center gap-1.5">
                          <span className="font-medium text-foreground">Mercury Balance</span>
                          <CheckCircle2 className="w-3.5 h-3.5 text-accent" />
                        </div>
                        <span className="text-[10px] font-mono">USD</span>
                      </div>
                      <div className="mt-1 flex items-baseline gap-1">
                        <span className="text-xl font-bold tracking-tight text-foreground">
                          $8,450,190
                        </span>
                        <span className="text-xs text-muted-foreground font-semibold">.32</span>
                      </div>
                      <div className="mt-1 flex items-center gap-3 text-[10px]">
                        <span className="text-muted-foreground">Last 30 Days:</span>
                        <span className="text-emerald-600 font-semibold">+$1.8M</span>
                        <span className="text-rose-500 font-semibold">-$900K</span>
                      </div>
                    </div>

                    {/* Smooth Handcrafted Cubic Bézier SVG Area Chart */}
                    <div className="mt-2 h-20 w-full relative">
                      <svg
                        viewBox="0 0 300 70"
                        preserveAspectRatio="none"
                        className="w-full h-full overflow-visible"
                      >
                        <defs>
                          <linearGradient id="chartGradient" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="0%" stopColor="hsl(var(--accent))" stopOpacity="0.25" />
                            <stop offset="100%" stopColor="hsl(var(--accent))" stopOpacity="0.0" />
                          </linearGradient>
                        </defs>
                        {/* Area fill */}
                        <path
                          d="M 0,55 C 30,50 60,62 90,45 C 120,28 150,38 180,24 C 210,12 240,22 270,14 C 285,10 300,8 300,8 L 300,70 L 0,70 Z"
                          fill="url(#chartGradient)"
                        />
                        {/* Stroke curve */}
                        <path
                          d="M 0,55 C 30,50 60,62 90,45 C 120,28 150,38 180,24 C 210,12 240,22 270,14 C 285,10 300,8 300,8"
                          fill="none"
                          stroke="hsl(var(--accent))"
                          strokeWidth="1.5"
                          strokeLinecap="round"
                        />
                        {/* Indicator pulse dot */}
                        <circle cx="300" cy="8" r="3" fill="hsl(var(--accent))" />
                      </svg>
                    </div>
                  </div>

                  {/* Accounts Card */}
                  <div className="rounded-xl bg-background/90 p-3.5 border border-border/60 shadow-xs flex flex-col justify-between">
                    <div className="flex items-center justify-between text-muted-foreground border-b border-border/30 pb-2">
                      <span className="font-semibold text-foreground">Accounts</span>
                      <div className="flex items-center gap-1.5">
                        <Plus className="w-3.5 h-3.5 cursor-pointer text-muted-foreground hover:text-foreground" />
                        <MoreVertical className="w-3.5 h-3.5 cursor-pointer text-muted-foreground hover:text-foreground" />
                      </div>
                    </div>
                    <div className="divide-y divide-border/20 text-xs">
                      <div className="py-2.5 flex items-center justify-between">
                        <div>
                          <div className="font-medium text-foreground">Credit Account</div>
                          <div className="text-[10px] text-muted-foreground">Corporate Visa · 4912</div>
                        </div>
                        <span className="font-semibold text-foreground">$98,125.50</span>
                      </div>
                      <div className="py-2.5 flex items-center justify-between">
                        <div>
                          <div className="font-medium text-foreground">Treasury Reserve</div>
                          <div className="text-[10px] text-muted-foreground">Yield account 5.1% APY</div>
                        </div>
                        <span className="font-semibold text-foreground">$6,750,200.00</span>
                      </div>
                      <div className="py-2.5 flex items-center justify-between">
                        <div>
                          <div className="font-medium text-foreground">Operations Checking</div>
                          <div className="text-[10px] text-muted-foreground">Primary payroll & bills</div>
                        </div>
                        <span className="font-semibold text-foreground">$1,592,864.82</span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Recent Transactions Table */}
                <div className="rounded-xl bg-background/90 p-3.5 border border-border/60 shadow-xs">
                  <div className="font-semibold text-foreground mb-2">Recent Transactions</div>
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-[11px]">
                      <thead>
                        <tr className="border-b border-border/40 text-muted-foreground text-[10px]">
                          <th className="pb-1.5 font-medium">Date</th>
                          <th className="pb-1.5 font-medium">Description</th>
                          <th className="pb-1.5 font-medium text-right">Amount</th>
                          <th className="pb-1.5 font-medium text-right">Status</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-border/20">
                        <tr>
                          <td className="py-1.5 text-muted-foreground">Today</td>
                          <td className="py-1.5 font-medium text-foreground">Amazon Web Services (Cloud Compute)</td>
                          <td className="py-1.5 text-right font-medium text-rose-600">-$5,200.00</td>
                          <td className="py-1.5 text-right">
                            <span className="inline-block px-1.5 py-0.5 rounded-full bg-amber-500/15 text-amber-600 dark:text-amber-400 font-semibold text-[9px]">
                              Pending
                            </span>
                          </td>
                        </tr>
                        <tr>
                          <td className="py-1.5 text-muted-foreground">Yesterday</td>
                          <td className="py-1.5 font-medium text-foreground">Client Payment (Enterprise License)</td>
                          <td className="py-1.5 text-right font-medium text-emerald-600">+$125,000.00</td>
                          <td className="py-1.5 text-right">
                            <span className="inline-block px-1.5 py-0.5 rounded-full bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 font-semibold text-[9px]">
                              Completed
                            </span>
                          </td>
                        </tr>
                        <tr>
                          <td className="py-1.5 text-muted-foreground">Oct 22</td>
                          <td className="py-1.5 font-medium text-foreground">Bi-Weekly Global Payroll</td>
                          <td className="py-1.5 text-right font-medium text-foreground">-$85,450.00</td>
                          <td className="py-1.5 text-right">
                            <span className="inline-block px-1.5 py-0.5 rounded-full bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 font-semibold text-[9px]">
                              Completed
                            </span>
                          </td>
                        </tr>
                        <tr>
                          <td className="py-1.5 text-muted-foreground">Oct 20</td>
                          <td className="py-1.5 font-medium text-foreground">Office Supplies & Hardware</td>
                          <td className="py-1.5 text-right font-medium text-foreground">-$1,200.00</td>
                          <td className="py-1.5 text-right">
                            <span className="inline-block px-1.5 py-0.5 rounded-full bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 font-semibold text-[9px]">
                              Completed
                            </span>
                          </td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
