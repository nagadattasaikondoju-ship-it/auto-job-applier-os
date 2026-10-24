"use client";

import React, { useState, useMemo } from "react";
import { Search, ChevronDown, CircleDollarSign, BarChart2, Target, TrendingUp } from "lucide-react";
import { cn } from "@/lib/utils";

interface FaqItem {
  id: number;
  question: string;
  answer: string;
  category: string;
}

const initialFaqs: FaqItem[] = [
  {
    id: 1,
    question: "What assets can I trade on ZENTRADE?",
    answer:
      "Forex majors and minors, indices, commodities such as gold and oil, and popular cryptocurrencies, all from one account, with live spread, leverage and hours shown before each order.",
    category: "About Zen Trade",
  },
  {
    id: 2,
    question: "What is ZENTRADE?",
    answer:
      "An online trading platform with access to global markets through a fast, secure, easy-to-use interface and dedicated support.",
    category: "About Zen Trade",
  },
  {
    id: 3,
    question: "How do I open an account?",
    answer:
      "Sign up, complete the form, verify your identity, then make your first deposit.",
    category: "Trading Rules & Guidelines",
  },
  {
    id: 4,
    question: "Which deposit and withdrawal methods are available?",
    answer:
      "The secure methods listed in your client area, varying by region.",
    category: "Zen Trade Challenge Insight",
  },
  {
    id: 5,
    question: "What are the trading conditions?",
    answer:
      "Spreads, leverage and fees vary by account type and instrument; compare them on the Accounts page.",
    category: "Zen Trade Features",
  },
];

