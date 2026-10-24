"use client";

import React from "react";
import { motion } from "framer-motion";

export function CapabilitiesSection() {
  return (
    <section
      id="capabilities"
      className="relative w-full bg-[#050505] text-white py-24 sm:py-32 overflow-hidden border-t border-white/5"
    >
      {/* Two faint vertical hairline guides at the thirds */}
      <div className="absolute inset-y-0 left-1/3 w-[1px] bg-white/[0.03] pointer-events-none" />
      <div className="absolute inset-y-0 left-2/3 w-[1px] bg-white/[0.03] pointer-events-none" />

      {/* Subtle top ambient amber glow */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[700px] h-[300px] bg-[radial-gradient(ellipse_at_top,rgba(255,165,36,0.12),transparent_70%)] pointer-events-none" />

      <div className="relative max-w-6xl mx-auto px-6">
        {/* Top Strip */}
        <div className="flex items-center justify-between font-mono text-[11px] uppercase tracking-[0.275em] text-white/45 mb-10 pb-4 border-b border-white/[0.06]">
          <div className="flex items-center gap-3">
            <span>01</span>
            <div className="w-8 h-[1px] bg-white/20" />
          </div>
          <div className="text-white/60 tracking-[0.3em] font-medium">
            // Capabilities
          </div>
          <div>Full Visibility</div>
        </div>

        {/* Headline & Lede */}
        <div className="max-w-3xl mb-16">
          <h2 className="text-4xl sm:text-5xl lg:text-6xl font-normal tracking-[-0.05em] leading-[1.05] text-white">
            <span
              className="font-semibold text-transparent bg-clip-text"
              style={{
                backgroundImage: "linear-gradient(90deg, #FFC24A 0%, #E9931E 50%, #A85A0C 100%)",
                filter: "drop-shadow(0 0 24px rgba(233,147,30,0.35))",
              }}
            >
              Clarity
            </span>{" "}
            across every layer
          </h2>
          <p className="mt-5 text-base sm:text-lg text-white/65 leading-relaxed max-w-2xl font-light">
            A unified view of your infrastructure. Detect patterns, anticipate issues, and optimize performance before problems arise.
          </p>
        </div>

        {/* 3 Amber Holographic Glass Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Card 1: Real-Time Signals */}
          <motion.div
            initial={{ opacity: 0, y: 24 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, amount: 0.2 }}
            transition={{ duration: 0.6, delay: 0.1 }}
            className="group relative rounded-2xl p-7 flex flex-col justify-between overflow-hidden border border-white/[0.08] hover:border-amber-500/40 transition-all duration-300"
            style={{
              backgroundColor: "rgba(255, 255, 255, 0.021)",
              backdropFilter: "blur(14px)",
              boxShadow: "0 20px 40px -15px rgba(0,0,0,0.7)",
            }}
          >
            {/* Amber radial glow */}
            <div
              className="absolute -top-10 -right-10 w-48 h-48 rounded-full pointer-events-none opacity-40 group-hover:opacity-75 transition-opacity"
              style={{
                background: "radial-gradient(circle, rgba(190,112,22,0.3) 0%, transparent 70%)",
              }}
            />

            {/* Stage: Holographic Radar Object */}
            <div className="h-44 w-full flex items-center justify-center relative mb-6">
              <svg viewBox="0 0 160 160" className="w-36 h-36">
                <defs>
                  <radialGradient id="amberGlow1" cx="50%" cy="50%" r="50%">
                    <stop offset="0%" stopColor="#FFC24A" stopOpacity="0.8" />
                    <stop offset="60%" stopColor="#E9931E" stopOpacity="0.2" />
                    <stop offset="100%" stopColor="#A85A0C" stopOpacity="0" />
                  </radialGradient>
                </defs>
                {/* Concentric radar rings */}
                <circle cx="80" cy="80" r="64" fill="none" stroke="#E9931E" strokeWidth="1" strokeDasharray="3 3" opacity="0.35" />
                <circle cx="80" cy="80" r="46" fill="none" stroke="#FFC24A" strokeWidth="1.2" opacity="0.5" />
                <circle cx="80" cy="80" r="28" fill="none" stroke="#FFC24A" strokeWidth="1.5" opacity="0.75" />
                {/* Center glowing orb */}
                <circle cx="80" cy="80" r="14" fill="url(#amberGlow1)" />
                <circle cx="80" cy="80" r="5" fill="#FFE29A" />
                {/* Radar sweep beam */}
                <line x1="80" y1="80" x2="135" y2="40" stroke="#FFE29A" strokeWidth="1.5" opacity="0.8" />
                {/* Small tracking dot on outer ring */}
                <circle cx="132" cy="42" r="3.5" fill="#FFC24A" className="animate-pulse" />
              </svg>
            </div>

            {/* Body */}
            <div>
              <h3 className="text-lg font-medium text-white/95 tracking-tight mb-2">
                Real-Time Signals
              </h3>
              <p className="text-sm text-white/60 leading-relaxed font-light">
                Stay ahead with live system data and continuous performance tracking across all nodes.
              </p>
            </div>
          </motion.div>

          {/* Card 2: Actionable Insights */}
          <motion.div
            initial={{ opacity: 0, y: 24 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, amount: 0.2 }}
            transition={{ duration: 0.6, delay: 0.2 }}
            className="group relative rounded-2xl p-7 flex flex-col justify-between overflow-hidden border border-white/[0.08] hover:border-amber-500/40 transition-all duration-300"
            style={{
              backgroundColor: "rgba(255, 255, 255, 0.021)",
              backdropFilter: "blur(14px)",
              boxShadow: "0 20px 40px -15px rgba(0,0,0,0.7)",
            }}
          >
            {/* Amber radial glow */}
            <div
              className="absolute -top-10 -right-10 w-48 h-48 rounded-full pointer-events-none opacity-40 group-hover:opacity-75 transition-opacity"
              style={{
                background: "radial-gradient(circle, rgba(190,112,22,0.3) 0%, transparent 70%)",
              }}
            />

            {/* Stage: Holographic Wireframe Spheres & Bar-Chart Cylinders */}
            <div className="h-44 w-full flex items-center justify-center relative mb-6">
              <svg viewBox="0 0 160 160" className="w-36 h-36">
                {/* 3 Short dashes above */}
                <line x1="55" y1="30" x2="68" y2="30" stroke="#FFE29A" strokeWidth="1.5" strokeLinecap="round" opacity="0.8" />
                <line x1="74" y1="30" x2="87" y2="30" stroke="#FFE29A" strokeWidth="1.5" strokeLinecap="round" opacity="0.8" />
                <line x1="93" y1="30" x2="106" y2="30" stroke="#FFE29A" strokeWidth="1.5" strokeLinecap="round" opacity="0.8" />

                {/* Overlapping wireframe spheres */}
                <ellipse cx="62" cy="85" rx="26" ry="26" fill="none" stroke="#E9931E" strokeWidth="1" opacity="0.4" />
                <ellipse cx="62" cy="85" rx="26" ry="10" fill="none" stroke="#FFC24A" strokeWidth="1" opacity="0.5" />
                <ellipse cx="88" cy="72" rx="22" ry="22" fill="none" stroke="#FFC24A" strokeWidth="1.2" opacity="0.6" />
                <ellipse cx="88" cy="72" rx="22" ry="8" fill="none" stroke="#E9931E" strokeWidth="1" opacity="0.4" />

                {/* Glowing bar chart cylinders */}
                <rect x="116" y="70" width="8" height="42" rx="3" fill="none" stroke="#FFE29A" strokeWidth="1.2" opacity="0.8" />
                <rect x="128" y="52" width="8" height="60" rx="3" fill="none" stroke="#FFC24A" strokeWidth="1.2" opacity="0.9" />
              </svg>
            </div>

            {/* Body */}
            <div>
              <h3 className="text-lg font-medium text-white/95 tracking-tight mb-2">
                Actionable Insights
              </h3>
              <p className="text-sm text-white/60 leading-relaxed font-light">
                Turn complex data into clear decisions with instant, intelligent analysis.
              </p>
            </div>
          </motion.div>

          {/* Card 3: Automated Reporting */}
          <motion.div
            initial={{ opacity: 0, y: 24 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, amount: 0.2 }}
            transition={{ duration: 0.6, delay: 0.3 }}
            className="group relative rounded-2xl p-7 flex flex-col justify-between overflow-hidden border border-white/[0.08] hover:border-amber-500/40 transition-all duration-300"
            style={{
              backgroundColor: "rgba(255, 255, 255, 0.021)",
              backdropFilter: "blur(14px)",
              boxShadow: "0 20px 40px -15px rgba(0,0,0,0.7)",
            }}
          >
            {/* Amber radial glow */}
            <div
              className="absolute -top-10 -right-10 w-48 h-48 rounded-full pointer-events-none opacity-40 group-hover:opacity-75 transition-opacity"
              style={{
                background: "radial-gradient(circle, rgba(190,112,22,0.3) 0%, transparent 70%)",
              }}
            />

            {/* Stage: Translucent Glowing Document Sheets */}
            <div className="h-44 w-full flex items-center justify-center relative mb-6">
              <svg viewBox="0 0 160 160" className="w-36 h-36">
                {/* Back document sheet */}
                <rect
                  x="56"
                  y="40"
                  width="58"
                  height="72"
                  rx="4"
                  fill="none"
                  stroke="#A85A0C"
                  strokeWidth="1.2"
                  opacity="0.45"
                  transform="rotate(6 85 76)"
                />
                {/* Middle document sheet */}
                <rect
                  x="48"
                  y="46"
                  width="58"
                  height="72"
                  rx="4"
                  fill="rgba(233,147,30,0.06)"
                  stroke="#E9931E"
                  strokeWidth="1.2"
                  opacity="0.7"
                  transform="rotate(-4 77 82)"
                />
                {/* Front document sheet */}
                <rect
                  x="52"
                  y="48"
                  width="60"
                  height="74"
                  rx="4"
                  fill="rgba(255,194,74,0.08)"
                  stroke="#FFE29A"
                  strokeWidth="1.5"
                  opacity="0.95"
                />
                {/* Text lines on front sheet */}
                <line x1="62" y1="62" x2="88" y2="62" stroke="#FFE29A" strokeWidth="2" strokeLinecap="round" opacity="0.9" />
                <line x1="62" y1="72" x2="100" y2="72" stroke="#FFC24A" strokeWidth="1.5" strokeLinecap="round" opacity="0.7" />
                <line x1="62" y1="80" x2="94" y2="80" stroke="#FFC24A" strokeWidth="1.5" strokeLinecap="round" opacity="0.7" />
                <line x1="62" y1="88" x2="82" y2="88" stroke="#E9931E" strokeWidth="1.5" strokeLinecap="round" opacity="0.5" />
                <circle cx="100" cy="106" r="4" fill="#FFC24A" opacity="0.85" />
              </svg>
            </div>

            {/* Body */}
            <div>
              <h3 className="text-lg font-medium text-white/95 tracking-tight mb-2">
                Automated Reporting
              </h3>
              <p className="text-sm text-white/60 leading-relaxed font-light">
                Generate structured reports that reveal system health at a glance.
              </p>
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  );
}
