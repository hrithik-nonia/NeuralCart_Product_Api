import os
import uuid
from datetime import datetime, timedelta, timezone
import jwt
from dotenv import load_dotenv

load_dotenv()

SECRET = os.getenv("JWT_SECRET")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_MIN = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 15))
REFRESH_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", 7))

class JWTService:
    def _create(self, user_id: str, role: str, token_type: str, expires: timedelta) -> str:
        now = datetime.now(timezone.utc)
        payload = {
            "sub": user_id,          # user ki id
            "role": role,
            "type": token_type,      # "access" ya "refresh"
            "iat": now,
            "exp": now + expires,
            "jti": str(uuid.uuid4()),  # token ki unique id (revoke ke kaam aati hai)
        }
        return jwt.encode(payload, SECRET, algorithm=ALGORITHM)

    def create_access_token(self, user_id: str, role: str) -> str:
        return self._create(user_id, role, "access", timedelta(minutes=ACCESS_MIN))

    def create_refresh_token(self, user_id: str, role: str) -> str:
        return self._create(user_id, role, "refresh", timedelta(days=REFRESH_DAYS))

    def decode(self, token: str, expected_type: str = "access") -> dict:
        # expired ya galat token par jwt.ExpiredSignatureError / InvalidTokenError aayega
        payload = jwt.decode(token, SECRET, algorithms=[ALGORITHM])
        if payload.get("type") != expected_type:
            raise jwt.InvalidTokenError("Wrong token type")
        return payload


jwt_service = JWTService()