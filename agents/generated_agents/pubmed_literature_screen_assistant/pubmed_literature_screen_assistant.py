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

# 导入工具（用于后续步骤）
from tools.generated_tools.pubmed_literature_screen_assistant.literature_analyzer import analyze_literature_with_query
from tools.generated_tools.pubmed_literature_screen_assistant.mark_literature import mark_literature


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
    print(f"Agent响应: {result.message[:200]}...")
    
    # 从缓存目录获取检索到的文献ID
    cache_dir = Path(f".cache/pmc_literature/{research_id}/meta_data")
    if cache_dir.exists():
        pmc_ids = [f.stem for f in cache_dir.glob("*.json")]
        print(f"✅ 检索到 {len(pmc_ids)} 篇文献")
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
    
    for i, pmc_id in enumerate(pmc_ids, 1):
        print(f"\n[{i}/{len(pmc_ids)}] 分析文献: {pmc_id}")
        
        # 检查是否已经分析过
        analysis_file = analysis_dir / f"{pmc_id}.json"
        if analysis_file.exists():
            print(f"  ✅ 已存在分析结果，跳过")
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
    
    # 批量标记（每批10篇）
    batch_size = 10
    for i in range(0, len(to_mark), batch_size):
        batch = to_mark[i:i+batch_size]
        batch_reasoning = {pmcid: reasoning_dict[pmcid] for pmcid in batch}
        
        print(f"\n标记批次 {i//batch_size + 1}: {len(batch)} 篇文献")
        
        try:
            result = mark_literature(batch, research_id, batch_reasoning, auto_download=False)
            result_data = json.loads(result)
            
            if result_data.get("status") == "success":
                print(f"✅ 成功标记 {result_data.get('marked_count', 0)} 篇文献")
            else:
                print(f"❌ 标记失败: {result_data.get('message', 'Unknown error')}")
                
        except Exception as e:
            print(f"❌ 标记失败: {str(e)}")


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