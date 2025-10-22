# 使用 Amazon Titan 文本嵌入 V2 来生成和打印嵌入。
import boto3 
import json
import os
from typing import List, Dict, Any, Optional

from botocore import args
import argparse
from tooluniverse.execute_function import ToolUniverse

s3vectors_bucket = "curebench"
indexName = "tools-index"
modelId = "amazon.titan-embed-text-v2:0"

def generate_toolslist_from_tooluniverse():
    engine = ToolUniverse()
    engine.load_tools()
    tool_name_list, tool_desc_list = engine.refresh_tool_name_desc()
    genre_list = []
    for i in tool_name_list:
        genre_list.append(engine.get_tool_type_by_name(i))
    # [tool_name: "OpenTargets_get_similar_entities_by_drug_chemblId", desc: "Retrieve similar entities for a given drug chemblId using a model trained with PubMed.", genre: "tooluniverse"]
    tools_list = []
    for i in range(len(tool_name_list)):
        tools_list.append({"tool_name": tool_name_list[i], "desc": tool_desc_list[i], "genre": genre_list[i]})
    with open('embedding/toolslist_from_tooluniverse.json', 'w', encoding='utf-8') as f:
        json.dump(tools_list, f, ensure_ascii=False, indent=2)
    return tools_list

def get_bedrock_client():
    bedrock = boto3.client("bedrock-runtime", region_name="us-west-2") 
    return bedrock


def save_embeddings_to_cache(embeddings: List[List[float]], tools_name: List[str], tools_desc: List[str], cache_file: str, genres: List[str] = None):
    """将embeddings保存到本地缓存文件"""
    cache_data = {
        "embeddings": embeddings,
        "tools_name": tools_name,
        "tools_desc": tools_desc,
        "genres": genres if genres else ['tooluniverse'] * len(tools_name),
        "metadata": {
            "count": len(tools_name),
            "model": "amazon.titan-embed-text-v2:0"
        }
    }
    
    # 确保目录存在
    os.makedirs(os.path.dirname(cache_file), exist_ok=True)
    
    with open(cache_file, 'w', encoding='utf-8') as f:
        json.dump(cache_data, f, ensure_ascii=False, indent=2)
    
    print(f"Embeddings cached to {cache_file}")


def load_embeddings_from_cache(cache_file: str) -> Optional[Dict[str, Any]]:
    """从本地缓存文件加载embeddings"""
    if not os.path.exists(cache_file):
        print(f"Cache file {cache_file} does not exist")
        return None
    
    try:
        with open(cache_file, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)
        
        print(f"Loaded embeddings from cache: {len(cache_data['tools_name'])} tools")
        return cache_data
    except Exception as e:
        print(f"Error loading cache file {cache_file}: {e}")
        return None

def get_s3vectors_client():
    s3vectors_client = boto3.client('s3vectors', region_name='us-west-2')
    return s3vectors_client


def ensure_index_exists(s3vectors_client, bucket_name, index_name="tools-index"):
    """确保索引存在，如果不存在则创建"""
    try:
        # 尝试查询索引信息  
        response = s3vectors_client.get_index(vectorBucketName=bucket_name, indexName=index_name)
        print(f"索引 {index_name} 已存在")
        return True
    except s3vectors_client.exceptions.NotFoundException:
        print(f"索引 {index_name} 不存在，尝试创建...")
        try:
            # 创建索引
            create_response = s3vectors_client.create_index(
                vectorBucketName=bucket_name,
                indexName=index_name,
                dimension=1024,  # Titan embedding的维度
                distanceMetric="cosine",  # 使用余弦距离度量
                dataType="float32"  # 添加数据类型参数
            )
            print(f"成功创建索引 {index_name}")
            return True
        except Exception as e:
            print(f"创建索引失败: {e}")
            return False
    except Exception as e:
        print(f"检查索引时出错: {e}")
        return False


