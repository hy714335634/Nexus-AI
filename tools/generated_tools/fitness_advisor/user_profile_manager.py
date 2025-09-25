"""
用户数据管理工具 - 用于保存和检索用户信息、健身目标和进度
"""

import json
import os
import time
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple, Union
from strands import tool

# 用户数据存储目录
USER_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".cache", "fitness_advisor")

# 确保存储目录存在
os.makedirs(USER_DATA_DIR, exist_ok=True)

@tool
def save_user_profile(
    user_id: str,
    profile_data: Dict[str, Any],
    overwrite: bool = True
) -> str:
    """
    保存用户个人资料
    
    Args:
        user_id: 用户唯一标识符
        profile_data: 用户资料数据，包含个人信息如身高、体重、年龄等
        overwrite: 是否覆盖现有资料，默认为True
    
    Returns:
        str: JSON格式的操作结果
    """
    try:
        # 验证用户ID
        if not user_id or not isinstance(user_id, str):
            raise ValueError("用户ID必须是非空字符串")
        
        # 验证资料数据
        if not isinstance(profile_data, dict):
            raise ValueError("资料数据必须是字典格式")
        
        # 必要的字段验证
        required_fields = ["age", "gender", "height", "weight"]
        missing_fields = [field for field in required_fields if field not in profile_data]
        if missing_fields:
            raise ValueError(f"缺少必要的资料字段: {', '.join(missing_fields)}")
        
        # 验证数据类型和范围
        if not isinstance(profile_data.get("age"), (int, float)) or profile_data.get("age") <= 0:
            raise ValueError("年龄必须是正数")
        
        if profile_data.get("gender") not in ["male", "female", "other"]:
            raise ValueError("性别必须是 'male', 'female' 或 'other'")
        
        if not isinstance(profile_data.get("height"), (int, float)) or profile_data.get("height") <= 0:
            raise ValueError("身高必须是正数")
        
        if not isinstance(profile_data.get("weight"), (int, float)) or profile_data.get("weight") <= 0:
            raise ValueError("体重必须是正数")
        
        # 构建用户文件路径
        user_file_path = os.path.join(USER_DATA_DIR, f"{user_id}_profile.json")
        
        # 检查文件是否存在
        file_exists = os.path.exists(user_file_path)
        
        # 如果文件存在且不允许覆盖，则返回错误
        if file_exists and not overwrite:
            return json.dumps({
                "status": "error",
                "message": "用户资料已存在，未启用覆盖选项",
                "timestamp": datetime.now().isoformat()
            }, ensure_ascii=False)
        
        # 添加时间戳
        profile_data["last_updated"] = datetime.now().isoformat()
        
        # 如果是新用户，添加创建时间
        if not file_exists:
            profile_data["created_at"] = datetime.now().isoformat()
        else:
            # 如果是更新，保留创建时间
            try:
                with open(user_file_path, 'r', encoding='utf-8') as file:
                    existing_data = json.load(file)
                    if "created_at" in existing_data:
                        profile_data["created_at"] = existing_data["created_at"]
            except (json.JSONDecodeError, FileNotFoundError):
                profile_data["created_at"] = datetime.now().isoformat()
        
        # 保存数据
        with open(user_file_path, 'w', encoding='utf-8') as file:
            json.dump(profile_data, file, ensure_ascii=False, indent=2)
        
        return json.dumps({
            "status": "success",
            "message": "用户资料保存成功",
            "user_id": user_id,
            "timestamp": datetime.now().isoformat(),
            "is_new_user": not file_exists
        }, ensure_ascii=False)
    
    except ValueError as e:
        return json.dumps({
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }, ensure_ascii=False)
    
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"保存用户资料时发生错误: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }, ensure_ascii=False)

