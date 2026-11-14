"use client";

import React from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useApp } from "../lib/state";
import { logoutUser } from "../lib/api";

const NAV_ITEMS = [
  { href: "/", label: "Overview", icon: "grid" },
  { href: "/graph", label: "Attack Graph", icon: "graph" },
  { href: "/logs", label: "Evidence Log", icon: "list" },
  { href: "/stress", label: "Stress Test", icon: "activity" },
  { href: "/report", label: "Report", icon: "file-text" },
];

export function Shell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, intake, caseData, isRunning, runInvestigation, resetCase, error } = useApp();
  const eventCount = intake?.summary.events.toLocaleString() ?? "";

  const handleRerun = () => {
    runInvestigation();
    if (pathname !== "/") {
      router.push("/");
    }
  };

  const handleReset = () => {
    resetCase();
    if (pathname !== "/") {
      router.push("/");
    }
  };

  const isCaseReady = Boolean(caseData && caseData.verdict && caseData.verdict.found);
  const isNoChain = Boolean(caseData && caseData.verdict && !caseData.verdict.found);
  const confidence = caseData?.verdict?.confidence ?? 0;

  return (
    <div className="app-container">
      {/* Sidebar */}
      <aside className="sidebar">
        <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "24px" }}>
          <div
            style={{
              width: "32px",
              height: "32px",
              borderRadius: "6px",
              background: "var(--lime)",
              color: "#0c1018",
              display: "grid",
              placeItems: "center",
              fontWeight: 800,
              fontFamily: "var(--font-mono)",
              fontSize: "18px",
            }}
          >
            C
          </div>
          <div className="brand-text">
            <div style={{ fontWeight: 700, letterSpacing: "1px", fontSize: "14px" }}>CHIMERA</div>
            <div className="kicker" style={{ fontSize: "9px" }}>Threat Intelligence</div>
          </div>
        </div>

        {/* Case Card */}
        <div
          className="sidebar-card"
          style={{
            background: "var(--panel)",
            border: "1px solid var(--border)",
            borderRadius: "6px",
            padding: "10px 12px",
            marginBottom: "20px",
          }}
        >
          <div className="kicker" style={{ marginBottom: "2px" }}>Case 0114 · Acme Corp</div>
          <div style={{ fontSize: "12px", color: "var(--text)", fontWeight: 500 }}>
            {isCaseReady
              ? "Active Breach Investigation"
              : isNoChain
              ? "Investigation Complete · No Chain"
              : "Pre-Investigation Intake"}
          </div>
          <div style={{ fontSize: "10px", color: "var(--text-dim)", marginTop: "4px" }}>
            14 Nov 2026 · 03:00–04:30 UTC
          </div>
        </div>

        {/* Navigation */}
        <nav style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
          {NAV_ITEMS.map((item) => {
            const active = pathname === item.href;
            const disabled = !isCaseReady && item.href !== "/" && item.href !== "/logs";

            return (
              <Link
                key={item.href}
                href={disabled ? "#" : item.href}
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  padding: "9px 12px",
                  borderRadius: "6px",
                  fontSize: "12px",
                  fontWeight: 500,
                  color: active ? "var(--lime)" : disabled ? "var(--text-dim)" : "var(--text-muted)",
                  background: active ? "var(--panel-raised)" : "transparent",
                  border: active ? "1px solid var(--border-light)" : "1px solid transparent",
                  pointerEvents: disabled ? "none" : "auto",
                  opacity: disabled ? 0.45 : 1,
                  transition: "all 0.15s",
                }}
              >
                <span style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                  <NavIcon name={item.icon} />
                  <span className="nav-label">{item.label}</span>
                </span>
                {item.href === "/logs" && (
                  <span className="mono" style={{ fontSize: "10px", color: "var(--text-dim)" }}>
                    {eventCount}
                  </span>
                )}
                {item.href === "/graph" && isCaseReady && (
                  <span className="mono" style={{ fontSize: "10px", color: "var(--lime)" }}>
                    {caseData?.chain.length} steps
                  </span>
                )}
              </Link>
            );
          })}
        </nav>

        {/* Bottom Card */}
        <div style={{ marginTop: "auto" }} className="sidebar-card">
          <div
            style={{
              padding: "12px",
              borderRadius: "6px",
              border: "1px solid var(--border)",
              background: "var(--panel)",
              fontSize: "11px",
              color: "var(--text-muted)",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "6px", marginBottom: "4px" }}>
              <span
                style={{
                  width: "6px",
                  height: "6px",
                  borderRadius: "50%",
                  background: "var(--amber)",
                }}
              />
              <span style={{ fontWeight: 600, color: "var(--text)" }}>Simulated Data</span>
            </div>
            {intake
              ? `${eventCount} events from ${intake.summary.sources} log sources. Plain deterministic engine rules.`
              : "Plain deterministic engine rules."}
          </div>
        </div>
      </aside>

      {/* Main Container */}
      <div className="main-content">
        {/* Top bar */}
        <header className="topbar">
          <div style={{ display: "flex", alignItems: "center", gap: "14px", flexWrap: "wrap" }}>
            <span style={{ fontSize: "12px", color: "var(--text-muted)" }}>
              Cases <span style={{ color: "var(--text-dim)" }}>/</span> 0114{" "}
              <span style={{ color: "var(--text-dim)" }}>/</span>{" "}
              <strong style={{ color: "var(--text)" }}>
                {NAV_ITEMS.find((n) => n.href === pathname)?.label || "Investigation"}
              </strong>
            </span>

            {isCaseReady ? (
              <span className={`pill ${confidence >= 70 ? "pill-red" : "pill-amber"}`}>
                {confidence >= 70 ? "High Severity Attack" : "Suspicious Activity"}
              </span>
            ) : isNoChain ? (
              <span className="pill pill-lime">No Attack Chain Found</span>
            ) : (
              <span className="pill pill-lime">Intake Ingested · Clean Alert Rules</span>
            )}
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            {(isCaseReady || isNoChain) && (
              <>
                <button
                  className="btn btn-small"
                  onClick={handleReset}
                  title="Reset to intake preview screen"
                >
                  Start Over
                </button>
                <button
                  className="btn btn-small"
                  onClick={handleRerun}
                  disabled={isRunning || user?.role === "viewer"}
                  title={user?.role === "viewer" ? "Viewers cannot trigger runs" : "Re-run engine pipeline"}
                >
                  {isRunning ? "Running..." : "Re-run Investigation"}
                </button>
              </>
            )}

            {user && (
              <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                <div
                  style={{
                    width: "28px",
                    height: "28px",
                    borderRadius: "50%",
                    background: "var(--panel-raised)",
                    border: "1px solid var(--border-light)",
                    display: "grid",
                    placeItems: "center",
                    fontSize: "11px",
                    fontFamily: "var(--font-mono)",
                    color: "var(--lime)",
                  }}
                >
                  {user.name.slice(0, 2).toUpperCase()}
                </div>
                <div style={{ display: "flex", flexDirection: "column" }}>
                  <span style={{ fontSize: "12px", fontWeight: 600, color: "var(--text)" }}>{user.name}</span>
                  <span className="kicker" style={{ fontSize: "9px", color: "var(--text-dim)" }}>
                    {user.role.toUpperCase()}
                  </span>
                </div>
                <button
                  onClick={logoutUser}
                  className="btn btn-small"
                  style={{ marginLeft: "8px", color: "var(--text-dim)" }}
                  title="Sign out"
                >
                  Logout
                </button>
              </div>
            )}
          </div>
        </header>

        {/* Content View */}
        <main className="page-wrapper">
          {error && (
            <p
              role="alert"
              style={{
                margin: "0 0 16px",
                padding: "10px 14px",
                border: "1px solid var(--red-border)",
                background: "var(--red-soft)",
                color: "var(--red)",
                borderRadius: "6px",
              }}
            >
              {error}
            </p>
          )}
          {children}
        </main>
      </div>
    </div>
  );
}

