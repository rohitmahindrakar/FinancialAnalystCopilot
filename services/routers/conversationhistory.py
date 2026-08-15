from database.connection import DatabaseConnection
from database.crud import ConversationHistoryDAO
import json
from services.api_schemas import ConversationHistoryCreate, ConversationHistoryUpdate
from services.dependencies import get_database_connection
from services.dependencies import get_database_connection
from typing import Any

from agents.memory.session import SessionABC
from agents.items import TResponseInputItem

class ConversationHistorySession(SessionABC):
    def __init__(self, conversation_id: str, db: DatabaseConnection = get_database_connection()):
        self.conversation_id = conversation_id
        self.db = db
        self.dao = ConversationHistoryDAO(db)

    def _get_item_type(self, item: dict) -> str | None:
        if "type" in item:
            return item["type"]
        if "role" in item:
            return "message"
        return None

    def _get_role(self, item: dict) -> str | None:
        return item.get("role")

    async def get_items(self) -> list[TResponseInputItem]:
        """Retrieve the conversation history for the given conversation_id."""
        records = await self.dao.get_by_conversation_id(self.conversation_id)
        return [
            json.loads(record["item_json"])
            if isinstance(record["item_json"], str)
            else record["item_json"]
            for record in records
        ]

    async def add_items(
        self,
        items: list[TResponseInputItem],
    ) -> None:

        # Add new items to the conversation history for the given conversation_id.
        for item in items:
            item_type = self._get_item_type(item)
            role = self._get_role(item)
            conversation_history_create = ConversationHistoryCreate(
                conversation_id=self.conversation_id,
                sequence_no= await self.dao.get_next_sequence_no(self.conversation_id),
                item_type=item_type,
                role= role if role else item_type,
                item_json=json.dumps(item),
                #created_at=item.created_at
            )
            await self.dao.create_from_model(conversation_history_create.model_dump())

    async def pop_item(
        self,
    ) -> TResponseInputItem | None:

        return await self.dao.delete_most_recent_by_conversation_id(
            conversation_id=self.conversation_id,
        )

    async def clear_session(self) -> None:
        await self.dao.delete_by_conversation_id(
            conversation_id=self.conversation_id,
        )
    
async def create_conversation_history(payload: ConversationHistoryCreate, db: DatabaseConnection = get_database_connection()) -> Any:
    dao = ConversationHistoryDAO(db)
    conversation_id = dao.create_from_model(payload)
    return {"conversation_id": conversation_id}

async def update_conversation_history(
    conversation_id: int,
    payload: ConversationHistoryUpdate,
    db: DatabaseConnection = get_database_connection(),
) -> Any:
    dao = ConversationHistoryDAO(db)
    if not dao.update(conversation_id, payload):
        raise Exception("Conversation not found")
    return {"conversation_id": conversation_id}