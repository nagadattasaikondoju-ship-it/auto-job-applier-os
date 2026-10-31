import { apiRequest, apiUpload, downloadFile, downloadJson } from "./client";
import type {
  AnalyticsOverview,
  Answer,
  AnswerUpsert,
  ApplicationDetail,
  ApplicationListItem,
  ApplicationStatus,
  ApplyAtsResult,
  ApplyMode,
  AtsReport,
  AutopilotState,
  BatchResult,
  BillingOrder,
  Campaign,
  Completeness,
  ConsentPurpose,
  CoverLetterDoc,
  CreateApplicationResult,
  CreditBalance,
  ExperienceCreate,
  FollowUpDraft,
  FullProfile,
  Funnel,
  JobAtsResult,
  JobDetail,
  JobDocuments,
  JobFeed,
  JobFeedback,
  JobImportResult,
  LedgerEntry,
  MatchItem,
  Me,
  NextQuestion,
  NotificationList,
  OnboardingStatus,
  Paginated,
  Plan,
  Preferences,
  ProfileUpdate,
  RefreshMatchesResult,
  ResumeConfirmResult,
  ResumeVersion,
  ResumeVersionListItem,
  RewriteResult,
  SkillCreate,
  SubmitMode,
  TailorResult,
  TaskStatus,
  UploadResumeResult,
} from "./types";

