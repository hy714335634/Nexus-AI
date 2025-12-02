"""
体育数据分析和预测工具

提供数据验证、统计分析、预测模型、报告生成等功能
"""

import json
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from statistics import mean, stdev

from strands import tool


# ============================================================================
# 数据验证工具
# ============================================================================

@tool
def validate_team_data(team_data: str) -> str:
    """
    验证球队数据的完整性和有效性
    
    Args:
        team_data: 球队数据（JSON字符串）
        
    Returns:
        str: JSON格式的验证结果
    """
    try:
        data = json.loads(team_data)
        
        required_fields = ["id", "name", "sport", "league"]
        optional_fields = ["country", "stadium", "formed_year", "description"]
        
        missing_required = [f for f in required_fields if f not in data or not data[f]]
        missing_optional = [f for f in optional_fields if f not in data or not data[f]]
        
        completeness = (len(required_fields) - len(missing_required)) / len(required_fields) * 100
        
        validation_result = {
            "valid": len(missing_required) == 0,
            "completeness": round(completeness, 2),
            "missing_required_fields": missing_required,
            "missing_optional_fields": missing_optional,
            "data_quality": "high" if completeness >= 90 else "medium" if completeness >= 70 else "low"
        }
        
        return json.dumps({
            "success": True,
            "validation": validation_result
        })
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
            "message": "Failed to validate team data"
        })


@tool
def validate_match_data(match_data: str) -> str:
    """
    验证比赛数据的完整性和有效性
    
    Args:
        match_data: 比赛数据（JSON字符串，可以是单场比赛或比赛列表）
        
    Returns:
        str: JSON格式的验证结果
    """
    try:
        data = json.loads(match_data)
        
        # 支持单场比赛和比赛列表
        matches = data if isinstance(data, list) else [data]
        
        required_fields = ["date", "home_team", "away_team"]
        score_fields = ["home_score", "away_score"]
        
        validation_results = []
        for match in matches:
            missing_required = [f for f in required_fields if f not in match or not match[f]]
            missing_scores = [f for f in score_fields if f not in match or match[f] is None]
            
            has_scores = len(missing_scores) == 0
            completeness = (len(required_fields + score_fields) - len(missing_required) - len(missing_scores)) / len(required_fields + score_fields) * 100
            
            validation_results.append({
                "match_id": match.get("id", "unknown"),
                "valid": len(missing_required) == 0,
                "has_scores": has_scores,
                "completeness": round(completeness, 2),
                "missing_required_fields": missing_required,
                "missing_score_fields": missing_scores
            })
        
        overall_valid = all(v["valid"] for v in validation_results)
        overall_completeness = mean([v["completeness"] for v in validation_results])
        
        return json.dumps({
            "success": True,
            "overall_valid": overall_valid,
            "overall_completeness": round(overall_completeness, 2),
            "total_matches": len(validation_results),
            "valid_matches": sum(1 for v in validation_results if v["valid"]),
            "matches_with_scores": sum(1 for v in validation_results if v["has_scores"]),
            "validation_details": validation_results
        })
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
            "message": "Failed to validate match data"
        })


# ============================================================================
# 统计分析工具
# ============================================================================

