// Response and request shapes for the Applyon FastAPI backend (/v1).
// Kept in sync by hand with apps/api/routers/*.py.

export type Decision = "apply" | "maybe" | "skip";
export type MatchStatus = "new" | "seen" | "saved" | "dismissed" | "queued";

export type ApplicationStatus =
  | "draft"
  | "preparing"
  | "ready_for_review"
  | "approved"
  | "submitting"
  | "submitted"
  | "needs_user_action"
  | "failed"
  | "withdrawn"
  | "interview"
  | "offer"
  | "rejected"
  | "ghosted";

export interface ApiErrorBody {
  error?: { code: string; message: string; details?: unknown };
  detail?: unknown;
}

// ---------- Me / profile ----------
export interface Me {
  user_id: string;
  email: string | null;
  role: string;
}

export interface ProfileCore {
  user_id: string;
  full_name: string;
  email: string;
  phone: string | null;
  city: string | null;
  state: string | null;
  country: string | null;
  headline: string | null;
  summary: string | null;
  total_experience_months: number | null;
  current_title: string | null;
  current_company: string | null;
  current_ctc_lpa: number | null;
  expected_ctc_lpa: number | null;
  notice_period_days: number | null;
  currently_serving_notice: boolean | null;
  willing_to_relocate: boolean | null;
  links: Record<string, string> | null;
}

export interface ExperienceBullet {
  id?: string;
  text: string;
  skills?: string[];
  metrics?: string[];
}

export interface Experience {
  id: string;
  company: string;
  title: string;
  start_date: string;
  end_date: string | null;
  is_current: boolean;
  bullets: ExperienceBullet[] | string[];
}

export interface Education {
  id: string;
  institution: string;
  degree: string;
  field: string;
  grade: string;
}

export interface Skill {
  id: string;
  name: string;
  normalized_name: string;
  category: string;
  proficiency: string;
}

export interface Completeness {
  score: number;
  can_start_autopilot: boolean;
  missing?: string[];
  [key: string]: unknown;
}

export interface FullProfile {
  profile: ProfileCore;
  experiences: Experience[];
  educations: Education[];
  skills: Skill[];
  completeness: Completeness;
}

export type ProfileUpdate = Partial<
  Pick<
    ProfileCore,
    | "full_name"
    | "phone"
    | "city"
    | "state"
    | "country"
    | "headline"
    | "summary"
    | "current_title"
    | "current_company"
    | "current_ctc_lpa"
    | "expected_ctc_lpa"
    | "notice_period_days"
    | "currently_serving_notice"
    | "willing_to_relocate"
    | "links"
  >
>;

export interface ExperienceCreate {
  company: string;
  title: string;
  employment_type?: string;
  location?: string;
  start_date: string;
  end_date?: string | null;
  is_current?: boolean;
  bullets?: { text: string }[];
}

export interface SkillCreate {
  name: string;
  category?: string;
  years?: number;
  proficiency?: string;
}

// ---------- Resumes ----------
export interface ParsedResume {
  full_name?: string;
  email?: string;
  phone?: string;
  city?: string;
  headline?: string;
  summary?: string;
  current_title?: string;
  current_company?: string;
  total_experience_months?: number;
  experiences?: {
    company?: string;
    title?: string;
    start_date?: string;
    end_date?: string | null;
    is_current?: boolean;
    bullets?: (string | ExperienceBullet)[];
  }[];
  educations?: { institution?: string; degree?: string; field?: string; grade?: string }[];
  skills?: { name?: string; category?: string }[];
  [key: string]: unknown;
}

export interface ResumeUploadResult {
  id: string;
  status: string;
  parsed_profile: ParsedResume;
}

export interface ResumeConfirmResult {
  status: string;
  profile_version_id: string;
  version_no: number;
}

// ---------- Onboarding ----------
export type QuestionType =
  | "text"
  | "long_text"
  | "number"
  | "choice"
  | "multi_select"
  | "boolean"
  | "date"
  | string;

export interface Question {
  id: string;
  canonical_key: string;
  text: string;
  type: QuestionType;
  options?: string[];
  required?: boolean;
  placeholder?: string;
  help_text?: string;
  min?: number;
  max?: number;
}

export interface NextQuestion {
  completed: boolean;
  progress_percent: number;
  question: Question | null;
}

export interface OnboardingStatus {
  status: string;
  current_step: string;
  progress_percent: number;
  completed?: boolean;
  answers: Record<string, unknown>;
}

export type ConsentPurpose = "profile_matching" | "document_generation" | "auto_submit";

// ---------- Jobs & matches ----------
export interface MatchSummary {
  score: number;
  decision: Decision;
  fit_reasons: string[];
  gaps: string[];
  resume_focus?: string[];
  risk_flags?: string[];
  user_feedback?: string | null;
  status: MatchStatus;
}

export interface JobFeedItem {
  id: string;
  title: string;
  company: string;
  location: string | null;
  locations: string[] | null;
  remote_mode: string | null;
  employment_type: string | null;
  experience_range: string | null;
  salary_min_lpa: number | null;
  salary_max_lpa: number | null;
  required_skills: string[] | null;
  application_url: string;
  ats_type: string | null;
  posted_at: string | null;
  match: MatchSummary | null;
}

export interface JobFeed {
  items: JobFeedItem[];
  next_cursor: string | null;
  count: number;
}