// One object per backend router. Every page talks to the backend only through here.
export const api = {
  me: {
    get: () => apiRequest<Me>("/v1/me"),
  },

  profile: {
    get: () => apiRequest<FullProfile>("/v1/profile"),
    update: (body: ProfileUpdate) => apiRequest<{ status: string }>("/v1/profile", { method: "PUT", body }),
    completeness: () => apiRequest<Completeness>("/v1/profile/completeness"),
    addExperience: (body: ExperienceCreate) =>
      apiRequest<{ id: string }>("/v1/profile/experiences", { method: "POST", body }),
    addSkill: (body: SkillCreate) => apiRequest<{ id: string }>("/v1/profile/skills", { method: "POST", body }),
  },

  resumes: {
    upload: (raw_text: string, filename: string) =>
      apiRequest<UploadResumeResult>("/v1/resumes", { method: "POST", body: { raw_text, filename } }),
    uploadFile: (file: File) => apiUpload<UploadResumeResult>("/v1/resumes/upload", file),
    confirm: (id: string) => apiRequest<ResumeConfirmResult>(`/v1/resumes/${id}/confirm`, { method: "POST" }),
  },

  onboarding: {
    status: () => apiRequest<OnboardingStatus>("/v1/onboarding/status"),
    nextQuestion: () => apiRequest<NextQuestion>("/v1/onboarding/next-question"),
    answer: (question_id: string, answer: unknown) =>
      apiRequest<{ status: string }>("/v1/onboarding/answer", { method: "POST", body: { question_id, answer } }),
  },

  consents: {
    get: () => apiRequest<{ consents: Record<ConsentPurpose, boolean> }>("/v1/consents"),
    set: (purpose: ConsentPurpose, granted: boolean) =>
      apiRequest<{ status: string }>("/v1/consents", { method: "POST", body: { purpose, granted, version: "v1" } }),
  },

  jobs: {
    feed: (params: { cursor?: string | null; limit?: number; min_match_score?: number | null; matched_only?: boolean }) =>
      apiRequest<JobFeed>("/v1/jobs", { query: params }),
    get: (id: string) => apiRequest<JobDetail>(`/v1/jobs/${id}`),
    import: (url: string, optional_text = "") =>
      apiRequest<JobImportResult>("/v1/jobs/import", { method: "POST", body: { url, optional_text } }),
    feedback: (id: string, feedback: JobFeedback, reason?: string) =>
      apiRequest<{ status: string }>(`/v1/jobs/${id}/feedback`, { method: "POST", body: { feedback, reason } }),
    tailor: (id: string, includeCoverLetter = true, tone: "professional" | "friendly" | "direct" = "professional") =>
      apiRequest<TailorResult>(`/v1/jobs/${id}/tailor`, {
        method: "POST",
        query: { include_cover_letter: includeCoverLetter, tone },
      }),
    coverLetter: (id: string, tone: "professional" | "friendly" | "direct") =>
      apiRequest<CoverLetterDoc>(`/v1/jobs/${id}/cover-letter`, { method: "POST", query: { tone } }),
    documents: (id: string) => apiRequest<JobDocuments>(`/v1/jobs/${id}/documents`),
    save: (id: string, saved: boolean) =>
      apiRequest<{ saved: boolean }>(`/v1/jobs/${id}/save`, { method: "POST", query: { saved } }),
    discover: () => apiRequest<{ status: string; message: string }>("/v1/jobs/discover", { method: "POST" }),
  },

  matches: {
    list: (params: { decision?: string; status?: string; limit?: number } = {}) =>
      apiRequest<{ items: MatchItem[]; count: number }>("/v1/matches", { query: params }),
    refresh: () => apiRequest<RefreshMatchesResult>("/v1/matches/refresh", { method: "POST" }),
  },

  documents: {
    resumeVersion: (id: string) => apiRequest<ResumeVersion>(`/v1/resume-versions/${id}`),
    resumeVersions: () => apiRequest<{ items: ResumeVersionListItem[] }>("/v1/resume-versions"),
    downloadResumePdf: (id: string, filename = "Resume.pdf") => downloadFile(`/v1/resume-versions/${id}/pdf`, filename),
    downloadResumeDocx: (id: string, filename = "Resume.docx") =>
      downloadFile(`/v1/resume-versions/${id}/docx`, filename),
    downloadCoverLetterPdf: (id: string) => downloadFile(`/v1/cover-letters/${id}/pdf`, "Cover_Letter.pdf"),
  },

  ats: {
    scan: (body: { resume_id?: string; use_profile?: boolean; job_id?: string; jd_text?: string }) =>
      apiRequest<AtsReport>("/v1/ats/scan", { method: "POST", body }),
    rewriteBullets: (body: { job_id?: string; jd_text?: string } = {}) =>
      apiRequest<RewriteResult>("/v1/ats/rewrite-bullets", { method: "POST", body }),
    apply: (body: {
      bullet_updates: { experience_id: string; bullet_id: string; text: string }[];
      summary?: string;
      add_skills?: string[];
    }) => apiRequest<ApplyAtsResult>("/v1/ats/apply", { method: "POST", body }),
    optimizeForJob: (body: { job_id?: string; jd_text?: string; job_title?: string; company?: string }) =>
      apiRequest<JobAtsResult>("/v1/ats/optimize-for-job", { method: "POST", body }),
  },

  preferences: {
    get: () => apiRequest<Preferences>("/v1/preferences"),
    save: (body: Omit<Preferences, "exists">) => apiRequest<Preferences>("/v1/preferences", { method: "PUT", body }),
  },

  autopilot: {
    get: () => apiRequest<AutopilotState>("/v1/autopilot"),
    start: (body: { mode: ApplyMode; daily_limit: number; min_match_score?: number; hybrid_threshold?: number }) =>
      apiRequest<{ campaign: Campaign; first_batch: BatchResult }>("/v1/autopilot/start", { method: "POST", body }),
    pause: () => apiRequest<{ campaign: Campaign }>("/v1/autopilot/pause", { method: "POST" }),
    resume: () => apiRequest<{ campaign: Campaign }>("/v1/autopilot/resume", { method: "POST" }),
    runNow: () => apiRequest<BatchResult>("/v1/autopilot/run-now", { method: "POST" }),
    retry: (applicationId: string) =>
      apiRequest<{ status: string }>(`/v1/autopilot/retry/${applicationId}`, { method: "POST" }),
  },

  applications: {
    create: (job_id: string, channel = "extension") =>
      apiRequest<CreateApplicationResult>("/v1/applications", { method: "POST", body: { job_id, channel } }),
    list: (params: { status?: string; search?: string; page?: number; page_size?: number } = {}) =>
      apiRequest<Paginated<ApplicationListItem>>("/v1/applications", { query: params }),
    get: (id: string) => apiRequest<ApplicationDetail>(`/v1/applications/${id}`),
    updateStatus: (id: string, status: ApplicationStatus, notes?: string) =>
      apiRequest<{ id: string; status: ApplicationStatus }>(`/v1/applications/${id}/status`, {
        method: "PATCH",
        body: { status, notes },
      }),
    withdraw: (id: string) => apiRequest<void>(`/v1/applications/${id}`, { method: "DELETE" }),
    exportCsv: () => downloadFile("/v1/applications/export.csv", "applyon-applications.csv"),
    followUps: () =>
      apiRequest<{ due: ApplicationListItem[]; upcoming: ApplicationListItem[] }>("/v1/applications/follow-ups"),
    draftFollowUp: (id: string, tone: "professional" | "friendly" | "direct" = "professional") =>
      apiRequest<FollowUpDraft>(`/v1/applications/${id}/follow-up/draft`, { method: "POST", body: { tone } }),
    followUpSent: (id: string) =>
      apiRequest<{ follow_up_at: string | null }>(`/v1/applications/${id}/follow-up/sent`, { method: "POST" }),
    setFollowUp: (id: string, follow_up_at: string | null) =>
      apiRequest<{ follow_up_at: string | null }>(`/v1/applications/${id}/follow-up`, {
        method: "PATCH",
        body: { follow_up_at },
      }),
  },

  reviewQueue: {
    list: (page = 1) => apiRequest<Paginated<ApplicationDetail>>("/v1/review-queue", { query: { page } }),
    approve: (id: string) =>
      apiRequest<{ status: string; submission_queued: boolean; apply_mode?: SubmitMode }>(`/v1/review-queue/applications/${id}/approve`, {
        method: "POST",
      }),
    reject: (id: string) =>
      apiRequest<{ status: string }>(`/v1/review-queue/applications/${id}/reject`, { method: "POST" }),
    editAnswer: (id: string, field_id: string, new_value: unknown, save_to_answer_bank: boolean) =>
      apiRequest<{ updated: boolean }>(`/v1/review-queue/applications/${id}/edit-answer`, {
        method: "POST",
        body: { field_id, new_value, save_to_answer_bank },
      }),
  },

  answers: {
    list: () => apiRequest<Answer[]>("/v1/answers"),
    upsert: (body: AnswerUpsert) => apiRequest<{ id: string }>("/v1/answers", { method: "POST", body }),
  },

  billing: {
    balance: () => apiRequest<CreditBalance>("/v1/credits/balance"),
    ledger: (page = 1) => apiRequest<Paginated<LedgerEntry>>("/v1/credits/ledger", { query: { page } }),
    plans: () => apiRequest<{ plans: Record<string, Plan> }>("/v1/plans"),
    createOrder: (plan_id: string, billing_period: "monthly" | "yearly" = "monthly") =>
      apiRequest<BillingOrder>("/v1/billing/create-order", { method: "POST", body: { plan_id, billing_period } }),
    topupDemo: (amount = 10, credit_type: "apply" | "ai" = "apply") =>
      apiRequest<{ balance_after: number }>("/v1/credits/topup-demo", {
        method: "POST",
        body: { amount, credit_type, reason: "demo_topup" },
      }),
  },

  notifications: {
    list: (unread_only = false) => apiRequest<NotificationList>("/v1/notifications", { query: { unread_only } }),
    read: (id: string) => apiRequest<{ id: string }>(`/v1/notifications/${id}/read`, { method: "POST" }),
    readAll: () => apiRequest<{ marked_read_count: number }>("/v1/notifications/read-all", { method: "POST" }),
  },

  analytics: {
    overview: () => apiRequest<AnalyticsOverview>("/v1/analytics/overview"),
    funnel: () => apiRequest<Funnel>("/v1/analytics/funnel"),
  },

  privacy: {
    exportData: () => downloadJson("/v1/privacy/export", "applyon-data-export.json"),
    deleteAccount: () => apiRequest<unknown>("/v1/privacy/delete-account", { method: "DELETE" }),
  },

  tasks: {
    get: (id: string) => apiRequest<TaskStatus>(`/v1/tasks/${id}`),
  },
};
