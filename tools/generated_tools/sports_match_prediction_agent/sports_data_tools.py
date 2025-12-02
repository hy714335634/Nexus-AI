"""
体育数据收集和管理工具

提供体育赛事数据的API调用、缓存管理、数据验证等功能
"""

import json
import os
import time
import pickle
import hashlib
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path

from strands import tool


# ============================================================================
# 缓存管理工具
# ============================================================================

class CacheManager:
    """缓存管理器"""
    
    def __init__(self, cache_dir: str = ".cache/sports_match_prediction_agent"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.max_cache_size_mb = 500
        
    def _get_cache_key(self, data_type: str, identifier: str) -> str:
        """生成缓存键"""
        key_str = f"{data_type}:{identifier}"
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def _get_cache_path(self, cache_key: str) -> Path:
        """获取缓存文件路径"""
        return self.cache_dir / f"{cache_key}.cache"
    
    def get(self, data_type: str, identifier: str) -> Optional[Dict[str, Any]]:
        """
        从缓存获取数据
        
        Args:
            data_type: 数据类型（team_info, match_history, player_status等）
            identifier: 数据标识符（如team_id）
            
        Returns:
            缓存的数据，如果不存在或已过期返回None
        """
        cache_key = self._get_cache_key(data_type, identifier)
        cache_path = self._get_cache_path(cache_key)
        
        if not cache_path.exists():
            return None
        
        try:
            with open(cache_path, 'rb') as f:
                cache_data = pickle.load(f)
            
            # 检查是否过期
            if cache_data['expires_at'] < time.time():
                cache_path.unlink()  # 删除过期缓存
                return None
            
            return cache_data['data']
        except Exception as e:
            print(f"读取缓存失败: {e}")
            return None
    
    def set(self, data_type: str, identifier: str, data: Dict[str, Any], ttl_seconds: int):
        """
        设置缓存数据
        
        Args:
            data_type: 数据类型
            identifier: 数据标识符
            data: 要缓存的数据
            ttl_seconds: 缓存过期时间（秒）
        """
        cache_key = self._get_cache_key(data_type, identifier)
        cache_path = self._get_cache_path(cache_key)
        
        cache_data = {
            'data': data,
            'cached_at': time.time(),
            'expires_at': time.time() + ttl_seconds,
            'data_type': data_type,
            'identifier': identifier
        }
        
        try:
            with open(cache_path, 'wb') as f:
                pickle.dump(cache_data, f)
            
            # 检查缓存大小
            self._cleanup_if_needed()
        except Exception as e:
            print(f"写入缓存失败: {e}")
    
    def _get_cache_size_mb(self) -> float:
        """获取缓存总大小（MB）"""
        total_size = sum(f.stat().st_size for f in self.cache_dir.glob('*.cache'))
        return total_size / (1024 * 1024)
    
    def _cleanup_if_needed(self):
        """如果缓存超过限制，清理最少使用的缓存"""
        current_size = self._get_cache_size_mb()
        if current_size <= self.max_cache_size_mb:
            return
        
        # 按访问时间排序，删除最旧的缓存
        cache_files = list(self.cache_dir.glob('*.cache'))
        cache_files.sort(key=lambda f: f.stat().st_atime)
        
        # 删除最旧的25%缓存
        num_to_delete = len(cache_files) // 4
        for cache_file in cache_files[:num_to_delete]:
            cache_file.unlink()
    
    def clear(self):
        """清空所有缓存"""
        for cache_file in self.cache_dir.glob('*.cache'):
            cache_file.unlink()


# 全局缓存管理器实例
_cache_manager = CacheManager()


@tool
def cache_get(data_type: str, identifier: str) -> str:
    """
    从缓存获取数据
    
    Args:
        data_type: 数据类型（team_info, match_history, player_status, upcoming_matches）
        identifier: 数据标识符（如team_id）
        
    Returns:
        str: JSON格式的缓存数据，如果不存在返回空对象
    """
    try:
        data = _cache_manager.get(data_type, identifier)
        if data is None:
            return json.dumps({
                "success": False,
                "message": "Cache miss",
                "data": None
            })
        
        return json.dumps({
            "success": True,
            "message": "Cache hit",
            "data": data
        })
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
            "message": "Failed to get cache"
        })


@tool
def cache_set(data_type: str, identifier: str, data: str, ttl_hours: int = 24) -> str:
    """
    设置缓存数据
    
    Args:
        data_type: 数据类型（team_info, match_history, player_status, upcoming_matches）
        identifier: 数据标识符
        data: 要缓存的数据（JSON字符串）
        ttl_hours: 缓存过期时间（小时），默认24小时
        
    Returns:
        str: JSON格式的操作结果
    """
    try:
        data_dict = json.loads(data)
        ttl_seconds = ttl_hours * 3600
        _cache_manager.set(data_type, identifier, data_dict, ttl_seconds)
        
        return json.dumps({
            "success": True,
            "message": f"Cache set successfully, TTL: {ttl_hours} hours"
        })
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
            "message": "Failed to set cache"
        })


