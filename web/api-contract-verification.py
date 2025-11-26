#!/usr/bin/env python3
"""
API Contract Verification Script
验证前端类型定义与后端API实际响应的一致性
"""

import json
import sys
from typing import Any, Dict, List, Optional
from datetime import datetime
import requests

BASE_URL = "http://localhost:8000"

class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def log_test(message: str, status: str = "info"):
    """打印彩色日志"""
    color = {
        "info": Colors.OKBLUE,
        "success": Colors.OKGREEN,
        "warning": Colors.WARNING,
        "error": Colors.FAIL,
        "header": Colors.HEADER
    }.get(status, "")
    print(f"{color}{message}{Colors.ENDC}")

def save_snapshot(endpoint: str, response_data: Any):
    """保存API响应快照"""
    filename = endpoint.replace("/", "_").replace(":", "").replace("{", "").replace("}", "")
    filepath = f"api-snapshots/{filename}.json"
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump({
            "endpoint": endpoint,
            "timestamp": datetime.now().isoformat(),
            "response": response_data
        }, f, indent=2, ensure_ascii=False)
    return filepath

def test_endpoint(method: str, endpoint: str, expected_fields: Optional[Dict[str, str]] = None,
                  data: Optional[Dict] = None, description: str = ""):
    """测试单个endpoint并验证响应结构"""
    url = f"{BASE_URL}{endpoint}"
    log_test(f"\n{'='*80}", "header")
    log_test(f"Testing: {method} {endpoint}", "header")
    if description:
        log_test(f"Description: {description}", "info")

    try:
        if method == "GET":
            response = requests.get(url, timeout=10)
        elif method == "POST":
            response = requests.post(url, json=data, timeout=10)
        elif method == "PUT":
            response = requests.put(url, json=data, timeout=10)
        elif method == "DELETE":
            response = requests.delete(url, timeout=10)
        else:
            log_test(f"Unsupported method: {method}", "error")
            return None

        log_test(f"Status Code: {response.status_code}",
                "success" if 200 <= response.status_code < 300 else "warning")

        if response.status_code >= 400:
            log_test(f"Error Response: {response.text}", "error")
            return None

        response_json = response.json()

        # 验证响应结构
        if expected_fields:
            log_test("Verifying response structure...", "info")
            for field, field_type in expected_fields.items():
                if field in response_json:
                    log_test(f"  ✓ Field '{field}' exists (type: {type(response_json[field]).__name__})", "success")
                    if 'data' in field and isinstance(response_json[field], dict):
                        log_test(f"    Data keys: {list(response_json[field].keys())}", "info")
                else:
                    log_test(f"  ✗ Field '{field}' MISSING!", "error")

        # 保存快照
        snapshot_path = save_snapshot(endpoint, response_json)
        log_test(f"Snapshot saved: {snapshot_path}", "success")

        # 打印响应示例
        log_test("Response Sample:", "info")
        print(json.dumps(response_json, indent=2, ensure_ascii=False)[:500] + "...")

        return response_json

    except requests.exceptions.RequestException as e:
        log_test(f"Request failed: {str(e)}", "error")
        return None
    except Exception as e:
        log_test(f"Unexpected error: {str(e)}", "error")
        return None

