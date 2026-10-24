"use client";

import React, { useRef, useState, MouseEvent } from "react";
import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

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
      viewport={{ once: true, amount: 0.3 }}
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
  radius = "2xl",
  size = 520,
  intensity = 0.5,
}: {
  children: React.ReactNode;
  className?: string;
  radius?: string;
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
      {/* Outer 1px spotlight gradient ring */}
      <div
        className="pointer-events-none absolute -inset-[1px] rounded-2xl transition-opacity duration-300 opacity-60 group-hover:opacity-100"
        style={{
          background: `radial-gradient(circle var(--size) at var(--spot-x) var(--spot-y), rgba(255,255,255,var(--intensity)), transparent 60%)`,
        }}
      />
      {/* Inner card container */}
      <div className="relative z-10 h-full">{children}</div>
    </div>
  );
}

// Buttons
export function PrimaryButton({
  href,
  children,
  size = "sm",
}: {
  href: string;
  children: React.ReactNode;
  size?: "sm" | "md";
}) {
  return (
    <a
      href={href}
      className={cn(
        "inline-flex items-center justify-center rounded-full font-body leading-none transition-all duration-200 cursor-pointer",
        "bg-white/90 hover:bg-white text-black font-medium shadow-sm hover:scale-[1.02]",
        size === "sm" ? "h-9 px-5 text-sm" : "h-11 px-6 text-base"
      )}
    >
      {children}
    </a>
  );
}

export function SecondaryButton({
  href,
  children,
  size = "sm",
}: {
  href: string;
  children: React.ReactNode;
  size?: "sm" | "md";
}) {
  return (
    <a
      href={href}
      className={cn(
        "inline-flex items-center justify-center rounded-full font-body leading-none transition-all duration-200 cursor-pointer",
        "bg-white/[0.10] hover:bg-white/[0.16] border border-white/10 text-white backdrop-blur-[2.5px] font-medium hover:scale-[1.02]",
        size === "sm" ? "h-9 px-5 text-sm" : "h-11 px-6 text-base"
      )}
    >
      {children}
    </a>
  );
}

// Plans Data
export type Feature = { text: string; included: boolean };
export type Plan = {
  name: string;
  price: string;
  originalPrice?: string;
  description: string;
  features: Feature[];
  featured?: boolean;
  badge?: string;
  bg: string;
};

const plans: Plan[] = [
  {
    name: "Course",
    price: "159",
    originalPrice: "497",
    description: "Once. Lifetime. 68% off.",
    bg: "#161616",
    features: [
      { text: "All courses and videos", included: true },
      { text: "All modules. Lifetime access.", included: true },
      { text: "AI Builder", included: true },
      { text: "Unlimited Templates", included: false },
      { text: "Unlimited Motion Videos", included: false },
    ],
  },
  {
    name: "Course + Lovable Templates",
    price: "239",
    originalPrice: "697",
    description: "Once. Lifetime. Best deal.",
    bg: "#252525",
    features: [
      { text: "All courses and videos", included: true },
      { text: "All modules. Lifetime access.", included: true },
      { text: "AI Builder", included: true },
      { text: "Unlimited Templates", included: true },
      { text: "Unlimited Motion Videos", included: true },
    ],
    featured: true,
    badge: "Best Value",
  },
];

export function PricingCard({ plan }: { plan: Plan }) {
  return (
    <SpotlightBorder radius="2xl" size={460} intensity={0.5} className="relative h-full p-2 sm:p-3">
      <div
        className="relative flex h-full flex-col rounded-2xl border border-white/10 p-7 sm:p-8"
        style={{ backgroundColor: plan.bg }}
      >
        {plan.badge && (
          <div className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full border border-white/15 bg-white px-3 py-1 text-xs font-semibold text-black shadow-md">
            {plan.badge}
          </div>
        )}

        <FadeUp delay={0}>
          <div className="text-[11px] uppercase tracking-[0.2em] text-white/60 font-mono">
            {plan.name}
          </div>
        </FadeUp>
        <div className="mt-3 border-t border-white/10" />

        <FadeUp delay={0.1}>
          <div className="mt-10 flex items-baseline gap-2">
            <span className="text-[2.75rem] leading-none font-normal tracking-tight text-white font-body">
              ${plan.price}
            </span>
            {plan.originalPrice && (
              <span className="text-lg text-white/40 line-through">
                ${plan.originalPrice}
              </span>
            )}
          </div>
        </FadeUp>

        <FadeUp delay={0.2}>
          <p className="mt-4 text-sm leading-relaxed text-white/60 font-body">
            {plan.description}
          </p>
        </FadeUp>

        <FadeUp delay={0.3}>
          <div className="mt-7">
            {plan.featured ? (
              <PrimaryButton href="#hero-waitlist" size="sm">
                Get Started
              </PrimaryButton>
            ) : (
              <SecondaryButton href="#hero-waitlist" size="sm">
                Get Started
              </SecondaryButton>
            )}
          </div>
        </FadeUp>

        <FadeUp delay={0.4}>
          <ul className="mt-7 flex flex-1 flex-col gap-2">
            {plan.features.map((f, i) => (
              <li
                key={f.text}
                className={cn(
                  "flex items-center gap-3 py-4 text-sm font-body",
                  i !== 0 && "border-t border-white/10",
                  f.included ? "text-white/85" : "text-white/40"
                )}
              >
                <span
                  className={cn(
                    "flex h-5 w-5 shrink-0 items-center justify-center rounded-full border",
                    f.included
                      ? "border-white/20 bg-white/[0.06]"
                      : "border-white/10 bg-transparent"
                  )}
                >
                  {f.included ? (
                    <MIcon name="check" size={12} className="text-white" />
                  ) : (
                    <MIcon name="close" size={12} className="text-white/50" />
                  )}
                </span>
                {f.text}
              </li>
            ))}
          </ul>
        </FadeUp>
      </div>
    </SpotlightBorder>
  );
}

export function PricingSection() {
  return (
    <section id="pricing" className="relative w-full bg-[#000000] text-white py-16 sm:py-24 border-t border-white/10">
      <div className="mx-auto max-w-[1080px] px-4 sm:px-6">
        {/* HEADER */}
        <div className="mb-14 flex flex-col items-start gap-10 lg:flex-row lg:items-end lg:justify-between">
          <div className="max-w-2xl">
            <FadeUp>
              <span className="mb-6 inline-flex items-center gap-2 rounded-full bg-white/[0.10] border border-white/10 px-3 py-1 text-xs text-white/80 backdrop-blur">
                <span className="h-1.5 w-1.5 rounded-full bg-white/70" />
                Pricing
              </span>
            </FadeUp>
            <FadeUp delay={0.1}>
              <h2 className="text-3xl sm:text-4xl font-normal tracking-[-0.02em] leading-[1.05] text-white">
                Clear pricing plans
                <br className="hidden sm:block" /> that scale with you.
              </h2>
            </FadeUp>
          </div>
          <FadeUp delay={0.2}>
            <p className="max-w-sm text-sm sm:text-base text-white/60">
              One-time payment. Lifetime access. Pick the plan that fits how far you want to go.
            </p>
          </FadeUp>
        </div>

        {/* CARDS */}
        <div className="mx-auto grid max-w-3xl grid-cols-1 gap-6 md:grid-cols-2">
          {plans.map((p) => (
            <PricingCard key={p.name} plan={p} />
          ))}
        </div>
      </div>
    </section>
  );
}
