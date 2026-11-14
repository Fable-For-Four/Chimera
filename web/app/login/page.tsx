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
  borderRadius: "6px",
  background: "var(--bg)",
  padding: "10px 12px",
  outline: "none",
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
    <main
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 100,
        overflowY: "auto",
        background: "var(--bg)",
        display: "grid",
        gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 420px), 1fr))",
      }}
    >
      <section
        style={{
          minHeight: "100vh",
          padding: "clamp(32px, 7vw, 96px)",
          borderRight: "1px solid var(--border)",
          background: "var(--sidebar)",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          gap: "48px",
        }}
      >
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
            <span
              aria-hidden="true"
              style={{
                width: "36px",
                height: "36px",
                display: "grid",
                placeItems: "center",
                borderRadius: "6px",
                background: "var(--lime)",
                color: "var(--bg)",
                fontFamily: "var(--font-mono)",
                fontWeight: 800,
              }}
            >
              C
            </span>
            <strong style={{ letterSpacing: "0.08em" }}>CHIMERA</strong>
          </div>

          <h1
            style={{
              maxWidth: "540px",
              marginTop: "clamp(64px, 14vh, 150px)",
              fontSize: "clamp(32px, 4.5vw, 64px)",
              lineHeight: 1.02,
              letterSpacing: "-0.045em",
            }}
          >
            Follow the evidence, not the noise.
          </h1>
          <p style={{ maxWidth: "520px", marginTop: "24px", color: "var(--text-muted)", fontSize: "15px" }}>
            Reconstruct a security incident across scattered logs, test the story against innocent explanations,
            and keep every conclusion tied to its source.
          </p>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "10px", color: "var(--text-dim)" }}>
          <span style={{ width: "8px", height: "8px", borderRadius: "50%", background: "var(--lime)" }} />
          <span style={{ fontSize: "12px" }}>Local, deterministic investigation</span>
        </div>
      </section>

      <section
        style={{
          minHeight: "100vh",
          padding: "32px",
          display: "grid",
          placeItems: "center",
        }}
      >
        <div style={{ width: "min(100%, 440px)" }}>
          {checking ? (
            <p style={{ color: "var(--text-muted)" }}>Loading</p>
          ) : pendingEmail ? (
            <div className="card" style={{ gap: "20px", padding: "clamp(24px, 5vw, 40px)" }}>
              <span className="pill pill-lime" style={{ alignSelf: "flex-start" }}>
                Account created
              </span>
              <div>
                <h2 style={{ fontSize: "28px", letterSpacing: "-0.03em" }}>Check your email</h2>
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
              <div style={{ marginBottom: "28px" }}>
                <h2 style={{ fontSize: "30px", letterSpacing: "-0.035em" }}>
                  {mode === "login" ? "Sign in to the case" : "Create an account"}
                </h2>
                <p style={{ marginTop: "8px", color: "var(--text-muted)" }}>
                  {mode === "login"
                    ? "Use your assigned account to continue the investigation."
                    : "New accounts begin with read-only Viewer access."}
                </p>
              </div>

              <div
                role="tablist"
                aria-label="Account access"
                style={{
                  display: "grid",
                  gridTemplateColumns: "1fr 1fr",
                  padding: "4px",
                  marginBottom: "20px",
                  border: "1px solid var(--border)",
                  borderRadius: "8px",
                  background: "var(--panel)",
                }}
              >
                <button
                  role="tab"
                  aria-selected={mode === "login"}
                  className={mode === "login" ? "btn btn-primary" : "btn"}
                  type="button"
                  onClick={() => chooseMode("login")}
                >
                  Sign in
                </button>
                <button
                  role="tab"
                  aria-selected={mode === "signup"}
                  className={mode === "signup" ? "btn btn-primary" : "btn"}
                  type="button"
                  onClick={() => chooseMode("signup")}
                >
                  Sign up
                </button>
              </div>

              <form className="card" onSubmit={submit} style={{ padding: "24px", gap: "18px" }}>
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
        </div>
      </section>
    </main>
  );
}