@tool
def get_user_profile(user_id: str) -> str:
    """
    获取用户个人资料
    
    Args:
        user_id: 用户唯一标识符
    
    Returns:
        str: JSON格式的用户资料数据
    """
    try:
        # 验证用户ID
        if not user_id or not isinstance(user_id, str):
            raise ValueError("用户ID必须是非空字符串")
        
        # 构建用户文件路径
        user_file_path = os.path.join(USER_DATA_DIR, f"{user_id}_profile.json")
        
        # 检查文件是否存在
        if not os.path.exists(user_file_path):
            return json.dumps({
                "status": "error",
                "message": f"用户 {user_id} 的资料不存在",
                "timestamp": datetime.now().isoformat()
            }, ensure_ascii=False)
        
        # 读取用户资料
        with open(user_file_path, 'r', encoding='utf-8') as file:
            profile_data = json.load(file)
        
        return json.dumps({
            "status": "success",
            "user_id": user_id,
            "profile": profile_data,
            "timestamp": datetime.now().isoformat()
        }, ensure_ascii=False)
    
    except json.JSONDecodeError:
        return json.dumps({
            "status": "error",
            "message": f"用户 {user_id} 的资料文件格式无效",
            "timestamp": datetime.now().isoformat()
        }, ensure_ascii=False)
    
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"获取用户资料时发生错误: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }, ensure_ascii=False)

@tool
def save_fitness_goal(
    user_id: str,
    goal_data: Dict[str, Any],
    goal_id: Optional[str] = None,
    overwrite: bool = True
) -> str:
    """
    保存用户健身目标
    
    Args:
        user_id: 用户唯一标识符
        goal_data: 健身目标数据，包含目标类型、目标值、时间期限等
        goal_id: 目标唯一标识符，如果不提供则自动生成
        overwrite: 是否覆盖现有目标，默认为True
    
    Returns:
        str: JSON格式的操作结果
    """
    try:
        # 验证用户ID
        if not user_id or not isinstance(user_id, str):
            raise ValueError("用户ID必须是非空字符串")
        
        # 验证目标数据
        if not isinstance(goal_data, dict):
            raise ValueError("目标数据必须是字典格式")
        
        # 必要的字段验证
        required_fields = ["type", "target_value", "timeframe"]
        missing_fields = [field for field in required_fields if field not in goal_data]
        if missing_fields:
            raise ValueError(f"缺少必要的目标字段: {', '.join(missing_fields)}")
        
        # 验证目标类型
        valid_goal_types = ["weight_loss", "muscle_gain", "endurance", "strength", "flexibility", "general_fitness"]
        if goal_data["type"] not in valid_goal_types:
            raise ValueError(f"目标类型无效，有效类型: {', '.join(valid_goal_types)}")
        
        # 构建目标文件路径
        goals_file_path = os.path.join(USER_DATA_DIR, f"{user_id}_goals.json")
        
        # 读取现有目标或创建新的目标列表
        goals = {}
        if os.path.exists(goals_file_path):
            try:
                with open(goals_file_path, 'r', encoding='utf-8') as file:
                    goals = json.load(file)
            except json.JSONDecodeError:
                goals = {}
        
        # 如果没有提供目标ID，生成一个新的
        if not goal_id:
            goal_id = f"goal_{int(time.time())}"
        
        # 如果目标已存在且不允许覆盖，则返回错误
        if goal_id in goals and not overwrite:
            return json.dumps({
                "status": "error",
                "message": "目标已存在，未启用覆盖选项",
                "timestamp": datetime.now().isoformat()
            }, ensure_ascii=False)
        
        # 添加时间戳和状态
        goal_data["last_updated"] = datetime.now().isoformat()
        goal_data["status"] = goal_data.get("status", "active")  # 默认为活动状态
        
        # 如果是新目标，添加创建时间
        if goal_id not in goals:
            goal_data["created_at"] = datetime.now().isoformat()
        else:
            # 如果是更新，保留创建时间
            if "created_at" in goals[goal_id]:
                goal_data["created_at"] = goals[goal_id]["created_at"]
            else:
                goal_data["created_at"] = datetime.now().isoformat()
        
        # 保存目标
        goals[goal_id] = goal_data
        
        # 写入文件
        with open(goals_file_path, 'w', encoding='utf-8') as file:
            json.dump(goals, file, ensure_ascii=False, indent=2)
        
        return json.dumps({
            "status": "success",
            "message": "健身目标保存成功",
            "user_id": user_id,
            "goal_id": goal_id,
            "timestamp": datetime.now().isoformat()
        }, ensure_ascii=False)
    
    except ValueError as e:
        return json.dumps({
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }, ensure_ascii=False)
    
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"保存健身目标时发生错误: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }, ensure_ascii=False)

