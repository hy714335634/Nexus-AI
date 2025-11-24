#!/usr/bin/env python3
"""
天气查询工具集

提供天气数据查询、城市名称规范化和天气数据格式化功能
"""

import json
import os
import time
import re
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path

try:
    import requests
except ImportError:
    raise ImportError("需要安装requests库: pip install requests")

from strands import tool

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 缓存目录
CACHE_DIR = Path(".cache/weather_query_agent")
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# 城市名称映射表（中英文对照）
CITY_NAME_MAPPING = {
    # 直辖市
    "北京": "Beijing", "北京市": "Beijing",
    "上海": "Shanghai", "上海市": "Shanghai",
    "天津": "Tianjin", "天津市": "Tianjin",
    "重庆": "Chongqing", "重庆市": "Chongqing",
    
    # 省会城市
    "广州": "Guangzhou", "广州市": "Guangzhou",
    "深圳": "Shenzhen", "深圳市": "Shenzhen",
    "杭州": "Hangzhou", "杭州市": "Hangzhou",
    "南京": "Nanjing", "南京市": "Nanjing",
    "武汉": "Wuhan", "武汉市": "Wuhan",
    "成都": "Chengdu", "成都市": "Chengdu",
    "西安": "Xi'an", "西安市": "Xi'an",
    "郑州": "Zhengzhou", "郑州市": "Zhengzhou",
    "济南": "Jinan", "济南市": "Jinan",
    "沈阳": "Shenyang", "沈阳市": "Shenyang",
    "长春": "Changchun", "长春市": "Changchun",
    "哈尔滨": "Harbin", "哈尔滨市": "Harbin",
    "石家庄": "Shijiazhuang", "石家庄市": "Shijiazhuang",
    "太原": "Taiyuan", "太原市": "Taiyuan",
    "呼和浩特": "Hohhot", "呼和浩特市": "Hohhot",
    "合肥": "Hefei", "合肥市": "Hefei",
    "福州": "Fuzhou", "福州市": "Fuzhou",
    "南昌": "Nanchang", "南昌市": "Nanchang",
    "长沙": "Changsha", "长沙市": "Changsha",
    "南宁": "Nanning", "南宁市": "Nanning",
    "海口": "Haikou", "海口市": "Haikou",
    "贵阳": "Guiyang", "贵阳市": "Guiyang",
    "昆明": "Kunming", "昆明市": "Kunming",
    "拉萨": "Lhasa", "拉萨市": "Lhasa",
    "兰州": "Lanzhou", "兰州市": "Lanzhou",
    "西宁": "Xining", "西宁市": "Xining",
    "银川": "Yinchuan", "银川市": "Yinchuan",
    "乌鲁木齐": "Urumqi", "乌鲁木齐市": "Urumqi",
    
    # 其他主要城市
    "苏州": "Suzhou", "苏州市": "Suzhou",
    "无锡": "Wuxi", "无锡市": "Wuxi",
    "宁波": "Ningbo", "宁波市": "Ningbo",
    "温州": "Wenzhou", "温州市": "Wenzhou",
    "青岛": "Qingdao", "青岛市": "Qingdao",
    "大连": "Dalian", "大连市": "Dalian",
    "厦门": "Xiamen", "厦门市": "Xiamen",
    "东莞": "Dongguan", "东莞市": "Dongguan",
    "佛山": "Foshan", "佛山市": "Foshan",
    "珠海": "Zhuhai", "珠海市": "Zhuhai",
    
    # 国际城市
    "纽约": "New York", "伦敦": "London", "巴黎": "Paris",
    "东京": "Tokyo", "首尔": "Seoul", "新加坡": "Singapore",
    "悉尼": "Sydney", "莫斯科": "Moscow", "柏林": "Berlin",
    "罗马": "Rome", "马德里": "Madrid", "阿姆斯特丹": "Amsterdam",
    "曼谷": "Bangkok", "迪拜": "Dubai", "孟买": "Mumbai",
    "多伦多": "Toronto", "温哥华": "Vancouver", "洛杉矶": "Los Angeles",
    "旧金山": "San Francisco", "芝加哥": "Chicago", "波士顿": "Boston",
}

# 反向映射
CITY_NAME_REVERSE_MAPPING = {v: k for k, v in CITY_NAME_MAPPING.items() if "市" not in k}

