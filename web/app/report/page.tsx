"use client";

import Link from "next/link";

import { IncidentReport } from "../../components/IncidentReport";
import { useApp } from "../../lib/state";

export default function ReportPage() {
  const { user } = useApp();

  return (
    <div style={{ display: "grid", gap: "14px" }}>
      {user?.role === "admin" && (
        <div style={{ display: "flex", justifyContent: "flex-end" }}>
          <Link className="btn" href="/admin">Open administration</Link>
        </div>
      )}
      <IncidentReport />
    </div>
  );
}
