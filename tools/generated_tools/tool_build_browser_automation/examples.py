#!/usr/bin/env python3
"""
浏览器自动化工具集使用示例

本文件包含所有5个工具函数的实际使用示例。
"""

import json
from browser_automation_tools import (
    browser_with_nova_act,
    browser_with_live_view_nova,
    browser_with_live_view_use,
    manage_browser_session,
    batch_extract_from_urls
)


# ============================================
# 示例 1: 基础 Nova Act 浏览器自动化
# ============================================

def example_browser_with_nova_act():
    """使用Nova Act在Google搜索并提取结果"""
    print("\n" + "="*60)
    print("示例 1: 基础 Nova Act 浏览器自动化")
    print("="*60)
    
    result = browser_with_nova_act(
        prompt="搜索'机器学习'并提取前3个搜索结果的标题",
        starting_page="https://www.google.com",
        nova_act_key="your-nova-act-api-key",  # 替换为实际API密钥
        region="us-west-2"
    )
    
    result_dict = json.loads(result)
    print(json.dumps(result_dict, ensure_ascii=False, indent=2))
    
    if result_dict["status"] == "success":
        print("\n✅ 操作成功完成！")
        print(f"响应: {result_dict['response']}")


# ============================================
# 示例 2: Nova Act + 实时视图
# ============================================

def example_browser_with_live_view_nova():
    """使用Nova Act自动化，并通过实时视图监控"""
    print("\n" + "="*60)
    print("示例 2: Nova Act + 实时视图")
    print("="*60)
    
    result = browser_with_live_view_nova(
        prompt="访问亚马逊首页，搜索'笔记本电脑'，并截图前5个产品",
        starting_page="https://www.amazon.com",
        nova_act_key="your-nova-act-api-key",  # 替换为实际API密钥
        region="us-west-2",
        viewer_port=8000,
        display_size="1080p",  # 支持: 720p, 900p, 1080p, 1440p
        open_browser=True  # 自动打开浏览器查看
    )
    
    result_dict = json.loads(result)
    print(json.dumps(result_dict, ensure_ascii=False, indent=2))
    
    if result_dict["status"] == "success":
        print(f"\n✅ 操作成功！实时视图: {result_dict['viewer_url']}")
        print("💡 提示: 打开浏览器访问实时视图URL查看操作过程")


# ============================================
# 示例 3: Browser Use AI 驱动自动化
# ============================================

def example_browser_with_live_view_use():
    """使用AI驱动的浏览器自动化执行复杂任务"""
    print("\n" + "="*60)
    print("示例 3: Browser Use AI 驱动自动化")
    print("="*60)
    
    result = browser_with_live_view_use(
        task="""
        在维基百科搜索'人工智能'，然后：
        1. 提取定义段落
        2. 找到'历史'章节
        3. 提取前3个重要历史事件
        """,
        region="us-west-2",
        viewer_port=8001,  # 使用不同端口避免冲突
        open_browser=True,
        model_id="anthropic.claude-3-5-sonnet-20240620-v1:0",
        timeout=1500  # 25分钟超时
    )
    
    result_dict = json.loads(result)
    print(json.dumps(result_dict, ensure_ascii=False, indent=2))
    
    if result_dict["status"] == "success":
        print(f"\n✅ AI任务完成！实时视图: {result_dict['viewer_url']}")


# ============================================
# 示例 4: 浏览器会话管理
# ============================================

def example_manage_browser_session():
    """管理浏览器会话的完整生命周期"""
    print("\n" + "="*60)
    print("示例 4: 浏览器会话管理")
    print("="*60)
    
    # 1. 创建会话
    print("\n1️⃣ 创建新会话...")
    create_result = manage_browser_session(
        action="create",
        region="us-west-2"
    )
    create_dict = json.loads(create_result)
    print(json.dumps(create_dict, ensure_ascii=False, indent=2))
    
    if create_dict["status"] == "success":
        session_id = create_dict["session_id"]
        print(f"\n✅ 会话创建成功: {session_id}")
        
        # 2. 获取WebSocket连接信息
        print("\n2️⃣ 获取WebSocket连接信息...")
        ws_result = manage_browser_session(
            action="get_ws_headers",
            session_id=session_id
        )
        ws_dict = json.loads(ws_result)
        print(f"WebSocket URL: {ws_dict.get('ws_url', 'N/A')}")
        
        # 3. 查询会话状态
        print("\n3️⃣ 查询会话状态...")
        status_result = manage_browser_session(
            action="get_status",
            session_id=session_id
        )
        status_dict = json.loads(status_result)
        print(f"会话状态: {status_dict.get('session_status', 'N/A')}")
        
        # 4. 列出所有会话
        print("\n4️⃣ 列出所有会话...")
        list_result = manage_browser_session(action="list_all")
        list_dict = json.loads(list_result)
        print(f"总会话数: {list_dict.get('total_sessions', 0)}")
        
        # 5. 停止会话
        print("\n5️⃣ 停止会话...")
        stop_result = manage_browser_session(
            action="stop",
            session_id=session_id
        )
        stop_dict = json.loads(stop_result)
        print(f"✅ {stop_dict.get('message', '会话已停止')}")