@tool
def calculate_team_statistics(match_history: str, team_id: str) -> str:
    """
    计算球队统计指标
    
    Args:
        match_history: 比赛历史数据（JSON字符串）
        team_id: 球队ID
        
    Returns:
        str: JSON格式的统计结果
    """
    try:
        data = json.loads(match_history)
        matches = data.get("matches", [])
        
        if not matches:
            return json.dumps({
                "success": False,
                "message": "No match data provided"
            })
        
        # 基础统计
        total_matches = 0
        wins = 0
        draws = 0
        losses = 0
        goals_scored = []
        goals_conceded = []
        home_matches = 0
        away_matches = 0
        home_wins = 0
        away_wins = 0
        
        for match in matches:
            home_score = match.get("home_score")
            away_score = match.get("away_score")
            
            if home_score is None or away_score is None:
                continue
            
            home_score = int(home_score)
            away_score = int(away_score)
            total_matches += 1
            
            # 判断主客场（简化处理）
            is_home = match.get("home_team_id") == team_id or team_id in match.get("home_team", "")
            
            if is_home:
                home_matches += 1
                goals_scored.append(home_score)
                goals_conceded.append(away_score)
                
                if home_score > away_score:
                    wins += 1
                    home_wins += 1
                elif home_score == away_score:
                    draws += 1
                else:
                    losses += 1
            else:
                away_matches += 1
                goals_scored.append(away_score)
                goals_conceded.append(home_score)
                
                if away_score > home_score:
                    wins += 1
                    away_wins += 1
                elif away_score == home_score:
                    draws += 1
                else:
                    losses += 1
        
        # 计算高级指标
        win_rate = (wins / total_matches * 100) if total_matches > 0 else 0
        home_win_rate = (home_wins / home_matches * 100) if home_matches > 0 else 0
        away_win_rate = (away_wins / away_matches * 100) if away_matches > 0 else 0
        
        avg_goals_scored = mean(goals_scored) if goals_scored else 0
        avg_goals_conceded = mean(goals_conceded) if goals_conceded else 0
        goal_difference = sum(goals_scored) - sum(goals_conceded)
        
        # 近期状态（最近5场）
        recent_matches = matches[:5]
        recent_form = []
        for match in recent_matches:
            home_score = match.get("home_score")
            away_score = match.get("away_score")
            
            if home_score is None or away_score is None:
                continue
            
            home_score = int(home_score)
            away_score = int(away_score)
            
            is_home = match.get("home_team_id") == team_id or team_id in match.get("home_team", "")
            
            if is_home:
                if home_score > away_score:
                    recent_form.append("W")
                elif home_score == away_score:
                    recent_form.append("D")
                else:
                    recent_form.append("L")
            else:
                if away_score > home_score:
                    recent_form.append("W")
                elif away_score == home_score:
                    recent_form.append("D")
                else:
                    recent_form.append("L")
        
        # 计算近期状态得分
        form_score = sum(3 if r == "W" else 1 if r == "D" else 0 for r in recent_form)
        max_form_score = len(recent_form) * 3
        form_percentage = (form_score / max_form_score * 100) if max_form_score > 0 else 0
        
        statistics = {
            "team_id": team_id,
            "total_matches": total_matches,
            "wins": wins,
            "draws": draws,
            "losses": losses,
            "win_rate": round(win_rate, 2),
            "home_matches": home_matches,
            "away_matches": away_matches,
            "home_win_rate": round(home_win_rate, 2),
            "away_win_rate": round(away_win_rate, 2),
            "goals_scored": sum(goals_scored),
            "goals_conceded": sum(goals_conceded),
            "goal_difference": goal_difference,
            "avg_goals_scored": round(avg_goals_scored, 2),
            "avg_goals_conceded": round(avg_goals_conceded, 2),
            "recent_form": "".join(recent_form),
            "recent_form_score": form_score,
            "recent_form_percentage": round(form_percentage, 2),
            "clean_sheets": sum(1 for g in goals_conceded if g == 0),
            "failed_to_score": sum(1 for g in goals_scored if g == 0)
        }
        
        return json.dumps({
            "success": True,
            "statistics": statistics
        })
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
            "message": "Failed to calculate statistics"
        })


