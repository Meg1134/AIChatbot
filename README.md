# AI Chatbot with LangChain, LangGraph, MCP, and RAG

一个集成了 LangChain、LangGraph、MCP（Model Context Protocol）和 RAG（检索增强生成）的智能聊天机器人，具有工具调用功能。

## 功能特性

- **LangChain 集成**：使用 LangChain 构建智能对话流程
- **LangGraph 状态管理**：通过 LangGraph 管理复杂的对话状态
- **MCP 协议支持**：集成 Model Context Protocol 进行模型通信
- **RAG 检索增强**：基于向量数据库的知识检索和增强生成
- **工具调用**：支持多种外部工具和 API 调用
- **多种接口**：Streamlit Web UI 和 FastAPI 后端接口

## 项目结构

```
ai-chatbot/
├── src/
│   ├── agents/           # LangGraph 智能体
│   ├── chains/           # LangChain 链式处理
│   ├── tools/            # 工具调用实现
│   ├── rag/              # RAG 相关组件
│   ├── mcp/              # MCP 协议实现
│   └── api/              # API 接口
├── data/                 # 数据存储
├── config/               # 配置文件
├── streamlit_app.py      # Streamlit Web 界面
├── main.py               # FastAPI 后端服务
└── requirements.txt      # 依赖包
```

## 快速开始

### 方式一：使用安装脚本

```bash
# Windows
setup.bat

# Linux/Mac
chmod +x setup.sh
./setup.sh
```

### 方式二：手动安装

1. 安装依赖：

```bash
pip install -r requirements.txt
```

2. 配置环境变量：

```bash
cp .env.example .env
# 编辑 .env 文件，添加你的 API 密钥
```

3. 启动 Web 界面：

```bash
streamlit run streamlit_app.py
```

4. 或启动 API 服务：

```bash
python main.py
```

5. 测试功能：

```bash
python test_chatbot.py
```

## 环境变量配置

在 `.env` 文件中配置以下变量：

```
OPENAI_API_KEY=your_openai_api_key
LANGCHAIN_API_KEY=your_langchain_api_key
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=ai-chatbot
```

## 使用说明

### Web 界面
访问 http://localhost:8501 使用 Streamlit Web 界面进行对话。

### API 接口
启动 FastAPI 服务后，访问 http://localhost:8000/docs 查看 API 文档。

## 主要组件

- **智能体 (Agents)**：基于 LangGraph 的状态管理智能体
- **工具 (Tools)**：集成各种外部工具和 API
- **RAG 系统**：向量存储和检索增强生成
- **MCP 协议**：模型上下文协议支持
