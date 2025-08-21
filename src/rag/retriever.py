"""
RAG 检索器
"""
from typing import List, Optional
from langchain.docstore.document import Document
from langchain.schema import BaseRetriever
from .vector_store import VectorStoreManager


class RAGRetriever(BaseRetriever):
    """RAG 检索器"""
    
    def __init__(self, vector_store_manager: VectorStoreManager, k: int = 4):
        """初始化检索器"""
        self.vector_store_manager = vector_store_manager
        self.k = k
    
    def get_relevant_documents(self, query: str) -> List[Document]:
        """获取相关文档"""
        return self.vector_store_manager.similarity_search(query, k=self.k)
    
    async def aget_relevant_documents(self, query: str) -> List[Document]:
        """异步获取相关文档"""
        return self.get_relevant_documents(query)
    
    def get_relevant_documents_with_scores(self, query: str) -> List[tuple]:
        """获取带分数的相关文档"""
        return self.vector_store_manager.similarity_search_with_score(query, k=self.k)
    
    def format_docs(self, docs: List[Document]) -> str:
        """格式化文档为字符串"""
        if not docs:
            return "没有找到相关文档。"
        
        formatted_docs = []
        for i, doc in enumerate(docs, 1):
            content = doc.page_content.strip()
            source = doc.metadata.get("source", "未知来源")
            formatted_docs.append(f"文档 {i} (来源: {source}):\n{content}")
        
        return "\n\n".join(formatted_docs)
    
    def search_and_format(self, query: str) -> str:
        """搜索并格式化结果"""
        docs = self.get_relevant_documents(query)
        return self.format_docs(docs)
