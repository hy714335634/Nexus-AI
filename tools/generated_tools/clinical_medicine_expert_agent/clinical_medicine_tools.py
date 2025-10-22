from strands import tool
from typing import Dict, List, Optional, Any, Union
import json
import boto3
import os
import logging
import time
from botocore.exceptions import ClientError

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 创建缓存目录
CACHE_DIR = os.path.join(".cache", "clinical_medicine_expert")
os.makedirs(CACHE_DIR, exist_ok=True)

class EmbeddingSearchClient:
    """S3向量搜索客户端类"""
    
    def __init__(self, region: str = "us-east-1"):
        """初始化S3向量搜索客户端"""
        self.s3_client = boto3.client('s3', region_name=region)
        self.region = region
        
    def search_by_embeddings(self, 
                            bucket_name: str, 
                            vector_key: str, 
                            query_vector: List[float], 
                            top_k: int = 10, 
                            filter_expression: Optional[Dict] = None) -> Dict:
        """
        使用向量搜索S3中的向量数据
        
        Args:
            bucket_name: S3桶名称
            vector_key: 向量数据的S3键
            query_vector: 查询向量
            top_k: 返回的最大结果数
            filter_expression: 过滤表达式
            
        Returns:
            搜索结果
        """
        try:
            params = {
                'Bucket': bucket_name,
                'Key': vector_key,
                'VectorSearchConfiguration': {
                    'QueryVector': query_vector,
                    'K': top_k
                }
            }
            
            if filter_expression:
                params['VectorSearchConfiguration']['FilterExpression'] = filter_expression
                
            response = self.s3_client.select_object_content(**params)
            
            # 处理响应
            result = {"matches": []}
            for event in response['Payload']:
                if 'Records' in event:
                    records = event['Records']['Payload'].decode('utf-8')
                    result_data = json.loads(records)
                    if isinstance(result_data, list):
                        result["matches"].extend(result_data)
                    else:
                        result["matches"].append(result_data)
                        
            return result
            
        except ClientError as e:
            logger.error(f"Error searching vectors in S3: {e}")
            return {"error": str(e), "matches": []}

class Neo4jClient:
    """Neo4j知识图谱查询客户端类"""
    
    def __init__(self, region: str = "us-east-1"):
        """初始化Neo4j客户端"""
        # 使用AWS Lambda函数作为Neo4j查询的代理
        self.lambda_client = boto3.client('lambda', region_name=region)
        self.region = region
        
    def query_knowledge_graph(self, function_name: str, payload: Dict) -> Dict:
        """
        调用Lambda函数执行Neo4j查询
        
        Args:
            function_name: Lambda函数名称
            payload: 查询参数
            
        Returns:
            查询结果
        """
        try:
            response = self.lambda_client.invoke(
                FunctionName=function_name,
                InvocationType='RequestResponse',
                Payload=json.dumps(payload)
            )
            
            result = json.loads(response['Payload'].read().decode())
            return result
        
        except ClientError as e:
            logger.error(f"Error invoking Lambda function for Neo4j query: {e}")
            return {"error": str(e), "data": []}

class DynamicToolClient:
    """动态工具调用客户端类"""
    
    def __init__(self, region: str = "us-east-1"):
        """初始化动态工具调用客户端"""
        # 使用AWS Lambda函数作为动态工具调用的代理
        self.lambda_client = boto3.client('lambda', region_name=region)
        self.region = region
        
    def invoke_dynamic_tool(self, function_name: str, tool_name: str, parameters: Dict) -> Dict:
        """
        调用动态工具
        
        Args:
            function_name: Lambda函数名称
            tool_name: 工具名称
            parameters: 工具参数
            
        Returns:
            工具执行结果
        """
        try:
            payload = {
                "tool_name": tool_name,
                "parameters": parameters
            }
            
            response = self.lambda_client.invoke(
                FunctionName=function_name,
                InvocationType='RequestResponse',
                Payload=json.dumps(payload)
            )
            
            result = json.loads(response['Payload'].read().decode())
            return result
        
        except ClientError as e:
            logger.error(f"Error invoking dynamic tool: {e}")
            return {"error": str(e), "result": None}

