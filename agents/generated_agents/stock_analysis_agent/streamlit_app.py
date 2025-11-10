"""Streamlit 前端：Stock Analysis Agent 可视化控制台

该应用为多Agent股票分析系统提供交互式界面，覆盖以下核心能力：

- 股票代码输入与分析参数配置
- 系统状态监控与日志查看
- 估值、盈利预测、风险评估、行业对比等结果展示
- 投资报告预览与下载
- 历史分析记录与缓存报告访问

运行方式：

```bash
streamlit run projects/stock_analysis_agent/streamlit_app.py
```
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple, Union

import pandas as pd
import plotly.express as px
import streamlit as st


# ---------------------------------------------------------------------------
# 路径和依赖配置
# ---------------------------------------------------------------------------
FILE_PATH = Path(__file__).resolve()
PROJECT_DIR = FILE_PATH.parent
REPO_ROOT = FILE_PATH.parents[2]

if str(REPO_ROOT) not in sys.path:
    sys.path.append(str(REPO_ROOT))

from agents.generated_agents.stock_analysis_agent.stock_analysis_agent import (  # noqa: E402
    StockAnalysisSystem,
)


REPORTS_DIR = REPO_ROOT / "reports" / "stock_analysis"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------
JsonLike = Union[Dict[str, Any], List[Any], str, int, float, bool, None]


@st.cache_resource(show_spinner=False)
def load_system(env: str, version: str, model_id: str) -> StockAnalysisSystem:
    """基于配置缓存并复用 StockAnalysisSystem 实例。"""

    return StockAnalysisSystem(env=env, version=version, model_id=model_id)


def to_jsonable(obj: JsonLike) -> JsonLike:
    """递归解析可能的 JSON 字符串，转为 Python 结构。"""

    if isinstance(obj, str):
        cleaned = obj.strip()
        if cleaned and cleaned[0] in "[{" and cleaned[-1] in "]}" :
            try:
                parsed = json.loads(cleaned)
            except json.JSONDecodeError:
                return cleaned
            return to_jsonable(parsed)
        return cleaned

    if isinstance(obj, list):
        return [to_jsonable(item) for item in obj]

    if isinstance(obj, dict):
        return {key: to_jsonable(value) for key, value in obj.items()}

    return obj


def find_section(data: JsonLike, keys: Iterable[str]) -> Optional[JsonLike]:
    """在嵌套结构中查找指定键对应的数据。"""

    if not isinstance(data, dict):
        return None

    for key in keys:
        if key in data:
            return data[key]

    for value in data.values():
        if isinstance(value, dict):
            found = find_section(value, keys)
            if found is not None:
                return found

    return None


def normalize_symbol(symbol: str) -> str:
    return symbol.strip().upper()


def build_quarterly_dataframe(prediction: Dict[str, Any]) -> Optional[pd.DataFrame]:
    quarters = prediction.get("quarters")
    earnings = prediction.get("quarterly_earnings")
    eps = prediction.get("eps_growth_rates")
    revenue = prediction.get("revenue_forecast")

    if not any([quarters, earnings, eps, revenue]):
        return None

    if quarters is None:
        quarters = [f"Q{idx + 1}" for idx in range(max(len(earnings or []), len(eps or [])))]

    data = {"季度": quarters}

    if earnings:
        data["净利润预测"] = earnings
    if revenue:
        data["营收预测"] = revenue
    if eps:
        data["EPS增长率(%)"] = eps

    return pd.DataFrame(data)


def build_comparable_dataframe(benchmark: Dict[str, Any]) -> Optional[pd.DataFrame]:
    comparables = benchmark.get("comparable_companies")
    if not isinstance(comparables, list):
        return None

    return pd.DataFrame(comparables)


def list_reports() -> List[Path]:
    if not REPORTS_DIR.exists():
        return []
    return sorted(REPORTS_DIR.glob("*.json")) + sorted(REPORTS_DIR.glob("*.md")) + sorted(
        REPORTS_DIR.glob("*.pdf")
    )


def format_timestamp(ts: str) -> str:
    try:
        return datetime.fromisoformat(ts).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return ts


# ---------------------------------------------------------------------------
# 展示逻辑
# ---------------------------------------------------------------------------
def render_summary_tab(container, analysis: Dict[str, Any], base_result: Dict[str, Any]) -> None:
    company_info = to_jsonable(find_section(analysis, ["company_info"])) or {}
    market_data = to_jsonable(find_section(analysis, ["market_data", "pricing", "price_data"])) or {}
    valuation = to_jsonable(
        find_section(analysis, ["valuation", "valuation_result", "valuation_results", "dcf_analysis"])
    ) or {}
    executive_summary = to_jsonable(
        find_section(
            analysis,
            [
                "executive_summary",
                "analysis_summary",
                "summary",
            ],
        )
    )

    cols = container.columns(3)

    cols[0].metric(
        "公司",
        company_info.get("company_name") or company_info.get("name") or base_result.get("symbol", "-"),
    )
    current_price = market_data.get("current_price") or market_data.get("last_price")
    if current_price is not None:
        cols[1].metric("当前股价", f"{current_price:,.2f}")
    intrinsic = None
    if isinstance(valuation, dict):
        intrinsic = (
            valuation.get("value_per_share")
            or valuation.get("intrinsic_value")
            or valuation.get("valuation")
            or find_section(valuation, ["value_per_share", "intrinsic_value"])
        )
    if intrinsic:
        cols[2].metric("内在价值", f"{float(intrinsic):,.2f}")

    valuation_judgment = None
    if isinstance(valuation, dict):
        valuation_judgment = (
            valuation.get("valuation_judgment")
            or valuation.get("judgment")
            or valuation.get("rating")
        )

    if valuation_judgment:
        container.info(f"估值判断：{valuation_judgment}")

    if executive_summary:
        container.subheader("执行摘要")
        if isinstance(executive_summary, dict):
            key_findings = executive_summary.get("key_findings")
            recommendation = executive_summary.get("investment_recommendation")
            if recommendation:
                container.success(f"投资建议：{recommendation}")
            if key_findings and isinstance(key_findings, list):
                for item in key_findings:
                    container.markdown(f"- {item}")
            else:
                container.json(executive_summary)
        else:
            container.write(executive_summary)


def render_valuation_tab(container, analysis: Dict[str, Any]) -> None:
    valuation = to_jsonable(
        find_section(
            analysis,
            [
                "valuation",
                "valuation_result",
                "valuation_results",
                "dcf_result",
                "dcf_analysis",
                "valuation_report",
            ],
        )
    )

    if not valuation:
        container.warning("未获取到估值结果。")
        return

    container.subheader("DCF 估值结果")
    if isinstance(valuation, dict):
        summary = valuation.get("valuation_results") or valuation
        if isinstance(summary, dict):
            df = pd.DataFrame(summary.items(), columns=["指标", "数值"])
            container.dataframe(df, use_container_width=True)

        sensitivity = to_jsonable(
            find_section(
                valuation,
                ["sensitivity_analysis", "sensitivity", "scenario_analysis"],
            )
        )
        if isinstance(sensitivity, dict):
            container.markdown("**敏感性分析**")
            sens_df = pd.DataFrame(sensitivity)
            container.dataframe(sens_df, use_container_width=True)
        elif isinstance(sensitivity, list):
            container.markdown("**敏感性分析**")
            container.dataframe(pd.DataFrame(sensitivity), use_container_width=True)
    else:
        container.write(valuation)


def render_prediction_tab(container, analysis: Dict[str, Any]) -> None:
    prediction = to_jsonable(
        find_section(
            analysis,
            [
                "prediction_result",
                "prediction",
                "earnings_forecast",
                "forecast",
            ],
        )
    )

    if not prediction:
        container.warning("未获取到盈利预测数据。")
        return

    container.subheader("未来季度盈利预测")
    if isinstance(prediction, dict):
        table = build_quarterly_dataframe(prediction)
        if table is not None:
            container.dataframe(table, use_container_width=True)
            y_cols = [col for col in table.columns if col != "季度"]
            if y_cols:
                fig = px.line(table, x="季度", y=y_cols, markers=True)
                fig.update_layout(height=400)
                container.plotly_chart(fig, use_container_width=True)

        confidence = prediction.get("confidence_intervals")
        if confidence:
            container.markdown("**置信区间**")
            container.json(confidence)
    else:
        container.write(prediction)


def render_risk_tab(container, analysis: Dict[str, Any]) -> None:
    risk = to_jsonable(
        find_section(
            analysis,
            ["risk_assessment", "risks", "risk_report"],
        )
    )

    if not risk:
        container.warning("未获取到风险评估数据。")
        return

    container.subheader("风险评估")
    if isinstance(risk, dict):
        factors = risk.get("risk_factors") or risk.get("factors")
        if isinstance(factors, list) and factors:
            df = pd.DataFrame(factors)
            container.dataframe(df, use_container_width=True)
        if "overall_risk_score" in risk:
            container.metric("总体风险评分", risk.get("overall_risk_score"))
        if "risk_levels" in risk:
            container.json(risk["risk_levels"])
        mitigation = risk.get("mitigation_strategies")
        if mitigation:
            container.markdown("**风险缓解建议**")
            if isinstance(mitigation, list):
                for item in mitigation:
                    container.markdown(f"- {item}")
            else:
                container.write(mitigation)
    else:
        container.write(risk)


def render_benchmark_tab(container, analysis: Dict[str, Any]) -> None:
    benchmark = to_jsonable(
        find_section(
            analysis,
            ["benchmark_analysis", "benchmark", "comparison", "peer_analysis"],
        )
    )

    if not benchmark:
        container.warning("未获取到行业对比数据。")
        return

    container.subheader("行业可比公司分析")
    if isinstance(benchmark, dict):
        comparables_df = build_comparable_dataframe(benchmark)
        if comparables_df is not None and not comparables_df.empty:
            container.dataframe(comparables_df, use_container_width=True)
        analyst = benchmark.get("analyst_predictions")
        if analyst:
            container.markdown("**华尔街券商预测对比**")
            if isinstance(analyst, dict):
                analyst_df = pd.DataFrame(analyst)
                container.dataframe(analyst_df, use_container_width=True)
            else:
                container.write(analyst)
        recommendations = benchmark.get("investment_recommendations")
        if recommendations:
            container.markdown("**投资建议**")
            if isinstance(recommendations, list):
                for item in recommendations:
                    container.markdown(f"- {item}")
            else:
                container.write(recommendations)
    else:
        container.write(benchmark)


def render_report_tab(container, analysis: Dict[str, Any], symbol: str) -> None:
    report = to_jsonable(
        find_section(
            analysis,
            ["report", "report_content", "full_report", "investment_report"],
        )
    )

    if not report:
        container.warning("未获取到完整投资报告。")
        return

    container.subheader("投资分析报告")

    if isinstance(report, dict):
        markdown = report.get("markdown") or report.get("content") or report.get("report_text")
        if markdown:
            container.markdown(markdown)
            container.download_button(
                label="下载 Markdown 报告",
                data=markdown.encode("utf-8"),
                file_name=f"{symbol}_report.md",
                mime="text/markdown",
            )
        else:
            container.json(report)
    elif isinstance(report, str):
        container.markdown(report)
        container.download_button(
            label="下载 Markdown 报告",
            data=report.encode("utf-8"),
            file_name=f"{symbol}_report.md",
            mime="text/markdown",
        )
    else:
        container.write(report)


def render_raw_tab(container, analysis: Dict[str, Any]) -> None:
    container.json(analysis)


def render_result(result: Dict[str, Any]) -> None:
    status = result.get("status")
    symbol = result.get("symbol", "")
    timestamp = format_timestamp(result.get("timestamp", ""))

    if status == "success":
        st.success(f"分析完成：{symbol}（{timestamp}）")
    else:
        st.error(f"分析失败：{result.get('message', '未知错误')}")
        if "analysis_result" in result:
            st.json(result["analysis_result"])
        return

    analysis = result.get("analysis_result", {})
    analysis = to_jsonable(analysis)

    if not isinstance(analysis, dict):
        st.write(analysis)
        return

    tab_titles = [
        "执行摘要",
        "估值分析",
        "盈利预测",
        "风险评估",
        "行业对比",
        "完整报告",
        "原始数据",
    ]
    tabs = st.tabs(tab_titles)

    render_summary_tab(tabs[0], analysis, result)
    render_valuation_tab(tabs[1], analysis)
    render_prediction_tab(tabs[2], analysis)
    render_risk_tab(tabs[3], analysis)
    render_benchmark_tab(tabs[4], analysis)
    render_report_tab(tabs[5], analysis, symbol)
    render_raw_tab(tabs[6], analysis)

    st.download_button(
        label="下载原始结果 JSON",
        data=json.dumps(analysis, ensure_ascii=False, indent=2).encode("utf-8"),
        file_name=f"{symbol}_{datetime.now():%Y%m%d_%H%M%S}.json",
        mime="application/json",
    )


# ---------------------------------------------------------------------------
# Streamlit 页面布局
# ---------------------------------------------------------------------------
st.set_page_config(page_title="Stock Analysis Agent 前端", layout="wide")
st.title("📈 Stock Analysis Agent 智能股票分析控制台")
st.markdown(
    "通过下方输入股票代码并配置分析参数，系统将调用多Agent工作流完成数据抓取、估值、预测、风险评估、行业对比以及报告生成。"
)


with st.sidebar:
    st.header("⚙️ 系统配置")
    env = st.selectbox("运行环境", ["production", "development", "testing"], index=0)
    version = st.selectbox("Agent 版本", ["latest"], index=0)
    model_id = st.text_input("模型 ID", value="default")

    st.divider()
    st.header("📊 分析选项")
    analysis_depth_display = st.selectbox("分析深度", ["快速", "标准", "深度"], index=1)
    depth_map = {"快速": "quick", "标准": "standard", "深度": "deep_dive"}
    lookback_years = st.slider("历史回溯年数", min_value=3, max_value=10, value=5)
    forecast_quarters = st.slider("预测季度数", min_value=4, max_value=12, value=4, step=1)
    include_macro = st.checkbox("包含宏观经济分析", value=True)
    include_benchmark = st.checkbox("包含行业对比分析", value=True)
    include_risk = st.checkbox("包含风险评估", value=True)
    include_report = st.checkbox("生成完整投资报告", value=True)
    preferred_currency = st.selectbox("报告币种", ["USD", "CNY", "HKD", "EUR"], index=0)
    risk_preference_display = st.selectbox("投资偏好", ["稳健型", "平衡型", "进取型"], index=1)
    risk_map = {"稳健型": "conservative", "平衡型": "balanced", "进取型": "aggressive"}
    custom_notes = st.text_area("附加说明或重点关注", height=120)

    status_button = st.button("刷新系统状态", use_container_width=True)

    if status_button:
        try:
            system = load_system(env, version, model_id)
            st.session_state["latest_status"] = system.get_system_status()
        except Exception as exc:  # noqa: BLE001
            st.error(f"获取系统状态失败：{exc}")

    history = st.session_state.get("analysis_history", [])
    if history:
        st.divider()
        st.header("🕘 历史记录")
        labels = [f"{item['symbol']} | {format_timestamp(item['timestamp'])}" for item in history]
        selected = st.selectbox("选择记录", options=list(range(len(history))), format_func=lambda idx: labels[idx])
        if st.button("加载选中记录", use_container_width=True):
            st.session_state["latest_result"] = history[selected]["result"]
        if st.button("清空历史记录", use_container_width=True):
            st.session_state.pop("analysis_history", None)
            st.session_state.pop("latest_result", None)

    report_files = list_reports()
    if report_files:
        st.divider()
        st.header("📁 本地报告")
        for file_path in report_files:
            with file_path.open("rb") as handle:
                st.download_button(
                    label=f"下载 {file_path.name}",
                    data=handle.read(),
                    file_name=file_path.name,
                    key=f"report_{file_path.name}",
                )


symbol = st.text_input("请输入股票代码（例如：AAPL、TSLA）", help="仅支持单只股票分析。")

col_run, col_reset = st.columns([3, 1])
run_clicked = col_run.button("开始分析", type="primary", use_container_width=True)
reset_clicked = col_reset.button("重置结果", use_container_width=True)

if reset_clicked:
    st.session_state.pop("latest_result", None)


analysis_parameters = {
    "analysis_depth": depth_map[analysis_depth_display],
    "lookback_years": lookback_years,
    "forecast_horizon_quarters": forecast_quarters,
    "include_macro_analysis": include_macro,
    "include_benchmark_analysis": include_benchmark,
    "include_risk_assessment": include_risk,
    "generate_full_report": include_report,
    "preferred_currency": preferred_currency,
    "risk_preference": risk_map[risk_preference_display],
}

if custom_notes:
    analysis_parameters["user_notes"] = custom_notes


if run_clicked:
    if not symbol.strip():
        st.warning("请先输入有效的股票代码。")
    else:
        try:
            with st.spinner("正在执行股票分析流水线，请稍候..."):
                system_instance = load_system(env, version, model_id)
                result = system_instance.analyze_stock(normalize_symbol(symbol), **analysis_parameters)
                result = to_jsonable(result)

            st.session_state["latest_result"] = result

            history_entry = {
                "symbol": result.get("symbol", normalize_symbol(symbol)),
                "timestamp": result.get("timestamp", datetime.utcnow().isoformat()),
                "result": result,
            }
            st.session_state.setdefault("analysis_history", [])
            st.session_state["analysis_history"].insert(0, history_entry)
        except Exception as exc:  # noqa: BLE001
            st.error(f"分析过程中出现异常：{exc}")


if status_button and "latest_status" in st.session_state:
    with st.expander("系统状态", expanded=False):
        st.json(st.session_state["latest_status"])


if "latest_result" in st.session_state:
    render_result(st.session_state["latest_result"])
else:
    st.info("等待输入股票代码并启动分析。")