@tool
def cache_clear() -> str:
    """
    清空所有缓存
    
    Returns:
        str: JSON格式的操作结果
    """
    try:
        _cache_manager.clear()
        return json.dumps({
            "success": True,
            "message": "All cache cleared"
        })
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
            "message": "Failed to clear cache"
        })


# ============================================================================
# 体育数据API工具
# ============================================================================

@tool
def search_team(team_name: str, sport_type: str = "soccer") -> str:
    """
    搜索球队信息
    
    Args:
        team_name: 球队名称（支持模糊匹配）
        sport_type: 体育类型（soccer/basketball）
        
    Returns:
        str: JSON格式的球队搜索结果
    """
    import requests
    
    try:
        # 先检查缓存
        cache_key = f"{team_name}:{sport_type}"
        cached_data = _cache_manager.get("team_search", cache_key)
        if cached_data:
            return json.dumps({
                "success": True,
                "message": "Data from cache",
                "data": cached_data,
                "source": "cache"
            })
        
        # TheSportsDB API
        base_url = "https://www.thesportsdb.com/api/v1/json/3"
        search_url = f"{base_url}/searchteams.php"
        
        params = {"t": team_name}
        response = requests.get(search_url, params=params, timeout=5)
        response.raise_for_status()
        
        result = response.json()
        
        if not result.get("teams"):
            return json.dumps({
                "success": False,
                "message": f"No team found with name: {team_name}",
                "suggestions": ["Check spelling", "Try full team name", "Try different language"]
            })
        
        # 过滤体育类型
        sport_map = {
            "soccer": "Soccer",
            "basketball": "Basketball"
        }
        target_sport = sport_map.get(sport_type.lower(), "Soccer")
        
        teams = [
            {
                "id": team["idTeam"],
                "name": team["strTeam"],
                "alternate_name": team.get("strAlternate"),
                "sport": team["strSport"],
                "league": team["strLeague"],
                "country": team.get("strCountry"),
                "stadium": team.get("strStadium"),
                "description": team.get("strDescriptionEN", "")[:200],
                "badge": team.get("strTeamBadge"),
                "formed_year": team.get("intFormedYear")
            }
            for team in result["teams"]
            if team["strSport"] == target_sport
        ]
        
        if not teams:
            return json.dumps({
                "success": False,
                "message": f"No {sport_type} team found with name: {team_name}",
                "available_sports": list(set(t["strSport"] for t in result["teams"]))
            })
        
        # 缓存结果（24小时）
        cache_data = {"teams": teams, "count": len(teams)}
        _cache_manager.set("team_search", cache_key, cache_data, 24 * 3600)
        
        return json.dumps({
            "success": True,
            "message": f"Found {len(teams)} team(s)",
            "data": cache_data,
            "source": "api"
        })
        
    except requests.exceptions.Timeout:
        return json.dumps({
            "success": False,
            "error": "API request timeout",
            "message": "Please try again later"
        })
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
            "message": "Failed to search team"
        })


@tool
def get_team_details(team_id: str) -> str:
    """
    获取球队详细信息
    
    Args:
        team_id: 球队ID
        
    Returns:
        str: JSON格式的球队详细信息
    """
    import requests
    
    try:
        # 先检查缓存
        cached_data = _cache_manager.get("team_info", team_id)
        if cached_data:
            return json.dumps({
                "success": True,
                "message": "Data from cache",
                "data": cached_data,
                "source": "cache"
            })
        
        # TheSportsDB API
        base_url = "https://www.thesportsdb.com/api/v1/json/3"
        detail_url = f"{base_url}/lookupteam.php"
        
        params = {"id": team_id}
        response = requests.get(detail_url, params=params, timeout=5)
        response.raise_for_status()
        
        result = response.json()
        
        if not result.get("teams"):
            return json.dumps({
                "success": False,
                "message": f"Team not found: {team_id}"
            })
        
        team = result["teams"][0]
        team_data = {
            "id": team["idTeam"],
            "name": team["strTeam"],
            "alternate_name": team.get("strAlternate"),
            "sport": team["strSport"],
            "league": team["strLeague"],
            "country": team.get("strCountry"),
            "stadium": team.get("strStadium"),
            "stadium_capacity": team.get("intStadiumCapacity"),
            "description": team.get("strDescriptionEN"),
            "formed_year": team.get("intFormedYear"),
            "badge": team.get("strTeamBadge"),
            "jersey": team.get("strTeamJersey"),
            "website": team.get("strWebsite"),
            "facebook": team.get("strFacebook"),
            "twitter": team.get("strTwitter"),
            "instagram": team.get("strInstagram"),
            "youtube": team.get("strYoutube")
        }
        
        # 缓存结果（24小时）
        _cache_manager.set("team_info", team_id, team_data, 24 * 3600)
        
        return json.dumps({
            "success": True,
            "message": "Team details retrieved",
            "data": team_data,
            "source": "api"
        })
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
            "message": "Failed to get team details"
        })


