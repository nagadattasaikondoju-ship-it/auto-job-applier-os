# Spec: Salary (CTC) inputs in onboarding and Profile

**Status:** Implemented. Code: `src/lib/salary.ts` (parsing), `src/components/app/salary-input.tsx` (field), `apps/api/routers/preferences.py` (server rules).

## Problem

The salary step had three plain number boxes labelled "(LPA)". People type salaries the way they think of them: `150000`, `6,00,000`, `50k a month`. A value like `600000` broke the backend's 500 LPA limit. The whole onboarding save then failed with "Invalid request parameters", and nothing said which field was wrong. Monthly figures were silently read as yearly. A blank expected CTC had no explanation. Salary answers given before a resume was uploaded were dropped.

## Goals

1. Accept any reasonable way of writing an Indian salary, and store it as **annual LPA** (lakhs per annum).
2. Always show what we understood, before the user moves on.
3. Block only input that can't be used. Everything else gets a fix-it note, never a dead end.
4. Name the field and say how to fix it whenever something is wrong.

## Field design

| Field | Label | Required | Placeholder | Helper text |
|---|---|---|---|---|
| Current CTC | `Current CTC` | No | `e.g. 6.5` | Shows how the value was read, e.g. `= ₹6,50,000 a year (6.5 LPA)` |
| Fresher toggle | `I don't have a current salary (fresher or between jobs)` | No | — | Sets current CTC to 0 and disables the box |
| Expected CTC | `Expected CTC` | No | `e.g. 6.5` | When empty: "Optional. If you leave it blank, we'll ask you whenever an application form needs it." |
| Pay floor | `Hide jobs that pay less than` | No | `e.g. 6.5` | When empty: "Optional. Jobs without a listed salary are always shown." |

- **Step description:** "Indian application forms ask for current and expected CTC (yearly, before tax). Type it the way you know it: 6.5 LPA, 6,50,000 a year or 54,000 a month."
- **Unit selector** beside each box: `LPA` (default), `₹/yr`, `₹/mo`. Switching units converts the shown number and keeps the same salary.
- **Text input** (`inputMode="decimal"`) rather than `type="number"`, so commas, ₹ and words like "lakh" can be typed.
- **Live readback** under each box, updated as the user types and announced to screen readers (`aria-live="polite"`).

## Parsing and normalization (client, `parseSalary`)

Everything is stored as annual LPA, rounded to 2 decimals.

| Input | Unit selected | Stored | What the user sees |
|---|---|---|---|
| `6`, `6.5`, `6 LPA`, `6L`, `6 lakh` | any | 6 / 6.5 | `= ₹6,00,000 a year (6 LPA)` |
| `150000`, `₹1,50,000`, `6,00,000` | LPA | 1.5 / 6 | Read as rupees per year. On leaving the field it switches to `₹/yr` and shows `1,50,000` |
| `600000` | ₹/yr | 6 | Tidied to `6,00,000` |
| `6` | ₹/yr | 6 | "Read as 6 LPA." (six rupees a year can't be meant) |
| `50000` | LPA | 6 | Under ₹1 lakh a year is not a real CTC, so it's read as monthly, with a note saying so and how to change it |
| `50000` | ₹/yr (picked on purpose) | 0.5 | Kept as typed. Warning: "That's only ₹50,000 a year. If it's a monthly salary, choose ₹ per month." |
| `75,000`, `75k` | ₹/mo | 9 | `= ₹9,00,000 a year (9 LPA)` |
| `50k/month`, `1.5L pm` | any | 6 / 18 | Words such as "per month", "pm" and "/month" decide the period |
| `1.2 cr` | any | 120 | Warning (non-blocking): "That's ₹1.2 crore a year (120 LPA). Just checking: is that right?" |
| `8-10`, `8 to 10 lpa`, `6,00,000 - 8,00,000` | any | lower end | "Forms take one number, so we'll use the lower end of 8–10 LPA: 8 LPA." |
| `0` | any | 0 | `No current salary (₹0)` |

The server applies the same rule as a safety net (`PreferencesPayload`): any CTC or floor of 1,000 or more is read as rupees and divided by 1,00,000. Old clients and direct API callers then get the same result.

## Validation and errors

**Blocking** (field turns red, Continue/Save disabled):

| Case | Message |
|---|---|
| Not a number (`abc`) | "Use numbers only, like 6, 6.5 or 6,00,000." |
| Negative | "Salary can't be negative. Enter 0 if you have no current salary." |
| Over ₹5 crore a year (500 LPA) | "₹600 crore a year (60000 LPA) is above our ₹5 crore limit. Check for extra zeros: for ₹12 lakh, type 12 (LPA) or 12,00,000." |
| Monthly figure under ₹1,000 (`50` with ₹/mo) | "Enter the full monthly amount in rupees, e.g. 50,000 (not 50)." |

**Non-blocking warnings** (shown with an alert icon; saving still allowed):

| Case | Message |
|---|---|
| 100 LPA or more | "That's ₹X crore a year. Just checking: is that right?" |
| Yearly amount under 1 LPA | "That's only ₹X a year. If it's a monthly salary, choose ₹ per month." |
| Expected lower than current | "Expected (6 LPA) is lower than current (8 LPA). Fine if you mean it, e.g. for a career switch." |
| Floor higher than expected | "This hides jobs paying your expected 8 LPA. Usually this is at or below your expected CTC." |

**Server errors:** a validation failure names the fields, e.g. "Please check: expected ctc lpa", never just "Invalid request parameters". Lists that are too long (target roles, keywords, cities) are de-duplicated and trimmed to their limits instead of failing the save.

## Edge cases

- **Fresher:** the checkbox stores `current_ctc_lpa = 0`, which form filling answers as 0. That is different from blank (`null`), which means "not answered".
- **Blank expected CTC:** stored as `null`. Application questions about expected CTC are left for the user in the review queue, never guessed.
- **No resume yet:** salary, notice and relocation answers given before a profile exists are kept in the questionnaire session (`pending_logistics`). They are shown back on the preferences screen and copied onto the profile when it's created, either by confirming a resume or by saving the profile.
- **Stored values coming back** (reload, Profile page) are shown in LPA.
- **Ranges:** stored as the lower end, with a note. Forms take a single number.
- **Scale mismatch:** rupees under LPA, lakhs under ₹/yr, and monthly values written with "k" or "pm" are all converted and explained. They are never silently guessed.

## Out of scope / later

- Currencies other than INR (salaries for jobs abroad).
- A separate fixed vs variable pay breakdown. Some Indian forms ask for "fixed CTC"; today the same figure is used.
- Analytics on which conversions fire most, to tune the defaults.
