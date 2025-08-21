"""
聊天机器人智能体（修复 langgraph 返回 dict 的问题）
"""
from typing import Dict, List, Any, Optional
import logging
import asyncio

from langchain_openai import ChatOpenAI
from langchain.schema import BaseMessage, HumanMessage, AIMessage, SystemMessage
from pydantic import BaseModel

try:
    from langgraph.graph import StateGraph, END
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False

from src.rag import RAGRetriever, VectorStoreManager
from src.tools import CalculatorTool, WebSearchTool, FileOperationsTool, WeatherTool
from config import settings

logger = logging.getLogger(__name__)


class AgentState(BaseModel):
    messages: List[BaseMessage] = []
    next_action: Optional[str] = None
    tool_calls: List[Dict] = []
    rag_context: Optional[str] = None


class ChatbotAgent:
    """聊天机器人智能体"""

    def __init__(self, model_name: str = "gpt-3.5-turbo"):
        llm_kwargs = {
            "model": model_name,
            "temperature": 0.7,
            "base_url": settings.openai_base_url,
            "default_headers": {'x-foo': 'true'},
        }
        self.llm = ChatOpenAI(**llm_kwargs)

        # 工具实例
        self.calculator = CalculatorTool()
        self.weather_tool = WeatherTool()
        self.search_tool = WebSearchTool()
        self.file_tool = FileOperationsTool()
        self.tools = [self.calculator, self.weather_tool, self.search_tool, self.file_tool]

        # RAG
        self.vector_store_manager = VectorStoreManager()
        self.rag_retriever = RAGRetriever(self.vector_store_manager)

        self.graph = self._build_graph() if LANGGRAPH_AVAILABLE else None

    def _build_graph(self):
        workflow = StateGraph(AgentState)
        workflow.add_node("reasoning", self._reasoning_node)
        workflow.add_node("tool_calling", self._tool_calling_node)
        workflow.add_node("rag_retrieval", self._rag_retrieval_node)
        workflow.add_node("response_generation", self._response_generation_node)
        workflow.set_entry_point("reasoning")
        workflow.add_conditional_edges(
            "reasoning",
            self._should_use_tools_or_rag,
            {"tools": "tool_calling", "rag": "rag_retrieval", "response": "response_generation"}
        )
        workflow.add_edge("tool_calling", "response_generation")
        workflow.add_edge("rag_retrieval", "response_generation")
        workflow.add_edge("response_generation", END)
        return workflow.compile()

    # ----------------- 节点逻辑 -----------------
    def _reasoning_node(self, state: AgentState) -> AgentState:
        if not state.messages:
            return state
        last = state.messages[-1]
        if isinstance(last, HumanMessage):
            txt = last.content.lower()
            if any(k in txt for k in ["计算", "算", "数学"]):
                state.next_action = "tools"
            elif any(k in txt for k in ["搜索", "查找", "天气"]):
                state.next_action = "tools"
            elif any(k in txt for k in ["知识", "文档", "资料"]):
                state.next_action = "rag"
            else:
                state.next_action = "response"
        return state

    def _should_use_tools_or_rag(self, state: AgentState) -> str:
        return state.next_action or "response"

    def _tool_calling_node(self, state: AgentState) -> AgentState:
        if not state.messages:
            return state
        last = state.messages[-1]
        if isinstance(last, HumanMessage):
            user_input = last.content
            result = None
            if any(k in user_input for k in ["计算", "算", "数学"]):
                import re
                math_pattern = r'[\d+\-*/().\s]+'
                matches = re.findall(math_pattern, user_input)
                if matches:
                    expression = max(matches, key=len).strip()
                    result = self.calculator._run(expression)
            elif "天气" in user_input:
                cities = ["北京", "上海", "广州", "深圳", "杭州", "南京"]
                city = next((c for c in cities if c in user_input), "北京")
                result = self.weather_tool._run(city)
            elif "搜索" in user_input:
                query = user_input.replace("搜索", "").strip()
                result = self.search_tool._run(query)
            if result:
                state.tool_calls.append({"tool": "auto", "result": result})
        return state

    def _rag_retrieval_node(self, state: AgentState) -> AgentState:
        if not state.messages:
            return state
        last = state.messages[-1]
        if isinstance(last, HumanMessage):
            user_input = last.content
            state.rag_context = self.rag_retriever.search_and_format(user_input)
        return state

    def _response_generation_node(self, state: AgentState) -> AgentState:
        if not state.messages:
            return state
        system_prompt = (
            "你是一个智能助手，可以：\n"
            "1. 进行数学计算\n2. 搜索信息\n3. 查询天气\n4. 基于知识库回答问题\n\n"
            "请根据用户的问题和可用的信息提供有帮助的回答。"
        )
        msgs: List[BaseMessage] = [SystemMessage(content=system_prompt)]
        if state.rag_context:
            msgs.append(SystemMessage(content=f"相关知识背景：\n{state.rag_context}"))
        for tc in state.tool_calls:
            msgs.append(SystemMessage(content=f"工具执行结果：{tc['result']}"))
        msgs.extend(state.messages)
        # 使用 invoke（同步）或 .invoke / .ainvoke 取决于版本
        response = self.llm.invoke(msgs)
        state.messages.append(response)
        return state

    # ----------------- 辅助 -----------------
    def _extract_messages(self, final_state) -> List[BaseMessage]:
        """
        兼容 langgraph 返回 dict 或 AgentState。
        """
        if isinstance(final_state, AgentState):
            return final_state.messages
        if isinstance(final_state, dict):
            return final_state.get("messages", [])
        logger.warning("未知 final_state 类型: %s", type(final_state))
            # 返回空，触发 fallback
        return []

    # ----------------- 对话接口 -----------------
    async def chat(self, user_input: str, chat_history: Optional[List[BaseMessage]] = None) -> str:
        """
        异步聊天接口。
        """
        messages = list(chat_history) if chat_history else []
        messages.append(HumanMessage(content=user_input))

        if self.graph and LANGGRAPH_AVAILABLE:
            # 用 dict 作为初始状态，避免 Pydantic 二次封装
            initial_state_dict = {
                "messages": messages,
                "next_action": None,
                "tool_calls": [],
                "rag_context": None
            }
            try:
                final_state = await self.graph.ainvoke(initial_state_dict)
                msgs = self._extract_messages(final_state)
                if msgs and isinstance(msgs[-1], AIMessage):
                    return msgs[-1].content
                # 没拿到 AIMessage 则降级
                logger.warning("Graph 执行没有得到 AIMessage，使用简化逻辑 fallback。")
            except Exception as e:
                logger.exception("Graph 执行失败，回退简单对话: %s", e)
                return await self._simple_chat(user_input, chat_history)
        # 没有 graph 或失败 fallback
        return await self._simple_chat(user_input, chat_history)

    async def _simple_chat(self, user_input: str, chat_history: Optional[List[BaseMessage]] = None) -> str:
        messages = list(chat_history) if chat_history else []
        tool_result = None
        lower = user_input.lower()

        if any(k in lower for k in ["计算", "算", "数学"]):
            import re
            matches = re.findall(r'[\d+\-*/().\s]+', user_input)
            if matches:
                tool_result = self.calculator._run(max(matches, key=len).strip())
        elif "天气" in lower:
            cities = ["北京", "上海", "广州", "深圳", "杭州", "南京"]
            city = next((c for c in cities if c in user_input), "北京")
            tool_result = self.weather_tool._run(city)
        elif "搜索" in lower:
            query = user_input.replace("搜索", "").strip()
            tool_result = self.search_tool._run(query)

        rag_context = None
        if any(k in lower for k in ["知识", "文档", "资料"]):
            rag_context = self.rag_retriever.search_and_format(user_input)

        system_prompt = (
            "你是一个智能助手，可以：\n"
            "1. 进行数学计算\n2. 搜索信息\n3. 查询天气\n4. 基于知识库回答问题\n\n"
            "请根据用户的问题和可用的信息提供有帮助的回答。"
        )
        prompt_messages: List[BaseMessage] = [SystemMessage(content=system_prompt)]
        if rag_context:
            prompt_messages.append(SystemMessage(content=f"相关知识背景：\n{rag_context}"))
        if tool_result:
            prompt_messages.append(SystemMessage(content=f"工具执行结果：{tool_result}"))
        prompt_messages.extend(messages)
        prompt_messages.append(HumanMessage(content=user_input))
        response = self.llm.invoke(prompt_messages)
        return response.content

    def chat_sync(self, user_input: str, chat_history: Optional[List[BaseMessage]] = None) -> str:
        """
        同步包装，供 Streamlit 或非异步环境直接调用。
        避免在已经运行的事件循环里再次 asyncio.run（如需兼容，可做更多判断）。
        """
        try:
            return asyncio.run(self.chat(user_input, chat_history))
        except RuntimeError:
            # 若已有事件循环（某些环境），退回用简化逻辑或创建新任务
            logger.warning("检测到已有事件循环，改用简化逻辑同步调用。")
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(self.chat(user_input, chat_history))

    def add_documents_to_rag(self, texts: List[str], metadatas: Optional[List[Dict]] = None):
        self.vector_store_manager.add_texts(texts, metadatas)