@tool
def get_fitness_goals(
    user_id: str,
    goal_id: Optional[str] = None,
    status: Optional[str] = None
) -> str:
    """
    获取用户健身目标
    
    Args:
        user_id: 用户唯一标识符
        goal_id: 目标唯一标识符，如果提供则只返回特定目标
        status: 筛选目标状态，如"active"、"completed"、"abandoned"等
    
    Returns:
        str: JSON格式的健身目标数据
    """
    try:
        # 验证用户ID
        if not user_id or not isinstance(user_id, str):
            raise ValueError("用户ID必须是非空字符串")
        
        # 构建目标文件路径
        goals_file_path = os.path.join(USER_DATA_DIR, f"{user_id}_goals.json")
        
        # 检查文件是否存在
        if not os.path.exists(goals_file_path):
            return json.dumps({
                "status": "error",
                "message": f"用户 {user_id} 的健身目标不存在",
                "timestamp": datetime.now().isoformat()
            }, ensure_ascii=False)
        
        # 读取健身目标
        with open(goals_file_path, 'r', encoding='utf-8') as file:
            goals = json.load(file)
        
        # 如果提供了特定目标ID
        if goal_id:
            if goal_id not in goals:
                return json.dumps({
                    "status": "error",
                    "message": f"目标 {goal_id} 不存在",
                    "timestamp": datetime.now().isoformat()
                }, ensure_ascii=False)
            
            return json.dumps({
                "status": "success",
                "user_id": user_id,
                "goal_id": goal_id,
                "goal": goals[goal_id],
                "timestamp": datetime.now().isoformat()
            }, ensure_ascii=False)
        
        # 如果提供了状态筛选
        if status:
            filtered_goals = {gid: gdata for gid, gdata in goals.items() if gdata.get("status") == status}
            
            return json.dumps({
                "status": "success",
                "user_id": user_id,
                "goals": filtered_goals,
                "filter_status": status,
                "count": len(filtered_goals),
                "timestamp": datetime.now().isoformat()
            }, ensure_ascii=False)
        
        # 返回所有目标
        return json.dumps({
            "status": "success",
            "user_id": user_id,
            "goals": goals,
            "count": len(goals),
            "timestamp": datetime.now().isoformat()
        }, ensure_ascii=False)
    
    except json.JSONDecodeError:
        return json.dumps({
            "status": "error",
            "message": f"用户 {user_id} 的健身目标文件格式无效",
            "timestamp": datetime.now().isoformat()
        }, ensure_ascii=False)
    
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"获取健身目标时发生错误: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }, ensure_ascii=False)

@tool
def save_workout_record(
    user_id: str,
    workout_data: Dict[str, Any],
    record_id: Optional[str] = None
) -> str:
    """
    保存用户锻炼记录
    
    Args:
        user_id: 用户唯一标识符
        workout_data: 锻炼记录数据，包含锻炼类型、时长、强度等信息
        record_id: 记录唯一标识符，如果不提供则自动生成
    
    Returns:
        str: JSON格式的操作结果
    """
    try:
        # 验证用户ID
        if not user_id or not isinstance(user_id, str):
            raise ValueError("用户ID必须是非空字符串")
        
        # 验证锻炼数据
        if not isinstance(workout_data, dict):
            raise ValueError("锻炼数据必须是字典格式")
        
        # 必要的字段验证
        required_fields = ["type", "duration", "date"]
        missing_fields = [field for field in required_fields if field not in workout_data]
        if missing_fields:
            raise ValueError(f"缺少必要的锻炼记录字段: {', '.join(missing_fields)}")
        
        # 验证日期格式
        try:
            datetime.fromisoformat(workout_data["date"])
        except ValueError:
            raise ValueError("日期格式无效，请使用ISO格式 (YYYY-MM-DDTHH:MM:SS)")
        
        # 构建锻炼记录文件路径
        workouts_file_path = os.path.join(USER_DATA_DIR, f"{user_id}_workouts.json")
        
        # 读取现有锻炼记录或创建新的记录列表
        workouts = []
        if os.path.exists(workouts_file_path):
            try:
                with open(workouts_file_path, 'r', encoding='utf-8') as file:
                    workouts = json.load(file)
            except json.JSONDecodeError:
                workouts = []
        
        # 如果没有提供记录ID，生成一个新的
        if not record_id:
            record_id = f"workout_{int(time.time())}"
        
        # 添加记录ID和时间戳
        workout_data["record_id"] = record_id
        workout_data["recorded_at"] = datetime.now().isoformat()
        
        # 添加到锻炼记录列表
        workouts.append(workout_data)
        
        # 写入文件
        with open(workouts_file_path, 'w', encoding='utf-8') as file:
            json.dump(workouts, file, ensure_ascii=False, indent=2)
        
        return json.dumps({
            "status": "success",
            "message": "锻炼记录保存成功",
            "user_id": user_id,
            "record_id": record_id,
            "timestamp": datetime.now().isoformat()
        }, ensure_ascii=False)
    
    except ValueError as e:
        return json.dumps({
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }, ensure_ascii=False)
    
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"保存锻炼记录时发生错误: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }, ensure_ascii=False)