export interface JobDetail extends Omit<JobFeedItem, "experience_range"> {
  description_html: string | null;
  description_text: string | null;
  experience_min: number | null;
  experience_max: number | null;
}

export interface JobImportResult {
  job_id: string;
  title: string;
  company: string;
  ats_type: string | null;
  is_new: boolean;
  application_url: string;
}

export type JobFeedback = "good" | "bad" | "dismissed";

export interface MatchItem {
  id: string;
  job_id: string;
  title: string;
  company: string;
  location: string | null;
  match_score: number;
  decision: Decision;
  fit_reasons: string[];
  gaps: string[];
  resume_focus: string[];
  risk_flags: string[];
  status: MatchStatus;
  user_feedback: string | null;
  application_url: string;
  created_at: string;
}

export interface RefreshMatchesResult {
  status: string;
  new_matches_count: number;
}

// ---------- Documents ----------
export interface FlaggedClaim {
  claim?: string;
  text?: string;
  reason?: string;
  [key: string]: unknown;
}

export interface ResumeVersion {
  id: string;
  job_id?: string | null;
  version_no: number;
  truth_check_status: "passed" | "flagged" | "failed" | string;
  flagged_claims: FlaggedClaim[] | null;
  content: Record<string, unknown> | null;
  status?: string;
  pdf_url: string;
  created_at?: string;
}

export interface TailorResult {
  status: string;
  resume_version: ResumeVersion;
  cover_letter: { id: string; text: string; pdf_path: string | null } | null;
}

// ---------- Applications ----------
export interface ApplicationListItem {
  id: string;
  job_id: string;
  job_title: string;
  company_name: string;
  location: string | null;
  salary_min_lpa: number | null;
  salary_max_lpa: number | null;
  status: ApplicationStatus;
  channel: string;
  application_url: string | null;
  submitted_at: string | null;
  created_at: string;
}

export interface Paginated<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export interface ResolvedField {
  field_id: string;
  label: string;
  canonical_key: string | null;
  field_type: string;
  required: boolean;
  value: unknown;
  source: "profile" | "answer_bank" | "ai" | "user" | "unresolved" | string;
  confidence: number;
  needs_review: boolean;
  options: string[];
}

export interface ApplicationEvent {
  id: string;
  type: string;
  payload: Record<string, unknown> | null;
  actor: string;
  created_at: string;
}

export interface ApplicationDetail {
  id: string;
  status: ApplicationStatus;
  channel: string;
  application_url: string | null;
  submitted_at: string | null;
  created_at: string;
  failure_reason: string | null;
  job: {
    id: string;
    title: string;
    company_name: string;
    location_city: string;
    is_remote: boolean;
    ats_type: string;
    description: string;
    salary_min_lpa: number | null;
    salary_max_lpa: number | null;
  };
  plan: { fields?: ResolvedField[]; can_auto_submit?: boolean; unresolved_count?: number };
  events: ApplicationEvent[];
}

export interface CreateApplicationResult {
  id: string;
  status: ApplicationStatus;
  channel: string;
  application_url: string | null;
  unresolved_count: number;
  can_auto_submit: boolean;
}

// ---------- Answer bank ----------
export interface Answer {
  id: string;
  question_key: string;
  question_text: string;
  answer_text: string;
  answer_type: string;
  source: string;
  times_used: number;
}

export interface AnswerUpsert {
  question_key: string;
  question_text: string;
  answer_text: string;
  answer_type?: string;
}

// ---------- Credits & billing ----------
export interface CreditBucket {
  available: number;
  held: number;
  total: number;
}

export interface CreditBalance {
  apply_credits: CreditBucket;
  ai_credits: CreditBucket;
  plan: string;
  plan_name: string;
  daily_limit: { limit?: number; used?: number; remaining?: number; [key: string]: unknown } | number;
}

export interface LedgerEntry {
  id: string;
  credit_type: string;
  amount: number;
  reason: string;
  balance_after: number;
  created_at: string;
  [key: string]: unknown;
}

export interface Plan {
  name: string;
  price_inr: number;
  monthly_ai_credits: number;
  monthly_apply_credits: number;
  daily_application_limit: number;
  auto_submit_allowed: boolean;
  priority_queue: boolean;
  features: string[];
}

export interface BillingOrder {
  order_id: string;
  currency: string;
  amount_paise: number;
  plan_id: string;
  gateway: string;
  notes?: string;
}

// ---------- Notifications ----------
export interface Notification {
  id: string;
  type: string;
  title: string;
  body: string;
  data: Record<string, unknown> | null;
  read_at: string | null;
  created_at: string | null;
}

export interface NotificationList {
  items: Notification[];
  unread_count: number;
  limit: number;
  offset: number;
}

// ---------- Analytics ----------
export interface AnalyticsOverview {
  total_applications: number;
  total_submitted: number;
  total_interviews: number;
  total_offers: number;
  status_distribution: Record<string, number>;
  credits: { available_balance: number; daily_remaining: number; daily_limit: number };
  ai_usage: { tokens_in: number; tokens_out: number; total_tokens: number; estimated_cost_usd: number };
  profile_completeness_score: number;
  can_start_autopilot: boolean;
}

export interface FunnelStage {
  stage: string;
  count: number;
  conversion_pct: number;
}

export interface Funnel {
  stages: FunnelStage[];
  overall_conversion_pct: number;
}

export interface TaskStatus {
  id: string;
  kind: string;
  status: string;
  progress: number;
  result_ref: string | null;
  error: string | null;
}
