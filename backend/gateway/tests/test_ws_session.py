import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.ws_session import WebSocketSessionStore


class FakeRedis:
    def __init__(self):
        self.data = {}

    def hset(self, key, mapping):
        self.data[key] = dict(mapping)

    def expire(self, key, ttl):
        return True

    def hgetall(self, key):
        return dict(self.data.get(key, {}))

    def delete(self, key):
        self.data.pop(key, None)


class WebSocketSessionStoreTests(unittest.TestCase):
    def test_save_session_round_trips_boolean_values(self):
        store = WebSocketSessionStore()
        fake_redis = FakeRedis()
        store._redis = fake_redis

        store.save_session("conn-1", {"authenticated": True, "user_id": "user-1", "last_activity_at": 123})

        payload = store.get_session("conn-1")
        self.assertIs(payload["authenticated"], True)
        self.assertEqual(payload["user_id"], "user-1")
        self.assertEqual(payload["last_activity_at"], 123)


if __name__ == "__main__":
    unittest.main()
