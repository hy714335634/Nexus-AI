#!/usr/bin/env python3
"""
体育数据工具模块

提供体育比赛预测相关的工具函数，专注于真实的体育数据收集和分析。
支持足球、篮球等主流体育项目的数据获取和预测分析。
"""

import json
import re
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from urllib.parse import quote_plus

from strands import tool


@tool
def team_info_collector(team_name: str, sport_type: str = "auto") -> str:
    """
    球队信息收集工具 - 收集球队基本信息、近期战绩、球员状态等
    
    Args:
        team_name (str): 球队名称
        sport_type (str): 体育项目类型 (auto/football/basketball)
        
    Returns:
        str: JSON格式的球队信息数据
    """
    try:
        # 标准化球队名称
        normalized_name = _normalize_team_name(team_name)
        
        # 自动识别体育项目类型
        if sport_type == "auto":
            sport_type = _detect_sport_type(team_name)
        
        # 构建数据收集结构
        team_data = {
            "collection_time": datetime.now().isoformat(),
            "team_name": team_name,
            "normalized_name": normalized_name,
            "sport_type": sport_type,
            "data_sources": [],
            "basic_info": {
                "official_name": "",
                "league": "",
                "country": "",
                "founded": "",
                "stadium": "",
                "coach": "",
                "status": "pending_collection"
            },
            "recent_matches": {
                "matches": [],
                "statistics": {
                    "total_matches": 0,
                    "wins": 0,
                    "draws": 0,
                    "losses": 0,
                    "win_rate": 0.0,
                    "goals_scored": 0,
                    "goals_conceded": 0,
                    "avg_goals_scored": 0.0,
                    "avg_goals_conceded": 0.0
                },
                "status": "pending_collection"
            },
            "player_info": {
                "key_players": [],
                "injuries": [],
                "suspensions": [],
                "status": "pending_collection"
            },
            "next_match": {
                "opponent": "",
                "date": "",
                "venue": "",
                "competition": "",
                "status": "pending_collection"
            },
            "api_urls": _build_api_urls(normalized_name, sport_type),
            "search_queries": _build_search_queries(team_name, sport_type),
            "collection_status": "ready_for_data_collection",
            "notes": [
                "球队信息结构已准备就绪",
                "等待实际API调用和网络搜索执行",
                f"支持的体育项目: {sport_type}",
                "数据收集完成后将提供完整的球队信息"
            ]
        }
        
        return json.dumps(team_data, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "error_message": str(e),
            "team_name": team_name,
            "timestamp": datetime.now().isoformat()
        }, ensure_ascii=False)


