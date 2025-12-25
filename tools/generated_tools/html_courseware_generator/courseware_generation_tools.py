"""
HTML课件生成工具集

该模块提供课件生成相关的工具函数，包括HTML结构生成、CSS样式生成、
JavaScript交互代码生成、学科特定内容生成等功能。
"""

import json
import re
from typing import Dict, Any, List, Optional
from strands import tool


@tool
def html_structure_generator(
    subject: str,
    topic: str,
    sections: List[Dict[str, Any]],
    include_navigation: bool = True
) -> str:
    """
    生成HTML课件的基础结构
    
    Args:
        subject: 学科名称
        topic: 课件主题
        sections: 章节列表，每个章节包含title和content_type
        include_navigation: 是否包含导航栏
        
    Returns:
        str: JSON格式的HTML结构字符串
    """
    try:
        # 生成HTML头部
        html_head = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="{subject} - {topic}">
    <title>{topic} - {subject}课件</title>
    <style id="courseware-styles"></style>
</head>"""
        
        # 生成导航栏
        nav_html = ""
        if include_navigation:
            nav_items = "".join([
                f'<li><a href="#section-{i}" class="nav-link">{section["title"]}</a></li>'
                for i, section in enumerate(sections)
            ])
            nav_html = f"""
    <nav class="courseware-nav">
        <div class="nav-header">
            <h1>{topic}</h1>
            <span class="subject-tag">{subject}</span>
        </div>
        <ul class="nav-menu">
            {nav_items}
        </ul>
    </nav>"""
        
        # 生成主体结构
        sections_html = "".join([
            f"""
    <section id="section-{i}" class="courseware-section" data-type="{section.get('content_type', 'text')}">
        <h2 class="section-title">{section["title"]}</h2>
        <div class="section-content" id="content-{i}">
            <!-- 内容将由其他工具填充 -->
        </div>
    </section>"""
            for i, section in enumerate(sections)
        ])
        
        # 生成HTML主体
        html_body = f"""
<body>
    <div class="courseware-container">
        {nav_html}
        <main class="courseware-main">
            {sections_html}
        </main>
    </div>
    <script id="courseware-scripts"></script>
</body>
</html>"""
        
        html_structure = html_head + html_body
        
        return json.dumps({
            "status": "success",
            "html_structure": html_structure,
            "section_count": len(sections),
            "has_navigation": include_navigation,
            "metadata": {
                "subject": subject,
                "topic": topic,
                "sections": [s["title"] for s in sections]
            }
        }, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "error_type": "html_structure_generation_error",
            "message": f"HTML结构生成失败: {str(e)}"
        }, ensure_ascii=False)


@tool
def css_style_generator(
    theme: str = "modern",
    color_scheme: Optional[Dict[str, str]] = None,
    responsive: bool = True
) -> str:
    """
    生成CSS样式代码
    
    Args:
        theme: 主题样式，可选值：modern, classic, minimal
        color_scheme: 自定义色彩方案，包含primary, secondary, background, text等
        responsive: 是否生成响应式样式
        
    Returns:
        str: JSON格式的CSS样式字符串
    """
    try:
        # 默认色彩方案
        default_colors = {
            "modern": {
                "primary": "#3498db",
                "secondary": "#2ecc71",
                "background": "#f8f9fa",
                "text": "#2c3e50",
                "accent": "#e74c3c"
            },
            "classic": {
                "primary": "#2c5aa0",
                "secondary": "#5a8fc0",
                "background": "#ffffff",
                "text": "#333333",
                "accent": "#d9534f"
            },
            "minimal": {
                "primary": "#000000",
                "secondary": "#666666",
                "background": "#ffffff",
                "text": "#333333",
                "accent": "#999999"
            }
        }
        
        colors = color_scheme if color_scheme else default_colors.get(theme, default_colors["modern"])
        
        # 基础样式
        css_content = f"""
/* 全局样式 */
* {{
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}}

body {{
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    line-height: 1.6;
    color: {colors['text']};
    background-color: {colors['background']};
}}

