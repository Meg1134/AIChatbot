"""
RAG 检索器
"""
from typing import List, Optional
from langchain.docstore.document import Document
import logging
from .vector_store import VectorStoreManager

logger = logging.getLogger(__name__)

class RAGRetriever:
    def __init__(self, vector_store_manager: VectorStoreManager, k: int = 4):
        self.vector_store_manager = vector_store_manager
        self.k = k

    def get_relevant_documents(self, query: str, k: Optional[int] = None) -> List[Document]:
        kk = k or self.k
        try:
            return self.vector_store_manager.similarity_search(query, k=kk)
        except Exception as e:
            logger.error("检索失败: %s", e)
            return []

    async def aget_relevant_documents(self, query: str, k: Optional[int] = None) -> List[Document]:
        return self.get_relevant_documents(query, k=k)

    def get_relevant_documents_with_scores(self, query: str, k: Optional[int] = None) -> List[tuple]:
        kk = k or self.k
        try:
            return self.vector_store_manager.similarity_search_with_score(query, k=kk)
        except Exception as e:
            logger.error("检索(带分数)失败: %s", e)
            return []

    def format_docs(self, docs: List[Document], max_chars: int = 4000) -> str:
        if not docs:
            return "没有找到相关文档。"
        parts = []
        total = 0
        for i, doc in enumerate(docs, 1):
            content = doc.page_content.strip()
            source = doc.metadata.get("source", "未知来源")
            snippet = f"文档 {i} (来源: {source}):\n{content}"
            if total + len(snippet) > max_chars:
                parts.append("...（截断）")
                break
            parts.append(snippet)
            total += len(snippet)
        return "\n\n".join(parts)

    def search_and_format(self, query: str, k: Optional[int] = None) -> str:
        docs = self.get_relevant_documents(query, k=k)
        return self.format_docs(docs)