import chromadb
from typing import List, Optional
from pydantic import BaseModel, Field
from uuid import uuid4
from openai import AsyncOpenAI
from datetime import datetime


class Memory(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    message: str
    agent_response: str
    channel_id: int
    author: str
    agent_name: str
    embedding: Optional[List[float]] = None
    timestamp: datetime = Field(default_factory=datetime.now)

    def __str__(self):
        return f"{self.author}: {self.message} - {self.agent_name}: {self.agent_response} - {self.timestamp}"
    
    def to_dict(self):
        return {
            "id": self.id,
            "message": self.message,
            "agent_response": self.agent_response,
            "channel_id": self.channel_id,
            "author": self.author,
            "agent_name": self.agent_name,
            "timestamp": self.timestamp
        }


class EmbeddingClient:
    def __init__(self, api_key: str):
        self.client = AsyncOpenAI(api_key=api_key)

    async def embed_text(self, text: str) -> List[float]:
        embedding = await self.client.embeddings.create(input=text, model="text-embedding-3-small")
        return embedding.data[0].embedding


class MemoryRepository():
    def __init__(self, client: chromadb.Client):
        self.client = client
    
    async def add_memory(self, user_id: str, memory: Memory, conversation_id: str = None):
        try:
            collection_name = f"{user_id}-{conversation_id}" if conversation_id else user_id
            try:
                collection = self.client.get_collection(collection_name)
            except Exception:
                collection = self.client.create_collection(collection_name)
                
            collection.add(
                documents=[memory.message],
                metadatas=[{
                    "author": memory.author,
                    "answer": memory.agent_response,
                    "channel_id": str(memory.channel_id),
                    "timestamp": memory.timestamp.isoformat(),
                    "agent_name": memory.agent_name
                }],
                embeddings=[memory.embedding] if memory.embedding else None,
                ids=[memory.id]
            )
        except Exception as e:
            print(e)

    async def get_short_term_memory(self, user_id: str, conversation_id: str, limit: int = 10) -> List[Memory]:
        try:
            collection = self.client.get_collection(f"{user_id}-{conversation_id}")
            result = collection.get(
                include=["documents", "metadatas"]
            )
            memories = []
            for document, metadata in zip(result["documents"], result["metadatas"]):
                memories.append(Memory(
                    message=document,
                    agent_response=metadata["answer"],
                    author=metadata["author"],
                    agent_name=metadata["agent_name"],
                    timestamp=datetime.fromisoformat(metadata["timestamp"]),
                    embedding=None, # no need to return the embedding
                    channel_id=metadata["channel_id"]
                ))
            # Sort memories by timestamp in descending order and limit the results
            memories.sort(key=lambda x: x.timestamp, reverse=True)
            return memories[:limit]
        except Exception as e:
            print(e)
            return []
    
    async def query_long_term_memory(self, user_id: str, conversation_id: str, embedding: List[float], top_k: int = 2) -> List[Memory]:
        try:
            collection = self.client.get_collection(f"{user_id}-{conversation_id}")
            result = collection.query(
                query_embeddings=[embedding],
                n_results=top_k,
                include=["documents", "metadatas"]
            )
            memories = []
            for document, metadata in zip(result["documents"], result["metadatas"]):
                memories.append(Memory(
                    message=document[0],
                    agent_response=metadata[0]["answer"],
                    author=metadata[0]["author"],
                    agent_name=metadata[0]["agent_name"],
                    timestamp=datetime.fromisoformat(metadata[0]["timestamp"]),
                    embedding=None, # no need to return the embedding
                    channel_id=metadata[0]["channel_id"]
                ))
            return memories
        except Exception as e:
            print(e)
            return []

# singleton
memory_repository = MemoryRepository(chromadb.Client())