# ============================================
# 示例 5: 批量网页数据采集
# ============================================

def example_batch_extract_from_urls():
    """批量从多个URL采集数据"""
    print("\n" + "="*60)
    print("示例 5: 批量网页数据采集")
    print("="*60)
    
    # 准备URL列表
    urls = [
        "https://example.com",
        "https://www.wikipedia.org",
        "https://www.github.com"
    ]
    
    # 方法1: 使用Browser Use（推荐）
    print("\n📋 方法1: 使用Browser Use批量采集...")
    result = batch_extract_from_urls(
        urls=json.dumps(urls),
        extraction_prompt="提取页面标题和主要描述",
        method="browser_use",
        region="us-west-2",
        max_concurrent=2  # 并发数为2
    )
    
    result_dict = json.loads(result)
    print(json.dumps(result_dict, ensure_ascii=False, indent=2))
    
    if result_dict["status"] == "success":
        print(f"\n✅ 批量采集完成！")
        print(f"总数: {result_dict['total']}")
        print(f"成功: {result_dict['success']}")
        print(f"失败: {result_dict['failed']}")
        
        # 显示部分结果
        print("\n📊 采集结果示例:")
        for i, item in enumerate(result_dict['results'][:3], 1):
            print(f"\n{i}. {item['url']}")
            print(f"   状态: {item['status']}")
            if item['error']:
                print(f"   错误: {item['error']}")
    
    # 方法2: 使用Nova Act
    print("\n\n📋 方法2: 使用Nova Act批量采集...")
    result2 = batch_extract_from_urls(
        urls=json.dumps(urls[:2]),  # 测试前2个URL
        extraction_prompt="提取页面标题",
        method="nova_act",
        nova_act_key="your-nova-act-api-key",  # 替换为实际API密钥
        region="us-west-2",
        max_concurrent=2
    )
    
    result2_dict = json.loads(result2)
    print(json.dumps(result2_dict, ensure_ascii=False, indent=2))


# ============================================
# 高级示例: 组合使用多个工具
# ============================================

def example_advanced_workflow():
    """组合使用多个工具完成复杂工作流"""
    print("\n" + "="*60)
    print("高级示例: 组合工作流")
    print("="*60)
    
    # 1. 创建持久化会话
    print("\n1️⃣ 创建持久化会话...")
    session_result = manage_browser_session(action="create", region="us-west-2")
    session_dict = json.loads(session_result)
    
    if session_dict["status"] == "success":
        session_id = session_dict["session_id"]
        print(f"✅ 会话ID: {session_id}")
        
        # 2. 使用会话执行多个任务
        print("\n2️⃣ 执行任务1: 搜索产品...")
        task1_result = browser_with_nova_act(
            prompt="在亚马逊搜索'Python书籍'",
            starting_page="https://www.amazon.com",
            nova_act_key="your-api-key",
            region="us-west-2"
        )
        print("任务1完成")
        
        print("\n3️⃣ 执行任务2: 提取产品信息...")
        task2_result = browser_with_live_view_use(
            task="提取前5个产品的标题、价格和评分",
            region="us-west-2"
        )
        print("任务2完成")
        
        # 3. 清理会话
        print("\n4️⃣ 清理会话...")
        manage_browser_session(action="stop", session_id=session_id)
        print("✅ 工作流完成")


# ============================================
# 主函数
# ============================================

def main():
    """运行所有示例"""
    print("\n" + "="*60)
    print("  浏览器自动化工具集 - 使用示例")
    print("="*60)
    print("\n⚠️  注意: 运行示例前请：")
    print("1. 将 'your-nova-act-api-key' 替换为实际的Nova Act API密钥")
    print("2. 确保AWS凭证已配置（用于Bedrock）")
    print("3. 确保安装了所有依赖包（见 requirements.txt）")
    print("4. 某些功能需要Amazon DCV SDK支持")
    
    print("\n" + "="*60)
    input("按Enter键继续运行示例...")
    
    # 运行各个示例（取消注释以运行）
    # example_browser_with_nova_act()
    # example_browser_with_live_view_nova()
    # example_browser_with_live_view_use()
    example_manage_browser_session()
    # example_batch_extract_from_urls()
    # example_advanced_workflow()
    
    print("\n" + "="*60)
    print("  示例运行完成！")
    print("="*60)


if __name__ == "__main__":
    main()