# 在您选择的 AWS 区域中创建 Bedrock Runtime 客户端。
def get_embeddings(bedrock_client, tools_data, modelId="amazon.titan-embed-text-v2:0", cache_file=None, batch_size=50):
    """生成embeddings，支持从缓存加载和批处理"""
    
    # 如果提供了cache_file，先尝试从缓存加载
    if cache_file:
        cache_data = load_embeddings_from_cache(cache_file)
        if cache_data:
            print("Using cached embeddings")
            return cache_data['embeddings'], cache_data['tools_name'], cache_data['tools_desc'], cache_data.get('genres', cache_data.get('genre', ['tooluniverse'] * len(cache_data['tools_name'])))
    
    embeddings = []
    tools_name = []
    tools_desc = []
    genres = []

    # 获取tools数据
    if isinstance(tools_data, dict):
        # 旧格式：{"tool_name": "description"}
        tools_name = list(tools_data.keys())
        tools_desc = list(tools_data.values())
        genres = ['tooluniverse'] * len(tools_name)  # 为旧格式设置默认genre
        texts = tools_desc  # 使用描述作为embedding文本
    elif isinstance(tools_data, list):
        # 新格式：[{"tool_name": "Name", "desc": "Description", "genre": "Category"}]
        tools_name = []
        tools_desc = []
        texts = []
        genres = []
        
        for item in tools_data:
            if isinstance(item, dict):
                tool_name = item.get('tool_name', f"tool_{len(tools_name)}")
                desc = item.get('desc', 'No description')
                genre_val = item.get('genre', 'Unknown')
                
                tools_name.append(tool_name)
                tools_desc.append(desc)
                texts.append(f"{tool_name}: {desc}")  # 结合名称和描述作为embedding文本
                genres.append(genre_val)
            else:
                # 如果不是字典，当作文本处理
                texts.append(str(item))
                tools_name.append(f"tool_{len(tools_name)}")
                tools_desc.append(str(item))
                genres.append('tooluniverse')
                
        print(f"Processed {len(tools_data)} tools from new JSON format")
        print(f"Sample genres: {genres[:5]}")
        print(f"Unique genres: {set(genres)}")
    else:
        # 其他格式
        texts = [str(item) for item in tools_data]
        tools_name = [f"tool_{i}" for i in range(len(texts))]
        tools_desc = texts
        genres = ['tooluniverse'] * len(texts)  # 为其他格式设置默认genre
    
    total_texts = len(texts)
    print(f"Processing {total_texts} texts in batches of {batch_size}")
    
    # 分批处理文本
    for batch_idx in range(0, total_texts, batch_size):
        batch_end = min(batch_idx + batch_size, total_texts)
        batch_texts = texts[batch_idx:batch_end]
        
        print(f"Processing batch {batch_idx//batch_size + 1}/{(total_texts+batch_size-1)//batch_size} ({batch_idx+1}-{batch_end})")
        
        # 为当前批次的文本生成向量嵌入
        for i, text in enumerate(batch_texts):
            body = json.dumps({
                "inputText": text
            })    
            try:
                # 调用 Bedrock 的嵌入 API
                response = bedrock_client.invoke_model(
                    modelId='amazon.titan-embed-text-v2:0',  # Titan embedding model 
                    body=body)   
                # 解析响应
                response_body = json.loads(response['body'].read())
                embedding = response_body['embedding']
                embeddings.append(embedding)
                global_idx = batch_idx + i + 1
                print(f"Embedding for tool {global_idx}/{total_texts} generated")
            except Exception as e:
                print(f"Error generating embedding for text {batch_idx + i + 1}: {e}")
                # 可以选择跳过或使用默认值
                embeddings.append([0.0] * 1536)  # Titan embedding默认维度
        
        # 在批次之间有短暂的延迟，避免API限制
        if batch_end < total_texts:
            print("Waiting before next batch...")
            import time
            time.sleep(1)

    # 如果提供了cache_file，保存到缓存
    if cache_file:
        save_embeddings_to_cache(embeddings, tools_name, tools_desc, cache_file, genres)

    print(f"Successfully generated {len(embeddings)} embeddings")
    return embeddings, tools_name, tools_desc, genres if 'genres' in locals() else ['tooluniverse'] * len(embeddings)

