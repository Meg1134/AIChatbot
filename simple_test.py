"""
简化版本的聊天机器人测试
"""
import os
import sys

# 添加项目根目录到 Python 路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import setup_environment

def test_basic_imports():
    """测试基本导入"""
    print("🔍 测试基本导入...")
    
    try:
        from config import settings
        print("✅ 配置模块导入成功")
    except Exception as e:
        print(f"❌ 配置模块导入失败: {e}")
        return False
    
    try:
        from src.tools import CalculatorTool, WeatherTool
        print("✅ 工具模块导入成功")
    except Exception as e:
        print(f"❌ 工具模块导入失败: {e}")
        return False
    
    return True

def test_tools():
    """测试工具功能"""
    print("\n🛠️ 测试工具功能...")
    
    try:
        from src.tools import CalculatorTool, WeatherTool, WebSearchTool
        
        # 测试计算器
        calc = CalculatorTool()
        result = calc._run("2 + 3 * 4")
        print(f"✅ 计算器测试: 2 + 3 * 4 = {result}")
        
        # 测试天气工具
        weather = WeatherTool()
        result = weather._run("北京")
        print(f"✅ 天气查询测试成功")
        
        # 测试搜索工具
        search = WebSearchTool()
        result = search._run("人工智能")
        print(f"✅ 搜索测试成功")
        
        return True
        
    except Exception as e:
        print(f"❌ 工具测试失败: {e}")
        return False

def test_simple_chat():
    """测试简单对话"""
    print("\n💬 测试简单对话...")
    
    try:
        # 设置环境变量
        setup_environment()
        
        # 简单的对话测试（不使用复杂的依赖）
        from src.tools import CalculatorTool
        
        calc_tool = CalculatorTool()
        questions = [
            "计算 10 + 20",
            "求 5 * 8 的结果",
            "100 / 4 等于多少"
        ]
        
        for question in questions:
            print(f"\n👤 问题: {question}")
            
            # 简单的数学计算识别
            import re
            math_pattern = r'[\d+\-*/().\s]+'
            matches = re.findall(math_pattern, question)
            
            if matches:
                expression = max(matches, key=len).strip()
                result = calc_tool._run(expression)
                print(f"🤖 回答: {result}")
            else:
                print("🤖 回答: 这是一个AI聊天机器人，可以进行数学计算、天气查询等功能。")
        
        return True
        
    except Exception as e:
        print(f"❌ 对话测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("🤖 AI 聊天机器人 - 基础功能测试")
    print("=" * 50)
    
    # 测试基本导入
    if not test_basic_imports():
        print("\n❌ 基础导入测试失败，请检查依赖安装")
        return
    
    # 测试工具
    if not test_tools():
        print("\n❌ 工具测试失败")
        return
    
    # 测试简单对话
    if not test_simple_chat():
        print("\n❌ 对话测试失败")
        return
    
    print("\n" + "=" * 50)
    print("✅ 所有基础测试通过！")
    print("\n💡 下一步:")
    print("1. 启动 Streamlit 应用: streamlit run streamlit_app.py")
    print("2. 启动 API 服务: python main.py")
    print("3. 访问 Web 界面: http://localhost:8501")

if __name__ == "__main__":
    main()
