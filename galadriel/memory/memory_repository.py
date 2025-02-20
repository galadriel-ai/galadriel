from datetime import datetime
import os
from typing import Dict, List, Optional

from langchain_openai import OpenAIEmbeddings

from galadriel.entities import Message
import faiss
from langchain_community.docstore.in_memory import InMemoryDocstore
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document


class MemoryRepository:
    def __init__(self,
                 api_key: str,
                 short_term_memory_limit: int = 10,
                 embedding_model: Optional[str] = "text-embedding-3-large",
                 agent_name: Optional[str] = "agent",
                 ):
        self.agent_name = agent_name
        self.vector_store = self._initialize_vector_database(embedding_model, api_key)
        self.short_term_memory = []
        self.short_term_memory_limit = short_term_memory_limit

    async def add_memory(self, memory: Message) -> None:
        # Add to short term memory
        self.short_term_memory.append(memory)
        
        # If short term memory is full, move oldest memory to long term
        if len(self.short_term_memory) > self.short_term_memory_limit:
            oldest_memory = self.short_term_memory.pop(0)  # Remove and get oldest memory
            # Add oldest memory to long term memory
            _metadata = oldest_memory.additional_kwargs if oldest_memory.additional_kwargs else {}
            _metadata["conversation_id"] = oldest_memory.conversation_id
            _metadata["date"] = datetime.now().isoformat()
            vector_document = Document(
                page_content=oldest_memory.content,
                metadata=_metadata, # this metadata is used for filtering in query_long_term_memory
            )
            await self.vector_store.aadd_documents(documents=[vector_document], ids=[oldest_memory.id])

    async def get_short_term_memory(self) -> List[Message]:
        return self.short_term_memory

    async def query_long_term_memory(
        self, prompt: str, filter: Optional[Dict[str, str]] = None, top_k: int = 4
    ) -> List[Message]:
        # example filter: {"source": {"$eq": "tweet"}} see filter operators here: https://python.langchain.com/docs/integrations/vectorstores/faiss/
        results = await self.vector_store.asimilarity_search_with_score(
            prompt,
            k=top_k,
            filter=filter,
            score_threshold=0.5
        )
        # filter out results with score less than 0.6
        results = [result for result, _ in results]
        return [Message(**result[0].metadata) for result in results]
    
    def save_data_locally(self) -> None:
        self.vector_store.save_local(f"{self.agent_name}_faiss_index")
    
    def _initialize_vector_database(self, embedding_model: str, api_key: str) -> FAISS:
        embeddings = OpenAIEmbeddings(model=embedding_model, api_key=api_key)
        if os.path.exists(f"{self.agent_name}_faiss_index"):
            return FAISS.load_local(
                f"{self.agent_name}_faiss_index",
                embeddings=embeddings,
                allow_dangerous_deserialization=True
            )
        else:
            index = faiss.IndexFlatL2(len(embeddings.embed_query(" ")))
            return FAISS(
                embedding_function=embeddings,
                index=index,
                docstore=InMemoryDocstore(),
                index_to_docstore_id={},
            )
    
if __name__ == "__main__":
    from dotenv import load_dotenv
    from pathlib import Path
    import asyncio
    
    async def main():
        load_dotenv(dotenv_path=Path(".") / ".env", override=True)
        memory_repository = MemoryRepository(api_key=os.getenv("OPENAI_API_KEY"), agent_name="test_agent")
        for i in range(30):
            await memory_repository.add_memory(Message(content=f"Hello, world! {i}", conversation_id="123"))
        results = await memory_repository.query_long_term_memory("Hello, world!")
        print(results)

    asyncio.run(main())
