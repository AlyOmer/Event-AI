import logging

logger = logging.getLogger(__name__)


class MemoryService:
    def __init__(self, api_key: str):
        self.client = None
        if api_key:
            try:
                from mem0 import MemoryClient
                self.client = MemoryClient(api_key=api_key)
            except ImportError:
                logger.warning("mem0ai is not installed — memory features disabled")
            except Exception as e:
                logger.warning("Failed to initialise Mem0 client: %s — memory features disabled", e)
        else:
            logger.warning("No Mem0 API key provided — memory features disabled")

    async def get_user_memory(self, user_id: str) -> str:
        if self.client is None:
            return ""
        try:
            memories = self.client.get_all(user_id=user_id)
            return "\n".join(m["memory"] for m in memories[:10])
        except Exception as e:
            logger.warning("Mem0 unavailable: %s", e)
            return ""

    async def update_user_memory(self, user_id: str, messages: list[dict]) -> None:
        if self.client is None:
            return
        try:
            self.client.add(messages, user_id=user_id)
        except Exception as e:
            logger.warning("Mem0 update failed — skipping: %s", e)

    async def delete_user_memory(self, user_id: str) -> None:
        if self.client is None:
            return
        try:
            self.client.delete_all(user_id=user_id)
        except Exception as e:
            logger.warning("Mem0 delete failed: %s", e)
