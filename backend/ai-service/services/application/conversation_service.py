from models.conversation import ConversationalDatasetManager


class ConversationService:
    def __init__(self, manager: ConversationalDatasetManager):
        self._manager = manager

    def list_conversations(self, user_id: str, view: str = "active"):
        return self._manager.get_conversations(user_id, view=view)

    def get_conversation(self, user_id: str, conversation_id: str):
        return self._manager.get_conversation(user_id, conversation_id)

    def soft_delete_all(self, user_id: str) -> int:
        return self._manager.soft_delete_all_conversations(user_id)

    def archive(self, user_id: str, conversation_id: str):
        return self._manager.archive_conversation(user_id, conversation_id)

    def recover(self, user_id: str, conversation_id: str):
        return self._manager.recover_conversation(user_id, conversation_id)

    def soft_delete(self, user_id: str, conversation_id: str):
        return self._manager.soft_delete_conversation(user_id, conversation_id)

    def sync_to_mongo(self, user_id: str, conversation_id: str | None = None):
        return self._manager.sync_from_redis_to_mongo(user_id, conversation_id)

    def update_etl_state(self, user_id: str, conversation_id: str, state: dict):
        return self._manager.update_conversation_etl_state(user_id, conversation_id, state)


conversational_dataset_manager = ConversationalDatasetManager()
conversation_service = ConversationService(conversational_dataset_manager)