@tool
def match_predictor(home_team_data: str, away_team_data: str, match_info: Dict[str, Any] = None) -> str:
    """
    比赛预测工具 - 基于双方球队数据进行比赛结果预测
    
    Args:
        home_team_data (str): 主队数据（JSON格式）
        away_team_data (str): 客队数据（JSON格式）
        match_info (Dict[str, Any], optional): 比赛附加信息
        
    Returns:
        str: JSON格式的预测结果
    """
    try:
        # 解析球队数据
        home_data = json.loads(home_team_data) if isinstance(home_team_data, str) else home_team_data
        away_data = json.loads(away_team_data) if isinstance(away_team_data, str) else away_team_data
        
        # 构建预测分析框架
        prediction = {
            "prediction_time": datetime.now().isoformat(),
            "match_info": {
                "home_team": home_data.get("team_name", "未知"),
                "away_team": away_data.get("team_name", "未知"),
                "sport_type": home_data.get("sport_type", "football"),
                "venue": match_info.get("venue", "主场") if match_info else "主场",
                "date": match_info.get("date", "") if match_info else ""
            },
            "team_comparison": {
                "recent_form": {
                    "home_win_rate": home_data.get("recent_matches", {}).get("statistics", {}).get("win_rate", 0),
                    "away_win_rate": away_data.get("recent_matches", {}).get("statistics", {}).get("win_rate", 0),
                    "advantage": "待Agent分析"
                },
                "offensive_power": {
                    "home_avg_goals": home_data.get("recent_matches", {}).get("statistics", {}).get("avg_goals_scored", 0),
                    "away_avg_goals": away_data.get("recent_matches", {}).get("statistics", {}).get("avg_goals_scored", 0),
                    "advantage": "待Agent分析"
                },
                "defensive_strength": {
                    "home_avg_conceded": home_data.get("recent_matches", {}).get("statistics", {}).get("avg_goals_conceded", 0),
                    "away_avg_conceded": away_data.get("recent_matches", {}).get("statistics", {}).get("avg_goals_conceded", 0),
                    "advantage": "待Agent分析"
                },
                "injury_impact": {
                    "home_injuries": len(home_data.get("player_info", {}).get("injuries", [])),
                    "away_injuries": len(away_data.get("player_info", {}).get("injuries", [])),
                    "advantage": "待Agent分析"
                },
                "home_advantage": {
                    "venue": match_info.get("venue", "主场") if match_info else "主场",
                    "impact": "待Agent评估主客场影响"
                }
            },
            "prediction_result": {
                "predicted_winner": "待Agent基于数据分析预测",
                "confidence_score": "待Agent计算置信度(0-100)",
                "predicted_score": "待Agent预测比分",
                "win_probability": {
                    "home_win": "待Agent计算主队获胜概率",
                    "draw": "待Agent计算平局概率",
                    "away_win": "待Agent计算客队获胜概率"
                }
            },
            "key_factors": [
                "待Agent识别影响比赛结果的关键因素",
                "待Agent分析球队状态和伤病影响",
                "待Agent评估主客场优势",
                "待Agent考虑历史交锋记录"
            ],
            "analysis_summary": "待Agent提供详细分析说明",
            "risk_factors": [
                "待Agent识别预测风险因素",
                "待Agent评估数据质量影响"
            ],
            "data_quality": {
                "home_data_completeness": _calculate_data_completeness(home_data),
                "away_data_completeness": _calculate_data_completeness(away_data),
                "overall_confidence": "待Agent基于数据完整性评估"
            },
            "notes": [
                "预测框架已生成，等待Agent进行具体分析",
                "所有预测结果应由Agent基于真实数据计算",
                "建议Agent综合考虑多个因素进行预测",
                "预测准确性取决于数据质量和完整性"
            ]
        }
        
        return json.dumps(prediction, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "error_message": str(e),
            "timestamp": datetime.now().isoformat()
        }, ensure_ascii=False)


@tool
def sports_api_client(endpoint: str, params: Dict[str, Any] = None, api_type: str = "auto") -> str:
    """
    体育数据API客户端 - 调用各种体育数据API获取真实数据
    
    Args:
        endpoint (str): API端点
        params (Dict[str, Any], optional): API参数
        api_type (str): API类型 (auto/thesportsdb/api-football/espn)
        
    Returns:
        str: JSON格式的API响应数据
    """
    try:
        if params is None:
            params = {}
        
        # 构建API请求信息
        api_request = {
            "request_time": datetime.now().isoformat(),
            "endpoint": endpoint,
            "params": params,
            "api_type": api_type,
            "api_urls": {},
            "request_method": "GET",
            "headers": {
                "Accept": "application/json",
                "User-Agent": "SportsPredictor/1.0"
            },
            "status": "pending_execution"
        }
        
        # 根据API类型构建具体URL
        if api_type == "thesportsdb" or api_type == "auto":
            # TheSportsDB API (免费)
            base_url = "https://www.thesportsdb.com/api/v1/json/3"
            api_request["api_urls"]["thesportsdb"] = {
                "search_team": f"{base_url}/searchteams.php?t={{team_name}}",
                "team_details": f"{base_url}/lookupteam.php?id={{team_id}}",
                "next_matches": f"{base_url}/eventsnext.php?id={{team_id}}",
                "last_matches": f"{base_url}/eventslast.php?id={{team_id}}",
                "league_table": f"{base_url}/lookuptable.php?l={{league_id}}&s={{season}}"
            }
        
        if api_type == "api-football" or api_type == "auto":
            # API-Football (需要API密钥)
            base_url = "https://v3.football.api-sports.io"
            api_request["api_urls"]["api-football"] = {
                "search_team": f"{base_url}/teams?search={{team_name}}",
                "team_details": f"{base_url}/teams?id={{team_id}}",
                "team_statistics": f"{base_url}/teams/statistics?team={{team_id}}&season={{season}}",
                "fixtures": f"{base_url}/fixtures?team={{team_id}}&last=10",
                "injuries": f"{base_url}/injuries?team={{team_id}}",
                "standings": f"{base_url}/standings?team={{team_id}}"
            }
            api_request["headers"]["x-rapidapi-key"] = "YOUR_API_KEY_HERE"
            api_request["headers"]["x-rapidapi-host"] = "v3.football.api-sports.io"
        
        if api_type == "espn" or api_type == "auto":
            # ESPN API (部分免费)
            api_request["api_urls"]["espn"] = {
                "search_team": "https://site.api.espn.com/apis/site/v2/sports/{sport}/teams",
                "team_details": "https://site.api.espn.com/apis/site/v2/sports/{sport}/teams/{team_id}",
                "team_roster": "https://site.api.espn.com/apis/site/v2/sports/{sport}/teams/{team_id}/roster",
                "team_schedule": "https://site.api.espn.com/apis/site/v2/sports/{sport}/teams/{team_id}/schedule"
            }
        
        api_request["notes"] = [
            "API请求信息已准备就绪",
            "等待实际HTTP请求执行",
            "支持多个体育数据API提供商",
            "建议使用免费的TheSportsDB API开始",
            "API密钥需要通过环境变量配置",
            "实际调用应使用strands_tools/http_request工具"
        ]
        
        return json.dumps(api_request, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "error_message": str(e),
            "timestamp": datetime.now().isoformat()
        }, ensure_ascii=False)


