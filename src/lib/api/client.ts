import type { ApiErrorBody } from "./types";

export const API_BASE_URL = (process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000").replace(
  /\/$/,
  ""
);

export class ApiError extends Error {
  status: number;
  code: string;
  details: unknown;

  constructor(status: number, code: string, message: string, details?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

type TokenGetter = () => Promise<string | null>;

let getToken: TokenGetter = async () => null;

/** Registered once by AuthProvider so every request carries the current user's ID token. */
export function setTokenGetter(fn: TokenGetter) {
  getToken = fn;
}

function toApiError(status: number, body: ApiErrorBody | null): ApiError {
  if (body?.error) {
    return new ApiError(status, body.error.code, body.error.message, body.error.details);
  }
  // FastAPI default `{detail: "..."}` or `{detail: {code, message}}`
  const detail = body?.detail;
  if (detail && typeof detail === "object" && "message" in detail) {
    const d = detail as { code?: string; message: string };
    return new ApiError(status, d.code ?? `HTTP_${status}`, d.message);
  }
  if (typeof detail === "string") return new ApiError(status, `HTTP_${status}`, detail);
  return new ApiError(status, `HTTP_${status}`, `Request failed (${status})`);
}

interface RequestOptions {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  body?: unknown;
  query?: Record<string, string | number | boolean | null | undefined>;
  signal?: AbortSignal;
}

function buildUrl(path: string, query?: RequestOptions["query"]) {
  const url = new URL(path.startsWith("http") ? path : `${API_BASE_URL}${path}`);
  if (query) {
    for (const [k, v] of Object.entries(query)) {
      if (v !== undefined && v !== null && v !== "") url.searchParams.set(k, String(v));
    }
  }
  return url.toString();
}

async function authHeaders(): Promise<Record<string, string>> {
  const token = await getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export async function apiRequest<T>(path: string, opts: RequestOptions = {}): Promise<T> {
  const headers: Record<string, string> = { Accept: "application/json", ...(await authHeaders()) };
  if (opts.body !== undefined) headers["Content-Type"] = "application/json";

  let res: Response;
  try {
    res = await fetch(buildUrl(path, opts.query), {
      method: opts.method ?? "GET",
      headers,
      body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined,
      signal: opts.signal,
    });
  } catch {
    throw new ApiError(0, "NETWORK_ERROR", "Can't reach the Applyon API. Is the backend running?");
  }

  if (res.status === 204) return undefined as T;

  const text = await res.text();
  let data: unknown = null;
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = null;
    }
  }

  if (!res.ok) throw toApiError(res.status, data as ApiErrorBody | null);
  return data as T;
}

/** Upload a file as multipart/form-data (field name "file"). */
export async function apiUpload<T>(path: string, file: File): Promise<T> {
  const form = new FormData();
  form.append("file", file);
  let res: Response;
  try {
    res = await fetch(buildUrl(path), { method: "POST", headers: await authHeaders(), body: form });
  } catch {
    throw new ApiError(0, "NETWORK_ERROR", "Can't reach the Applyon API. Is the backend running?");
  }
  const text = await res.text();
  let data: unknown = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = null;
  }
  if (!res.ok) throw toApiError(res.status, data as ApiErrorBody | null);
  return data as T;
}

/** Download a protected file (e.g. a resume PDF) and hand it to the browser. */
export async function downloadFile(path: string, filename: string) {
  const res = await fetch(buildUrl(path), { headers: await authHeaders() });
  if (!res.ok) {
    let body: ApiErrorBody | null = null;
    try {
      body = (await res.json()) as ApiErrorBody;
    } catch {
      body = null;
    }
    throw toApiError(res.status, body);
  }
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

/** Download JSON returned by a POST endpoint (used for the data export). */
export async function downloadJson(path: string, filename: string, method: "GET" | "POST" = "POST") {
  const data = await apiRequest<unknown>(path, { method });
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