@tool
def analyze_recent_form(match_history: str, team_id: str, num_matches: int = 5) -> str:
    """
    分析球队近期状态和趋势
    
    Args:
        match_history: 比赛历史数据（JSON字符串）
        team_id: 球队ID
        num_matches: 分析的比赛数量，默认5场
        
    Returns:
        str: JSON格式的近期状态分析
    """
    try:
        data = json.loads(match_history)
        matches = data.get("matches", [])[:num_matches]
        
        if not matches:
            return json.dumps({
                "success": False,
                "message": "No match data provided"
            })
        
        form_results = []
        points = []
        goals_scored = []
        goals_conceded = []
        
        for match in matches:
            home_score = match.get("home_score")
            away_score = match.get("away_score")
            
            if home_score is None or away_score is None:
                continue
            
            home_score = int(home_score)
            away_score = int(away_score)
            
            is_home = match.get("home_team_id") == team_id or team_id in match.get("home_team", "")
            
            if is_home:
                goals_scored.append(home_score)
                goals_conceded.append(away_score)
                
                if home_score > away_score:
                    form_results.append("W")
                    points.append(3)
                elif home_score == away_score:
                    form_results.append("D")
                    points.append(1)
                else:
                    form_results.append("L")
                    points.append(0)
            else:
                goals_scored.append(away_score)
                goals_conceded.append(home_score)
                
                if away_score > home_score:
                    form_results.append("W")
                    points.append(3)
                elif away_score == home_score:
                    form_results.append("D")
                    points.append(1)
                else:
                    form_results.append("L")
                    points.append(0)
        
        # 分析趋势
        if len(points) >= 3:
            early_points = sum(points[:len(points)//2])
            late_points = sum(points[len(points)//2:])
            
            if late_points > early_points:
                trend = "improving"
            elif late_points < early_points:
                trend = "declining"
            else:
                trend = "stable"
        else:
            trend = "insufficient_data"
        
        total_points = sum(points)
        max_points = len(points) * 3
        form_percentage = (total_points / max_points * 100) if max_points > 0 else 0
        
        # 状态评级
        if form_percentage >= 80:
            form_rating = "excellent"
        elif form_percentage >= 60:
            form_rating = "good"
        elif form_percentage >= 40:
            form_rating = "average"
        else:
            form_rating = "poor"
        
        analysis = {
            "team_id": team_id,
            "matches_analyzed": len(form_results),
            "form_string": "".join(form_results),
            "wins": form_results.count("W"),
            "draws": form_results.count("D"),
            "losses": form_results.count("L"),
            "total_points": total_points,
            "max_points": max_points,
            "form_percentage": round(form_percentage, 2),
            "form_rating": form_rating,
            "trend": trend,
            "avg_goals_scored": round(mean(goals_scored), 2) if goals_scored else 0,
            "avg_goals_conceded": round(mean(goals_conceded), 2) if goals_conceded else 0,
            "scoring_consistency": round(stdev(goals_scored), 2) if len(goals_scored) > 1 else 0,
            "defensive_consistency": round(stdev(goals_conceded), 2) if len(goals_conceded) > 1 else 0
        }
        
        return json.dumps({
            "success": True,
            "analysis": analysis
        })
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
            "message": "Failed to analyze recent form"
        })


# ============================================================================
# 预测模型工具
# ============================================================================

@tool
def predict_match_outcome(
    team1_stats: str,
    team2_stats: str,
    is_home: bool,
    head_to_head: str = None
) -> str:
    """
    基于权重评分模型预测比赛结果
    
    权重分配：
    - 实力对比（整体胜率、进攻防守能力）：40%
    - 近期状态（最近5场表现）：20%
    - 主客场优势：15%
    - 球员影响（伤病、状态）：15%
    - 历史交锋：10%
    
    Args:
        team1_stats: 球队1统计数据（JSON字符串）
        team2_stats: 球队2统计数据（JSON字符串）
        is_home: 球队1是否主场作战
        head_to_head: 历史交锋数据（JSON字符串，可选）
        
    Returns:
        str: JSON格式的预测结果
    """
    try:
        stats1 = json.loads(team1_stats)
        stats2 = json.loads(team2_stats)
        
        # 1. 实力对比得分（40%）
        strength_score = _calculate_strength_score(stats1, stats2)
        
        # 2. 近期状态得分（20%）
        form_score = _calculate_form_score(stats1, stats2)
        
        # 3. 主客场得分（15%）
        home_score = _calculate_home_advantage_score(stats1, stats2, is_home)
        
        # 4. 球员影响得分（15%）- 简化实现，基于进攻稳定性
        player_score = _calculate_player_impact_score(stats1, stats2)
        
        # 5. 历史交锋得分（10%）
        h2h_score = 0.0
        if head_to_head:
            h2h_data = json.loads(head_to_head)
            h2h_score = _calculate_h2h_score(h2h_data, stats1.get("team_id"), stats2.get("team_id"))
        
        # 综合得分
        team1_score = (
            strength_score * 0.40 +
            form_score * 0.20 +
            home_score * 0.15 +
            player_score * 0.15 +
            h2h_score * 0.10
        )
        
        # 归一化到0-100
        team1_win_probability = max(0, min(100, 50 + team1_score))
        team2_win_probability = 100 - team1_win_probability
        
        # 计算平局概率（基于实力接近程度）
        strength_gap = abs(strength_score)
        if strength_gap < 10:
            draw_probability = 25
        elif strength_gap < 20:
            draw_probability = 20
        else:
            draw_probability = 15
        
        # 调整胜负概率
        team1_win_probability = team1_win_probability * (1 - draw_probability / 100)
        team2_win_probability = team2_win_probability * (1 - draw_probability / 100)
        
        # 评估置信度
        confidence = _calculate_confidence(stats1, stats2, head_to_head)
        
        # 生成预测结果
        if team1_win_probability > team2_win_probability + 10:
            prediction = "team1_win"
            predicted_winner = stats1.get("team_id")
        elif team2_win_probability > team1_win_probability + 10:
            prediction = "team2_win"
            predicted_winner = stats2.get("team_id")
        else:
            prediction = "close_match"
            predicted_winner = None
        
        result = {
            "prediction": prediction,
            "predicted_winner": predicted_winner,
            "team1_win_probability": round(team1_win_probability, 2),
            "team2_win_probability": round(team2_win_probability, 2),
            "draw_probability": round(draw_probability, 2),
            "confidence": confidence,
            "score_breakdown": {
                "strength_comparison": round(strength_score, 2),
                "recent_form": round(form_score, 2),
                "home_advantage": round(home_score, 2),
                "player_impact": round(player_score, 2),
                "head_to_head": round(h2h_score, 2)
            },
            "weights": {
                "strength": 0.40,
                "form": 0.20,
                "home_advantage": 0.15,
                "player_impact": 0.15,
                "head_to_head": 0.10
            }
        }
        
        return json.dumps({
            "success": True,
            "prediction": result
        })
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
            "message": "Failed to predict match outcome"
        })


