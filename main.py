import asyncio
from contextlib import asynccontextmanager
from typing import List, Optional, Dict
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import logging

from config import setup_environment, settings
from src.agents import ChatbotAgent
from src.mcp import MCPServer  # 假设你仍可能用里面的一些逻辑（如果它不可分离，需要调整）

# ------------------------------------------------------------------
# 初始化日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("app")

setup_environment()

# 全局状态对象（线程/协程安全可以再包装）
class AppState:
    chatbot_agent: Optional[ChatbotAgent] = None
    # 如果继续使用独立端口启动的 MCPServer
    mcp_server: Optional[MCPServer] = None
    mcp_task: Optional[asyncio.Task] = None
    sessions: Dict[str, dict] = {}  # 简单的 session 存储（示例）

state = AppState()

# ------------------------------------------------------------------
# Pydantic 模型
class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    session_id: str

class DocumentRequest(BaseModel):
    texts: List[str]
    metadatas: Optional[List[dict]] = None

class HealthResponse(BaseModel):
    status: str
    version: str
    components: dict

# ------------------------------------------------------------------
# Lifespan 取代 on_event
@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        # Startup
        state.chatbot_agent = ChatbotAgent()
        logger.info("ChatbotAgent 初始化完成")

        # 如果你想保持单独的 websockets 服务器（原来 8765 端口）
        # 启动方式如下；如果不需要，注释掉
        state.mcp_server = MCPServer(host="localhost", port=8765)
        state.mcp_task = asyncio.create_task(state.mcp_server.start())
        logger.info("MCPServer 已启动 (独立端口 %s)", state.mcp_server.port)

        yield
    except Exception as e:
        logger.exception("启动失败: %s", e)
        # 失败则仍然 yield 保证应用启动失败时能优雅关闭
        yield
    finally:
        # Shutdown
        if state.mcp_server:
            try:
                await state.mcp_server.stop()  # 你需要在 MCPServer 中实现 stop()
                logger.info("MCPServer 已停止")
            except Exception:
                logger.exception("关闭 MCPServer 失败")
        if state.mcp_task:
            state.mcp_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await state.mcp_task
        logger.info("应用已清理资源")

app = FastAPI(
    title="AI 聊天机器人 API",
    description="基于 LangChain、LangGraph、MCP 和 RAG 的智能聊天机器人",
    version="1.0.0",
    lifespan=lifespan
)

# ------------------------------------------------------------------
# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产建议收紧
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------------------------------------------------
# 常规 HTTP 路由
@app.get("/")
async def root():
    return {"message": "AI 聊天机器人 API", "version": "1.0.0", "docs": "/docs"}

@app.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        components={
            "chatbot": "active" if state.chatbot_agent else "inactive",
            "mcp_server": "active" if state.mcp_server else "inactive"
        }
    )

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    if not state.chatbot_agent:
        raise HTTPException(status_code=503, detail="聊天机器人未初始化")

    session_id = request.session_id or "default"

    # （示例）简单维护会话上下文
    session_ctx = state.sessions.setdefault(session_id, {})

    try:
        response_text = await state.chatbot_agent.chat(request.message)
        # 这里可以把 response / user message 写进 session_ctx["history"]
        return ChatResponse(response=response_text, session_id=session_id)
    except Exception as e:
        logger.exception("聊天处理失败")
        raise HTTPException(status_code=500, detail=f"聊天处理失败: {e}")

@app.post("/documents")
async def add_documents(request: DocumentRequest):
    if not state.chatbot_agent:
        raise HTTPException(status_code=503, detail="聊天机器人未初始化")
    try:
        state.chatbot_agent.add_documents_to_rag(
            texts=request.texts,
            metadatas=request.metadatas
        )
        return {"message": f"成功添加 {len(request.texts)} 个文档到知识库", "document_count": len(request.texts)}
    except Exception as e:
        logger.exception("添加文档失败")
        raise HTTPException(status_code=500, detail=f"添加文档失败: {e}")

@app.get("/tools")
async def list_tools():
    if not state.chatbot_agent:
        raise HTTPException(status_code=503, detail="聊天机器人未初始化")
    tools_info = []
    for tool in getattr(state.chatbot_agent, "tools", []):
        name = getattr(tool, "name", "<unnamed>")
        desc = getattr(tool, "description", "")
        tools_info.append({"name": name, "description": desc})
    return {"tools": tools_info}

@app.get("/rag/status")
async def rag_status():
    if not state.chatbot_agent:
        raise HTTPException(status_code=503, detail="聊天机器人未初始化")
    try:
        count = state.chatbot_agent.vector_store_manager.get_collection_count()
        return {
            "status": "active",
            "document_count": count,
            "persist_directory": settings.chroma_persist_directory
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}

@app.delete("/rag/documents")
async def clear_documents():
    if not state.chatbot_agent:
        raise HTTPException(status_code=503, detail="聊天机器人未初始化")
    try:
        state.chatbot_agent.vector_store_manager.delete_collection()
        return {"message": "知识库已清空"}
    except Exception as e:
        logger.exception("清空失败")
        raise HTTPException(status_code=500, detail=f"清空知识库失败: {e}")

@app.get("/mcp/status")
async def mcp_status():
    if not state.mcp_server:
        return {"status": "inactive"}
    return {
        "status": "active",
        "host": state.mcp_server.host,
        "port": state.mcp_server.port,
        "client_count": len(getattr(state.mcp_server, "clients", []))
    }

# ------------------------------------------------------------------
# （可选）示例 WebSocket 路由：聊天
@app.websocket("/ws/chat")
async def ws_chat(websocket: WebSocket):
    await websocket.accept()
    session_id = "ws_default"
    if session_id not in state.sessions:
        state.sessions[session_id] = {}
    try:
        while True:
            text = await websocket.receive_text()
            if not state.chatbot_agent:
                await websocket.send_text("聊天机器人未初始化")
                continue
            try:
                reply = await state.chatbot_agent.chat(text)
                await websocket.send_text(reply)
            except Exception as e:
                await websocket.send_text(f"错误: {e}")
    except WebSocketDisconnect:
        logger.info("WebSocket 断开 /ws/chat")
    except Exception as e:
        logger.exception("WebSocket 出错: %s", e)
        await websocket.close(code=1011)

# ------------------------------------------------------------------
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True
    )