#!/usr/bin/env python3
"""
代理管理页面 - 管理和监控已部署的代理
"""

import streamlit as st
import sys
from pathlib import Path
from datetime import datetime

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from web.services.data_service import DataService
from web.services.agent_service import AgentService
from web.services.state_manager import StateManager
from web.utils.helpers import setup_page_config

def main():
    """代理管理主函数"""
    
    setup_page_config()
    
    st.title("⚙️ 代理管理")
    st.markdown("管理和监控您的AI代理系统")
    st.markdown("---")
    
    # 初始化服务
    data_service = DataService()
    agent_service = AgentService()
    state_manager = StateManager()
    
    try:
        # 获取项目数据
        projects_data = data_service.get_projects_status()
        projects = projects_data.get('projects', [])
        
        if not projects:
            st.info("暂无代理项目")
            
            if st.button("🔨 创建第一个代理"):
                st.switch_page("pages/02_🔨_创建代理.py")
            return
        
        # 检查是否有选中的项目
        selected_project_id = st.session_state.get('selected_project_id', None)
        
        if selected_project_id:
            # 显示特定项目的详细信息
            selected_project = next(
                (p for p in projects if p['id'] == selected_project_id), 
                None
            )
            
            if selected_project:
                render_project_details(selected_project, agent_service, data_service)
            else:
                st.error("未找到指定的项目")
                if st.button("返回项目列表"):
                    del st.session_state.selected_project_id
                    st.rerun()
        else:
            # 显示项目列表
            render_project_list(projects, data_service)
    
    except Exception as e:
        st.error(f"页面加载失败: {str(e)}")
        st.info("请检查系统状态或刷新页面")