@tool
def get_team_last_matches(team_id: str, limit: int = 10) -> str:
    """
    获取球队最近比赛记录
    
    Args:
        team_id: 球队ID
        limit: 返回结果数量限制，默认10场
        
    Returns:
        str: JSON格式的比赛记录
    """
    import requests
    
    try:
        # 先检查缓存
        cache_key = f"{team_id}:last_{limit}"
        cached_data = _cache_manager.get("match_history", cache_key)
        if cached_data:
            return json.dumps({
                "success": True,
                "message": "Data from cache",
                "data": cached_data,
                "source": "cache"
            })
        
        # TheSportsDB API
        base_url = "https://www.thesportsdb.com/api/v1/json/3"
        matches_url = f"{base_url}/eventslast.php"
        
        params = {"id": team_id}
        response = requests.get(matches_url, params=params, timeout=5)
        response.raise_for_status()
        
        result = response.json()
        
        if not result.get("results"):
            return json.dumps({
                "success": False,
                "message": f"No match history found for team: {team_id}"
            })
        
        matches = []
        for event in result["results"][:limit]:
            match_data = {
                "id": event["idEvent"],
                "date": event.get("dateEvent"),
                "time": event.get("strTime"),
                "home_team": event.get("strHomeTeam"),
                "away_team": event.get("strAwayTeam"),
                "home_score": event.get("intHomeScore"),
                "away_score": event.get("intAwayScore"),
                "league": event.get("strLeague"),
                "season": event.get("strSeason"),
                "venue": event.get("strVenue"),
                "status": event.get("strStatus")
            }
            matches.append(match_data)
        
        # 计算统计数据
        stats = _calculate_match_stats(matches, team_id)
        
        result_data = {
            "team_id": team_id,
            "matches": matches,
            "count": len(matches),
            "statistics": stats
        }
        
        # 缓存结果（7天）
        _cache_manager.set("match_history", cache_key, result_data, 7 * 24 * 3600)
        
        return json.dumps({
            "success": True,
            "message": f"Retrieved {len(matches)} matches",
            "data": result_data,
            "source": "api"
        })
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
            "message": "Failed to get match history"
        })


@tool
def get_team_next_matches(team_id: str, limit: int = 5) -> str:
    """
    获取球队未来赛程
    
    Args:
        team_id: 球队ID
        limit: 返回结果数量限制，默认5场
        
    Returns:
        str: JSON格式的未来赛程
    """
    import requests
    
    try:
        # 先检查缓存
        cache_key = f"{team_id}:next_{limit}"
        cached_data = _cache_manager.get("upcoming_matches", cache_key)
        if cached_data:
            return json.dumps({
                "success": True,
                "message": "Data from cache",
                "data": cached_data,
                "source": "cache"
            })
        
        # TheSportsDB API
        base_url = "https://www.thesportsdb.com/api/v1/json/3"
        matches_url = f"{base_url}/eventsnext.php"
        
        params = {"id": team_id}
        response = requests.get(matches_url, params=params, timeout=5)
        response.raise_for_status()
        
        result = response.json()
        
        if not result.get("events"):
            return json.dumps({
                "success": False,
                "message": f"No upcoming matches found for team: {team_id}"
            })
        
        matches = []
        for event in result["events"][:limit]:
            match_data = {
                "id": event["idEvent"],
                "date": event.get("dateEvent"),
                "time": event.get("strTime"),
                "home_team": event.get("strHomeTeam"),
                "home_team_id": event.get("idHomeTeam"),
                "away_team": event.get("strAwayTeam"),
                "away_team_id": event.get("idAwayTeam"),
                "league": event.get("strLeague"),
                "season": event.get("strSeason"),
                "venue": event.get("strVenue"),
                "status": event.get("strStatus")
            }
            matches.append(match_data)
        
        result_data = {
            "team_id": team_id,
            "matches": matches,
            "count": len(matches)
        }
        
        # 缓存结果（12小时）
        _cache_manager.set("upcoming_matches", cache_key, result_data, 12 * 3600)
        
        return json.dumps({
            "success": True,
            "message": f"Retrieved {len(matches)} upcoming matches",
            "data": result_data,
            "source": "api"
        })
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
            "message": "Failed to get upcoming matches"
        })


