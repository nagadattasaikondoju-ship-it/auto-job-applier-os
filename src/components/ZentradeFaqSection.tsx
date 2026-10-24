"use client";

import React, { useState, useMemo } from "react";
import { Search, ChevronDown, CircleDollarSign, BarChart2, Target, TrendingUp } from "lucide-react";
import { cn } from "@/lib/utils";
import { landingContent, FaqItem } from "@/content/landing";

export function ZentradeFaqSection() {
  const [searchQuery, setSearchQuery] = useState("");
  const [openId, setOpenId] = useState<number | null>(0);
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);

  const categories = [
    {
      title: "Platform",
      count: "12 Articles",
      icon: <CircleDollarSign className="w-6 h-6 text-white" aria-hidden="true" />,
    },
    {
      title: "Resume Tailoring",
      count: "18 Articles",
      icon: <BarChart2 className="w-6 h-6 text-white" aria-hidden="true" />,
    },
    {
      title: "Pricing & Plans",
      count: "8 Articles",
      icon: <Target className="w-6 h-6 text-white" aria-hidden="true" />,
    },
    {
      title: "Career Growth",
      count: "24 Articles",
      icon: <TrendingUp className="w-6 h-6 text-white" aria-hidden="true" />,
    },
  ];

  const faqs = landingContent.faqs;

  const filteredFaqs = useMemo(() => {
    return faqs.filter((faq) => {
      const matchesSearch =
        faq.question.toLowerCase().includes(searchQuery.toLowerCase()) ||
        faq.answer.toLowerCase().includes(searchQuery.toLowerCase());
      const matchesCategory = selectedCategory
        ? faq.category === selectedCategory
        : true;
      return matchesSearch && matchesCategory;
    });
  }, [faqs, searchQuery, selectedCategory]);

  const toggleAccordion = (idx: number) => {
    setOpenId((prev) => (prev === idx ? null : idx));
  };

  return (
    <section
      id="faq"
      aria-labelledby="faq-heading"
      className="relative w-full bg-[#090909] text-white py-24 sm:py-32 px-4 sm:px-6 overflow-hidden border-t border-[#2F2F2F]"
    >
      {/* Central radial green glow */}
      <div
        className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[600px] pointer-events-none opacity-50"
        aria-hidden="true"
        style={{
          background: "radial-gradient(circle at 50% 20%, #1D2E13 0%, #090909 70%)",
        }}
      />

      {/* Stepped green light bars at top edge */}
      <div
        className="absolute top-0 inset-x-0 h-48 flex justify-between pointer-events-none opacity-30 px-4 sm:px-12"
        aria-hidden="true"
      >
        <div className="flex gap-3 sm:gap-6 items-start">
          <div className="w-6 sm:w-12 h-44 bg-gradient-to-b from-[#2A4B1B] to-transparent rounded-b-lg" />
          <div className="w-6 sm:w-12 h-36 bg-gradient-to-b from-[#2A4B1B] to-transparent rounded-b-lg" />
          <div className="w-6 sm:w-12 h-28 bg-gradient-to-b from-[#2A4B1B] to-transparent rounded-b-lg" />
          <div className="w-6 sm:w-12 h-20 bg-gradient-to-b from-[#2A4B1B] to-transparent rounded-b-lg" />
          <div className="w-6 sm:w-12 h-14 bg-gradient-to-b from-[#1D2F14] to-transparent rounded-b-lg" />
        </div>
        <div className="flex gap-3 sm:gap-6 items-start flex-row-reverse">
          <div className="w-6 sm:w-12 h-44 bg-gradient-to-b from-[#2A4B1B] to-transparent rounded-b-lg" />
          <div className="w-6 sm:w-12 h-36 bg-gradient-to-b from-[#2A4B1B] to-transparent rounded-b-lg" />
          <div className="w-6 sm:w-12 h-28 bg-gradient-to-b from-[#2A4B1B] to-transparent rounded-b-lg" />
          <div className="w-6 sm:w-12 h-20 bg-gradient-to-b from-[#2A4B1B] to-transparent rounded-b-lg" />
          <div className="w-6 sm:w-12 h-14 bg-gradient-to-b from-[#1D2F14] to-transparent rounded-b-lg" />
        </div>
      </div>

      <div className="relative z-10 max-w-4xl mx-auto">
        {/* Hero Block */}
        <div className="flex flex-col items-center text-center">
          <div className="px-5 py-2 rounded-full border border-[#83F34D]/30 bg-[#83F34D]/10 backdrop-blur-md mb-6 shadow-sm">
            <span className="text-sm font-semibold text-[#83F34D] tracking-wider font-figtree">
              FAQ
            </span>
          </div>

          <h2
            id="faq-heading"
            className="text-4xl sm:text-5xl md:text-6xl font-extrabold font-figtree tracking-tight text-white leading-tight"
          >
            Frequently asked questions about Applyon
          </h2>

          <p className="mt-4 text-base sm:text-lg text-white/80 max-w-xl font-figtree leading-relaxed">
            Find answers to the most common questions about Applyon’s AI job copilot, ATS resume tailoring, application autofill, and pricing.
          </p>

          <a
            href="#hero"
            className="mt-7 inline-block px-8 py-3.5 rounded-xl bg-white text-black font-semibold text-sm hover:scale-[1.02] transition-transform shadow-lg cursor-pointer font-figtree"
          >
            Join Our Community
          </a>
        </div>

        {/* Search Bar */}
        <div className="mt-14 relative max-w-2xl mx-auto">
          <label htmlFor="faq-search-input" className="sr-only">
            Search frequently asked questions
          </label>
          <div className="relative flex items-center rounded-full bg-white/[0.08] border border-white/15 px-5 py-3.5 backdrop-blur-xl focus-within:border-[#83F34D] focus-within:ring-2 focus-within:ring-[#83F34D]/40 transition-all shadow-md">
            <Search className="w-5 h-5 text-white/60 mr-3 shrink-0" aria-hidden="true" />
            <input
              id="faq-search-input"
              name="faq-search"
              type="text"
              autoComplete="off"
              suppressHydrationWarning
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search for your queries"
              className="w-full bg-transparent text-white placeholder:text-white/40 focus:outline-hidden font-lexend text-sm sm:text-base font-light"
            />
            {searchQuery && (
              <button
                type="button"
                onClick={() => setSearchQuery("")}
                className="text-xs text-white/60 hover:text-white ml-2 cursor-pointer"
              >
                Clear
              </button>
            )}
          </div>
        </div>

        {/* 4 Pill-shaped Category Cards */}
        <div className="mt-12 grid grid-cols-1 sm:grid-cols-2 gap-5">
          {categories.map((cat) => {
            const isSelected = selectedCategory === cat.title;
            return (
              <button
                key={cat.title}
                type="button"
                onClick={() => setSelectedCategory(isSelected ? null : cat.title)}
                className={cn(
                  "p-5 rounded-full bg-[#1B1B1B] border transition-all duration-200 cursor-pointer flex items-center gap-4 text-left hover:border-[#83F34D]/70",
                  isSelected
                    ? "border-[#83F34D] bg-[#222222] shadow-[0_0_20px_rgba(131,243,77,0.15)]"
                    : "border-transparent"
                )}
              >
                <div className="w-14 h-14 rounded-full bg-[#232323] flex items-center justify-center shrink-0 shadow-inner">
                  {cat.icon}
                </div>
                <div>
                  <h3 className="text-base sm:text-lg font-medium text-white font-figtree">
                    {cat.title}
                  </h3>
                  <p className="text-xs text-white/50 font-figtree mt-0.5">
                    {cat.count}
                  </p>
                </div>
              </button>
            );
          })}
        </div>

        {/* Accordion Rows: Answers are always rendered in the DOM for search bots */}
        <div className="mt-14 space-y-4">
          {filteredFaqs.length > 0 ? (
            filteredFaqs.map((item, idx) => {
              const isOpen = openId === idx;
              return (
                <div
                  key={item.question}
                  className="rounded-2xl bg-[#131313] border border-[#2F2F2F]/60 overflow-hidden transition-all duration-200"
                >
                  <button
                    type="button"
                    onClick={() => toggleAccordion(idx)}
                    aria-expanded={isOpen}
                    aria-controls={`faq-answer-${idx}`}
                    className="w-full p-5 sm:p-6 text-left flex items-center justify-between gap-4 cursor-pointer hover:bg-white/[0.02]"
                  >
                    <h3 className="text-base sm:text-xl font-medium font-figtree text-white/95">
                      {item.question}
                    </h3>
                    <div
                      className={cn(
                        "w-8 h-8 rounded-full border border-white/20 flex items-center justify-center shrink-0 transition-transform duration-300",
                        isOpen
                          ? "rotate-180 bg-[#83F34D]/10 border-[#83F34D]/50 text-[#83F34D]"
                          : "text-white/60"
                      )}
                    >
                      <ChevronDown className="w-4 h-4" aria-hidden="true" />
                    </div>
                  </button>

                  {/* DOM-persisted Answer Container for Crawlers */}
                  <div
                    id={`faq-answer-${idx}`}
                    className={cn(
                      "grid transition-all duration-300 ease-out",
                      isOpen ? "grid-rows-[1fr] opacity-100" : "grid-rows-[0fr] opacity-0"
                    )}
                  >
                    <div className="overflow-hidden">
                      <div className="px-5 sm:px-6 pb-6 pt-1 text-sm sm:text-base text-white/80 font-figtree leading-relaxed border-t border-[#2F2F2F]/40">
                        <p>{item.answer}</p>
                      </div>
                    </div>
                  </div>
                </div>
              );
            })
          ) : (
            <div className="text-center py-12 text-white/50 font-figtree">
              No questions match your search.
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
