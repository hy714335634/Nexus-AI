#!/usr/bin/env python3
"""
代理对话页面 - 与构建完成的代理进行交互
"""

import streamlit as st
import sys
from pathlib import Path
from datetime import datetime

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from web.services.agent_service import AgentService
from web.services.data_service import DataService
from web.services.state_manager import StateManager
from web.components.chat_interface import (
    render_enhanced_chat_interface, 
    render_chat_session_manager,
    render_chat_analytics,
    render_chat_sidebar
)
from web.utils.helpers import setup_page_config

def main():
    """代理对话主函数"""
    
    setup_page_config()
    
    st.title("💬 代理对话")
    st.markdown("与您的AI代理进行实时交互")
    st.markdown("---")
    
    # 初始化服务
    agent_service = AgentService()
    data_service = DataService()
    state_manager = StateManager()
    
    # 获取可用的代理列表 - 直接扫描agents目录
    try:
        from web.components.chat_interface import get_available_agents
        available_agents = get_available_agents()
        
        if not available_agents:
            st.warning("暂无可用的代理")
            st.info("请先创建并部署一个代理")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("🔨 创建新代理"):
                    st.switch_page("pages/02_🔨_创建代理.py")
            
            with col2:
                if st.button("🔄 刷新代理列表"):
                    # 手动刷新代理列表
                    try:
                        if data_service.refresh_projects_from_agents():
                            st.success("✅ 代理列表已刷新")
                            st.rerun()
                        else:
                            st.error("❌ 刷新失败")
                    except Exception as e:
                        st.error(f"刷新失败: {str(e)}")
            return
        
        # 代理选择器
        st.subheader("🤖 选择代理")
        
        # 从URL参数或会话状态获取选中的代理
        selected_agent_id = st.session_state.get('selected_agent', None)
        
        # 代理选择下拉框
        agent_options = {agent['name']: agent['id'] for agent in available_agents}
        
        selected_agent_name = st.selectbox(
            "选择要对话的代理",
            options=list(agent_options.keys()),
            index=0 if not selected_agent_id else (
                list(agent_options.values()).index(selected_agent_id) 
                if selected_agent_id in agent_options.values() else 0
            )
        )
        
        selected_agent_id = agent_options[selected_agent_name]
        selected_agent = next(agent for agent in available_agents if agent['id'] == selected_agent_id)
        
        # 保存选中的代理到会话状态
        st.session_state.selected_agent = selected_agent_id
        
        # 显示代理信息
        with st.expander("ℹ️ 代理信息", expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown(f"**名称:** {selected_agent['name']}")
                st.markdown(f"**描述:** {selected_agent.get('description', '暂无描述')}")
                st.markdown(f"**状态:** {selected_agent['status']}")
            
            with col2:
                st.markdown(f"**创建时间:** {selected_agent.get('created_at', '未知')}")
                st.markdown(f"**版本:** {selected_agent.get('version', 'v1.0')}")
                
                metrics = selected_agent.get('metrics', {})
                st.markdown(f"**调用次数:** {metrics.get('total_calls', 0)}")
        
        st.markdown("---")
        
        # 聊天界面选项卡
        tab1, tab2, tab3 = st.tabs(["💭 对话", "💾 会话管理", "📊 分析"])
        
        with tab1:
            # 使用增强的聊天界面
            render_enhanced_chat_interface(selected_agent_id, selected_agent['name'])
        
        with tab2:
            # 会话管理
            render_chat_session_manager(selected_agent_id)
        
        with tab3:
            # 对话分析
            render_chat_analytics(selected_agent_id)
        
        # 侧边栏聊天设置
        render_chat_sidebar(selected_agent_id)
    
    except Exception as e:
        st.error(f"页面加载失败: {str(e)}")
        st.info("请检查系统状态或刷新页面")

if __name__ == "__main__":
    main()