# ============================================================================
# 报告生成工具
# ============================================================================

@tool
def generate_prediction_report(
    team1_info: str,
    team2_info: str,
    team1_stats: str,
    team2_stats: str,
    prediction: str,
    match_info: str = None
) -> str:
    """
    生成结构化的预测报告
    
    Args:
        team1_info: 球队1基本信息（JSON字符串）
        team2_info: 球队2基本信息（JSON字符串）
        team1_stats: 球队1统计数据（JSON字符串）
        team2_stats: 球队2统计数据（JSON字符串）
        prediction: 预测结果（JSON字符串）
        match_info: 比赛信息（JSON字符串，可选）
        
    Returns:
        str: JSON格式的预测报告
    """
    try:
        info1 = json.loads(team1_info)
        info2 = json.loads(team2_info)
        stats1 = json.loads(team1_stats)
        stats2 = json.loads(team2_stats)
        pred = json.loads(prediction)
        
        match_data = json.loads(match_info) if match_info else {}
        
        # 生成报告
        report = {
            "report_metadata": {
                "generated_at": datetime.now().isoformat(),
                "report_type": "match_prediction",
                "version": "1.0"
            },
            "match_overview": {
                "team1": {
                    "id": info1.get("id"),
                    "name": info1.get("name"),
                    "league": info1.get("league"),
                    "country": info1.get("country")
                },
                "team2": {
                    "id": info2.get("id"),
                    "name": info2.get("name"),
                    "league": info2.get("league"),
                    "country": info2.get("country")
                },
                "match_date": match_data.get("date"),
                "venue": match_data.get("venue"),
                "league": match_data.get("league")
            },
            "prediction_summary": {
                "prediction": pred.get("prediction"),
                "predicted_winner": pred.get("predicted_winner"),
                "team1_win_probability": pred.get("team1_win_probability"),
                "team2_win_probability": pred.get("team2_win_probability"),
                "draw_probability": pred.get("draw_probability"),
                "confidence": pred.get("confidence")
            },
            "analysis_details": {
                "team1_statistics": {
                    "win_rate": stats1.get("win_rate"),
                    "recent_form": stats1.get("recent_form"),
                    "recent_form_percentage": stats1.get("recent_form_percentage"),
                    "avg_goals_scored": stats1.get("avg_goals_scored"),
                    "avg_goals_conceded": stats1.get("avg_goals_conceded"),
                    "home_win_rate": stats1.get("home_win_rate"),
                    "away_win_rate": stats1.get("away_win_rate")
                },
                "team2_statistics": {
                    "win_rate": stats2.get("win_rate"),
                    "recent_form": stats2.get("recent_form"),
                    "recent_form_percentage": stats2.get("recent_form_percentage"),
                    "avg_goals_scored": stats2.get("avg_goals_scored"),
                    "avg_goals_conceded": stats2.get("avg_goals_conceded"),
                    "home_win_rate": stats2.get("home_win_rate"),
                    "away_win_rate": stats2.get("away_win_rate")
                },
                "score_breakdown": pred.get("score_breakdown"),
                "key_factors": _generate_key_factors(stats1, stats2, pred)
            },
            "recommendations": _generate_recommendations(pred)
        }
        
        return json.dumps({
            "success": True,
            "report": report
        })
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
            "message": "Failed to generate prediction report"
        })


