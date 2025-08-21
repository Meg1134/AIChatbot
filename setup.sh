#!/bin/bash

# AI 聊天机器人安装和启动脚本

echo "🤖 AI 聊天机器人 - 安装和启动脚本"
echo "=================================="

# 检查 Python 版本
echo "📋 检查 Python 环境..."
python --version

# 安装依赖
echo "📦 安装 Python 依赖包..."
pip install -r requirements.txt

# 复制环境变量文件
if [ ! -f .env ]; then
    echo "⚙️  创建环境变量文件..."
    cp .env.example .env
    echo "请编辑 .env 文件并添加您的 API 密钥"
fi

# 创建数据目录
echo "📁 创建数据目录..."
mkdir -p data/chroma_db

echo "✅ 安装完成！"
echo ""
echo "🚀 启动选项："
echo "1. Web 界面: streamlit run streamlit_app.py"
echo "2. API 服务: python main.py"
echo "3. 测试功能: python test_chatbot.py"
echo ""
echo "📚 访问地址："
echo "- Web 界面: http://localhost:8501"
echo "- API 文档: http://localhost:8000/docs"
