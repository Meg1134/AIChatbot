"""
示例数据和测试脚本
"""
import asyncio
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import setup_environment
from src.agents import ChatbotAgent
from src.rag import DocumentLoader


def add_sample_documents():
    """添加示例文档到知识库"""
    # 示例文档内容
    sample_docs = [
        """
        人工智能（Artificial Intelligence，AI）是指由人制造出来的机器所表现出来的智能。
        通常人工智能是指通过普通计算机程序来呈现人类智能的技术。
        AI的研究领域包括机器学习、深度学习、自然语言处理、计算机视觉等。
        """,
        """
        机器学习是人工智能的一个重要分支，它通过算法使计算机能够从数据中学习。
        主要类型包括监督学习、无监督学习和强化学习。
        常见的机器学习算法有线性回归、决策树、随机森林、支持向量机、神经网络等。
        """,
        """
        大语言模型（Large Language Model，LLM）是基于Transformer架构的深度学习模型。
        著名的大语言模型包括GPT系列、BERT、T5等。
        这些模型在自然语言理解和生成任务上表现出色。
        """,
        """
        LangChain是一个用于构建基于语言模型应用的框架。
        它提供了链式调用、智能体、记忆管理等功能。
        LangGraph是LangChain的扩展，专门用于构建有状态的智能体应用。
        """,
        """
        RAG（Retrieval Augmented Generation）是一种结合检索和生成的技术。
        它首先从知识库中检索相关信息，然后基于检索到的信息生成回答。
        RAG可以有效解决大语言模型的知识更新和幻觉问题。
        """
    ]
    
    metadatas = [
        {"source": "ai_intro.txt", "topic": "人工智能基础"},
        {"source": "ml_intro.txt", "topic": "机器学习"},
        {"source": "llm_intro.txt", "topic": "大语言模型"},
        {"source": "langchain_intro.txt", "topic": "LangChain"},
        {"source": "rag_intro.txt", "topic": "RAG技术"}
    ]
    
    return sample_docs, metadatas


async def test_chatbot():
    """测试聊天机器人功能"""
    print("🤖 初始化聊天机器人...")
    setup_environment()
    
    chatbot = ChatbotAgent()
    
    # 添加示例文档
    print("📚 添加示例文档到知识库...")
    # sample_docs, metadatas = add_sample_documents()
    # chatbot.add_documents_to_rag(sample_docs, metadatas)
    print("✅ 示例文档添加完成")
    
    # 测试对话
    test_questions = [
        "你好！",
        "计算 123 + 456",
        "北京的天气怎么样？",
        "什么是人工智能？",
        "解释一下机器学习",
        "RAG技术是什么？",
        "搜索最新的AI技术",
        "计算 sin(30) + cos(60)"
    ]
    
    print("\n🎯 开始测试对话功能...")
    print("=" * 60)
    
    for question in test_questions:
        print(f"\n👤 用户: {question}")
        print("🤖 AI思考中...")
        
        try:
            response = await chatbot.chat(question)
            print(f"🤖 AI: {response}")
        except Exception as e:
            print(f"❌ 错误: {e}")
        
        print("-" * 60)


async def test_tools():
    """测试工具功能"""
    print("\n🛠️ 测试工具功能...")
    
    from src.tools import CalculatorTool, WeatherTool, WebSearchTool
    
    # 测试计算器
    calc = CalculatorTool()
    result = calc._run("2 + 3 * 4")
    print(f"计算器测试: 2 + 3 * 4 = {result}")
    
    # 测试天气工具
    weather = WeatherTool()
    result = weather._run("北京")
    print(f"天气查询测试: {result}")
    
    # 测试搜索工具
    search = WebSearchTool()
    result = search._run("人工智能")
    print(f"搜索测试: {result}")


async def main():
    """主测试函数"""
    print("🚀 开始测试 AI 聊天机器人")
    print("=" * 60)
    
    # 测试工具
    # await test_tools()
    
    # 测试聊天机器人
    await test_chatbot()
    
    print("\n✅ 测试完成！")
    print("\n💡 使用说明:")
    print("1. 启动 Web 界面: streamlit run streamlit_app.py")
    print("2. 启动 API 服务: python main.py")
    print("3. 访问 API 文档: http://localhost:8000/docs")


if __name__ == "__main__":
    asyncio.run(main())
