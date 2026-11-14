"use client";

import React from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useApp } from "../lib/state";
import { logoutUser } from "../lib/api";
import { timeWindow } from "../lib/time";

const NAV_ITEMS = [
  { href: "/", label: "Overview", icon: "grid" },
  { href: "/graph", label: "Attack graph", icon: "graph" },
  { href: "/logs", label: "Evidence log", icon: "list" },
  { href: "/stress", label: "Stress test", icon: "activity" },
  { href: "/report", label: "Report", icon: "file-text" },
];

export function Shell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, intake, caseData, source, isRunning, runInvestigation, resetCase, error } = useApp();
  const eventCount = intake?.summary.events.toLocaleString() ?? "";
  const upload = source?.kind === "upload" ? source : null;

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
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark" aria-hidden="true">
            <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.6">
              <line x1="2" y1="4" x2="9" y2="4" />
              <line x1="5" y1="8" x2="12" y2="8" />
              <line x1="8" y1="12" x2="14" y2="12" />
            </svg>
          </span>
          <div className="brand-text">
            <div className="brand-name">Chimera</div>
            <div className="brand-sub">Log investigation</div>
          </div>
        </div>

        <div className="sidebar-card case-card">
          <div className="case-title">
            <span>Case 0114</span>
            <span className="case-org">Acme Corp</span>
          </div>
          <div className="case-state">
            <span
              className="status-dot"
              style={{
                background: isCaseReady ? "var(--red)" : isNoChain ? "var(--accent)" : "var(--text-dim)",
              }}
            />
            {isCaseReady ? "Breach under investigation" : isNoChain ? "Closed, no chain found" : "Waiting for a run"}
          </div>
          {intake && <div className="case-window">{timeWindow(intake.volume)}</div>}
        </div>

        <div className="nav-heading sidebar-card">Investigation</div>
        <nav className="nav">
          {NAV_ITEMS.map((item) => {
            const active = pathname === item.href;
            const disabled = !isCaseReady && item.href !== "/" && item.href !== "/logs";

            return (
              <Link
                key={item.href}
                href={disabled ? "#" : item.href}
                className={`nav-link${active ? " active" : ""}${disabled ? " disabled" : ""}`}
                aria-current={active ? "page" : undefined}
                aria-disabled={disabled || undefined}
                tabIndex={disabled ? -1 : undefined}
                onClick={disabled ? (e) => e.preventDefault() : undefined}
              >
                <span className="nav-link-main">
                  <NavIcon name={item.icon} />
                  <span className="nav-label">{item.label}</span>
                </span>
                {item.href === "/logs" && <span className="nav-count">{eventCount}</span>}
                {item.href === "/graph" && isCaseReady && (
                  <span className="nav-count nav-count-accent">{caseData?.chain.length}</span>
                )}
              </Link>
            );
          })}
        </nav>

        <div className="sidebar-card sidebar-foot">
          <span className="status-dot" style={{ background: upload ? "var(--accent)" : "var(--amber)" }} />
          <span>
            {upload ? "Uploaded logs" : "Simulated data"}
            {upload ? (
              <span className="sidebar-foot-sub">
                {upload.name}, {upload.events.toLocaleString()} lines read
              </span>
            ) : (
              intake && (
                <span className="sidebar-foot-sub">
                  {eventCount} events from {intake.summary.sources} sources
                </span>
              )
            )}
          </span>
        </div>
      </aside>

      <div className="main-content">
        <header className="topbar">
          <div className="topbar-left">
            <nav className="crumbs" aria-label="Breadcrumb">
              <span>Cases</span>
              <span className="crumb-sep">/</span>
              <span className="mono">0114</span>
              <span className="crumb-sep">/</span>
              <strong>{NAV_ITEMS.find((n) => n.href === pathname)?.label || "Investigation"}</strong>
            </nav>

            {isCaseReady ? (
              <span className={`pill ${confidence >= 70 ? "pill-red" : "pill-amber"}`}>
                {confidence >= 70 ? "High severity" : "Suspicious activity"}
              </span>
            ) : isNoChain ? (
              <span className="pill pill-lime">No attack chain</span>
            ) : (
              <span className="pill">Not run yet</span>
            )}
          </div>

          <div className="topbar-right">
            {(isCaseReady || isNoChain) && (
              <>
                <button className="btn btn-small btn-ghost" onClick={handleReset} title="Go back to the intake screen">
                  Start over
                </button>
                <button
                  className="btn btn-small"
                  onClick={handleRerun}
                  disabled={isRunning || user?.role === "viewer"}
                  title={user?.role === "viewer" ? "Viewers cannot start a run" : "Run the engine again"}
                >
                  {isRunning ? "Running..." : "Re-run investigation"}
                </button>
              </>
            )}

            {user && (
              <div className="user-chip">
                <span className="user-avatar" aria-hidden="true">
                  {user.name.slice(0, 2).toUpperCase()}
                </span>
                <span className="user-meta">
                  <span className="user-name">{user.name}</span>
                  <span className="user-role">{user.role}</span>
                </span>
                <button onClick={logoutUser} className="btn btn-small btn-ghost" title="Sign out">
                  Sign out
                </button>
              </div>
            )}
          </div>
        </header>

        <main className="page-wrapper">
          {error && (
            <p role="alert" className="shell-error">
              {error}
            </p>
          )}
          {upload && upload.unparsed > 0 && (
            <p role="status" className="shell-note">
              {upload.unparsed.toLocaleString()} {upload.unparsed === 1 ? "line" : "lines"} in {upload.name}{" "}
              could not be read and {upload.unparsed === 1 ? "is" : "are"} not in this case.
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
    strokeLinecap: "square" as const,
    strokeLinejoin: "miter" as const,
  };

  switch (name) {
    case "grid":
      return (
        <svg {...props}>
          <rect x="3" y="3" width="7" height="7" />
          <rect x="14" y="3" width="7" height="7" />
          <rect x="3" y="14" width="7" height="7" />
          <rect x="14" y="14" width="7" height="7" />
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
