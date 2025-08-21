"""
配置管理模块
"""
import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置设置"""
    
    # OpenAI API 配置
    openai_api_key: str = ""
    openai_base_url: Optional[str] = None
    openai_default_headers: Optional[str] = None
    openai_model: str = "gpt-3.5-turbo"
    
    # LangChain 配置
    langchain_api_key: str = ""
    langchain_tracing_v2: bool = True
    langchain_project: str = "ai-chatbot"
    
    # 向量数据库配置
    chroma_persist_directory: str = "./data/chroma_db"
    
    # API 配置
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    
    # Streamlit 配置
    streamlit_port: int = 8501
    
    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'


# 全局设置实例
settings = Settings()


def get_settings() -> Settings:
    """获取配置设置"""
    return settings


def setup_environment():
    """设置环境变量"""
    if settings.openai_api_key:
        os.environ["OPENAI_API_KEY"] = settings.openai_api_key
    
    if settings.openai_base_url:
        os.environ["OPENAI_BASE_URL"] = settings.openai_base_url
        
    if settings.openai_default_headers:
        os.environ["OPENAI_DEFAULT_HEADERS"] = settings.openai_default_headers
    
    if settings.langchain_api_key:
        os.environ["LANGCHAIN_API_KEY"] = settings.langchain_api_key
        
    if settings.langchain_tracing_v2:
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        
    if settings.langchain_project:
        os.environ["LANGCHAIN_PROJECT"] = settings.langchain_project
