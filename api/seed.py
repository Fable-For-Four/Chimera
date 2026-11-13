import os

from api.auth import MAX_PASSWORD_BYTES, hash_password
from api.db import connect, init_db, now_iso

DEFAULT_SEED_PASSWORD = "chimera-demo-1"

SEED_USERS = [
    ("admin@acme.test", "Admin", "admin"),
    ("analyst@acme.test", "Analyst", "analyst"),
    ("viewer@acme.test", "Viewer", "viewer"),
]


def seed(conn, password):
    created = []
    for email, name, role in SEED_USERS:
        exists = conn.execute("SELECT 1 FROM users WHERE email = ?", (email,)).fetchone()
        if exists:
            continue
        stamp = now_iso()
        conn.execute(
            "INSERT INTO users (email, name, password_hash, role, email_verified_at, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (email, name, hash_password(password), role, stamp, stamp),
        )
        created.append(email)
    conn.commit()
    return created


def main():
    password = os.environ.get("SEED_PASSWORD") or DEFAULT_SEED_PASSWORD
    if not 8 <= len(password.encode()) <= MAX_PASSWORD_BYTES:
        raise SystemExit("SEED_PASSWORD must be 8 to 72 bytes long")
    init_db()
    conn = connect()
    try:
        created = seed(conn, password)
    finally:
        conn.close()
    print(f"Seeded {len(created)} demo accounts" if created else "Demo accounts already exist")


if __name__ == "__main__":
    main()
