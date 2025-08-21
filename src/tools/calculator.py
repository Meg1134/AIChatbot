"""
计算器工具
"""
import math
from typing import Any
from langchain.tools import BaseTool
from pydantic import BaseModel, Field


class CalculatorInput(BaseModel):
    """计算器输入模型"""
    expression: str = Field(description="要计算的数学表达式")


class CalculatorTool(BaseTool):
    """计算器工具类"""
    
    name: str = "calculator"
    description: str = "执行数学计算的工具。可以计算基本的算术运算、三角函数、对数等"
    args_schema: type[BaseModel] = CalculatorInput
    
    def _run(self, expression: str) -> str:
        """执行计算"""
        try:
            # 安全的数学表达式求值
            allowed_names = {
                k: v for k, v in math.__dict__.items() 
                if not k.startswith("__")
            }
            allowed_names.update({
                "abs": abs,
                "round": round,
                "min": min,
                "max": max,
                "sum": sum,
                "pow": pow
            })
            
            # 替换常用的数学符号
            expression = expression.replace("^", "**")
            
            result = eval(expression, {"__builtins__": {}}, allowed_names)
            return f"计算结果: {result}"
            
        except Exception as e:
            return f"计算错误: {str(e)}"
    
    async def _arun(self, expression: str) -> str:
        """异步执行计算"""
        return self._run(expression)
