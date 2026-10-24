"use client";

import React from "react";
import { landingContent } from "@/content/landing";

export function TestimonialsSection() {
  const testimonials = landingContent.testimonials.items;
  // Split into two sets for bidirectional marquee
  const row1 = testimonials.slice(0, 3);
  const row2 = testimonials.slice(2);

  return (
    <section
      id="testimonials"
      aria-labelledby="testimonials-heading"
      className="relative w-full bg-background py-20 sm:py-28 border-t border-border/40 overflow-hidden"
    >
      <div className="max-w-7xl mx-auto px-6 mb-14 text-center">
        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-mono bg-accent/10 text-accent border border-accent/20 mb-4">
          Early Candidate Feedback
        </span>
        <h2
          id="testimonials-heading"
          className="text-3xl sm:text-4xl md:text-5xl font-display tracking-tight text-foreground"
        >
          {landingContent.testimonials.heading}
        </h2>
        <p className="mt-4 text-sm sm:text-base text-muted-foreground font-body max-w-xl mx-auto">
          {landingContent.testimonials.subheading}
        </p>
      </div>

      {/* Row 1 Marquee */}
      <div className="relative w-full overflow-hidden mb-6 [mask-image:linear-gradient(to_right,transparent,black_15%,black_85%,transparent)]">
        <div className="flex gap-6 items-center whitespace-nowrap animate-[marquee_30s_linear_infinite] hover:[animation-play-state:paused]">
          {/* Primary Cards */}
          <div className="flex gap-6">
            {row1.map((item) => (
              <figure
                key={item.name}
                className="w-[320px] sm:w-[380px] p-6 rounded-2xl bg-secondary/30 border border-border/70 backdrop-blur-xs flex flex-col justify-between whitespace-normal shrink-0 m-0"
              >
                <blockquote className="text-xs sm:text-sm text-foreground/90 font-body leading-relaxed m-0 italic">
                  “{item.quote}”
                </blockquote>
                <figcaption className="mt-5 pt-4 border-t border-border/40 flex items-center gap-3">
                  <div className="w-8 h-8 rounded-full bg-accent/20 text-accent font-semibold text-xs flex items-center justify-center shrink-0">
                    {item.avatar}
                  </div>
                  <div className="text-left">
                    <div className="text-xs font-semibold text-foreground">{item.name}</div>
                    <div className="text-[11px] text-muted-foreground">
                      {item.role} · {item.city}
                    </div>
                  </div>
                </figcaption>
              </figure>
            ))}
          </div>

          {/* Decorative Duplicate */}
          <div className="flex gap-6" aria-hidden="true">
            {row1.map((item, idx) => (
              <figure
                key={`row1-dup-${item.name}-${idx}`}
                className="w-[320px] sm:w-[380px] p-6 rounded-2xl bg-secondary/30 border border-border/70 backdrop-blur-xs flex flex-col justify-between whitespace-normal shrink-0 m-0"
              >
                <blockquote className="text-xs sm:text-sm text-foreground/90 font-body leading-relaxed m-0 italic">
                  “{item.quote}”
                </blockquote>
                <figcaption className="mt-5 pt-4 border-t border-border/40 flex items-center gap-3">
                  <div className="w-8 h-8 rounded-full bg-accent/20 text-accent font-semibold text-xs flex items-center justify-center shrink-0">
                    {item.avatar}
                  </div>
                  <div className="text-left">
                    <div className="text-xs font-semibold text-foreground">{item.name}</div>
                    <div className="text-[11px] text-muted-foreground">
                      {item.role} · {item.city}
                    </div>
                  </div>
                </figcaption>
              </figure>
            ))}
          </div>
        </div>
      </div>

      {/* Row 2 Marquee in reverse */}
      <div className="relative w-full overflow-hidden [mask-image:linear-gradient(to_right,transparent,black_15%,black_85%,transparent)]">
        <div className="flex gap-6 items-center whitespace-nowrap animate-[marquee_35s_linear_infinite_reverse] hover:[animation-play-state:paused]">
          <div className="flex gap-6">
            {row2.map((item) => (
              <figure
                key={item.name}
                className="w-[320px] sm:w-[380px] p-6 rounded-2xl bg-secondary/30 border border-border/70 backdrop-blur-xs flex flex-col justify-between whitespace-normal shrink-0 m-0"
              >
                <blockquote className="text-xs sm:text-sm text-foreground/90 font-body leading-relaxed m-0 italic">
                  “{item.quote}”
                </blockquote>
                <figcaption className="mt-5 pt-4 border-t border-border/40 flex items-center gap-3">
                  <div className="w-8 h-8 rounded-full bg-accent/20 text-accent font-semibold text-xs flex items-center justify-center shrink-0">
                    {item.avatar}
                  </div>
                  <div className="text-left">
                    <div className="text-xs font-semibold text-foreground">{item.name}</div>
                    <div className="text-[11px] text-muted-foreground">
                      {item.role} · {item.city}
                    </div>
                  </div>
                </figcaption>
              </figure>
            ))}
          </div>

          <div className="flex gap-6" aria-hidden="true">
            {row2.map((item, idx) => (
              <figure
                key={`row2-dup-${item.name}-${idx}`}
                className="w-[320px] sm:w-[380px] p-6 rounded-2xl bg-secondary/30 border border-border/70 backdrop-blur-xs flex flex-col justify-between whitespace-normal shrink-0 m-0"
              >
                <blockquote className="text-xs sm:text-sm text-foreground/90 font-body leading-relaxed m-0 italic">
                  “{item.quote}”
                </blockquote>
                <figcaption className="mt-5 pt-4 border-t border-border/40 flex items-center gap-3">
                  <div className="w-8 h-8 rounded-full bg-accent/20 text-accent font-semibold text-xs flex items-center justify-center shrink-0">
                    {item.avatar}
                  </div>
                  <div className="text-left">
                    <div className="text-xs font-semibold text-foreground">{item.name}</div>
                    <div className="text-[11px] text-muted-foreground">
                      {item.role} · {item.city}
                    </div>
                  </div>
                </figcaption>
              </figure>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
