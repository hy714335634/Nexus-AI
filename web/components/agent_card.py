#!/usr/bin/env python3
"""
代理卡片组件 - 显示代理信息的可复用UI组件
"""

import streamlit as st
from typing import Dict
from datetime import datetime

def render_agent_card(agent_info: Dict) -> None:
    """渲染代理信息卡片"""
    
    with st.container():
        # 创建卡片样式的容器
        with st.container():
            col1, col2, col3 = st.columns([3, 1, 1])
            
            with col1:
                # 代理名称和描述
                st.subheader(agent_info.get('name', '未知代理'))
                st.caption(agent_info.get('description', '暂无描述'))
                
                # 显示创建时间
                created_at = agent_info.get('created_at', '')
                if created_at:
                    try:
                        # 格式化时间显示
                        dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                        formatted_time = dt.strftime('%Y-%m-%d %H:%M')
                        st.caption(f"创建时间: {formatted_time}")
                    except:
                        st.caption(f"创建时间: {created_at}")
            
            with col2:
                # 状态指示器
                status = agent_info.get('status', 'unknown')
                status_colors = {
                    'running': 'success',
                    'building': 'warning', 
                    'stopped': 'info',
                    'error': 'error',
                    'needs_update': 'warning'
                }
                
                status_text = {
                    'running': '🟢 运行中',
                    'building': '🟡 构建中',
                    'stopped': '⚪ 已停止', 
                    'error': '🔴 错误',
                    'needs_update': '🟠 需要更新'
                }
                
                color = status_colors.get(status, 'info')
                text = status_text.get(status, f'⚪ {status}')
                
                if color == 'success':
                    st.success(text)
                elif color == 'warning':
                    st.warning(text)
                elif color == 'error':
                    st.error(text)
                else:
                    st.info(text)
                
                # 显示版本信息
                version = agent_info.get('version', 'v1.0')
                st.caption(f"版本: {version}")
            
            with col3:
                # 操作按钮
                agent_id = agent_info.get('id', '')
                
                # 对话按钮
                if st.button("💬 对话", key=f"chat_{agent_id}", help="与代理开始对话"):
                    st.session_state.selected_agent = agent_id
                    st.switch_page("pages/04_💬_代理对话.py")
                
                # 管理按钮
                if st.button("⚙️ 管理", key=f"manage_{agent_id}", help="查看代理详情和管理"):
                    st.session_state.selected_project_id = agent_id
                    st.switch_page("pages/05_⚙️_代理管理.py")
        
        # 性能指标（可选显示）
        metrics = agent_info.get('metrics', {})
        if metrics and any(metrics.values()):
            with st.expander("📊 性能指标", expanded=False):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    total_calls = metrics.get('total_calls', 0)
                    st.metric("调用次数", total_calls)
                
                with col2:
                    success_rate = metrics.get('success_rate', 0)
                    st.metric("成功率", f"{success_rate}%")
                
                with col3:
                    avg_response_time = metrics.get('avg_response_time', '未知')
                    st.metric("响应时间", avg_response_time)
        
        # 分隔线
        st.markdown("---")

def render_agent_grid(agents: list, columns: int = 2) -> None:
    """以网格形式渲染多个代理卡片"""
    
    if not agents:
        st.info("暂无代理")
        return
    
    # 计算行数
    rows = (len(agents) + columns - 1) // columns
    
    for row in range(rows):
        cols = st.columns(columns)
        
        for col_idx in range(columns):
            agent_idx = row * columns + col_idx
            
            if agent_idx < len(agents):
                with cols[col_idx]:
                    render_compact_agent_card(agents[agent_idx])

