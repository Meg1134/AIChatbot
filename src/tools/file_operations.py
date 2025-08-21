"""
文件操作工具
"""
import os
import json
from typing import Any
from langchain.tools import BaseTool
from pydantic import BaseModel, Field


class FileReadInput(BaseModel):
    """文件读取输入模型"""
    file_path: str = Field(description="要读取的文件路径")


class FileWriteInput(BaseModel):
    """文件写入输入模型"""
    file_path: str = Field(description="要写入的文件路径")
    content: str = Field(description="要写入的内容")


class FileOperationsTool(BaseTool):
    """文件操作工具类"""
    
    name: str = "file_operations"
    description: str = "文件操作工具，可以读取和写入文件"
    
    def _run(self, operation: str, file_path: str, content: str = None) -> str:
        """执行文件操作"""
        try:
            if operation == "read":
                if not os.path.exists(file_path):
                    return f"文件不存在: {file_path}"
                
                with open(file_path, 'r', encoding='utf-8') as f:
                    file_content = f.read()
                
                return f"文件内容:\n{file_content}"
            
            elif operation == "write":
                if content is None:
                    return "写入操作需要提供内容"
                
                # 确保目录存在
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                return f"文件写入成功: {file_path}"
            
            elif operation == "list":
                if not os.path.exists(file_path):
                    return f"目录不存在: {file_path}"
                
                if os.path.isfile(file_path):
                    return f"{file_path} 是一个文件，不是目录"
                
                files = os.listdir(file_path)
                return f"目录 {file_path} 中的文件:\n" + "\n".join(files)
            
            else:
                return f"不支持的操作: {operation}"
                
        except Exception as e:
            return f"文件操作错误: {str(e)}"
    
    async def _arun(self, operation: str, file_path: str, content: str = None) -> str:
        """异步执行文件操作"""
        return self._run(operation, file_path, content)
