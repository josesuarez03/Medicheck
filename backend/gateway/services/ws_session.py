import json
import os
import time
from typing import Any

import redis


REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")
REDIS_DB_CONTEXT = int(os.getenv("REDIS_DB_CONTEXT", "2"))
REDIS_DB_EPHEMERAL = int(os.getenv("REDIS_DB_EPHEMERAL", "6"))
WS_AUTH_TTL_SECONDS = int(os.getenv("WS_AUTH_TTL_SECONDS", "3600"))
WS_RATE_LIMIT_WINDOW_SECONDS = int(os.getenv("WS_RATE_LIMIT_WINDOW_SECONDS", "60"))
WS_RATE_LIMIT_MAX_MESSAGES = int(os.getenv("WS_RATE_LIMIT_MAX_MESSAGES", "20"))

_MEMORY_SESSIONS: dict[str, dict[str, Any]] = {}
_MEMORY_COUNTERS: dict[str, tuple[int, int]] = {}


class WebSocketSessionStore:
    def __init__(self) -> None:
        self._redis = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            password=REDIS_PASSWORD,
            db=REDIS_DB_CONTEXT,
            decode_responses=True,
            socket_connect_timeout=1,
            socket_timeout=1,
        )
        self._ephemeral_redis = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            password=REDIS_PASSWORD,
            db=REDIS_DB_EPHEMERAL,
            decode_responses=True,
            socket_connect_timeout=1,
            socket_timeout=1,
        )

    def _session_key(self, connection_id: str) -> str:
        return f"ws:session:{connection_id}"

    def _rate_key(self, identity: str) -> str:
        bucket = int(time.time() // WS_RATE_LIMIT_WINDOW_SECONDS)
        return f"gateway:ws:rate:{identity}:{bucket}"

    def _write_memory(self, connection_id: str, payload: dict[str, Any]) -> None:
        _MEMORY_SESSIONS[connection_id] = dict(payload)

    def _read_memory(self, connection_id: str) -> dict[str, Any]:
        return dict(_MEMORY_SESSIONS.get(connection_id, {}))

    def save_session(self, connection_id: str, payload: dict[str, Any]) -> None:
        serialized = {key: json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else str(value) for key, value in payload.items()}
        try:
            self._redis.hset(self._session_key(connection_id), mapping=serialized)
            self._redis.expire(self._session_key(connection_id), WS_AUTH_TTL_SECONDS)
        except Exception:
            self._write_memory(connection_id, payload)

    def get_session(self, connection_id: str) -> dict[str, Any]:
        try:
            raw = self._redis.hgetall(self._session_key(connection_id))
        except Exception:
            return self._read_memory(connection_id)
        if not raw:
            return self._read_memory(connection_id)
        payload: dict[str, Any] = {}
        for key, value in raw.items():
            try:
                payload[key] = json.loads(value)
            except Exception:
                payload[key] = value
        return payload

    def delete_session(self, connection_id: str) -> None:
        try:
            self._redis.delete(self._session_key(connection_id))
        except Exception:
            _MEMORY_SESSIONS.pop(connection_id, None)
        else:
            _MEMORY_SESSIONS.pop(connection_id, None)

    def create_pending_session(self, *, connection_id: str, client_host: str | None) -> dict[str, Any]:
        payload = {
            "connection_id": connection_id,
            "client_host": client_host or "",
            "authenticated": False,
            "user_id": "",
            "jwt_token": "",
            "last_conversation_id": "",
            "connected_at": int(time.time()),
            "last_activity_at": int(time.time()),
        }
        self.save_session(connection_id, payload)
        return payload

    def mark_authenticated(self, *, connection_id: str, user_id: str, jwt_token: str) -> dict[str, Any]:
        session = self.get_session(connection_id)
        session.update(
            {
                "authenticated": True,
                "user_id": user_id,
                "jwt_token": jwt_token,
                "authenticated_at": int(time.time()),
                "last_activity_at": int(time.time()),
            }
        )
        self.save_session(connection_id, session)
        return session

    def update_activity(self, *, connection_id: str, conversation_id: str | None = None) -> dict[str, Any]:
        session = self.get_session(connection_id)
        session["last_activity_at"] = int(time.time())
        if conversation_id:
            session["last_conversation_id"] = conversation_id
        self.save_session(connection_id, session)
        return session

    def check_rate_limit(self, *, identity: str) -> bool:
        key = self._rate_key(identity)
        try:
            current = self._ephemeral_redis.incr(key)
            if current == 1:
                self._ephemeral_redis.expire(key, WS_RATE_LIMIT_WINDOW_SECONDS)
            return int(current) <= WS_RATE_LIMIT_MAX_MESSAGES
        except Exception:
            count, bucket = _MEMORY_COUNTERS.get(key, (0, int(time.time() // WS_RATE_LIMIT_WINDOW_SECONDS)))
            current_bucket = int(time.time() // WS_RATE_LIMIT_WINDOW_SECONDS)
            if bucket != current_bucket:
                count = 0
                bucket = current_bucket
            count += 1
            _MEMORY_COUNTERS[key] = (count, bucket)
            return count <= WS_RATE_LIMIT_MAX_MESSAGES
