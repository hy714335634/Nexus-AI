"""
健康指标计算工具 - 用于计算BMI、基础代谢率、每日能量需求等健康指标
"""

import json
import math
from datetime import datetime
from typing import Dict, Any, Optional, Literal, Union, Tuple
from strands import tool

@tool
def calculate_bmi(height: float, weight: float) -> str:
    """
    计算身体质量指数(BMI)
    
    Args:
        height: 身高(米)
        weight: 体重(公斤)
    
    Returns:
        str: JSON格式的BMI计算结果，包含BMI值和体重状态分类
    """
    try:
        # 验证输入
        if height <= 0 or weight <= 0:
            raise ValueError("身高和体重必须为正数")
        
        # 计算BMI
        bmi = weight / (height * height)
        
        # 确定BMI分类
        category = ""
        if bmi < 18.5:
            category = "体重过轻"
        elif 18.5 <= bmi < 24:
            category = "正常体重"
        elif 24 <= bmi < 28:
            category = "超重"
        elif 28 <= bmi < 30:
            category = "轻度肥胖"
        elif 30 <= bmi < 40:
            category = "中度肥胖"
        else:
            category = "重度肥胖"
        
        result = {
            "status": "success",
            "bmi": round(bmi, 2),
            "category": category,
            "reference": "参考标准：中国成人BMI分类标准",
            "timestamp": datetime.now().isoformat()
        }
        
        return json.dumps(result, ensure_ascii=False)
    
    except ValueError as e:
        error_result = {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }
        return json.dumps(error_result, ensure_ascii=False)
    
    except Exception as e:
        error_result = {
            "status": "error",
            "message": f"计算BMI时发生错误: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }
        return json.dumps(error_result, ensure_ascii=False)

@tool
def calculate_bmr(
    weight: float, 
    height: float, 
    age: int, 
    gender: Literal["male", "female"],
    formula: Literal["mifflin_st_jeor", "harris_benedict", "katch_mcardle"] = "mifflin_st_jeor",
    body_fat_percentage: Optional[float] = None
) -> str:
    """
    计算基础代谢率(BMR)
    
    Args:
        weight: 体重(公斤)
        height: 身高(厘米)
        age: 年龄(岁)
        gender: 性别，"male"表示男性，"female"表示女性
        formula: 计算公式，可选"mifflin_st_jeor"(默认)、"harris_benedict"或"katch_mcardle"
        body_fat_percentage: 体脂率(%)，仅在使用Katch-McArdle公式时需要
    
    Returns:
        str: JSON格式的BMR计算结果，包含基础代谢率(卡路里/天)
    """
    try:
        # 验证输入
        if weight <= 0 or height <= 0 or age < 0:
            raise ValueError("体重、身高必须为正数，年龄必须为非负数")
        
        if formula == "katch_mcardle" and body_fat_percentage is None:
            raise ValueError("使用Katch-McArdle公式时必须提供体脂率")
        
        if body_fat_percentage is not None and (body_fat_percentage < 0 or body_fat_percentage > 100):
            raise ValueError("体脂率必须在0-100之间")
        
        # 计算BMR
        bmr = 0
        
        if formula == "mifflin_st_jeor":
            # Mifflin-St Jeor公式
            if gender == "male":
                bmr = (10 * weight) + (6.25 * height) - (5 * age) + 5
            else:  # female
                bmr = (10 * weight) + (6.25 * height) - (5 * age) - 161
                
        elif formula == "harris_benedict":
            # Harris-Benedict公式
            if gender == "male":
                bmr = 88.362 + (13.397 * weight) + (4.799 * height) - (5.677 * age)
            else:  # female
                bmr = 447.593 + (9.247 * weight) + (3.098 * height) - (4.330 * age)
                
        elif formula == "katch_mcardle":
            # Katch-McArdle公式
            lean_body_mass = weight * (1 - (body_fat_percentage / 100))
            bmr = 370 + (21.6 * lean_body_mass)
        
        result = {
            "status": "success",
            "bmr": round(bmr),  # 四舍五入到整数
            "unit": "卡路里/天",
            "formula": formula,
            "timestamp": datetime.now().isoformat()
        }
        
        return json.dumps(result, ensure_ascii=False)
    
    except ValueError as e:
        error_result = {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }
        return json.dumps(error_result, ensure_ascii=False)
    
    except Exception as e:
        error_result = {
            "status": "error",
            "message": f"计算BMR时发生错误: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }
        return json.dumps(error_result, ensure_ascii=False)

@tool
def calculate_tdee(
    bmr: float,
    activity_level: Literal["sedentary", "light", "moderate", "active", "very_active"],
    goal: Optional[Literal["maintain", "lose", "gain"]] = "maintain",
    rate: Optional[float] = 0
) -> str:
    """
    计算每日总能量消耗(TDEE)和根据目标调整的卡路里摄入建议
    
    Args:
        bmr: 基础代谢率(卡路里/天)
        activity_level: 活动水平
            - sedentary: 久坐不动 (几乎不运动)
            - light: 轻度活动 (每周轻度运动1-3天)
            - moderate: 中度活动 (每周中等强度运动3-5天)
            - active: 积极活动 (每周剧烈运动6-7天)
            - very_active: 非常活跃 (每天剧烈运动或体力劳动工作)
        goal: 健身目标，可选"maintain"(维持)、"lose"(减脂)或"gain"(增肌)
        rate: 对于减脂，表示每周期望减少的体重(公斤)；对于增肌，表示每周期望增加的体重(公斤)
    
    Returns:
        str: JSON格式的TDEE计算结果，包含每日总能量消耗和根据目标调整的卡路里摄入建议
    """
    try:
        # 验证输入
        if bmr <= 0:
            raise ValueError("基础代谢率必须为正数")
        
        if goal in ["lose", "gain"] and rate <= 0:
            raise ValueError("减脂或增肌的速率必须为正数")
        
        # 活动系数
        activity_multipliers = {
            "sedentary": 1.2,      # 久坐不动
            "light": 1.375,        # 轻度活动
            "moderate": 1.55,      # 中度活动
            "active": 1.725,       # 积极活动
            "very_active": 1.9     # 非常活跃
        }
        
        # 计算TDEE
        tdee = bmr * activity_multipliers[activity_level]
        
        # 根据目标调整卡路里
        adjusted_calories = tdee
        calorie_adjustment = 0
        
        if goal == "lose":
            # 每减少0.5公斤体重需要减少约3500卡路里
            calorie_adjustment = -1 * (rate * 7700) / 7  # 每天的卡路里赤字
            adjusted_calories = max(1200, tdee + calorie_adjustment)  # 确保每日摄入不低于1200卡路里
            
        elif goal == "gain":
            # 每增加0.5公斤体重需要增加约3500卡路里
            calorie_adjustment = (rate * 7700) / 7  # 每天的卡路里盈余
            adjusted_calories = tdee + calorie_adjustment
        
        # 准备宏量营养素建议
        macros = {}
        if goal == "maintain":
            macros = {
                "蛋白质": {"克": round(tdee * 0.3 / 4), "卡路里": round(tdee * 0.3), "比例": "30%"},
                "碳水化合物": {"克": round(tdee * 0.4 / 4), "卡路里": round(tdee * 0.4), "比例": "40%"},
                "脂肪": {"克": round(tdee * 0.3 / 9), "卡路里": round(tdee * 0.3), "比例": "30%"}
            }
        elif goal == "lose":
            macros = {
                "蛋白质": {"克": round(adjusted_calories * 0.35 / 4), "卡路里": round(adjusted_calories * 0.35), "比例": "35%"},
                "碳水化合物": {"克": round(adjusted_calories * 0.4 / 4), "卡路里": round(adjusted_calories * 0.4), "比例": "40%"},
                "脂肪": {"克": round(adjusted_calories * 0.25 / 9), "卡路里": round(adjusted_calories * 0.25), "比例": "25%"}
            }
        elif goal == "gain":
            macros = {
                "蛋白质": {"克": round(adjusted_calories * 0.25 / 4), "卡路里": round(adjusted_calories * 0.25), "比例": "25%"},
                "碳水化合物": {"克": round(adjusted_calories * 0.5 / 4), "卡路里": round(adjusted_calories * 0.5), "比例": "50%"},
                "脂肪": {"克": round(adjusted_calories * 0.25 / 9), "卡路里": round(adjusted_calories * 0.25), "比例": "25%"}
            }
        
        result = {
            "status": "success",
            "tdee": round(tdee),
            "activity_level": activity_level,
            "goal": goal,
            "calorie_adjustment": round(calorie_adjustment) if goal != "maintain" else 0,
            "adjusted_calories": round(adjusted_calories),
            "macronutrient_recommendation": macros,
            "unit": "卡路里/天",
            "timestamp": datetime.now().isoformat()
        }
        
        return json.dumps(result, ensure_ascii=False)
    
    except ValueError as e:
        error_result = {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }
        return json.dumps(error_result, ensure_ascii=False)
    
    except Exception as e:
        error_result = {
            "status": "error",
            "message": f"计算TDEE时发生错误: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }
        return json.dumps(error_result, ensure_ascii=False)

@tool
def calculate_body_fat(
    method: Literal["navy", "jackson_pollock_3", "jackson_pollock_7", "deurenberg"],
    gender: Literal["male", "female"],
    weight: float,
    height: float,
    age: Optional[int] = None,
    waist: Optional[float] = None,
    neck: Optional[float] = None,
    hip: Optional[float] = None,
    chest: Optional[float] = None,
    abdomen: Optional[float] = None,
    thigh: Optional[float] = None,
    tricep: Optional[float] = None,
    subscapular: Optional[float] = None,
    suprailiac: Optional[float] = None,
    midaxillary: Optional[float] = None
) -> str:
    """
    计算体脂率
    
    Args:
        method: 计算方法
            - navy: 海军法（需要腰围、颈围，女性还需要臀围）
            - jackson_pollock_3: Jackson-Pollock 3点法（需要胸部/三头肌、腹部、大腿皮褶厚度）
            - jackson_pollock_7: Jackson-Pollock 7点法（需要胸部、腹部、大腿、三头肌、肩胛下、髂上、腋中线皮褶厚度）
            - deurenberg: Deurenberg公式（需要BMI和年龄）
        gender: 性别，"male"表示男性，"female"表示女性
        weight: 体重(公斤)
        height: 身高(厘米)，用于Navy法和Deurenberg公式
        age: 年龄(岁)，用于Deurenberg公式
        waist: 腰围(厘米)，用于Navy法
        neck: 颈围(厘米)，用于Navy法
        hip: 臀围(厘米)，女性使用Navy法时需要
        chest: 胸部皮褶厚度(毫米)，用于Jackson-Pollock方法
        abdomen: 腹部皮褶厚度(毫米)，用于Jackson-Pollock方法
        thigh: 大腿皮褶厚度(毫米)，用于Jackson-Pollock方法
        tricep: 三头肌皮褶厚度(毫米)，用于Jackson-Pollock方法（女性3点法需要）
        subscapular: 肩胛下皮褶厚度(毫米)，用于Jackson-Pollock 7点法
        suprailiac: 髂上皮褶厚度(毫米)，用于Jackson-Pollock 7点法
        midaxillary: 腋中线皮褶厚度(毫米)，用于Jackson-Pollock 7点法
    
    Returns:
        str: JSON格式的体脂率计算结果
    """
    try:
        # 验证基本输入
        if weight <= 0 or height <= 0:
            raise ValueError("体重和身高必须为正数")
        
        body_fat_percentage = 0
        density = 0
        
        # 根据不同方法计算体脂率
        if method == "navy":
            # 验证Navy法所需参数
            if waist is None or neck is None:
                raise ValueError("Navy法需要提供腰围和颈围")
            if gender == "female" and hip is None:
                raise ValueError("女性使用Navy法需要提供臀围")
            
            # 计算体密度和体脂率
            if gender == "male":
                density = 1.0324 - (0.19077 * math.log10(waist - neck)) + (0.15456 * math.log10(height))
                body_fat_percentage = (495 / density) - 450
            else:  # female
                density = 1.29579 - (0.35004 * math.log10(waist + hip - neck)) + (0.22100 * math.log10(height))
                body_fat_percentage = (495 / density) - 450
                
        elif method == "jackson_pollock_3":
            # 验证Jackson-Pollock 3点法所需参数
            if gender == "male" and (chest is None or abdomen is None or thigh is None):
                raise ValueError("男性使用Jackson-Pollock 3点法需要提供胸部、腹部和大腿皮褶厚度")
            if gender == "female" and (tricep is None or abdomen is None or thigh is None):
                raise ValueError("女性使用Jackson-Pollock 3点法需要提供三头肌、腹部和大腿皮褶厚度")
            
            # 计算体密度和体脂率
            if gender == "male":
                sum_skinfolds = chest + abdomen + thigh
                density = 1.10938 - (0.0008267 * sum_skinfolds) + (0.0000016 * sum_skinfolds**2) - (0.0002574 * age)
            else:  # female
                sum_skinfolds = tricep + abdomen + thigh
                density = 1.0994921 - (0.0009929 * sum_skinfolds) + (0.0000023 * sum_skinfolds**2) - (0.0001392 * age)
            
            body_fat_percentage = (495 / density) - 450
                
        elif method == "jackson_pollock_7":
            # 验证Jackson-Pollock 7点法所需参数
            required_params = [chest, abdomen, thigh, tricep, subscapular, suprailiac, midaxillary]
            if any(param is None for param in required_params):
                raise ValueError("Jackson-Pollock 7点法需要提供所有7个皮褶厚度测量值")
            
            # 计算体密度和体脂率
            sum_skinfolds = chest + abdomen + thigh + tricep + subscapular + suprailiac + midaxillary
            
            if gender == "male":
                density = 1.112 - (0.00043499 * sum_skinfolds) + (0.00000055 * sum_skinfolds**2) - (0.00028826 * age)
            else:  # female
                density = 1.097 - (0.00046971 * sum_skinfolds) + (0.00000056 * sum_skinfolds**2) - (0.00012828 * age)
            
            body_fat_percentage = (495 / density) - 450
                
        elif method == "deurenberg":
            # 验证Deurenberg公式所需参数
            if age is None:
                raise ValueError("Deurenberg公式需要提供年龄")
            
            # 计算BMI和体脂率
            bmi = weight / ((height / 100) ** 2)
            
            if gender == "male":
                body_fat_percentage = (1.2 * bmi) + (0.23 * age) - 16.2
            else:  # female
                body_fat_percentage = (1.2 * bmi) + (0.23 * age) - 5.4
        
        # 确定体脂率分类
        category = ""
        if gender == "male":
            if body_fat_percentage < 6:
                category = "必需脂肪"
            elif 6 <= body_fat_percentage < 14:
                category = "运动员水平"
            elif 14 <= body_fat_percentage < 18:
                category = "健身水平"
            elif 18 <= body_fat_percentage < 25:
                category = "可接受水平"
            else:
                category = "肥胖"
        else:  # female
            if body_fat_percentage < 16:
                category = "必需脂肪"
            elif 16 <= body_fat_percentage < 24:
                category = "运动员水平"
            elif 24 <= body_fat_percentage < 30:
                category = "健身水平"
            elif 30 <= body_fat_percentage < 32:
                category = "可接受水平"
            else:
                category = "肥胖"
        
        result = {
            "status": "success",
            "body_fat_percentage": round(body_fat_percentage, 2),
            "category": category,
            "method": method,
            "gender": gender,
            "timestamp": datetime.now().isoformat()
        }
        
        return json.dumps(result, ensure_ascii=False)
    
    except ValueError as e:
        error_result = {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }
        return json.dumps(error_result, ensure_ascii=False)
    
    except Exception as e:
        error_result = {
            "status": "error",
            "message": f"计算体脂率时发生错误: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }
        return json.dumps(error_result, ensure_ascii=False)

@tool
def calculate_ideal_weight(
    height: float,
    gender: Literal["male", "female"],
    method: Literal["devine", "robinson", "miller", "hamwi", "bmi_based"] = "bmi_based",
    frame_size: Optional[Literal["small", "medium", "large"]] = "medium",
    target_bmi: Optional[float] = 22
) -> str:
    """
    计算理想体重
    
    Args:
        height: 身高(厘米)
        gender: 性别，"male"表示男性，"female"表示女性
        method: 计算方法
            - devine: Devine公式
            - robinson: Robinson公式
            - miller: Miller公式
            - hamwi: Hamwi公式
            - bmi_based: 基于BMI的计算(默认)
        frame_size: 体型大小，"small"(小)、"medium"(中)或"large"(大)，用于调整某些公式
        target_bmi: 目标BMI值，用于bmi_based方法，默认为22(健康范围中间值)
    
    Returns:
        str: JSON格式的理想体重计算结果
    """
    try:
        # 验证输入
        if height <= 0:
            raise ValueError("身高必须为正数")
        
        if method == "bmi_based" and (target_bmi < 18.5 or target_bmi > 24):
            raise ValueError("目标BMI应在健康范围内(18.5-24)")
        
        # 将身高转换为英寸(用于部分公式)
        height_in_inches = height / 2.54
        # 将身高转换为米(用于BMI公式)
        height_in_meters = height / 100
        
        ideal_weight = 0
        
        # 根据不同方法计算理想体重
        if method == "devine":
            if gender == "male":
                ideal_weight = 50 + 2.3 * (height_in_inches - 60)
            else:  # female
                ideal_weight = 45.5 + 2.3 * (height_in_inches - 60)
                
        elif method == "robinson":
            if gender == "male":
                ideal_weight = 52 + 1.9 * (height_in_inches - 60)
            else:  # female
                ideal_weight = 49 + 1.7 * (height_in_inches - 60)
                
        elif method == "miller":
            if gender == "male":
                ideal_weight = 56.2 + 1.41 * (height_in_inches - 60)
            else:  # female
                ideal_weight = 53.1 + 1.36 * (height_in_inches - 60)
                
        elif method == "hamwi":
            if gender == "male":
                ideal_weight = 48 + 2.7 * (height_in_inches - 60)
            else:  # female
                ideal_weight = 45.5 + 2.2 * (height_in_inches - 60)
                
        elif method == "bmi_based":
            ideal_weight = target_bmi * (height_in_meters ** 2)
        
        # 根据体型大小调整理想体重(除了BMI方法)
        if method != "bmi_based":
            if frame_size == "small":
                ideal_weight *= 0.9  # 小体型减少10%
            elif frame_size == "large":
                ideal_weight *= 1.1  # 大体型增加10%
        
        # 计算健康体重范围(基于BMI 18.5-24)
        min_healthy_weight = 18.5 * (height_in_meters ** 2)
        max_healthy_weight = 24 * (height_in_meters ** 2)
        
        result = {
            "status": "success",
            "ideal_weight": round(ideal_weight, 1),
            "healthy_weight_range": {
                "min": round(min_healthy_weight, 1),
                "max": round(max_healthy_weight, 1)
            },
            "method": method,
            "gender": gender,
            "unit": "公斤",
            "timestamp": datetime.now().isoformat()
        }
        
        return json.dumps(result, ensure_ascii=False)
    
    except ValueError as e:
        error_result = {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }
        return json.dumps(error_result, ensure_ascii=False)
    
    except Exception as e:
        error_result = {
            "status": "error",
            "message": f"计算理想体重时发生错误: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }
        return json.dumps(error_result, ensure_ascii=False)

@tool
def calculate_macronutrients(
    calories: float,
    goal: Literal["weight_loss", "maintenance", "muscle_gain"],
    protein_ratio: Optional[float] = None,
    carb_ratio: Optional[float] = None,
    fat_ratio: Optional[float] = None,
    body_weight: Optional[float] = None,
    preset: Optional[Literal["balanced", "low_carb", "high_protein", "ketogenic", "custom"]] = "balanced"
) -> str:
    """
    计算每日宏量营养素需求
    
    Args:
        calories: 每日卡路里目标
        goal: 健身目标，"weight_loss"(减脂)、"maintenance"(维持)或"muscle_gain"(增肌)
        protein_ratio: 蛋白质占总卡路里的比例(0-1之间)，如果提供则覆盖预设值
        carb_ratio: 碳水化合物占总卡路里的比例(0-1之间)，如果提供则覆盖预设值
        fat_ratio: 脂肪占总卡路里的比例(0-1之间)，如果提供则覆盖预设值
        body_weight: 体重(公斤)，用于基于体重的蛋白质计算
        preset: 宏量营养素比例预设，如果选择"custom"则必须提供自定义比例
    
    Returns:
        str: JSON格式的宏量营养素计算结果
    """
    try:
        # 验证输入
        if calories <= 0:
            raise ValueError("卡路里必须为正数")
        
        # 如果选择custom预设但未提供自定义比例
        if preset == "custom" and (protein_ratio is None or carb_ratio is None or fat_ratio is None):
            raise ValueError("选择自定义(custom)预设时必须提供蛋白质、碳水化合物和脂肪比例")
        
        # 如果提供了自定义比例，验证其和是否接近1
        if protein_ratio is not None and carb_ratio is not None and fat_ratio is not None:
            total_ratio = protein_ratio + carb_ratio + fat_ratio
            if abs(total_ratio - 1) > 0.01:  # 允许1%的误差
                raise ValueError(f"宏量营养素比例之和必须为1，当前为{total_ratio}")
        
        # 根据预设和目标设置默认宏量营养素比例
        if protein_ratio is None or carb_ratio is None or fat_ratio is None:
            if preset == "balanced":
                if goal == "weight_loss":
                    protein_ratio = 0.35
                    carb_ratio = 0.4
                    fat_ratio = 0.25
                elif goal == "maintenance":
                    protein_ratio = 0.3
                    carb_ratio = 0.45
                    fat_ratio = 0.25
                else:  # muscle_gain
                    protein_ratio = 0.3
                    carb_ratio = 0.5
                    fat_ratio = 0.2
            
            elif preset == "low_carb":
                if goal == "weight_loss":
                    protein_ratio = 0.4
                    carb_ratio = 0.2
                    fat_ratio = 0.4
                elif goal == "maintenance":
                    protein_ratio = 0.35
                    carb_ratio = 0.25
                    fat_ratio = 0.4
                else:  # muscle_gain
                    protein_ratio = 0.35
                    carb_ratio = 0.3
                    fat_ratio = 0.35
            
            elif preset == "high_protein":
                if goal == "weight_loss":
                    protein_ratio = 0.45
                    carb_ratio = 0.3
                    fat_ratio = 0.25
                elif goal == "maintenance":
                    protein_ratio = 0.4
                    carb_ratio = 0.35
                    fat_ratio = 0.25
                else:  # muscle_gain
                    protein_ratio = 0.4
                    carb_ratio = 0.4
                    fat_ratio = 0.2
            
            elif preset == "ketogenic":
                protein_ratio = 0.25
                carb_ratio = 0.05
                fat_ratio = 0.7
        
        # 计算各宏量营养素的卡路里和克数
        protein_calories = calories * protein_ratio
        carb_calories = calories * carb_ratio
        fat_calories = calories * fat_ratio
        
        # 蛋白质: 1克 = 4卡路里
        # 碳水化合物: 1克 = 4卡路里
        # 脂肪: 1克 = 9卡路里
        protein_grams = protein_calories / 4
        carb_grams = carb_calories / 4
        fat_grams = fat_calories / 9
        
        # 如果提供了体重，计算每公斤体重的蛋白质摄入量
        protein_per_kg = None
        if body_weight is not None and body_weight > 0:
            protein_per_kg = protein_grams / body_weight
        
        result = {
            "status": "success",
            "total_calories": round(calories),
            "macronutrients": {
                "protein": {
                    "grams": round(protein_grams),
                    "calories": round(protein_calories),
                    "percentage": round(protein_ratio * 100)
                },
                "carbohydrates": {
                    "grams": round(carb_grams),
                    "calories": round(carb_calories),
                    "percentage": round(carb_ratio * 100)
                },
                "fat": {
                    "grams": round(fat_grams),
                    "calories": round(fat_calories),
                    "percentage": round(fat_ratio * 100)
                }
            },
            "goal": goal,
            "preset": preset
        }
        
        # 如果提供了体重，添加每公斤蛋白质摄入量
        if protein_per_kg is not None:
            result["protein_per_kg"] = round(protein_per_kg, 2)
        
        return json.dumps(result, ensure_ascii=False)
    
    except ValueError as e:
        error_result = {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }
        return json.dumps(error_result, ensure_ascii=False)
    
    except Exception as e:
        error_result = {
            "status": "error",
            "message": f"计算宏量营养素时发生错误: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }
        return json.dumps(error_result, ensure_ascii=False)

@tool
def calculate_one_rep_max(
    weight: float,
    reps: int,
    formula: Literal["brzycki", "epley", "lander", "lombardi", "mayhew", "oconner", "wathan"] = "brzycki"
) -> str:
    """
    计算一次性最大重量(1RM)
    
    Args:
        weight: 已完成的重量(公斤)
        reps: 已完成的重复次数
        formula: 计算公式
            - brzycki: Brzycki公式(默认)
            - epley: Epley公式
            - lander: Lander公式
            - lombardi: Lombardi公式
            - mayhew: Mayhew公式
            - oconner: O'Conner公式
            - wathan: Wathan公式
    
    Returns:
        str: JSON格式的1RM计算结果
    """
    try:
        # 验证输入
        if weight <= 0:
            raise ValueError("重量必须为正数")
        
        if reps <= 0:
            raise ValueError("重复次数必须为正整数")
        
        if reps == 1:
            # 如果重复次数为1，则一次性最大重量就是输入的重量
            one_rep_max = weight
            formula_used = "直接返回(重复次数为1)"
        else:
            # 根据不同公式计算一次性最大重量
            if formula == "brzycki":
                one_rep_max = weight / (1.0278 - 0.0278 * reps)
                formula_used = "Brzycki: weight / (1.0278 - 0.0278 * reps)"
                
            elif formula == "epley":
                one_rep_max = weight * (1 + 0.0333 * reps)
                formula_used = "Epley: weight * (1 + 0.0333 * reps)"
                
            elif formula == "lander":
                one_rep_max = weight / (1.013 - 0.0267123 * reps)
                formula_used = "Lander: weight / (1.013 - 0.0267123 * reps)"
                
            elif formula == "lombardi":
                one_rep_max = weight * (reps ** 0.1)
                formula_used = "Lombardi: weight * (reps ^ 0.1)"
                
            elif formula == "mayhew":
                one_rep_max = weight / (0.522 + 0.419 * math.exp(-0.055 * reps))
                formula_used = "Mayhew: weight / (0.522 + 0.419 * exp(-0.055 * reps))"
                
            elif formula == "oconner":
                one_rep_max = weight * (1 + 0.025 * reps)
                formula_used = "O'Conner: weight * (1 + 0.025 * reps)"
                
            elif formula == "wathan":
                one_rep_max = weight / (0.488 + 0.538 * math.exp(-0.075 * reps))
                formula_used = "Wathan: weight / (0.488 + 0.538 * exp(-0.075 * reps))"
        
        # 计算各种重复次数下的训练重量
        training_weights = {}
        percentages = [0.65, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95]
        
        for percentage in percentages:
            training_weights[f"{int(percentage * 100)}%"] = round(one_rep_max * percentage, 1)
        
        result = {
            "status": "success",
            "one_rep_max": round(one_rep_max, 1),
            "input": {
                "weight": weight,
                "reps": reps
            },
            "formula": formula,
            "formula_used": formula_used,
            "training_weights": training_weights,
            "unit": "公斤",
            "timestamp": datetime.now().isoformat()
        }
        
        return json.dumps(result, ensure_ascii=False)
    
    except ValueError as e:
        error_result = {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }
        return json.dumps(error_result, ensure_ascii=False)
    
    except Exception as e:
        error_result = {
            "status": "error",
            "message": f"计算一次性最大重量时发生错误: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }
        return json.dumps(error_result, ensure_ascii=False)

@tool
def calculate_exercise_calories(
    weight: float,
    activity: str,
    duration: int,
    intensity: Optional[Literal["low", "moderate", "high"]] = "moderate",
    gender: Optional[Literal["male", "female"]] = None,
    age: Optional[int] = None,
    heart_rate: Optional[int] = None
) -> str:
    """
    计算运动消耗的卡路里
    
    Args:
        weight: 体重(公斤)
        activity: 运动类型(如跑步、游泳、骑车等)
        duration: 运动时长(分钟)
        intensity: 运动强度，"low"(低)、"moderate"(中)或"high"(高)
        gender: 性别，"male"表示男性，"female"表示女性，用于更精确的计算
        age: 年龄(岁)，用于更精确的计算
        heart_rate: 运动时的平均心率(次/分钟)，用于基于心率的计算
    
    Returns:
        str: JSON格式的卡路里消耗计算结果
    """
    try:
        # 验证输入
        if weight <= 0:
            raise ValueError("体重必须为正数")
        
        if duration <= 0:
            raise ValueError("运动时长必须为正数")
        
        if age is not None and age <= 0:
            raise ValueError("年龄必须为正数")
        
        if heart_rate is not None and heart_rate <= 0:
            raise ValueError("心率必须为正数")
        
        # 常见运动的MET值(代谢当量)
        # MET值表示相对于静息状态的能量消耗倍数
        met_values = {
            "跑步": {"low": 7.0, "moderate": 9.8, "high": 12.5},
            "慢跑": {"low": 6.0, "moderate": 8.0, "high": 10.0},
            "走路": {"low": 2.5, "moderate": 3.5, "high": 5.0},
            "游泳": {"low": 5.0, "moderate": 7.0, "high": 10.0},
            "骑车": {"low": 4.0, "moderate": 6.0, "high": 10.0},
            "健身操": {"low": 4.0, "moderate": 6.0, "high": 8.0},
            "举重": {"low": 3.0, "moderate": 5.0, "high": 6.0},
            "瑜伽": {"low": 2.5, "moderate": 3.0, "high": 4.0},
            "普拉提": {"low": 2.8, "moderate": 3.5, "high": 4.5},
            "高强度间歇训练": {"low": 6.0, "moderate": 8.0, "high": 12.0},
            "篮球": {"low": 4.5, "moderate": 6.0, "high": 8.0},
            "足球": {"low": 5.0, "moderate": 7.0, "high": 10.0},
            "网球": {"low": 4.0, "moderate": 6.0, "high": 8.0},
            "羽毛球": {"low": 4.0, "moderate": 5.5, "high": 7.0},
            "跳绳": {"low": 8.0, "moderate": 10.0, "high": 12.0},
            "爬楼梯": {"low": 4.0, "moderate": 6.0, "high": 8.0},
            "跳舞": {"low": 3.0, "moderate": 4.5, "high": 6.5},
            "拳击": {"low": 6.0, "moderate": 9.0, "high": 12.0},
            "划船": {"low": 3.5, "moderate": 5.5, "high": 8.5},
            "椭圆机": {"low": 5.0, "moderate": 7.0, "high": 9.0},
            "登山": {"low": 5.0, "moderate": 7.0, "high": 9.0}
        }
        
        # 如果提供的运动类型不在列表中，使用默认值
        if activity not in met_values:
            default_met = {"low": 3.0, "moderate": 5.0, "high": 8.0}
            met = default_met[intensity]
            activity_found = False
        else:
            met = met_values[activity][intensity]
            activity_found = True
        
        # 基于MET值计算卡路里消耗
        # 公式: 卡路里 = MET * 体重(kg) * 时长(小时)
        calories_burned = met * weight * (duration / 60)
        
        # 如果提供了心率，使用心率公式进行更精确的计算
        hr_calories = None
        if heart_rate is not None and age is not None and gender is not None:
            # 计算最大心率
            max_hr = 220 - age if gender == "male" else 226 - age
            
            # 计算心率储备百分比
            hr_reserve_percent = (heart_rate - 70) / (max_hr - 70)
            
            # 使用Keytel公式计算卡路里消耗
            if gender == "male":
                hr_calories = (-55.0969 + 0.6309 * heart_rate + 0.1988 * weight + 0.2017 * age) / 4.184 * duration
            else:  # female
                hr_calories = (-20.4022 + 0.4472 * heart_rate - 0.1263 * weight + 0.074 * age) / 4.184 * duration
        
        result = {
            "status": "success",
            "calories_burned": round(calories_burned),
            "activity": activity,
            "activity_found": activity_found,
            "duration": duration,
            "intensity": intensity,
            "met_value": met,
            "unit": "卡路里",
            "timestamp": datetime.now().isoformat()
        }
        
        # 如果计算了基于心率的卡路里消耗，添加到结果中
        if hr_calories is not None:
            result["heart_rate_based_calories"] = round(hr_calories)
            result["heart_rate"] = heart_rate
        
        return json.dumps(result, ensure_ascii=False)
    
    except ValueError as e:
        error_result = {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }
        return json.dumps(error_result, ensure_ascii=False)
    
    except Exception as e:
        error_result = {
            "status": "error",
            "message": f"计算运动卡路里消耗时发生错误: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }
        return json.dumps(error_result, ensure_ascii=False)

@tool
def calculate_water_needs(
    weight: float,
    activity_level: Literal["sedentary", "light", "moderate", "active", "very_active"],
    climate: Optional[Literal["temperate", "hot", "very_hot"]] = "temperate",
    include_food_water: bool = True
) -> str:
    """
    计算每日水分需求
    
    Args:
        weight: 体重(公斤)
        activity_level: 活动水平
            - sedentary: 久坐不动 (几乎不运动)
            - light: 轻度活动 (每周轻度运动1-3天)
            - moderate: 中度活动 (每周中等强度运动3-5天)
            - active: 积极活动 (每周剧烈运动6-7天)
            - very_active: 非常活跃 (每天剧烈运动或体力劳动工作)
        climate: 气候条件，"temperate"(温带)、"hot"(炎热)或"very_hot"(非常炎热)
        include_food_water: 是否包含从食物中获取的水分(约占总需求的20%)
    
    Returns:
        str: JSON格式的每日水分需求计算结果
    """
    try:
        # 验证输入
        if weight <= 0:
            raise ValueError("体重必须为正数")
        
        # 基础水分需求：每公斤体重30-35毫升
        base_water_ml = weight * 33
        
        # 根据活动水平调整
        activity_multipliers = {
            "sedentary": 1.0,
            "light": 1.1,
            "moderate": 1.2,
            "active": 1.3,
            "very_active": 1.4
        }
        
        # 根据气候条件调整
        climate_multipliers = {
            "temperate": 1.0,
            "hot": 1.1,
            "very_hot": 1.2
        }
        
        # 计算调整后的水分需求
        adjusted_water_ml = base_water_ml * activity_multipliers[activity_level] * climate_multipliers[climate]
        
        # 如果不包含食物中的水分，减去约20%
        if not include_food_water:
            water_from_food_ml = adjusted_water_ml * 0.2
            water_to_drink_ml = adjusted_water_ml - water_from_food_ml
        else:
            water_from_food_ml = adjusted_water_ml * 0.2
            water_to_drink_ml = adjusted_water_ml
        
        # 转换为升和杯数(假设1杯=240毫升)
        water_to_drink_liters = water_to_drink_ml / 1000
        water_to_drink_cups = water_to_drink_ml / 240
        
        result = {
            "status": "success",
            "daily_water_needs": {
                "milliliters": round(adjusted_water_ml),
                "liters": round(water_to_drink_liters, 2),
                "cups": round(water_to_drink_cups, 1)
            },
            "water_from_food": {
                "milliliters": round(water_from_food_ml),
                "percentage": "20%"
            },
            "factors": {
                "weight": weight,
                "activity_level": activity_level,
                "climate": climate,
                "include_food_water": include_food_water
            },
            "recommendations": [
                "早晨起床后立即喝1-2杯水",
                "每餐前30分钟喝1杯水",
                "运动前、中、后补充水分",
                "分散全天饮水，而不是一次大量饮用",
                "可以通过尿液颜色监测水分状态(淡黄色为理想状态)"
            ],
            "timestamp": datetime.now().isoformat()
        }
        
        return json.dumps(result, ensure_ascii=False)
    
    except ValueError as e:
        error_result = {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }
        return json.dumps(error_result, ensure_ascii=False)
    
    except Exception as e:
        error_result = {
            "status": "error",
            "message": f"计算水分需求时发生错误: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }
        return json.dumps(error_result, ensure_ascii=False)