@tool
def get_workout_records(
    user_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    workout_type: Optional[str] = None,
    limit: int = 10
) -> str:
    """
    获取用户锻炼记录
    
    Args:
        user_id: 用户唯一标识符
        start_date: 开始日期，ISO格式 (YYYY-MM-DD)
        end_date: 结束日期，ISO格式 (YYYY-MM-DD)
        workout_type: 锻炼类型筛选
        limit: 返回记录的最大数量，默认为10
    
    Returns:
        str: JSON格式的锻炼记录数据
    """
    try:
        # 验证用户ID
        if not user_id or not isinstance(user_id, str):
            raise ValueError("用户ID必须是非空字符串")
        
        # 验证日期格式
        start_datetime = None
        end_datetime = None
        
        if start_date:
            try:
                start_datetime = datetime.fromisoformat(start_date)
                if len(start_date) == 10:  # 只有日期部分 (YYYY-MM-DD)
                    start_datetime = datetime.combine(start_datetime.date(), datetime.min.time())
            except ValueError:
                raise ValueError("开始日期格式无效，请使用ISO格式 (YYYY-MM-DD)")
        
        if end_date:
            try:
                end_datetime = datetime.fromisoformat(end_date)
                if len(end_date) == 10:  # 只有日期部分 (YYYY-MM-DD)
                    end_datetime = datetime.combine(end_datetime.date(), datetime.max.time())
            except ValueError:
                raise ValueError("结束日期格式无效，请使用ISO格式 (YYYY-MM-DD)")
        
        # 构建锻炼记录文件路径
        workouts_file_path = os.path.join(USER_DATA_DIR, f"{user_id}_workouts.json")
        
        # 检查文件是否存在
        if not os.path.exists(workouts_file_path):
            return json.dumps({
                "status": "error",
                "message": f"用户 {user_id} 的锻炼记录不存在",
                "timestamp": datetime.now().isoformat()
            }, ensure_ascii=False)
        
        # 读取锻炼记录
        with open(workouts_file_path, 'r', encoding='utf-8') as file:
            workouts = json.load(file)
        
        # 应用筛选条件
        filtered_workouts = workouts
        
        # 按日期筛选
        if start_datetime or end_datetime:
            filtered_workouts = []
            for workout in workouts:
                workout_date = datetime.fromisoformat(workout["date"])
                
                if start_datetime and workout_date < start_datetime:
                    continue
                
                if end_datetime and workout_date > end_datetime:
                    continue
                
                filtered_workouts.append(workout)
        
        # 按锻炼类型筛选
        if workout_type:
            filtered_workouts = [w for w in filtered_workouts if w.get("type") == workout_type]
        
        # 按日期排序（最新的在前）
        filtered_workouts.sort(key=lambda x: x["date"], reverse=True)
        
        # 限制返回数量
        limited_workouts = filtered_workouts[:limit]
        
        return json.dumps({
            "status": "success",
            "user_id": user_id,
            "workouts": limited_workouts,
            "count": len(limited_workouts),
            "total_count": len(filtered_workouts),
            "filters": {
                "start_date": start_date,
                "end_date": end_date,
                "workout_type": workout_type,
                "limit": limit
            },
            "timestamp": datetime.now().isoformat()
        }, ensure_ascii=False)
    
    except json.JSONDecodeError:
        return json.dumps({
            "status": "error",
            "message": f"用户 {user_id} 的锻炼记录文件格式无效",
            "timestamp": datetime.now().isoformat()
        }, ensure_ascii=False)
    
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"获取锻炼记录时发生错误: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }, ensure_ascii=False)

