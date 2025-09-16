#!/usr/bin/env python3
"""
创建代理页面 - 自然语言输入和模板选择
"""

import streamlit as st
import sys
from pathlib import Path
import uuid
from datetime import datetime

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from web.services.agent_service import AgentService
from web.services.state_manager import StateManager
from web.utils.helpers import setup_page_config

def main():
    """创建代理主函数"""
    
    setup_page_config()
    
    st.title("🔨 创建代理")
    st.markdown("通过自然语言描述您的需求，让AI帮您构建专业的代理系统")
    st.markdown("---")
    
    # 初始化服务
    agent_service = AgentService()
    state_manager = StateManager()
    
    # 检查是否有选中的模板
    selected_template = st.session_state.get('selected_template', None)
    
    if selected_template:
        st.success(f"已选择模板: {selected_template['name']}")
        st.info("您可以基于此模板进行定制，或者清空重新开始")
        
        if st.button("清空模板选择"):
            del st.session_state.selected_template
            st.rerun()
    
    # 创建两个标签页
    tab1, tab2 = st.tabs(["💬 自然语言创建", "📋 模板选择"])
    
    with tab1:
        st.subheader("描述您的需求")
        
        # 示例提示
        with st.expander("💡 需求描述示例", expanded=False):
            st.markdown("""
            **好的需求描述应该包含：**
            - 代理的主要功能和目标
            - 处理的数据类型和来源
            - 期望的输出格式
            - 特殊的业务规则或约束
            
            **示例：**
            > "我需要一个客服代理，能够自动处理客户投诉，根据问题严重程度分配给不同的专家，并自动生成处理报告。需要支持邮件和在线聊天两种渠道，能够识别VIP客户并优先处理。"
            
            > "创建一个数据分析代理，能够读取Excel销售数据，自动生成月度销售报告，包含趋势分析、区域对比和产品排名。报告需要支持图表可视化和PDF导出。"
            """)
        
        # 需求输入区域
        user_input = st.text_area(
            label="📝 详细描述您的需求",
            placeholder="请详细描述您希望创建的AI代理的功能、用途和要求...\n\n例如：我需要一个客服代理，能够自动处理客户投诉，根据问题严重程度分配给不同的专家，并自动生成处理报告",
            height=200,
            value=selected_template.get('default_prompt', '') if selected_template else ''
        )
        
        # 高级选项
        with st.expander("⚙️ 高级选项", expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                project_name = st.text_input(
                    "项目名称（可选）",
                    placeholder="如不填写将自动生成"
                )
            
            with col2:
                priority = st.selectbox(
                    "构建优先级",
                    ["标准", "高优先级", "低优先级"],
                    index=0
                )
        
        # 创建按钮
        col1, col2 = st.columns([3, 1])
        
        with col1:
            if st.button("🚀 开始构建", type="primary", use_container_width=True):
                if user_input.strip():
                    try:
                        # 生成任务ID
                        task_id = str(uuid.uuid4())
                        
                        # 保存任务信息到状态
                        st.session_state.current_build_task = {
                            'task_id': task_id,
                            'user_input': user_input,
                            'project_name': project_name or f"项目_{task_id[:8]}",
                            'status': 'started',
                            'start_time': datetime.now().isoformat()
                        }
                        
                    
                        # 实时显示构建日志
                        st.info("🔄 开始构建，实时显示日志...")
                        
                        # 创建日志显示区域
                        log_tab1, log_tab2 = st.tabs(["📺 实时日志", "📄 完整日志"])
                        
                        with log_tab1:
                            log_container = st.empty()
                            log_lines = []
                            
                            # 流式显示构建日志
                            try:
                                for log_line in agent_service.stream_build_workflow(
                                    user_input=user_input,
                                    project_name=project_name,
                                    task_id=task_id
                                ):
                                    log_lines.append(log_line)
                                    # 显示最近的10000行日志用于实时查看
                                    display_lines = log_lines[-10000:] if len(log_lines) > 10000 else log_lines
                                    log_text = "\n".join(display_lines)
                                    
                                    # 添加日志统计信息
                                    log_info = f"📊 总日志行数: {len(log_lines)} | 显示最近: {len(display_lines)} 行"
                                    if len(log_lines) > 10000:
                                        log_info += f" | ⚠️ 仅显示最近10000行，完整日志请查看'完整日志'标签页"
                                    
                                    log_container.markdown(f"**{log_info}**")
                                    
                                    # 使用code块显示日志，并在末尾添加标记来"推动"滚动到底部
                                    # 在日志末尾添加一个特殊标记，让用户更容易看到最新内容
                                    log_with_marker = log_text + "\n\n" + "="*50 + " 最新日志 " + "="*50
                                    
                                    log_container.code(log_with_marker, language="text")
                                
                                st.success("✅ 构建完成！")
                                
                                # 显示日志文件信息
                                log_file_info = agent_service.get_log_file_info(task_id)
                                if log_file_info.get('exists'):
                                    st.info(f"📄 完整日志已保存到: `{log_file_info['path']}`")
                                    st.info(f"📊 日志文件大小: {log_file_info['size_mb']} MB ({log_file_info['size']} 字节)")
                                
                            except Exception as e:
                                st.error(f"构建过程中出现错误: {str(e)}")
                                # 仍然显示已收集的日志
                                if log_lines:
                                    st.text_area("构建日志（部分）", value="\n".join(log_lines), height=300)
                        
                        with log_tab2:
                            if st.button("🔄 刷新完整日志", key="refresh_full_log"):
                                st.rerun()
                            
                            # 显示完整日志
                            if 'current_build_task' in st.session_state:
                                current_task_id = st.session_state.current_build_task.get('task_id')
                                if current_task_id:
                                    full_logs = agent_service.get_full_logs(current_task_id)
                                    log_file_info = agent_service.get_log_file_info(current_task_id)
                                    
                                    if log_file_info.get('exists'):
                                        st.markdown(f"**📄 日志文件:** `{log_file_info['path']}`")
                                        st.markdown(f"**📊 文件大小:** {log_file_info['size_mb']} MB")
                                        st.markdown(f"**🕒 创建时间:** {log_file_info['created_time']}")
                                        st.markdown(f"**🕒 修改时间:** {log_file_info['modified_time']}")
                                        
                                        # 显示完整日志内容
                                        st.text_area(
                                            "完整构建日志",
                                            value=full_logs,
                                            height=500,
                                            disabled=True,
                                            label_visibility="collapsed"
                                        )
                                        
                                        # 提供下载选项
                                        st.download_button(
                                            label="💾 下载日志文件",
                                            data=full_logs,
                                            file_name=f"build_log_{current_task_id[:8]}.log",
                                            mime="text/plain"
                                        )
                                    else:
                                        st.warning("日志文件不存在或已被清理")
                                else:
                                    st.info("没有当前构建任务的日志")
                            else:
                                st.info("请先开始构建以查看完整日志")
                        
                        # 提供跳转选项
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            if st.button("💬 开始对话", type="primary"):
                                st.switch_page("pages/04_💬_代理对话.py")
                        
                        with col2:
                            if st.button("🔄 刷新代理列表"):
                                # 手动刷新项目状态
                                try:
                                    from web.services.data_service import DataService
                                    data_service = DataService()
                                    if data_service.refresh_projects_from_agents():
                                        st.success("✅ 代理列表已刷新")
                                        st.rerun()
                                    else:
                                        st.error("❌ 刷新失败")
                                except Exception as e:
                                    st.error(f"刷新失败: {str(e)}")
                        
                    except Exception as e:
                        st.error(f"启动构建失败: {str(e)}")
                        st.info("请检查系统配置或稍后重试")
                else:
                    st.warning("请先描述您的需求")
        
        with col2:
            if st.button("📋 选择模板", use_container_width=True):
                # 切换到模板选择标签页
                st.session_state.active_tab = "template"
                st.rerun()
    
    with tab2:
        st.subheader("选择预置模板")
        st.caption("基于成功案例的预置模板，快速开始您的代理创建")
        
        # 模板分类
        template_categories = {
            "客户服务": [
                {
                    "name": "智能客服机器人",
                    "description": "自动处理客户咨询，支持多渠道接入",
                    "icon": "📞",
                    "features": ["自动回复", "问题分类", "人工转接"],
                    "default_prompt": "创建一个智能客服代理，能够自动回复常见问题，对复杂问题进行分类并转接给相应的人工客服。"
                },
                {
                    "name": "投诉处理系统",
                    "description": "智能处理客户投诉，自动分级和分配",
                    "icon": "📝",
                    "features": ["投诉分类", "优先级判断", "自动分配"],
                    "default_prompt": "创建一个投诉处理代理，能够自动分析投诉内容，判断严重程度，分配给合适的处理专家，并生成处理报告。"
                }
            ],
            "数据分析": [
                {
                    "name": "销售数据分析师",
                    "description": "自动分析销售数据，生成报告和洞察",
                    "icon": "📊",
                    "features": ["数据清洗", "趋势分析", "报告生成"],
                    "default_prompt": "创建一个销售数据分析代理，能够读取销售数据，进行趋势分析，生成包含图表的月度销售报告。"
                },
                {
                    "name": "财务审核助手",
                    "description": "智能审核财务单据，检查合规性",
                    "icon": "💰",
                    "features": ["单据识别", "合规检查", "异常标记"],
                    "default_prompt": "创建一个财务审核代理，能够自动审核发票和财务单据，检查合规性，标记异常项目。"
                }
            ]
        }
        
        # 显示模板分类
        for category, templates in template_categories.items():
            st.markdown(f"### {category}")
            
            for template in templates:
                with st.container():
                    col1, col2, col3 = st.columns([1, 5, 2])
                    
                    with col1:
                        st.markdown(f"## {template['icon']}")
                    
                    with col2:
                        st.markdown(f"**{template['name']}**")
                        st.caption(template['description'])
                        
                        # 显示特性标签
                        feature_tags = " • ".join([f"`{feature}`" for feature in template['features']])
                        st.markdown(f"特性: {feature_tags}")
                    
                    with col3:
                        if st.button("使用此模板", key=f"template_{template['name']}"):
                            # 设置选中的模板
                            st.session_state.selected_template = template
                            st.success(f"已选择: {template['name']}")
                            st.rerun()
                
                st.markdown("---")

if __name__ == "__main__":
    main()