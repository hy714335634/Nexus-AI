#!/usr/bin/env python3
"""
PMC文献助手 (PMC Literature Assistant)
支持命令行参数控制，实现批量文献检索、分析和标记
"""

import os
import sys
import json
import argparse
from pathlib import Path
from nexus_utils.agent_factory import create_agent_from_prompt_template
from nexus_utils.config_loader import ConfigLoader
config = ConfigLoader()
# 导入工具（用于后续步骤）
from tools.generated_tools.pubmed_literature_screen_assistant.literature_analyzer import analyze_literature_with_query
from tools.generated_tools.pubmed_literature_screen_assistant.mark_literature import mark_literature

os.environ["BYPASS_TOOL_CONSENT"] = "true"
otel_endpoint = config.get_with_env_override(
    "OTEL_EXPORTER_OTLP_ENDPOINT",
    "nexus_ai", "OTEL_EXPORTER_OTLP_ENDPOINT",
    default="http://localhost:4318"
)
os.environ.setdefault("OTEL_EXPORTER_OTLP_ENDPOINT", otel_endpoint)
strands_telemetry = StrandsTelemetry()
strands_telemetry.setup_otlp_exporter()



def create_literature_assistant():
    """创建PMC文献助手"""
    return create_agent_from_prompt_template(
        agent_name="generated_agents_prompts/pubmed_literature_screen_assistant/pubmed_literature_screen_assistant",
        env="production",
        version="latest",
        model_id="default"
    )

def create_literature_analyzer():
    """创建文献分析agent"""
    from tools.generated_tools.pubmed_literature_screen_assistant.literature_analyzer import LiteratureAnalyzerAgent
    return LiteratureAnalyzerAgent(env="production")


def step1_search_literature(query: str, research_id: str, api_key: str = None, max_results: int = 50):
    """
    步骤1: 检索文献 - 让agent自主决定检索策略
    """
    print(f"\n{'='*80}")
    print("步骤1: 使用agent检索文献")
    print(f"{'='*80}")
    print(f"查询: {query}")
    print(f"Research ID: {research_id}")
    print(f"最大结果数: {max_results}")
    
    # 设置API密钥
    if api_key:
        os.environ["NCBI_API_KEY"] = api_key
    
    # 创建agent
    agent = create_literature_assistant()
    print(f"✅ Agent创建成功: {agent.name}")
    
    # 构造查询提示词
    prompt = f"""用户文献收集及筛选需求: {query}

请使用search_by_keywords或search_by_filters工具检索文献，研究ID为: {research_id}，最大检索结果数为: {max_results}。

请根据用户需求自主决定使用哪些关键词进行检索。
"""
    
    print(f"\n📝 将查询传递给agent，由agent自主决定检索策略...")
    
    # 调用agent
    result = agent(prompt)
    
    print(f"\n✅ Agent处理完成")
    print(f"Agent响应: {result.message}...")
    
    # 从缓存目录获取检索到的文献ID
    cache_dir = Path(f".cache/pmc_literature/{research_id}/meta_data")
    if cache_dir.exists():
        pmc_ids = [f.stem for f in cache_dir.glob("*.json")]
        print(f"✅ 检索到 {len(pmc_ids)} 篇文献")
        
        # 保存步骤1状态
        cache_dir.parent.mkdir(parents=True, exist_ok=True)
        status_file = cache_dir.parent / "step1.status"
        with open(status_file, 'w', encoding='utf-8') as f:
            f.write(result.message['content'][0]['text'])
        
        return pmc_ids
    else:
        print(f"❌ 缓存目录不存在")
        return []


