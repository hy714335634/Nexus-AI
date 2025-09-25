"""
时间管理工具 - 用于记录和跟踪用户健身进度和计划更新
"""

import json
import os
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Union, Literal
from strands import tool

# 时间数据存储目录
TIME_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".cache", "fitness_advisor", "time_tracker")

# 确保存储目录存在
os.makedirs(TIME_DATA_DIR, exist_ok=True)

@tool
def create_workout_schedule(
    user_id: str,
    schedule_data: Dict[str, Any],
    schedule_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> str:
    """
    创建用户健身计划表
    
    Args:
        user_id: 用户唯一标识符
        schedule_data: 健身计划数据，包含每周锻炼安排
        schedule_id: 计划唯一标识符，如果不提供则自动生成
        start_date: 计划开始日期，ISO格式 (YYYY-MM-DD)，如果不提供则使用当前日期
        end_date: 计划结束日期，ISO格式 (YYYY-MM-DD)，如果不提供则为无限期
    
    Returns:
        str: JSON格式的操作结果
    """
    try:
        # 验证用户ID
        if not user_id or not isinstance(user_id, str):
            raise ValueError("用户ID必须是非空字符串")
        
        # 验证计划数据
        if not isinstance(schedule_data, dict):
            raise ValueError("计划数据必须是字典格式")
        
        # 验证计划数据格式
        days_of_week = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        for day in days_of_week:
            if day in schedule_data:
                if not isinstance(schedule_data[day], list):
                    raise ValueError(f"{day} 的计划必须是列表格式")
                
                for workout in schedule_data[day]:
                    if not isinstance(workout, dict):
                        raise ValueError(f"{day} 的锻炼项目必须是字典格式")
                    
                    # 验证锻炼项目必要字段
                    if "type" not in workout:
                        raise ValueError(f"{day} 的锻炼项目缺少 'type' 字段")
        
        # 处理日期
        current_date = datetime.now()
        
        if start_date:
            try:
                start_datetime = datetime.fromisoformat(start_date)
                # 如果只提供了日期部分，添加时间部分
                if len(start_date) == 10:
                    start_datetime = datetime.combine(start_datetime.date(), datetime.min.time())
            except ValueError:
                raise ValueError("开始日期格式无效，请使用ISO格式 (YYYY-MM-DD)")
        else:
            # 默认使用当前日期
            start_datetime = datetime.combine(current_date.date(), datetime.min.time())
        
        if end_date:
            try:
                end_datetime = datetime.fromisoformat(end_date)
                # 如果只提供了日期部分，添加时间部分
                if len(end_date) == 10:
                    end_datetime = datetime.combine(end_datetime.date(), datetime.max.time())
            except ValueError:
                raise ValueError("结束日期格式无效，请使用ISO格式 (YYYY-MM-DD)")
        else:
            # 默认无结束日期
            end_datetime = None
        
        # 如果提供了结束日期，验证其是否晚于开始日期
        if end_datetime and end_datetime <= start_datetime:
            raise ValueError("结束日期必须晚于开始日期")
        
        # 生成计划ID（如果未提供）
        if not schedule_id:
            schedule_id = f"schedule_{int(time.time())}"
        
        # 构建计划文件路径
        schedule_file_path = os.path.join(TIME_DATA_DIR, f"{user_id}_schedules.json")
        
        # 读取现有计划或创建新的计划列表
        schedules = {}
        if os.path.exists(schedule_file_path):
            try:
                with open(schedule_file_path, 'r', encoding='utf-8') as file:
                    schedules = json.load(file)
            except json.JSONDecodeError:
                schedules = {}
        
        # 添加计划元数据
        schedule_with_metadata = {
            "id": schedule_id,
            "start_date": start_datetime.isoformat(),
            "end_date": end_datetime.isoformat() if end_datetime else None,
            "created_at": current_date.isoformat(),
            "last_updated": current_date.isoformat(),
            "schedule": schedule_data,
            "status": "active"
        }
        
        # 保存计划
        schedules[schedule_id] = schedule_with_metadata
        
        # 写入文件
        with open(schedule_file_path, 'w', encoding='utf-8') as file:
            json.dump(schedules, file, ensure_ascii=False, indent=2)
        
        return json.dumps({
            "status": "success",
            "message": "健身计划创建成功",
            "user_id": user_id,
            "schedule_id": schedule_id,
            "start_date": start_datetime.isoformat(),
            "end_date": end_datetime.isoformat() if end_datetime else None,
            "timestamp": current_date.isoformat()
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
            "message": f"创建健身计划时发生错误: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }, ensure_ascii=False)

@tool
def get_workout_schedule(
    user_id: str,
    schedule_id: Optional[str] = None,
    status: Optional[str] = "active",
    include_expired: bool = False
) -> str:
    """
    获取用户健身计划
    
    Args:
        user_id: 用户唯一标识符
        schedule_id: 计划唯一标识符，如果提供则只返回特定计划
        status: 筛选计划状态，如"active"、"completed"、"paused"等，默认为"active"
        include_expired: 是否包含已过期的计划，默认为False
    
    Returns:
        str: JSON格式的健身计划数据
    """
    try:
        # 验证用户ID
        if not user_id or not isinstance(user_id, str):
            raise ValueError("用户ID必须是非空字符串")
        
        # 构建计划文件路径
        schedule_file_path = os.path.join(TIME_DATA_DIR, f"{user_id}_schedules.json")
        
        # 检查文件是否存在
        if not os.path.exists(schedule_file_path):
            return json.dumps({
                "status": "error",
                "message": f"用户 {user_id} 的健身计划不存在",
                "timestamp": datetime.now().isoformat()
            }, ensure_ascii=False)
        
        # 读取健身计划
        with open(schedule_file_path, 'r', encoding='utf-8') as file:
            schedules = json.load(file)
        
        # 当前时间
        current_date = datetime.now()
        
        # 如果提供了特定计划ID
        if schedule_id:
            if schedule_id not in schedules:
                return json.dumps({
                    "status": "error",
                    "message": f"计划 {schedule_id} 不存在",
                    "timestamp": current_date.isoformat()
                }, ensure_ascii=False)
            
            schedule = schedules[schedule_id]
            
            # 检查计划是否已过期
            is_expired = False
            if schedule["end_date"]:
                end_datetime = datetime.fromisoformat(schedule["end_date"])
                is_expired = current_date > end_datetime
            
            # 如果计划已过期且不包含过期计划
            if is_expired and not include_expired:
                return json.dumps({
                    "status": "error",
                    "message": f"计划 {schedule_id} 已过期",
                    "timestamp": current_date.isoformat()
                }, ensure_ascii=False)
            
            return json.dumps({
                "status": "success",
                "user_id": user_id,
                "schedule_id": schedule_id,
                "schedule": schedule,
                "is_expired": is_expired,
                "timestamp": current_date.isoformat()
            }, ensure_ascii=False)
        
        # 筛选计划
        filtered_schedules = {}
        for sid, schedule in schedules.items():
            # 检查状态
            if status and schedule.get("status") != status:
                continue
            
            # 检查是否过期
            is_expired = False
            if schedule["end_date"]:
                end_datetime = datetime.fromisoformat(schedule["end_date"])
                is_expired = current_date > end_datetime
            
            if is_expired and not include_expired:
                continue
            
            # 添加到筛选结果
            schedule["is_expired"] = is_expired
            filtered_schedules[sid] = schedule
        
        return json.dumps({
            "status": "success",
            "user_id": user_id,
            "schedules": filtered_schedules,
            "count": len(filtered_schedules),
            "filters": {
                "status": status,
                "include_expired": include_expired
            },
            "timestamp": current_date.isoformat()
        }, ensure_ascii=False)
    
    except json.JSONDecodeError:
        return json.dumps({
            "status": "error",
            "message": f"用户 {user_id} 的健身计划文件格式无效",
            "timestamp": datetime.now().isoformat()
        }, ensure_ascii=False)
    
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"获取健身计划时发生错误: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }, ensure_ascii=False)

@tool
def update_workout_schedule(
    user_id: str,
    schedule_id: str,
    updates: Dict[str, Any]
) -> str:
    """
    更新用户健身计划
    
    Args:
        user_id: 用户唯一标识符
        schedule_id: 计划唯一标识符
        updates: 要更新的计划数据，可以包含schedule、status、end_date等字段
    
    Returns:
        str: JSON格式的操作结果
    """
    try:
        # 验证用户ID和计划ID
        if not user_id or not isinstance(user_id, str):
            raise ValueError("用户ID必须是非空字符串")
        
        if not schedule_id or not isinstance(schedule_id, str):
            raise ValueError("计划ID必须是非空字符串")
        
        # 验证更新数据
        if not isinstance(updates, dict):
            raise ValueError("更新数据必须是字典格式")
        
        # 构建计划文件路径
        schedule_file_path = os.path.join(TIME_DATA_DIR, f"{user_id}_schedules.json")
        
        # 检查文件是否存在
        if not os.path.exists(schedule_file_path):
            return json.dumps({
                "status": "error",
                "message": f"用户 {user_id} 的健身计划不存在",
                "timestamp": datetime.now().isoformat()
            }, ensure_ascii=False)
        
        # 读取健身计划
        with open(schedule_file_path, 'r', encoding='utf-8') as file:
            schedules = json.load(file)
        
        # 检查计划是否存在
        if schedule_id not in schedules:
            return json.dumps({
                "status": "error",
                "message": f"计划 {schedule_id} 不存在",
                "timestamp": datetime.now().isoformat()
            }, ensure_ascii=False)
        
        # 获取当前计划
        current_schedule = schedules[schedule_id]
        
        # 更新计划数据
        updated_fields = []
        
        if "schedule" in updates:
            # 验证计划数据格式
            days_of_week = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
            schedule_data = updates["schedule"]
            
            for day in days_of_week:
                if day in schedule_data:
                    if not isinstance(schedule_data[day], list):
                        raise ValueError(f"{day} 的计划必须是列表格式")
                    
                    for workout in schedule_data[day]:
                        if not isinstance(workout, dict):
                            raise ValueError(f"{day} 的锻炼项目必须是字典格式")
                        
                        # 验证锻炼项目必要字段
                        if "type" not in workout:
                            raise ValueError(f"{day} 的锻炼项目缺少 'type' 字段")
            
            current_schedule["schedule"] = schedule_data
            updated_fields.append("schedule")
        
        if "status" in updates:
            valid_statuses = ["active", "completed", "paused", "cancelled"]
            if updates["status"] not in valid_statuses:
                raise ValueError(f"状态无效，有效值: {', '.join(valid_statuses)}")
            
            current_schedule["status"] = updates["status"]
            updated_fields.append("status")
        
        if "end_date" in updates:
            if updates["end_date"]:
                try:
                    end_datetime = datetime.fromisoformat(updates["end_date"])
                    # 如果只提供了日期部分，添加时间部分
                    if len(updates["end_date"]) == 10:
                        end_datetime = datetime.combine(end_datetime.date(), datetime.max.time())
                    
                    # 验证结束日期是否晚于开始日期
                    start_datetime = datetime.fromisoformat(current_schedule["start_date"])
                    if end_datetime <= start_datetime:
                        raise ValueError("结束日期必须晚于开始日期")
                    
                    current_schedule["end_date"] = end_datetime.isoformat()
                except ValueError as e:
                    raise ValueError(f"结束日期格式无效: {str(e)}")
            else:
                # 设置为无限期
                current_schedule["end_date"] = None
            
            updated_fields.append("end_date")
        
        # 更新最后修改时间
        current_schedule["last_updated"] = datetime.now().isoformat()
        
        # 保存更新后的计划
        schedules[schedule_id] = current_schedule
        
        # 写入文件
        with open(schedule_file_path, 'w', encoding='utf-8') as file:
            json.dump(schedules, file, ensure_ascii=False, indent=2)
        
        return json.dumps({
            "status": "success",
            "message": "健身计划更新成功",
            "user_id": user_id,
            "schedule_id": schedule_id,
            "updated_fields": updated_fields,
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
            "message": f"更新健身计划时发生错误: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }, ensure_ascii=False)

@tool
def get_todays_workout(user_id: str, date: Optional[str] = None) -> str:
    """
    获取用户今天的锻炼计划
    
    Args:
        user_id: 用户唯一标识符
        date: 指定日期，ISO格式 (YYYY-MM-DD)，如果不提供则使用当前日期
    
    Returns:
        str: JSON格式的今日锻炼计划
    """
    try:
        # 验证用户ID
        if not user_id or not isinstance(user_id, str):
            raise ValueError("用户ID必须是非空字符串")
        
        # 处理日期
        if date:
            try:
                target_date = datetime.fromisoformat(date).date()
            except ValueError:
                raise ValueError("日期格式无效，请使用ISO格式 (YYYY-MM-DD)")
        else:
            target_date = datetime.now().date()
        
        # 获取星期几
        day_of_week = target_date.strftime("%A").lower()  # 英文星期几，小写
        
        # 构建计划文件路径
        schedule_file_path = os.path.join(TIME_DATA_DIR, f"{user_id}_schedules.json")
        
        # 检查文件是否存在
        if not os.path.exists(schedule_file_path):
            return json.dumps({
                "status": "error",
                "message": f"用户 {user_id} 的健身计划不存在",
                "timestamp": datetime.now().isoformat()
            }, ensure_ascii=False)
        
        # 读取健身计划
        with open(schedule_file_path, 'r', encoding='utf-8') as file:
            schedules = json.load(file)
        
        # 查找适用于目标日期的活跃计划
        applicable_schedules = []
        
        for schedule_id, schedule in schedules.items():
            # 检查计划状态
            if schedule.get("status") != "active":
                continue
            
            # 检查计划日期范围
            start_datetime = datetime.fromisoformat(schedule["start_date"]).date()
            
            if schedule["end_date"]:
                end_datetime = datetime.fromisoformat(schedule["end_date"]).date()
                if not (start_datetime <= target_date <= end_datetime):
                    continue
            else:
                # 无结束日期的计划
                if target_date < start_datetime:
                    continue
            
            # 检查计划是否包含目标日期的锻炼
            if day_of_week in schedule["schedule"]:
                applicable_schedules.append({
                    "schedule_id": schedule_id,
                    "workouts": schedule["schedule"][day_of_week]
                })
        
        if not applicable_schedules:
            return json.dumps({
                "status": "success",
                "message": f"在 {target_date.isoformat()} ({day_of_week}) 没有安排锻炼",
                "user_id": user_id,
                "date": target_date.isoformat(),
                "day_of_week": day_of_week,
                "has_workout": False,
                "timestamp": datetime.now().isoformat()
            }, ensure_ascii=False)
        
        # 合并所有适用计划的锻炼
        all_workouts = []
        for schedule in applicable_schedules:
            all_workouts.extend(schedule["workouts"])
        
        return json.dumps({
            "status": "success",
            "user_id": user_id,
            "date": target_date.isoformat(),
            "day_of_week": day_of_week,
            "has_workout": True,
            "workouts": all_workouts,
            "applicable_schedules": [s["schedule_id"] for s in applicable_schedules],
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
            "message": f"获取今日锻炼计划时发生错误: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }, ensure_ascii=False)

@tool
def get_weekly_workout_plan(
    user_id: str,
    start_date: Optional[str] = None,
    schedule_id: Optional[str] = None
) -> str:
    """
    获取用户一周的锻炼计划
    
    Args:
        user_id: 用户唯一标识符
        start_date: 周开始日期，ISO格式 (YYYY-MM-DD)，如果不提供则使用当前日期所在周的周一
        schedule_id: 计划唯一标识符，如果提供则只返回特定计划
    
    Returns:
        str: JSON格式的一周锻炼计划
    """
    try:
        # 验证用户ID
        if not user_id or not isinstance(user_id, str):
            raise ValueError("用户ID必须是非空字符串")
        
        # 处理开始日期
        if start_date:
            try:
                start_datetime = datetime.fromisoformat(start_date).date()
            except ValueError:
                raise ValueError("开始日期格式无效，请使用ISO格式 (YYYY-MM-DD)")
        else:
            # 默认使用当前日期所在周的周一
            today = datetime.now().date()
            start_datetime = today - timedelta(days=today.weekday())  # 周一是0，周日是6
        
        # 计算一周的日期
        week_dates = []
        for i in range(7):
            date = start_datetime + timedelta(days=i)
            week_dates.append({
                "date": date.isoformat(),
                "day_of_week": date.strftime("%A").lower(),
                "is_today": date == datetime.now().date()
            })
        
        # 构建计划文件路径
        schedule_file_path = os.path.join(TIME_DATA_DIR, f"{user_id}_schedules.json")
        
        # 检查文件是否存在
        if not os.path.exists(schedule_file_path):
            return json.dumps({
                "status": "error",
                "message": f"用户 {user_id} 的健身计划不存在",
                "timestamp": datetime.now().isoformat()
            }, ensure_ascii=False)
        
        # 读取健身计划
        with open(schedule_file_path, 'r', encoding='utf-8') as file:
            schedules = json.load(file)
        
        # 如果提供了特定计划ID
        if schedule_id:
            if schedule_id not in schedules:
                return json.dumps({
                    "status": "error",
                    "message": f"计划 {schedule_id} 不存在",
                    "timestamp": datetime.now().isoformat()
                }, ensure_ascii=False)
            
            schedule = schedules[schedule_id]
            
            # 检查计划状态
            if schedule.get("status") != "active":
                return json.dumps({
                    "status": "error",
                    "message": f"计划 {schedule_id} 不是活跃状态",
                    "timestamp": datetime.now().isoformat()
                }, ensure_ascii=False)
            
            # 检查计划日期范围
            start_date_schedule = datetime.fromisoformat(schedule["start_date"]).date()
            end_date_schedule = datetime.fromisoformat(schedule["end_date"]).date() if schedule["end_date"] else None
            
            # 构建一周计划
            week_plan = []
            for day_info in week_dates:
                day_date = datetime.fromisoformat(day_info["date"]).date()
                day_of_week = day_info["day_of_week"]
                
                # 检查日期是否在计划范围内
                is_in_range = True
                if day_date < start_date_schedule:
                    is_in_range = False
                if end_date_schedule and day_date > end_date_schedule:
                    is_in_range = False
                
                day_plan = {
                    "date": day_info["date"],
                    "day_of_week": day_of_week,
                    "is_today": day_info["is_today"],
                    "has_workout": False,
                    "workouts": [],
                    "is_in_schedule_range": is_in_range
                }
                
                if is_in_range and day_of_week in schedule["schedule"]:
                    day_plan["has_workout"] = True
                    day_plan["workouts"] = schedule["schedule"][day_of_week]
                
                week_plan.append(day_plan)
            
            return json.dumps({
                "status": "success",
                "user_id": user_id,
                "schedule_id": schedule_id,
                "week_start": start_datetime.isoformat(),
                "week_plan": week_plan,
                "timestamp": datetime.now().isoformat()
            }, ensure_ascii=False)
        
        # 如果没有提供特定计划ID，查找所有适用的活跃计划
        week_plan = []
        
        for day_info in week_dates:
            day_date = datetime.fromisoformat(day_info["date"]).date()
            day_of_week = day_info["day_of_week"]
            
            day_workouts = []
            applicable_schedules = []
            
            for sid, schedule in schedules.items():
                # 检查计划状态
                if schedule.get("status") != "active":
                    continue
                
                # 检查计划日期范围
                start_date_schedule = datetime.fromisoformat(schedule["start_date"]).date()
                end_date_schedule = datetime.fromisoformat(schedule["end_date"]).date() if schedule["end_date"] else None
                
                # 检查日期是否在计划范围内
                if day_date < start_date_schedule:
                    continue
                if end_date_schedule and day_date > end_date_schedule:
                    continue
                
                # 检查计划是否包含该日的锻炼
                if day_of_week in schedule["schedule"]:
                    day_workouts.extend(schedule["schedule"][day_of_week])
                    applicable_schedules.append(sid)
            
            day_plan = {
                "date": day_info["date"],
                "day_of_week": day_of_week,
                "is_today": day_info["is_today"],
                "has_workout": len(day_workouts) > 0,
                "workouts": day_workouts,
                "applicable_schedules": applicable_schedules
            }
            
            week_plan.append(day_plan)
        
        return json.dumps({
            "status": "success",
            "user_id": user_id,
            "week_start": start_datetime.isoformat(),
            "week_plan": week_plan,
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
            "message": f"获取周锻炼计划时发生错误: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }, ensure_ascii=False)

@tool
def record_workout_completion(
    user_id: str,
    workout_data: Dict[str, Any],
    completion_date: Optional[str] = None
) -> str:
    """
    记录用户完成的锻炼
    
    Args:
        user_id: 用户唯一标识符
        workout_data: 锻炼数据，包含锻炼类型、时长、强度等信息
        completion_date: 完成日期，ISO格式 (YYYY-MM-DD)，如果不提供则使用当前日期
    
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
        required_fields = ["type", "duration"]
        missing_fields = [field for field in required_fields if field not in workout_data]
        if missing_fields:
            raise ValueError(f"缺少必要的锻炼字段: {', '.join(missing_fields)}")
        
        # 处理完成日期
        if completion_date:
            try:
                completion_datetime = datetime.fromisoformat(completion_date)
                # 如果只提供了日期部分，添加时间部分
                if len(completion_date) == 10:
                    completion_datetime = datetime.combine(completion_datetime.date(), datetime.now().time())
            except ValueError:
                raise ValueError("完成日期格式无效，请使用ISO格式 (YYYY-MM-DD)")
        else:
            # 默认使用当前日期时间
            completion_datetime = datetime.now()
        
        # 构建完成记录文件路径
        completions_file_path = os.path.join(TIME_DATA_DIR, f"{user_id}_completions.json")
        
        # 读取现有完成记录或创建新的记录列表
        completions = []
        if os.path.exists(completions_file_path):
            try:
                with open(completions_file_path, 'r', encoding='utf-8') as file:
                    completions = json.load(file)
            except json.JSONDecodeError:
                completions = []
        
        # 生成记录ID
        completion_id = f"completion_{int(time.time())}"
        
        # 添加记录元数据
        workout_data["completion_id"] = completion_id
        workout_data["completion_date"] = completion_datetime.isoformat()
        workout_data["recorded_at"] = datetime.now().isoformat()
        
        # 添加星期几信息
        workout_data["day_of_week"] = completion_datetime.strftime("%A").lower()
        
        # 添加到完成记录列表
        completions.append(workout_data)
        
        # 写入文件
        with open(completions_file_path, 'w', encoding='utf-8') as file:
            json.dump(completions, file, ensure_ascii=False, indent=2)
        
        return json.dumps({
            "status": "success",
            "message": "锻炼完成记录保存成功",
            "user_id": user_id,
            "completion_id": completion_id,
            "completion_date": completion_datetime.isoformat(),
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
            "message": f"记录锻炼完成时发生错误: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }, ensure_ascii=False)

@tool
def get_workout_completions(
    user_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    workout_type: Optional[str] = None,
    limit: int = 10
) -> str:
    """
    获取用户完成的锻炼记录
    
    Args:
        user_id: 用户唯一标识符
        start_date: 开始日期，ISO格式 (YYYY-MM-DD)
        end_date: 结束日期，ISO格式 (YYYY-MM-DD)
        workout_type: 锻炼类型筛选
        limit: 返回记录的最大数量，默认为10
    
    Returns:
        str: JSON格式的锻炼完成记录
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
        
        # 构建完成记录文件路径
        completions_file_path = os.path.join(TIME_DATA_DIR, f"{user_id}_completions.json")
        
        # 检查文件是否存在
        if not os.path.exists(completions_file_path):
            return json.dumps({
                "status": "error",
                "message": f"用户 {user_id} 的锻炼完成记录不存在",
                "timestamp": datetime.now().isoformat()
            }, ensure_ascii=False)
        
        # 读取完成记录
        with open(completions_file_path, 'r', encoding='utf-8') as file:
            completions = json.load(file)
        
        # 应用筛选条件
        filtered_completions = completions
        
        # 按日期筛选
        if start_datetime or end_datetime:
            filtered_completions = []
            for completion in completions:
                completion_date = datetime.fromisoformat(completion["completion_date"])
                
                if start_datetime and completion_date < start_datetime:
                    continue
                
                if end_datetime and completion_date > end_datetime:
                    continue
                
                filtered_completions.append(completion)
        
        # 按锻炼类型筛选
        if workout_type:
            filtered_completions = [c for c in filtered_completions if c.get("type") == workout_type]
        
        # 按日期排序（最新的在前）
        filtered_completions.sort(key=lambda x: x["completion_date"], reverse=True)
        
        # 限制返回数量
        limited_completions = filtered_completions[:limit]
        
        # 计算统计数据
        total_duration = sum(c.get("duration", 0) for c in filtered_completions)
        workout_types = {}
        for completion in filtered_completions:
            workout_type = completion.get("type", "未指定")
            if workout_type in workout_types:
                workout_types[workout_type] += 1
            else:
                workout_types[workout_type] = 1
        
        # 计算每周锻炼频率
        if start_datetime and end_datetime:
            days_difference = (end_datetime.date() - start_datetime.date()).days
            weeks = max(1, days_difference / 7)
            weekly_frequency = len(filtered_completions) / weeks
        else:
            weekly_frequency = None
        
        return json.dumps({
            "status": "success",
            "user_id": user_id,
            "completions": limited_completions,
            "count": len(limited_completions),
            "total_count": len(filtered_completions),
            "statistics": {
                "total_duration": total_duration,
                "workout_types": workout_types,
                "weekly_frequency": round(weekly_frequency, 2) if weekly_frequency is not None else None
            },
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
            "message": f"用户 {user_id} 的锻炼完成记录文件格式无效",
            "timestamp": datetime.now().isoformat()
        }, ensure_ascii=False)
    
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"获取锻炼完成记录时发生错误: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }, ensure_ascii=False)

@tool
def set_workout_reminder(
    user_id: str,
    reminder_data: Dict[str, Any],
    reminder_id: Optional[str] = None
) -> str:
    """
    设置锻炼提醒
    
    Args:
        user_id: 用户唯一标识符
        reminder_data: 提醒数据，包含提醒时间、重复模式等信息
        reminder_id: 提醒唯一标识符，如果不提供则自动生成
    
    Returns:
        str: JSON格式的操作结果
    """
    try:
        # 验证用户ID
        if not user_id or not isinstance(user_id, str):
            raise ValueError("用户ID必须是非空字符串")
        
        # 验证提醒数据
        if not isinstance(reminder_data, dict):
            raise ValueError("提醒数据必须是字典格式")
        
        # 必要的字段验证
        required_fields = ["time", "days"]
        missing_fields = [field for field in required_fields if field not in reminder_data]
        if missing_fields:
            raise ValueError(f"缺少必要的提醒字段: {', '.join(missing_fields)}")
        
        # 验证时间格式
        try:
            reminder_time = datetime.strptime(reminder_data["time"], "%H:%M").time()
        except ValueError:
            raise ValueError("时间格式无效，请使用24小时制格式 (HH:MM)")
        
        # 验证重复日期
        days = reminder_data["days"]
        if not isinstance(days, list):
            raise ValueError("重复日期必须是列表格式")
        
        valid_days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        for day in days:
            if day not in valid_days:
                raise ValueError(f"无效的重复日期: {day}，有效值: {', '.join(valid_days)}")
        
        # 构建提醒文件路径
        reminders_file_path = os.path.join(TIME_DATA_DIR, f"{user_id}_reminders.json")
        
        # 读取现有提醒或创建新的提醒列表
        reminders = {}
        if os.path.exists(reminders_file_path):
            try:
                with open(reminders_file_path, 'r', encoding='utf-8') as file:
                    reminders = json.load(file)
            except json.JSONDecodeError:
                reminders = {}
        
        # 生成提醒ID（如果未提供）
        if not reminder_id:
            reminder_id = f"reminder_{int(time.time())}"
        
        # 添加提醒元数据
        reminder_data["id"] = reminder_id
        reminder_data["created_at"] = datetime.now().isoformat()
        reminder_data["last_updated"] = datetime.now().isoformat()
        reminder_data["status"] = "active"
        
        # 保存提醒
        reminders[reminder_id] = reminder_data
        
        # 写入文件
        with open(reminders_file_path, 'w', encoding='utf-8') as file:
            json.dump(reminders, file, ensure_ascii=False, indent=2)
        
        return json.dumps({
            "status": "success",
            "message": "锻炼提醒设置成功",
            "user_id": user_id,
            "reminder_id": reminder_id,
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
            "message": f"设置锻炼提醒时发生错误: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }, ensure_ascii=False)

@tool
def get_workout_reminders(
    user_id: str,
    reminder_id: Optional[str] = None,
    status: Optional[str] = "active",
    day: Optional[str] = None
) -> str:
    """
    获取锻炼提醒
    
    Args:
        user_id: 用户唯一标识符
        reminder_id: 提醒唯一标识符，如果提供则只返回特定提醒
        status: 筛选提醒状态，如"active"、"inactive"等，默认为"active"
        day: 筛选特定日期的提醒，如"monday"、"tuesday"等
    
    Returns:
        str: JSON格式的锻炼提醒数据
    """
    try:
        # 验证用户ID
        if not user_id or not isinstance(user_id, str):
            raise ValueError("用户ID必须是非空字符串")
        
        # 验证日期参数
        if day:
            valid_days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
            if day not in valid_days:
                raise ValueError(f"无效的日期: {day}，有效值: {', '.join(valid_days)}")
        
        # 构建提醒文件路径
        reminders_file_path = os.path.join(TIME_DATA_DIR, f"{user_id}_reminders.json")
        
        # 检查文件是否存在
        if not os.path.exists(reminders_file_path):
            return json.dumps({
                "status": "error",
                "message": f"用户 {user_id} 的锻炼提醒不存在",
                "timestamp": datetime.now().isoformat()
            }, ensure_ascii=False)
        
        # 读取锻炼提醒
        with open(reminders_file_path, 'r', encoding='utf-8') as file:
            reminders = json.load(file)
        
        # 如果提供了特定提醒ID
        if reminder_id:
            if reminder_id not in reminders:
                return json.dumps({
                    "status": "error",
                    "message": f"提醒 {reminder_id} 不存在",
                    "timestamp": datetime.now().isoformat()
                }, ensure_ascii=False)
            
            return json.dumps({
                "status": "success",
                "user_id": user_id,
                "reminder_id": reminder_id,
                "reminder": reminders[reminder_id],
                "timestamp": datetime.now().isoformat()
            }, ensure_ascii=False)
        
        # 筛选提醒
        filtered_reminders = {}
        for rid, reminder in reminders.items():
            # 检查状态
            if status and reminder.get("status") != status:
                continue
            
            # 检查特定日期
            if day and day not in reminder.get("days", []):
                continue
            
            # 添加到筛选结果
            filtered_reminders[rid] = reminder
        
        return json.dumps({
            "status": "success",
            "user_id": user_id,
            "reminders": filtered_reminders,
            "count": len(filtered_reminders),
            "filters": {
                "status": status,
                "day": day
            },
            "timestamp": datetime.now().isoformat()
        }, ensure_ascii=False)
    
    except json.JSONDecodeError:
        return json.dumps({
            "status": "error",
            "message": f"用户 {user_id} 的锻炼提醒文件格式无效",
            "timestamp": datetime.now().isoformat()
        }, ensure_ascii=False)
    
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"获取锻炼提醒时发生错误: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }, ensure_ascii=False)

@tool
def analyze_workout_adherence(
    user_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    schedule_id: Optional[str] = None
) -> str:
    """
    分析用户对锻炼计划的坚持情况
    
    Args:
        user_id: 用户唯一标识符
        start_date: 开始日期，ISO格式 (YYYY-MM-DD)，如果不提供则使用过去30天
        end_date: 结束日期，ISO格式 (YYYY-MM-DD)，如果不提供则使用当前日期
        schedule_id: 计划唯一标识符，如果提供则只分析特定计划
    
    Returns:
        str: JSON格式的坚持情况分析
    """
    try:
        # 验证用户ID
        if not user_id or not isinstance(user_id, str):
            raise ValueError("用户ID必须是非空字符串")
        
        # 处理日期范围
        end_datetime = datetime.now()
        if end_date:
            try:
                end_datetime = datetime.fromisoformat(end_date)
                if len(end_date) == 10:  # 只有日期部分 (YYYY-MM-DD)
                    end_datetime = datetime.combine(end_datetime.date(), datetime.max.time())
            except ValueError:
                raise ValueError("结束日期格式无效，请使用ISO格式 (YYYY-MM-DD)")
        
        start_datetime = end_datetime - timedelta(days=30)  # 默认分析过去30天
        if start_date:
            try:
                start_datetime = datetime.fromisoformat(start_date)
                if len(start_date) == 10:  # 只有日期部分 (YYYY-MM-DD)
                    start_datetime = datetime.combine(start_datetime.date(), datetime.min.time())
            except ValueError:
                raise ValueError("开始日期格式无效，请使用ISO格式 (YYYY-MM-DD)")
        
        # 检查日期范围
        if start_datetime >= end_datetime:
            raise ValueError("开始日期必须早于结束日期")
        
        # 获取计划数据
        schedule_file_path = os.path.join(TIME_DATA_DIR, f"{user_id}_schedules.json")
        if not os.path.exists(schedule_file_path):
            return json.dumps({
                "status": "error",
                "message": f"用户 {user_id} 的健身计划不存在",
                "timestamp": datetime.now().isoformat()
            }, ensure_ascii=False)
        
        with open(schedule_file_path, 'r', encoding='utf-8') as file:
            schedules = json.load(file)
        
        # 获取完成记录
        completions_file_path = os.path.join(TIME_DATA_DIR, f"{user_id}_completions.json")
        if not os.path.exists(completions_file_path):
            return json.dumps({
                "status": "error",
                "message": f"用户 {user_id} 的锻炼完成记录不存在",
                "timestamp": datetime.now().isoformat()
            }, ensure_ascii=False)
        
        with open(completions_file_path, 'r', encoding='utf-8') as file:
            completions = json.load(file)
        
        # 筛选时间范围内的完成记录
        filtered_completions = []
        for completion in completions:
            completion_date = datetime.fromisoformat(completion["completion_date"])
            if start_datetime <= completion_date <= end_datetime:
                filtered_completions.append(completion)
        
        # 按日期组织完成记录
        completions_by_date = {}
        for completion in filtered_completions:
            completion_date = datetime.fromisoformat(completion["completion_date"]).date().isoformat()
            if completion_date not in completions_by_date:
                completions_by_date[completion_date] = []
            completions_by_date[completion_date].append(completion)
        
        # 如果提供了特定计划ID
        if schedule_id:
            if schedule_id not in schedules:
                return json.dumps({
                    "status": "error",
                    "message": f"计划 {schedule_id} 不存在",
                    "timestamp": datetime.now().isoformat()
                }, ensure_ascii=False)
            
            schedule = schedules[schedule_id]
            
            # 分析特定计划的坚持情况
            return analyze_specific_schedule_adherence(
                user_id, schedule, schedule_id, start_datetime, end_datetime, completions_by_date
            )
        
        # 分析所有计划的总体坚持情况
        return analyze_overall_adherence(
            user_id, schedules, start_datetime, end_datetime, completions_by_date
        )
    
    except ValueError as e:
        return json.dumps({
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }, ensure_ascii=False)
    
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"分析锻炼坚持情况时发生错误: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }, ensure_ascii=False)

def analyze_specific_schedule_adherence(
    user_id: str,
    schedule: Dict[str, Any],
    schedule_id: str,
    start_datetime: datetime,
    end_datetime: datetime,
    completions_by_date: Dict[str, List[Dict[str, Any]]]
) -> str:
    """分析特定计划的坚持情况"""
    # 检查计划状态
    if schedule.get("status") != "active":
        return json.dumps({
            "status": "warning",
            "message": f"计划 {schedule_id} 不是活跃状态",
            "timestamp": datetime.now().isoformat()
        }, ensure_ascii=False)
    
    # 获取计划的日期范围
    schedule_start = datetime.fromisoformat(schedule["start_date"])
    schedule_end = datetime.fromisoformat(schedule["end_date"]) if schedule["end_date"] else datetime.max
    
    # 调整分析范围，确保在计划范围内
    analysis_start = max(start_datetime, schedule_start)
    analysis_end = min(end_datetime, schedule_end)
    
    if analysis_start >= analysis_end:
        return json.dumps({
            "status": "warning",
            "message": f"计划 {schedule_id} 与指定的分析时间范围没有重叠",
            "timestamp": datetime.now().isoformat()
        }, ensure_ascii=False)
    
    # 生成分析期间的所有日期
    analysis_dates = []
    current_date = analysis_start.date()
    while current_date <= analysis_end.date():
        analysis_dates.append(current_date)
        current_date += timedelta(days=1)
    
    # 计算每个日期应该进行的锻炼
    scheduled_workouts = {}
    completed_workouts = {}
    
    for date in analysis_dates:
        day_of_week = date.strftime("%A").lower()
        date_str = date.isoformat()
        
        # 检查该日期是否有计划的锻炼
        if day_of_week in schedule["schedule"]:
            scheduled_workouts[date_str] = schedule["schedule"][day_of_week]
        else:
            scheduled_workouts[date_str] = []
        
        # 检查该日期是否有完成的锻炼
        completed_workouts[date_str] = completions_by_date.get(date_str, [])
    
    # 计算坚持率
    total_scheduled_days = sum(1 for date, workouts in scheduled_workouts.items() if workouts)
    total_completed_days = sum(1 for date, workouts in completed_workouts.items() if workouts)
    
    # 计算有计划锻炼的日期中，实际完成锻炼的比例
    scheduled_days_with_completion = sum(
        1 for date, workouts in scheduled_workouts.items()
        if workouts and completed_workouts.get(date, [])
    )
    
    adherence_rate = (scheduled_days_with_completion / total_scheduled_days * 100) if total_scheduled_days > 0 else 0
    
    # 分析每周坚持情况
    weekly_adherence = analyze_weekly_adherence(analysis_dates, scheduled_workouts, completed_workouts)
    
    # 分析每种锻炼类型的坚持情况
    workout_type_adherence = analyze_workout_type_adherence(scheduled_workouts, completed_workouts)
    
    return json.dumps({
        "status": "success",
        "user_id": user_id,
        "schedule_id": schedule_id,
        "analysis_period": {
            "start_date": analysis_start.date().isoformat(),
            "end_date": analysis_end.date().isoformat(),
            "total_days": len(analysis_dates)
        },
        "adherence_summary": {
            "scheduled_workout_days": total_scheduled_days,
            "days_with_workouts_completed": total_completed_days,
            "scheduled_days_with_completion": scheduled_days_with_completion,
            "adherence_rate": round(adherence_rate, 2),
            "extra_workout_days": max(0, total_completed_days - scheduled_days_with_completion)
        },
        "weekly_adherence": weekly_adherence,
        "workout_type_adherence": workout_type_adherence,
        "timestamp": datetime.now().isoformat()
    }, ensure_ascii=False)

def analyze_overall_adherence(
    user_id: str,
    schedules: Dict[str, Dict[str, Any]],
    start_datetime: datetime,
    end_datetime: datetime,
    completions_by_date: Dict[str, List[Dict[str, Any]]]
) -> str:
    """分析所有计划的总体坚持情况"""
    # 筛选活跃的计划
    active_schedules = {
        sid: schedule for sid, schedule in schedules.items()
        if schedule.get("status") == "active"
    }
    
    if not active_schedules:
        return json.dumps({
            "status": "warning",
            "message": f"用户 {user_id} 没有活跃的健身计划",
            "timestamp": datetime.now().isoformat()
        }, ensure_ascii=False)
    
    # 生成分析期间的所有日期
    analysis_dates = []
    current_date = start_datetime.date()
    while current_date <= end_datetime.date():
        analysis_dates.append(current_date)
        current_date += timedelta(days=1)
    
    # 计算每个日期应该进行的锻炼（合并所有活跃计划）
    scheduled_workouts = {}
    completed_workouts = {}
    
    for date in analysis_dates:
        day_of_week = date.strftime("%A").lower()
        date_str = date.isoformat()
        
        # 初始化该日期的计划锻炼
        scheduled_workouts[date_str] = []
        
        # 检查每个活跃计划
        for schedule_id, schedule in active_schedules.items():
            # 检查日期是否在计划范围内
            schedule_start = datetime.fromisoformat(schedule["start_date"]).date()
            schedule_end = datetime.fromisoformat(schedule["end_date"]).date() if schedule["end_date"] else datetime.max.date()
            
            if schedule_start <= date <= schedule_end:
                # 检查该日期是否有计划的锻炼
                if day_of_week in schedule["schedule"]:
                    scheduled_workouts[date_str].extend(schedule["schedule"][day_of_week])
        
        # 检查该日期是否有完成的锻炼
        completed_workouts[date_str] = completions_by_date.get(date_str, [])
    
    # 计算坚持率
    total_scheduled_days = sum(1 for date, workouts in scheduled_workouts.items() if workouts)
    total_completed_days = sum(1 for date, workouts in completed_workouts.items() if workouts)
    
    # 计算有计划锻炼的日期中，实际完成锻炼的比例
    scheduled_days_with_completion = sum(
        1 for date, workouts in scheduled_workouts.items()
        if workouts and completed_workouts.get(date, [])
    )
    
    adherence_rate = (scheduled_days_with_completion / total_scheduled_days * 100) if total_scheduled_days > 0 else 0
    
    # 分析每周坚持情况
    weekly_adherence = analyze_weekly_adherence(analysis_dates, scheduled_workouts, completed_workouts)
    
    # 分析每种锻炼类型的坚持情况
    workout_type_adherence = analyze_workout_type_adherence(scheduled_workouts, completed_workouts)
    
    # 分析每个计划的坚持情况
    schedule_adherence = {}
    for schedule_id, schedule in active_schedules.items():
        # 获取计划的日期范围
        schedule_start = datetime.fromisoformat(schedule["start_date"]).date()
        schedule_end = datetime.fromisoformat(schedule["end_date"]).date() if schedule["end_date"] else datetime.max.date()
        
        # 调整分析范围，确保在计划范围内
        analysis_start = max(start_datetime.date(), schedule_start)
        analysis_end = min(end_datetime.date(), schedule_end)
        
        if analysis_start >= analysis_end:
            continue
        
        # 计算该计划在分析期间的坚持情况
        schedule_scheduled_days = 0
        schedule_completed_days = 0
        
        for date in analysis_dates:
            if analysis_start <= date <= analysis_end:
                day_of_week = date.strftime("%A").lower()
                date_str = date.isoformat()
                
                # 检查该日期是否有该计划的锻炼
                has_scheduled = day_of_week in schedule["schedule"] and schedule["schedule"][day_of_week]
                has_completed = date_str in completions_by_date and completions_by_date[date_str]
                
                if has_scheduled:
                    schedule_scheduled_days += 1
                    if has_completed:
                        schedule_completed_days += 1
        
        schedule_adherence_rate = (schedule_completed_days / schedule_scheduled_days * 100) if schedule_scheduled_days > 0 else 0
        
        schedule_adherence[schedule_id] = {
            "scheduled_days": schedule_scheduled_days,
            "completed_days": schedule_completed_days,
            "adherence_rate": round(schedule_adherence_rate, 2)
        }
    
    return json.dumps({
        "status": "success",
        "user_id": user_id,
        "analysis_period": {
            "start_date": start_datetime.date().isoformat(),
            "end_date": end_datetime.date().isoformat(),
            "total_days": len(analysis_dates)
        },
        "adherence_summary": {
            "scheduled_workout_days": total_scheduled_days,
            "days_with_workouts_completed": total_completed_days,
            "scheduled_days_with_completion": scheduled_days_with_completion,
            "adherence_rate": round(adherence_rate, 2),
            "extra_workout_days": max(0, total_completed_days - scheduled_days_with_completion)
        },
        "weekly_adherence": weekly_adherence,
        "workout_type_adherence": workout_type_adherence,
        "schedule_adherence": schedule_adherence,
        "timestamp": datetime.now().isoformat()
    }, ensure_ascii=False)

def analyze_weekly_adherence(
    analysis_dates: List[datetime.date],
    scheduled_workouts: Dict[str, List[Dict[str, Any]]],
    completed_workouts: Dict[str, List[Dict[str, Any]]]
) -> Dict[str, Any]:
    """分析每周坚持情况"""
    # 按周组织日期
    weeks = {}
    for date in analysis_dates:
        # 计算周数（以第一天为基准）
        week_number = (date - analysis_dates[0]).days // 7 + 1
        week_key = f"week_{week_number}"
        
        if week_key not in weeks:
            weeks[week_key] = []
        
        weeks[week_key].append(date)
    
    # 计算每周的坚持情况
    weekly_adherence = {}
    
    for week_key, dates in weeks.items():
        scheduled_days = 0
        completed_days = 0
        scheduled_with_completion = 0
        
        for date in dates:
            date_str = date.isoformat()
            has_scheduled = bool(scheduled_workouts.get(date_str, []))
            has_completed = bool(completed_workouts.get(date_str, []))
            
            if has_scheduled:
                scheduled_days += 1
                if has_completed:
                    scheduled_with_completion += 1
            
            if has_completed:
                completed_days += 1
        
        adherence_rate = (scheduled_with_completion / scheduled_days * 100) if scheduled_days > 0 else 0
        
        weekly_adherence[week_key] = {
            "start_date": dates[0].isoformat(),
            "end_date": dates[-1].isoformat(),
            "scheduled_days": scheduled_days,
            "completed_days": completed_days,
            "scheduled_with_completion": scheduled_with_completion,
            "adherence_rate": round(adherence_rate, 2)
        }
    
    return weekly_adherence

def analyze_workout_type_adherence(
    scheduled_workouts: Dict[str, List[Dict[str, Any]]],
    completed_workouts: Dict[str, List[Dict[str, Any]]]
) -> Dict[str, Any]:
    """分析每种锻炼类型的坚持情况"""
    # 统计计划的锻炼类型
    scheduled_types = {}
    for date, workouts in scheduled_workouts.items():
        for workout in workouts:
            workout_type = workout.get("type", "未指定")
            if workout_type not in scheduled_types:
                scheduled_types[workout_type] = 0
            scheduled_types[workout_type] += 1
    
    # 统计完成的锻炼类型
    completed_types = {}
    for date, workouts in completed_workouts.items():
        for workout in workouts:
            workout_type = workout.get("type", "未指定")
            if workout_type not in completed_types:
                completed_types[workout_type] = 0
            completed_types[workout_type] += 1
    
    # 计算每种类型的坚持率
    type_adherence = {}
    
    for workout_type, scheduled_count in scheduled_types.items():
        completed_count = completed_types.get(workout_type, 0)
        adherence_rate = (completed_count / scheduled_count * 100) if scheduled_count > 0 else 0
        
        type_adherence[workout_type] = {
            "scheduled_count": scheduled_count,
            "completed_count": completed_count,
            "adherence_rate": round(adherence_rate, 2)
        }
    
    # 添加额外完成的锻炼类型（计划外）
    for workout_type, completed_count in completed_types.items():
        if workout_type not in type_adherence:
            type_adherence[workout_type] = {
                "scheduled_count": 0,
                "completed_count": completed_count,
                "adherence_rate": None,  # 没有计划，无法计算坚持率
                "is_extra": True  # 标记为计划外锻炼
            }
    
    return type_adherence