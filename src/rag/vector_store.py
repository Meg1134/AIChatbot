"""
向量存储管理器
"""
import os
import logging
from typing import List, Optional, Sequence
from uuid import uuid4
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.docstore.document import Document
from config import settings

logger = logging.getLogger(__name__)

class VectorStoreManager:
    """向量存储管理器"""

    def __init__(
        self,
        persist_directory: Optional[str] = None,
        embedding_model: Optional[str] = None,
        chunk_size: int = 1000,
        chunk_overlap: int = 200
    ):
        self.persist_directory = persist_directory or settings.chroma_persist_directory
        os.makedirs(self.persist_directory, exist_ok=True)

        self.embeddings = OpenAIEmbeddings(
            # model=embedding_model or "text-embedding-3-small"  # 视你的环境调整
        )
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
        )
        self.vector_store = Chroma(
            embedding_function=self.embeddings,
            persist_directory=self.persist_directory
        )

    def add_documents(self, documents: List[Document]) -> List[str]:
        if not documents:
            return []
        try:
            enriched: List[Document] = []
            for doc in documents:
                original_id = doc.metadata.get("doc_id", str(uuid4()))
                chunks = self.text_splitter.split_text(doc.page_content)
                for idx, chunk in enumerate(chunks):
                    enriched.append(
                        Document(
                            page_content=chunk,
                            metadata={
                                **doc.metadata,
                                "doc_id": original_id,
                                "chunk_index": idx,
                                "chunk_total_est": len(chunks)
                            }
                        )
                    )
            ids = self.vector_store.add_documents(enriched)
            self.vector_store.persist()
            return ids
        except Exception as e:
            logger.error("添加文档失败: %s", e)
            return []

    def add_texts(
        self,
        texts: List[str],
        metadatas: Optional[List[dict]] = None
    ) -> List[str]:
        if not texts:
            return []
        try:
            final_texts: List[str] = []
            final_metadatas: List[dict] = []
            for i, t in enumerate(texts):
                if not t or not t.strip():
                    continue
                base_meta = (metadatas[i] if metadatas and i < len(metadatas) else {}) or {}
                chunks = self.text_splitter.split_text(t)
                for idx, chunk in enumerate(chunks):
                    final_texts.append(chunk)
                    meta = {
                        **base_meta,
                        "doc_id": base_meta.get("doc_id", str(uuid4())),
                        "chunk_index": idx,
                        "chunk_total_est": len(chunks)
                    }
                    final_metadatas.append(meta)
            ids = self.vector_store.add_texts(texts=final_texts, metadatas=final_metadatas)
            self.vector_store.persist()
            return ids
        except Exception as e:
            logger.error("添加文本失败: %s", e)
            return []

    def similarity_search(self, query: str, k: int = 4) -> List[Document]:
        try:
            return self.vector_store.similarity_search(query, k=k)
        except Exception as e:
            logger.error("相似性搜索失败: %s", e)
            return []

    def similarity_search_with_score(self, query: str, k: int = 4) -> List[tuple]:
        try:
            return self.vector_store.similarity_search_with_score(query, k=k)
        except Exception as e:
            logger.error("带分数搜索失败: %s", e)
            return []

    def delete_collection(self):
        try:
            self.vector_store.delete_collection()
            logger.info("集合已删除，重新初始化")
            self.vector_store = Chroma(
                embedding_function=self.embeddings,
                persist_directory=self.persist_directory
            )
        except Exception as e:
            logger.error("删除集合失败: %s", e)

    def get_collection_count(self) -> int:
        try:
            # 使用公开 API（若新版本提供）。这里回退使用 _collection 但保护异常。
            return self.vector_store._collection.count()  # 仍为内部；如未来 API 变动需调整
        except Exception as e:
            logger.error("获取文档数量失败: %s", e)
            return 0