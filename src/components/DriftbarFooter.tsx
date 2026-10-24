"use client";

import React from "react";

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
          src="https://d2ol7oe51mr4n9.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/4d01c727-d9c5-47c8-a778-35a451ffd39f.mp4"
          poster="https://d8j0ntlcm91z4.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/hf_20261014_121838_c97d0940-f430-4304-8573-4f47ee44f447.png"
          autoPlay
          muted
          loop
          playsInline
          preload="auto"
        />
        {/* Haze overlay so text stays perfectly readable */}
        <div
          className="absolute inset-0"
          style={{
            background:
              "linear-gradient(to bottom, #f1f1ee 0%, rgba(241, 241, 238, 0.96) 26%, rgba(241, 241, 238, 0.72) 44%, rgba(241, 241, 238, 0) 70%)",
          }}
        />
      </div>

      {/* 2. Giant Frosted Glass Wordmark sinking into fog */}
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
        Driftbar
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
            {/* Logo */}
            <a
              href="#"
              className="inline-flex items-center gap-2.5 text-[17px] font-medium tracking-tight text-[#0c0c0c]"
              aria-label="Driftbar home"
            >
              <span className="relative w-[30px] h-[30px] rounded-[8px] bg-gradient-to-b from-[#2b2b2b] to-[#0a0a0a] shadow-[0_1px_2px_rgba(0,0,0,0.25)] flex items-center justify-center">
                <span className="absolute inset-x-[13%] bottom-[14%] h-[19%] rounded-full bg-white" />
              </span>
              <span className="font-semibold text-lg">Driftbar</span>
            </a>

            {/* Title */}
            <h2 className="mt-5 text-xl sm:text-2xl font-semibold tracking-[-0.045em] leading-[1.2] text-[#0c0c0c]">
              The calm bar for macOS
            </h2>

            {/* Text */}
            <p className="mt-3.5 max-w-sm text-[13.7px] leading-[1.43] tracking-[-0.012em] text-[#6f6f6c]">
              Driftbar gathers music, tasks, meetings, weather, search, focus timers, quick notes, and more handy widgets into one calm floating bar just above your Mac Dock.
            </p>

            {/* Apple Logo CTA */}
            <div className="mt-5">
              <a
                href="#hero-waitlist"
                className="inline-flex items-center gap-2 h-[34px] px-4 rounded-[7px] bg-[#0c0c0c] hover:bg-[#262626] text-white text-[12px] font-medium transition-all hover:-translate-y-0.5 cursor-pointer shadow-sm"
              >
                <svg viewBox="0 0 24 24" fill="currentColor" className="w-3.5 h-3.5 -mt-0.5" aria-hidden="true">
                  <path d="M17.05 12.54c-.03-2.75 2.25-4.07 2.35-4.14-1.28-1.87-3.27-2.13-3.98-2.16-1.69-.17-3.3 1-4.16 1-.86 0-2.18-.97-3.59-.95-1.85.03-3.55 1.07-4.5 2.72-1.92 3.33-.49 8.25 1.38 10.95.91 1.32 2 2.8 3.43 2.75 1.38-.06 1.9-.89 3.56-.89 1.66 0 2.13.89 3.59.86 1.48-.03 2.42-1.34 3.33-2.67 1.05-1.53 1.48-3.02 1.5-3.1-.03-.01-2.88-1.1-2.91-4.37ZM14.31 4.46c.76-.92 1.27-2.2 1.13-3.46-1.09.04-2.41.73-3.19 1.64-.7.81-1.31 2.1-1.15 3.34 1.22.09 2.46-.62 3.21-1.52Z" />
                </svg>
                <span>Get Driftbar today</span>
              </a>
            </div>

            {/* Copyright & Credit */}
            <p className="mt-5 text-[12px] tracking-[0.01em] text-[#9c9c98]">
              © 2026 Driftbar Inc. - Made in Lisbon.
            </p>

            <div className="mt-3 flex items-center gap-1.5 text-[12px] font-medium text-[#0c0c0c]">
              <span>Built with</span>
              <span aria-label="love" className="text-sm">💙</span>
              <span>by</span>
              <span className="inline-flex items-center gap-1.5 ml-1">
                <span className="w-5 h-5 rounded-full overflow-hidden bg-[#e3e3e0] inline-block" aria-hidden="true">
                  <svg viewBox="0 0 24 24">
                    <rect width="24" height="24" fill="#e6e6e3" />
                    <circle cx="12" cy="9.2" r="4.4" fill="#1b1b1b" />
                    <path d="M3 25c0-6 4-9.4 9-9.4S21 19 21 25Z" fill="#1b1b1b" />
                  </svg>
                </span>
                <span className="font-semibold">Mira Okafor</span>
              </span>
            </div>

            {/* Status Chips */}
            <ul className="mt-4 flex flex-wrap gap-2" aria-label="Driftbar status">
              <li className="inline-flex items-center gap-2 h-[26px] px-3 rounded-full border border-[rgba(12,12,12,0.12)] bg-white/60 text-[11px] font-medium text-[#0c0c0c] backdrop-blur-xs">
                <span className="w-1.5 h-1.5 rounded-full bg-[#2fb36a] ring-2 ring-[#2fb36a]/20" aria-hidden="true" />
                <span>9,400 Macs in sync</span>
              </li>

              <li className="inline-flex items-center gap-1.5 h-[26px] px-3 rounded-full border border-[rgba(12,12,12,0.12)] bg-white/60 text-[11px] font-medium text-[#0c0c0c] backdrop-blur-xs">
                <svg viewBox="0 0 24 24" className="w-3 h-3 stroke-current fill-none stroke-2" aria-hidden="true">
                  <path d="M20 11a8 8 0 1 0-2.3 5.7" />
                  <path d="M20 4v7h-7" />
                </svg>
                <span>v1.8 · Shipped today</span>
              </li>

              <li className="inline-flex items-center gap-1.5 h-[26px] px-3 rounded-full border border-[rgba(12,12,12,0.12)] bg-white/60 text-[11px] font-medium text-[#0c0c0c] backdrop-blur-xs">
                <svg viewBox="0 0 24 24" className="w-3 h-3 stroke-current fill-none stroke-2" aria-hidden="true">
                  <path d="m12 3 2.7 5.6 6.1.8-4.5 4.2 1.1 6-5.4-2.9-5.4 2.9 1.1-6L3.2 9.4l6.1-.8Z" />
                </svg>
                <span>Rated 4.8 avg</span>
              </li>
            </ul>
          </div>

          {/* Col 1: Menu */}
          <nav aria-label="Menu" className="pt-2">
            <h3 className="text-[16px] font-semibold tracking-[-0.045em] text-[#0c0c0c]">
              Menu
            </h3>
            <ul className="mt-5 space-y-3.5 text-[13.7px] font-medium text-[#0c0c0c]">
              {["Tour", "Showcase", "Q&A", "Licence", "Journal"].map((item) => (
                <li key={item}>
                  <a href="#" className="hover:opacity-55 transition-opacity">
                    {item}
                  </a>
                </li>
              ))}
            </ul>
          </nav>

          {/* Col 2: Essentials */}
          <nav aria-label="Essentials" className="pt-2">
            <h3 className="text-[16px] font-semibold tracking-[-0.045em] text-[#0c0c0c]">
              Essentials
            </h3>
            <ul className="mt-5 space-y-4 text-[13.7px] text-[#161616] tracking-[0.022em]">
              {["Support", "Up next", "Privacy notice", "Usage guidelines", "Manage licences"].map(
                (item) => (
                  <li key={item}>
                    <a href="#" className="hover:opacity-55 transition-opacity">
                      {item}
                    </a>
                  </li>
                )
              )}
            </ul>
          </nav>

          {/* Col 3: From our team */}
          <nav aria-label="From our team" className="pt-2">
            <h3 className="text-[16px] font-semibold tracking-[-0.045em] text-[#0c0c0c]">
              From our team
            </h3>
            <ul className="mt-5 space-y-3.5 text-[13.7px] text-[#161616] tracking-[0.022em]">
              {[
                "Clipnest.io",
                "Tallyo.io",
                "Pinwell.io",
                "Glyfo.co",
                "Shelfmark.app",
                "Wireloom.com",
                "Gridcraft.app",
              ].map((item) => (
                <li key={item}>
                  <a href="#" className="hover:opacity-55 transition-opacity">
                    {item}
                  </a>
                </li>
              ))}
            </ul>
          </nav>
        </div>
      </div>
    </footer>
  );
}