# ============================================================================
# 辅助函数
# ============================================================================

def _calculate_strength_score(stats1: Dict, stats2: Dict) -> float:
    """计算实力对比得分（-50到+50，正值表示team1更强）"""
    # 胜率对比
    win_rate_diff = stats1.get("win_rate", 0) - stats2.get("win_rate", 0)
    
    # 进攻能力对比
    attack_diff = stats1.get("avg_goals_scored", 0) - stats2.get("avg_goals_scored", 0)
    
    # 防守能力对比（进球少的更好）
    defense_diff = stats2.get("avg_goals_conceded", 0) - stats1.get("avg_goals_conceded", 0)
    
    # 综合得分
    strength_score = (win_rate_diff * 0.5 + attack_diff * 5 + defense_diff * 5)
    
    return max(-50, min(50, strength_score))


def _calculate_form_score(stats1: Dict, stats2: Dict) -> float:
    """计算近期状态得分（-50到+50）"""
    form1 = stats1.get("recent_form_percentage", 50)
    form2 = stats2.get("recent_form_percentage", 50)
    
    form_diff = form1 - form2
    
    return max(-50, min(50, form_diff))


def _calculate_home_advantage_score(stats1: Dict, stats2: Dict, is_home: bool) -> float:
    """计算主客场优势得分（-50到+50）"""
    if is_home:
        home_rate1 = stats1.get("home_win_rate", 50)
        away_rate2 = stats2.get("away_win_rate", 50)
        advantage = (home_rate1 - away_rate2) * 0.5 + 10  # 主场额外加成
    else:
        away_rate1 = stats1.get("away_win_rate", 50)
        home_rate2 = stats2.get("home_win_rate", 50)
        advantage = (away_rate1 - home_rate2) * 0.5 - 10  # 客场劣势
    
    return max(-50, min(50, advantage))