# 创建客户端实例
embedding_client = EmbeddingSearchClient()
neo4j_client = Neo4jClient()
dynamic_tool_client = DynamicToolClient()

@tool
def search_from_s3vectors_by_embeddings(query: str, 
                                       bucket_name: str, 
                                       vector_key: str, 
                                       top_k: int = 10,
                                       model_id: str = "amazon.titan-embed-text-v1",
                                       region: str = "us-east-1",
                                       filter_expression: Optional[Dict] = None) -> str:
    """
    使用文本查询通过嵌入向量搜索S3中的向量数据
    
    Args:
        query: 查询文本
        bucket_name: S3桶名称
        vector_key: 向量数据的S3键
        top_k: 返回的最大结果数
        model_id: 用于生成嵌入的模型ID
        region: AWS区域
        filter_expression: 过滤表达式
        
    Returns:
        JSON格式的搜索结果
    """
    try:
        # 生成查询文本的嵌入向量
        bedrock_client = boto3.client('bedrock-runtime', region_name=region)
        
        # 调用Bedrock API生成嵌入
        response = bedrock_client.invoke_model(
            modelId=model_id,
            contentType="application/json",
            accept="application/json",
            body=json.dumps({
                "inputText": query
            })
        )
        
        embedding_result = json.loads(response['body'].read().decode())
        query_vector = embedding_result.get('embedding', [])
        
        if not query_vector:
            return json.dumps({"error": "Failed to generate embedding for query", "matches": []})
        
        # 使用嵌入向量搜索
        client = EmbeddingSearchClient(region)
        result = client.search_by_embeddings(
            bucket_name=bucket_name,
            vector_key=vector_key,
            query_vector=query_vector,
            top_k=top_k,
            filter_expression=filter_expression
        )
        
        return json.dumps(result)
    
    except Exception as e:
        logger.error(f"Error in search_from_s3vectors_by_embeddings: {e}")
        return json.dumps({"error": str(e), "matches": []})

@tool
def get_tools_by_parameter(parameter_name: str, 
                          exact_match: bool = True, 
                          limit: int = 10,
                          neo4j_function: str = "tooluniverse-neo4j-query",
                          region: str = "us-east-1") -> str:
    """
    根据参数名称查询工具
    
    Args:
        parameter_name: 参数名称
        exact_match: 是否精确匹配
        limit: 返回结果数量限制
        neo4j_function: Neo4j查询Lambda函数名称
        region: AWS区域
        
    Returns:
        JSON格式的工具列表
    """
    try:
        payload = {
            "query_type": "get_tools_by_parameter",
            "parameter_name": parameter_name,
            "exact_match": exact_match,
            "limit": limit
        }
        
        client = Neo4jClient(region)
        result = client.query_knowledge_graph(neo4j_function, payload)
        
        return json.dumps(result)
    
    except Exception as e:
        logger.error(f"Error in get_tools_by_parameter: {e}")
        return json.dumps({"error": str(e), "data": []})

@tool
def get_parameters_by_tool(tool_name: str, 
                          exact_match: bool = True, 
                          neo4j_function: str = "tooluniverse-neo4j-query",
                          region: str = "us-east-1") -> str:
    """
    根据工具名称查询参数
    
    Args:
        tool_name: 工具名称
        exact_match: 是否精确匹配
        neo4j_function: Neo4j查询Lambda函数名称
        region: AWS区域
        
    Returns:
        JSON格式的参数列表
    """
    try:
        payload = {
            "query_type": "get_parameters_by_tool",
            "tool_name": tool_name,
            "exact_match": exact_match
        }
        
        client = Neo4jClient(region)
        result = client.query_knowledge_graph(neo4j_function, payload)
        
        return json.dumps(result)
    
    except Exception as e:
        logger.error(f"Error in get_parameters_by_tool: {e}")
        return json.dumps({"error": str(e), "data": []})

