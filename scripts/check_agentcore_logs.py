#!/usr/bin/env python3
"""
检查 AgentCore CloudWatch 日志的脚本
"""
import boto3
import sys
from datetime import datetime, timedelta

def get_agentcore_logs(agent_arn: str, region: str = "us-west-2", minutes: int = 10):
    """
    获取 AgentCore 的 CloudWatch 日志

    Args:
        agent_arn: AgentCore ARN
        region: AWS 区域
        minutes: 获取最近几分钟的日志
    """
    # 从 ARN 中提取 agent name
    # ARN 格式: arn:aws:bedrock-agentcore:us-west-2:034362076319:runtime/natural_language_calculator-Cp4whc73v0
    agent_name = agent_arn.split('/')[-1]

    # CloudWatch 日志组名称（通常是这个格式）
    log_group_name = f"/aws/bedrock/agentcore/{agent_name}"

    print(f"检查日志组: {log_group_name}")
    print(f"时间范围: 最近 {minutes} 分钟\n")

    client = boto3.client('logs', region_name=region)

    # 计算时间范围
    end_time = datetime.now()
    start_time = end_time - timedelta(minutes=minutes)

    start_timestamp = int(start_time.timestamp() * 1000)
    end_timestamp = int(end_time.timestamp() * 1000)

    try:
        # 获取日志流
        streams_response = client.describe_log_streams(
            logGroupName=log_group_name,
            orderBy='LastEventTime',
            descending=True,
            limit=5
        )

        if not streams_response.get('logStreams'):
            print(f"❌ 没有找到日志流")
            return

        print(f"找到 {len(streams_response['logStreams'])} 个日志流\n")

        # 获取每个日志流的最新日志
        for stream in streams_response['logStreams']:
            stream_name = stream['logStreamName']
            print(f"{'='*80}")
            print(f"日志流: {stream_name}")
            print(f"最后事件时间: {datetime.fromtimestamp(stream['lastEventTimestamp']/1000)}")
            print(f"{'='*80}\n")

            # 获取日志事件
            events_response = client.get_log_events(
                logGroupName=log_group_name,
                logStreamName=stream_name,
                startTime=start_timestamp,
                endTime=end_timestamp,
                limit=100,
                startFromHead=False  # 从最新的开始
            )

            events = events_response.get('events', [])
            if not events:
                print("  没有新的日志事件\n")
                continue

            # 打印日志
            for event in reversed(events):  # 反转以按时间顺序显示
                timestamp = datetime.fromtimestamp(event['timestamp']/1000)
                message = event['message']
                print(f"[{timestamp}] {message}")

            print()

    except client.exceptions.ResourceNotFoundException:
        print(f"❌ 日志组不存在: {log_group_name}")
        print(f"\n可能的原因:")
        print(f"1. AgentCore 还没有生成日志")
        print(f"2. 日志组名称格式不正确")
        print(f"3. Agent 从未成功启动过")
        print(f"\n尝试查找相关日志组:")

        try:
            # 列出所有 bedrock 相关的日志组
            all_groups = client.describe_log_groups(
                logGroupNamePrefix="/aws/bedrock"
            )

            if all_groups.get('logGroups'):
                print(f"\n找到的 Bedrock 相关日志组:")
                for group in all_groups['logGroups']:
                    print(f"  - {group['logGroupName']}")
            else:
                print(f"\n未找到任何 /aws/bedrock 开头的日志组")
        except Exception as e:
            print(f"列出日志组失败: {e}")

    except Exception as e:
        print(f"❌ 获取日志失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python check_agentcore_logs.py <agent_arn> [region] [minutes]")
        print("示例: python check_agentcore_logs.py arn:aws:bedrock-agentcore:us-west-2:123456789012:runtime/my-agent-abc123 us-west-2 10")
        sys.exit(1)

    agent_arn = sys.argv[1]
    region = sys.argv[2] if len(sys.argv) > 2 else "us-west-2"
    minutes = int(sys.argv[3]) if len(sys.argv) > 3 else 10

    get_agentcore_logs(agent_arn, region, minutes)
