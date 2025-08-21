"""
文档加载器
"""
import os
from typing import List, Optional
from langchain.docstore.document import Document
from langchain_community.document_loaders import (
    TextLoader,
    PyPDFLoader,
    DirectoryLoader
)


class DocumentLoader:
    """文档加载器"""
    
    def __init__(self):
        """初始化文档加载器"""
        pass
    
    def load_text_file(self, file_path: str) -> List[Document]:
        """加载文本文件"""
        loader = TextLoader(file_path, encoding='utf-8')
        return loader.load()
    
    def load_pdf_file(self, file_path: str) -> List[Document]:
        """加载PDF文件"""
        loader = PyPDFLoader(file_path)
        return loader.load()
    
    def load_directory(self, directory_path: str, glob_pattern: str = "**/*") -> List[Document]:
        """加载目录中的所有文档"""
        try:
            # 根据文件扩展名选择合适的加载器
            loader_mapping = {
                ".txt": TextLoader,
                ".md": TextLoader,
                ".pdf": PyPDFLoader,
            }
            
            documents = []
            
            # 遍历目录中的文件
            for root, dirs, files in os.walk(directory_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    file_ext = os.path.splitext(file)[1].lower()
                    
                    if file_ext in loader_mapping:
                        try:
                            if file_ext == ".pdf":
                                loader = PyPDFLoader(file_path)
                            else:
                                loader = TextLoader(file_path, encoding='utf-8')
                            
                            docs = loader.load()
                            
                            # 添加文件路径到元数据
                            for doc in docs:
                                doc.metadata["source"] = file_path
                                doc.metadata["file_type"] = file_ext
                            
                            documents.extend(docs)
                            
                        except Exception as e:
                            print(f"加载文件 {file_path} 时出错: {e}")
                            continue
            
            return documents
            
        except Exception as e:
            print(f"加载目录时出错: {e}")
            return []
    
    def load_from_text(self, text: str, metadata: Optional[dict] = None) -> List[Document]:
        """从文本字符串创建文档"""
        try:
            metadata = metadata or {}
            return [Document(page_content=text, metadata=metadata)]
        except Exception as e:
            print(f"从文本创建文档时出错: {e}")
            return []
    
    def load_multiple_files(self, file_paths: List[str]) -> List[Document]:
        """加载多个文件"""
        documents = []
        
        for file_path in file_paths:
            if not os.path.exists(file_path):
                print(f"文件不存在: {file_path}")
                continue
            
            file_ext = os.path.splitext(file_path)[1].lower()
            
            if file_ext == ".pdf":
                docs = self.load_pdf_file(file_path)
            elif file_ext in [".txt", ".md"]:
                docs = self.load_text_file(file_path)
            else:
                print(f"不支持的文件类型: {file_ext}")
                continue
            
            documents.extend(docs)
        
        return documents
