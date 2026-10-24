"use client";

import React, { useEffect, useState, useRef } from "react";
import { motion, useInView } from "framer-motion";
import { Clock, Layers, FileX, ArrowRight } from "lucide-react";

export function ProblemSection() {
  const ref = useRef<HTMLDivElement>(null);
  const isInView = useInView(ref, { once: true, amount: 0.3 });

  const [counter1, setCounter1] = useState(0);
  const [counter2, setCounter2] = useState(0);

  useEffect(() => {
    if (isInView) {
      // Counter 1: 0 -> 4
      const t1 = setInterval(() => {
        setCounter1((prev) => (prev < 4 ? prev + 1 : 4));
      }, 150);

      // Counter 2: 0 -> 100
      const t2 = setInterval(() => {
        setCounter2((prev) => {
          if (prev >= 100) return 100;
          return prev + 5;
        });
      }, 35);

      return () => {
        clearInterval(t1);
        clearInterval(t2);
      };
    }
  }, [isInView]);

  const partners = [
    "RAZORFIN",
    "HYPERGROWTH",
    "LATTICE OS",
    "NOVAPAY",
    "ZEPTH AI",
    "KINETIX",
    "VERTEX LABS",
    "SCALEFORGE",
    "FINWAVE",
    "SYNERGY CLOUD",
  ];

  return (
    <section className="relative w-full bg-background py-16 lg:py-24 border-t border-border/40 overflow-hidden">
      {/* Trust Strip Marquee */}
      <div className="max-w-7xl mx-auto px-6 mb-20">
        <p className="text-center text-xs font-mono tracking-widest text-muted-foreground uppercase mb-8">
          ✦ Built for job seekers targeting top startups and tech companies ✦
        </p>

        {/* Infinite Marquee Container */}
        <div className="relative w-full overflow-hidden mask-radial [mask-image:linear-gradient(to_right,transparent,black_15%,black_85%,transparent)]">
          <div className="flex gap-12 sm:gap-16 items-center whitespace-nowrap animate-[marquee_25s_linear_infinite] hover:[animation-play-state:paused]">
            {[...partners, ...partners].map((company, index) => (
              <span
                key={index}
                className="text-lg sm:text-xl font-bold tracking-tighter text-muted-foreground/60 hover:text-foreground transition-colors select-none font-mono"
              >
                {company}
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* Problem Section Container */}
      <div ref={ref} className="max-w-6xl mx-auto px-6">
        <div className="text-center max-w-2xl mx-auto mb-16">
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-mono bg-rose-500/10 text-rose-600 dark:text-rose-400 border border-rose-500/20 mb-4">
            The Status Quo
          </span>
          <h2 className="text-4xl sm:text-5xl font-display tracking-tight text-foreground">
            Job hunting is{" "}
            <span className="italic font-normal text-rose-500 underline decoration-rose-500/30 underline-offset-8">
              broken
            </span>
            .
          </h2>
          <p className="mt-4 text-base text-muted-foreground font-body">
            Candidates spend hundreds of hours retyping work histories into clunky portals only to get ghosted by automated filters.
          </p>
        </div>

        {/* 3 Glass Stat Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Card 1 */}
          <motion.div
            initial={{ opacity: 0, y: 24 }}
            animate={isInView ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 0.6, delay: 0.1 }}
            className="p-8 rounded-2xl bg-secondary/40 border border-border/80 backdrop-blur-md relative overflow-hidden group hover:border-foreground/20 transition-all shadow-xs"
          >
            <div className="w-10 h-10 rounded-xl bg-background border border-border flex items-center justify-center text-rose-500 mb-6 shadow-xs">
              <Clock className="w-5 h-5" />
            </div>
            <div className="text-4xl sm:text-5xl font-mono font-bold text-foreground tracking-tight">
              {counter1}+ hrs
            </div>
            <h3 className="mt-2 text-base font-semibold text-foreground">
              Lost to repetitive forms every day
            </h3>
            <p className="mt-2 text-sm text-muted-foreground leading-relaxed">
              Filling duplicate work history, personal summaries, and manual dropdowns across dozens of workday and greenhouse boards.
            </p>
          </motion.div>

          {/* Card 2 */}
          <motion.div
            initial={{ opacity: 0, y: 24 }}
            animate={isInView ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 0.6, delay: 0.2 }}
            className="p-8 rounded-2xl bg-secondary/40 border border-border/80 backdrop-blur-md relative overflow-hidden group hover:border-foreground/20 transition-all shadow-xs"
          >
            <div className="w-10 h-10 rounded-xl bg-background border border-border flex items-center justify-center text-amber-500 mb-6 shadow-xs">
              <Layers className="w-5 h-5" />
            </div>
            <div className="text-4xl sm:text-5xl font-mono font-bold text-foreground tracking-tight">
              {counter2}+
            </div>
            <h3 className="mt-2 text-base font-semibold text-foreground">
              Applications before one interview
            </h3>
            <p className="mt-2 text-sm text-muted-foreground leading-relaxed">
              Spray-and-pray applications fail ATS scans because standard resumes miss specific keyword nuances required by recruiters.
            </p>
          </motion.div>

          {/* Card 3 */}
          <motion.div
            initial={{ opacity: 0, y: 24 }}
            animate={isInView ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 0.6, delay: 0.3 }}
            className="p-8 rounded-2xl bg-secondary/40 border border-border/80 backdrop-blur-md relative overflow-hidden group hover:border-foreground/20 transition-all shadow-xs"
          >
            <div className="w-10 h-10 rounded-xl bg-background border border-border flex items-center justify-center text-accent mb-6 shadow-xs">
              <FileX className="w-5 h-5" />
            </div>
            <div className="text-4xl sm:text-5xl font-mono font-bold text-foreground tracking-tight">
              1 resume
            </div>
            <h3 className="mt-2 text-base font-semibold text-foreground">
              Sent to every role, completely unchanged
            </h3>
            <p className="mt-2 text-sm text-muted-foreground leading-relaxed">
              Without AI tailoring, high-caliber talent gets overlooked simply because their experience isn't highlighted for that job description.
            </p>
          </motion.div>
        </div>

        {/* Scroll reveal statement */}
        <div className="mt-20 py-12 px-8 rounded-3xl bg-foreground text-background text-center max-w-4xl mx-auto shadow-2xl">
          <p className="text-xl sm:text-2xl md:text-3xl font-display leading-snug">
            “You don’t need to apply to more jobs. You need to apply to the{" "}
            <span className="italic font-normal text-amber-300">right ones</span> — with the{" "}
            <span className="italic font-normal text-indigo-300">right resume</span>.”
          </p>
          <p className="mt-4 text-xs sm:text-sm font-mono opacity-80">
            Applyon Copilot · Human in control, AI at work
          </p>
        </div>
      </div>
    </section>
  );
}
