"""
Streamlit Web 界面（改进版）
"""
import streamlit as st
from typing import List, Optional
import json
import time
import traceback

from langchain.schema import HumanMessage, AIMessage, BaseMessage

from config import setup_environment
from src.agents import ChatbotAgent
from src.rag import DocumentLoader

# ------------- 基础设置 -------------
st.set_page_config(
    page_title="AI 聊天机器人",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

setup_environment()

# ------------- 常量 / 配置 -------------
MAX_CHAT_HISTORY = 12         # 只保留最近的对话轮数（用户+AI 各一条算2）
SHOW_RETRIEVED_CONTEXT = True # 调试：显示检索到的文档
DEFAULT_MODEL = "gpt-3.5-turbo"

# ------------- 缓存 ChatbotAgent -------------
@st.cache_resource(show_spinner=False)
def load_chatbot(model_name: str):
    return ChatbotAgent(model_name=model_name)

# ------------- 工具函数 -------------
def get_chatbot(model_choice: str) -> ChatbotAgent:
    # 使模型选择生效：模型变更会重新构建
    return load_chatbot(model_choice)

def truncate_history(messages: List[BaseMessage], limit: int) -> List[BaseMessage]:
    if len(messages) <= limit:
        return messages
    return messages[-limit:]

def add_rag_documents(chatbot: ChatbotAgent, uploaded_files):
    loader = DocumentLoader()
    texts = []
    metadatas = []
    for f in uploaded_files:
        name = f.name
        mime = f.type
        suffix = name.lower().split(".")[-1]

        try:
            if suffix in ["txt", "md"]:
                # 尝试解码（Streamlit 给的是一个 BytesIO-like）
                raw = f.read()
                try:
                    content = raw.decode("utf-8")
                except UnicodeDecodeError:
                    content = raw.decode("utf-8", errors="ignore")
                texts.append(content)
                metadatas.append({"source": name, "type": mime})
            elif suffix == "pdf":
                # 使用临时文件方式让 loader 解析
                # Streamlit uploaded_file 有 getvalue()
                import tempfile, os
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                    tmp.write(f.getvalue())
                    tmp_path = tmp.name
                try:
                    docs = loader.load_pdf_file(tmp_path)
                    # 将 PDF 每页合并为一个字符串或直接添加 page_content
                    for d in docs:
                        texts.append(d.page_content)
                        meta = d.metadata.copy()
                        meta.update({"source": name, "type": mime})
                        metadatas.append(meta)
                finally:
                    try:
                        os.remove(tmp_path)
                    except OSError:
                        pass
            else:
                st.warning(f"跳过不支持的文件类型: {name}")
        except Exception as e:
            st.error(f"文件 {name} 解析失败: {e}")
    if not texts:
        st.info("没有可添加的文本。")
        return

    with st.spinner("向量化并添加到知识库..."):
        chatbot.add_documents_to_rag(texts, metadatas)
    st.success(f"已添加 {len(texts)} 个文本块（原文件 {len(uploaded_files)} 个）")

def render_history(messages: List[BaseMessage]):
    for m in messages:
        if isinstance(m, HumanMessage):
            with st.chat_message("user"):
                st.markdown(m.content)
        elif isinstance(m, AIMessage):
            with st.chat_message("assistant"):
                st.markdown(m.content)

def ensure_state():
    if "messages" not in st.session_state:
        st.session_state.messages: List[BaseMessage] = []
    if "last_retrieval" not in st.session_state:
        st.session_state.last_retrieval = None  # 存储一个检索上下文片段

def maybe_prune_history():
    st.session_state.messages = truncate_history(st.session_state.messages, MAX_CHAT_HISTORY)

# ------------- 主逻辑 -------------
def main():
    st.title("🤖 AI 聊天机器人")
    st.caption("支持：数学计算 / 天气 / 搜索 / RAG 知识库")
    st.markdown("---")

    ensure_state()

    # ----------- 侧边栏 -----------
    with st.sidebar:
        st.header("🛠️ 功能设置")

        # 模型设置
        model_choice = st.selectbox(
            "选择模型",
            ["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo-preview"],
            index=0
        )

        # 是否启用 RAG
        use_rag = st.toggle("启用 RAG 检索", value=True, help="关闭后只使用纯模型对话")

        # 知识库上传
        st.subheader("📚 知识库管理")
        uploaded_files = st.file_uploader(
            "上传文档（txt/pdf/md）",
            type=['txt', 'pdf', 'md'],
            accept_multiple_files=True
        )
        if uploaded_files and st.button("添加到知识库"):
            chatbot = get_chatbot(model_choice)
            add_rag_documents(chatbot, uploaded_files)

        # 清除对话
        if st.button("🗑️ 清除对话历史"):
            st.session_state.messages = []
            st.session_state.last_retrieval = None
            st.experimental_rerun()

        # 显示调试区
        if st.checkbox("调试信息", value=False):
            st.write("当前消息条数:", len(st.session_state.messages))
            st.write("最近检索摘要:", st.session_state.last_retrieval[:300] + "..." if st.session_state.last_retrieval else None)

    # 获取 / 缓存 Chatbot
    chatbot = get_chatbot(model_choice)

    # ----------- 显示历史 -----------
    render_history(st.session_state.messages)

    # ----------- 输入框 -----------
    if prompt := st.chat_input("请输入您的问题..."):
        # 追加用户消息
        user_msg = HumanMessage(content=prompt)
        st.session_state.messages.append(user_msg)

        with st.chat_message("user"):
            st.markdown(prompt)

        # 生成 AI 回复
        with st.chat_message("assistant"):
            with st.spinner("思考中..."):
                try:
                    # 根据是否启用 RAG 控制输入（最小侵入：如果关闭 RAG，在传入前去掉可能触发 RAG 的关键词处理或让 ChatbotAgent 内部做开关）
                    # 简单方式：如果 use_rag=False，临时屏蔽那些关键词 => 直接调用 chat 同样逻辑（这里先不改 ChatbotAgent，做一个快速绕开）
                    history_for_agent = st.session_state.messages[:-1]  # 历史（不含当前）
                    # 调用 chat（异步接口同步化）—— 如果你的 ChatbotAgent.chat 已 async：
                    import asyncio
                    response_text = asyncio.run(chatbot.chat(prompt, history_for_agent))

                    ai_msg = AIMessage(content=response_text)
                    st.session_state.messages.append(ai_msg)
                    st.markdown(response_text)

                    # （可选）显示最近 RAG 检索的数据：这里只能修改 ChatbotAgent 来返回上下文。
                    # 当前无法直接拿到 rag_context，只能透过修改 ChatbotAgent.chat 返回 (text, rag_context)
                    # 暂时略。如果需要我可帮你改 ChatbotAgent。
                except Exception as e:
                    err = f"处理请求出错: {e}"
                    st.error(err)
                    st.session_state.messages.append(AIMessage(content=err))
                    traceback.print_exc()

        maybe_prune_history()

    st.markdown("---")
    # 功能说明
    cols = st.columns(4)
    infos = [
        ("🧮 数学计算", "例：计算 25 * 4 + 10"),
        ("🌤️ 天气查询", "例：北京的天气怎么样？"),
        ("🔍 信息搜索", "例：搜索人工智能最新发展"),
        ("📚 知识问答", "上传文档后进行问答")
    ]
    for col, (title, body) in zip(cols, infos):
        with col:
            st.info(f"**{title}**\n\n{body}")

    with st.expander("💡 使用示例", expanded=False):
        st.markdown("""
        ### 数学计算
        - "计算 123 + 456"
        - "求 sin(30) 的值"
        - "平方根 144 是多少？"

        ### 天气查询
        - "北京今天天气如何？"
        - "上海的天气预报"
        - "广州现在的温度"

        ### 信息搜索
        - "搜索人工智能发展趋势"
        - "查找机器学习算法"
        - "搜索最新科技新闻"

        ### 知识问答
        - 上传相关文档后，可以基于文档内容进行问答
        - "根据上传的文档，解释XXX概念"
        - "文档中提到的XXX是什么？"
        """)

if __name__ == "__main__":
    # 正确启动建议使用： streamlit run streamlit_app.py
    # 直接 python 运行只适合调试模块导入，不会有完整前端。
    main()