def render_compact_agent_card(agent_info: Dict) -> None:
    """渲染紧凑版代理卡片（用于网格显示）"""
    
    with st.container():
        # 代理名称
        st.markdown(f"### {agent_info.get('name', '未知代理')}")
        
        # 状态
        status = agent_info.get('status', 'unknown')
        status_icons = {
            'running': '🟢',
            'building': '🟡',
            'stopped': '⚪',
            'error': '🔴',
            'needs_update': '🟠'
        }
        
        status_text = {
            'running': '运行中',
            'building': '构建中',
            'stopped': '已停止',
            'error': '错误',
            'needs_update': '需要更新'
        }
        
        icon = status_icons.get(status, '⚪')
        text = status_text.get(status, status)
        st.markdown(f"{icon} {text}")
        
        # 描述
        description = agent_info.get('description', '暂无描述')
        if len(description) > 50:
            description = description[:50] + "..."
        st.caption(description)
        
        # 操作按钮
        agent_id = agent_info.get('id', '')
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("💬", key=f"chat_compact_{agent_id}", help="对话"):
                st.session_state.selected_agent = agent_id
                st.switch_page("pages/04_💬_代理对话.py")
        
        with col2:
            if st.button("⚙️", key=f"manage_compact_{agent_id}", help="管理"):
                st.session_state.selected_project_id = agent_id
                st.switch_page("pages/05_⚙️_代理管理.py")

def render_agent_list_item(agent_info: Dict, show_actions: bool = True) -> None:
    """渲染列表项形式的代理信息"""
    
    col1, col2, col3 = st.columns([4, 2, 2] if show_actions else [6, 2, 0])
    
    with col1:
        # 状态指示器 + 名称
        status = agent_info.get('status', 'unknown')
        status_icons = {
            'running': '🟢',
            'building': '🟡',
            'stopped': '⚪',
            'error': '🔴',
            'needs_update': '🟠'
        }
        
        icon = status_icons.get(status, '⚪')
        name = agent_info.get('name', '未知代理')
        st.markdown(f"{icon} **{name}**")
        
        # 描述
        description = agent_info.get('description', '暂无描述')
        st.caption(description)
    
    with col2:
        # 基本信息
        metrics = agent_info.get('metrics', {})
        total_calls = metrics.get('total_calls', 0)
        
        if total_calls > 0:
            st.caption(f"调用: {total_calls}次")
        else:
            st.caption("暂未使用")
        
        # 最后更新时间
        updated_at = agent_info.get('updated_at', '')
        if updated_at:
            try:
                dt = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
                formatted_time = dt.strftime('%m-%d %H:%M')
                st.caption(f"更新: {formatted_time}")
            except:
                st.caption("更新: 未知")
    
    if show_actions:
        with col3:
            # 快速操作
            agent_id = agent_info.get('id', '')
            
            # 创建两个小按钮
            btn_col1, btn_col2 = st.columns(2)
            
            with btn_col1:
                if st.button("💬", key=f"chat_list_{agent_id}", help="对话"):
                    st.session_state.selected_agent = agent_id
                    st.switch_page("pages/04_💬_代理对话.py")
            
            with btn_col2:
                if st.button("⚙️", key=f"manage_list_{agent_id}", help="管理"):
                    st.session_state.selected_project_id = agent_id
                    st.switch_page("pages/05_⚙️_代理管理.py")

def render_agent_status_badge(status: str) -> None:
    """渲染代理状态徽章"""
    
    status_config = {
        'running': {'color': 'success', 'icon': '🟢', 'text': '运行中'},
        'building': {'color': 'warning', 'icon': '🟡', 'text': '构建中'},
        'stopped': {'color': 'info', 'icon': '⚪', 'text': '已停止'},
        'error': {'color': 'error', 'icon': '🔴', 'text': '错误'},
        'needs_update': {'color': 'warning', 'icon': '🟠', 'text': '需要更新'}
    }
    
    config = status_config.get(status, {'color': 'info', 'icon': '⚪', 'text': status})
    
    # 使用Streamlit的状态显示
    if config['color'] == 'success':
        st.success(f"{config['icon']} {config['text']}")
    elif config['color'] == 'warning':
        st.warning(f"{config['icon']} {config['text']}")
    elif config['color'] == 'error':
        st.error(f"{config['icon']} {config['text']}")
    else:
        st.info(f"{config['icon']} {config['text']}")

def render_agent_metrics_summary(metrics: Dict) -> None:
    """渲染代理性能指标摘要"""
    
    if not metrics:
        st.caption("暂无性能数据")
        return
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        total_calls = metrics.get('total_calls', 0)
        st.metric("调用次数", total_calls, delta=None)
    
    with col2:
        success_rate = metrics.get('success_rate', 0)
        st.metric("成功率", f"{success_rate}%", delta=None)
    
    with col3:
        avg_response_time = metrics.get('avg_response_time', '未知')
        st.metric("响应时间", avg_response_time, delta=None)