def render_project_list(projects, data_service):
    """渲染项目列表"""
    
    st.subheader(f"📋 项目列表 ({len(projects)})")
    
    # 项目筛选和排序
    col1, col2, col3 = st.columns(3)
    
    with col1:
        status_filter = st.selectbox(
            "状态筛选",
            ["全部", "运行中", "构建中", "已停止", "错误", "需要更新"]
        )
    
    with col2:
        sort_by = st.selectbox(
            "排序方式",
            ["创建时间", "名称", "调用次数", "最后更新"]
        )
    
    with col3:
        sort_order = st.selectbox("排序顺序", ["降序", "升序"])
    
    # 应用筛选
    filtered_projects = projects
    if status_filter != "全部":
        status_map = {
            "运行中": "running",
            "构建中": "building", 
            "已停止": "stopped",
            "错误": "error",
            "需要更新": "needs_update"
        }
        filtered_projects = [
            p for p in projects 
            if p.get('status') == status_map.get(status_filter)
        ]
    
    # 应用排序
    reverse = sort_order == "降序"
    if sort_by == "创建时间":
        filtered_projects.sort(key=lambda x: x.get('created_at', ''), reverse=reverse)
    elif sort_by == "名称":
        filtered_projects.sort(key=lambda x: x.get('name', ''), reverse=reverse)
    elif sort_by == "调用次数":
        filtered_projects.sort(key=lambda x: x.get('metrics', {}).get('total_calls', 0), reverse=reverse)
    elif sort_by == "最后更新":
        filtered_projects.sort(key=lambda x: x.get('updated_at', ''), reverse=reverse)
    
    # 显示项目卡片
    for project in filtered_projects:
        with st.container():
            # 项目卡片
            col1, col2, col3, col4 = st.columns([3, 2, 2, 2])
            
            with col1:
                st.markdown(f"### {project['name']}")
                st.caption(project.get('description', '暂无描述'))
                
                # 状态指示器
                status = project.get('status', 'unknown')
                status_colors = {
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
                
                st.markdown(f"{status_colors.get(status, '⚪')} {status_text.get(status, '未知')}")
            
            with col2:
                st.markdown("**基本信息**")
                st.caption(f"创建: {project.get('created_at', '未知')}")
                st.caption(f"版本: {project.get('version', 'v1.0')}")
                st.caption(f"构建时间: {project.get('build_time', '未知')}")
            
            with col3:
                st.markdown("**性能指标**")
                metrics = project.get('metrics', {})
                st.caption(f"调用次数: {metrics.get('total_calls', 0)}")
                st.caption(f"成功率: {metrics.get('success_rate', 0)}%")
                st.caption(f"响应时间: {metrics.get('avg_response_time', '未知')}")
            
            with col4:
                st.markdown("**操作**")
                
                # 操作按钮
                if st.button("📊 详情", key=f"details_{project['id']}"):
                    st.session_state.selected_project_id = project['id']
                    st.rerun()
                
                if st.button("💬 对话", key=f"chat_{project['id']}"):
                    st.session_state.selected_agent = project['id']
                    st.switch_page("pages/04_💬_代理对话.py")
                
                # 状态控制按钮
                if status == 'running':
                    if st.button("⏸️ 停止", key=f"stop_{project['id']}"):
                        # 停止代理
                        try:
                            # 这里应该调用实际的停止逻辑
                            st.success("代理已停止")
                            st.rerun()
                        except Exception as e:
                            st.error(f"停止失败: {str(e)}")
                
                elif status == 'stopped':
                    if st.button("▶️ 启动", key=f"start_{project['id']}"):
                        # 启动代理
                        try:
                            # 这里应该调用实际的启动逻辑
                            st.success("代理已启动")
                            st.rerun()
                        except Exception as e:
                            st.error(f"启动失败: {str(e)}")
            
            st.markdown("---")

def render_project_details(project, agent_service, data_service):
    """渲染项目详细信息"""
    
    # 返回按钮
    if st.button("← 返回项目列表"):
        del st.session_state.selected_project_id
        st.rerun()
    
    st.markdown("---")
    
    # 项目标题和状态
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.title(project['name'])
        st.caption(project.get('description', '暂无描述'))
    
    with col2:
        status = project.get('status', 'unknown')
        if status == 'running':
            st.success("🟢 运行中")
        elif status == 'building':
            st.warning("🟡 构建中")
        elif status == 'error':
            st.error("🔴 错误")
        else:
            st.info(f"⚪ {status}")
    
    # 项目概览
    st.subheader("📊 项目概览")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("创建时间", project.get('created_at', '未知'))
    
    with col2:
        st.metric("构建耗时", project.get('build_time', '未知'))
    
    with col3:
        st.metric("当前版本", project.get('version', 'v1.0'))
    
    with col4:
        metrics = project.get('metrics', {})
        st.metric("调用次数", metrics.get('total_calls', 0))
    
    # 操作面板
    st.subheader("🎛️ 操作面板")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("💬 开始对话", type="primary"):
            st.session_state.selected_agent = project['id']
            st.switch_page("pages/04_💬_代理对话.py")
    
    with col2:
        if st.button("🔧 查看配置"):
            st.info("配置查看功能开发中...")
    
    with col3:
        if st.button("📋 查看日志"):
            # 显示日志管理界面
            render_log_management(project, agent_service)
    
    with col4:
        if st.button("🧪 测试功能"):
            st.info("功能测试开发中...")
    
    # 系统架构
    st.subheader("🏗️ 系统架构")
    
    agents = project.get('agents', [])
    if agents:
        st.markdown("**组件代理:**")
        
        for agent in agents:
            col1, col2, col3 = st.columns([2, 1, 1])
            
            with col1:
                st.markdown(f"• **{agent['name']}**")
                st.caption(f"类型: {agent.get('type', '未知')}")
            
            with col2:
                agent_status = agent.get('status', 'unknown')
                if agent_status == 'running':
                    st.success("运行中")
                elif agent_status == 'stopped':
                    st.warning("已停止")
                else:
                    st.info(agent_status)
            
            with col3:
                st.caption("操作")
    else:
        st.info("暂无组件代理信息")
    
    # 性能指标
    st.subheader("📈 性能指标")
    
    metrics = project.get('metrics', {})
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "总调用次数",
            metrics.get('total_calls', 0),
            delta=None
        )
    
    with col2:
        st.metric(
            "成功率",
            f"{metrics.get('success_rate', 0)}%",
            delta=None
        )
    
    with col3:
        st.metric(
            "平均响应时间",
            metrics.get('avg_response_time', '未知'),
            delta=None
        )
    
    # 构建历史
    st.subheader("📝 构建历史")
    
    build_history = project.get('build_history', [])
    
    if build_history:
        for entry in build_history:
            col1, col2, col3 = st.columns([2, 1, 1])
            
            with col1:
                st.markdown(f"**{entry['stage']}**")
            
            with col2:
                entry_status = entry.get('status', 'unknown')
                if entry_status == 'completed':
                    st.success("✅ 已完成")
                elif entry_status == 'failed':
                    st.error("❌ 失败")
                else:
                    st.info(f"🔄 {entry_status}")
            
            with col3:
                st.caption(f"用时: {entry.get('duration', '未知')}")
                st.caption(f"时间: {entry.get('timestamp', '未知')}")
    else:
        st.info("暂无构建历史记录")