@tool
def sports_news_collector(team_name: str, news_type: str = "all", max_results: int = 10) -> str:
    """
    体育新闻收集工具 - 收集球队相关的最新新闻和报道
    
    Args:
        team_name (str): 球队名称
        news_type (str): 新闻类型 (all/injuries/transfers/matches/analysis)
        max_results (int): 最大结果数量
        
    Returns:
        str: JSON格式的新闻数据
    """
    try:
        # 构建新闻搜索查询
        search_queries = []
        
        if news_type in ["all", "injuries"]:
            search_queries.append(f"{team_name} 伤病情况")
            search_queries.append(f"{team_name} injury news")
        
        if news_type in ["all", "transfers"]:
            search_queries.append(f"{team_name} 转会新闻")
            search_queries.append(f"{team_name} transfer news")
        
        if news_type in ["all", "matches"]:
            search_queries.append(f"{team_name} 比赛预告")
            search_queries.append(f"{team_name} match preview")
        
        if news_type in ["all", "analysis"]:
            search_queries.append(f"{team_name} 战术分析")
            search_queries.append(f"{team_name} tactical analysis")
        
        # 构建RSS订阅源
        rss_feeds = [
            "https://feeds.reuters.com/reuters/sportsNews",
            "https://feeds.bbci.co.uk/sport/rss.xml",
            "https://www.espn.com/espn/rss/news",
            "https://www.goal.com/feeds/news?fmt=rss",
            "https://www.skysports.com/rss/12040"
        ]
        
        # 构建新闻收集结构
        news_data = {
            "collection_time": datetime.now().isoformat(),
            "team_name": team_name,
            "news_type": news_type,
            "max_results": max_results,
            "search_queries": search_queries,
            "rss_feeds": rss_feeds,
            "web_search_urls": [
                f"https://www.google.com/search?q={quote_plus(query)}&tbm=nws"
                for query in search_queries
            ],
            "news_results": [],
            "status": "pending_collection",
            "notes": [
                "新闻搜索查询已准备就绪",
                "等待实际搜索和RSS订阅执行",
                "支持多语言新闻源",
                "建议使用strands_tools/http_request获取RSS",
                "建议使用web_search工具进行新闻搜索"
            ]
        }
        
        return json.dumps(news_data, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "error_message": str(e),
            "timestamp": datetime.now().isoformat()
        }, ensure_ascii=False)