/* 容器样式 */
.courseware-container {{
    max-width: 1200px;
    margin: 0 auto;
    padding: 20px;
}}

/* 导航栏样式 */
.courseware-nav {{
    background: {colors['primary']};
    color: white;
    padding: 20px;
    border-radius: 8px;
    margin-bottom: 30px;
}}

.nav-header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 15px;
}}

.nav-header h1 {{
    font-size: 2rem;
    font-weight: 600;
}}

.subject-tag {{
    background: {colors['secondary']};
    padding: 5px 15px;
    border-radius: 20px;
    font-size: 0.9rem;
}}

.nav-menu {{
    list-style: none;
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
}}

.nav-link {{
    color: white;
    text-decoration: none;
    padding: 8px 16px;
    border-radius: 5px;
    transition: background 0.3s;
}}

.nav-link:hover {{
    background: rgba(255, 255, 255, 0.2);
}}

/* 章节样式 */
.courseware-section {{
    background: white;
    padding: 30px;
    margin-bottom: 30px;
    border-radius: 8px;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}}

.section-title {{
    color: {colors['primary']};
    font-size: 1.8rem;
    margin-bottom: 20px;
    border-bottom: 3px solid {colors['secondary']};
    padding-bottom: 10px;
}}

.section-content {{
    font-size: 1.1rem;
    line-height: 1.8;
}}

/* 交互元素样式 */
.interactive-element {{
    margin: 20px 0;
    padding: 20px;
    background: {colors['background']};
    border-left: 4px solid {colors['accent']};
    border-radius: 5px;
}}

.quiz-question {{
    margin: 15px 0;
}}

.quiz-options {{
    list-style: none;
    margin: 10px 0;
}}

.quiz-option {{
    padding: 10px;
    margin: 5px 0;
    background: white;
    border: 2px solid #ddd;
    border-radius: 5px;
    cursor: pointer;
    transition: all 0.3s;
}}

.quiz-option:hover {{
    border-color: {colors['primary']};
    background: {colors['background']};
}}

.quiz-option.selected {{
    border-color: {colors['secondary']};
    background: {colors['secondary']};
    color: white;
}}

.quiz-option.correct {{
    border-color: #2ecc71;
    background: #d5f4e6;
}}

.quiz-option.incorrect {{
    border-color: #e74c3c;
    background: #fadbd8;
}}

/* 按钮样式 */
.btn {{
    padding: 10px 20px;
    border: none;
    border-radius: 5px;
    cursor: pointer;
    font-size: 1rem;
    transition: all 0.3s;
}}

.btn-primary {{
    background: {colors['primary']};
    color: white;
}}

.btn-primary:hover {{
    background: {colors['secondary']};
}}

.btn-secondary {{
    background: {colors['secondary']};
    color: white;
}}

.feedback-message {{
    padding: 15px;
    margin: 10px 0;
    border-radius: 5px;
    font-weight: 500;
}}

.feedback-success {{
    background: #d5f4e6;
    color: #27ae60;
    border-left: 4px solid #27ae60;
}}

.feedback-error {{
    background: #fadbd8;
    color: #c0392b;
    border-left: 4px solid #c0392b;
}}

/* 数学公式样式 */
.math-formula {{
    display: block;
    margin: 20px 0;
    padding: 15px;
    background: white;
    border: 1px solid #ddd;
    border-radius: 5px;
    overflow-x: auto;
    text-align: center;
}}

/* 化学方程式样式 */
.chemistry-equation {{
    display: block;
    margin: 20px 0;
    padding: 15px;
    background: #f0f8ff;
    border: 1px solid #b0d4f1;
    border-radius: 5px;
    text-align: center;
    font-family: 'Courier New', monospace;
}}

/* 图表容器 */
.chart-container {{
    margin: 20px 0;
    padding: 20px;
    background: white;
    border-radius: 5px;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}}"""

        # 响应式样式
        if responsive:
            css_content += f"""

