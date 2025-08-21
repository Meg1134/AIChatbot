"""
网络搜索工具
"""
import requests
from typing import Any
from langchain.tools import BaseTool
from pydantic import BaseModel, Field


class WebSearchInput(BaseModel):
    """网络搜索输入模型"""
    query: str = Field(description="搜索查询字符串")
    num_results: int = Field(default=5, description="返回结果数量")


class WebSearchTool(BaseTool):
    """网络搜索工具类"""
    
    name: str = "web_search"
    description: str = "在互联网上搜索信息的工具。可以搜索最新的信息和资讯"
    args_schema: type[BaseModel] = WebSearchInput
    
    def _run(self, query: str, num_results: int = 5) -> str:
        """执行网络搜索"""
        try:
            # 这里使用模拟搜索，实际应用中可以集成真实的搜索API
            # 比如 Google Search API, DuckDuckGo API 等
            
            # 模拟搜索结果
            mock_results = [
                {
                    "title": f"搜索结果 {i+1}: {query}",
                    "url": f"https://example.com/result{i+1}",
                    "snippet": f"这是关于 '{query}' 的搜索结果 {i+1}。包含相关信息和详细内容..."
                }
                for i in range(min(num_results, 5))
            ]
            
            # 格式化搜索结果
            formatted_results = []
            for result in mock_results:
                formatted_results.append(
                    f"标题: {result['title']}\n"
                    f"链接: {result['url']}\n"
                    f"摘要: {result['snippet']}\n"
                )
            
            return "搜索结果:\n\n" + "\n".join(formatted_results)
            
        except Exception as e:
            return f"搜索错误: {str(e)}"
    
    async def _arun(self, query: str, num_results: int = 5) -> str:
        """异步执行搜索"""
        return self._run(query, num_results)
