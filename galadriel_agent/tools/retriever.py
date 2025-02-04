from typing import List

from galadriel_agent.core_agent import Tool
from langchain.docstore.document import Document
from langchain_community.retrievers import BM25Retriever

"""
Example usage:
Load documents: https://python.langchain.com/docs/tutorials/rag/#loading-documents
Split documents: https://python.langchain.com/docs/tutorials/rag/#splitting-documents

retriever_tool = RetrieverTool(docs)
agent = CodeAgent(
    tools=[retriever_tool], model=model, max_steps=4, verbosity_level=2
)
"""


class RetrieverTool(Tool):
    name = "retriever"
    description = "Uses semantic search to retrieve the parts of transformers documentation that could be most relevant to answer your query."
    inputs = {
        "query": {
            "type": "string",
            "description": "The query to perform. This should be semantically close to your target documents. Use the affirmative form rather than a question.",
        }
    }
    output_type = "string"

    def __init__(self, docs: List[Document], **kwargs):
        super().__init__(**kwargs)
        self.retriever = BM25Retriever.from_documents(docs, k=10)

    def forward(self, query: str) -> str:
        assert isinstance(query, str), "Your search query must be a string"

        docs = self.retriever.invoke(
            query,
        )
        return "\nRetrieved documents:\n" + "".join(
            [
                f"\n\n===== Document {str(i)} =====\n" + doc.page_content
                for i, doc in enumerate(docs)
            ]
        )
