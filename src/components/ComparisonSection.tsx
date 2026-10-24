"use client";

import React from "react";
import { Check, X, Minus } from "lucide-react";
import { landingContent } from "@/content/landing";

export function ComparisonSection() {
  const comparison = landingContent.comparison;

  const renderBadge = (item: { value: string; label: string }) => {
    if (item.label === "Yes") {
      return (
        <div className="flex items-center gap-1.5 text-emerald-600 dark:text-emerald-400 font-medium">
          <span className="w-5 h-5 rounded-full bg-emerald-500/10 flex items-center justify-center shrink-0">
            <Check className="w-3.5 h-3.5" aria-hidden="true" />
          </span>
          <span className="sr-only">Yes: </span>
          <span>{item.value}</span>
        </div>
      );
    }
    if (item.label === "No") {
      return (
        <div className="flex items-center gap-1.5 text-rose-500 font-medium">
          <span className="w-5 h-5 rounded-full bg-rose-500/10 flex items-center justify-center shrink-0">
            <X className="w-3.5 h-3.5" aria-hidden="true" />
          </span>
          <span className="sr-only">No: </span>
          <span>{item.value}</span>
        </div>
      );
    }
    return (
      <div className="flex items-center gap-1.5 text-amber-500 font-medium">
        <span className="w-5 h-5 rounded-full bg-amber-500/10 flex items-center justify-center shrink-0">
          <Minus className="w-3.5 h-3.5" aria-hidden="true" />
        </span>
        <span className="sr-only">Partial: </span>
        <span>{item.value}</span>
      </div>
    );
  };

  return (
    <section
      id="comparison"
      aria-labelledby="comparison-heading"
      className="relative w-full bg-background py-20 sm:py-28 border-t border-border/40 overflow-hidden"
    >
      <div className="max-w-6xl mx-auto px-4 sm:px-6">
        <div className="text-center max-w-2xl mx-auto mb-16">
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-mono bg-accent/10 text-accent border border-accent/20 mb-4">
            Market Comparison
          </span>
          <h2
            id="comparison-heading"
            className="text-3xl sm:text-4xl md:text-5xl font-display tracking-tight text-foreground"
          >
            {comparison.heading}
          </h2>
          <p className="mt-4 text-sm sm:text-base text-muted-foreground font-body">
            Why intelligent assistance outperforms both exhausting manual applications and spam bots that get rejected by recruiters.
          </p>
        </div>

        {/* Semantic Accessible Table */}
        <div className="overflow-x-auto rounded-2xl border border-border/80 bg-secondary/20 backdrop-blur-sm shadow-xs">
          <table className="w-full text-left border-collapse min-w-[620px]">
            <caption className="sr-only">{comparison.caption}</caption>
            <thead>
              <tr className="border-b border-border/60 text-xs sm:text-sm font-body">
                <th scope="col" className="p-4 sm:p-5 font-semibold text-muted-foreground w-1/4">
                  Feature / Criterion
                </th>
                <th scope="col" className="p-4 sm:p-5 font-semibold text-muted-foreground w-1/4">
                  Manual Applying
                </th>
                <th scope="col" className="p-4 sm:p-5 font-semibold text-muted-foreground w-1/4">
                  Auto-Apply Bots
                </th>
                <th
                  scope="col"
                  className="p-4 sm:p-5 font-bold text-accent bg-accent/5 border-l border-r border-accent/20 w-1/4"
                >
                  <div className="flex items-center gap-1.5">
                    <span>✦ Applyon Copilot</span>
                  </div>
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/40 text-xs sm:text-sm font-body">
              {comparison.rows.map((row) => (
                <tr key={row.criterion} className="hover:bg-secondary/40 transition-colors">
                  <th scope="row" className="p-4 sm:p-5 font-semibold text-foreground">
                    {row.criterion}
                  </th>
                  <td className="p-4 sm:p-5 text-muted-foreground">
                    {renderBadge(row.manual)}
                  </td>
                  <td className="p-4 sm:p-5 text-muted-foreground">
                    {renderBadge(row.bots)}
                  </td>
                  <td className="p-4 sm:p-5 bg-accent/[0.04] border-l border-r border-accent/20 font-medium text-foreground">
                    {renderBadge(row.applyon)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}
