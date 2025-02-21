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
                 short_term_memory_limit: int = 3, # Todo: revert to 20, this is just for testing
                 embedding_model: Optional[str] = "text-embedding-3-large",
                 agent_name: Optional[str] = "agent",
                 ):
        self.agent_name = agent_name
        self.vector_store = self._initialize_vector_database(embedding_model, api_key)
        self.short_term_memory = []
        self.short_term_memory_limit = short_term_memory_limit

    async def add_memory(self, request: Message, response: Message) -> None:
        memory = Message(content=f"User: {request.content}\n Assistant: {response.content}")
        memory.conversation_id = request.conversation_id
        memory.additional_kwargs = request.additional_kwargs if request.additional_kwargs else {}
        memory.additional_kwargs["date"] = datetime.now().strftime("%Y-%m-%d %H:%M")

        # 1. Add to short term memory
        self.short_term_memory.append(memory)
        
        # 2. If short term memory is full, move oldest memory to long term
        if len(self.short_term_memory) > self.short_term_memory_limit:
            oldest_memory = self.short_term_memory.pop(0)  # Remove and get oldest memory
            # Add oldest memory to long term memory
            _metadata = oldest_memory.additional_kwargs if oldest_memory.additional_kwargs else {}
            _metadata["conversation_id"] = oldest_memory.conversation_id
            _metadata["date"] = oldest_memory.additional_kwargs["date"]
            vector_document = Document(
                page_content=oldest_memory.content,
                metadata=_metadata, # this metadata is used for filtering in query_long_term_memory
            )
            await self.vector_store.aadd_documents(documents=[vector_document], ids=[oldest_memory.id])
    
    async def get_memories(self, prompt: str, top_k: int = 2, filter: Optional[Dict[str, str]] = None) -> str:
        template = """recent messages: \n{short_term_memory} \nlong term memories that might be relevant: \n{long_term_memory}"""
        short_term = await self._get_short_term_memory()
        long_term = await self._query_long_term_memory(prompt, top_k, filter)
        
        return template.format(
            short_term_memory="\n".join([
                f"[{memory.additional_kwargs['date']}]\n {memory.content}" 
                for memory in short_term
            ]),
            long_term_memory="\n".join([
                f"[{memory.additional_kwargs['date']}]\n {memory.content}" 
                for memory in long_term
            ])
        )
    
    async def _get_short_term_memory(self) -> List[Message]:
        return self.short_term_memory

    async def _query_long_term_memory(
        self, prompt: str, top_k: int, filter: Optional[Dict[str, str]] = None) -> List[Message]:
        # example filter: {"source": {"$eq": "tweet"}} see filter operators here: https://python.langchain.com/docs/integrations/vectorstores/faiss/
        results = await self.vector_store.asimilarity_search_with_score(
            query=prompt,
            k=top_k,
            filter=filter,
            #search_type="similarity_score_threshold",
            #score_threshold=0.6 # lower is closer match, higher is more different
        )
        messages = []
        for result in results:
            message = Message(content=result[0].page_content,
                              conversation_id=result[0].metadata.get("conversation_id", None),
                              additional_kwargs=result[0].metadata)
            messages.append(message)
        return messages
    
    def save_data_locally(self, file_name: str) -> None:
        self.vector_store.save_local(file_name)
    
    def _initialize_vector_database(self, embedding_model: str, api_key: str, file_name: Optional[str] = None) -> FAISS:
        embeddings = OpenAIEmbeddings(model=embedding_model, api_key=api_key)
        if file_name:
            if os.path.exists(file_name):
                return FAISS.load_local(
                    file_name,
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
