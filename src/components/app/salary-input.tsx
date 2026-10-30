"use client";

import { AlertTriangle } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { cn } from "@/lib/utils";
import { SALARY_UNITS, describeLpa, lpaToText, parseSalary, type SalaryUnit } from "@/lib/salary";
import { Field, Input, Select } from "./ui";

const PLACEHOLDER: Record<SalaryUnit, string> = { lpa: "e.g. 6.5", year: "e.g. 6,50,000", month: "e.g. 54,000" };

/**
 * CTC input that accepts lakhs, yearly or monthly rupees ("6", "6,00,000", "50k/month", "8-10")
 * and always reports annual LPA. Text it can't use is reported as NaN so the form can't submit it.
 * Spec: docs/specs/salary-input.md
 */
export function SalaryInput({
  id,
  label,
  hint,
  value,
  onChange,
  disabled,
  crossFieldWarning,
}: {
  id: string;
  label: string;
  hint?: string;
  value: number | null;
  onChange: (lpa: number | null) => void;
  disabled?: boolean;
  /** A check against the other salary fields (never blocks saving). */
  crossFieldWarning?: string;
}) {
  const [unit, setUnit] = useState<SalaryUnit>("lpa");
  const [text, setText] = useState(() => lpaToText(value, "lpa"));
  // The last value we reported; anything else arriving in `value` came from outside (loaded data, a reset)
  const reported = useRef<number | null>(value);

  useEffect(() => {
    const same = Object.is(value, reported.current) || (value === null && reported.current === null);
    if (!same) {
      reported.current = value;
      setText(lpaToText(value, unit));
    }
  }, [value, unit]);

  const parsed = parseSalary(text, unit);

  const report = (lpa: number | null) => {
    reported.current = lpa;
    onChange(lpa);
  };

  const onText = (next: string) => {
    setText(next);
    report(parseSalary(next, unit).lpa);
  };

  const onUnit = (next: SalaryUnit) => {
    // Keep the same salary, shown in the new unit; unusable text is re-read in the new unit instead
    if (parsed.lpa !== null && Number.isFinite(parsed.lpa)) {
      setText(lpaToText(parsed.lpa, next));
    } else {
      report(parseSalary(text, next).lpa);
    }
    setUnit(next);
  };

  const onBlur = () => {
    // Settle on the unit we detected ("150000" typed under LPA becomes ₹1,50,000 per year)
    if (parsed.detectedUnit && parsed.lpa !== null && Number.isFinite(parsed.lpa) && !/-|–|to/.test(text)) {
      setUnit(parsed.detectedUnit);
      setText(lpaToText(parsed.lpa, parsed.detectedUnit));
    } else if (parsed.lpa !== null && Number.isFinite(parsed.lpa) && unit !== "lpa") {
      setText(lpaToText(parsed.lpa, unit)); // tidy commas: 600000 -> 6,00,000
    }
  };

  const valid = parsed.lpa !== null && Number.isFinite(parsed.lpa);
  const describedBy = `${id}-read`;
  const warning = parsed.warning ?? crossFieldWarning;

  return (
    <Field label={label} htmlFor={id} error={parsed.error}>
      <div className="flex gap-2">
        <Input
          id={id}
          type="text"
          inputMode="decimal"
          autoComplete="off"
          placeholder={PLACEHOLDER[unit]}
          value={text}
          disabled={disabled}
          onChange={(e) => onText(e.target.value)}
          onBlur={onBlur}
          aria-invalid={Boolean(parsed.error) || undefined}
          aria-describedby={describedBy}
          className={cn("min-w-0 flex-1", parsed.error && "border-app-danger")}
        />
        <Select
          aria-label={`${label} unit`}
          value={unit}
          disabled={disabled}
          onChange={(e) => onUnit(e.target.value as SalaryUnit)}
          className="w-28 shrink-0"
        >
          {SALARY_UNITS.map((u) => (
            <option key={u.value} value={u.value} title={u.label}>
              {u.short}
            </option>
          ))}
        </Select>
      </div>
      <div id={describedBy} aria-live="polite" className="flex flex-col gap-1 text-xs">
        {valid && !parsed.error && (
          <p className="text-app-muted">
            {parsed.lpa === 0 ? "No current salary (₹0)" : `= ${describeLpa(parsed.lpa as number)}`}
          </p>
        )}
        {parsed.note && <p className="text-app-muted">{parsed.note}</p>}
        {warning && !parsed.error && (
          <p className="flex items-start gap-1.5 text-app-ink">
            <AlertTriangle className="size-3.5 mt-0.5 shrink-0 text-app-danger" aria-hidden="true" />
            {warning}
          </p>
        )}
        {!text && hint && <p className="text-app-muted">{hint}</p>}
      </div>
    </Field>
  );
}
