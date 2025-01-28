from typing import List
import uuid

import chromadb
from openai import AsyncOpenAI

from galadriel_agent.entities import Message


class EmbeddingClient:
    def __init__(self, api_key: str):
        self.client = AsyncOpenAI(api_key=api_key)

    async def embed_text(self, text: str) -> List[float]:
        embedding = await self.client.embeddings.create(
            input=text, model="text-embedding-3-small"
        )
        return embedding.data[0].embedding


class MemoryRepository:
    def __init__(self, client: chromadb.ClientAPI):
        self.client = client

    async def add_memory(self, memory: Message):
        try:
            collection_name = f"{memory.additional_kwargs['author'].replace(' ', '')}-{memory.conversation_id}"
            try:
                collection = self.client.get_collection(collection_name)
            except Exception:
                collection = self.client.create_collection(collection_name)

            collection.add(
                documents=[memory.content],
                metadatas=[
                    {
                        "author": memory.additional_kwargs["author"],
                        "answer": memory.additional_kwargs["agent_response"],
                        "channel_id": str(memory.conversation_id),
                        "timestamp": memory.additional_kwargs["timestamp"],
                        "agent_name": memory.additional_kwargs["agent_name"],
                    }
                ],
                embeddings=(
                    [memory.additional_kwargs["embeddings"]]
                    if memory.additional_kwargs["embeddings"]
                    else None
                ),
                ids=[str(uuid.uuid4())],
            )
        except Exception as e:
            print(e)

    async def get_short_term_memory(
        self, user_id: str, conversation_id: str, limit: int = 10
    ) -> List[Message]:
        try:
            collection = self.client.get_collection(
                f"{user_id.replace(' ', '')}-{conversation_id}"
            )
            result = collection.get(include=["documents", "metadatas"])
            memories = []
            for document, metadata in zip(result["documents"], result["metadatas"]):
                memories.append(
                    Message(
                        content=document,
                        additional_kwargs={
                            "agent_response": metadata["answer"],
                            "author": metadata["author"],
                            "agent_name": metadata["agent_name"],
                            "timestamp": metadata["timestamp"],
                        },
                        conversation_id=metadata["channel_id"],
                        type="memory",
                    )
                )
            # Sort memories by timestamp in descending order and limit the results
            memories.sort(key=lambda x: x.additional_kwargs["timestamp"], reverse=True)
            return self._parse_memory(memories[:limit])
        except Exception as e:
            print(e)
            return []

    async def query_long_term_memory(
        self, user_id: str, conversation_id: str, embedding: List[float], top_k: int = 2
    ) -> List[Message]:
        try:
            collection = self.client.get_collection(
                f"{user_id.replace(' ', '')}-{conversation_id}"
            )
            result = collection.query(
                query_embeddings=[embedding],
                n_results=top_k,
                include=["documents", "metadatas"],
            )
            memories = []
            for document, metadata in zip(result["documents"], result["metadatas"]):
                memories.append(
                    Message(
                        content=document[0],
                        additional_kwargs={
                            "agent_response": metadata[0]["answer"],
                            "author": metadata[0]["author"],
                            "agent_name": metadata[0]["agent_name"],
                            "timestamp": metadata[0]["timestamp"],
                        },
                        conversation_id=metadata[0]["channel_id"],
                        type="memory",
                    )
                )
            return self._parse_memory(memories)
        except Exception as e:
            print(e)
            return []

    def _parse_memory(self, memories: List[Message]) -> List[str]:
        parsed_memories = []
        for memory in memories:
            author = memory.additional_kwargs["author"]
            content = memory.content
            timestamp = memory.additional_kwargs["timestamp"]
            agent_name = memory.additional_kwargs["agent_name"]
            agent_response = memory.additional_kwargs["agent_response"]
            parsed_memories.append(
                f"{author}: {content} ({timestamp})\n" f"{agent_name}: {agent_response}"
            )
        return parsed_memories


# singleton
memory_repository = MemoryRepository(chromadb.Client())
