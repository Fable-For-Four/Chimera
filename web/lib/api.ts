import { CaseData, IntakeData, User, Approval } from "./types";

const IS_BROWSER = typeof window !== "undefined";

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers || {});
  if (!headers.has("Content-Type") && options.body && typeof options.body === "string") {
    headers.set("Content-Type", "application/json");
  }

  // No client timeout: a run can take a few seconds, and the API itself gives up after 120 s.
  let res: Response;
  try {
    res = await fetch(path, {
      ...options,
      headers,
      credentials: "same-origin",
    });
  } catch (fetchErr: unknown) {
    // Network-level failures (ECONNREFUSED, EPERM, abort) → treat as offline
    throw new Error(fetchErr instanceof Error ? fetchErr.message : "Network error");
  }

  if (res.status === 401) {
    if (IS_BROWSER && !window.location.pathname.startsWith("/login") && !window.location.pathname.startsWith("/verify")) {
      window.location.href = "/login";
    }
    const errData = await res.json().catch(() => ({ detail: "Not signed in" }));
    throw new Error(errData.detail || "Authentication required");
  }

  if (res.status === 403) {
    const errData = await res.json().catch(() => ({ detail: "Forbidden" }));
    throw new Error(errData.detail || "You do not have permission for this action");
  }

  if (!res.ok) {
    const errData = await res.json().catch(() => ({ detail: `HTTP Error ${res.status}` }));
    throw new Error(errData.detail || `Request failed with status ${res.status}`);
  }

  if (res.status === 204) {
    return {} as T;
  }

  return (await res.json()) as T;
}

export async function getMe(): Promise<User | null> {
  try {
    return await request<User>("/api/auth/me");
  } catch {
    return null;
  }
}

export async function logoutUser(): Promise<void> {
  try {
    await request<void>("/api/auth/logout", { method: "POST" });
  } finally {
    if (IS_BROWSER) window.location.href = "/login";
  }
}

export async function getIntake(): Promise<IntakeData> {
  return request<IntakeData>("/api/intake");
}

export async function getCase(): Promise<CaseData | null> {
  try {
    return await request<CaseData>("/api/case");
  } catch {
    return null;
  }
}

export async function getStressCase(level: number): Promise<CaseData> {
  return request<CaseData>(`/api/case/stress/${level}`);
}

export async function postRunInvestigation(): Promise<CaseData> {
  return request<CaseData>("/api/case/run", { method: "POST" });
}

export async function postApproveAction(actionId: string): Promise<Approval> {
  return request<Approval>(`/api/actions/${encodeURIComponent(actionId)}/approve`, {
    method: "POST",
  });
}

export async function getApprovals(): Promise<Approval[]> {
  try {
    return await request<Approval[]>("/api/approvals");
  } catch {
    return [];
  }
}
