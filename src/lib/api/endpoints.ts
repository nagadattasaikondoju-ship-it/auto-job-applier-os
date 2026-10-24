import { apiRequest, downloadFile, downloadJson } from "./client";
import type {
  AnalyticsOverview,
  Answer,
  AnswerUpsert,
  ApplicationDetail,
  ApplicationListItem,
  ApplicationStatus,
  BillingOrder,
  ConsentPurpose,
  CreateApplicationResult,
  CreditBalance,
  ExperienceCreate,
  FullProfile,
  Funnel,
  JobDetail,
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
  ProfileUpdate,
  RefreshMatchesResult,
  ResumeConfirmResult,
  ResumeUploadResult,
  ResumeVersion,
  SkillCreate,
  TailorResult,
  TaskStatus,
  Completeness,
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
      apiRequest<ResumeUploadResult>("/v1/resumes", { method: "POST", body: { raw_text, filename } }),
    confirm: (id: string) => apiRequest<ResumeConfirmResult>(`/v1/resumes/${id}/confirm`, { method: "POST" }),
  },

  onboarding: {
    status: () => apiRequest<OnboardingStatus>("/v1/onboarding/status"),
    nextQuestion: () => apiRequest<NextQuestion>("/v1/onboarding/next-question"),
    answer: (question_id: string, answer: unknown) =>
      apiRequest<{ status: string }>("/v1/onboarding/answer", { method: "POST", body: { question_id, answer } }),
  },

  consents: {
    set: (purpose: ConsentPurpose, granted: boolean) =>
      apiRequest<{ status: string }>("/v1/consents", { method: "POST", body: { purpose, granted, version: "v1" } }),
  },

  jobs: {
    feed: (params: { cursor?: string | null; limit?: number; min_match_score?: number | null }) =>
      apiRequest<JobFeed>("/v1/jobs", { query: params }),
    get: (id: string) => apiRequest<JobDetail>(`/v1/jobs/${id}`),
    import: (url: string, optional_text = "") =>
      apiRequest<JobImportResult>("/v1/jobs/import", { method: "POST", body: { url, optional_text } }),
    feedback: (id: string, feedback: JobFeedback, reason?: string) =>
      apiRequest<{ status: string }>(`/v1/jobs/${id}/feedback`, { method: "POST", body: { feedback, reason } }),
    tailor: (id: string, includeCoverLetter = true) =>
      apiRequest<TailorResult>(`/v1/jobs/${id}/tailor`, {
        method: "POST",
        query: { include_cover_letter: includeCoverLetter },
      }),
  },

  matches: {
    list: (params: { decision?: string; status?: string; limit?: number } = {}) =>
      apiRequest<{ items: MatchItem[]; count: number }>("/v1/matches", { query: params }),
    refresh: () => apiRequest<RefreshMatchesResult>("/v1/matches/refresh", { method: "POST" }),
  },

  documents: {
    resumeVersion: (id: string) => apiRequest<ResumeVersion>(`/v1/resume-versions/${id}`),
    downloadResumePdf: (id: string, filename = "Applyon_Resume.pdf") =>
      downloadFile(`/v1/resume-versions/${id}/pdf`, filename),
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
  },

  reviewQueue: {
    list: (page = 1) => apiRequest<Paginated<ApplicationDetail>>("/v1/review-queue", { query: { page } }),
    approve: (id: string) =>
      apiRequest<{ status: string }>(`/v1/review-queue/applications/${id}/approve`, { method: "POST" }),
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
