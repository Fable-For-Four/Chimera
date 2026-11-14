"use client";

import { FormEvent, useEffect, useState } from "react";

import type { User } from "../../lib/types";

type Mode = "login" | "signup";

async function responseDetail(response: Response, fallback: string) {
  const body = await response.json().catch(() => null);
  return typeof body?.detail === "string" ? body.detail : fallback;
}

const fieldStyle = {
  width: "100%",
  border: "1px solid var(--border-light)",
  background: "var(--bg)",
  padding: "9px 11px",
} as const;

function useIsolateAuthPage() {
  useEffect(() => {
    const shellElements = [
      document.querySelector<HTMLElement>(".sidebar"),
      document.querySelector<HTMLElement>(".topbar"),
    ].filter((element): element is HTMLElement => element !== null);

    for (const element of shellElements) {
      element.inert = true;
      element.setAttribute("aria-hidden", "true");
    }

    return () => {
      for (const element of shellElements) {
        element.inert = false;
        element.removeAttribute("aria-hidden");
      }
    };
  }, []);
}

export default function LoginPage() {
  useIsolateAuthPage();
  const [mode, setMode] = useState<Mode>("login");
  const [checking, setChecking] = useState(true);
  const [busy, setBusy] = useState(false);
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [password, setPassword] = useState("");
  const [pendingEmail, setPendingEmail] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  useEffect(() => {
    let active = true;

    fetch("/api/auth/me", { credentials: "same-origin" })
      .then(async (response) => {
        if (!active || !response.ok) return;
        const user = (await response.json()) as User;
        if (user.verified) {
          window.location.replace("/");
        } else {
          setPendingEmail(user.email);
        }
      })
      .catch(() => undefined)
      .finally(() => {
        if (active) setChecking(false);
      });

    return () => {
      active = false;
    };
  }, []);

  function chooseMode(nextMode: Mode) {
    setMode(nextMode);
    setError("");
    setNotice("");
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    setNotice("");

    const path = mode === "login" ? "/api/auth/login" : "/api/auth/signup";
    const body = mode === "login" ? { email, password } : { email, name, password };

    try {
      const response = await fetch(path, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "same-origin",
        body: JSON.stringify(body),
      });
      if (!response.ok) {
        setError(await responseDetail(response, "We could not complete that request"));
        return;
      }

      const user = (await response.json()) as User;
      if (user.verified) {
        window.location.replace("/");
      } else {
        setPendingEmail(user.email);
      }
    } catch {
      setError("Chimera could not reach the API. Check that the server is running");
    } finally {
      setBusy(false);
    }
  }

  async function resend() {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const response = await fetch("/api/auth/resend-verification", {
        method: "POST",
        credentials: "same-origin",
      });
      if (!response.ok) {
        setError(await responseDetail(response, "A new confirmation link could not be sent"));
        return;
      }
      setNotice("A new confirmation link is on its way");
    } catch {
      setError("Chimera could not reach the API. Check that the server is running");
    } finally {
      setBusy(false);
    }
  }

  async function signOut() {
    setBusy(true);
    try {
      await fetch("/api/auth/logout", { method: "POST", credentials: "same-origin" });
    } finally {
      setPendingEmail(null);
      setPassword("");
      setNotice("");
      setError("");
      setBusy(false);
    }
  }

  return (
    <main className="login-page">
      <div className="login-panel">
        <div className="brand login-brand">
          <span className="brand-mark" aria-hidden="true">
            <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.6">
              <line x1="2" y1="4" x2="9" y2="4" />
              <line x1="5" y1="8" x2="12" y2="8" />
              <line x1="8" y1="12" x2="14" y2="12" />
            </svg>
          </span>
          <div>
            <div className="brand-name">Chimera</div>
            <div className="brand-sub">Log investigation</div>
          </div>
        </div>
          {checking ? (
            <p style={{ color: "var(--text-muted)" }}>Loading</p>
          ) : pendingEmail ? (
            <div className="card" style={{ gap: "20px", padding: "clamp(24px, 5vw, 40px)" }}>
              <span className="pill pill-lime" style={{ alignSelf: "flex-start" }}>
                Account created
              </span>
              <div>
                <h2 className="login-title">Check your email</h2>
                <p style={{ marginTop: "10px", color: "var(--text-muted)" }}>
                  We sent a confirmation link to <strong style={{ color: "var(--text)" }}>{pendingEmail}</strong>.
                  Confirm it before opening a case.
                </p>
              </div>
              {notice && <p role="status" style={{ color: "var(--lime)" }}>{notice}</p>}
              {error && <p role="alert" style={{ color: "var(--red)" }}>{error}</p>}
              <div style={{ display: "flex", gap: "10px", flexWrap: "wrap" }}>
                <button className="btn btn-primary" type="button" onClick={resend} disabled={busy}>
                  {busy ? "Sending..." : "Send again"}
                </button>
                <button className="btn" type="button" onClick={signOut} disabled={busy}>
                  Sign out
                </button>
              </div>
            </div>
          ) : (
            <>
              <div style={{ marginBottom: "18px" }}>
                <h2 className="login-title">
                  {mode === "login" ? "Sign in" : "Create an account"}
                </h2>
                <p style={{ marginTop: "8px", color: "var(--text-muted)" }}>
                  {mode === "login"
                    ? "Use the account your team gave you."
                    : "New accounts begin with read-only Viewer access."}
                </p>
              </div>

              <div
                role="tablist"
                aria-label="Account access"
                className="login-tabs"
              >
                <button
                  role="tab"
                  aria-selected={mode === "login"}
                  className={mode === "login" ? "active" : ""}
                  type="button"
                  onClick={() => chooseMode("login")}
                >
                  Sign in
                </button>
                <button
                  role="tab"
                  aria-selected={mode === "signup"}
                  className={mode === "signup" ? "active" : ""}
                  type="button"
                  onClick={() => chooseMode("signup")}
                >
                  Sign up
                </button>
              </div>

              <form className="card" onSubmit={submit} style={{ padding: "20px", gap: "16px" }}>
                {mode === "signup" && (
                  <label style={{ display: "grid", gap: "7px", fontSize: "12px", fontWeight: 600 }}>
                    Name
                    <input
                      name="name"
                      autoComplete="name"
                      required
                      value={name}
                      onChange={(event) => setName(event.target.value)}
                      style={fieldStyle}
                    />
                  </label>
                )}
                <label style={{ display: "grid", gap: "7px", fontSize: "12px", fontWeight: 600 }}>
                  Email
                  <input
                    name="email"
                    type="email"
                    autoComplete="email"
                    required
                    value={email}
                    onChange={(event) => setEmail(event.target.value)}
                    style={fieldStyle}
                  />
                </label>
                <label style={{ display: "grid", gap: "7px", fontSize: "12px", fontWeight: 600 }}>
                  Password
                  <input
                    name="password"
                    type="password"
                    autoComplete={mode === "login" ? "current-password" : "new-password"}
                    minLength={8}
                    required
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    style={fieldStyle}
                  />
                  {mode === "signup" && (
                    <span style={{ color: "var(--text-dim)", fontWeight: 400 }}>Use 8 to 72 bytes.</span>
                  )}
                </label>

                {error && <p role="alert" style={{ color: "var(--red)", fontSize: "12px" }}>{error}</p>}
                <button className="btn btn-primary" type="submit" disabled={busy} style={{ width: "100%" }}>
                  {busy ? "Working..." : mode === "login" ? "Sign in" : "Create account"}
                </button>
              </form>
            </>
          )}
        <p className="login-foot">Simulated company logs. Every number comes from the engine.</p>
      </div>
    </main>
  );
}
