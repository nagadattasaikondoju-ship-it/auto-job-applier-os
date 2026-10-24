"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { Sparkles, Menu, X, ArrowRight } from "lucide-react";
import { cn } from "@/lib/utils";

interface NavbarProps {
  onOpenWaitlist?: () => void;
}

export function Navbar({ onOpenWaitlist }: NavbarProps) {
  const [scrolled, setScrolled] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 20);
    };
    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  const navLinks = [
    { label: "Features", href: "#features" },
    { label: "How it works", href: "#how-it-works" },
    { label: "Capabilities", href: "#capabilities" },
    { label: "About", href: "#about" },
    { label: "Pricing", href: "#pricing" },
    { label: "FAQ", href: "#faq" },
  ];

  return (
    <header
      className={cn(
        "fixed top-0 left-0 right-0 z-50 transition-all duration-300 font-body",
        scrolled
          ? "bg-white/85 dark:bg-black/85 backdrop-blur-md shadow-xs border-b border-border/40 py-3"
          : "bg-transparent py-5"
      )}
    >
      <div className="max-w-7xl mx-auto px-6 md:px-12 lg:px-20 flex items-center justify-between">
        {/* Left: Brand Logo linking to "/" with accessible name */}
        <Link
          href="/"
          aria-label="Applyon home"
          className="flex items-center gap-2 group text-foreground"
        >
          <div
            className="w-8 h-8 rounded-lg bg-foreground text-background flex items-center justify-center font-bold text-sm shadow-xs transition-transform group-hover:scale-105"
            aria-hidden="true"
          >
            ✦
          </div>
          <span className="text-xl font-semibold tracking-tight text-foreground">
            Applyon
          </span>
          <span className="hidden sm:inline-block text-[11px] font-mono px-2 py-0.5 rounded-full bg-secondary text-muted-foreground border border-border">
            Copilot OS
          </span>
        </Link>

        {/* Center: Desktop Nav Links with real crawlable anchors */}
        <nav aria-label="Primary" className="hidden md:flex items-center gap-8">
          {navLinks.map((link) => (
            <a
              key={link.label}
              href={link.href}
              className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
            >
              {link.label}
            </a>
          ))}
        </nav>

        {/* Right: CTA Button */}
        <div className="hidden sm:flex items-center gap-3">
          <a
            href="#hero"
            onClick={(e) => {
              if (onOpenWaitlist) {
                e.preventDefault();
                onOpenWaitlist();
              }
            }}
            className="rounded-full px-5 py-2 text-sm font-medium bg-foreground text-background hover:opacity-90 transition-all shadow-xs flex items-center gap-2 group cursor-pointer"
          >
            <span>Join waitlist</span>
            <ArrowRight className="w-3.5 h-3.5 transition-transform group-hover:translate-x-0.5" aria-hidden="true" />
          </a>
        </div>

        {/* Mobile menu trigger */}
        <button
          type="button"
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          className="md:hidden p-2 rounded-lg text-foreground hover:bg-secondary transition-colors"
          aria-label={mobileMenuOpen ? "Close navigation menu" : "Open navigation menu"}
          aria-expanded={mobileMenuOpen}
        >
          {mobileMenuOpen ? (
            <X className="w-6 h-6" aria-hidden="true" />
          ) : (
            <Menu className="w-6 h-6" aria-hidden="true" />
          )}
        </button>
      </div>

      {/* Mobile Drawer Menu */}
      {mobileMenuOpen && (
        <nav
          aria-label="Mobile Navigation"
          className="md:hidden border-b border-border bg-background/95 backdrop-blur-xl px-6 py-6 flex flex-col gap-4 animate-in fade-in slide-in-from-top-4"
        >
          {navLinks.map((link) => (
            <a
              key={link.label}
              href={link.href}
              onClick={() => setMobileMenuOpen(false)}
              className="text-base font-medium text-foreground/80 hover:text-foreground py-2 border-b border-border/30"
            >
              {link.label}
            </a>
          ))}
          <a
            href="#hero"
            onClick={() => setMobileMenuOpen(false)}
            className="w-full rounded-full py-3 text-sm font-medium bg-foreground text-background hover:opacity-90 transition-all text-center mt-2 flex items-center justify-center gap-2"
          >
            <span>Join waitlist</span>
            <Sparkles className="w-4 h-4 text-amber-400" aria-hidden="true" />
          </a>
        </nav>
      )}
    </header>
  );
}