# 天气描述映射（英文到中文）
WEATHER_DESC_MAPPING = {
    "clear sky": "晴空",
    "few clouds": "少云",
    "scattered clouds": "多云",
    "broken clouds": "阴天",
    "overcast clouds": "阴天",
    "shower rain": "阵雨",
    "rain": "雨",
    "light rain": "小雨",
    "moderate rain": "中雨",
    "heavy rain": "大雨",
    "thunderstorm": "雷暴",
    "snow": "雪",
    "light snow": "小雪",
    "mist": "薄雾",
    "fog": "雾",
    "haze": "霾",
    "dust": "浮尘",
}

# 天气图标emoji映射
WEATHER_EMOJI = {
    "clear": "☀️",
    "clouds": "☁️",
    "rain": "🌧️",
    "drizzle": "🌦️",
    "thunderstorm": "⛈️",
    "snow": "❄️",
    "mist": "🌫️",
    "fog": "🌫️",
    "haze": "😶‍🌫️",
}


class WeatherCache:
    """天气数据缓存管理器"""
    
    def __init__(self, cache_duration: int = 300):
        """
        初始化缓存管理器
        
        Args:
            cache_duration: 缓存有效期（秒），默认5分钟
        """
        self.cache_duration = cache_duration
        self.cache_file = CACHE_DIR / "weather_cache.json"
        self._load_cache()
    
    def _load_cache(self):
        """加载缓存数据"""
        try:
            if self.cache_file.exists():
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    self.cache = json.load(f)
            else:
                self.cache = {}
        except Exception as e:
            logger.warning(f"加载缓存失败: {e}")
            self.cache = {}
    
    def _save_cache(self):
        """保存缓存数据"""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存缓存失败: {e}")
    
    def get(self, key: str) -> Optional[Dict]:
        """
        获取缓存数据
        
        Args:
            key: 缓存键
            
        Returns:
            缓存的数据，如果不存在或已过期则返回None
        """
        if key not in self.cache:
            return None
        
        cached_data = self.cache[key]
        cache_time = cached_data.get("cache_time", 0)
        
        # 检查是否过期
        if time.time() - cache_time > self.cache_duration:
            del self.cache[key]
            self._save_cache()
            return None
        
        return cached_data.get("data")
    
    def set(self, key: str, data: Dict):
        """
        设置缓存数据
        
        Args:
            key: 缓存键
            data: 要缓存的数据
        """
        self.cache[key] = {
            "data": data,
            "cache_time": time.time()
        }
        self._save_cache()
    
    def clear(self):
        """清空所有缓存"""
        self.cache = {}
        self._save_cache()


# 全局缓存实例
weather_cache = WeatherCache()


def detect_language(text: str) -> str:
    """
    检测文本语言
    
    Args:
        text: 输入文本
        
    Returns:
        语言代码 ('zh' 或 'en')
    """
    # 检查是否包含中文字符
    if re.search(r'[\u4e00-\u9fff]', text):
        return 'zh'
    return 'en'


def celsius_to_fahrenheit(celsius: float) -> float:
    """
    摄氏度转华氏度
    
    Args:
        celsius: 摄氏温度
        
    Returns:
        华氏温度
    """
    return celsius * 9/5 + 32


def fahrenheit_to_celsius(fahrenheit: float) -> float:
    """
    华氏度转摄氏度
    
    Args:
        fahrenheit: 华氏温度
        
    Returns:
        摄氏温度
    """
    return (fahrenheit - 32) * 5/9