def insert_embeddings(s3vectors_client, s3vectors_bucket="", embeddings=[], tools_name=[],tools_desc=[], indexName="tools-index", genre=[], cache_file=None, batch_size=50):
    """将embeddings分批插入到S3 vectors，支持批处理"""
    
    total_vectors = len(tools_name)
    print(f"Inserting {total_vectors} embeddings in batches of {batch_size}")
    
    success_count = 0
    error_count = 0
    
    # 分批插入vectors
    for batch_idx in range(0, total_vectors, batch_size):
        batch_end = min(batch_idx + batch_size, total_vectors)
        
        # 构建当前批次的vectors
        batch_vectors = []
        for i in range(batch_idx, batch_end):
            # 获取当前工具的genre，如果是数组则获取对应索引的值，否则使用默认值
            tool_genre_val = genre[i] if i < len(genre) else (genre[0] if len(genre) > 0 else "tooluniverse")
            batch_vectors.append({
                "key": tools_name[i], 
                "data": {"float32": embeddings[i]}, 
                "metadata": {
                    "id": tools_name[i], 
                    "source_text": tools_desc[i], 
                    "genre": tool_genre_val
                }
            })

        print(f"Inserting batch {batch_idx//batch_size + 1}/{(total_vectors+batch_size-1)//batch_size} ({batch_idx+1}-{batch_end})")

        try:
            # 插入当前批次的向量嵌入
            s3vectors_client.put_vectors(
                vectorBucketName=s3vectors_bucket,
                indexName=indexName,
                vectors=batch_vectors
            )
            success_count += len(batch_vectors)
            print(f"Successfully inserted {len(batch_vectors)} vectors in this batch")
            
            # 批次之间稍作延迟
            if batch_end < total_vectors:
                print("Waiting before next batch...")
                import time
                time.sleep(1)
                
        except Exception as e:
            print(f"Error inserting batch {batch_idx//batch_size + 1}: {e}")
            error_count += len(batch_vectors)
            
            # 如果插入失败但仍想保存，可以将失败的batch保存到本地
            if cache_file:
                error_cache_file = cache_file.replace('.json', f'_failed_batch_{batch_idx//batch_size + 1}.json')
                batch_embeddings = embeddings[batch_idx:batch_end]
                batch_tools_name = tools_name[batch_idx:batch_end]
                batch_tools_desc = tools_desc[batch_idx:batch_end]
                save_embeddings_to_cache(batch_embeddings, batch_tools_name, batch_tools_desc, error_cache_file)
                print(f"Saved failed batch to {error_cache_file}")

    print(f"\nInsertion completed:")
    print(f"- Successfully inserted: {success_count} vectors")
    print(f"- Failed to insert: {error_count} vectors")
    
    # 保存完整的数据到备份
    if cache_file and success_count > 0:
        backup_file = cache_file.replace('.json', '_backup.json')
        save_embeddings_to_cache(embeddings, tools_name, tools_desc, backup_file)
        print(f"Saved complete backup to {backup_file}")
    
    # 如果没有成功插入任何数据，至少保存到缓存
    if success_count == 0 and cache_file:
        print("No vectors were successfully inserted, saving to local cache...")
        save_embeddings_to_cache(embeddings, tools_name, tools_desc, cache_file)
    elif success_count == 0:
        print("No cache file specified, embeddings will be lost")

def process_tools_with_cache(tools_file: str, cache_file: str = None, save_to_s3: bool = False, batch_size: int = 50):
    """处理tools数据并生成embeddings，支持完整的缓存机制"""
    if cache_file is None:
        cache_file = tools_file.replace('.json', '_embeddings_cache.json')
    
    # 读取tools数据
    with open(tools_file, 'r', encoding='utf-8') as f:
        tools_data = json.load(f)
    
    # 尝试从缓存加载
    cache_data = load_embeddings_from_cache(cache_file)
    if cache_data:
        print("Found cached embeddings, skipping Bedrock API calls")
        return cache_data['embeddings'], cache_data['tools_name'], cache_data['tools_desc'], cache_data.get('genres', cache_data.get('genre', ['tooluniverse'] * len(cache_data['tools_name']))), cache_data
    
    print("No cache found, generating embeddings from Bedrock...")
    
    # 如果没有缓存，生成新的embeddings
    try:
        bedrock_client = get_bedrock_client()
        embeddings, tools_name, tools_desc, genres = get_embeddings(bedrock_client, tools_data, cache_file=cache_file, batch_size=batch_size)
        
        if save_to_s3:
            try:
                s3vectors_client = get_s3vectors_client()
                insert_embeddings(s3vectors_client, "curebench", embeddings, tools_name, tools_desc, indexName="tools-index", genre=genres, cache_file=cache_file, batch_size=batch_size)
            except Exception as e:
                print(f"S3 vectors insertion failed: {e}")
                print("Embeddings saved to local cache only")
        
        return embeddings, tools_name, tools_desc, genres, None
        
    except Exception as e:
        print(f"Error generating embeddings: {e}")
        raise


def diagnose_vector_store(s3vectors_client, bucket_name="", index_name="tools-index"):
    """诊断向量存储的状态"""
    print("=== 诊断S3 Vectors状态 ===")
    
    try:
        # 检查存储桶是否存在
        try:
            response = s3vectors_client.head_vector_bucket(bucketName=bucket_name)
            print(f"✓ 存储桶 '{bucket_name}' 存在")
        except s3vectors_client.exceptions.ResourceNotFoundException:
            print(f"✗ 存储桶 '{bucket_name}' 不存在")
            return False
        except Exception as e:
            print(f"✗ 检查存储桶时出错: {e}")
            return False
        
        # 检查索引是否存在
        try:
            response = s3vectors_client.head_index(bucketName=bucket_name, indexName=index_name)
            print(f"✓ 索引 '{index_name}' 存在")
            print(f"  - 维度: {response.get('dimension', 'Unknown')}")
            return True
        except s3vectors_client.exceptions.ResourceNotFoundException:
            print(f"✗ 索引 '{index_name}' 不存在")
            return False
        except Exception as e:
            print(f"✗ 检查索引时出错: {e}")
            return False
            
    except Exception as e:
        print(f"✗ 诊断过程出错: {e}")
        return False


