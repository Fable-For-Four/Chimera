"use client";

import { Suspense, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";

async function responseDetail(response: Response) {
  const body = await response.json().catch(() => null);
  return typeof body?.detail === "string" ? body.detail : "This link is invalid or has expired";
}

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

function VerifyLink() {
  const searchParams = useSearchParams();
  const started = useRef(false);
  const [status, setStatus] = useState<"loading" | "confirmed" | "error">("loading");
  const [message, setMessage] = useState("Confirming your email");

  useEffect(() => {
    if (started.current) return;
    started.current = true;
    const token = searchParams.get("token");

    if (!token) {
      setStatus("error");
      setMessage("This link is invalid or has expired");
      return;
    }

    fetch("/api/auth/verify", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "same-origin",
      body: JSON.stringify({ token }),
    })
      .then(async (response) => {
        if (!response.ok) throw new Error(await responseDetail(response));
        setStatus("confirmed");
        setMessage("Email confirmed");
      })
      .catch((error: unknown) => {
        setStatus("error");
        setMessage(error instanceof Error ? error.message : "This link is invalid or has expired");
      });
  }, [searchParams]);

  return (
    <div className="card" style={{ width: "min(100%, 480px)", padding: "clamp(28px, 6vw, 48px)", gap: "22px" }}>
      <span
        aria-hidden="true"
        style={{
          width: "48px",
          height: "48px",
          display: "grid",
          placeItems: "center",
          borderRadius: "50%",
          border: `1px solid ${status === "error" ? "var(--red-border)" : "var(--lime-border)"}`,
          background: status === "error" ? "var(--red-soft)" : "var(--lime-soft)",
          color: status === "error" ? "var(--red)" : "var(--lime)",
          fontSize: "20px",
        }}
      >
        {status === "loading" ? "…" : status === "confirmed" ? "✓" : "!"}
      </span>
      <div aria-live="polite">
        <h1 style={{ fontSize: "30px", letterSpacing: "-0.035em" }}>{message}</h1>
        <p style={{ marginTop: "10px", color: "var(--text-muted)" }}>
          {status === "loading" && "The confirmation link is being checked."}
          {status === "confirmed" && "Your account can now open and investigate cases."}
          {status === "error" && "Ask for a new confirmation link from the sign-in screen."}
        </p>
      </div>
      {status === "confirmed" && (
        <Link className="btn btn-primary" href="/" style={{ alignSelf: "flex-start" }}>
          Open Chimera
        </Link>
      )}
      {status === "error" && (
        <Link className="btn" href="/login" style={{ alignSelf: "flex-start" }}>
          Return to sign in
        </Link>
      )}
    </div>
  );
}

export default function VerifyPage() {
  useIsolateAuthPage();

  return (
    <main
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 100,
        overflowY: "auto",
        background: "var(--bg)",
        display: "grid",
        placeItems: "center",
        padding: "24px",
      }}
    >
      <Suspense fallback={<p style={{ color: "var(--text-muted)" }}>Loading</p>}>
        <VerifyLink />
      </Suspense>
    </main>
  );
}