@tool
def city_name_normalizer_tool(city_name: str, language: Optional[str] = None) -> str:
    """
    规范化和验证用户输入的城市名称
    
    Args:
        city_name (str): 用户输入的城市名称
        language (str, optional): 输入语言类型，自动检测如果不提供
        
    Returns:
        str: JSON格式的规范化结果
    """
    try:
        logger.info(f"规范化城市名称: {city_name}")
        
        # 清理输入
        original_name = city_name
        cleaned_name = city_name.strip()
        
        # 检测语言
        if language is None:
            language = detect_language(cleaned_name)
        
        # 规范化名称
        normalized_name = cleaned_name
        suggestions = []
        confidence = 1.0
        
        # 中文名称处理
        if language == 'zh':
            # 移除"市"后缀
            if cleaned_name.endswith('市'):
                cleaned_name = cleaned_name[:-1]
            
            # 查找映射
            if cleaned_name in CITY_NAME_MAPPING:
                normalized_name = CITY_NAME_MAPPING[cleaned_name]
                confidence = 1.0
            elif cleaned_name + '市' in CITY_NAME_MAPPING:
                normalized_name = CITY_NAME_MAPPING[cleaned_name + '市']
                confidence = 1.0
            else:
                # 模糊匹配
                matches = []
                for cn_name, en_name in CITY_NAME_MAPPING.items():
                    if cleaned_name in cn_name or cn_name in cleaned_name:
                        matches.append((cn_name, en_name))
                
                if matches:
                    normalized_name = matches[0][1]
                    confidence = 0.8
                    suggestions = [m[0] for m in matches[:5]]
                else:
                    # 使用原始名称
                    normalized_name = cleaned_name
                    confidence = 0.5
                    suggestions = list(CITY_NAME_MAPPING.keys())[:5]
        
        # 英文名称处理
        else:
            # 首字母大写
            cleaned_name = cleaned_name.title()
            
            # 查找映射
            if cleaned_name in CITY_NAME_MAPPING.values():
                normalized_name = cleaned_name
                confidence = 1.0
            else:
                # 模糊匹配
                matches = []
                for cn_name, en_name in CITY_NAME_MAPPING.items():
                    if cleaned_name.lower() in en_name.lower() or en_name.lower() in cleaned_name.lower():
                        matches.append((cn_name, en_name))
                
                if matches:
                    normalized_name = matches[0][1]
                    confidence = 0.8
                    suggestions = [m[1] for m in matches[:5]]
                else:
                    # 使用原始名称
                    normalized_name = cleaned_name
                    confidence = 0.5
                    suggestions = list(CITY_NAME_MAPPING.values())[:5]
        
        result = {
            "success": True,
            "normalized_name": normalized_name,
            "original_name": original_name,
            "language": language,
            "confidence": confidence,
            "suggestions": suggestions if confidence < 1.0 else []
        }
        
        logger.info(f"城市名称规范化完成: {original_name} -> {normalized_name}")
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"城市名称规范化失败: {e}")
        return json.dumps({
            "success": False,
            "error": {
                "code": "NORMALIZATION_ERROR",
                "message": f"城市名称规范化失败: {str(e)}"
            },
            "original_name": city_name
        }, ensure_ascii=False, indent=2)