@tool
def match_report_generator(prediction_data: str, team_data: Dict[str, Any] = None) -> str:
    """
    比赛预测报告生成工具 - 生成结构化的比赛预测报告
    
    Args:
        prediction_data (str): 预测数据（JSON格式）
        team_data (Dict[str, Any], optional): 附加球队数据
        
    Returns:
        str: Markdown格式的预测报告
    """
    try:
        # 解析预测数据
        prediction = json.loads(prediction_data) if isinstance(prediction_data, str) else prediction_data
        
        # 生成Markdown格式报告
        report = f"""# ⚽ 比赛预测分析报告

**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**比赛对阵**: {prediction.get('match_info', {}).get('home_team', '未知')} vs {prediction.get('match_info', {}).get('away_team', '未知')}  
**体育项目**: {prediction.get('match_info', {}).get('sport_type', '足球')}  
**比赛地点**: {prediction.get('match_info', {}).get('venue', '主场')}  

---

## 📊 预测结果

### 🏆 预测胜者
**{prediction.get('prediction_result', {}).get('predicted_winner', '待分析')}**

### 📈 置信度
**{prediction.get('prediction_result', {}).get('confidence_score', '待计算')}**

### ⚽ 预测比分
**{prediction.get('prediction_result', {}).get('predicted_score', '待预测')}**

### 📊 获胜概率
- **主队获胜**: {prediction.get('prediction_result', {}).get('win_probability', {}).get('home_win', '待计算')}
- **平局**: {prediction.get('prediction_result', {}).get('win_probability', {}).get('draw', '待计算')}
- **客队获胜**: {prediction.get('prediction_result', {}).get('win_probability', {}).get('away_win', '待计算')}

---

## 🔍 数据对比分析

### 📈 近期状态
- **主队胜率**: {prediction.get('team_comparison', {}).get('recent_form', {}).get('home_win_rate', 0):.1%}
- **客队胜率**: {prediction.get('team_comparison', {}).get('recent_form', {}).get('away_win_rate', 0):.1%}
- **状态优势**: {prediction.get('team_comparison', {}).get('recent_form', {}).get('advantage', '待分析')}

### ⚔️ 进攻能力
- **主队场均进球**: {prediction.get('team_comparison', {}).get('offensive_power', {}).get('home_avg_goals', 0):.2f}
- **客队场均进球**: {prediction.get('team_comparison', {}).get('offensive_power', {}).get('away_avg_goals', 0):.2f}
- **进攻优势**: {prediction.get('team_comparison', {}).get('offensive_power', {}).get('advantage', '待分析')}

### 🛡️ 防守能力
- **主队场均失球**: {prediction.get('team_comparison', {}).get('defensive_strength', {}).get('home_avg_conceded', 0):.2f}
- **客队场均失球**: {prediction.get('team_comparison', {}).get('defensive_strength', {}).get('away_avg_conceded', 0):.2f}
- **防守优势**: {prediction.get('team_comparison', {}).get('defensive_strength', {}).get('advantage', '待分析')}

### 🏥 伤病影响
- **主队伤病人数**: {prediction.get('team_comparison', {}).get('injury_impact', {}).get('home_injuries', 0)}
- **客队伤病人数**: {prediction.get('team_comparison', {}).get('injury_impact', {}).get('away_injuries', 0)}
- **伤病影响**: {prediction.get('team_comparison', {}).get('injury_impact', {}).get('advantage', '待分析')}

### 🏟️ 主场优势
- **比赛地点**: {prediction.get('team_comparison', {}).get('home_advantage', {}).get('venue', '主场')}
- **主场影响**: {prediction.get('team_comparison', {}).get('home_advantage', {}).get('impact', '待评估')}

---

## 🎯 关键影响因素

"""
        
        # 添加关键因素
        key_factors = prediction.get('key_factors', [])
        for i, factor in enumerate(key_factors, 1):
            report += f"{i}. {factor}\n"
        
        report += "\n---\n\n## 📝 分析总结\n\n"
        report += prediction.get('analysis_summary', '待Agent提供详细分析说明')
        
        report += "\n\n---\n\n## ⚠️ 风险因素\n\n"
        
        # 添加风险因素
        risk_factors = prediction.get('risk_factors', [])
        for i, risk in enumerate(risk_factors, 1):
            report += f"{i}. {risk}\n"
        
        report += "\n---\n\n## 📊 数据质量评估\n\n"
        data_quality = prediction.get('data_quality', {})
        report += f"- **主队数据完整性**: {data_quality.get('home_data_completeness', 0):.1%}\n"
        report += f"- **客队数据完整性**: {data_quality.get('away_data_completeness', 0):.1%}\n"
        report += f"- **整体置信度**: {data_quality.get('overall_confidence', '待评估')}\n"
        
        report += "\n---\n\n## 📚 免责声明\n\n"
        report += "本预测报告基于公开数据和统计分析生成，仅供参考。实际比赛结果受多种因素影响，预测不保证准确性。\n"
        
        report += "\n---\n\n*报告由 Sports Team Match Predictor 自动生成*\n"
        
        return report
        
    except Exception as e:
        return f"# 报告生成失败\n\n错误信息: {str(e)}"


# 辅助函数