@tool
def get_head_to_head(team1_id: str, team2_id: str) -> str:
    """
    获取两队历史交锋记录
    
    Args:
        team1_id: 球队1 ID
        team2_id: 球队2 ID
        
    Returns:
        str: JSON格式的交锋记录
    """
    import requests
    
    try:
        # 先检查缓存
        cache_key = f"{team1_id}_vs_{team2_id}"
        cached_data = _cache_manager.get("head_to_head", cache_key)
        if cached_data:
            return json.dumps({
                "success": True,
                "message": "Data from cache",
                "data": cached_data,
                "source": "cache"
            })
        
        # 尝试使用备用方案：获取两队的最近比赛，然后筛选交锋记录
        # 这里使用简化实现，实际应用中可能需要更复杂的逻辑
        
        # 获取team1的比赛记录
        team1_matches_result = get_team_last_matches(team1_id, 20)
        team1_data = json.loads(team1_matches_result)
        
        if not team1_data.get("success"):
            return json.dumps({
                "success": False,
                "message": "Failed to get team1 match history"
            })
        
        # 筛选与team2的交锋
        h2h_matches = []
        for match in team1_data["data"]["matches"]:
            home_team_id = match.get("home_team_id")
            away_team_id = match.get("away_team_id")
            
            # 简化判断：通过球队名称匹配
            if team2_id in [home_team_id, away_team_id]:
                h2h_matches.append(match)
        
        if not h2h_matches:
            return json.dumps({
                "success": True,
                "message": "No head-to-head records found in recent matches",
                "data": {
                    "team1_id": team1_id,
                    "team2_id": team2_id,
                    "matches": [],
                    "count": 0
                }
            })
        
        # 计算交锋统计
        stats = _calculate_h2h_stats(h2h_matches, team1_id, team2_id)
        
        result_data = {
            "team1_id": team1_id,
            "team2_id": team2_id,
            "matches": h2h_matches,
            "count": len(h2h_matches),
            "statistics": stats
        }
        
        # 缓存结果（7天）
        _cache_manager.set("head_to_head", cache_key, result_data, 7 * 24 * 3600)
        
        return json.dumps({
            "success": True,
            "message": f"Retrieved {len(h2h_matches)} head-to-head matches",
            "data": result_data,
            "source": "api"
        })
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
            "message": "Failed to get head-to-head records"
        })


# ============================================================================
# 辅助函数
# ============================================================================

def _calculate_match_stats(matches: List[Dict[str, Any]], team_id: str) -> Dict[str, Any]:
    """计算比赛统计数据"""
    if not matches:
        return {}
    
    wins = 0
    draws = 0
    losses = 0
    goals_scored = 0
    goals_conceded = 0
    
    for match in matches:
        home_score = match.get("home_score")
        away_score = match.get("away_score")
        
        if home_score is None or away_score is None:
            continue
        
        home_score = int(home_score)
        away_score = int(away_score)
        
        # 判断是主场还是客场
        # 这里简化处理，实际需要更精确的判断
        is_home = True  # 简化假设
        
        if is_home:
            goals_scored += home_score
            goals_conceded += away_score
            if home_score > away_score:
                wins += 1
            elif home_score == away_score:
                draws += 1
            else:
                losses += 1
        else:
            goals_scored += away_score
            goals_conceded += home_score
            if away_score > home_score:
                wins += 1
            elif away_score == home_score:
                draws += 1
            else:
                losses += 1
    
    total_matches = wins + draws + losses
    win_rate = (wins / total_matches * 100) if total_matches > 0 else 0
    
    return {
        "total_matches": total_matches,
        "wins": wins,
        "draws": draws,
        "losses": losses,
        "win_rate": round(win_rate, 2),
        "goals_scored": goals_scored,
        "goals_conceded": goals_conceded,
        "goals_per_match": round(goals_scored / total_matches, 2) if total_matches > 0 else 0,
        "goals_conceded_per_match": round(goals_conceded / total_matches, 2) if total_matches > 0 else 0
    }


def _calculate_h2h_stats(matches: List[Dict[str, Any]], team1_id: str, team2_id: str) -> Dict[str, Any]:
    """计算历史交锋统计"""
    if not matches:
        return {}
    
    team1_wins = 0
    team2_wins = 0
    draws = 0
    
    for match in matches:
        home_score = match.get("home_score")
        away_score = match.get("away_score")
        
        if home_score is None or away_score is None:
            continue
        
        home_score = int(home_score)
        away_score = int(away_score)
        
        if home_score > away_score:
            team1_wins += 1
        elif home_score < away_score:
            team2_wins += 1
        else:
            draws += 1
    
    total = team1_wins + team2_wins + draws
    
    return {
        "total_matches": total,
        "team1_wins": team1_wins,
        "team2_wins": team2_wins,
        "draws": draws,
        "team1_win_rate": round(team1_wins / total * 100, 2) if total > 0 else 0,
        "team2_win_rate": round(team2_wins / total * 100, 2) if total > 0 else 0
    }
