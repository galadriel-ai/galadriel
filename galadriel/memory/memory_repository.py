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
    """Repository for managing short-term and long-term memory storage for an agent.

    Uses a vector database for long-term memory storage and a list for short-term memory.
    Automatically moves memories from short-term to long-term storage when the short-term limit is reached.
    """

    def __init__(
        self,
        api_key: str,
        short_term_memory_limit: int = 20,
        embedding_model: Optional[str] = "text-embedding-3-large",
        agent_name: Optional[str] = "agent",
        memory_folder_path: Optional[str] = None,
    ):
        """Initialize the memory repository.

        Args:
            api_key: OpenAI API key for embeddings
            short_term_memory_limit: Maximum number of memories to keep in short-term memory
            embedding_model: Name of the OpenAI embedding model to use
            agent_name: Name identifier for the agent using this repository
            memory_folder_path: Path to the folder to load the vector store from
        """
        self.agent_name = agent_name
        self.api_key = api_key
        self.embedding_model = embedding_model
        self.memory_folder_path = memory_folder_path
        self.vector_store = self._initialize_vector_database(embedding_model, api_key, memory_folder_path)  # type: ignore
        self.short_term_memory = []  # type: ignore
        self.short_term_memory_limit = short_term_memory_limit

    async def add_memory(self, request: Message, response: Message) -> None:
        """Add a new memory from a request-response interaction.

        Creates a memory combining the request and response, stores it in short-term memory,
        and moves the oldest memory to long-term storage if the short-term limit is exceeded.

        Args:
            request: The user's request message
            response: The assistant's response message
        """
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
                metadata=_metadata,  # this metadata is used for filtering in query_long_term_memory
            )
            await self.vector_store.aadd_documents(documents=[vector_document], ids=[oldest_memory.id])

    async def get_memories(self, prompt: str, top_k: int = 2, filter: Optional[Dict[str, str]] = None) -> str:
        """Retrieve relevant memories based on a prompt.

        Gets all short-term memories and searches long-term memory for relevant matches.
        Returns memories formatted with timestamps.

        Args:
            prompt: Query string to search memories
            top_k: Number of long-term memories to retrieve
            filter: Optional filter criteria for long-term memory search

        Returns:
            Formatted string containing recent and relevant memories
        """
        template = """recent messages: \n{short_term_memory} \nlong term memories that might be relevant: \n{long_term_memory}"""
        short_term = await self._get_short_term_memory()
        long_term = await self._query_long_term_memory(prompt, top_k, filter)

        return template.format(
            short_term_memory="\n".join(
                [f"[{memory.additional_kwargs['date']}]\n {memory.content}" for memory in short_term]  # type: ignore
            ),
            long_term_memory="\n".join(
                [f"[{memory.additional_kwargs['date']}]\n {memory.content}" for memory in long_term]  # type: ignore
            ),
        )

    async def _get_short_term_memory(self) -> List[Message]:
        """Get all memories currently in short-term storage.

        Returns:
            List of Message objects from short-term memory
        """
        return self.short_term_memory

    async def _query_long_term_memory(
        self, prompt: str, top_k: int, filter: Optional[Dict[str, str]] = None
    ) -> List[Message]:
        """Search long-term memory for relevant memories.

        Args:
            prompt: Query string to search memories
            top_k: Number of memories to retrieve
            filter: Optional filter criteria (e.g. {"source": {"$eq": "tweet"}})

        Returns:
            List of relevant Message objects from long-term memory
        """
        # example filter: {"source": {"$eq": "tweet"}} see filter operators here: https://python.langchain.com/docs/integrations/vectorstores/faiss/
        results = await self.vector_store.asimilarity_search_with_score(
            query=prompt,
            k=top_k,
            filter=filter,
        )
        messages = []
        for result in results:
            message = Message(
                content=result[0].page_content,
                conversation_id=result[0].metadata.get("conversation_id", None),
                additional_kwargs=result[0].metadata,
            )
            messages.append(message)
        return messages

    def save_data_locally(self, folder_path: str) -> None:
        """Save the vector store to a local folder.

        Args:
            file_name: Path where the vector store should be saved
        """
        self.vector_store.save_local(folder_path)

    def _initialize_vector_database(
        self, embedding_model: str, api_key: str, folder_path: Optional[str] = None
    ) -> Optional[FAISS]:
        """Initialize or load the vector database for long-term memory storage.

        Args:
            embedding_model: Name of the OpenAI embedding model to use
            api_key: OpenAI API key for embeddings
            folder_path: Optional path to load an existing vector store from

        Returns:
            Initialized FAISS vector store
        """
        embeddings = OpenAIEmbeddings(model=embedding_model, api_key=api_key)  # type: ignore
        vector_store = None
        if folder_path and os.path.exists(folder_path):
            vector_store = FAISS.load_local(folder_path, embeddings=embeddings, allow_dangerous_deserialization=True)
        else:
            index = faiss.IndexFlatL2(len(embeddings.embed_query(" ")))
            vector_store = FAISS(
                embedding_function=embeddings,
                index=index,
                docstore=InMemoryDocstore(),
                index_to_docstore_id={},
            )
        return vector_store  # type: ignore
