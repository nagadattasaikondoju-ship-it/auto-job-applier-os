"use client";

import React from "react";
import { ArrowUpRight } from "lucide-react";

export function AboutFoundersSection() {
  const statCards = [
    {
      value: "7+ years",
      text: "Launchex has served the market, guiding ventures and their journeys",
      image:
        "https://images.higgs.ai/?default=1&output=webp&url=https%3A%2F%2Fd8j0ntlcm91z4.cloudfront.net%2Fuser_38xzZboKViGWJOttwIXH07lWA1P%2Fhf_20260514_154203_6c6f94dc-a07e-4ba5-8688-106f01ccd2c8.png&w=1280&q=85",
      offset: false,
      clipPath:
        "polygon(64px 0, calc(100% - 14px) 0, calc(100% - 4px) 4px, 100% 14px, 100% calc(100% - 14px), calc(100% - 4px) calc(100% - 4px), calc(100% - 14px) 100%, 14px 100%, 4px calc(100% - 4px), 0 calc(100% - 14px), 0 64px)",
      textPlacement: "left-6 right-6 bottom-6",
    },
    {
      value: "15000+",
      text: "innovation ventures moved through the Launchex pipeline",
      image:
        "https://images.higgs.ai/?default=1&output=webp&url=https%3A%2F%2Fd8j0ntlcm91z4.cloudfront.net%2Fuser_38xzZboKViGWJOttwIXH07lWA1P%2Fhf_20260514_154151_45c62c60-3bcc-4f21-8f9d-03722ebb5df8.png&w=1280&q=85",
      offset: true,
      clipPath:
        "polygon(0 14px, 4px 4px, 14px 0, calc(100% - 64px) 0, 100% 64px, 100% calc(100% - 14px), calc(100% - 4px) calc(100% - 4px), calc(100% - 14px) 100%, 64px 100%, 0 calc(100% - 64px))",
      textPlacement: "left-6 bottom-20",
    },
    {
      value: "120+",
      text: "accelerator sessions delivered by Launchex across Eastern Europe",
      image:
        "https://images.higgs.ai/?default=1&output=webp&url=https%3A%2F%2Fd8j0ntlcm91z4.cloudfront.net%2Fuser_38xzZboKViGWJOttwIXH07lWA1P%2Fhf_20260514_152238_24ec8db4-d728-4739-bb30-e985533e9637.png&w=1280&q=85",
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
              the founders
            </h2>
          </div>

          {/* Right side -- Description block */}
          <div className="flex flex-col max-w-xl text-[#154359]">
            <div className="text-[17px] sm:text-[18px] leading-[1.5]">
              <p>
                Launchex.Hub is a platform that is part of a portfolio of companies Launchex, for sourcing and showcasing groundbreaking innovations.
              </p>
              <p className="mt-4">
                Launchex.Hub's mission is to offer every local-language innovator the chance to reshape our world with their pioneering creation.
              </p>
            </div>

            {/* External link */}
            <a
              href="https://base.launchex.vc/"
              target="_blank"
              rel="noreferrer"
              className="group inline-flex items-center gap-4 mt-6 text-[14px] font-medium text-[#154359]"
            >
              <span>Launchex.Hub website</span>
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
