import json
import logging
from datetime import datetime
from typing import Any, Dict, List

import boto3
import numpy as np

from config.config import Config
from data.connect import context_redis_client, mongo_db
from models.conversation import ConversationalDatasetManager

logger = logging.getLogger(__name__)
conversation_dataset_manager = ConversationalDatasetManager()


class ConversationContextService:
    KEY_CTX = "chat:ctx:{user_id}:{conversation_id}"
    KEY_SUMMARY = "chat:idx:summary:{user_id}:{conversation_id}"
    KEY_LOOP = "chat:idx:loop:{user_id}:{conversation_id}"

    def __init__(self):
        self.context_ttl = Config.CHAT_CONTEXT_TTL_SECONDS
        self.window_n = Config.CHAT_CONTEXT_WINDOW_N
        self.top_k = Config.CHAT_CONTEXT_TOP_K
        self.embedding_model_id = Config.BEDROCK_EMBEDDING_MODEL_ID
        self.embedding_collection = mongo_db["conversation_embeddings"]
        self.conversation_collection = mongo_db["conversations"]
        self.embedding_collection.create_index([("user_id", 1), ("conversation_id", 1), ("timestamp", -1)])
        self.embedding_collection.create_index([("user_id", 1), ("conversation_id", 1), ("source_turn_id", 1)])

    def _ctx_key(self, user_id: str, conversation_id: str) -> str:
        return self.KEY_CTX.format(user_id=user_id, conversation_id=conversation_id)

    def _summary_key(self, user_id: str, conversation_id: str) -> str:
        return self.KEY_SUMMARY.format(user_id=user_id, conversation_id=conversation_id)

    def _loop_key(self, user_id: str, conversation_id: str) -> str:
        return self.KEY_LOOP.format(user_id=user_id, conversation_id=conversation_id)

    def _embed_text(self, text: str) -> List[float]:
        if not text:
            return []
        client = boto3.client("bedrock-runtime", region_name=Config.AWS_REGION)
        body = json.dumps({"inputText": text})
        response = client.invoke_model(
            modelId=self.embedding_model_id,
            body=body,
            contentType="application/json",
            accept="application/json",
        )
        payload = json.loads(response["body"].read())
        return payload.get("embedding", [])

    @staticmethod
    def _cosine(a: List[float], b: List[float]) -> float:
        if not a or not b:
            return 0.0
        va = np.array(a, dtype="float32")
        vb = np.array(b, dtype="float32")
        denom = np.linalg.norm(va) * np.linalg.norm(vb)
        if denom == 0.0:
            return 0.0
        return float(np.dot(va, vb) / denom)

    def append_turn(self, user_id: str, conversation_id: str, user_msg: str, bot_msg: str, metadata: Dict[str, Any]):
        key = self._ctx_key(user_id, conversation_id)
        turn = {
            "timestamp": datetime.utcnow().isoformat(),
            "user_message": user_msg,
            "assistant_message": bot_msg,
            "metadata": metadata or {},
        }
        context_redis_client.rpush(key, json.dumps(turn))
        context_redis_client.expire(key, self.context_ttl)
        context_redis_client.ltrim(key, -self.window_n, -1)

        summary_key = self._summary_key(user_id, conversation_id)
        previous_summary = context_redis_client.get(summary_key)
        prev_text = previous_summary.decode("utf-8") if previous_summary else ""
        new_summary = f"{prev_text}\nPaciente: {user_msg}\nAsistente: {bot_msg}".strip()
        context_redis_client.set(summary_key, new_summary, ex=self.context_ttl)

        source_turn_id = metadata.get("source_turn_id") if metadata else None
        embedding_input = f"Paciente: {user_msg}\nAsistente: {bot_msg}"
        try:
            embedding = self._embed_text(embedding_input)
            self.embedding_collection.insert_one(
                {
                    "user_id": user_id,
                    "conversation_id": conversation_id,
                    "source_turn_id": source_turn_id,
                    "text": embedding_input,
                    "embedding": embedding,
                    "timestamp": datetime.utcnow(),
                    "metadata": metadata or {},
                }
            )
        except Exception as e:
            logger.warning("Error generating/storing embeddings: %s", e)

    def get_recent_window(self, user_id: str, conversation_id: str, n: int | None = None) -> List[Dict[str, Any]]:
        key = self._ctx_key(user_id, conversation_id)
        n = n or self.window_n
        turns = context_redis_client.lrange(key, -n, -1)
        results: List[Dict[str, Any]] = []
        for t in turns:
            try:
                results.append(json.loads(t))
            except Exception:
                continue
        return results

    def get_semantic_context(self, user_id: str, conversation_id: str, query_text: str, k: int | None = None) -> List[Dict[str, Any]]:
        k = k or self.top_k
        query_embedding = self._embed_text(query_text)
        docs = list(
            self.embedding_collection.find(
                {"user_id": user_id, "conversation_id": conversation_id},
                {"text": 1, "embedding": 1, "metadata": 1, "source_turn_id": 1, "timestamp": 1},
            ).sort("timestamp", -1).limit(100)
        )
        scored = []
        for d in docs:
            score = self._cosine(query_embedding, d.get("embedding", []))
            if score > 0:
                scored.append({"score": score, "text": d.get("text", ""), "metadata": d.get("metadata", {}), "source_turn_id": d.get("source_turn_id")})
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:k]

    def get_global_semantic_context(self, user_id: str, query_text: str, current_conversation_id: str | None = None, k: int | None = None) -> List[Dict[str, Any]]:
        k = k or self.top_k
        query_embedding = self._embed_text(query_text)
        query = {"user_id": user_id}
        if current_conversation_id:
            query["conversation_id"] = {"$ne": current_conversation_id}
        docs = list(
            self.embedding_collection.find(
                query,
                {"text": 1, "embedding": 1, "metadata": 1, "source_turn_id": 1, "timestamp": 1, "conversation_id": 1},
            ).sort("timestamp", -1).limit(200)
        )
        scored = []
        for d in docs:
            score = self._cosine(query_embedding, d.get("embedding", []))
            if score > 0:
                scored.append(
                    {
                        "score": score,
                        "text": d.get("text", ""),
                        "metadata": d.get("metadata", {}),
                        "source_turn_id": d.get("source_turn_id"),
                        "conversation_id": d.get("conversation_id"),
                    }
                )
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:k]

    def get_global_patient_context_mongo(self, user_id: str, current_conversation_id: str | None = None, max_conversations: int = 5) -> Dict[str, Any]:
        query = {
            "user_id": user_id,
            "$or": [{"lifecycle_status": {"$exists": False}}, {"lifecycle_status": {"$ne": "deleted"}}],
        }
        if current_conversation_id:
            query["_id"] = {"$ne": current_conversation_id}

        conversations = list(
            self.conversation_collection.find(
                query,
                {"_id": 1, "triaje_level": 1, "symptoms": 1, "pain_scale": 1, "timestamp": 1, "messages": 1, "medical_context": 1},
            ).sort("timestamp", -1).limit(max_conversations)
        )
        compact = []
        for conv in conversations:
            conv = conversation_dataset_manager._serialize_conversation_record(conv)
            msgs = conv.get("messages", [])[-4:]
            compact.append(
                {
                    "conversation_id": str(conv.get("_id")),
                    "triaje_level": conv.get("triaje_level"),
                    "symptoms": conv.get("symptoms", []),
                    "pain_scale": conv.get("pain_scale"),
                    "timestamp": str(conv.get("timestamp")),
                    "recent_messages": msgs,
                    "medical_context": conv.get("medical_context", {}),
                }
            )
        return {"recent_conversations": compact}

    def _extract_question_intents(self, assistant_message: str) -> List[str]:
        intents = []
        for part in assistant_message.split("?"):
            cleaned = "".join(ch.lower() for ch in part if ch.isalnum() or ch.isspace()).strip()
            if cleaned:
                intents.append(" ".join(cleaned.split()[:8]))
        return intents[:2]

    def detect_loop(self, user_id: str, conversation_id: str, assistant_message: str) -> bool:
        key = self._loop_key(user_id, conversation_id)
        previous = context_redis_client.get(key)
        current_intents = self._extract_question_intents(assistant_message)
        payload = {"last": assistant_message, "last_intents": current_intents, "count": 1}
        if previous:
            try:
                data = json.loads(previous)
                same_text = data.get("last", "").strip().lower() == assistant_message.strip().lower()
                prev_intents = data.get("last_intents", [])
                same_intent = bool(set(prev_intents) & set(current_intents))
                if same_text or same_intent:
                    payload["count"] = int(data.get("count", 1)) + 1
            except Exception:
                pass
        context_redis_client.set(key, json.dumps(payload), ex=self.context_ttl)
        return payload["count"] >= 2

    def get_summary(self, user_id: str, conversation_id: str) -> str:
        raw = context_redis_client.get(self._summary_key(user_id, conversation_id))
        return raw.decode("utf-8") if raw else ""

    def build_prompt_context(
        self,
        *,
        user_id: str,
        conversation_id: str,
        user_input: str,
        current_context: Dict[str, Any],
        missing_questions: List[str],
        questions_selected: List[str],
        postgres_context: Dict[str, Any] | None = None,
        triage_level: str | None,
    ) -> Dict[str, Any]:
        recent_turns = self.get_recent_window(user_id, conversation_id, self.window_n)
        semantic = self.get_semantic_context(user_id, conversation_id, user_input, self.top_k)
        global_semantic = self.get_global_semantic_context(
            user_id=user_id,
            query_text=user_input,
            current_conversation_id=conversation_id,
            k=self.top_k,
        )
        global_mongo = self.get_global_patient_context_mongo(
            user_id=user_id,
            current_conversation_id=conversation_id,
        )
        return {
            **(current_context or {}),
            "user_input": user_input,
            "conversation_summary": self.get_summary(user_id, conversation_id),
            "recent_turns": recent_turns,
            "semantic_context": semantic,
            "global_semantic_context": global_semantic,
            "global_mongo_context": global_mongo,
            "postgres_context": postgres_context or {},
            "missing_questions": missing_questions or [],
            "questions_selected": questions_selected or [],
            "triage_level": triage_level,
            "interaction_style": "turn_based",
            "max_questions_per_turn": 2,
            "intro_mode": "brief_context_plus_one_question",
        }