def _normalize_team_name(team_name: str) -> str:
    """标准化球队名称"""
    # 移除特殊字符
    normalized = re.sub(r'[^\w\s]', '', team_name)
    # 转换为小写
    normalized = normalized.lower().strip()
    # 移除多余空格
    normalized = re.sub(r'\s+', ' ', normalized)
    return normalized


def _detect_sport_type(team_name: str) -> str:
    """自动识别体育项目类型"""
    team_lower = team_name.lower()
    
    # 足球关键词
    football_keywords = ['fc', 'united', 'city', 'real', 'barcelona', 'juventus', 
                        'bayern', 'liverpool', 'arsenal', 'chelsea', 'milan']
    
    # 篮球关键词
    basketball_keywords = ['lakers', 'warriors', 'bulls', 'celtics', 'heat', 
                          'spurs', 'rockets', 'knicks', 'nets', 'clippers']
    
    for keyword in football_keywords:
        if keyword in team_lower:
            return "football"
    
    for keyword in basketball_keywords:
        if keyword in team_lower:
            return "basketball"
    
    # 默认返回足球
    return "football"


def _build_api_urls(team_name: str, sport_type: str) -> Dict[str, str]:
    """构建API URL列表"""
    urls = {
        "thesportsdb": {
            "search": f"https://www.thesportsdb.com/api/v1/json/3/searchteams.php?t={quote_plus(team_name)}",
            "details": "https://www.thesportsdb.com/api/v1/json/3/lookupteam.php?id={team_id}",
            "next_matches": "https://www.thesportsdb.com/api/v1/json/3/eventsnext.php?id={team_id}",
            "last_matches": "https://www.thesportsdb.com/api/v1/json/3/eventslast.php?id={team_id}"
        }
    }
    
    if sport_type == "football":
        urls["api-football"] = {
            "search": f"https://v3.football.api-sports.io/teams?search={quote_plus(team_name)}",
            "statistics": "https://v3.football.api-sports.io/teams/statistics?team={team_id}&season=2024",
            "fixtures": "https://v3.football.api-sports.io/fixtures?team={team_id}&last=10",
            "injuries": "https://v3.football.api-sports.io/injuries?team={team_id}"
        }
    
    return urls


def _build_search_queries(team_name: str, sport_type: str) -> List[str]:
    """构建搜索查询列表"""
    queries = [
        f"{team_name} 球队信息",
        f"{team_name} 近期比赛",
        f"{team_name} 球员名单",
        f"{team_name} 伤病情况",
        f"{team_name} 下一场比赛",
        f"{team_name} team information",
        f"{team_name} recent matches",
        f"{team_name} player roster",
        f"{team_name} injuries",
        f"{team_name} next match"
    ]
    
    return queries


def _calculate_data_completeness(team_data: Dict[str, Any]) -> float:
    """计算数据完整性"""
    total_fields = 0
    completed_fields = 0
    
    # 检查基本信息
    basic_info = team_data.get("basic_info", {})
    if basic_info:
        total_fields += 6
        for key in ["official_name", "league", "country", "founded", "stadium", "coach"]:
            if basic_info.get(key) and basic_info.get(key) != "":
                completed_fields += 1
    
    # 检查近期比赛
    recent_matches = team_data.get("recent_matches", {})
    if recent_matches and recent_matches.get("matches"):
        total_fields += 1
        if len(recent_matches.get("matches", [])) > 0:
            completed_fields += 1
    
    # 检查球员信息
    player_info = team_data.get("player_info", {})
    if player_info:
        total_fields += 1
        if player_info.get("key_players") or player_info.get("injuries"):
            completed_fields += 1
    
    # 检查下一场比赛
    next_match = team_data.get("next_match", {})
    if next_match:
        total_fields += 1
        if next_match.get("opponent") and next_match.get("opponent") != "":
            completed_fields += 1
    
    if total_fields == 0:
        return 0.0
    
    return completed_fields / total_fields


if __name__ == "__main__":
    # 测试工具功能
    print("🧪 测试体育数据工具...")
    
    # 测试球队信息收集
    team_info = team_info_collector("Manchester United", "football")
    print("📊 球队信息收集:", team_info[:200] + "...")
    
    # 测试API客户端
    api_request = sports_api_client("search_team", {"team_name": "Manchester United"}, "thesportsdb")
    print("🔍 API请求:", api_request[:200] + "...")
    
    # 测试新闻收集
    news_data = sports_news_collector("Manchester United", "injuries", 5)
    print("📰 新闻收集:", news_data[:200] + "...")
    
    print("✅ 体育数据工具测试完成！")