def main():
    """主验证流程"""
    log_test(f"\n{'#'*80}", "header")
    log_test("# API CONTRACT VERIFICATION", "header")
    log_test(f"# Started at: {datetime.now().isoformat()}", "header")
    log_test(f"{'#'*80}\n", "header")

    results = {
        "total": 0,
        "passed": 0,
        "failed": 0,
        "endpoints": []
    }

    # ============= PROJECTS API =============
    log_test("\n" + "="*80, "header")
    log_test("PHASE 1: Projects API Verification", "header")
    log_test("="*80, "header")

    # 1. GET /api/v1/projects
    response = test_endpoint(
        "GET", "/api/v1/projects?limit=100",
        expected_fields={"success": bool, "data": dict, "timestamp": str},
        description="获取项目列表 - 验证返回 'items' 字段"
    )
    results["total"] += 1
    if response and "data" in response and "items" in response["data"]:
        log_test("✓ CRITICAL: Response contains 'items' (not 'projects')", "success")
        results["passed"] += 1
    else:
        log_test("✗ CRITICAL: Response structure incorrect!", "error")
        results["failed"] += 1

    # 获取一个项目ID用于后续测试
    project_id = None
    if response and "data" in response and "items" in response["data"] and response["data"]["items"]:
        project_id = response["data"]["items"][0].get("project_id")
        log_test(f"Using project_id for testing: {project_id}", "info")

    # 2. POST /api/v1/projects
    create_response = test_endpoint(
        "POST", "/api/v1/projects",
        data={"requirement": "Test API verification - create a simple greeting agent"},
        expected_fields={"success": bool, "data": dict, "message": str},
        description="创建新项目"
    )
    results["total"] += 1
    if create_response and create_response.get("success"):
        results["passed"] += 1
        # 使用新创建的项目ID
        if "data" in create_response and "project_id" in create_response["data"]:
            test_project_id = create_response["data"]["project_id"]
    else:
        results["failed"] += 1
        test_project_id = project_id  # fallback

    if not project_id:
        project_id = test_project_id

    # 3. GET /api/v1/projects/{id}
    if project_id:
        response = test_endpoint(
            "GET", f"/api/v1/projects/{project_id}",
            expected_fields={"success": bool, "data": dict},
            description="获取项目详情"
        )
        results["total"] += 1
        results["passed" if response else "failed"] += 1

        # 4. GET /api/v1/projects/{id}/stages
        response = test_endpoint(
            "GET", f"/api/v1/projects/{project_id}/stages",
            expected_fields={"success": bool, "data": dict},
            description="获取项目所有阶段"
        )
        results["total"] += 1
        results["passed" if response else "failed"] += 1

        # 5. GET /api/v1/projects/{id}/stages/{name}
        response = test_endpoint(
            "GET", f"/api/v1/projects/{project_id}/stages/orchestrator",
            expected_fields={"success": bool, "data": dict},
            description="获取特定阶段详情"
        )
        results["total"] += 1
        results["passed" if response else "failed"] += 1

    # ============= AGENTS API =============
    log_test("\n" + "="*80, "header")
    log_test("PHASE 2: Agents API Verification", "header")
    log_test("="*80, "header")

    # 6. GET /api/v1/agents
    response = test_endpoint(
        "GET", "/api/v1/agents?limit=100",
        expected_fields={"success": bool, "data": dict},
        description="获取Agents列表"
    )
    results["total"] += 1
    results["passed" if response else "failed"] += 1

    # ============= STATISTICS API =============
    log_test("\n" + "="*80, "header")
    log_test("PHASE 3: Statistics API Verification", "header")
    log_test("="*80, "header")

    # 7. GET /api/v1/statistics/overview
    response = test_endpoint(
        "GET", "/api/v1/statistics/overview",
        expected_fields={"success": bool, "data": dict},
        description="获取统计概览"
    )
    results["total"] += 1
    results["passed" if response else "failed"] += 1

    # ============= SUMMARY =============
    log_test("\n" + "="*80, "header")
    log_test("VERIFICATION SUMMARY", "header")
    log_test("="*80, "header")
    log_test(f"Total Endpoints Tested: {results['total']}", "info")
    log_test(f"Passed: {results['passed']}", "success")
    log_test(f"Failed: {results['failed']}", "error" if results['failed'] > 0 else "info")
    log_test(f"Success Rate: {results['passed']/results['total']*100:.1f}%",
            "success" if results['failed'] == 0 else "warning")

    # 保存验证报告
    report = {
        "verification_date": datetime.now().isoformat(),
        "base_url": BASE_URL,
        "results": results
    }
    with open("api-snapshots/verification-report.json", 'w') as f:
        json.dump(report, f, indent=2)
    log_test("\nVerification report saved to: api-snapshots/verification-report.json", "success")

    return 0 if results['failed'] == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
