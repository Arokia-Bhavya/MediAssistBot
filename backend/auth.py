from datetime import datetime, timedelta
from jose import JWTError, jwt
from config import SECRET_KEY, TOKEN_EXPIRE_HOURS, DEMO_USERS

ALGORITHM = "HS256"


def authenticate_user(username: str, password: str) -> dict | None:
    """Check credentials and return user dict if valid."""
    user = DEMO_USERS.get(username)
    if not user:
        return None
    if user["password"] != password:
        return None
    return {"username": username, "role": user["role"]}


def create_token(username: str, role: str) -> str:
    """Create a JWT token with role embedded."""
    payload = {
        "sub": username,
        "role": role,
        "exp": datetime.utcnow() + timedelta(hours=TOKEN_EXPIRE_HOURS),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict | None:
    """Decode and validate JWT token. Returns payload or None."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None