def test_embeddings(input_text="", s3vectors_bucket=s3vectors_bucket, indexName=indexName,modelId=modelId):
    # 为模型创建 JSON 请求。

    bedrock_client = get_bedrock_client()
    s3vectors_client = get_s3vectors_client()

    request = json.dumps({"inputText": input_text})

    # 使用请求和模型 ID 来调用模型，例如 Titan 文本嵌入 V2。
    response = bedrock_client.invoke_model(modelId=modelId, body=request)

    # 解码模型的原生响应正文。
    model_response = json.loads(response["body"].read())

    # 提取并打印所生成的嵌入和输入文本标记计数。
    embedding = model_response["embedding"]

    # 执行相似度查询。您也可以选择在查询中使用筛选器
    query = s3vectors_client.query_vectors( vectorBucketName=s3vectors_bucket,
        indexName=indexName,
        queryVector={"float32":embedding},
        topK=3,
        returnDistance=True,
        returnMetadata=True
    )
    results = query["vectors"]
    print(results)
    return results

def delete_index(bucket_name=s3vectors_bucket, index_name=indexName):
    """删除索引"""
    s3vectors_client = get_s3vectors_client()
    try:
        s3vectors_client.delete_index(vectorBucketName=bucket_name, indexName=index_name)
        print(f"索引 '{index_name}' 已删除")
        return True
    except Exception as e:
        print(f"删除索引失败: {e}")
        return False

def init_index():
    tools_file = "embedding/toolslist_from_tooluniverse.json"
    cache_file = "embedding/embeddings_cache.json"
    batch_size = 50  # 批处理大小，可以根据需要调整
    
    print(f"Starting tools embedding process with batch size: {batch_size}")
    
    try:
        # 使用新的缓存处理函数，支持批处理
        embeddings, tools_name, tools_desc, genres, cache_data = process_tools_with_cache(
            tools_file=tools_file,
            cache_file=cache_file,
            save_to_s3=True,  # 尝试保存到S3 vectors
            batch_size=batch_size
        )
        
        print(f"Successfully processed {len(tools_name)} tools")
        
        # 如果数据是从缓存加载的，但我们仍然尝试插入到S3 vectors
        if cache_data:
            print("数据来自缓存，现在尝试插入到S3 vectors...")
            try:
                s3vectors_client = get_s3vectors_client()
                
                # 确保索引存在
                if ensure_index_exists(s3vectors_client, s3vectors_bucket, "tools-index"):
                    print("开始插入embeddings到S3 vectors...")
                    insert_embeddings(s3vectors_client, s3vectors_bucket, embeddings, tools_name, tools_desc, indexName="tools-index", genre=genres, cache_file=cache_file, batch_size=batch_size)
                else:
                    print("无法创建或确认索引，跳过插入操作")
                    
            except Exception as e:
                print(f"插入到S3 vectors失败: {e}")
                print("这可能是由于网络问题或AWS配置问题")
        else:
            print("数据已通过process_tools_with_cache处理完成")
        
        # 测试embeddings功能（可选，仅在连接正常时）
        try:
            bedrock_client = get_bedrock_client()
            s3vectors_client = get_s3vectors_client()
            test_embeddings(bedrock_client, s3vectors_client, "Retrieve the drug name based on the specified environmental warnings.", s3vectors_bucket)
        except Exception as e:
            print(f"Test embeddings failed (this is OK if S3 vectors is not working): {e}")
            
    except Exception as e:
        print(f"Main execution failed: {e}")
        print("Make sure AWS credentials are properly configured")

if __name__ == "__main__":
    # 添加命令行参数type，分别是init和delete
    parser = argparse.ArgumentParser()
    parser.add_argument("--type", type=str, help="init/delete/test/generate")
    args = parser.parse_args()
    if args.type == "init":
        init_index()
    elif args.type == "delete":
        delete_index(bucket_name=s3vectors_bucket, index_name=indexName)
    elif args.type == "test":
        test_embeddings("Which drug is the best choice for managing elevated intraocular pressure in a 35-year-old pregnant patient with primary hereditary glaucoma, currently in her second trimester and without any respiratory or cardiac history?")
    elif args.type == "generate":
        generate_toolslist_from_tooluniverse()
    else:
        print("请输入正确的参数")
        exit(1)

    