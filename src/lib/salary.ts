// Salary input parsing for Indian CTC fields. Everything is stored as LPA (lakhs per annum).
// Spec: docs/specs/salary-input.md

export type SalaryUnit = "lpa" | "year" | "month";

export const SALARY_UNITS: { value: SalaryUnit; label: string; short: string }[] = [
  { value: "lpa", label: "Lakhs per year (LPA)", short: "LPA" },
  { value: "year", label: "₹ per year", short: "₹/yr" },
  { value: "month", label: "₹ per month", short: "₹/mo" },
];

/** Hard cap shared with the backend (PreferencesPayload): ₹5 crore a year. */
export const MAX_LPA = 500;
/** Above this we still accept the value but ask the user to double-check it. */
export const CONFIRM_LPA = 100;

export interface SalaryParse {
  /** Annual CTC in LPA; null when the field is empty, NaN when the text can't be used. */
  lpa: number | null;
  error?: string;
  /** Non-blocking: how the input was read, or a "please double-check". */
  note?: string;
  warning?: string;
  /** The unit the text turned out to be in, when it differs from the selected one. */
  detectedUnit?: SalaryUnit;
}

const inr = new Intl.NumberFormat("en-IN", { maximumFractionDigits: 0 });

export function formatRupees(amount: number): string {
  return `₹${inr.format(Math.round(amount))}`;
}

export function formatLpa(lpa: number): string {
  return `${Number(lpa.toFixed(2))} LPA`;
}

/** "₹6,00,000 a year (6 LPA)": how a stored value reads back to the user. */
export function describeLpa(lpa: number): string {
  if (lpa >= 100) return `₹${Number((lpa / 100).toFixed(2))} crore a year (${formatLpa(lpa)})`;
  return `${formatRupees(lpa * 100_000)} a year (${formatLpa(lpa)})`;
}

const round2 = (n: number) => Math.round(n * 100) / 100;

// Words that pin the scale or period regardless of the selected unit
// (?<![a-z]) / (?![a-z]) instead of \b so "6L", "50k" and "1.2cr" (digit next to letter) match
const LAKH = /(?<![a-z])(lpa|lakhs?|lacs?|lk|l)(?![a-z])/;
const CRORE = /(?<![a-z])(crores?|cr)(?![a-z])/;
const THOUSAND = /(?<![a-z])(thousand|k)(?![a-z])/;
const MONTHLY = /(\/\s*m(on(th)?)?(?![a-z])|(?<![a-z])p\.?\s?m\.?(?![a-z])|per\s+month|monthly|a\s+month)/;
const YEARLY = /(\/\s*y(ea)?r(?![a-z])|(?<![a-z])p\.?\s?a\.?(?![a-z])|per\s+(year|annum)|yearly|annual(ly)?|a\s+year)/;

function toNumber(raw: string): number | null {
  const cleaned = raw.replace(/,/g, "").trim();
  if (!/^\d+(\.\d+)?$/.test(cleaned)) return null;
  return Number(cleaned);
}

/**
 * Read what someone typed into a CTC field.
 * Accepts "6", "6.5", "6 LPA", "6L", "6,00,000", "₹600000", "50k/month", "1.2 cr" and ranges "8-10".
 */
