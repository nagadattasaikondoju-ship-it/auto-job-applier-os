"use client";

import React from "react";
import Link from "next/link";
import { landingContent } from "@/content/landing";

export function DriftbarFooter() {
  return (
    <footer
      className="relative w-full overflow-hidden isolation-isolate select-none font-body min-h-[680px] lg:h-[720px]"
      style={{
        backgroundColor: "#f1f1ee",
        color: "#0c0c0c",
      }}
    >
      {/* 1. Stage & Meadow Video */}
      <div className="absolute inset-0 z-0 pointer-events-none" aria-hidden="true">
        <video
          className="w-full h-full object-cover object-[50%_100%] translate-y-[9%]"
          src="/media/footer.mp4"
          poster="/media/footer-poster.webp"
          autoPlay
          muted
          loop
          playsInline
          preload="metadata"
        />
        <div
          className="absolute inset-0"
          style={{
            background:
              "linear-gradient(to bottom, #f1f1ee 0%, rgba(241, 241, 238, 0.96) 26%, rgba(241, 241, 238, 0.72) 44%, rgba(241, 241, 238, 0) 70%)",
          }}
        />
      </div>

      {/* 2. Giant Frosted Glass Wordmark (Decorative, aria-hidden) */}
      <p
        className="absolute left-1/2 -bottom-2 -translate-x-1/2 z-1 m-0 pointer-events-none whitespace-nowrap font-bold tracking-[-0.045em] leading-[0.74] text-[20vw] sm:text-[180px] lg:text-[260px]"
        aria-hidden="true"
        style={{
          color: "rgba(232, 234, 250, 0.4)",
          background:
            "linear-gradient(to bottom, rgba(255, 255, 255, 0.78), rgba(214, 218, 246, 0.36) 48%, rgba(255, 255, 255, 0.62))",
          WebkitBackgroundClip: "text",
          backgroundClip: "text",
          WebkitTextFillColor: "transparent",
          filter:
            "drop-shadow(0 -1px 0 rgba(255, 255, 255, 0.55)) drop-shadow(0 0 18px rgba(190, 200, 255, 0.45))",
        }}
      >
        Applyon
      </p>

      {/* 3. Fog overlay at bottom edge */}
      <div
        className="absolute inset-x-0 bottom-0 h-[17%] z-2 pointer-events-none"
        aria-hidden="true"
        style={{
          background:
            "linear-gradient(to top, #e2e3f1 0%, rgba(226, 227, 241, 0.6) 30%, rgba(226, 227, 241, 0) 100%)",
        }}
      />

      {/* 4. Content Grid */}
      <div className="relative z-3 max-w-[1440px] mx-auto pt-16 sm:pt-20 px-6 sm:px-12 lg:px-24">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-[440px_200px_200px_1fr] gap-10 lg:gap-12 items-start">
          {/* Brand Block */}
          <div className="flex flex-col">
            <Link
              href="/"
              className="inline-flex items-center gap-2.5 text-[17px] font-medium tracking-tight text-[#0c0c0c]"
              aria-label="Applyon home"
            >
              <span className="relative w-[30px] h-[30px] rounded-[8px] bg-gradient-to-b from-[#2b2b2b] to-[#0a0a0a] shadow-[0_1px_2px_rgba(0,0,0,0.25)] flex items-center justify-center">
                <span className="absolute inset-x-[13%] bottom-[14%] h-[19%] rounded-full bg-white" />
              </span>
              <span className="font-semibold text-lg">Applyon</span>
            </Link>

            <h2 className="mt-5 text-xl sm:text-2xl font-semibold tracking-[-0.045em] leading-[1.2] text-[#0c0c0c]">
              The AI Job Search Copilot for India
            </h2>

            {/* Brand line */}
            <p className="mt-3.5 max-w-sm text-[13.7px] leading-[1.43] tracking-[-0.012em] text-[#6f6f6c]">
              Applyon — AI-powered job applications for India. Tailor your resume, autofill forms, and manage your job hunt from one unified dashboard.
            </p>

            {/* Primary CTA */}
            <div className="mt-5">
              <a
                href="/signup"
                className="inline-flex items-center gap-2 h-[34px] px-4 rounded-[7px] bg-[#0c0c0c] hover:bg-[#262626] text-white text-[12px] font-medium transition-all hover:-translate-y-0.5 cursor-pointer shadow-xs"
              >
                <span>Apply for jobs</span>
              </a>
            </div>

            {/* Copyright */}
            <p className="mt-5 text-[12px] tracking-[0.01em] text-[#9c9c98]">
              © 2026 Applyon Inc. - Made with pride in India 🇮🇳
            </p>

            <div className="mt-3 flex items-center gap-1.5 text-[12px] font-medium text-[#0c0c0c]">
              <span>Built with</span>
              <span aria-label="love" className="text-sm">💙</span>
              <span>by the</span>
              <span className="font-semibold">Applyon Core Team</span>
            </div>

            {/* Status Chips */}
            <ul className="mt-4 flex flex-wrap gap-2 list-none p-0" aria-label="Applyon status">
              <li className="inline-flex items-center gap-2 h-[26px] px-3 rounded-full border border-[rgba(12,12,12,0.12)] bg-white/60 text-[11px] font-medium text-[#0c0c0c] backdrop-blur-xs">
                <span className="w-1.5 h-1.5 rounded-full bg-[#2fb36a] ring-2 ring-[#2fb36a]/20" aria-hidden="true" />
                <span>Free ATS resume check</span>
              </li>

              <li className="inline-flex items-center gap-1.5 h-[26px] px-3 rounded-full border border-[rgba(12,12,12,0.12)] bg-white/60 text-[11px] font-medium text-[#0c0c0c] backdrop-blur-xs">
                <span>You approve every application</span>
              </li>

              <li className="inline-flex items-center gap-1.5 h-[26px] px-3 rounded-full border border-[rgba(12,12,12,0.12)] bg-white/60 text-[11px] font-medium text-[#0c0c0c] backdrop-blur-xs">
                <span>Rated 4.9 by early testers</span>
              </li>
            </ul>
          </div>

          {/* Navigation Columns */}
          <nav aria-label="Footer" className="col-span-1 md:col-span-3 grid grid-cols-1 sm:grid-cols-3 gap-8">
            {/* Col 1: Solutions */}
            <div>
              <h3 className="text-[16px] font-semibold tracking-[-0.045em] text-[#0c0c0c]">
                Solutions
              </h3>
              <ul className="mt-5 space-y-3.5 text-[13.7px] font-medium text-[#0c0c0c] list-none p-0">
                <li>
                  <Link href="/resume-tailoring" className="hover:opacity-55 transition-opacity">
                    AI Resume Tailoring
                  </Link>
                </li>
                <li>
                  <Link href="/autofill-job-applications" className="hover:opacity-55 transition-opacity">
                    Autofill Job Applications
                  </Link>
                </li>
                <li>
                  <Link href="/jobs-for-freshers" className="hover:opacity-55 transition-opacity">
                    Jobs for Freshers in India
                  </Link>
                </li>
                <li>
                  <a href="#how-it-works" className="hover:opacity-55 transition-opacity">
                    How Applyon Works
                  </a>
                </li>
                <li>
                  <a href="#pricing" className="hover:opacity-55 transition-opacity">
                    Pricing & Plans
                  </a>
                </li>
              </ul>
            </div>

            {/* Col 2: Resources & Legal */}
            <div>
              <h3 className="text-[16px] font-semibold tracking-[-0.045em] text-[#0c0c0c]">
                Resources & Legal
              </h3>
              <ul className="mt-5 space-y-3.5 text-[13.7px] text-[#161616] tracking-[0.022em] list-none p-0">
                <li>
                  <Link href="/blog" className="hover:opacity-55 transition-opacity">
                    Career Blog & Guides
                  </Link>
                </li>
                <li>
                  <Link href="/privacy" className="hover:opacity-55 transition-opacity">
                    Privacy Policy
                  </Link>
                </li>
                <li>
                  <Link href="/terms" className="hover:opacity-55 transition-opacity">
                    Terms of Service
                  </Link>
                </li>
                <li>
                  <a href="#our-promise" className="hover:opacity-55 transition-opacity">
                    Our Safety Promise
                  </a>
                </li>
                <li>
                  <a href="#faq" className="hover:opacity-55 transition-opacity">
                    Frequently Asked Questions
                  </a>
                </li>
              </ul>
            </div>

            {/* Col 3: Tech Hubs */}
            <div>
              <h3 className="text-[16px] font-semibold tracking-[-0.045em] text-[#0c0c0c]">
                Tech Hubs in India
              </h3>
              <ul className="mt-5 space-y-3.5 text-[13.7px] text-[#161616] tracking-[0.022em] list-none p-0">
                <li>
                  <span className="text-[#6f6f6c]">Bengaluru Tech Startups</span>
                </li>
                <li>
                  <span className="text-[#6f6f6c]">Hyderabad IT Hubs</span>
                </li>
                <li>
                  <span className="text-[#6f6f6c]">Pune Engineering Roles</span>
                </li>
                <li>
                  <span className="text-[#6f6f6c]">Delhi NCR Tech Ventures</span>
                </li>
                <li>
                  <span className="text-[#6f6f6c]">Mumbai FinTech Companies</span>
                </li>
              </ul>
            </div>
          </nav>
        </div>
      </div>
    </footer>
  );
}