@tool
def save_body_measurement(
    user_id: str,
    measurement_data: Dict[str, Any],
    measurement_id: Optional[str] = None
) -> str:
    """
    保存用户身体测量数据
    
    Args:
        user_id: 用户唯一标识符
        measurement_data: 测量数据，包含体重、体脂率、围度等信息
        measurement_id: 测量记录唯一标识符，如果不提供则自动生成
    
    Returns:
        str: JSON格式的操作结果
    """
    try:
        # 验证用户ID
        if not user_id or not isinstance(user_id, str):
            raise ValueError("用户ID必须是非空字符串")
        
        # 验证测量数据
        if not isinstance(measurement_data, dict):
            raise ValueError("测量数据必须是字典格式")
        
        # 必要的字段验证
        required_fields = ["date"]
        missing_fields = [field for field in required_fields if field not in measurement_data]
        if missing_fields:
            raise ValueError(f"缺少必要的测量记录字段: {', '.join(missing_fields)}")
        
        # 验证至少有一个测量值
        measurement_fields = ["weight", "body_fat", "chest", "waist", "hips", "arms", "thighs"]
        if not any(field in measurement_data for field in measurement_fields):
            raise ValueError("至少需要提供一个测量值字段")
        
        # 验证日期格式
        try:
            datetime.fromisoformat(measurement_data["date"])
        except ValueError:
            raise ValueError("日期格式无效，请使用ISO格式 (YYYY-MM-DDTHH:MM:SS)")
        
        # 构建测量记录文件路径
        measurements_file_path = os.path.join(USER_DATA_DIR, f"{user_id}_measurements.json")
        
        # 读取现有测量记录或创建新的记录列表
        measurements = []
        if os.path.exists(measurements_file_path):
            try:
                with open(measurements_file_path, 'r', encoding='utf-8') as file:
                    measurements = json.load(file)
            except json.JSONDecodeError:
                measurements = []
        
        # 如果没有提供记录ID，生成一个新的
        if not measurement_id:
            measurement_id = f"measurement_{int(time.time())}"
        
        # 添加记录ID和时间戳
        measurement_data["measurement_id"] = measurement_id
        measurement_data["recorded_at"] = datetime.now().isoformat()
        
        # 添加到测量记录列表
        measurements.append(measurement_data)
        
        # 写入文件
        with open(measurements_file_path, 'w', encoding='utf-8') as file:
            json.dump(measurements, file, ensure_ascii=False, indent=2)
        
        return json.dumps({
            "status": "success",
            "message": "身体测量数据保存成功",
            "user_id": user_id,
            "measurement_id": measurement_id,
            "timestamp": datetime.now().isoformat()
        }, ensure_ascii=False)
    
    except ValueError as e:
        return json.dumps({
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }, ensure_ascii=False)
    
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"保存身体测量数据时发生错误: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }, ensure_ascii=False)