/* 响应式样式 */
@media (max-width: 768px) {{
    .courseware-container {{
        padding: 10px;
    }}
    
    .nav-header h1 {{
        font-size: 1.5rem;
    }}
    
    .nav-menu {{
        flex-direction: column;
    }}
    
    .courseware-section {{
        padding: 20px;
    }}
    
    .section-title {{
        font-size: 1.5rem;
    }}
    
    .section-content {{
        font-size: 1rem;
    }}
}}

@media (max-width: 480px) {{
    .nav-header {{
        flex-direction: column;
        align-items: flex-start;
        gap: 10px;
    }}
    
    .section-title {{
        font-size: 1.3rem;
    }}
}}"""
        
        return json.dumps({
            "status": "success",
            "css_content": css_content,
            "theme": theme,
            "responsive": responsive,
            "color_scheme": colors
        }, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "error_type": "css_generation_error",
            "message": f"CSS生成失败: {str(e)}"
        }, ensure_ascii=False)


@tool
def javascript_code_generator(
    interactive_elements: List[Dict[str, Any]],
    include_analytics: bool = False
) -> str:
    """
    生成JavaScript交互代码
    
    Args:
        interactive_elements: 交互元素列表，每个元素包含type和config
        include_analytics: 是否包含学习分析代码
        
    Returns:
        str: JSON格式的JavaScript代码字符串
    """
    try:
        js_code = """
// 课件交互代码
(function() {
    'use strict';
    
    // 工具函数
    const utils = {
        // 获取元素
        getElement: (selector) => document.querySelector(selector),
        getElements: (selector) => document.querySelectorAll(selector),
        
        // 显示反馈
        showFeedback: (message, type = 'success') => {
            const feedback = document.createElement('div');
            feedback.className = `feedback-message feedback-${type}`;
            feedback.textContent = message;
            feedback.style.animation = 'fadeIn 0.3s';
            return feedback;
        },
        
        // 平滑滚动
        smoothScroll: (targetId) => {
            const target = document.getElementById(targetId);
            if (target) {
                target.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        }
    };
    
    // 导航功能
    const navigation = {
        init: () => {
            const navLinks = utils.getElements('.nav-link');
            navLinks.forEach(link => {
                link.addEventListener('click', (e) => {
                    e.preventDefault();
                    const targetId = link.getAttribute('href').substring(1);
                    utils.smoothScroll(targetId);
                });
            });
        }
    };
"""
        
        # 为每种交互元素类型生成代码
        for element in interactive_elements:
            element_type = element.get("type", "")
            element_config = element.get("config", {})
            
            if element_type == "quiz":
                js_code += """
    // 选择题功能
    const quiz = {
        init: () => {
            const quizzes = utils.getElements('.quiz-question');
            quizzes.forEach((quizEl, index) => {
                const options = quizEl.querySelectorAll('.quiz-option');
                const submitBtn = quizEl.querySelector('.quiz-submit');
                const correctAnswer = quizEl.dataset.correct;
                
                options.forEach(option => {
                    option.addEventListener('click', () => {
                        options.forEach(opt => opt.classList.remove('selected'));
                        option.classList.add('selected');
                    });
                });
                
                if (submitBtn) {
                    submitBtn.addEventListener('click', () => {
                        const selected = quizEl.querySelector('.quiz-option.selected');
                        if (!selected) {
                            const feedback = utils.showFeedback('请先选择一个答案', 'error');
                            quizEl.appendChild(feedback);
                            setTimeout(() => feedback.remove(), 3000);
                            return;
                        }
                        
                        const selectedValue = selected.dataset.value;
                        const isCorrect = selectedValue === correctAnswer;
                        
                        selected.classList.add(isCorrect ? 'correct' : 'incorrect');
                        submitBtn.disabled = true;
                        
                        const message = isCorrect ? '回答正确！' : `回答错误，正确答案是：${correctAnswer}`;
                        const feedback = utils.showFeedback(message, isCorrect ? 'success' : 'error');
                        quizEl.appendChild(feedback);
                        
                        // 显示正确答案
                        if (!isCorrect) {
                            const correctOption = quizEl.querySelector(`[data-value="${correctAnswer}"]`);
                            if (correctOption) {
                                correctOption.classList.add('correct');
                            }
                        }
                    });
                }
            });
        }
    };
"""
            
            elif element_type == "input":
                js_code += """
    // 输入题功能
    const inputQuiz = {
        init: () => {
            const inputQuestions = utils.getElements('.input-question');
            inputQuestions.forEach(questionEl => {
                const inputField = questionEl.querySelector('.answer-input');
                const submitBtn = questionEl.querySelector('.input-submit');
                const correctAnswer = questionEl.dataset.correct;
                const caseSensitive = questionEl.dataset.caseSensitive === 'true';
                
                if (submitBtn) {
                    submitBtn.addEventListener('click', () => {
                        let userAnswer = inputField.value.trim();
                        let correct = correctAnswer;
                        
                        if (!caseSensitive) {
                            userAnswer = userAnswer.toLowerCase();
                            correct = correct.toLowerCase();
                        }
                        
                        const isCorrect = userAnswer === correct;
                        
                        inputField.classList.add(isCorrect ? 'correct' : 'incorrect');
                        submitBtn.disabled = true;
                        
                        const message = isCorrect ? '回答正确！' : `回答错误，正确答案是：${correctAnswer}`;
                        const feedback = utils.showFeedback(message, isCorrect ? 'success' : 'error');
                        questionEl.appendChild(feedback);
                    });
                }
            });
        }
    };
"""
            
            elif element_type == "chart":
                js_code += """
    // 图表功能（使用Chart.js）
    const charts = {
        init: () => {
            const chartContainers = utils.getElements('.chart-container');
            chartContainers.forEach(container => {
                const canvas = container.querySelector('canvas');
                if (!canvas) return;
                
                const chartData = JSON.parse(container.dataset.chartData || '{}');
                const chartType = container.dataset.chartType || 'line';
                
                new Chart(canvas.getContext('2d'), {
                    type: chartType,
                    data: chartData,
                    options: {
                        responsive: true,
                        maintainAspectRatio: true,
                        plugins: {
                            legend: {
                                position: 'top',
                            },
                            title: {
                                display: true,
                                text: chartData.title || '图表'
                            }
                        }
                    }
                });
            });
        }
    };
"""
        
        # 添加初始化代码
        js_code += """
    // 页面加载完成后初始化
    document.addEventListener('DOMContentLoaded', () => {
        navigation.init();
"""
        
        for element in interactive_elements:
            element_type = element.get("type", "")
            if element_type == "quiz":
                js_code += "        quiz.init();\n"
            elif element_type == "input":
                js_code += "        inputQuiz.init();\n"
            elif element_type == "chart":
                js_code += "        charts.init();\n"
        
        js_code += """    });
})();
"""
        
        # 添加学习分析代码
        if include_analytics:
            js_code += """
// 学习分析
const analytics = {
    trackInteraction: (type, data) => {
        console.log('Learning Analytics:', { type, data, timestamp: new Date().toISOString() });
        // 可以将数据发送到后端分析系统
    }
};
"""
        
        return json.dumps({
            "status": "success",
            "javascript_content": js_code,
            "interactive_element_count": len(interactive_elements),
            "includes_analytics": include_analytics
        }, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "error_type": "javascript_generation_error",
            "message": f"JavaScript生成失败: {str(e)}"
        }, ensure_ascii=False)


@tool
def math_formula_renderer(
    formulas: List[Dict[str, str]],
    library: str = "mathjax"
) -> str:
    """
    生成数学公式渲染代码
    
    Args:
        formulas: 公式列表，每个公式包含id、latex和description
        library: 渲染库，可选值：mathjax, katex
        
    Returns:
        str: JSON格式的公式渲染HTML和配置
    """
    try:
        if library == "mathjax":
            # MathJax配置
            config_script = """
<script>
MathJax = {
    tex: {
        inlineMath: [['$', '$'], ['\\\\(', '\\\\)']],
        displayMath: [['$$', '$$'], ['\\\\[', '\\\\]']],
        processEscapes: true
    },
    svg: {
        fontCache: 'global'
    }
};
</script>
<script src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
"""
        else:  # katex
            config_script = """
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.0/dist/katex.min.css">
<script src="https://cdn.jsdelivr.net/npm/katex@0.16.0/dist/katex.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/katex@0.16.0/dist/contrib/auto-render.min.js"></script>
<script>
document.addEventListener("DOMContentLoaded", function() {
    renderMathInElement(document.body, {
        delimiters: [
            {left: '$$', right: '$$', display: true},
            {left: '$', right: '$', display: false}
        ]
    });
});
</script>
"""
        
        # 生成公式HTML
        formulas_html = ""
        for formula in formulas:
            formula_id = formula.get("id", "")
            latex = formula.get("latex", "")
            description = formula.get("description", "")
            
            formulas_html += f"""
<div class="math-formula" id="{formula_id}">
    {f'<p class="formula-description">{description}</p>' if description else ''}
    <div class="formula-content">$${ latex}$$</div>
</div>
"""
        
        return json.dumps({
            "status": "success",
            "config_script": config_script,
            "formulas_html": formulas_html,
            "formula_count": len(formulas),
            "library": library
        }, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "error_type": "math_rendering_error",
            "message": f"数学公式渲染代码生成失败: {str(e)}"
        }, ensure_ascii=False)


@tool
def chemistry_equation_generator(
    equations: List[Dict[str, str]]
) -> str:
    """
    生成化学方程式展示HTML
    
    Args:
        equations: 化学方程式列表，每个包含id、equation和description
        
    Returns:
        str: JSON格式的化学方程式HTML
    """
    try:
        equations_html = ""
        
        for eq in equations:
            eq_id = eq.get("id", "")
            equation = eq.get("equation", "")
            description = eq.get("description", "")
            
            # 处理化学方程式格式（上标、下标）
            formatted_eq = equation
            # 下标处理：H2O -> H<sub>2</sub>O
            formatted_eq = re.sub(r'([A-Z][a-z]?)(\d+)', r'\1<sub>\2</sub>', formatted_eq)
            # 上标处理：2+ -> <sup>2+</sup>
            formatted_eq = re.sub(r'(\d+[+-])', r'<sup>\1</sup>', formatted_eq)
            
            equations_html += f"""
<div class="chemistry-equation" id="{eq_id}">
    {f'<p class="equation-description">{description}</p>' if description else ''}
    <div class="equation-content">{formatted_eq}</div>
</div>
"""
        
        # 添加化学方程式样式
        style_html = """
<style>
.chemistry-equation {
    display: block;
    margin: 20px 0;
    padding: 15px;
    background: #f0f8ff;
    border: 2px solid #b0d4f1;
    border-radius: 8px;
    text-align: center;
}

.equation-description {
    margin-bottom: 10px;
    color: #555;
    font-size: 0.95rem;
}

.equation-content {
    font-family: 'Courier New', monospace;
    font-size: 1.3rem;
    color: #2c3e50;
    font-weight: 500;
}

.chemistry-equation sub {
    font-size: 0.7em;
}

.chemistry-equation sup {
    font-size: 0.7em;
}
</style>
"""
        
        return json.dumps({
            "status": "success",
            "equations_html": equations_html,
            "style_html": style_html,
            "equation_count": len(equations)
        }, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "error_type": "chemistry_generation_error",
            "message": f"化学方程式生成失败: {str(e)}"
        }, ensure_ascii=False)


@tool
def interactive_element_builder(
    element_type: str,
    element_config: Dict[str, Any]
) -> str:
    """
    构建交互元素HTML
    
    Args:
        element_type: 元素类型，可选值：quiz, input, drag_drop, chart
        element_config: 元素配置
        
    Returns:
        str: JSON格式的交互元素HTML
    """
    try:
        element_html = ""
        
        if element_type == "quiz":
            question = element_config.get("question", "")
            options = element_config.get("options", [])
            correct_answer = element_config.get("correct_answer", "")
            explanation = element_config.get("explanation", "")
            
            options_html = "".join([
                f'<li class="quiz-option" data-value="{opt["value"]}">{opt["text"]}</li>'
                for opt in options
            ])
            
            element_html = f"""
<div class="quiz-question interactive-element" data-correct="{correct_answer}">
    <p class="question-text">{question}</p>
    <ul class="quiz-options">
        {options_html}
    </ul>
    <button class="btn btn-primary quiz-submit">提交答案</button>
    {f'<div class="explanation" style="display:none;">{explanation}</div>' if explanation else ''}
</div>
"""
        
        elif element_type == "input":
            question = element_config.get("question", "")
            correct_answer = element_config.get("correct_answer", "")
            placeholder = element_config.get("placeholder", "请输入答案")
            case_sensitive = element_config.get("case_sensitive", False)
            
            element_html = f"""
<div class="input-question interactive-element" data-correct="{correct_answer}" data-case-sensitive="{str(case_sensitive).lower()}">
    <p class="question-text">{question}</p>
    <input type="text" class="answer-input" placeholder="{placeholder}">
    <button class="btn btn-primary input-submit">提交答案</button>
</div>
"""
        
        elif element_type == "chart":
            chart_data = element_config.get("data", {})
            chart_type = element_config.get("chart_type", "line")
            title = element_config.get("title", "图表")
            
            element_html = f"""
<div class="chart-container interactive-element" data-chart-type="{chart_type}" data-chart-data='{json.dumps(chart_data)}'>
    <canvas id="chart-{element_config.get('id', 'default')}"></canvas>
</div>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
"""
        
        return json.dumps({
            "status": "success",
            "element_html": element_html,
            "element_type": element_type
        }, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "error_type": "interactive_element_error",
            "message": f"交互元素构建失败: {str(e)}"
        }, ensure_ascii=False)


@tool
def code_validator(
    html_content: str,
    check_xss: bool = True,
    check_syntax: bool = True
) -> str:
    """
    验证HTML、CSS、JavaScript代码
    
    Args:
        html_content: 完整的HTML内容
        check_xss: 是否检查XSS安全问题
        check_syntax: 是否检查语法错误
        
    Returns:
        str: JSON格式的验证结果
    """
    try:
        validation_results = {
            "is_valid": True,
            "warnings": [],
            "errors": [],
            "security_issues": []
        }
        
        # XSS安全检查
        if check_xss:
            dangerous_patterns = [
                r'<script[^>]*>.*?eval\(',
                r'javascript:',
                r'onerror\s*=',
                r'onclick\s*=.*?<script',
                r'<iframe[^>]*src\s*=\s*["\']javascript:',
            ]
            
            for pattern in dangerous_patterns:
                if re.search(pattern, html_content, re.IGNORECASE | re.DOTALL):
                    validation_results["security_issues"].append({
                        "type": "xss_risk",
                        "pattern": pattern,
                        "severity": "high",
                        "message": "检测到潜在的XSS安全风险"
                    })
                    validation_results["is_valid"] = False
        
        # 语法检查
        if check_syntax:
            # 检查HTML标签闭合
            open_tags = re.findall(r'<([a-zA-Z][a-zA-Z0-9]*)[^>]*>', html_content)
            close_tags = re.findall(r'</([a-zA-Z][a-zA-Z0-9]*)>', html_content)
            
            # 过滤自闭合标签
            self_closing = {'img', 'br', 'hr', 'input', 'meta', 'link'}
            open_tags = [tag for tag in open_tags if tag.lower() not in self_closing]
            
            # 检查标签匹配
            if len(open_tags) != len(close_tags):
                validation_results["errors"].append({
                    "type": "syntax_error",
                    "message": f"HTML标签不匹配：开始标签{len(open_tags)}个，结束标签{len(close_tags)}个"
                })
                validation_results["is_valid"] = False
            
            # 检查基本结构
            required_elements = ['<!DOCTYPE', '<html', '<head', '<body']
            for element in required_elements:
                if element not in html_content:
                    validation_results["warnings"].append({
                        "type": "structure_warning",
                        "message": f"缺少推荐的HTML元素：{element}"
                    })
        
        # 文件大小检查
        size_kb = len(html_content.encode('utf-8')) / 1024
        if size_kb > 500:
            validation_results["warnings"].append({
                "type": "size_warning",
                "message": f"HTML文件较大（{size_kb:.2f}KB），建议优化"
            })
        
        return json.dumps({
            "status": "success",
            "validation_results": validation_results,
            "file_size_kb": round(size_kb, 2)
        }, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "error_type": "validation_error",
            "message": f"代码验证失败: {str(e)}"
        }, ensure_ascii=False)


@tool
def xss_scanner(
    html_content: str,
    auto_fix: bool = False
) -> str:
    """
    扫描XSS安全漏洞
    
    Args:
        html_content: HTML内容
        auto_fix: 是否自动修复安全问题
        
    Returns:
        str: JSON格式的扫描结果
    """
    try:
        issues = []
        fixed_content = html_content
        
        # 定义危险模式
        dangerous_patterns = [
            {
                "pattern": r'<script[^>]*>.*?eval\(',
                "name": "eval函数",
                "severity": "critical",
                "fix": None  # eval不能自动修复
            },
            {
                "pattern": r'javascript:',
                "name": "javascript:协议",
                "severity": "high",
                "fix": r'#'
            },
            {
                "pattern": r'\bon\w+\s*=',
                "name": "内联事件处理器",
                "severity": "medium",
                "fix": None
            },
            {
                "pattern": r'document\.write',
                "name": "document.write",
                "severity": "medium",
                "fix": None
            }
        ]
        
        for pattern_info in dangerous_patterns:
            pattern = pattern_info["pattern"]
            matches = list(re.finditer(pattern, html_content, re.IGNORECASE | re.DOTALL))
            
            if matches:
                issue = {
                    "type": "xss_vulnerability",
                    "name": pattern_info["name"],
                    "severity": pattern_info["severity"],
                    "count": len(matches),
                    "locations": [m.start() for m in matches[:5]],  # 最多显示5个位置
                    "can_auto_fix": pattern_info["fix"] is not None
                }
                issues.append(issue)
                
                # 自动修复
                if auto_fix and pattern_info["fix"] is not None:
                    fixed_content = re.sub(pattern, pattern_info["fix"], fixed_content, flags=re.IGNORECASE)
        
        # 检查HTML实体编码
        unencoded_chars = re.findall(r'[<>&"\']', html_content)
        if unencoded_chars:
            issues.append({
                "type": "encoding_warning",
                "name": "未编码的特殊字符",
                "severity": "low",
                "count": len(unencoded_chars),
                "message": "建议对特殊字符进行HTML实体编码"
            })
        
        is_safe = len([i for i in issues if i["severity"] in ["critical", "high"]]) == 0
        
        return json.dumps({
            "status": "success",
            "is_safe": is_safe,
            "issues": issues,
            "total_issues": len(issues),
            "fixed_content": fixed_content if auto_fix else None,
            "auto_fix_applied": auto_fix
        }, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "error_type": "xss_scan_error",
            "message": f"XSS扫描失败: {str(e)}"
        }, ensure_ascii=False)


@tool
def subject_template_selector(
    subject: str
) -> str:
    """
    选择学科对应的模板配置
    
    Args:
        subject: 学科名称
        
    Returns:
        str: JSON格式的模板配置
    """
    try:
        # 学科模板配置
        templates = {
            "数学": {
                "features": ["math_formulas", "charts", "quiz"],
                "required_libraries": ["mathjax"],
                "color_scheme": {"primary": "#3498db", "secondary": "#2ecc71"},
                "section_templates": [
                    {"title": "学习目标", "type": "text"},
                    {"title": "知识讲解", "type": "text_with_formulas"},
                    {"title": "例题演示", "type": "examples"},
                    {"title": "练习题", "type": "quiz"},
                    {"title": "总结", "type": "text"}
                ]
            },
            "化学": {
                "features": ["chemistry_equations", "charts", "quiz"],
                "required_libraries": [],
                "color_scheme": {"primary": "#9b59b6", "secondary": "#3498db"},
                "section_templates": [
                    {"title": "学习目标", "type": "text"},
                    {"title": "知识讲解", "type": "text_with_equations"},
                    {"title": "化学反应", "type": "chemistry"},
                    {"title": "练习题", "type": "quiz"},
                    {"title": "总结", "type": "text"}
                ]
            },
            "物理": {
                "features": ["math_formulas", "charts", "quiz"],
                "required_libraries": ["mathjax", "chartjs"],
                "color_scheme": {"primary": "#e74c3c", "secondary": "#f39c12"},
                "section_templates": [
                    {"title": "学习目标", "type": "text"},
                    {"title": "物理概念", "type": "text_with_formulas"},
                    {"title": "图表分析", "type": "charts"},
                    {"title": "练习题", "type": "quiz"},
                    {"title": "总结", "type": "text"}
                ]
            },
            "语文": {
                "features": ["quiz", "input"],
                "required_libraries": [],
                "color_scheme": {"primary": "#16a085", "secondary": "#27ae60"},
                "section_templates": [
                    {"title": "学习目标", "type": "text"},
                    {"title": "课文讲解", "type": "text"},
                    {"title": "重点词句", "type": "text"},
                    {"title": "练习题", "type": "quiz"},
                    {"title": "总结", "type": "text"}
                ]
            },
            "英语": {
                "features": ["quiz", "input", "audio"],
                "required_libraries": [],
                "color_scheme": {"primary": "#2980b9", "secondary": "#8e44ad"},
                "section_templates": [
                    {"title": "学习目标", "type": "text"},
                    {"title": "词汇讲解", "type": "text"},
                    {"title": "语法要点", "type": "text"},
                    {"title": "练习题", "type": "quiz"},
                    {"title": "总结", "type": "text"}
                ]
            }
        }
        
        # 获取模板或使用通用模板
        template = templates.get(subject, {
            "features": ["quiz"],
            "required_libraries": [],
            "color_scheme": {"primary": "#34495e", "secondary": "#7f8c8d"},
            "section_templates": [
                {"title": "学习目标", "type": "text"},
                {"title": "知识讲解", "type": "text"},
                {"title": "练习题", "type": "quiz"},
                {"title": "总结", "type": "text"}
            ]
        })
        
        return json.dumps({
            "status": "success",
            "subject": subject,
            "template": template,
            "is_custom_subject": subject not in templates
        }, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "error_type": "template_selection_error",
            "message": f"模板选择失败: {str(e)}"
        }, ensure_ascii=False)


@tool
def physics_chart_generator(
    chart_config: Dict[str, Any]
) -> str:
    """
    生成物理图表代码
    
    Args:
        chart_config: 图表配置，包含type、data、labels等
        
    Returns:
        str: JSON格式的图表HTML和配置
    """
    try:
        chart_id = chart_config.get("id", f"chart-{hash(str(chart_config))}")
        chart_type = chart_config.get("type", "line")
        title = chart_config.get("title", "物理图表")
        data = chart_config.get("data", {})
        
        # 生成Chart.js配置
        chart_data_json = json.dumps(data, ensure_ascii=False)
        
        chart_html = f"""
<div class="chart-container" id="{chart_id}-container">
    <h3 class="chart-title">{title}</h3>
    <canvas id="{chart_id}"></canvas>
</div>

<script>
(function() {{
    const ctx = document.getElementById('{chart_id}');
    if (ctx && typeof Chart !== 'undefined') {{
        new Chart(ctx, {{
            type: '{chart_type}',
            data: {chart_data_json},
            options: {{
                responsive: true,
                maintainAspectRatio: true,
                plugins: {{
                    legend: {{
                        position: 'top',
                    }},
                    title: {{
                        display: true,
                        text: '{title}'
                    }}
                }},
                scales: {{
                    y: {{
                        beginAtZero: true
                    }}
                }}
            }}
        }});
    }}
}})();
</script>
"""
        
        # Chart.js CDN链接
        cdn_link = '<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>'
        
        return json.dumps({
            "status": "success",
            "chart_html": chart_html,
            "cdn_link": cdn_link,
            "chart_id": chart_id,
            "chart_type": chart_type
        }, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "error_type": "chart_generation_error",
            "message": f"图表生成失败: {str(e)}"
        }, ensure_ascii=False)