@tool
def weather_query_tool(
    city_name: str,
    language: str = "zh",
    units: str = "metric",
    use_cache: bool = True
) -> str:
    """
    调用天气API获取指定城市的实时天气信息
    
    Args:
        city_name (str): 城市名称，支持中英文，如"北京", "Beijing"
        language (str, optional): 返回语言，支持"zh"(中文)、"en"(英文)，默认为"zh"
        units (str, optional): 温度单位，支持"metric"(摄氏度)、"imperial"(华氏度)，默认为"metric"
        use_cache (bool, optional): 是否使用缓存，默认为True
        
    Returns:
        str: JSON格式的天气数据
    """
    try:
        logger.info(f"查询天气: {city_name}, 语言: {language}, 单位: {units}")
        
        # 规范化城市名称
        normalized_result = json.loads(city_name_normalizer_tool(city_name))
        if not normalized_result.get("success"):
            return json.dumps({
                "success": False,
                "error": {
                    "code": "INVALID_CITY",
                    "message": "无效的城市名称"
                }
            }, ensure_ascii=False, indent=2)
        
        normalized_city = normalized_result["normalized_name"]
        
        # 检查缓存
        cache_key = f"{normalized_city}_{language}_{units}"
        if use_cache:
            cached_data = weather_cache.get(cache_key)
            if cached_data:
                logger.info(f"使用缓存数据: {cache_key}")
                return json.dumps(cached_data, ensure_ascii=False, indent=2)
        
        # 获取API密钥
        api_key = os.environ.get("OPENWEATHER_API_KEY")
        if not api_key:
            # 如果没有配置API密钥，返回模拟数据用于演示
            logger.warning("未配置OPENWEATHER_API_KEY环境变量，使用模拟数据")
            return _get_mock_weather_data(normalized_city, language, units)
        
        # 调用OpenWeatherMap API
        api_url = "https://api.openweathermap.org/data/2.5/weather"
        params = {
            "q": normalized_city,
            "appid": api_key,
            "units": units,
            "lang": "zh_cn" if language == "zh" else "en"
        }
        
        # 实现重试机制
        max_retries = 3
        retry_delay = 1
        
        for attempt in range(max_retries):
            try:
                logger.info(f"API请求尝试 {attempt + 1}/{max_retries}")
                response = requests.get(api_url, params=params, timeout=10)
                
                if response.status_code == 200:
                    # 解析响应数据
                    data = response.json()
                    result = _parse_weather_data(data, normalized_city, language, units)
                    
                    # 缓存结果
                    if use_cache:
                        weather_cache.set(cache_key, result)
                    
                    logger.info(f"天气查询成功: {normalized_city}")
                    return json.dumps(result, ensure_ascii=False, indent=2)
                
                elif response.status_code == 404:
                    return json.dumps({
                        "success": False,
                        "error": {
                            "code": "CITY_NOT_FOUND",
                            "message": f"未找到城市: {city_name}"
                        }
                    }, ensure_ascii=False, indent=2)
                
                elif response.status_code == 401:
                    return json.dumps({
                        "success": False,
                        "error": {
                            "code": "INVALID_API_KEY",
                            "message": "API密钥无效"
                        }
                    }, ensure_ascii=False, indent=2)
                
                elif response.status_code == 429:
                    return json.dumps({
                        "success": False,
                        "error": {
                            "code": "API_QUOTA_EXCEEDED",
                            "message": "API配额已超限"
                        }
                    }, ensure_ascii=False, indent=2)
                
                else:
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay)
                        retry_delay *= 2
                        continue
                    
                    return json.dumps({
                        "success": False,
                        "error": {
                            "code": "API_ERROR",
                            "message": f"API请求失败: HTTP {response.status_code}"
                        }
                    }, ensure_ascii=False, indent=2)
            
            except requests.exceptions.Timeout:
                if attempt < max_retries - 1:
                    logger.warning(f"请求超时，重试中... ({attempt + 1}/{max_retries})")
                    time.sleep(retry_delay)
                    retry_delay *= 2
                    continue
                
                return json.dumps({
                    "success": False,
                    "error": {
                        "code": "REQUEST_TIMEOUT",
                        "message": "请求超时，请稍后重试"
                    }
                }, ensure_ascii=False, indent=2)
            
            except requests.exceptions.ConnectionError:
                if attempt < max_retries - 1:
                    logger.warning(f"连接失败，重试中... ({attempt + 1}/{max_retries})")
                    time.sleep(retry_delay)
                    retry_delay *= 2
                    continue
                
                return json.dumps({
                    "success": False,
                    "error": {
                        "code": "CONNECTION_ERROR",
                        "message": "网络连接失败"
                    }
                }, ensure_ascii=False, indent=2)
        
        return json.dumps({
            "success": False,
            "error": {
                "code": "MAX_RETRIES_EXCEEDED",
                "message": "达到最大重试次数"
            }
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"天气查询失败: {e}")
        return json.dumps({
            "success": False,
            "error": {
                "code": "UNKNOWN_ERROR",
                "message": f"未知错误: {str(e)}"
            }
        }, ensure_ascii=False, indent=2)


def _parse_weather_data(data: Dict, city_name: str, language: str, units: str) -> Dict:
    """
    解析天气API响应数据
    
    Args:
        data: API响应数据
        city_name: 城市名称
        language: 语言
        units: 单位
        
    Returns:
        格式化的天气数据
    """
    # 提取数据
    main = data.get("main", {})
    weather = data.get("weather", [{}])[0]
    wind = data.get("wind", {})
    clouds = data.get("clouds", {})
    sys_data = data.get("sys", {})
    
    # 温度数据
    temp = main.get("temp", 0)
    feels_like = main.get("feels_like", 0)
    
    # 如果是摄氏度，也计算华氏度
    if units == "metric":
        temp_celsius = temp
        temp_fahrenheit = celsius_to_fahrenheit(temp)
    else:
        temp_fahrenheit = temp
        temp_celsius = fahrenheit_to_celsius(temp)
    
    # 天气描述
    description = weather.get("description", "")
    if language == "zh" and description.lower() in WEATHER_DESC_MAPPING:
        description = WEATHER_DESC_MAPPING[description.lower()]
    
    # 日出日落时间
    sunrise_timestamp = sys_data.get("sunrise", 0)
    sunset_timestamp = sys_data.get("sunset", 0)
    
    sunrise = datetime.fromtimestamp(sunrise_timestamp).strftime("%H:%M:%S") if sunrise_timestamp else "N/A"
    sunset = datetime.fromtimestamp(sunset_timestamp).strftime("%H:%M:%S") if sunset_timestamp else "N/A"
    
    # 构建结果
    result = {
        "success": True,
        "data": {
            "city": city_name,
            "country": sys_data.get("country", ""),
            "temperature": temp,
            "temperature_celsius": round(temp_celsius, 1),
            "temperature_fahrenheit": round(temp_fahrenheit, 1),
            "feels_like": feels_like,
            "humidity": main.get("humidity", 0),
            "pressure": main.get("pressure", 0),
            "description": description,
            "wind_speed": wind.get("speed", 0),
            "wind_direction": wind.get("deg", 0),
            "clouds": clouds.get("all", 0),
            "visibility": data.get("visibility", 0),
            "sunrise": sunrise,
            "sunset": sunset,
            "timestamp": datetime.now().isoformat()
        }
    }
    
    return result


def _get_mock_weather_data(city_name: str, language: str, units: str) -> str:
    """
    生成模拟天气数据（用于演示）
    
    Args:
        city_name: 城市名称
        language: 语言
        units: 单位
        
    Returns:
        JSON格式的模拟天气数据
    """
    import random
    
    # 随机生成温度
    if units == "metric":
        temp = round(random.uniform(-10, 35), 1)
        temp_celsius = temp
        temp_fahrenheit = round(celsius_to_fahrenheit(temp), 1)
    else:
        temp = round(random.uniform(14, 95), 1)
        temp_fahrenheit = temp
        temp_celsius = round(fahrenheit_to_celsius(temp), 1)
    
    # 随机选择天气状况
    weather_conditions = [
        ("晴空", "clear sky", "☀️") if language == "zh" else ("clear sky", "clear sky", "☀️"),
        ("多云", "scattered clouds", "☁️") if language == "zh" else ("scattered clouds", "scattered clouds", "☁️"),
        ("小雨", "light rain", "🌧️") if language == "zh" else ("light rain", "light rain", "🌧️"),
    ]
    
    condition = random.choice(weather_conditions)
    
    result = {
        "success": True,
        "data": {
            "city": city_name,
            "country": "CN",
            "temperature": temp,
            "temperature_celsius": temp_celsius,
            "temperature_fahrenheit": temp_fahrenheit,
            "feels_like": round(temp - random.uniform(-2, 2), 1),
            "humidity": random.randint(30, 90),
            "pressure": random.randint(990, 1030),
            "description": condition[0],
            "wind_speed": round(random.uniform(0, 15), 1),
            "wind_direction": random.randint(0, 360),
            "clouds": random.randint(0, 100),
            "visibility": random.randint(5000, 10000),
            "sunrise": "06:30:00",
            "sunset": "18:30:00",
            "timestamp": datetime.now().isoformat()
        },
        "note": "这是模拟数据，请配置OPENWEATHER_API_KEY环境变量以获取真实天气数据"
    }
    
    return json.dumps(result, ensure_ascii=False, indent=2)


@tool
def weather_formatter_tool(
    weather_data: str,
    format_type: str = "simple",
    language: str = "zh"
) -> str:
    """
    格式化天气数据为用户友好的输出格式
    
    Args:
        weather_data (str): 原始天气数据（JSON字符串）
        format_type (str, optional): 格式类型，支持"simple"(简洁)、"detailed"(详细)，默认为"simple"
        language (str, optional): 输出语言，支持"zh"(中文)、"en"(英文)，默认为"zh"
        
    Returns:
        str: JSON格式的格式化结果
    """
    try:
        logger.info(f"格式化天气数据: format_type={format_type}, language={language}")
        
        # 解析天气数据
        try:
            data = json.loads(weather_data)
        except json.JSONDecodeError:
            return json.dumps({
                "success": False,
                "error": {
                    "code": "INVALID_JSON",
                    "message": "无效的JSON数据"
                }
            }, ensure_ascii=False, indent=2)
        
        if not data.get("success"):
            return json.dumps({
                "success": False,
                "error": {
                    "code": "INVALID_WEATHER_DATA",
                    "message": "无效的天气数据"
                }
            }, ensure_ascii=False, indent=2)
        
        weather_info = data.get("data", {})
        
        # 生成格式化文本
        if format_type == "simple":
            formatted_text = _format_simple_text(weather_info, language)
            formatted_html = _format_simple_html(weather_info, language)
        else:  # detailed
            formatted_text = _format_detailed_text(weather_info, language)
            formatted_html = _format_detailed_html(weather_info, language)
        
        result = {
            "success": True,
            "formatted_text": formatted_text,
            "formatted_html": formatted_html,
            "formatted_json": weather_info
        }
        
        logger.info("天气数据格式化完成")
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"天气数据格式化失败: {e}")
        return json.dumps({
            "success": False,
            "error": {
                "code": "FORMATTING_ERROR",
                "message": f"格式化失败: {str(e)}"
            }
        }, ensure_ascii=False, indent=2)