@tool
def get_body_measurements(
    user_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    measurement_type: Optional[str] = None,
    limit: int = 10
) -> str:
    """
    获取用户身体测量记录
    
    Args:
        user_id: 用户唯一标识符
        start_date: 开始日期，ISO格式 (YYYY-MM-DD)
        end_date: 结束日期，ISO格式 (YYYY-MM-DD)
        measurement_type: 测量类型筛选 (weight, body_fat, chest, waist, hips, arms, thighs)
        limit: 返回记录的最大数量，默认为10
    
    Returns:
        str: JSON格式的身体测量记录数据
    """
    try:
        # 验证用户ID
        if not user_id or not isinstance(user_id, str):
            raise ValueError("用户ID必须是非空字符串")
        
        # 验证日期格式
        start_datetime = None
        end_datetime = None
        
        if start_date:
            try:
                start_datetime = datetime.fromisoformat(start_date)
                if len(start_date) == 10:  # 只有日期部分 (YYYY-MM-DD)
                    start_datetime = datetime.combine(start_datetime.date(), datetime.min.time())
            except ValueError:
                raise ValueError("开始日期格式无效，请使用ISO格式 (YYYY-MM-DD)")
        
        if end_date:
            try:
                end_datetime = datetime.fromisoformat(end_date)
                if len(end_date) == 10:  # 只有日期部分 (YYYY-MM-DD)
                    end_datetime = datetime.combine(end_datetime.date(), datetime.max.time())
            except ValueError:
                raise ValueError("结束日期格式无效，请使用ISO格式 (YYYY-MM-DD)")
        
        # 构建测量记录文件路径
        measurements_file_path = os.path.join(USER_DATA_DIR, f"{user_id}_measurements.json")
        
        # 检查文件是否存在
        if not os.path.exists(measurements_file_path):
            return json.dumps({
                "status": "error",
                "message": f"用户 {user_id} 的身体测量记录不存在",
                "timestamp": datetime.now().isoformat()
            }, ensure_ascii=False)
        
        # 读取测量记录
        with open(measurements_file_path, 'r', encoding='utf-8') as file:
            measurements = json.load(file)
        
        # 应用筛选条件
        filtered_measurements = measurements
        
        # 按日期筛选
        if start_datetime or end_datetime:
            filtered_measurements = []
            for measurement in measurements:
                measurement_date = datetime.fromisoformat(measurement["date"])
                
                if start_datetime and measurement_date < start_datetime:
                    continue
                
                if end_datetime and measurement_date > end_datetime:
                    continue
                
                filtered_measurements.append(measurement)
        
        # 按测量类型筛选
        if measurement_type:
            filtered_measurements = [m for m in filtered_measurements if measurement_type in m]
        
        # 按日期排序（最新的在前）
        filtered_measurements.sort(key=lambda x: x["date"], reverse=True)
        
        # 限制返回数量
        limited_measurements = filtered_measurements[:limit]
        
        # 如果请求了特定类型的测量，提取趋势数据
        trend_data = None
        if measurement_type and filtered_measurements:
            # 按日期排序（最早的在前，用于趋势分析）
            sorted_for_trend = sorted(filtered_measurements, key=lambda x: x["date"])
            
            # 提取特定测量类型的数据点
            trend_data = {
                "dates": [m["date"] for m in sorted_for_trend if measurement_type in m],
                "values": [m[measurement_type] for m in sorted_for_trend if measurement_type in m]
            }
        
        return json.dumps({
            "status": "success",
            "user_id": user_id,
            "measurements": limited_measurements,
            "count": len(limited_measurements),
            "total_count": len(filtered_measurements),
            "filters": {
                "start_date": start_date,
                "end_date": end_date,
                "measurement_type": measurement_type,
                "limit": limit
            },
            "trend_data": trend_data,
            "timestamp": datetime.now().isoformat()
        }, ensure_ascii=False)
    
    except json.JSONDecodeError:
        return json.dumps({
            "status": "error",
            "message": f"用户 {user_id} 的身体测量记录文件格式无效",
            "timestamp": datetime.now().isoformat()
        }, ensure_ascii=False)
    
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"获取身体测量记录时发生错误: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }, ensure_ascii=False)