def step2_analyze_literature(pmc_ids: list, research_id: str, user_query: str):
    """
    步骤2: 分析文献 - 创建独立的agent对每篇文献进行分析
    """
    print(f"\n{'='*80}")
    print("步骤2: 分析文献")
    print(f"{'='*80}")
    
    # 创建analysis_results目录
    cache_dir = Path(f".cache/pmc_literature/{research_id}")
    analysis_dir = cache_dir / "analysis_results"
    analysis_dir.mkdir(parents=True, exist_ok=True)
    
    analyzed_results = []
    skipped_count = 0
    
    for i, pmc_id in enumerate(pmc_ids, 1):
        print(f"\n[{i}/{len(pmc_ids)}] 分析文献: {pmc_id}")
        
        # 检查是否已经分析过
        analysis_file = analysis_dir / f"{pmc_id}.json"
        if analysis_file.exists():
            print(f"  ✅ 已存在分析结果，跳过")
            skipped_count += 1
            try:
                with open(analysis_file, 'r', encoding='utf-8') as f:
                    analysis = json.load(f)
                analyzed_results.append({
                    "pmcid": pmc_id,
                    "analysis": analysis
                })
            except Exception as e:
                print(f"  ⚠️  读取分析结果失败: {str(e)}")
            continue
        
        try:
            # 调用分析工具
            result = analyze_literature_with_query(research_id, user_query, [pmc_id])
            
            # 尝试解析JSON
            try:
                analysis = json.loads(result)
                
                # 保存分析结果
                with open(analysis_file, 'w', encoding='utf-8') as f:
                    json.dump(analysis, f, ensure_ascii=False, indent=2)
                
                analyzed_results.append({
                    "pmcid": pmc_id,
                    "analysis": analysis
                })
                
                # 打印分析结果
                should_mark = analysis.get("should_mark", False)
                relevance_score = analysis.get("relevance_score", 0)
                print(f"  -> should_mark: {should_mark}, relevance_score: {relevance_score}")
                
            except json.JSONDecodeError:
                print(f"  ⚠️  无法解析JSON结果，跳过")
                analyzed_results.append({
                    "pmcid": pmc_id,
                    "analysis": {"should_mark": False, "error": "Failed to parse JSON"}
                })
                
        except Exception as e:
            print(f"  ❌ 分析失败: {str(e)}")
            analyzed_results.append({
                "pmcid": pmc_id,
                "analysis": {"should_mark": False, "error": str(e)}
            })
    
    # 保存步骤2状态
    if skipped_count > 0:
        print(f"\n📊 跳过 {skipped_count} 个已分析的文件，新增分析 {len(analyzed_results) - skipped_count} 个")
    
    status_file = cache_dir / "step2.status"
    with open(status_file, 'w', encoding='utf-8') as f:
        json.dump(analyzed_results, f, ensure_ascii=False, indent=2)
    
    return analyzed_results


def step3_mark_literature(research_id: str):
    """
    步骤3: 标记相关文献 - 从analysis_results目录读取所有分析结果
    """
    print(f"\n{'='*80}")
    print("步骤3: 标记相关文献")
    print(f"{'='*80}")
    
    # 读取analysis_results目录中的所有JSON文件
    analysis_dir = Path(f".cache/pmc_literature/{research_id}/analysis_results")
    
    if not analysis_dir.exists():
        print("❌ analysis_results目录不存在")
        return
    
    # 收集所有分析结果
    to_mark = []
    reasoning_dict = {}
    
    json_files = list(analysis_dir.glob("*.json"))
    print(f"找到 {len(json_files)} 个分析结果文件")
    
    for json_file in json_files:
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                analysis = json.load(f)
            
            pmcid = json_file.stem
            
            if analysis.get("should_mark", False):
                to_mark.append(pmcid)
                reasoning_dict[pmcid] = analysis.get("reasoning", "")
                
        except Exception as e:
            print(f"⚠️  读取分析结果失败 {json_file.name}: {str(e)}")
    
    print(f"找到 {len(to_mark)} 篇相关文献需要标记")
    
    if not to_mark:
        print("没有文献需要标记")
        return
    
    # 一次性标记所有文献
    print(f"\n开始标记 {len(to_mark)} 篇文献...")
    
    try:
        result = mark_literature(to_mark, research_id, reasoning_dict, auto_download=False)
        result_data = json.loads(result)
        
        if result_data.get("status") == "success":
            print(f"✅ 成功标记 {result_data.get('marked_count', 0)} 篇文献")
            
            # 保存步骤3状态
            cache_dir = Path(f".cache/pmc_literature/{research_id}")
            status_file = cache_dir / "step3.status"
            with open(status_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "total_to_mark": len(to_mark),
                    "marked_pmcs": to_mark
                }, f, ensure_ascii=False, indent=2)
        else:
            print(f"❌ 标记失败: {result_data.get('message', 'Unknown error')}")
            
    except Exception as e:
        print(f"❌ 标记失败: {str(e)}")


