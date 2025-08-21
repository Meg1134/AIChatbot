"""
聊天机器人智能体
"""
from typing import Dict, List, Any, Optional

from langchain_openai import ChatOpenAI
from langchain.schema import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, END
from pydantic import BaseModel

from src.rag import RAGRetriever, VectorStoreManager
from src.tools import CalculatorTool, WebSearchTool, FileOperationsTool, WeatherTool
from config import settings


class AgentState(BaseModel):
    """智能体状态"""
    messages: List[BaseMessage] = []
    next_action: Optional[str] = None
    tool_calls: List[Dict] = []
    rag_context: Optional[str] = None


class ChatbotAgent:
    """聊天机器人智能体"""
    
    def __init__(self, model_name: str = "gpt-3.5-turbo"):
        """初始化聊天机器人智能体"""
        # 构建 LLM 配置
        llm_kwargs = {
            "model": model_name,
            "temperature": 0.7,
            'base_url': settings.openai_base_url,
            'default_headers': {'x-foo': 'true'},
        }

        
        self.llm = ChatOpenAI(**llm_kwargs)
        
        # 初始化工具
        self.tools = [
            CalculatorTool(),
            WebSearchTool(),
            FileOperationsTool(), 
            WeatherTool()
        ]

        self.vector_store_manager = VectorStoreManager()
        self.rag_retriever = RAGRetriever(self.vector_store_manager)

        self.graph = self._build_graph()
    
    def _build_graph(self):
        """构建 LangGraph 状态图"""
            
        workflow = StateGraph(AgentState)
        
        # 添加节点
        workflow.add_node("reasoning", self._reasoning_node)
        workflow.add_node("tool_calling", self._tool_calling_node)
        workflow.add_node("rag_retrieval", self._rag_retrieval_node)
        workflow.add_node("response_generation", self._response_generation_node)
        
        # 设置入口点
        workflow.set_entry_point("reasoning")
        
        # 添加条件边
        workflow.add_conditional_edges(
            "reasoning",
            self._should_use_tools_or_rag,
            {
                "tools": "tool_calling",
                "rag": "rag_retrieval", 
                "response": "response_generation"
            }
        )
        
        workflow.add_edge("tool_calling", "response_generation")
        workflow.add_edge("rag_retrieval", "response_generation")
        workflow.add_edge("response_generation", END)
        
        return workflow.compile()
    
    def _reasoning_node(self, state: AgentState) -> AgentState:
        """推理节点 - 分析用户意图"""
        if not state.messages:
            return state
        
        last_message = state.messages[-1]
        if isinstance(last_message, HumanMessage):
            user_input = last_message.content
            
            # 简单的意图识别
            if any(keyword in user_input.lower() for keyword in ["计算", "算", "数学"]):
                state.next_action = "tools"
            elif any(keyword in user_input.lower() for keyword in ["搜索", "查找", "天气"]):
                state.next_action = "tools"
            elif any(keyword in user_input.lower() for keyword in ["知识", "文档", "资料"]):
                state.next_action = "rag"
            else:
                state.next_action = "response"
        
        return state
    
    def _should_use_tools_or_rag(self, state: AgentState) -> str:
        """判断是否需要使用工具或 RAG"""
        return state.next_action or "response"
    
    def _tool_calling_node(self, state: AgentState) -> AgentState:
        """工具调用节点"""
        if not state.messages:
            return state
        
        last_message = state.messages[-1]
        if isinstance(last_message, HumanMessage):
            user_input = last_message.content
            
            # 根据用户输入选择合适的工具
            tool_result = None
            
            if any(keyword in user_input.lower() for keyword in ["计算", "算", "数学"]):
                # 提取数学表达式（简化版）
                import re
                math_pattern = r'[\d+\-*/().\s]+'
                matches = re.findall(math_pattern, user_input)
                if matches:
                    expression = max(matches, key=len).strip()
                    calculator = CalculatorTool()
                    tool_result = calculator._run(expression)
            
            elif "天气" in user_input.lower():
                # 提取城市名（简化版）
                cities = ["北京", "上海", "广州", "深圳", "杭州", "南京"]
                city = next((c for c in cities if c in user_input), "北京")
                weather_tool = WeatherTool()
                tool_result = weather_tool._run(city)
            
            elif "搜索" in user_input.lower():
                # 提取搜索关键词
                query = user_input.replace("搜索", "").strip()
                search_tool = WebSearchTool()
                tool_result = search_tool._run(query)
            
            if tool_result:
                state.tool_calls.append({
                    "tool": "auto_selected",
                    "result": tool_result
                })
        
        return state
    
    def _rag_retrieval_node(self, state: AgentState) -> AgentState:
        """RAG 检索节点"""
        if not state.messages:
            return state
        
        last_message = state.messages[-1]
        if isinstance(last_message, HumanMessage):
            user_input = last_message.content
            
            # 使用 RAG 检索相关信息
            relevant_docs = self.rag_retriever.search_and_format(user_input)
            state.rag_context = relevant_docs
        
        return state
    
    def _response_generation_node(self, state: AgentState) -> AgentState:
        """响应生成节点"""
        if not state.messages:
            return state
        
        # 构建系统提示
        system_prompt = """你是一个智能助手，可以：
1. 进行数学计算
2. 搜索信息
3. 查询天气
4. 基于知识库回答问题

请根据用户的问题和可用的信息提供有帮助的回答。"""
        
        # 构建消息列表
        messages = [SystemMessage(content=system_prompt)]
        
        # 添加 RAG 上下文
        if state.rag_context:
            context_message = SystemMessage(
                content=f"相关知识背景：\n{state.rag_context}"
            )
            messages.append(context_message)
        
        # 添加工具调用结果
        if state.tool_calls:
            for tool_call in state.tool_calls:
                tool_result_message = SystemMessage(
                    content=f"工具执行结果：{tool_call['result']}"
                )
                messages.append(tool_result_message)
        
        # 添加对话历史
        messages.extend(state.messages)
        
        # 生成回复
        response = self.llm(messages)
        state.messages.append(response)
        
        return state
    
    async def chat(self, user_input: str, chat_history: List[BaseMessage] = None) -> str:
        """进行对话"""
        # 如果 LangGraph 可用，使用图执行
        if self.graph and LANGGRAPH_AVAILABLE:
            # 初始化状态
            messages = chat_history or []
            messages.append(HumanMessage(content=user_input))
            
            initial_state = AgentState(messages=messages)
            
            # 运行图
            final_state = await self.graph.ainvoke(initial_state)
            
            # 返回最后的 AI 回复
            if final_state.messages:
                last_message = final_state.messages[-1]
                if isinstance(last_message, AIMessage):
                    return last_message.content
        
        # 如果 LangGraph 不可用，使用简化逻辑
        return await self._simple_chat(user_input, chat_history)
    
    async def _simple_chat(self, user_input: str, chat_history: List[BaseMessage] = None) -> str:
        """简化的对话逻辑（不使用 LangGraph）"""
        messages = chat_history or []
        
        # 检查是否需要工具调用
        tool_result = None
        
        if any(keyword in user_input.lower() for keyword in ["计算", "算", "数学"]):
            # 数学计算
            import re
            math_pattern = r'[\d+\-*/().\s]+'
            matches = re.findall(math_pattern, user_input)
            if matches:
                expression = max(matches, key=len).strip()
                calculator = CalculatorTool()
                tool_result = calculator._run(expression)
        
        elif "天气" in user_input.lower():
            # 天气查询
            cities = ["北京", "上海", "广州", "深圳", "杭州", "南京"]
            city = next((c for c in cities if c in user_input), "北京")
            weather_tool = WeatherTool()
            tool_result = weather_tool._run(city)
        
        elif "搜索" in user_input.lower():
            # 搜索功能
            query = user_input.replace("搜索", "").strip()
            search_tool = WebSearchTool()
            tool_result = search_tool._run(query)
        
        # 检查是否需要 RAG
        rag_context = None
        if any(keyword in user_input.lower() for keyword in ["知识", "文档", "资料"]):
            rag_context = self.rag_retriever.search_and_format(user_input)
        
        # 构建系统提示
        system_prompt = """你是一个智能助手，可以：
1. 进行数学计算
2. 搜索信息
3. 查询天气
4. 基于知识库回答问题

请根据用户的问题和可用的信息提供有帮助的回答。"""
        
        # 构建消息列表
        chat_messages = [SystemMessage(content=system_prompt)]
        
        # 添加 RAG 上下文
        if rag_context:
            context_message = SystemMessage(
                content=f"相关知识背景：\n{rag_context}"
            )
            chat_messages.append(context_message)
        
        # 添加工具调用结果
        if tool_result:
            tool_result_message = SystemMessage(
                content=f"工具执行结果：{tool_result}"
            )
            chat_messages.append(tool_result_message)
        
        # 添加对话历史
        chat_messages.extend(messages)
        chat_messages.append(HumanMessage(content=user_input))
        
        # 生成回复
        response = self.llm(chat_messages)
        return response.content
    
    def add_documents_to_rag(self, texts: List[str], metadatas: List[Dict] = None):
        """向 RAG 系统添加文档"""
        self.vector_store_manager.add_texts(texts, metadatas)
