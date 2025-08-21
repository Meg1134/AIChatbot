"""
向量存储管理器
"""
import os
from typing import List, Optional
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.docstore.document import Document
from config import settings


class VectorStoreManager:
    """向量存储管理器"""
    
    def __init__(self, persist_directory: Optional[str] = None):
        """初始化向量存储管理器"""
        self.persist_directory = settings.chroma_persist_directory
        self.embeddings = OpenAIEmbeddings()
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
        )
        
        # 确保持久化目录存在
        os.makedirs(self.persist_directory, exist_ok=True)
        
        # 初始化向量存储
        self.vector_store = Chroma(
            embedding_function=self.embeddings,
            persist_directory=self.persist_directory
        )
    
    def add_documents(self, documents: List[Document]) -> List[str]:
        """添加文档到向量存储"""
        try:
            # 分割文档
            split_docs = self.text_splitter.split_documents(documents)
            
            # 添加到向量存储
            ids = self.vector_store.add_documents(split_docs)
            
            # 持久化
            self.vector_store.persist()
            
            return ids
            
        except Exception as e:
            print(f"添加文档时出错: {e}")
            return []
    
    def add_texts(self, texts: List[str], metadatas: Optional[List[dict]] = None) -> List[str]:
        """添加文本到向量存储"""
        try:
            # 分割文本
            split_texts = []
            split_metadatas = []
            
            for i, text in enumerate(texts):
                chunks = self.text_splitter.split_text(text)
                split_texts.extend(chunks)
                
                # 为每个块复制元数据
                if metadatas:
                    metadata = metadatas[i] if i < len(metadatas) else {}
                    split_metadatas.extend([metadata] * len(chunks))
            
            # 添加到向量存储
            ids = self.vector_store.add_texts(
                texts=split_texts,
                metadatas=split_metadatas if split_metadatas else None
            )
            
            # 持久化
            self.vector_store.persist()
            
            return ids
            
        except Exception as e:
            print(f"添加文本时出错: {e}")
            return []
    
    def similarity_search(self, query: str, k: int = 4) -> List[Document]:
        """相似性搜索"""
        try:
            return self.vector_store.similarity_search(query, k=k)
        except Exception as e:
            print(f"搜索时出错: {e}")
            return []
    
    def similarity_search_with_score(self, query: str, k: int = 4) -> List[tuple]:
        """带分数的相似性搜索"""
        try:
            return self.vector_store.similarity_search_with_score(query, k=k)
        except Exception as e:
            print(f"搜索时出错: {e}")
            return []
    
    def delete_collection(self):
        """删除集合"""
        try:
            self.vector_store.delete_collection()
        except Exception as e:
            print(f"删除集合时出错: {e}")
    
    def get_collection_count(self) -> int:
        """获取集合中文档数量"""
        try:
            return self.vector_store._collection.count()
        except Exception as e:
            print(f"获取文档数量时出错: {e}")
            return 0