export function parseSalary(text: string, unit: SalaryUnit): SalaryParse {
  let s = text.trim().toLowerCase();
  if (!s) return { lpa: null };

  if (s.startsWith("-")) {
    return { lpa: NaN, error: "Salary can't be negative. Enter 0 if you have no current salary." };
  }
  s = s.replace(/₹|\brs\.?|\binr\b/g, " ").replace(/\s+/g, " ").trim();

  // Ranges: forms take one number, so use the lower end and say so
  let rangeNote: string | undefined;
  const range = s.match(/^(.+?)\s*(?:-|–|to)\s*(.+)$/);
  if (range && /\d/.test(range[1]) && /\d/.test(range[2])) {
    // "8-10 lpa": the unit written after the range applies to both ends
    const tail = range[2].replace(/[\d.,\s]/g, "");
    const lo = parseSalary(/[a-z]/.test(range[1]) ? range[1] : `${range[1]} ${tail}`, unit);
    const hi = parseSalary(range[2], unit);
    if (lo.error || hi.error || lo.lpa === null || hi.lpa === null) {
      return { lpa: NaN, error: "Enter one amount, e.g. 8 (LPA) or 8,00,000. Forms ask for a single number." };
    }
    const [a, b] = [Math.min(lo.lpa, hi.lpa), Math.max(lo.lpa, hi.lpa)];
    rangeNote = `Forms take one number, so we'll use the lower end of ${Number(a.toFixed(2))}–${formatLpa(b)}: ${formatLpa(a)}.`;
    return { ...lo, lpa: a, note: rangeNote };
  }

  const hasCrore = CRORE.test(s);
  const hasLakh = LAKH.test(s);
  const hasThousand = THOUSAND.test(s);
  const monthly = MONTHLY.test(s);
  const yearly = YEARLY.test(s);

  const numPart = s
    .replace(CRORE, " ")
    .replace(LAKH, " ")
    .replace(THOUSAND, " ")
    .replace(MONTHLY, " ")
    .replace(YEARLY, " ")
    .replace(/\s+/g, "")
    .replace(/(\d)\.(?=\D|$)/, "$1");
  const value = toNumber(numPart);
  if (value === null) {
    return { lpa: NaN, error: "Use numbers only, like 6, 6.5 or 6,00,000." };
  }

  let lpa: number;
  let note: string | undefined;
  let detectedUnit: SalaryUnit | undefined;

  if (hasCrore) {
    lpa = value * 100;
  } else if (hasLakh) {
    lpa = monthly ? value * 12 : value;
  } else {
    // Bare number or "k": decide rupees vs lakhs and month vs year
    const rupees = hasThousand ? value * 1000 : value;
    const period: SalaryUnit = monthly ? "month" : yearly ? "year" : unit;

    if (!hasThousand && period === "lpa" && value < 1000) {
      lpa = value;
    } else if (period === "month") {
      if (rupees < 1000) {
        return { lpa: NaN, error: "Enter the full monthly amount in rupees, e.g. 50,000 (not 50)." };
      }
      lpa = (rupees * 12) / 100_000;
      if (unit !== "month") detectedUnit = "month";
    } else if (period === "year" && !hasThousand && value < 1000) {
      // "6" with ₹/year selected is almost certainly lakhs, not six rupees
      lpa = value;
      detectedUnit = "lpa";
      note = `Read as ${formatLpa(value)}.`;
    } else {
      // A rupee amount. Typed under "LPA"? Convert rather than reject.
      lpa = rupees / 100_000;
      if (unit === "lpa") detectedUnit = "year";
      if (lpa < 1 && unit === "lpa" && !yearly) {
        // ₹50,000 "a year" is below any CTC; it's a monthly salary
        lpa = (rupees * 12) / 100_000;
        detectedUnit = "month";
        note = `${formatRupees(rupees)} looks like a monthly salary, so we read it as ${describeLpa(round2(lpa))}. If it's yearly, choose ₹ per year.`;
      }
    }
  }

  lpa = round2(lpa);
  if (lpa > MAX_LPA) {
    return {
      lpa: NaN,
      error: `${describeLpa(lpa)} is above our ₹5 crore limit. Check for extra zeros: for ₹12 lakh, type 12 (LPA) or 12,00,000.`,
    };
  }
  if (!note && detectedUnit && detectedUnit !== unit) {
    note = `Read as ${describeLpa(lpa)}.`;
  }
  const warning =
    lpa >= CONFIRM_LPA
      ? `That's ${describeLpa(lpa)}. Just checking: is that right?`
      : lpa > 0 && lpa < 1
        ? `That's only ${formatRupees(lpa * 100_000)} a year. If it's a monthly salary, choose ₹ per month.`
        : undefined;
  return { lpa, note: rangeNote ?? note, warning, detectedUnit };
}

/** Text to show for a stored LPA value in the chosen unit. */
export function lpaToText(lpa: number | null, unit: SalaryUnit): string {
  if (lpa === null || !Number.isFinite(lpa)) return "";
  if (unit === "lpa") return String(Number(lpa.toFixed(2)));
  const rupees = unit === "month" ? (lpa * 100_000) / 12 : lpa * 100_000;
  return inr.format(Math.round(rupees));
}

/** Cross-field checks: never block, only point out likely mistakes. */
export function salaryWarnings(v: {
  current_ctc_lpa: number | null;
  expected_ctc_lpa: number | null;
  min_salary_lpa: number;
}): { expected?: string; floor?: string } {
  const out: { expected?: string; floor?: string } = {};
  const cur = v.current_ctc_lpa;
  const exp = v.expected_ctc_lpa;
  const ok = (n: number | null): n is number => n !== null && Number.isFinite(n);
  if (ok(cur) && ok(exp) && cur > 0 && exp < cur) {
    out.expected = `Expected (${formatLpa(exp)}) is lower than current (${formatLpa(cur)}). Fine if you mean it, e.g. for a career switch.`;
  }
  if (ok(exp) && Number.isFinite(v.min_salary_lpa) && v.min_salary_lpa > exp && exp > 0) {
    out.floor = `This hides jobs paying your expected ${formatLpa(exp)}. Usually this is at or below your expected CTC.`;
  }
  return out;
}

/** A field whose text couldn't be used is stored as NaN so the step can't be submitted. */
export const isSalaryValid = (n: number | null) => n === null || Number.isFinite(n);