export function ZentradeFaqSection() {
  const [searchQuery, setSearchQuery] = useState("");
  const [openId, setOpenId] = useState<number | null>(1);
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);

  const categories = [
    {
      title: "About Zen Trade",
      count: "62 Articles",
      icon: <CircleDollarSign className="w-6 h-6 text-white" />,
    },
    {
      title: "Trading Rules & Guidelines",
      count: "62 Articles",
      icon: <BarChart2 className="w-6 h-6 text-white" />,
    },
    {
      title: "Zen Trade Challenge Insight",
      count: "62 Articles",
      icon: <Target className="w-6 h-6 text-white" />,
    },
    {
      title: "Zen Trade Features",
      count: "62 Articles",
      icon: <TrendingUp className="w-6 h-6 text-white" />,
    },
  ];

  const filteredFaqs = useMemo(() => {
    return initialFaqs.filter((faq) => {
      const matchesSearch =
        faq.question.toLowerCase().includes(searchQuery.toLowerCase()) ||
        faq.answer.toLowerCase().includes(searchQuery.toLowerCase());
      const matchesCategory = selectedCategory
        ? faq.category === selectedCategory
        : true;
      return matchesSearch && matchesCategory;
    });
  }, [searchQuery, selectedCategory]);

  const toggleAccordion = (id: number) => {
    setOpenId((prev) => (prev === id ? null : id));
  };

  return (
    <section
      id="faq"
      className="relative w-full bg-[#090909] text-white py-24 sm:py-32 px-4 sm:px-6 overflow-hidden border-t border-[#2F2F2F]"
    >
      {/* Central radial green glow */}
      <div
        className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[600px] pointer-events-none opacity-50"
        style={{
          background: "radial-gradient(circle at 50% 20%, #1D2E13 0%, #090909 70%)",
        }}
      />

      {/* Stepped green light bars at the top edge */}
      <div className="absolute top-0 inset-x-0 h-48 flex justify-between pointer-events-none opacity-30 px-4 sm:px-12">
        {/* Left stepped bars */}
        <div className="flex gap-3 sm:gap-6 items-start">
          <div className="w-6 sm:w-12 h-44 bg-gradient-to-b from-[#2A4B1B] to-transparent rounded-b-lg" />
          <div className="w-6 sm:w-12 h-36 bg-gradient-to-b from-[#2A4B1B] to-transparent rounded-b-lg" />
          <div className="w-6 sm:w-12 h-28 bg-gradient-to-b from-[#2A4B1B] to-transparent rounded-b-lg" />
          <div className="w-6 sm:w-12 h-20 bg-gradient-to-b from-[#2A4B1B] to-transparent rounded-b-lg" />
          <div className="w-6 sm:w-12 h-14 bg-gradient-to-b from-[#1D2F14] to-transparent rounded-b-lg" />
        </div>
        {/* Right stepped bars */}
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
          {/* Tag: FAQ */}
          <div className="px-5 py-2 rounded-full border border-[#83F34D]/30 bg-[#83F34D]/10 backdrop-blur-md mb-6 shadow-sm">
            <span className="text-sm font-semibold text-[#83F34D] tracking-wider font-figtree">
              FAQ
            </span>
          </div>

          {/* Headline */}
          <h2 className="text-4xl sm:text-5xl md:text-6xl font-extrabold font-figtree tracking-tight text-white leading-tight">
            Frequently Asked Questions
          </h2>

          {/* Lede */}
          <p className="mt-4 text-base sm:text-lg text-white/80 max-w-xl font-figtree leading-relaxed">
            Find answers to the most common questions about ZENTRADE’s platforms, accounts, deposits, trading conditions, and more.
          </p>

          {/* White Button */}
          <button
            type="button"
            onClick={() => {
              document.getElementById("hero-waitlist")?.scrollIntoView({ behavior: "smooth" });
            }}
            className="mt-7 px-8 py-3.5 rounded-xl bg-white text-black font-semibold text-sm hover:scale-[1.02] transition-transform shadow-lg cursor-pointer font-figtree"
          >
            Join Our Community
          </button>
        </div>

        {/* Search Bar */}
        <div className="mt-14 relative max-w-2xl mx-auto">
          <div className="relative flex items-center rounded-full bg-white/[0.08] border border-white/15 px-5 py-3.5 backdrop-blur-xl focus-within:border-[#83F34D] focus-within:ring-2 focus-within:ring-[#83F34D]/40 transition-all shadow-md">
            <Search className="w-5 h-5 text-white/60 mr-3 shrink-0" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search for your queries"
              className="w-full bg-transparent text-white placeholder:text-white/40 focus:outline-hidden font-lexend text-sm sm:text-base font-light"
            />
            {searchQuery && (
              <button
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
              <div
                key={cat.title}
                onClick={() =>
                  setSelectedCategory(isSelected ? null : cat.title)
                }
                className={cn(
                  "p-5 rounded-full bg-[#1B1B1B] border transition-all duration-200 cursor-pointer flex items-center gap-4 hover:border-[#83F34D]/70",
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
              </div>
            );
          })}
        </div>

        {/* Accordion Rows */}
        <div className="mt-14 space-y-4">
          {filteredFaqs.length > 0 ? (
            filteredFaqs.map((item) => {
              const isOpen = openId === item.id;
              return (
                <div
                  key={item.id}
                  className="rounded-2xl bg-[#131313] border border-[#2F2F2F]/60 overflow-hidden transition-all duration-200"
                >
                  <button
                    type="button"
                    onClick={() => toggleAccordion(item.id)}
                    className="w-full p-5 sm:p-6 text-left flex items-center justify-between gap-4 cursor-pointer hover:bg-white/[0.02]"
                  >
                    <span className="text-base sm:text-xl font-medium font-figtree text-white/95">
                      {item.question}
                    </span>
                    <div
                      className={cn(
                        "w-8 h-8 rounded-full border border-white/20 flex items-center justify-center shrink-0 transition-transform duration-300",
                        isOpen ? "rotate-180 bg-[#83F34D]/10 border-[#83F34D]/50 text-[#83F34D]" : "text-white/60"
                      )}
                    >
                      <ChevronDown className="w-4 h-4" />
                    </div>
                  </button>

                  {/* Smooth Accordion Body */}
                  {isOpen && (
                    <div className="px-5 sm:px-6 pb-6 pt-1 text-sm sm:text-base text-white/80 font-figtree leading-relaxed border-t border-[#2F2F2F]/40 animate-in fade-in duration-200">
                      <p>{item.answer}</p>
                    </div>
                  )}
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