function NavIcon({ name }: { name: string }) {
  const props = {
    width: "16",
    height: "16",
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: "1.8",
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
  };

  switch (name) {
    case "grid":
      return (
        <svg {...props}>
          <rect x="3" y="3" width="7" height="7" rx="1" />
          <rect x="14" y="3" width="7" height="7" rx="1" />
          <rect x="3" y="14" width="7" height="7" rx="1" />
          <rect x="14" y="14" width="7" height="7" rx="1" />
        </svg>
      );
    case "graph":
      return (
        <svg {...props}>
          <circle cx="6" cy="6" r="3" />
          <circle cx="18" cy="8" r="3" />
          <circle cx="10" cy="18" r="3" />
          <line x1="8.5" y1="7" x2="15.5" y2="7.5" />
          <line x1="7" y1="8.5" x2="9.5" y2="15.5" />
          <line x1="12" y1="16.5" x2="16.5" y2="10" />
        </svg>
      );
    case "list":
      return (
        <svg {...props}>
          <line x1="8" y1="6" x2="21" y2="6" />
          <line x1="8" y1="12" x2="21" y2="12" />
          <line x1="8" y1="18" x2="21" y2="18" />
          <line x1="3" y1="6" x2="3.01" y2="6" />
          <line x1="3" y1="12" x2="3.01" y2="12" />
          <line x1="3" y1="18" x2="3.01" y2="18" />
        </svg>
      );
    case "activity":
      return (
        <svg {...props}>
          <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
        </svg>
      );
    case "file-text":
      return (
        <svg {...props}>
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
          <polyline points="14 2 14 8 20 8" />
          <line x1="16" y1="13" x2="8" y2="13" />
          <line x1="16" y1="17" x2="8" y2="17" />
          <polyline points="10 9 9 9 8 9" />
        </svg>
      );
    default:
      return null;
  }
}
