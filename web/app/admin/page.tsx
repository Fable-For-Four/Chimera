"use client";

import { useCallback, useEffect, useState } from "react";

import { useApp } from "../../lib/state";
import type { Approval, User } from "../../lib/types";

type Role = User["role"];

const roles: Array<{ value: Role; label: string }> = [
  { value: "viewer", label: "Viewer" },
  { value: "analyst", label: "Analyst" },
  { value: "admin", label: "Admin" },
];

const selectStyle = {
  minWidth: "126px",
  border: "1px solid var(--border-light)",
  background: "var(--panel-raised)",
  padding: "7px 10px",
} as const;

async function responseDetail(response: Response, fallback: string) {
  const body = await response.json().catch(() => null);
  return typeof body?.detail === "string" ? body.detail : fallback;
}

async function apiRequest<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...options,
    credentials: "same-origin",
    headers: options?.body ? { "Content-Type": "application/json", ...options.headers } : options?.headers,
  });

  if (response.status === 401) {
    window.location.assign("/login");
    throw new Error("Sign in to continue");
  }
  if (!response.ok) {
    throw new Error(await responseDetail(response, "The administration request failed"));
  }
  return (await response.json()) as T;
}

export default function AdminPage() {
  const { user } = useApp();
  const [users, setUsers] = useState<User[]>([]);
  const [approvals, setApprovals] = useState<Approval[]>([]);
  const [loading, setLoading] = useState(false);
  const [savingUser, setSavingUser] = useState<number | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const loadAdminData = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [userList, approvalList] = await Promise.all([
        apiRequest<User[]>("/api/users"),
        apiRequest<Approval[]>("/api/approvals"),
      ]);
      setUsers(userList);
      setApprovals(approvalList);
    } catch (loadError: unknown) {
      setError(loadError instanceof Error ? loadError.message : "Administration data could not be loaded");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (user?.role === "admin") void loadAdminData();
  }, [loadAdminData, user?.role]);

  async function changeRole(target: User, role: Role) {
    if (target.role === role) return;
    setSavingUser(target.id);
    setError("");
    setNotice("");
    try {
      const updated = await apiRequest<User>(`/api/users/${target.id}/role`, {
        method: "PATCH",
        body: JSON.stringify({ role }),
      });
      setUsers((current) => current.map((entry) => (entry.id === updated.id ? updated : entry)));
      setNotice(`${updated.name} is now ${updated.role}.`);
    } catch (saveError: unknown) {
      setError(saveError instanceof Error ? saveError.message : "The role could not be changed");
    } finally {
      setSavingUser(null);
    }
  }

  if (!user) {
    return <div className="card">Loading account permissions.</div>;
  }

  if (user.role !== "admin") {
    return (
      <div className="card" style={{ maxWidth: "640px", padding: "32px" }}>
        <span className="pill pill-amber" style={{ alignSelf: "flex-start" }}>Restricted</span>
        <div>
          <h1 style={{ fontSize: "24px", marginBottom: "8px" }}>Admin access required</h1>
          <p style={{ color: "var(--text-muted)" }}>
            Your role cannot manage users. An administrator can change roles and review the approval history.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div style={{ display: "grid", gap: "20px" }}>
      <header className="card-header">
        <div>
          <div className="kicker">Access and accountability</div>
          <h1 style={{ fontSize: "26px", marginTop: "3px" }}>Administration</h1>
          <p style={{ color: "var(--text-muted)", marginTop: "6px" }}>
            Assign case permissions and review who authorized each response action.
          </p>
        </div>
        <button className="btn" type="button" onClick={loadAdminData} disabled={loading}>
          {loading ? "Refreshing..." : "Refresh"}
        </button>
      </header>

      {error && <p role="alert" className="pill pill-red" style={{ justifySelf: "start" }}>{error}</p>}
      {notice && <p role="status" className="pill pill-lime" style={{ justifySelf: "start" }}>{notice}</p>}

      <section className="card" aria-labelledby="users-heading">
        <div className="card-header">
          <div>
            <h2 id="users-heading" className="card-title">User roles</h2>
            <p style={{ color: "var(--text-muted)", fontSize: "12px", marginTop: "3px" }}>
              Role changes take effect on the user&apos;s next API request.
            </p>
          </div>
          <span className="pill">{users.length} accounts</span>
        </div>

        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Email</th>
                <th>Verification</th>
                <th>Role</th>
              </tr>
            </thead>
            <tbody>
              {users.map((entry) => {
                const ownAccount = entry.id === user.id;
                return (
                  <tr key={entry.id}>
                    <td className="primary-cell">
                      {entry.name}
                      {ownAccount && <span style={{ color: "var(--text-dim)", marginLeft: "6px" }}>(you)</span>}
                    </td>
                    <td>{entry.email}</td>
                    <td>
                      <span className={`pill ${entry.verified ? "pill-lime" : "pill-amber"}`}>
                        {entry.verified ? "Confirmed" : "Waiting"}
                      </span>
                    </td>
                    <td>
                      <select
                        aria-label={`Role for ${entry.name}`}
                        value={entry.role}
                        disabled={ownAccount || savingUser === entry.id}
                        onChange={(event) => void changeRole(entry, event.target.value as Role)}
                        style={selectStyle}
                        title={ownAccount ? "Administrators cannot change their own role" : "Change role"}
                      >
                        {roles.map((role) => (
                          <option key={role.value} value={role.value}>{role.label}</option>
                        ))}
                      </select>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {!loading && users.length === 0 && (
          <p style={{ color: "var(--text-muted)" }}>No user accounts were returned by the API.</p>
        )}
      </section>

      <section className="card" aria-labelledby="approvals-heading">
        <div className="card-header">
          <div>
            <h2 id="approvals-heading" className="card-title">Approval history</h2>
            <p style={{ color: "var(--text-muted)", fontSize: "12px", marginTop: "3px" }}>
              This ledger records the person and time behind each approved response.
            </p>
          </div>
          <span className="pill">{approvals.length} approvals</span>
        </div>

        {approvals.length > 0 ? (
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Action</th>
                  <th>Approved by</th>
                  <th>Approved at</th>
                </tr>
              </thead>
              <tbody>
                {approvals.map((approval) => (
                  <tr key={approval.action_id}>
                    <td className="primary-cell">{approval.action_id}</td>
                    <td>{approval.approved_by}</td>
                    <td>{new Date(approval.approved_at).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p style={{ color: "var(--text-muted)" }}>
            No actions have been approved for the current investigation.
          </p>
        )}
      </section>
    </div>
  );
}
