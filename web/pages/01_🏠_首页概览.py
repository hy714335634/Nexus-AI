#!/usr/bin/env python3
"""
首页概览页面 - 显示平台统计、我的代理列表、热门模板等
"""

import streamlit as st
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from web.services.data_service import DataService
from web.services.state_manager import StateManager
from web.components.agent_card import render_agent_card
from web.utils.helpers import setup_page_config

def main():
    """首页概览主函数"""
    
    setup_page_config()
    
    st.title("🏠 首页概览")
    st.markdown("---")
    
    # 初始化服务
    data_service = DataService()
    state_manager = StateManager()
    
    # 平台统计仪表板
    st.subheader("📊 平台统计")
    
    try:
        projects_data = data_service.get_projects_status()
        
        # 统计指标
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                label="已构建Agent",
                value=projects_data.get('total_projects', 0),
                delta=None
            )
        
        with col2:
            st.metric(
                label="活跃项目",
                value=projects_data.get('active_projects', 0),
                delta=None
            )
        
        with col3:
            # 计算平均构建时间（示例数据）
            st.metric(
                label="平均构建时间",
                value="28分钟",
                delta=None
            )
        
        with col4:
            # 系统可用性
            system_metrics = projects_data.get('system_metrics', {})
            availability = 100 - system_metrics.get('cpu_usage', 0)
            st.metric(
                label="系统可用性",
                value=f"{availability:.1f}%",
                delta=None
            )
        
        st.markdown("---")
        
        # 我的代理列表
        st.subheader("🏆 我的Agent")
        
        projects = projects_data.get('projects', [])
        
        if projects:
            # 显示代理数量
            st.caption(f"共 {len(projects)} 个代理")
            
            # 代理列表
            for project in projects[:5]:  # 只显示前5个
                render_agent_card(project)
            
            # 查看全部按钮
            if len(projects) > 5:
                if st.button("查看全部 Agent →", key="view_all_agents"):
                    st.switch_page("pages/05_⚙️_代理管理.py")
        else:
            st.info("还没有创建任何代理。点击左侧 '🔨 创建代理' 开始创建您的第一个AI代理！")
        
        st.markdown("---")
        
        # 热门模板
        st.subheader("🔥 热门Agent模板")
        
        # 模板数据（示例）
        templates = [
            {
                "name": "智能客服机器人",
                "description": "适用于售后服务",
                "icon": "📞",
                "usage_count": 89
            },
            {
                "name": "数据分析助手", 
                "description": "报表自动生成",
                "icon": "📊",
                "usage_count": 67
            },
            {
                "name": "财务审核员",
                "description": "发票智能审核", 
                "icon": "💰",
                "usage_count": 45
            },
            {
                "name": "合规检查器",
                "description": "文档合规性检查",
                "icon": "📋", 
                "usage_count": 32
            }
        ]
        
        # 显示模板
        for template in templates:
            with st.container():
                col1, col2, col3 = st.columns([1, 4, 2])
                
                with col1:
                    st.markdown(f"## {template['icon']}")
                
                with col2:
                    st.markdown(f"**{template['name']}**")
                    st.caption(f"{template['description']} • 使用次数: {template['usage_count']}")
                
                with col3:
                    if st.button("使用模板", key=f"use_template_{template['name']}"):
                        # 设置模板信息到状态
                        st.session_state.selected_template = template
                        st.switch_page("pages/02_🔨_创建代理.py")
        
    except Exception as e:
        st.error(f"数据加载失败: {str(e)}")
        st.info("请检查系统配置或联系管理员")

if __name__ == "__main__":
    main()