@tool
def get_parameter_path(parameter_name: str, 
                      tool_name: str, 
                      neo4j_function: str = "tooluniverse-neo4j-query",
                      region: str = "us-east-1") -> str:
    """
    获取参数在工具中的路径
    
    Args:
        parameter_name: 参数名称
        tool_name: 工具名称
        neo4j_function: Neo4j查询Lambda函数名称
        region: AWS区域
        
    Returns:
        JSON格式的参数路径信息
    """
    try:
        payload = {
            "query_type": "get_parameter_path",
            "parameter_name": parameter_name,
            "tool_name": tool_name
        }
        
        client = Neo4jClient(region)
        result = client.query_knowledge_graph(neo4j_function, payload)
        
        return json.dumps(result)
    
    except Exception as e:
        logger.error(f"Error in get_parameter_path: {e}")
        return json.dumps({"error": str(e), "data": []})

@tool
def get_tools_by_genre(genre: str, 
                      exact_match: bool = True, 
                      limit: int = 10,
                      neo4j_function: str = "tooluniverse-neo4j-query",
                      region: str = "us-east-1") -> str:
    """
    根据类别查询工具
    
    Args:
        genre: 工具类别
        exact_match: 是否精确匹配
        limit: 返回结果数量限制
        neo4j_function: Neo4j查询Lambda函数名称
        region: AWS区域
        
    Returns:
        JSON格式的工具列表
    """
    try:
        payload = {
            "query_type": "get_tools_by_genre",
            "genre": genre,
            "exact_match": exact_match,
            "limit": limit
        }
        
        client = Neo4jClient(region)
        result = client.query_knowledge_graph(neo4j_function, payload)
        
        return json.dumps(result)
    
    except Exception as e:
        logger.error(f"Error in get_tools_by_genre: {e}")
        return json.dumps({"error": str(e), "data": []})

@tool
def get_all_genres(neo4j_function: str = "tooluniverse-neo4j-query",
                  region: str = "us-east-1") -> str:
    """
    获取所有工具类别
    
    Args:
        neo4j_function: Neo4j查询Lambda函数名称
        region: AWS区域
        
    Returns:
        JSON格式的类别列表
    """
    try:
        payload = {
            "query_type": "get_all_genres"
        }
        
        client = Neo4jClient(region)
        result = client.query_knowledge_graph(neo4j_function, payload)
        
        return json.dumps(result)
    
    except Exception as e:
        logger.error(f"Error in get_all_genres: {e}")
        return json.dumps({"error": str(e), "data": []})

@tool
def run_dynamic_tools_from_tooluniverse(tool_name: str, 
                                       parameters: Dict[str, Any], 
                                       dynamic_function: str = "tooluniverse-dynamic-tools",
                                       region: str = "us-east-1",
                                       timeout: int = 60,
                                       use_cache: bool = True) -> str:
    """
    运行来自ToolUniverse的动态工具
    
    Args:
        tool_name: 工具名称
        parameters: 工具参数
        dynamic_function: 动态工具调用Lambda函数名称
        region: AWS区域
        timeout: 超时时间(秒)
        use_cache: 是否使用缓存
        
    Returns:
        JSON格式的工具执行结果
    """
    try:
        # 生成缓存键
        cache_key = f"{tool_name}_{hash(json.dumps(parameters, sort_keys=True))}"
        cache_file = os.path.join(CACHE_DIR, f"{cache_key}.json")
        
        # 检查缓存
        if use_cache and os.path.exists(cache_file):
            # 检查缓存是否过期(24小时)
            if time.time() - os.path.getmtime(cache_file) < 86400:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    return f.read()
        
        client = DynamicToolClient(region)
        result = client.invoke_dynamic_tool(
            function_name=dynamic_function,
            tool_name=tool_name,
            parameters=parameters
        )
        
        # 缓存结果
        if use_cache:
            os.makedirs(os.path.dirname(cache_file), exist_ok=True)
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
        
        return json.dumps(result)
    
    except Exception as e:
        logger.error(f"Error in run_dynamic_tools_from_tooluniverse: {e}")
        return json.dumps({"error": str(e), "result": None})