@tool
def get_user_progress(
    user_id: str,
    goal_id: Optional[str] = None,
    metric: Optional[str] = None,
    period: Optional[str] = "month"
) -> str:
    """
    获取用户健身进度报告
    
    Args:
        user_id: 用户唯一标识符
        goal_id: 特定目标的唯一标识符，如果提供则只分析该目标的进度
        metric: 要分析的特定指标 (weight, body_fat, workout_frequency, workout_duration)
        period: 时间周期 ("week", "month", "quarter", "year")，默认为"month"
    
    Returns:
        str: JSON格式的进度报告数据
    """
    try:
        # 验证用户ID
        if not user_id or not isinstance(user_id, str):
            raise ValueError("用户ID必须是非空字符串")
        
        # 验证时间周期
        valid_periods = ["week", "month", "quarter", "year"]
        if period not in valid_periods:
            raise ValueError(f"时间周期无效，有效值: {', '.join(valid_periods)}")
        
        # 获取当前日期
        now = datetime.now()
        
        # 根据时间周期确定开始日期
        if period == "week":
            start_date = (now - datetime.timedelta(days=7)).isoformat()
        elif period == "month":
            start_date = (now - datetime.timedelta(days=30)).isoformat()
        elif period == "quarter":
            start_date = (now - datetime.timedelta(days=90)).isoformat()
        else:  # year
            start_date = (now - datetime.timedelta(days=365)).isoformat()
        
        # 初始化进度报告
        progress_report = {
            "user_id": user_id,
            "period": period,
            "start_date": start_date,
            "end_date": now.isoformat(),
            "metrics": {}
        }
        
        # 如果提供了目标ID，获取目标信息
        if goal_id:
            goals_file_path = os.path.join(USER_DATA_DIR, f"{user_id}_goals.json")
            if os.path.exists(goals_file_path):
                with open(goals_file_path, 'r', encoding='utf-8') as file:
                    goals = json.load(file)
                
                if goal_id in goals:
                    progress_report["goal"] = goals[goal_id]
        
        # 获取身体测量记录
        measurements_file_path = os.path.join(USER_DATA_DIR, f"{user_id}_measurements.json")
        if os.path.exists(measurements_file_path):
            with open(measurements_file_path, 'r', encoding='utf-8') as file:
                measurements = json.load(file)
            
            # 筛选时间范围内的记录
            recent_measurements = [
                m for m in measurements 
                if m["date"] >= start_date and m["date"] <= now.isoformat()
            ]
            
            # 按日期排序
            recent_measurements.sort(key=lambda x: x["date"])
            
            # 分析体重变化
            if not metric or metric == "weight":
                weight_data = [m for m in recent_measurements if "weight" in m]
                if weight_data:
                    first_weight = weight_data[0]["weight"]
                    last_weight = weight_data[-1]["weight"]
                    weight_change = last_weight - first_weight
                    
                    progress_report["metrics"]["weight"] = {
                        "first_value": first_weight,
                        "last_value": last_weight,
                        "change": weight_change,
                        "change_percentage": round((weight_change / first_weight) * 100, 2) if first_weight else 0,
                        "data_points": len(weight_data),
                        "trend": "decreasing" if weight_change < 0 else "increasing" if weight_change > 0 else "stable"
                    }
            
            # 分析体脂率变化
            if not metric or metric == "body_fat":
                body_fat_data = [m for m in recent_measurements if "body_fat" in m]
                if body_fat_data:
                    first_body_fat = body_fat_data[0]["body_fat"]
                    last_body_fat = body_fat_data[-1]["body_fat"]
                    body_fat_change = last_body_fat - first_body_fat
                    
                    progress_report["metrics"]["body_fat"] = {
                        "first_value": first_body_fat,
                        "last_value": last_body_fat,
                        "change": body_fat_change,
                        "change_percentage": round((body_fat_change / first_body_fat) * 100, 2) if first_body_fat else 0,
                        "data_points": len(body_fat_data),
                        "trend": "decreasing" if body_fat_change < 0 else "increasing" if body_fat_change > 0 else "stable"
                    }
        
        # 获取锻炼记录
        workouts_file_path = os.path.join(USER_DATA_DIR, f"{user_id}_workouts.json")
        if os.path.exists(workouts_file_path):
            with open(workouts_file_path, 'r', encoding='utf-8') as file:
                workouts = json.load(file)
            
            # 筛选时间范围内的记录
            recent_workouts = [
                w for w in workouts 
                if w["date"] >= start_date and w["date"] <= now.isoformat()
            ]
            
            # 分析锻炼频率
            if not metric or metric == "workout_frequency":
                # 计算每周锻炼次数
                days_in_period = 7 if period == "week" else 30 if period == "month" else 90 if period == "quarter" else 365
                weeks_in_period = days_in_period / 7
                
                progress_report["metrics"]["workout_frequency"] = {
                    "total_workouts": len(recent_workouts),
                    "average_per_week": round(len(recent_workouts) / weeks_in_period, 2),
                    "workout_types": {}
                }
                
                # 统计各类型锻炼的次数
                for workout in recent_workouts:
                    workout_type = workout.get("type", "未指定")
                    if workout_type in progress_report["metrics"]["workout_frequency"]["workout_types"]:
                        progress_report["metrics"]["workout_frequency"]["workout_types"][workout_type] += 1
                    else:
                        progress_report["metrics"]["workout_frequency"]["workout_types"][workout_type] = 1
            
            # 分析锻炼时长
            if not metric or metric == "workout_duration":
                if recent_workouts:
                    total_duration = sum(w.get("duration", 0) for w in recent_workouts)
                    average_duration = total_duration / len(recent_workouts) if recent_workouts else 0
                    
                    progress_report["metrics"]["workout_duration"] = {
                        "total_duration": total_duration,
                        "average_duration": average_duration,
                        "data_points": len(recent_workouts)
                    }
        
        # 如果有目标，分析目标进度
        if "goal" in progress_report:
            goal = progress_report["goal"]
            goal_type = goal.get("type")
            target_value = goal.get("target_value")
            
            if goal_type == "weight_loss" and "weight" in progress_report["metrics"]:
                weight_change = progress_report["metrics"]["weight"]["change"]
                if target_value and weight_change < 0:  # 减重目标
                    progress_percentage = min(100, (abs(weight_change) / target_value) * 100)
                    progress_report["goal_progress"] = {
                        "percentage": round(progress_percentage, 2),
                        "remaining": max(0, target_value - abs(weight_change))
                    }
            
            elif goal_type == "muscle_gain" and "weight" in progress_report["metrics"]:
                weight_change = progress_report["metrics"]["weight"]["change"]
                if target_value and weight_change > 0:  # 增重目标
                    progress_percentage = min(100, (weight_change / target_value) * 100)
                    progress_report["goal_progress"] = {
                        "percentage": round(progress_percentage, 2),
                        "remaining": max(0, target_value - weight_change)
                    }
            
            elif goal_type == "body_fat_reduction" and "body_fat" in progress_report["metrics"]:
                body_fat_change = progress_report["metrics"]["body_fat"]["change"]
                if target_value and body_fat_change < 0:  # 减脂目标
                    progress_percentage = min(100, (abs(body_fat_change) / target_value) * 100)
                    progress_report["goal_progress"] = {
                        "percentage": round(progress_percentage, 2),
                        "remaining": max(0, target_value - abs(body_fat_change))
                    }
        
        return json.dumps({
            "status": "success",
            "progress_report": progress_report,
            "timestamp": datetime.now().isoformat()
        }, ensure_ascii=False)
    
    except ValueError as e:
        return json.dumps({
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }, ensure_ascii=False)
    
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"获取用户进度报告时发生错误: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }, ensure_ascii=False)

