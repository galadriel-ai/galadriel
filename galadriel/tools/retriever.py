"""
Document Retrieval Module

This module provides semantic search functionality for retrieving relevant
documents or document segments based on user queries. It uses the BM25
algorithm for ranking document relevance.

Key Features:
- Semantic document search
- BM25-based relevance ranking
- Support for multiple document formats
- Configurable result count

Here's an example of how to use the RetrieverTool:
https://docs.galadriel.com/galadriel-network/tutorials/rag
"""

from typing import List

from langchain.docstore.document import Document
from langchain_community.retrievers import BM25Retriever

from galadriel.tools import Tool


class RetrieverTool(Tool):
    """A tool for semantic document retrieval using BM25 ranking.

    This tool enables semantic search across a collection of documents,
    returning the most relevant document segments based on the query.
    It uses the BM25 algorithm for ranking document relevance.

    Attributes:
        name (str): Tool identifier for the agent system
        description (str): Description of the tool's functionality
        inputs (dict): Schema for the required input parameters
        output_type (str): Type of data returned by the tool
        retriever (BM25Retriever): The underlying BM25 retrieval engine

    Example:
        docs = [Document(page_content="some content"), ...]
        retriever = RetrieverTool(docs)
        results = retriever.forward("search query")
    """

    name = "retriever"
    description = (
        "Uses semantic search to retrieve the parts of documentation that could be most relevant to answer your query."
    )
    inputs = {
        "query": {
            "type": "string",
            "description": "The query to perform. This should be semantically close to your target documents. "
            "Use the affirmative form rather than a question.",
        }
    }
    output_type = "string"

    def __init__(self, docs: List[Document], **kwargs):
        """Initialize the retriever tool with a document collection.

        Args:
            docs (List[Document]): List of documents to index for retrieval
            **kwargs: Additional arguments passed to parent Tool class

        Note:
            - Documents should be pre-processed and split if needed
            - The BM25Retriever is initialized to return top 10 results
        """
        super().__init__(**kwargs)
        self.retriever = BM25Retriever.from_documents(docs, k=10)

    # pylint:disable=W0221
    def forward(self, query: str) -> str:
        """Perform a semantic search across the document collection.

        Retrieves and formats the most relevant document segments based
        on the input query using BM25 ranking.

        Args:
            query (str): The search query string

        Returns:
            str: A formatted string containing the retrieved documents,
                 with each document prefixed by its index

        Raises:
            AssertionError: If the query is not a string

        Note:
            - Returns top 10 most relevant documents
            - Documents are numbered and clearly separated in the output
            - Query should be in affirmative form for best results
        """
        assert isinstance(query, str), "Your search query must be a string"

        docs = self.retriever.invoke(
            query,
        )
        return "\nRetrieved documents:\n" + "".join(
            [f"\n\n===== Document {str(i)} =====\n" + doc.page_content for i, doc in enumerate(docs)]
        )