def check_progress(research_id: str):
    """
    检查进度状态，返回需要从哪个步骤开始
    按照步骤顺序检查：step1 -> step2 -> step3 -> manifest.json
    
    Returns:
        返回需要开始的步骤号 (1, 2, 3) 或 0 (全部完成)
    """
    cache_dir = Path(f".cache/pmc_literature/{research_id}")
    
    # 第一步：检查步骤1是否完成（通过step1.status和meta_data目录）
    step1_status = cache_dir / "step1.status"
    meta_data_dir = cache_dir / "meta_data"
    
    if not step1_status.exists() or not meta_data_dir.exists():
        print(f"\n⚠️  步骤1未完成，从步骤1开始")
        return 1
    
    meta_data_files = list(meta_data_dir.glob("*.json"))
    total_pmc_ids = len(meta_data_files)
    if total_pmc_ids == 0:
        print(f"\n⚠️  步骤1未完成（无文献数据），从步骤1开始")
        return 1
    
    print(f"\n✅ 步骤1已完成：发现 {total_pmc_ids} 篇文献")
    
    # 第二步：检查步骤2是否完成
    # 步骤2基于paper文件夹下的文件进行分析
    step2_status = cache_dir / "step2.status"
    analysis_dir = cache_dir / "analysis_results"
    paper_dir = cache_dir / "paper"
    
    # 检查paper文件夹下的待处理文件
    if not paper_dir.exists():
        print(f"\n⚠️  paper文件夹不存在，从步骤2开始（可能需要先下载全文）")
        return 2
    
    paper_files = list(paper_dir.glob("*.txt"))
    total_papers = len(paper_files)
    
    if total_papers == 0:
        print(f"\n⚠️  paper文件夹为空，从步骤2开始")
        return 2
    
    # 检查analysis_results目录
    if not analysis_dir.exists():
        print(f"\n⚠️  步骤2未开始，从步骤2开始")
        return 2
    
    analysis_files = list(analysis_dir.glob("*.json"))
    
    # 如果没有step2.status，说明步骤2未完成
    if not step2_status.exists():
        print(f"\n⚠️  步骤2未完成：已分析 {len(analysis_files)}/{total_papers} 篇文献，从步骤2继续")
        return 2
    
    # 对比paper文件和analysis_results，检查是否需要继续分析
    paper_pmc_ids = set([f.stem for f in paper_files])
    analysis_pmc_ids = set([f.stem for f in analysis_files])
    
    if paper_pmc_ids == analysis_pmc_ids:
        print(f"\n✅ 步骤2已完成：分析了 {len(analysis_files)} 篇文献")
    else:
        print(f"\n⚠️  步骤2未完成：已分析 {len(analysis_files)}/{total_papers} 篇文献，从步骤2继续")
        return 2
    
    # 第三步：检查步骤3是否完成（通过step3.status文件）
    step3_status = cache_dir / "step3.status"
    
    if not step3_status.exists():
        print(f"\n⚠️  步骤3未完成，从步骤3开始")
        return 3
    
    # step3.status存在，检查是否有效
    try:
        with open(step3_status, 'r', encoding='utf-8') as f:
            step3_data = json.load(f)
        marked_pmcs = step3_data.get('marked_pmcs', [])
        if not marked_pmcs:
            print(f"\n⚠️  步骤3未完成，从步骤3开始")
            return 3
        print(f"\n✅ 步骤3已完成：已标记 {len(marked_pmcs)} 篇文献")
    except Exception as e:
        print(f"\n⚠️  读取步骤3状态失败: {str(e)}，从步骤3开始")
        return 3
    
    # 第四步：最终检查manifest.json文件
    manifest_file = cache_dir / "manifest.json"
    
    if not manifest_file.exists():
        print(f"\n⚠️  manifest.json不存在，从步骤3开始")
        return 3
    
    # manifest.json存在，检查是否有效
    try:
        with open(manifest_file, 'r', encoding='utf-8') as f:
            manifest = json.load(f)
        total_count = manifest.get("statistics", {}).get("total_count", 0)
        if total_count > 0:
            print(f"\n✅ 所有步骤已完成！总共标记 {total_count} 篇文献")
            return 0
        else:
            print(f"\n⚠️  manifest.json存在但无标记文献，从步骤3开始")
            return 3
    except Exception as e:
        print(f"\n⚠️  读取manifest.json失败: {str(e)}，从步骤3开始")
        return 3


