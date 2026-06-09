import os
import base64
import json
import tempfile
import firebase_admin
from firebase_admin import auth as fb_auth, credentials
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials


def _init_firebase():
    """Initialize Firebase from either a file path (local) or a base64 env var (prod)."""
    if firebase_admin._apps:
        return  # already initialized

    b64 = os.environ.get("FIREBASE_SERVICE_ACCOUNT_B64")
    if b64:
        # Production: decode base64, write to a temp file, point Firebase at it
        decoded = base64.b64decode(b64).decode("utf-8")
        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        tmp.write(decoded)
        tmp.close()
        cred = credentials.Certificate(tmp.name)
    else:
        # Local dev: read from the file path in .env
        path = os.environ["FIREBASE_SERVICE_ACCOUNT_PATH"]
        cred = credentials.Certificate(path)

    firebase_admin.initialize_app(cred)


_init_firebase()
bearer = HTTPBearer(auto_error=False)


async def require_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> str:
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