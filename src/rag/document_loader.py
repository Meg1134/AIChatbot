"""
文档加载器
"""
import os
import fnmatch
import chardet
from typing import List, Optional, Iterable
from langchain.docstore.document import Document
from langchain_community.document_loaders import (
    TextLoader,
    PyPDFLoader,
)
import logging

logger = logging.getLogger(__name__)

SUPPORTED_EXT = {".txt", ".md", ".pdf"}

class DocumentLoader:
    """文档加载器"""

    def __init__(
        self,
        max_file_size_mb: float = 20.0,
        detect_encoding: bool = True,
        default_encoding: str = "utf-8"
    ):
        self.max_file_size = max_file_size_mb * 1024 * 1024
        self.detect_encoding = detect_encoding
        self.default_encoding = default_encoding

    def _pick_encoding(self, file_path: str) -> str:
        if not self.detect_encoding:
            return self.default_encoding
        try:
            with open(file_path, "rb") as f:
                raw = f.read(50000)
            guess = chardet.detect(raw)
            enc = guess.get("encoding") or self.default_encoding
            return enc
        except Exception:
            return self.default_encoding

    def load_text_file(self, file_path: str) -> List[Document]:
        """加载文本文件"""
        encoding = self._pick_encoding(file_path)
        loader = TextLoader(file_path, encoding=encoding)
        docs = loader.load()
        for d in docs:
            d.metadata.setdefault("source", file_path)
        return docs

    def load_pdf_file(self, file_path: str) -> List[Document]:
        """加载 PDF 文件"""
        loader = PyPDFLoader(file_path)
        docs = loader.load()
        for d in docs:
            d.metadata.setdefault("source", file_path)
        return docs

    def _iter_files(self, directory_path: str, glob_pattern: str) -> Iterable[str]:
        for root, _, files in os.walk(directory_path):
            for file in files:
                if glob_pattern == "**/*" or fnmatch.fnmatch(file, glob_pattern):
                    yield os.path.join(root, file)

    def load_directory(
        self,
        directory_path: str,
        glob_pattern: str = "**/*",
        ignore_errors: bool = True
    ) -> List[Document]:
        """加载目录中的所有支持的文档"""
        documents: List[Document] = []
        for file_path in self._iter_files(directory_path, glob_pattern):
            ext = os.path.splitext(file_path)[1].lower()
            if ext not in SUPPORTED_EXT:
                continue
            try:
                size = os.path.getsize(file_path)
                if size > self.max_file_size:
                    logger.warning("跳过过大文件 %s (%.2fMB)", file_path, size / 1024 / 1024)
                    continue
                if ext == ".pdf":
                    docs = self.load_pdf_file(file_path)
                else:
                    docs = self.load_text_file(file_path)
                for d in docs:
                    d.metadata.setdefault("file_type", ext)
                documents.extend(docs)
            except Exception as e:
                msg = f"加载文件 {file_path} 时出错: {e}"
                if ignore_errors:
                    logger.error(msg)
                    continue
                else:
                    raise
        return documents

    def load_from_text(self, text: str, metadata: Optional[dict] = None) -> List[Document]:
        metadata = metadata.copy() if metadata else {}
        return [Document(page_content=text, metadata=metadata)]

    def load_multiple_files(self, file_paths: List[str]) -> List[Document]:
        docs: List[Document] = []
        for fp in file_paths:
            if not os.path.exists(fp):
                logger.warning("文件不存在: %s", fp)
                continue
            ext = os.path.splitext(fp)[1].lower()
            try:
                if ext == ".pdf":
                    docs.extend(self.load_pdf_file(fp))
                elif ext in (".txt", ".md"):
                    docs.extend(self.load_text_file(fp))
                else:
                    logger.warning("不支持的文件类型: %s", ext)
            except Exception as e:
                logger.error("加载 %s 失败: %s", fp, e)
        return docs