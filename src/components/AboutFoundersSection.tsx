"use client";

import React from "react";
import { ArrowUpRight } from "lucide-react";

export function AboutFoundersSection() {
  const statCards = [
    {
      value: "100%",
      text: "of resume changes are checked against your real experience. We never invent skills, titles or numbers.",
      image: "/media/about-1.webp",
      offset: false,
      clipPath:
        "polygon(64px 0, calc(100% - 14px) 0, calc(100% - 4px) 4px, 100% 14px, 100% calc(100% - 14px), calc(100% - 4px) calc(100% - 4px), calc(100% - 14px) 100%, 14px 100%, 4px calc(100% - 4px), 0 calc(100% - 14px), 0 64px)",
      textPlacement: "left-6 right-6 bottom-6",
    },
    {
      value: "< 1 min",
      text: "to get your free ATS score and a list of fixes after you upload your resume.",
      image: "/media/about-2.webp",
      offset: true,
      clipPath:
        "polygon(0 14px, 4px 4px, 14px 0, calc(100% - 64px) 0, 100% 64px, 100% calc(100% - 14px), calc(100% - 4px) calc(100% - 4px), calc(100% - 14px) 100%, 64px 100%, 0 calc(100% - 64px))",
      textPlacement: "left-6 bottom-20",
    },
    {
      value: "0",
      text: "applications sent without your approval in Review mode. You see every one first.",
      image: "/media/about-3.webp",
      offset: false,
      clipPath:
        "polygon(0 14px, 4px 4px, 14px 0, calc(100% - 64px) 0, 100% 64px, 100% calc(100% - 64px), calc(100% - 64px) 100%, 14px 100%, 4px calc(100% - 4px), 0 calc(100% - 14px))",
      textPlacement: "left-6 right-28 bottom-6",
    },
  ];

  return (
    <section
      id="about"
      className="relative min-h-screen py-20 sm:py-28 px-6 sm:px-10 flex flex-col justify-center overflow-hidden"
      style={{ backgroundColor: "#F0F5F7" }}
    >
      <div className="max-w-7xl mx-auto w-full relative z-0">
        {/* Top row -- heading + description (side by side on desktop) */}
        <div className="flex flex-col lg:flex-row items-start justify-between gap-10 lg:gap-20 text-[#154359]">
          {/* Left side -- Section heading */}
          <div>
            <h2 className="font-firs text-[36px] sm:text-[48px] lg:text-[54px] font-semibold uppercase tracking-tight leading-[0.95] text-[#154359]">
              About
              <br />
              Applyon
            </h2>
          </div>

          {/* Right side -- Description block */}
          <div className="flex flex-col max-w-xl text-[#154359]">
            <div className="text-[17px] sm:text-[18px] leading-[1.5]">
              <p>
                Applyon is an AI job copilot built for India. It reads your resume, finds roles that fit on LinkedIn, Indeed
                and company career pages, and tailors your resume and answers for each one.
              </p>
              <p className="mt-4">
                Our rule is simple: your applications stay honest. Every change is checked against what you&apos;ve really done,
                and nothing is sent until you say so.
              </p>
            </div>

            {/* External link */}
            <a
              href="/onboarding"
              className="group inline-flex items-center gap-4 mt-6 text-[14px] font-medium text-[#154359]"
            >
              <span>Get your free ATS score</span>
              <div
                className="flex items-center justify-center w-8 h-8 border border-[#154359] transition-transform group-hover:-translate-y-0.5"
                style={{
                  clipPath: "polygon(8px 0, 100% 0, 100% calc(100% - 8px), calc(100% - 8px) 100%, 0 100%, 0 8px)",
                }}
              >
                <ArrowUpRight className="w-3.5 h-3.5" strokeWidth={2} />
              </div>
            </a>
          </div>
        </div>

        {/* Stats cards grid (below heading row) */}
        <div className="mt-14 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {statCards.map((card, i) => (
            <div
              key={card.value}
              className={`relative w-full h-[280px] sm:h-[340px] ${
                card.offset ? "lg:mt-24" : ""
              }`}
              style={{
                backgroundColor: "rgba(255, 255, 255, 0.8)",
                padding: "1.5px",
                clipPath: card.clipPath,
              }}
            >
              {/* Inner div with background image and matching clip-path */}
              <div
                className="relative w-full h-full overflow-hidden bg-cover bg-center"
                style={{
                  backgroundImage: `url('${card.image}')`,
                  mixBlendMode: "normal",
                  clipPath: card.clipPath,
                }}
              >
                {/* Subtle soft tint for readability */}
                <div className="absolute inset-0 bg-white/10 backdrop-blur-[1px]" />

                {/* Text overlay inside each card */}
                <div className={`absolute ${card.textPlacement} max-w-[66%] z-10`}>
                  <div
                    className="font-firs font-semibold uppercase leading-none text-[36px] sm:text-[52px]"
                    style={{
                      background: "linear-gradient(294deg, #185B7B 20%, #4BBDF0)",
                      WebkitBackgroundClip: "text",
                      backgroundClip: "text",
                      color: "transparent",
                    }}
                  >
                    {card.value}
                  </div>
                  <p className="mt-3 text-[14px] leading-[1.4] text-[#154359]">
                    {card.text}
                  </p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Bottom fade overlay */}
      <div
        className="pointer-events-none absolute inset-x-0 bottom-0 h-40 sm:h-56 z-10"
        style={{
          background:
            "linear-gradient(to bottom, rgba(240, 245, 247, 0) 0%, rgba(240, 245, 247, 0.7) 60%, #F0F5F7 100%)",
        }}
      />
    </section>
  );
}
