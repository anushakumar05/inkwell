"""
Firebase auth dependency.

Usage in an endpoint:
    @router.get("/something")
    async def something(user_id: str = Depends(require_user)):
        ...

The dependency:
  1. Extracts the Bearer token from the Authorization header.
  2. Verifies it with Firebase.
  3. Returns the Firebase UID (a stable string ID for this user).
  4. Raises 401 if anything is wrong.
"""
import os
import firebase_admin
from firebase_admin import auth as fb_auth, credentials
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# Initialize the Firebase Admin SDK once at module load.
if not firebase_admin._apps:
    cred = credentials.Certificate(os.environ["FIREBASE_SERVICE_ACCOUNT_PATH"])
    firebase_admin.initialize_app(cred)

bearer = HTTPBearer(auto_error=False)


async def require_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> str:
    """Returns the Firebase UID of the authenticated user, or raises 401."""
    if creds is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
        )
    try:
        decoded = fb_auth.verify_id_token(creds.credentials)
        return decoded["uid"]
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )