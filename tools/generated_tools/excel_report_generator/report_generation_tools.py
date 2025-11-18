#!/usr/bin/env python3
"""
报告生成工具模块

提供HTML报告生成功能，支持嵌入图表、分析结果和自定义样式。
"""

import json
import os
import base64
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

from strands import tool


@tool
def html_report_builder(
    analysis_results: str,
    chart_paths: List[str],
    report_title: str,
    report_summary: str,
    save_path: str,
    include_data_table: bool = False,
    data_json: Optional[str] = None
) -> str:
    """
    HTML报告生成工具
    
    功能：生成包含分析逻辑和图表的HTML报告，专业的HTML结构和样式，图表嵌入，完整的分析逻辑展示
    
    Args:
        analysis_results (str): JSON格式的分析结果（来自data_analyzer）
        chart_paths (List[str]): 图表文件路径列表
        report_title (str): 报告标题
        report_summary (str): 报告摘要
        save_path (str): HTML文件保存路径
        include_data_table (bool): 是否包含原始数据表格，默认False
        data_json (Optional[str]): 原始数据JSON（如果include_data_table为True则必需）
        
    Returns:
        str: JSON格式的生成结果
    """
    try:
        # 解析分析结果
        analysis = json.loads(analysis_results)
        
        # 确保保存目录存在
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        
        # 验证图表文件
        valid_charts = []
        for chart_path in chart_paths:
            if os.path.exists(chart_path):
                valid_charts.append(chart_path)
        
        # 生成HTML内容
        html_content = _generate_html_template(
            report_title=report_title,
            report_summary=report_summary,
            analysis=analysis,
            chart_paths=valid_charts,
            include_data_table=include_data_table,
            data_json=data_json
        )
        
        # 保存HTML文件
        with open(save_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return json.dumps({
            "status": "success",
            "report_type": "html",
            "file_path": save_path,
            "file_name": os.path.basename(save_path),
            "file_size_bytes": os.path.getsize(save_path),
            "report_info": {
                "title": report_title,
                "charts_included": len(valid_charts),
                "charts_missing": len(chart_paths) - len(valid_charts),
                "includes_data_table": include_data_table
            },
            "timestamp": datetime.now().isoformat()
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"HTML报告生成失败: {str(e)}",
            "error_type": type(e).__name__,
            "timestamp": datetime.now().isoformat()
        }, ensure_ascii=False, indent=2)


def _generate_html_template(
    report_title: str,
    report_summary: str,
    analysis: Dict[str, Any],
    chart_paths: List[str],
    include_data_table: bool,
    data_json: Optional[str]
) -> str:
    """生成HTML报告模板"""
    
    # 嵌入图表为base64
    chart_embeds = []
    for chart_path in chart_paths:
        try:
            with open(chart_path, 'rb') as f:
                chart_data = base64.b64encode(f.read()).decode('utf-8')
                chart_embeds.append({
                    "name": os.path.basename(chart_path),
                    "data": chart_data
                })
        except Exception as e:
            print(f"警告: 无法嵌入图表 {chart_path}: {e}")
    
    # 生成统计分析HTML
    stats_html = _generate_statistics_html(analysis.get("statistical_analysis", {}))
    
    # 生成相关性分析HTML
    corr_html = _generate_correlation_html(analysis.get("correlation_analysis", {}))
    
    # 生成趋势分析HTML
    trend_html = _generate_trend_html(analysis.get("trend_analysis", {}))
    
    # 生成异常检测HTML
    anomaly_html = _generate_anomaly_html(analysis.get("anomaly_detection", {}))
    
    # 生成数据表格HTML
    table_html = ""
    if include_data_table and data_json:
        table_html = _generate_data_table_html(data_json)
    
    # 生成图表HTML
    charts_html = ""
    for idx, chart in enumerate(chart_embeds, 1):
        charts_html += f"""
        <div class="chart-container">
            <h3>图表 {idx}: {chart['name']}</h3>
            <img src="data:image/png;base64,{chart['data']}" alt="{chart['name']}" class="chart-image">
        </div>
        """
    
    # 完整HTML模板
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{report_title}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            background-color: #f5f5f5;
            padding: 20px;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            padding: 40px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        
        h1 {{
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 15px;
            margin-bottom: 30px;
            font-size: 2.5em;
        }}
        
        h2 {{
            color: #34495e;
            margin-top: 40px;
            margin-bottom: 20px;
            font-size: 1.8em;
            border-left: 4px solid #3498db;
            padding-left: 15px;
        }}
        
        h3 {{
            color: #7f8c8d;
            margin-top: 25px;
            margin-bottom: 15px;
            font-size: 1.3em;
        }}
        
        .summary {{
            background-color: #ecf0f1;
            padding: 20px;
            border-radius: 5px;
            margin-bottom: 30px;
            border-left: 4px solid #3498db;
        }}
        
        .section {{
            margin-bottom: 40px;
        }}
        
        .stat-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }}
        
        .stat-card {{
            background-color: #f8f9fa;
            padding: 15px;
            border-radius: 5px;
            border: 1px solid #dee2e6;
        }}
        
        .stat-card h4 {{
            color: #495057;
            margin-bottom: 10px;
            font-size: 1.1em;
        }}
        
        .stat-value {{
            font-size: 1.2em;
            font-weight: bold;
            color: #3498db;
            margin: 5px 0;
        }}
        
        .chart-container {{
            margin: 30px 0;
            text-align: center;
        }}
        
        .chart-image {{
            max-width: 100%;
            height: auto;
            border: 1px solid #ddd;
            border-radius: 5px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            font-size: 0.9em;
        }}
        
        table th {{
            background-color: #3498db;
            color: white;
            padding: 12px;
            text-align: left;
            font-weight: bold;
        }}
        
        table td {{
            padding: 10px;
            border-bottom: 1px solid #ddd;
        }}
        
        table tr:nth-child(even) {{
            background-color: #f8f9fa;
        }}
        
        table tr:hover {{
            background-color: #e9ecef;
        }}
        
        .correlation-item {{
            background-color: #fff3cd;
            padding: 10px;
            margin: 10px 0;
            border-left: 3px solid #ffc107;
            border-radius: 3px;
        }}
        
        .anomaly-item {{
            background-color: #f8d7da;
            padding: 10px;
            margin: 10px 0;
            border-left: 3px solid #dc3545;
            border-radius: 3px;
        }}
        
        .trend-item {{
            background-color: #d1ecf1;
            padding: 10px;
            margin: 10px 0;
            border-left: 3px solid #17a2b8;
            border-radius: 3px;
        }}
        
        .footer {{
            margin-top: 50px;
            padding-top: 20px;
            border-top: 2px solid #dee2e6;
            text-align: center;
            color: #6c757d;
            font-size: 0.9em;
        }}
        
        .timestamp {{
            color: #6c757d;
            font-size: 0.85em;
            margin-top: 10px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{report_title}</h1>
        
        <div class="summary">
            <h3>📋 报告摘要</h3>
            <p>{report_summary}</p>
            <div class="timestamp">生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
        </div>
        
        <div class="section">
            <h2>📊 统计分析</h2>
            {stats_html}
        </div>
        
        <div class="section">
            <h2>🔗 相关性分析</h2>
            {corr_html}
        </div>
        
        <div class="section">
            <h2>📈 趋势分析</h2>
            {trend_html}
        </div>
        
        <div class="section">
            <h2>⚠️ 异常检测</h2>
            {anomaly_html}
        </div>
        
        <div class="section">
            <h2>📉 可视化图表</h2>
            {charts_html}
        </div>
        
        {table_html}
        
        <div class="footer">
            <p>本报告由Excel报表生成系统自动生成</p>
            <p class="timestamp">© {datetime.now().year} Excel Report Generator</p>
        </div>
    </div>
</body>
</html>"""
    
    return html


def _generate_statistics_html(stats: Dict[str, Any]) -> str:
    """生成统计分析HTML"""
    if not stats:
        return "<p>无统计分析数据</p>"
    
    html = '<div class="stat-grid">'
    
    for col_name, col_stats in stats.items():
        html += f"""
        <div class="stat-card">
            <h4>{col_name}</h4>
            <div class="stat-value">均值: {col_stats.get('mean', 'N/A'):.2f}</div>
            <div class="stat-value">中位数: {col_stats.get('median', 'N/A'):.2f}</div>
            <div class="stat-value">标准差: {col_stats.get('std', 'N/A'):.2f}</div>
            <div class="stat-value">最小值: {col_stats.get('min', 'N/A'):.2f}</div>
            <div class="stat-value">最大值: {col_stats.get('max', 'N/A'):.2f}</div>
            <div class="stat-value">范围: {col_stats.get('range', 'N/A'):.2f}</div>
        </div>
        """
    
    html += '</div>'
    return html


def _generate_correlation_html(corr_analysis: Dict[str, Any]) -> str:
    """生成相关性分析HTML"""
    if not corr_analysis or "high_correlations" not in corr_analysis:
        return "<p>无显著相关性</p>"
    
    high_corrs = corr_analysis["high_correlations"]
    
    if not high_corrs:
        return "<p>未发现高相关性变量对</p>"
    
    html = "<p>发现以下高相关性变量对：</p>"
    
    for corr in high_corrs:
        html += f"""
        <div class="correlation-item">
            <strong>{corr['variable1']}</strong> 与 <strong>{corr['variable2']}</strong>
            <br>相关系数: {corr['correlation']:.3f} ({corr['strength']})
        </div>
        """
    
    return html


def _generate_trend_html(trend_analysis: Dict[str, Any]) -> str:
    """生成趋势分析HTML"""
    if not trend_analysis:
        return "<p>无趋势分析数据（可能未检测到时间序列）</p>"
    
    html = ""
    
    for col_name, trend_info in trend_analysis.items():
        direction = "上升" if trend_info["trend_direction"] == "increasing" else "下降"
        change_pct = trend_info.get("change_percentage")
        
        html += f"""
        <div class="trend-item">
            <strong>{col_name}</strong>
            <br>趋势方向: {direction}
            <br>变化幅度: {change_pct:.2f}% (从 {trend_info['start_value']:.2f} 到 {trend_info['end_value']:.2f})
            <br>斜率: {trend_info['slope']:.4f}
        </div>
        """
    
    return html


def _generate_anomaly_html(anomaly_detection: Dict[str, Any]) -> str:
    """生成异常检测HTML"""
    if not anomaly_detection:
        return "<p>未检测到异常值</p>"
    
    html = ""
    
    for col_name, anomaly_info in anomaly_detection.items():
        html += f"""
        <div class="anomaly-item">
            <strong>{col_name}</strong>
            <br>异常值数量: {anomaly_info['count']} ({anomaly_info['percentage']:.2f}%)
            <br>异常值范围: 低于 {anomaly_info['bounds']['lower']:.2f} 或高于 {anomaly_info['bounds']['upper']:.2f}
            <br>异常值索引: {', '.join(map(str, anomaly_info['outlier_indices'][:10]))}
        </div>
        """
    
    return html


def _generate_data_table_html(data_json: str) -> str:
    """生成数据表格HTML"""
    try:
        import pandas as pd
        
        data = json.loads(data_json)
        if "data" in data:
            df = pd.DataFrame(data["data"])
        else:
            df = pd.DataFrame(data)
        
        # 限制显示行数
        max_rows = 100
        if len(df) > max_rows:
            df_display = df.head(max_rows)
            note = f"<p><em>注意: 仅显示前{max_rows}行数据，共{len(df)}行</em></p>"
        else:
            df_display = df
            note = ""
        
        # 转换为HTML表格
        table_html = df_display.to_html(
            index=False,
            classes='data-table',
            border=0,
            na_rep='N/A'
        )
        
        return f"""
        <div class="section">
            <h2>📋 原始数据</h2>
            {note}
            {table_html}
        </div>
        """
    except Exception as e:
        return f"<p>数据表格生成失败: {str(e)}</p>"


if __name__ == "__main__":
    print("🧪 测试报告生成工具...")
    print("✅ 报告生成工具模块加载成功！")
