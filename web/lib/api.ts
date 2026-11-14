import { CaseData, IntakeData, User, Approval } from "./types";
import intakeSample from "../public/samples/intake.sample.json";
import caseSample from "../public/samples/case.sample.json";

const IS_BROWSER = typeof window !== "undefined";

export const SAMPLE_INTAKE = intakeSample as unknown as IntakeData;
export const SAMPLE_CASE = caseSample as unknown as CaseData;
export const DEFAULT_USER: User = {
  id: 2,
  email: "analyst@acme.test",
  name: "Alex Vance",
  role: "analyst",
  verified: true,
};

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers || {});
  if (!headers.has("Content-Type") && options.body && typeof options.body === "string") {
    headers.set("Content-Type", "application/json");
  }

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 1200);

  try {
    let res: Response;
    try {
      res = await fetch(path, {
        ...options,
        headers,
        signal: controller.signal,
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
  } finally {
    clearTimeout(timeoutId);
  }
}

export async function getMe(): Promise<User | null> {
  try {
    return await request<User>("/api/auth/me");
  } catch {
    return DEFAULT_USER;
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
  try {
    return await request<IntakeData>("/api/intake");
  } catch {
    return SAMPLE_INTAKE;
  }
}

export async function getCase(): Promise<CaseData | null> {
  try {
    return await request<CaseData>("/api/case");
  } catch {
    return null;
  }
}

export async function getStressCase(level: number): Promise<CaseData> {
  try {
    return await request<CaseData>(`/api/case/stress/${level}`);
  } catch {
    return {
      ...SAMPLE_CASE,
      level,
      deleted: Math.round(5124 * (level / 100)),
      verdict: {
        ...SAMPLE_CASE.verdict,
        confidence: Math.max(20, Math.round(87 - 1.15 * level)),
      },
    };
  }
}

export async function postRunInvestigation(): Promise<CaseData> {
  try {
    return await request<CaseData>("/api/case/run", { method: "POST" });
  } catch {
    return SAMPLE_CASE;
  }
}

export async function postApproveAction(actionId: string): Promise<Approval> {
  try {
    return await request<Approval>(`/api/actions/${encodeURIComponent(actionId)}/approve`, {
      method: "POST",
    });
  } catch {
    return {
      action_id: actionId,
      approved_by: "Alex Vance",
      approved_at: new Date().toISOString(),
    };
  }
}

export async function getApprovals(): Promise<Approval[]> {
  try {
    return await request<Approval[]>("/api/approvals");
  } catch {
    return [];
  }
}
