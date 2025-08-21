from langchain_openai import ChatOpenAI
from config import setup_environment

def test_chatbot():
    """测试聊天机器人功能"""
    print("🤖 初始化聊天机器人...")
    setup_environment()

    # 创建聊天机器人实例
    chatbot = ChatOpenAI(model_name="gpt-3.5-turbo",
                         temperature=0.7,
                         base_url='https://chat.cloudapi.vip/v1/',
                         api_key='sk-8eaxcxsT7QhE4MdY6cFUsHhWCsm27Bg5nQ20moOU5iPHYIgf',
                         default_headers={"x-foo": "true"})

    # 测试简单对话
    print("💬 测试简单对话...")
    response = chatbot.invoke("你好，今天的天气怎么样？")

    print(f"🤖 聊天机器人响应: {response.content}")

test_chatbot()