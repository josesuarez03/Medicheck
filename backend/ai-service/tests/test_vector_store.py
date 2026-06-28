import pathlib
import sys
import unittest
from unittest.mock import patch


ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.vector_store import VectorStore


class VectorStoreTests(unittest.TestCase):
    def setUp(self):
        VectorStore._schema_ready = False

    def test_ensure_ready_returns_false_when_disabled(self):
        store = VectorStore()
        store.enabled = False
        self.assertFalse(store.ensure_ready())

    def test_ensure_ready_marks_schema_as_ready(self):
        store = VectorStore()
        store.enabled = True

        class DummyConnection:
            def close(self):
                return None

        def fake_ensure_schema_ready(_connection):
            VectorStore._schema_ready = True

        with patch("services.vector_store.psycopg.connect", return_value=DummyConnection()), patch(
            "services.vector_store.register_vector", return_value=None
        ), patch.object(store, "_ensure_schema_ready", side_effect=fake_ensure_schema_ready):
            self.assertTrue(store.ensure_ready())

        self.assertEqual(store.status(), {"enabled": True, "schema_ready": True})


if __name__ == "__main__":
    unittest.main()