def _calculate_player_impact_score(stats1: Dict, stats2: Dict) -> float:
    """计算球员影响得分（-50到+50）"""
    # 简化实现：基于进攻稳定性
    # 实际应用中应考虑伤病、红黄牌等因素
    
    # 零封场次对比
    clean_sheets1 = stats1.get("clean_sheets", 0)
    clean_sheets2 = stats2.get("clean_sheets", 0)
    
    # 零进球场次对比（少的更好）
    failed_score1 = stats1.get("failed_to_score", 0)
    failed_score2 = stats2.get("failed_to_score", 0)
    
    impact_score = (clean_sheets1 - clean_sheets2) * 5 - (failed_score1 - failed_score2) * 5
    
    return max(-50, min(50, impact_score))


def _calculate_h2h_score(h2h_data: Dict, team1_id: str, team2_id: str) -> float:
    """计算历史交锋得分（-50到+50）"""
    stats = h2h_data.get("statistics", {})
    
    team1_wins = stats.get("team1_wins", 0)
    team2_wins = stats.get("team2_wins", 0)
    total = stats.get("total_matches", 0)
    
    if total == 0:
        return 0
    
    win_rate_diff = (team1_wins - team2_wins) / total * 100
    
    return max(-50, min(50, win_rate_diff))


def _calculate_confidence(stats1: Dict, stats2: Dict, head_to_head: str) -> str:
    """评估预测置信度"""
    # 数据完整性
    completeness1 = 100 if stats1.get("total_matches", 0) >= 5 else 50
    completeness2 = 100 if stats2.get("total_matches", 0) >= 5 else 50
    
    # 历史交锋数据
    h2h_completeness = 100 if head_to_head else 0
    
    # 综合评分
    avg_completeness = (completeness1 + completeness2 + h2h_completeness) / 3
    
    if avg_completeness >= 80:
        return "high"
    elif avg_completeness >= 50:
        return "medium"
    else:
        return "low"


def _generate_key_factors(stats1: Dict, stats2: Dict, prediction: Dict) -> List[str]:
    """生成关键因素说明"""
    factors = []
    
    breakdown = prediction.get("score_breakdown", {})
    
    # 实力对比
    strength = breakdown.get("strength_comparison", 0)
    if abs(strength) > 20:
        stronger_team = "球队1" if strength > 0 else "球队2"
        factors.append(f"{stronger_team}在整体实力上占据明显优势")
    
    # 近期状态
    form = breakdown.get("recent_form", 0)
    if abs(form) > 20:
        better_form = "球队1" if form > 0 else "球队2"
        factors.append(f"{better_form}近期状态更佳")
    
    # 主客场
    home = breakdown.get("home_advantage", 0)
    if abs(home) > 10:
        if home > 0:
            factors.append("球队1享有主场优势")
        else:
            factors.append("球队2主场作战更有信心")
    
    # 历史交锋
    h2h = breakdown.get("head_to_head", 0)
    if abs(h2h) > 20:
        dominant_team = "球队1" if h2h > 0 else "球队2"
        factors.append(f"{dominant_team}在历史交锋中占优")
    
    if not factors:
        factors.append("两队实力接近，比赛结果难以预测")
    
    return factors


def _generate_recommendations(prediction: Dict) -> List[str]:
    """生成预测建议"""
    recommendations = []
    
    confidence = prediction.get("confidence")
    team1_prob = prediction.get("team1_win_probability", 0)
    team2_prob = prediction.get("team2_win_probability", 0)
    draw_prob = prediction.get("draw_probability", 0)
    
    if confidence == "low":
        recommendations.append("预测置信度较低，建议谨慎参考")
        recommendations.append("数据不完整可能影响预测准确性")
    
    if abs(team1_prob - team2_prob) < 10:
        recommendations.append("两队实力接近，比赛存在较大不确定性")
        recommendations.append("建议关注临场因素（伤病、天气等）")
    
    if draw_prob > 20:
        recommendations.append("平局概率较高，双方可能战成平手")
    
    if confidence == "high" and max(team1_prob, team2_prob) > 60:
        recommendations.append("预测置信度高，结果相对可靠")
    
    return recommendations
