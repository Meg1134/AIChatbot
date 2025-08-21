"""
天气查询工具
"""
import json
from typing import Any
from langchain.tools import BaseTool
from pydantic import BaseModel, Field


class WeatherInput(BaseModel):
    """天气查询输入模型"""
    city: str = Field(description="要查询天气的城市名称")


class WeatherTool(BaseTool):
    """天气查询工具类"""
    
    name: str = "weather"
    description: str = "查询指定城市的天气信息"
    args_schema: type[BaseModel] = WeatherInput
    
    def _run(self, city: str) -> str:
        """查询天气信息"""
        try:
            # 这里使用模拟天气数据，实际应用中可以集成真实的天气API
            # 比如 OpenWeatherMap API
            
            # 模拟天气数据
            mock_weather_data = {
                "北京": {
                    "temperature": "22°C",
                    "condition": "晴朗",
                    "humidity": "45%",
                    "wind": "北风 3级"
                },
                "上海": {
                    "temperature": "25°C", 
                    "condition": "多云",
                    "humidity": "65%",
                    "wind": "东南风 2级"
                },
                "广州": {
                    "temperature": "28°C",
                    "condition": "小雨",
                    "humidity": "80%",
                    "wind": "南风 1级"
                }
            }
            
            # 获取天气信息
            weather = mock_weather_data.get(city)
            if not weather:
                # 提供默认天气信息
                weather = {
                    "temperature": "20°C",
                    "condition": "晴朗",
                    "humidity": "50%",
                    "wind": "微风"
                }
            
            result = (
                f"{city}的天气信息:\n"
                f"温度: {weather['temperature']}\n"
                f"天气: {weather['condition']}\n"
                f"湿度: {weather['humidity']}\n"
                f"风力: {weather['wind']}"
            )
            
            return result
            
        except Exception as e:
            return f"天气查询错误: {str(e)}"
    
    async def _arun(self, city: str) -> str:
        """异步查询天气"""
        return self._run(city)