def _format_simple_text(weather_info: Dict, language: str) -> str:
    """
    生成简洁格式的文本
    
    Args:
        weather_info: 天气信息
        language: 语言
        
    Returns:
        格式化的文本
    """
    city = weather_info.get("city", "")
    temp_c = weather_info.get("temperature_celsius", 0)
    temp_f = weather_info.get("temperature_fahrenheit", 0)
    desc = weather_info.get("description", "")
    humidity = weather_info.get("humidity", 0)
    
    # 获取天气emoji
    emoji = "🌤️"
    desc_lower = desc.lower()
    for key, value in WEATHER_EMOJI.items():
        if key in desc_lower:
            emoji = value
            break
    
    if language == "zh":
        text = f"{emoji} {city}天气\n"
        text += f"🌡️ 温度: {temp_c}°C / {temp_f}°F\n"
        text += f"☁️ 天气: {desc}\n"
        text += f"💧 湿度: {humidity}%"
    else:
        text = f"{emoji} Weather in {city}\n"
        text += f"🌡️ Temperature: {temp_c}°C / {temp_f}°F\n"
        text += f"☁️ Condition: {desc}\n"
        text += f"💧 Humidity: {humidity}%"
    
    return text


def _format_detailed_text(weather_info: Dict, language: str) -> str:
    """
    生成详细格式的文本
    
    Args:
        weather_info: 天气信息
        language: 语言
        
    Returns:
        格式化的文本
    """
    city = weather_info.get("city", "")
    country = weather_info.get("country", "")
    temp_c = weather_info.get("temperature_celsius", 0)
    temp_f = weather_info.get("temperature_fahrenheit", 0)
    feels_like = weather_info.get("feels_like", 0)
    desc = weather_info.get("description", "")
    humidity = weather_info.get("humidity", 0)
    pressure = weather_info.get("pressure", 0)
    wind_speed = weather_info.get("wind_speed", 0)
    wind_direction = weather_info.get("wind_direction", 0)
    clouds = weather_info.get("clouds", 0)
    visibility = weather_info.get("visibility", 0)
    sunrise = weather_info.get("sunrise", "")
    sunset = weather_info.get("sunset", "")
    
    # 获取天气emoji
    emoji = "🌤️"
    desc_lower = desc.lower()
    for key, value in WEATHER_EMOJI.items():
        if key in desc_lower:
            emoji = value
            break
    
    if language == "zh":
        text = f"{emoji} {city} ({country}) 天气详情\n"
        text += f"{'='*40}\n"
        text += f"🌡️ 温度信息:\n"
        text += f"   当前温度: {temp_c}°C / {temp_f}°F\n"
        text += f"   体感温度: {feels_like}°C\n"
        text += f"\n☁️ 天气状况:\n"
        text += f"   天气描述: {desc}\n"
        text += f"   云量: {clouds}%\n"
        text += f"   能见度: {visibility}米\n"
        text += f"\n💨 风力信息:\n"
        text += f"   风速: {wind_speed} m/s\n"
        text += f"   风向: {wind_direction}°\n"
        text += f"\n💧 其他信息:\n"
        text += f"   湿度: {humidity}%\n"
        text += f"   气压: {pressure} hPa\n"
        text += f"\n🌅 日出日落:\n"
        text += f"   日出: {sunrise}\n"
        text += f"   日落: {sunset}"
    else:
        text = f"{emoji} Weather Details for {city} ({country})\n"
        text += f"{'='*40}\n"
        text += f"🌡️ Temperature:\n"
        text += f"   Current: {temp_c}°C / {temp_f}°F\n"
        text += f"   Feels Like: {feels_like}°C\n"
        text += f"\n☁️ Conditions:\n"
        text += f"   Description: {desc}\n"
        text += f"   Cloud Cover: {clouds}%\n"
        text += f"   Visibility: {visibility}m\n"
        text += f"\n💨 Wind:\n"
        text += f"   Speed: {wind_speed} m/s\n"
        text += f"   Direction: {wind_direction}°\n"
        text += f"\n💧 Other:\n"
        text += f"   Humidity: {humidity}%\n"
        text += f"   Pressure: {pressure} hPa\n"
        text += f"\n🌅 Sun:\n"
        text += f"   Sunrise: {sunrise}\n"
        text += f"   Sunset: {sunset}"
    
    return text


