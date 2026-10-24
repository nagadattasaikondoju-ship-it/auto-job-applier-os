"use client";

import React, { useRef, useState, MouseEvent } from "react";
import { motion } from "framer-motion";
import { Sparkles, Zap, Coins, Check } from "lucide-react";
import { cn } from "@/lib/utils";
import { landingContent, PricingPlan, CreditPack } from "@/content/landing";

// Helper Component: Material Symbols Icon
export function MIcon({
  name,
  size = 20,
  weight = 400,
  fill = 0,
  grade = 0,
  opticalSize = 24,
  className,
}: {
  name: string;
  size?: number;
  weight?: number;
  fill?: number;
  grade?: number;
  opticalSize?: number;
  className?: string;
}) {
  return (
    <span
      className={cn("material-symbols-outlined select-none leading-none", className)}
      style={{
        fontSize: size,
        fontVariationSettings: `'FILL' ${fill}, 'wght' ${weight}, 'GRAD' ${grade}, 'opsz' ${opticalSize}`,
      }}
      aria-hidden="true"
    >
      {name}
    </span>
  );
}

// Helper Component: FadeUp
export function FadeUp({
  children,
  delay = 0,
  className,
}: {
  children: React.ReactNode;
  delay?: number;
  className?: string;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 24 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, amount: 0.2 }}
      transition={{ duration: 0.6, delay, ease: [0.22, 1, 0.36, 1] }}
      className={className}
    >
      {children}
    </motion.div>
  );
}

