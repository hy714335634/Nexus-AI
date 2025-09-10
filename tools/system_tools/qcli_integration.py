import subprocess
import json
from strands import tool

def call_q_cli(prompt, model=None):
    """调用 Q CLI 进行推理"""
    cmd = ["q", "chat"]
    if model:
        cmd.extend(["--model", model])
    
    # 使用 stdin 传递 prompt
    process = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    stdout, stderr = process.communicate(input=prompt)
    
    if process.returncode != 0:
        raise Exception(f"Q CLI error: {stderr}")
    
    return stdout

# 在 Strands SDK 中使用
@tool
def inference_with_amazon_q(data):
    """
    与amazon Q CLI进行交互，使用Q CLI进行推理
    
    Args:
        data: 用户问题/需求
    
    Returns:
        Q CLI的响应结果
    """
    prompt = f"请针对用户问题进行回答，不要生成任何本地文件，需要生成文件或脚本，请直接通过标准输出，用户问题: {data}"
    result = call_q_cli(prompt)
    return result

if __name__ == "__main__":
    data = "你好，我是Strands SDK，我是一个AI Agent，我可以帮助你完成各种任务。"
    result = strands_inference_with_q(data)
    print(result)