def _format_simple_html(weather_info: Dict, language: str) -> str:
    """
    生成简洁格式的HTML
    
    Args:
        weather_info: 天气信息
        language: 语言
        
    Returns:
        格式化的HTML
    """
    city = weather_info.get("city", "")
    temp_c = weather_info.get("temperature_celsius", 0)
    temp_f = weather_info.get("temperature_fahrenheit", 0)
    desc = weather_info.get("description", "")
    humidity = weather_info.get("humidity", 0)
    
    # 获取天气emoji
    emoji = "🌤️"
    desc_lower = desc.lower()
    for key, value in WEATHER_EMOJI.items():
        if key in desc_lower:
            emoji = value
            break
    
    if language == "zh":
        html = f"""
        <div style="font-family: Arial, sans-serif; padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border-radius: 10px;">
            <h2>{emoji} {city}天气</h2>
            <div style="font-size: 48px; margin: 20px 0;">{temp_c}°C</div>
            <div style="font-size: 18px;">{desc}</div>
            <div style="margin-top: 20px;">
                <span>💧 湿度: {humidity}%</span>
            </div>
        </div>
        """
    else:
        html = f"""
        <div style="font-family: Arial, sans-serif; padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border-radius: 10px;">
            <h2>{emoji} Weather in {city}</h2>
            <div style="font-size: 48px; margin: 20px 0;">{temp_c}°C</div>
            <div style="font-size: 18px;">{desc}</div>
            <div style="margin-top: 20px;">
                <span>💧 Humidity: {humidity}%</span>
            </div>
        </div>
        """
    
    return html


