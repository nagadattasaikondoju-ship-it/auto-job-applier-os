"use client";

import React, { useEffect, useState, useRef } from "react";
import { motion, useInView } from "framer-motion";
import { Clock, Layers, FileX } from "lucide-react";
import { landingContent } from "@/content/landing";

export function ProblemSection() {
  const ref = useRef<HTMLDivElement>(null);
  const isInView = useInView(ref, { once: true, amount: 0.3 });

  const [counter1, setCounter1] = useState(0);
  const [counter2, setCounter2] = useState(0);

  useEffect(() => {
    if (isInView) {
      const t1 = setInterval(() => {
        setCounter1((prev) => (prev < 4 ? prev + 1 : 4));
      }, 150);

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

  const partners = landingContent.trust.companies;

  return (
    <>
      {/* SECTION 3: TRUST STRIP */}
      <section
        id="companies"
        aria-labelledby="companies-heading"
        className="relative w-full bg-background pt-14 pb-12 border-t border-border/40 overflow-hidden"
      >
        <div className="max-w-7xl mx-auto px-6">
          <h2
            id="companies-heading"
            className="text-center text-xs sm:text-sm font-mono tracking-widest text-muted-foreground uppercase mb-8"
          >
            {landingContent.trust.heading}
          </h2>

          {/* Marquee with aria-hidden on duplicates */}
          <div className="relative w-full overflow-hidden [mask-image:linear-gradient(to_right,transparent,black_15%,black_85%,transparent)]">
            <div className="flex gap-12 sm:gap-16 items-center whitespace-nowrap animate-[marquee_25s_linear_infinite] hover:[animation-play-state:paused]">
              {/* Primary list for crawlers and screen readers */}
              <ul className="flex gap-12 sm:gap-16 items-center list-none p-0 m-0">
                {partners.map((company) => (
                  <li
                    key={company}
                    className="text-lg sm:text-xl font-bold tracking-tighter text-muted-foreground/60 hover:text-foreground transition-colors select-none font-mono"
                  >
                    {company}
                  </li>
                ))}
              </ul>

              {/* Duplicate decorative list for smooth infinite CSS animation */}
              <ul
                className="flex gap-12 sm:gap-16 items-center list-none p-0 m-0"
                aria-hidden="true"
              >
                {partners.map((company, index) => (
                  <li
                    key={`duplicate-${company}-${index}`}
                    className="text-lg sm:text-xl font-bold tracking-tighter text-muted-foreground/60 hover:text-foreground transition-colors select-none font-mono"
                  >
                    {company}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      </section>

      {/* SECTION 4: PROBLEM */}
      <section
        id="problem"
        aria-labelledby="problem-heading"
        className="relative w-full bg-background py-16 lg:py-24 border-t border-border/30 overflow-hidden"
      >
        <div ref={ref} className="max-w-6xl mx-auto px-6">
          <div className="text-center max-w-2xl mx-auto mb-16">
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-mono bg-rose-500/10 text-rose-600 dark:text-rose-400 border border-rose-500/20 mb-4">
              The Status Quo
            </span>
            <h2
              id="problem-heading"
              className="text-4xl sm:text-5xl font-display tracking-tight text-foreground"
            >
              Job hunting is{" "}
              <span className="italic font-normal text-rose-500 underline decoration-rose-500/30 underline-offset-8">
                broken
              </span>
              .
            </h2>
            <p className="mt-4 text-base text-muted-foreground font-body">
              {landingContent.problem.subheading}
            </p>
          </div>

          {/* 3 Glass Stat Cards using semantic Definition List */}
          <dl className="grid grid-cols-1 md:grid-cols-3 gap-6 m-0 p-0">
            {/* Card 1 */}
            <motion.div
              initial={{ opacity: 0, y: 24 }}
              animate={isInView ? { opacity: 1, y: 0 } : {}}
              transition={{ duration: 0.6, delay: 0.1 }}
              className="p-8 rounded-2xl bg-secondary/40 border border-border/80 backdrop-blur-md relative overflow-hidden group hover:border-foreground/20 transition-all shadow-xs"
            >
              <div
                className="w-10 h-10 rounded-xl bg-background border border-border flex items-center justify-center text-rose-500 mb-6 shadow-xs"
                aria-hidden="true"
              >
                <Clock className="w-5 h-5" />
              </div>
              <dt className="text-4xl sm:text-5xl font-mono font-bold text-foreground tracking-tight">
                {counter1 > 0 ? `${counter1}+ hrs` : landingContent.problem.stats[0].value}
              </dt>
              <dd className="m-0 mt-2">
                <h3 className="text-base font-semibold text-foreground">
                  {landingContent.problem.stats[0].label}
                </h3>
                <p className="mt-2 text-sm text-muted-foreground leading-relaxed">
                  {landingContent.problem.stats[0].description}
                </p>
              </dd>
            </motion.div>

            {/* Card 2 */}
            <motion.div
              initial={{ opacity: 0, y: 24 }}
              animate={isInView ? { opacity: 1, y: 0 } : {}}
              transition={{ duration: 0.6, delay: 0.2 }}
              className="p-8 rounded-2xl bg-secondary/40 border border-border/80 backdrop-blur-md relative overflow-hidden group hover:border-foreground/20 transition-all shadow-xs"
            >
              <div
                className="w-10 h-10 rounded-xl bg-background border border-border flex items-center justify-center text-amber-500 mb-6 shadow-xs"
                aria-hidden="true"
              >
                <Layers className="w-5 h-5" />
              </div>
              <dt className="text-4xl sm:text-5xl font-mono font-bold text-foreground tracking-tight">
                {counter2 > 0 ? `${counter2}+` : landingContent.problem.stats[1].value}
              </dt>
              <dd className="m-0 mt-2">
                <h3 className="text-base font-semibold text-foreground">
                  {landingContent.problem.stats[1].label}
                </h3>
                <p className="mt-2 text-sm text-muted-foreground leading-relaxed">
                  {landingContent.problem.stats[1].description}
                </p>
              </dd>
            </motion.div>

            {/* Card 3 */}
            <motion.div
              initial={{ opacity: 0, y: 24 }}
              animate={isInView ? { opacity: 1, y: 0 } : {}}
              transition={{ duration: 0.6, delay: 0.3 }}
              className="p-8 rounded-2xl bg-secondary/40 border border-border/80 backdrop-blur-md relative overflow-hidden group hover:border-foreground/20 transition-all shadow-xs"
            >
              <div
                className="w-10 h-10 rounded-xl bg-background border border-border flex items-center justify-center text-accent mb-6 shadow-xs"
                aria-hidden="true"
              >
                <FileX className="w-5 h-5" />
              </div>
              <dt className="text-4xl sm:text-5xl font-mono font-bold text-foreground tracking-tight">
                {landingContent.problem.stats[2].value}
              </dt>
              <dd className="m-0 mt-2">
                <h3 className="text-base font-semibold text-foreground">
                  {landingContent.problem.stats[2].label}
                </h3>
                <p className="mt-2 text-sm text-muted-foreground leading-relaxed">
                  {landingContent.problem.stats[2].description}
                </p>
              </dd>
            </motion.div>
          </dl>

          {/* Complete statement in a single real <p> tag in SSR HTML */}
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
    </>
  );
}