@tool
def delete_user_data(
    user_id: str,
    data_type: Literal["profile", "goals", "workouts", "measurements", "all"]
) -> str:
    """
    删除用户数据
    
    Args:
        user_id: 用户唯一标识符
        data_type: 要删除的数据类型
            - profile: 用户个人资料
            - goals: 健身目标
            - workouts: 锻炼记录
            - measurements: 身体测量记录
            - all: 所有用户数据
    
    Returns:
        str: JSON格式的操作结果
    """
    try:
        # 验证用户ID
        if not user_id or not isinstance(user_id, str):
            raise ValueError("用户ID必须是非空字符串")
        
        deleted_files = []
        
        # 根据数据类型删除相应文件
        if data_type == "profile" or data_type == "all":
            profile_file_path = os.path.join(USER_DATA_DIR, f"{user_id}_profile.json")
            if os.path.exists(profile_file_path):
                os.remove(profile_file_path)
                deleted_files.append("profile")
        
        if data_type == "goals" or data_type == "all":
            goals_file_path = os.path.join(USER_DATA_DIR, f"{user_id}_goals.json")
            if os.path.exists(goals_file_path):
                os.remove(goals_file_path)
                deleted_files.append("goals")
        
        if data_type == "workouts" or data_type == "all":
            workouts_file_path = os.path.join(USER_DATA_DIR, f"{user_id}_workouts.json")
            if os.path.exists(workouts_file_path):
                os.remove(workouts_file_path)
                deleted_files.append("workouts")
        
        if data_type == "measurements" or data_type == "all":
            measurements_file_path = os.path.join(USER_DATA_DIR, f"{user_id}_measurements.json")
            if os.path.exists(measurements_file_path):
                os.remove(measurements_file_path)
                deleted_files.append("measurements")
        
        if not deleted_files:
            return json.dumps({
                "status": "warning",
                "message": f"未找到用户 {user_id} 的 {data_type} 数据",
                "timestamp": datetime.now().isoformat()
            }, ensure_ascii=False)
        
        return json.dumps({
            "status": "success",
            "message": f"成功删除用户 {user_id} 的数据",
            "deleted_data_types": deleted_files,
            "timestamp": datetime.now().isoformat()
        }, ensure_ascii=False)
    
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"删除用户数据时发生错误: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }, ensure_ascii=False)