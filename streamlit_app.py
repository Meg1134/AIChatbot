"""
Streamlit Web 界面
"""
import streamlit as st
import asyncio
from typing import List
from langchain.schema import HumanMessage, AIMessage

from config import setup_environment
from src.agents import ChatbotAgent
from src.rag import DocumentLoader


# 设置页面配置
st.set_page_config(
    page_title="AI 聊天机器人",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 设置环境变量
setup_environment()


@st.cache_resource
def load_chatbot():
    """加载聊天机器人（缓存）"""
    return ChatbotAgent()


def main():
    """主函数"""
    st.title("🤖 AI 聊天机器人")
    st.markdown("---")
    
    # 侧边栏
    with st.sidebar:
        st.header("🛠️ 功能设置")
        
        # RAG 文档上传
        st.subheader("📚 知识库管理")
        uploaded_files = st.file_uploader(
            "上传文档到知识库",
            type=['txt', 'pdf', 'md'],
            accept_multiple_files=True
        )
        
        if uploaded_files:
            if st.button("添加到知识库"):
                chatbot = load_chatbot()
                document_loader = DocumentLoader()
                
                texts = []
                metadatas = []
                
                for uploaded_file in uploaded_files:
                    # 读取文件内容
                    if uploaded_file.type == "text/plain":
                        content = str(uploaded_file.read(), "utf-8")
                    else:
                        content = str(uploaded_file.read(), "utf-8")
                    
                    texts.append(content)
                    metadatas.append({
                        "source": uploaded_file.name,
                        "type": uploaded_file.type
                    })
                
                # 添加到 RAG 系统
                chatbot.add_documents_to_rag(texts, metadatas)
                st.success(f"已添加 {len(uploaded_files)} 个文档到知识库！")
        
        # 模型设置
        st.subheader("⚙️ 模型设置")
        model_choice = st.selectbox(
            "选择模型",
            ["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo-preview"],
            index=0
        )
        
        # 清除对话历史
        if st.button("🗑️ 清除对话历史"):
            if "messages" in st.session_state:
                del st.session_state.messages
            if "chatbot" in st.session_state:
                del st.session_state.chatbot
            st.rerun()
    
    # 初始化聊天历史
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    # 显示聊天历史
    chat_container = st.container()
    
    with chat_container:
        for message in st.session_state.messages:
            if isinstance(message, HumanMessage):
                with st.chat_message("user"):
                    st.markdown(message.content)
            elif isinstance(message, AIMessage):
                with st.chat_message("assistant"):
                    st.markdown(message.content)
    
    # 聊天输入
    if prompt := st.chat_input("请输入您的问题..."):
        # 添加用户消息到历史
        user_message = HumanMessage(content=prompt)
        st.session_state.messages.append(user_message)
        
        # 显示用户消息
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # 生成 AI 回复
        with st.chat_message("assistant"):
            with st.spinner("思考中..."):
                try:
                    chatbot = load_chatbot()
                    
                    # 异步调用聊天功能
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    response = loop.run_until_complete(
                        chatbot.chat(prompt, st.session_state.messages[:-1])
                    )
                    loop.close()
                    
                    # 显示回复
                    st.markdown(response)
                    
                    # 添加 AI 回复到历史
                    ai_message = AIMessage(content=response)
                    st.session_state.messages.append(ai_message)
                    
                except Exception as e:
                    error_message = f"抱歉，处理您的请求时出现错误：{str(e)}"
                    st.error(error_message)
                    
                    # 添加错误消息到历史
                    ai_message = AIMessage(content=error_message)
                    st.session_state.messages.append(ai_message)
    
    # 功能展示
    st.markdown("---")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.info("🧮 **数学计算**\n\n例：计算 25 * 4 + 10")
    
    with col2:
        st.info("🌤️ **天气查询**\n\n例：北京的天气怎么样？")
    
    with col3:
        st.info("🔍 **信息搜索**\n\n例：搜索人工智能最新发展")
    
    with col4:
        st.info("📚 **知识问答**\n\n基于上传的文档回答问题")
    
    # 使用示例
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
    main()
