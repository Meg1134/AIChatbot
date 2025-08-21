"""
FastAPI 后端服务
"""
import asyncio
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from config import setup_environment, settings
from src.agents import ChatbotAgent
from src.mcp import MCPServer


# 设置环境变量
setup_environment()

# 创建 FastAPI 应用
app = FastAPI(
    title="AI 聊天机器人 API",
    description="基于 LangChain、LangGraph、MCP 和 RAG 的智能聊天机器人",
    version="1.0.0"
)

# 添加 CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局变量
chatbot_agent = None
mcp_server = None


# Pydantic 模型
class ChatRequest(BaseModel):
    """聊天请求模型"""
    message: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    """聊天响应模型"""
    response: str
    session_id: str


class DocumentRequest(BaseModel):
    """文档添加请求模型"""
    texts: List[str]
    metadatas: Optional[List[dict]] = None


class HealthResponse(BaseModel):
    """健康检查响应模型"""
    status: str
    version: str
    components: dict


# 启动事件
@app.on_event("startup")
async def startup_event():
    """应用启动时的初始化"""
    global chatbot_agent, mcp_server
    
    try:
        # 初始化聊天机器人
        chatbot_agent = ChatbotAgent()
        print("✅ 聊天机器人初始化完成")
        
        # 启动 MCP 服务器
        mcp_server = MCPServer(host="localhost", port=8765)
        asyncio.create_task(mcp_server.start())
        print("✅ MCP 服务器启动完成")
        
    except Exception as e:
        print(f"❌ 启动时出错: {e}")


@app.get("/", response_model=dict)
async def root():
    """根路径"""
    return {
        "message": "AI 聊天机器人 API", 
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """健康检查"""
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        components={
            "chatbot": "active" if chatbot_agent else "inactive",
            "mcp_server": "active" if mcp_server else "inactive"
        }
    )


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """聊天接口"""
    if not chatbot_agent:
        raise HTTPException(status_code=503, detail="聊天机器人未初始化")
    
    try:
        # 生成会话ID（如果没有提供）
        session_id = request.session_id or "default"
        
        # 调用聊天机器人
        response = await chatbot_agent.chat(request.message)
        
        return ChatResponse(
            response=response,
            session_id=session_id
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"聊天处理失败: {str(e)}")


@app.post("/documents")
async def add_documents(request: DocumentRequest):
    """添加文档到知识库"""
    if not chatbot_agent:
        raise HTTPException(status_code=503, detail="聊天机器人未初始化")
    
    try:
        # 添加文档到 RAG 系统
        chatbot_agent.add_documents_to_rag(
            texts=request.texts,
            metadatas=request.metadatas
        )
        
        return {
            "message": f"成功添加 {len(request.texts)} 个文档到知识库",
            "document_count": len(request.texts)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"添加文档失败: {str(e)}")


@app.get("/tools")
async def list_tools():
    """获取可用工具列表"""
    if not chatbot_agent:
        raise HTTPException(status_code=503, detail="聊天机器人未初始化")
    
    tools_info = []
    for tool in chatbot_agent.tools:
        tools_info.append({
            "name": tool.name,
            "description": tool.description
        })
    
    return {"tools": tools_info}


@app.get("/rag/status")
async def rag_status():
    """获取 RAG 系统状态"""
    if not chatbot_agent:
        raise HTTPException(status_code=503, detail="聊天机器人未初始化")
    
    try:
        document_count = chatbot_agent.vector_store_manager.get_collection_count()
        
        return {
            "status": "active",
            "document_count": document_count,
            "persist_directory": settings.chroma_persist_directory
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


@app.delete("/rag/documents")
async def clear_documents():
    """清空知识库"""
    if not chatbot_agent:
        raise HTTPException(status_code=503, detail="聊天机器人未初始化")
    
    try:
        chatbot_agent.vector_store_manager.delete_collection()
        
        return {"message": "知识库已清空"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"清空知识库失败: {str(e)}")


@app.get("/mcp/status")
async def mcp_status():
    """获取 MCP 服务器状态"""
    if not mcp_server:
        return {"status": "inactive"}
    
    return {
        "status": "active",
        "host": mcp_server.host,
        "port": mcp_server.port,
        "client_count": len(mcp_server.clients)
    }


# 开发模式运行
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True
    )