def main():
    parser = argparse.ArgumentParser(description='PMC文献检索、分析和标记工具')
    parser.add_argument('--query', '-q', type=str, required=True,
                        help='用户查询语句')
    parser.add_argument('--api-key', '-k', type=str, default=None,
                        help='NCBI API密钥（可选）')
    parser.add_argument('--research-id', '-r', type=str, default=None,
                        help='研究ID（可选，默认自动生成）')
    parser.add_argument('--max-results', '-m', type=int, default=100,
                        help='最大检索结果数（默认50）')
    parser.add_argument('--search-only', '-s', action='store_true',
                        help='只执行检索，不进行分析和标记')
    
    args = parser.parse_args()
    
    # 生成research_id
    from datetime import datetime
    if not args.research_id:
        timestamp = datetime.now().strftime("%Y%m%d")
        args.research_id = f"literature_search_{timestamp}"
    
    print(f"\n{'='*80}")
    print("PMC文献检索和分析工具")
    print(f"{'='*80}")
    print(f"Research ID: {args.research_id}")
    print(f"User Query: {args.query}")
    print(f"{'='*80}\n")
    
    # 检查进度
    start_step = check_progress(args.research_id)
    
    # 根据进度决定从哪个步骤开始
    if start_step == 0:
        print("\n✅ 所有步骤已完成，无需重新运行")
        return
    elif start_step == 3:
        # 从步骤3开始
        print("\n从断点继续：步骤3 - 标记文献")
        step3_mark_literature(args.research_id)
        print(f"\n{'='*80}")
        print("✅ 完成！")
        print(f"{'='*80}\n")
        return
    elif start_step == 2:
        # 从步骤2开始
        print("\n从断点继续：步骤2 - 分析文献")
        
        # 从paper文件夹获取待处理的文献列表
        paper_dir = Path(f".cache/pmc_literature/{args.research_id}/paper")
        if not paper_dir.exists():
            print("❌ paper目录不存在，无法继续")
            return
        
        paper_files = list(paper_dir.glob("*.txt"))
        if not paper_files:
            print("❌ 未找到文献全文文件，无法继续")
            return
        
        pmc_ids = [f.stem for f in paper_files]
        print(f"找到 {len(pmc_ids)} 篇文献需要分析")
        
        # 步骤2: 分析文献
        step2_analyze_literature(pmc_ids, args.research_id, args.query)
        
        # 步骤3: 标记文献
        step3_mark_literature(args.research_id)
        
        print(f"\n{'='*80}")
        print("✅ 完成！")
        print(f"{'='*80}\n")
        return
    else:
        # 从步骤1开始
        print("\n从步骤1开始执行")
    
    # 步骤1: 检索文献
    pmc_ids = step1_search_literature(args.query, args.research_id, args.api_key, args.max_results)
    
    if not pmc_ids:
        print("\n❌ 没有检索到文献，退出")
        return
    
    if args.search_only:
        print("\n只执行检索步骤，跳过分析和标记")
        return
    
    # 步骤2: 分析文献
    step2_analyze_literature(pmc_ids, args.research_id, args.query)
    
    # 步骤3: 标记文献（从analysis_results目录读取结果）
    step3_mark_literature(args.research_id)
    
    print(f"\n{'='*80}")
    print("✅ 完成！")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    # 如果直接运行，使用默认查询
    if len(sys.argv) == 1:
        print("使用示例:")
        print("  python pubmed_literature_screen_assistant.py --query 'ADMET prediction tools'")
        print("  python pubmed_literature_screen_assistant.py --query 'machine learning' --max-results 100")
        print("  python pubmed_literature_screen_assistant.py --query 'deep learning' --search-only")
        print("\n开始运行默认查询...\n")
        
        # 默认查询
        agent = create_literature_assistant()
        print(f"PMC文献助手创建成功: {agent.name}")
        result = agent("用户文献收集及筛选需求:ADMET（吸收、分布、代谢、排泄和毒性）预测是新药研发中的关键环节。调研一下当前大多数state of the art的ADMET预测工具，写一份关于ADMET预测工具的调研报告（深度学习的，大模型的，强算法类的等等）,要求查看近五年的文献")
        print(f"智能体响应:\n{result}")
    else:
        main()