def _format_detailed_html(weather_info: Dict, language: str) -> str:
    """
    生成详细格式的HTML
    
    Args:
        weather_info: 天气信息
        language: 语言
        
    Returns:
        格式化的HTML
    """
    city = weather_info.get("city", "")
    country = weather_info.get("country", "")
    temp_c = weather_info.get("temperature_celsius", 0)
    temp_f = weather_info.get("temperature_fahrenheit", 0)
    feels_like = weather_info.get("feels_like", 0)
    desc = weather_info.get("description", "")
    humidity = weather_info.get("humidity", 0)
    pressure = weather_info.get("pressure", 0)
    wind_speed = weather_info.get("wind_speed", 0)
    clouds = weather_info.get("clouds", 0)
    visibility = weather_info.get("visibility", 0)
    sunrise = weather_info.get("sunrise", "")
    sunset = weather_info.get("sunset", "")
    
    # 获取天气emoji
    emoji = "🌤️"
    desc_lower = desc.lower()
    for key, value in WEATHER_EMOJI.items():
        if key in desc_lower:
            emoji = value
            break
    
    if language == "zh":
        html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border-radius: 15px; padding: 30px; box-shadow: 0 10px 30px rgba(0,0,0,0.3);">
            <h1 style="text-align: center; margin-bottom: 10px;">{emoji} {city}</h1>
            <p style="text-align: center; opacity: 0.8; margin-bottom: 30px;">{country}</p>
            
            <div style="text-align: center; margin-bottom: 30px;">
                <div style="font-size: 72px; font-weight: bold;">{temp_c}°C</div>
                <div style="font-size: 24px; margin-top: 10px;">{desc}</div>
                <div style="font-size: 16px; opacity: 0.8; margin-top: 5px;">体感 {feels_like}°C</div>
            </div>
            
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-top: 30px;">
                <div style="background: rgba(255,255,255,0.1); padding: 15px; border-radius: 10px;">
                    <div style="font-size: 14px; opacity: 0.8;">💧 湿度</div>
                    <div style="font-size: 24px; font-weight: bold;">{humidity}%</div>
                </div>
                <div style="background: rgba(255,255,255,0.1); padding: 15px; border-radius: 10px;">
                    <div style="font-size: 14px; opacity: 0.8;">💨 风速</div>
                    <div style="font-size: 24px; font-weight: bold;">{wind_speed} m/s</div>
                </div>
                <div style="background: rgba(255,255,255,0.1); padding: 15px; border-radius: 10px;">
                    <div style="font-size: 14px; opacity: 0.8;">☁️ 云量</div>
                    <div style="font-size: 24px; font-weight: bold;">{clouds}%</div>
                </div>
                <div style="background: rgba(255,255,255,0.1); padding: 15px; border-radius: 10px;">
                    <div style="font-size: 14px; opacity: 0.8;">🔽 气压</div>
                    <div style="font-size: 24px; font-weight: bold;">{pressure} hPa</div>
                </div>
            </div>
            
            <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid rgba(255,255,255,0.2);">
                <div style="display: flex; justify-content: space-between;">
                    <div>
                        <div style="font-size: 14px; opacity: 0.8;">🌅 日出</div>
                        <div style="font-size: 18px; font-weight: bold;">{sunrise}</div>
                    </div>
                    <div style="text-align: right;">
                        <div style="font-size: 14px; opacity: 0.8;">🌇 日落</div>
                        <div style="font-size: 18px; font-weight: bold;">{sunset}</div>
                    </div>
                </div>
            </div>
        </div>
        """
    else:
        html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border-radius: 15px; padding: 30px; box-shadow: 0 10px 30px rgba(0,0,0,0.3);">
            <h1 style="text-align: center; margin-bottom: 10px;">{emoji} {city}</h1>
            <p style="text-align: center; opacity: 0.8; margin-bottom: 30px;">{country}</p>
            
            <div style="text-align: center; margin-bottom: 30px;">
                <div style="font-size: 72px; font-weight: bold;">{temp_c}°C</div>
                <div style="font-size: 24px; margin-top: 10px;">{desc}</div>
                <div style="font-size: 16px; opacity: 0.8; margin-top: 5px;">Feels like {feels_like}°C</div>
            </div>
            
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-top: 30px;">
                <div style="background: rgba(255,255,255,0.1); padding: 15px; border-radius: 10px;">
                    <div style="font-size: 14px; opacity: 0.8;">💧 Humidity</div>
                    <div style="font-size: 24px; font-weight: bold;">{humidity}%</div>
                </div>
                <div style="background: rgba(255,255,255,0.1); padding: 15px; border-radius: 10px;">
                    <div style="font-size: 14px; opacity: 0.8;">💨 Wind Speed</div>
                    <div style="font-size: 24px; font-weight: bold;">{wind_speed} m/s</div>
                </div>
                <div style="background: rgba(255,255,255,0.1); padding: 15px; border-radius: 10px;">
                    <div style="font-size: 14px; opacity: 0.8;">☁️ Cloud Cover</div>
                    <div style="font-size: 24px; font-weight: bold;">{clouds}%</div>
                </div>
                <div style="background: rgba(255,255,255,0.1); padding: 15px; border-radius: 10px;">
                    <div style="font-size: 14px; opacity: 0.8;">🔽 Pressure</div>
                    <div style="font-size: 24px; font-weight: bold;">{pressure} hPa</div>
                </div>
            </div>
            
            <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid rgba(255,255,255,0.2);">
                <div style="display: flex; justify-content: space-between;">
                    <div>
                        <div style="font-size: 14px; opacity: 0.8;">🌅 Sunrise</div>
                        <div style="font-size: 18px; font-weight: bold;">{sunrise}</div>
                    </div>
                    <div style="text-align: right;">
                        <div style="font-size: 14px; opacity: 0.8;">🌇 Sunset</div>
                        <div style="font-size: 18px; font-weight: bold;">{sunset}</div>
                    </div>
                </div>
            </div>
        </div>
        """
    
    return html