// Helper Component: SpotlightBorder
export function SpotlightBorder({
  children,
  className,
  size = 520,
  intensity = 0.5,
}: {
  children: React.ReactNode;
  className?: string;
  size?: number;
  intensity?: number;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [coords, setCoords] = useState({ x: -9999, y: -9999 });

  const handlePointerMove = (e: MouseEvent<HTMLDivElement>) => {
    if (!containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    setCoords({
      x: e.clientX - rect.left,
      y: e.clientY - rect.top,
    });
  };

  const handlePointerLeave = () => {
    setCoords({ x: -9999, y: -9999 });
  };

  return (
    <div
      ref={containerRef}
      onMouseMove={handlePointerMove}
      onMouseLeave={handlePointerLeave}
      className={cn("relative rounded-2xl group", className)}
      style={
        {
          "--spot-x": `${coords.x}px`,
          "--spot-y": `${coords.y}px`,
          "--size": `${size}px`,
          "--intensity": intensity,
        } as React.CSSProperties
      }
    >
      <div
        className="pointer-events-none absolute -inset-[1px] rounded-2xl transition-opacity duration-300 opacity-60 group-hover:opacity-100"
        style={{
          background: `radial-gradient(circle var(--size) at var(--spot-x) var(--spot-y), rgba(255,255,255,var(--intensity)), transparent 60%)`,
        }}
        aria-hidden="true"
      />
      <div className="relative z-10 h-full">{children}</div>
    </div>
  );
}

export function PricingCard({
  plan,
  isYearly,
}: {
  plan: PricingPlan;
  isYearly: boolean;
}) {
  const displayPrice = isYearly ? plan.yearlyPrice : plan.price;

  return (
    <SpotlightBorder size={460} intensity={0.5} className="relative h-full p-2">
      <div
        className={cn(
          "relative flex h-full flex-col rounded-2xl border p-6 sm:p-7 transition-all duration-300",
          plan.featured
            ? "border-accent/80 shadow-[0_0_30px_rgba(99,102,241,0.15)] ring-1 ring-accent/40"
            : "border-white/10"
        )}
        style={{ backgroundColor: plan.bg }}
      >
        {plan.badge && (
          <div className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full border border-white/20 bg-accent px-3.5 py-1 text-xs font-semibold text-white shadow-md flex items-center gap-1">
            <Zap className="w-3 h-3 fill-current" />
            <span>{plan.badge}</span>
          </div>
        )}

        <FadeUp delay={0}>
          <h3 className="text-sm uppercase tracking-[0.2em] text-white/70 font-mono font-medium m-0">
            {plan.name}
          </h3>
        </FadeUp>
        <div className="mt-3 border-t border-white/10" />

        <FadeUp delay={0.1}>
          <div className="mt-6 flex items-baseline gap-1.5">
            <span className="text-xl text-white/60">₹</span>
            <span className="text-3xl sm:text-4xl leading-none font-bold tracking-tight text-white font-body">
              {displayPrice}
            </span>
            <span className="text-xs text-white/60 font-body">
              {plan.billingPeriod}
            </span>
            {plan.originalPrice && plan.price !== "0" && (
              <span className="text-xs text-white/40 line-through ml-1">
                ₹{plan.originalPrice}
              </span>
            )}
          </div>
        </FadeUp>

        <FadeUp delay={0.2}>
          <p className="mt-3 text-xs sm:text-sm leading-relaxed text-white/60 font-body min-h-[36px]">
            {plan.description}
          </p>
        </FadeUp>

        <FadeUp delay={0.3}>
          <div className="mt-5">
            <a
              href="#hero"
              className={cn(
                "w-full inline-flex items-center justify-center rounded-full font-body text-xs sm:text-sm font-medium h-9 sm:h-10 px-4 transition-all duration-200 cursor-pointer shadow-xs hover:scale-[1.02]",
                plan.featured
                  ? "bg-white text-black hover:bg-white/90 font-semibold"
                  : "bg-white/[0.10] hover:bg-white/[0.16] border border-white/10 text-white backdrop-blur-[2.5px]"
              )}
            >
              Choose {plan.name}
            </a>
          </div>
        </FadeUp>

        <FadeUp delay={0.4}>
          <ul className="mt-6 flex flex-1 flex-col gap-1.5 list-none p-0">
            {plan.features.map((f, i) => (
              <li
                key={f.text}
                className={cn(
                  "flex items-center gap-2.5 py-2.5 text-xs sm:text-sm font-body",
                  i !== 0 && "border-t border-white/10",
                  f.included ? "text-white/85" : "text-white/40"
                )}
              >
                <span
                  className={cn(
                    "flex h-4 w-4 shrink-0 items-center justify-center rounded-full border",
                    f.included
                      ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-400"
                      : "border-white/10 bg-transparent text-white/30"
                  )}
                >
                  {f.included ? (
                    <Check className="w-2.5 h-2.5" />
                  ) : (
                    <MIcon name="close" size={10} className="text-white/40" />
                  )}
                </span>
                <span>{f.text}</span>
              </li>
            ))}
          </ul>
        </FadeUp>
      </div>
    </SpotlightBorder>
  );
}

export function PricingSection() {
  const [isYearly, setIsYearly] = useState(false);
  const plans = landingContent.pricing;
  const credits = landingContent.credits;

  return (
    <section
      id="pricing"
      aria-labelledby="pricing-heading"
      className="relative w-full bg-[#000000] text-white py-20 sm:py-28 border-t border-white/10"
    >
      <div className="mx-auto max-w-7xl px-4 sm:px-6">
        {/* HEADER */}
        <div className="mb-14 flex flex-col items-start gap-8 lg:flex-row lg:items-end lg:justify-between">
          <div className="max-w-2xl">
            <FadeUp>
              <span className="mb-4 inline-flex items-center gap-2 rounded-full bg-white/[0.10] border border-white/10 px-3 py-1 text-xs text-white/80 backdrop-blur">
                <Coins className="w-3.5 h-3.5 text-amber-400" />
                Hybrid Monetization Model
              </span>
            </FadeUp>
            <FadeUp delay={0.1}>
              <h2
                id="pricing-heading"
                className="text-3xl sm:text-4xl lg:text-5xl font-normal tracking-[-0.02em] leading-[1.05] text-white"
              >
                Subscription for the toolkit,
                <br className="hidden sm:block" /> credits for application volume.
              </h2>
            </FadeUp>
            <FadeUp delay={0.15}>
              <p className="mt-3 text-sm sm:text-base text-white/60 max-w-xl">
                Just like AIApply, we separate your monthly copilot platform toolkit from pay-as-you-go Auto Apply credit packs. One credit equals one verified application.
              </p>
            </FadeUp>
          </div>

          <FadeUp delay={0.2}>
            {/* Monthly / Yearly Billing Pill */}
            <div className="flex items-center gap-2 p-1.5 rounded-full bg-white/[0.08] border border-white/15">
              <button
                type="button"
                onClick={() => setIsYearly(false)}
                className={cn(
                  "px-4 py-1.5 rounded-full text-xs font-medium transition-all cursor-pointer",
                  !isYearly ? "bg-white text-black shadow-xs" : "text-white/60 hover:text-white"
                )}
              >
                Monthly
              </button>
              <button
                type="button"
                onClick={() => setIsYearly(true)}
                className={cn(
                  "px-4 py-1.5 rounded-full text-xs font-medium transition-all cursor-pointer flex items-center gap-1.5",
                  isYearly ? "bg-white text-black shadow-xs" : "text-white/60 hover:text-white"
                )}
              >
                <span>Yearly</span>
                <span className="px-1.5 py-0.2 rounded-full bg-emerald-500 text-black text-[10px] font-bold">
                  Save 20%
                </span>
              </button>
            </div>
          </FadeUp>
        </div>

        {/* 4 SUBSCRIPTION PLANS GRID */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
          {plans.map((p) => (
            <PricingCard key={p.name} plan={p} isYearly={isYearly} />
          ))}
        </div>

        {/* HYBRID CREDIT PACKS SECTION */}
        <div className="mt-16 sm:mt-20 rounded-3xl bg-gradient-to-br from-white/[0.06] to-white/[0.02] border border-white/15 p-6 sm:p-10 backdrop-blur-xl relative overflow-hidden">
          {/* Subtle accent glow */}
          <div
            className="absolute -top-24 -right-24 w-80 h-80 rounded-full bg-accent/20 blur-3xl pointer-events-none"
            aria-hidden="true"
          />

          <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6 pb-8 border-b border-white/10">
            <div>
              <div className="flex items-center gap-2 mb-2">
                <span className="px-2.5 py-0.5 rounded-md bg-amber-400/20 text-amber-300 text-xs font-mono font-semibold border border-amber-400/30">
                  {credits.unitRange}
                </span>
                <span className="text-xs text-white/50 font-mono">1 Credit = 1 Application</span>
              </div>
              <h3 className="text-2xl sm:text-3xl font-display font-medium text-white">
                {credits.heading}
              </h3>
              <p className="mt-2 text-sm text-white/60 max-w-xl">
                {credits.subheading} Credits never expire and can be used on demand for auto-apply submissions or premium ATS tailoring.
              </p>
            </div>

            <div className="shrink-0">
              <a
                href="#hero"
                className="inline-flex items-center gap-2 px-6 py-3 rounded-full bg-accent hover:bg-accent/90 text-white font-medium text-sm transition-transform hover:scale-105 shadow-md cursor-pointer"
              >
                <Sparkles className="w-4 h-4 text-amber-300" />
                <span>Buy Credits On Demand</span>
              </a>
            </div>
          </div>

          {/* 4 Credit Tiers Grid */}
          <div className="mt-8 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {credits.packs.map((pack) => (
              <div
                key={pack.credits}
                className={cn(
                  "p-5 rounded-2xl border transition-all flex flex-col justify-between relative",
                  pack.popular
                    ? "bg-white/[0.09] border-accent/60 shadow-lg shadow-accent/10"
                    : "bg-white/[0.04] border-white/10 hover:border-white/20"
                )}
              >
                {pack.badge && (
                  <span
                    className={cn(
                      "absolute -top-2.5 right-4 px-2 py-0.5 rounded-full text-[10px] font-semibold",
                      pack.popular
                        ? "bg-accent text-white"
                        : "bg-white/15 text-white/80 border border-white/20"
                    )}
                  >
                    {pack.badge}
                  </span>
                )}
                <div>
                  <div className="text-xl sm:text-2xl font-bold font-mono text-white">
                    {pack.credits} Credits
                  </div>
                  <div className="text-xs font-mono text-emerald-400 mt-1">
                    {pack.pricePerApp}
                  </div>
                </div>

                <div className="mt-4 pt-3 border-t border-white/10 flex items-baseline justify-between">
                  <div className="text-2xl font-bold text-white">₹{pack.price}</div>
                  <a
                    href="#hero"
                    className="text-xs text-accent font-semibold hover:underline"
                  >
                    Add pack →
                  </a>
                </div>
              </div>
            ))}
          </div>

          <div className="mt-6 flex flex-wrap items-center justify-between gap-3 text-xs text-white/50 font-mono">
            <span>✓ No monthly lock-in for credit packs</span>
            <span>✓ Credits carry forward indefinitely</span>
            <span>✓ Verified submission logs with full approvals</span>
          </div>
        </div>
      </div>
    </section>
  );
}
