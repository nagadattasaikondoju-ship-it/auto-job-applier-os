"use client";

import React from "react";
import { Navbar } from "@/components/Navbar";
import { HeroSection } from "@/components/HeroSection";
import { ProblemSection } from "@/components/ProblemSection";
import { CapabilitiesSection } from "@/components/CapabilitiesSection";
import { HowItWorksBento } from "@/components/HowItWorksBento";
import { AboutFoundersSection } from "@/components/AboutFoundersSection";
import { ComparisonSection } from "@/components/ComparisonSection";
import { TestimonialsSection } from "@/components/TestimonialsSection";
import { PricingSection } from "@/components/PricingSection";
import { ZentradeFaqSection } from "@/components/ZentradeFaqSection";
import { FinalCtaSection } from "@/components/FinalCtaSection";
import { DriftbarFooter } from "@/components/DriftbarFooter";
import { SmoothScroll } from "@/components/SmoothScroll";

export default function Home() {
  return (
    <SmoothScroll>
      <div className="min-h-screen bg-background text-foreground flex flex-col selection:bg-accent/20 selection:text-accent">
        <Navbar />
        <main className="flex-1 flex flex-col">
          {/* Section 2: Hero */}
          <HeroSection />

          {/* Section 3 & 4: Trust Companies Marquee & Problem Analysis */}
          <ProblemSection />

          {/* Capabilities Section */}
          <CapabilitiesSection />

          {/* Section 5, 6 & 7: How It Works, Features Bento Grid, Safety Promise */}
          <HowItWorksBento />

          {/* About Applyon */}
          <AboutFoundersSection />

          {/* Section 8: Comparison Table */}
          <ComparisonSection />

          {/* Section 9: Testimonials Marquee */}
          <TestimonialsSection />

          {/* Section 10: Pricing Plans */}
          <PricingSection />

          {/* Section 11: Frequently Asked Questions */}
          <ZentradeFaqSection />

          {/* Section 12: Final CTA Banner */}
          <FinalCtaSection />
        </main>

        {/* Section 13: Footer */}
        <DriftbarFooter />
      </div>
    </SmoothScroll>
  );
}
