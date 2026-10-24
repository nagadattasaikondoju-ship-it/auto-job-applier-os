"use client";

import React from "react";
import { Navbar } from "@/components/Navbar";
import { HeroSection } from "@/components/HeroSection";
import { ProblemSection } from "@/components/ProblemSection";
import { CapabilitiesSection } from "@/components/CapabilitiesSection";
import { HowItWorksBento } from "@/components/HowItWorksBento";
import { AboutFoundersSection } from "@/components/AboutFoundersSection";
import { PricingSection } from "@/components/PricingSection";
import { ZentradeFaqSection } from "@/components/ZentradeFaqSection";
import { DriftbarFooter } from "@/components/DriftbarFooter";
import { SmoothScroll } from "@/components/SmoothScroll";

export default function Home() {
  return (
    <SmoothScroll>
      <div className="min-h-screen bg-background text-foreground flex flex-col selection:bg-accent/20 selection:text-accent">
        <Navbar />
        <main className="flex-1 flex flex-col">
          {/* Hero Section */}
          <HeroSection />

          {/* Problem & Trust Strip Section */}
          <ProblemSection />

          {/* Capabilities Amber Glow Section */}
          <CapabilitiesSection />

          {/* How It Works & Bento Grid Features */}
          <HowItWorksBento />

          {/* About The Founders Section */}
          <AboutFoundersSection />

          {/* Pricing Section */}
          <PricingSection />

          {/* FAQ Section */}
          <ZentradeFaqSection />
        </main>

        {/* Driftbar Meadow Footer Section */}
        <DriftbarFooter />
      </div>
    </SmoothScroll>
  );
}
