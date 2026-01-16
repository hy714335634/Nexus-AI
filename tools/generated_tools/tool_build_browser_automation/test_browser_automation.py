#!/usr/bin/env python3
"""
浏览器自动化工具集测试脚本

测试所有5个工具函数的基本功能和错误处理。
"""

import json
import sys
from browser_automation_tools import (
    browser_with_nova_act,
    browser_with_live_view_nova,
    browser_with_live_view_use,
    manage_browser_session,
    batch_extract_from_urls
)
from rich.console import Console

console = Console()


def test_browser_with_nova_act():
    """测试基础Nova Act浏览器自动化"""
    console.print("\n[bold cyan]测试 1: browser_with_nova_act[/bold cyan]")
    
    # 测试参数验证
    console.print("[yellow]测试参数验证...[/yellow]")
    result = browser_with_nova_act("", "https://google.com", "test-key")
    result_dict = json.loads(result)
    assert result_dict["status"] == "error", "应该返回参数错误"
    console.print("[green]✅ 参数验证测试通过[/green]")
    
    # 注意：实际功能测试需要有效的API密钥和AWS环境
    console.print("[yellow]⚠️  实际功能测试需要有效的Nova Act API密钥[/yellow]")


def test_browser_with_live_view_nova():
    """测试带实时视图的Nova Act自动化"""
    console.print("\n[bold cyan]测试 2: browser_with_live_view_nova[/bold cyan]")
    
    # 测试显示尺寸验证
    console.print("[yellow]测试显示尺寸验证...[/yellow]")
    result = browser_with_live_view_nova(
        "test", "https://google.com", "test-key", display_size="invalid"
    )
    result_dict = json.loads(result)
    assert result_dict["status"] == "error", "应该返回显示尺寸错误"
    assert "720p" in result_dict["message"], "错误消息应包含有效尺寸"
    console.print("[green]✅ 显示尺寸验证测试通过[/green]")


def test_browser_with_live_view_use():
    """测试Browser Use AI驱动自动化"""
    console.print("\n[bold cyan]测试 3: browser_with_live_view_use[/bold cyan]")
    
    # 测试任务参数验证
    console.print("[yellow]测试任务参数验证...[/yellow]")
    result = browser_with_live_view_use("")
    result_dict = json.loads(result)
    assert result_dict["status"] == "error", "应该返回任务参数错误"
    console.print("[green]✅ 任务参数验证测试通过[/green]")
    
    # 测试超时参数验证
    console.print("[yellow]测试超时参数验证...[/yellow]")
    result = browser_with_live_view_use("test task", timeout=-1)
    result_dict = json.loads(result)
    assert result_dict["status"] == "error", "应该返回超时参数错误"
    console.print("[green]✅ 超时参数验证测试通过[/green]")


def test_manage_browser_session():
    """测试浏览器会话管理器"""
    console.print("\n[bold cyan]测试 4: manage_browser_session[/bold cyan]")
    
    # 测试无效action
    console.print("[yellow]测试无效action验证...[/yellow]")
    result = manage_browser_session("invalid_action")
    result_dict = json.loads(result)
    assert result_dict["status"] == "error", "应该返回action错误"
    console.print("[green]✅ Action验证测试通过[/green]")
    
    # 测试list_all操作
    console.print("[yellow]测试list_all操作...[/yellow]")
    result = manage_browser_session("list_all")
    result_dict = json.loads(result)
    assert result_dict["status"] == "success", "list_all应该成功"
    assert "total_sessions" in result_dict, "应该包含会话总数"
    console.print(f"[green]✅ 当前会话数: {result_dict['total_sessions']}[/green]")
    
    # 注意：create和stop操作需要实际AWS环境
    console.print("[yellow]⚠️  create和stop操作需要AWS环境[/yellow]")


def test_batch_extract_from_urls():
    """测试批量URL数据采集"""
    console.print("\n[bold cyan]测试 5: batch_extract_from_urls[/bold cyan]")
    
    # 测试URL格式验证
    console.print("[yellow]测试URL格式验证...[/yellow]")
    result = batch_extract_from_urls("invalid json", "extract title")
    result_dict = json.loads(result)
    assert result_dict["status"] == "error", "应该返回JSON格式错误"
    console.print("[green]✅ URL格式验证测试通过[/green]")
    
    # 测试空URL列表
    console.print("[yellow]测试空URL列表...[/yellow]")
    result = batch_extract_from_urls("[]", "extract title")
    result_dict = json.loads(result)
    assert result_dict["status"] == "error", "应该返回空列表错误"
    console.print("[green]✅ 空URL列表验证测试通过[/green]")
    
    # 测试method验证
    console.print("[yellow]测试method验证...[/yellow]")
    urls = '["https://example.com"]'
    result = batch_extract_from_urls(urls, "extract", method="invalid")
    result_dict = json.loads(result)
    assert result_dict["status"] == "error", "应该返回method错误"
    console.print("[green]✅ Method验证测试通过[/green]")
    
    # 测试nova_act方法需要API密钥
    console.print("[yellow]测试nova_act方法需要API密钥...[/yellow]")
    result = batch_extract_from_urls(urls, "extract", method="nova_act")
    result_dict = json.loads(result)
    assert result_dict["status"] == "error", "应该返回API密钥缺失错误"
    console.print("[green]✅ API密钥验证测试通过[/green]")


def run_all_tests():
    """运行所有测试"""
    console.print("[bold magenta]═══════════════════════════════════════════[/bold magenta]")
    console.print("[bold magenta]  浏览器自动化工具集 - 测试套件[/bold magenta]")
    console.print("[bold magenta]═══════════════════════════════════════════[/bold magenta]")
    
    try:
        test_browser_with_nova_act()
        test_browser_with_live_view_nova()
        test_browser_with_live_view_use()
        test_manage_browser_session()
        test_batch_extract_from_urls()
        
        console.print("\n[bold green]═══════════════════════════════════════════[/bold green]")
        console.print("[bold green]  ✅ 所有测试通过！[/bold green]")
        console.print("[bold green]═══════════════════════════════════════════[/bold green]")
        
        console.print("\n[yellow]注意：[/yellow]")
        console.print("• 完整功能测试需要有效的Nova Act API密钥")
        console.print("• 某些功能需要AWS Bedrock环境配置")
        console.print("• 实时视图功能需要Amazon DCV SDK")
        
        return 0
    
    except AssertionError as e:
        console.print(f"\n[bold red]❌ 测试失败: {e}[/bold red]")
        return 1
    
    except Exception as e:
        console.print(f"\n[bold red]❌ 测试异常: {e}[/bold red]")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
