import pytest
from unittest.mock import Mock, patch

from galadriel.memory.memory_repository import MemoryRepository
from galadriel.entities import Message
from langchain_core.documents import Document


@pytest.fixture(autouse=True)
def mock_embeddings():
    with patch("openai.OpenAI") as mock_client, patch("langchain_openai.OpenAIEmbeddings") as mock_embeddings:
        # Mock OpenAI client's embeddings.create method
        mock_embeddings_client = Mock()
        mock_embeddings_client.create.return_value = {
            "data": [{"embedding": [0.0] * 1536}]  # OpenAI embedding dimension
        }
        mock_client.return_value.embeddings = mock_embeddings_client

        # Mock embeddings
        embeddings = Mock()
        embeddings.embed_query.return_value = [0.0] * 1536
        embeddings.embed_documents.return_value = [[0.0] * 1536]
        mock_embeddings.return_value = embeddings

        yield mock_embeddings


@pytest.fixture
def memory_repo():
    repo = MemoryRepository(api_key="fake-api-key", short_term_memory_limit=2, agent_name="test-agent")
    # Mock the vector store's async methods with AsyncMock
    from unittest.mock import AsyncMock

    repo.vector_store.aadd_documents = AsyncMock()
    repo.vector_store.asimilarity_search_with_score = AsyncMock()
    return repo


@pytest.mark.asyncio
async def test_add_memory(memory_repo):
    # Create test messages
    request = Message(content="Hello", conversation_id="123")
    response = Message(content="Hi there!", conversation_id="123")

    # Add memory
    await memory_repo.add_memory(request, response)

    # Check short term memory
    assert len(memory_repo.short_term_memory) == 1
    memory = memory_repo.short_term_memory[0]
    assert memory.content == "User: Hello\n Assistant: Hi there!"
    assert memory.conversation_id == "123"
    assert "date" in memory.additional_kwargs


@pytest.mark.asyncio
async def test_memory_overflow_to_long_term(memory_repo):
    # Add memories beyond the limit (limit is 2)
    for i in range(3):
        request = Message(content=f"Request {i}", conversation_id=str(i))
        response = Message(content=f"Response {i}", conversation_id=str(i))
        await memory_repo.add_memory(request, response)

    # Check short term memory
    assert len(memory_repo.short_term_memory) == 2
    # Verify oldest memory was moved to long term
    memory_repo.vector_store.aadd_documents.assert_called_once()


@pytest.mark.asyncio
async def test_get_memories(memory_repo):
    # Add some test memories
    request = Message(content="Test request", conversation_id="123")
    response = Message(content="Test response", conversation_id="123")
    await memory_repo.add_memory(request, response)

    # Mock long-term memory results
    mock_doc = Document(page_content="Old memory", metadata={"date": "2024-01-01 12:00", "conversation_id": "456"})
    memory_repo.vector_store.asimilarity_search_with_score.return_value = [(mock_doc, 0.8)]

    # Get memories
    result = await memory_repo.get_memories("test query", top_k=1)

    # Verify result contains both short-term and long-term memories
    assert "recent messages" in result
    assert "long term memories" in result
    assert "Test request" in result
    assert "Old memory" in result


@pytest.mark.asyncio
async def test_query_long_term_memory(memory_repo):
    # Mock search results
    mock_doc = Document(page_content="Test memory", metadata={"date": "2024-01-01 12:00", "conversation_id": "123"})
    memory_repo.vector_store.asimilarity_search_with_score.return_value = [(mock_doc, 0.8)]

    # Query memories
    results = await memory_repo._query_long_term_memory("test", top_k=1)

    # Verify results
    assert len(results) == 1
    assert results[0].content == "Test memory"
    assert results[0].conversation_id == "123"


def test_save_data_locally(memory_repo):
    memory_repo.vector_store.save_local = Mock()
    memory_repo.save_data_locally("test.faiss")
    memory_repo.vector_store.save_local.assert_called_once_with("test.faiss")


@pytest.mark.asyncio
async def test_get_short_term_memory(memory_repo):
    # Add test memory
    request = Message(content="Test", conversation_id="123")
    response = Message(content="Response", conversation_id="123")
    await memory_repo.add_memory(request, response)

    # Get short term memories
    memories = await memory_repo._get_short_term_memory()

    # Verify
    assert len(memories) == 1
    assert memories[0].content == "User: Test\n Assistant: Response"


@patch("galadriel.memory.memory_repository.FAISS.load_local")
@patch("galadriel.memory.memory_repository.OpenAIEmbeddings")
def test_initialize_with_existing_memory_folder(mock_embeddings, mock_faiss, tmp_path):
    """Test if MemoryRepository loads from an existing memory folder."""

    memory_folder = tmp_path / "test_memory"
    memory_folder.mkdir()

    # Mock FAISS load_local behavior
    mock_faiss.return_value = Mock()

    MemoryRepository(api_key="test-key", memory_folder_path=str(memory_folder))

    mock_faiss.assert_called_once_with(
        str(memory_folder), embeddings=mock_embeddings.return_value, allow_dangerous_deserialization=True
    )