def render_log_management(project, agent_service):
    """渲染日志管理界面"""
    
    st.subheader("📋 日志管理")
    
    # 日志文件管理标签页
    log_tab1, log_tab2, log_tab3 = st.tabs(["🏗️ 构建日志", "💬 运行日志", "🧹 日志清理"])
    
    with log_tab1:
        st.markdown("### 构建日志文件")
        
        # 列出所有构建日志文件
        logs_dir = agent_service.logs_dir
        build_logs = list(logs_dir.glob("build_*.log"))
        
        if build_logs:
            # 按修改时间排序
            build_logs.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            
            for log_file in build_logs:
                stat = log_file.stat()
                file_size_mb = round(stat.st_size / 1024 / 1024, 2)
                modified_time = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                
                col1, col2, col3, col4 = st.columns([3, 1, 1, 2])
                
                with col1:
                    st.markdown(f"**{log_file.name}**")
                    st.caption(f"修改时间: {modified_time}")
                
                with col2:
                    st.metric("大小", f"{file_size_mb} MB")
                
                with col3:
                    if st.button("👁️ 查看", key=f"view_{log_file.name}"):
                        # 显示日志内容
                        try:
                            with open(log_file, 'r', encoding='utf-8') as f:
                                log_content = f.read()
                            
                            # 使用HTML显示日志并自动滚动到底部
                            container_id = f"log_view_{log_file.name.replace('.', '_').replace('-', '_')}"
                            
                            log_html = f"""
                            <div style="margin-bottom: 10px;">
                                <strong>日志内容 - {log_file.name}</strong>
                            </div>
                            <div id="{container_id}" style="
                                height: 400px; 
                                overflow-y: auto; 
                                background-color: #f0f2f6; 
                                padding: 10px; 
                                border-radius: 5px;
                                font-family: 'Courier New', monospace;
                                font-size: 12px;
                                white-space: pre-wrap;
                                border: 1px solid #ddd;
                            ">{log_content}</div>
                            <script>
                                // 自动滚动到底部
                                setTimeout(function() {{
                                    var container = document.getElementById('{container_id}');
                                    if (container) {{
                                        container.scrollTop = container.scrollHeight;
                                    }}
                                }}, 100);
                            </script>
                            """
                            
                            st.html(log_html, height=450)
                        except Exception as e:
                            st.error(f"读取日志文件失败: {str(e)}")
                
                with col4:
                    # 下载按钮
                    try:
                        with open(log_file, 'r', encoding='utf-8') as f:
                            log_content = f.read()
                        
                        st.download_button(
                            label="💾 下载",
                            data=log_content,
                            file_name=log_file.name,
                            mime="text/plain",
                            key=f"download_{log_file.name}"
                        )
                    except Exception as e:
                        st.error(f"准备下载失败: {str(e)}")
        else:
            st.info("暂无构建日志文件")
    
    with log_tab2:
        st.markdown("### 代理运行日志")
        
        # 列出代理调用日志
        agent_logs = list(logs_dir.glob("agent_call_*.log"))
        
        if agent_logs:
            # 按修改时间排序
            agent_logs.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            
            # 只显示最近的20个日志文件
            recent_logs = agent_logs[:20]
            
            for log_file in recent_logs:
                stat = log_file.stat()
                file_size_mb = round(stat.st_size / 1024 / 1024, 2)
                modified_time = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                
                col1, col2, col3, col4 = st.columns([3, 1, 1, 2])
                
                with col1:
                    st.markdown(f"**{log_file.name}**")
                    st.caption(f"修改时间: {modified_time}")
                
                with col2:
                    st.metric("大小", f"{file_size_mb} MB")
                
                with col3:
                    if st.button("👁️ 查看", key=f"view_agent_{log_file.name}"):
                        # 显示日志内容
                        try:
                            with open(log_file, 'r', encoding='utf-8') as f:
                                log_content = f.read()
                            
                            # 使用HTML显示日志并自动滚动到底部
                            container_id = f"agent_log_view_{log_file.name.replace('.', '_').replace('-', '_')}"
                            
                            log_html = f"""
                            <div style="margin-bottom: 10px;">
                                <strong>代理调用日志 - {log_file.name}</strong>
                            </div>
                            <div id="{container_id}" style="
                                height: 400px; 
                                overflow-y: auto; 
                                background-color: #f0f2f6; 
                                padding: 10px; 
                                border-radius: 5px;
                                font-family: 'Courier New', monospace;
                                font-size: 12px;
                                white-space: pre-wrap;
                                border: 1px solid #ddd;
                            ">{log_content}</div>
                            <script>
                                // 自动滚动到底部
                                setTimeout(function() {{
                                    var container = document.getElementById('{container_id}');
                                    if (container) {{
                                        container.scrollTop = container.scrollHeight;
                                    }}
                                }}, 100);
                            </script>
                            """
                            
                            st.html(log_html, height=450)
                        except Exception as e:
                            st.error(f"读取日志文件失败: {str(e)}")
                
                with col4:
                    # 下载按钮
                    try:
                        with open(log_file, 'r', encoding='utf-8') as f:
                            log_content = f.read()
                        
                        st.download_button(
                            label="💾 下载",
                            data=log_content,
                            file_name=log_file.name,
                            mime="text/plain",
                            key=f"download_agent_{log_file.name}"
                        )
                    except Exception as e:
                        st.error(f"准备下载失败: {str(e)}")
            
            if len(agent_logs) > 20:
                st.info(f"显示最近20个日志文件，共有 {len(agent_logs)} 个日志文件")
        else:
            st.info("暂无代理运行日志")
    
    with log_tab3:
        st.markdown("### 日志清理")
        
        # 日志统计信息
        all_logs = list(logs_dir.glob("*.log"))
        total_size = sum(log.stat().st_size for log in all_logs)
        total_size_mb = round(total_size / 1024 / 1024, 2)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("日志文件数量", len(all_logs))
        
        with col2:
            st.metric("总大小", f"{total_size_mb} MB")
        
        with col3:
            st.metric("日志目录", str(logs_dir))
        
        st.markdown("---")
        
        # 清理选项
        st.markdown("**清理选项:**")
        
        days_to_keep = st.slider(
            "保留最近几天的日志",
            min_value=1,
            max_value=30,
            value=7,
            help="删除指定天数之前的日志文件"
        )
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🧹 清理旧日志", type="primary"):
                try:
                    result = agent_service.cleanup_old_logs(days_to_keep)
                    if 'error' in result:
                        st.error(f"清理失败: {result['error']}")
                    else:
                        st.success(f"✅ {result['message']}")
                        st.rerun()
                except Exception as e:
                    st.error(f"清理操作失败: {str(e)}")
        
        with col2:
            if st.button("🔄 刷新统计"):
                st.rerun()
        
        # 警告信息
        st.warning("⚠️ 清理操作不可逆，请确保不需要这些日志文件后再执行清理")

def render_project_logs(project):
    """渲染项目日志（保留原有功能）"""
    
    with st.expander("📋 项目日志", expanded=True):
        # 这里应该从实际的日志文件中读取
        sample_logs = [
            {"timestamp": "2025-01-13 15:45:23", "level": "INFO", "message": "代理系统启动成功"},
            {"timestamp": "2025-01-13 15:44:12", "level": "INFO", "message": "加载配置文件完成"},
            {"timestamp": "2025-01-13 15:43:45", "level": "SUCCESS", "message": "部署完成，代理系统上线"},
            {"timestamp": "2025-01-13 15:42:30", "level": "INFO", "message": "工具集成完成"},
        ]
        
        for log in sample_logs:
            level = log['level']
            if level == 'ERROR':
                st.error(f"[{log['timestamp']}] {log['message']}")
            elif level == 'WARNING':
                st.warning(f"[{log['timestamp']}] {log['message']}")
            elif level == 'SUCCESS':
                st.success(f"[{log['timestamp']}] {log['message']}")
            else:
                st.info(f"[{log['timestamp']}] {log['message']}")

if __name__ == "__main__":
    main()