#!/usr/bin/env python3
"""
Nexus-AI Streamlit 前端主应用入口
"""

import streamlit as st
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 导入服务层
from web.services.state_manager import StateManager
from web.services.data_service import DataService
from web.utils.helpers import setup_page_config, load_custom_css

def main():
    """主应用入口"""
    
    # 设置页面配置
    setup_page_config()
    
    # 加载自定义样式
    load_custom_css()
    
    # 初始化状态管理器
    state_manager = StateManager()
    state_manager.init_session_state()
    
    # 初始化数据服务
    data_service = DataService()
    
    # 主页面内容
    st.title("🤖 Nexus-AI Platform")
    st.markdown("### 让AI帮你构建AI")
    st.markdown("从想法到实现，只需要一句话描述")
    
    # 显示欢迎信息
    st.info("👋 欢迎使用Nexus-AI平台！请从左侧导航栏选择功能模块。")
    
    # 快速统计信息
    col1, col2, col3 = st.columns(3)
    
    try:
        projects_data = data_service.get_projects_status()
        
        with col1:
            st.metric(
                label="📊 总项目数", 
                value=projects_data.get('total_projects', 0)
            )
        
        with col2:
            st.metric(
                label="🏃 活跃项目", 
                value=projects_data.get('active_projects', 0)
            )
        
        with col3:
            st.metric(
                label="✅ 系统状态", 
                value="正常"
            )
    
    except Exception as e:
        st.warning(f"数据加载中... {str(e)}")
    
    # 快速入门指导
    with st.expander("🎯 快速入门", expanded=False):
        st.markdown("""
        **开始使用Nexus-AI平台：**
        
        1. **🔨 创建代理** - 使用自然语言描述您的需求
        2. **📊 监控进度** - 实时查看代理构建过程
        3. **💬 代理对话** - 与构建完成的代理进行交互
        4. **⚙️ 代理管理** - 管理和监控您的代理系统
        
        **示例需求描述：**
        > "我需要一个客服代理，能够自动处理客户投诉，根据问题严重程度分配给不同的专家，并自动生成处理报告"
        """)

if __name__ == "__main__":
    main()