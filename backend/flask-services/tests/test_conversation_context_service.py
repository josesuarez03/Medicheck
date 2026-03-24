import os
import sys
import unittest


CURRENT_DIR = os.path.dirname(__file__)
SRC_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "..", "src"))
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from services.chatbot.conversation_context_service import ConversationContextService  # noqa: E402


class ConversationContextServiceTests(unittest.TestCase):
    def test_redis_text_accepts_bytes(self):
        self.assertEqual(ConversationContextService._redis_text(b"hola"), "hola")

    def test_redis_text_accepts_plain_str(self):
        self.assertEqual(ConversationContextService._redis_text("hola"), "hola")


if __name__ == "__main__":
    unittest.main()
