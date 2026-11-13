from fastapi import Depends, HTTPException

from api.auth import current_user

ROLE_PERMISSIONS = {
    "viewer": {"case:read"},
    "analyst": {"case:read", "case:run", "action:approve"},
    "admin": {"case:read", "case:run", "action:approve", "user:manage"},
}

DEFAULT_ROLE = "viewer"


def require(permission):
    def check(user=Depends(current_user)):
        if user["email_verified_at"] is None:
            raise HTTPException(status_code=403, detail="Confirm your email first")
        if permission not in ROLE_PERMISSIONS.get(user["role"], set()):
            raise HTTPException(status_code=403, detail="Your role cannot do this")
        return user

    return check
