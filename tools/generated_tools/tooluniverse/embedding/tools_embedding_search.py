# 使用 Amazon Titan 文本嵌入 V2 来生成和打印嵌入。
import boto3 
import json
from strands import tool
from tools.generated_tools.tooluniverse.embedding.tools_embedding import get_bedrock_client, get_s3vectors_client

s3vectors_bucket = "curebench"
indexName = "tools-index"
modelId = "amazon.titan-embed-text-v2:0"

 
@tool(description="""
    Search for similar tools in the Vectors database using semantic similarity.
    
    This is particularly useful for finding appropriate tools based on natural language
    descriptions of tasks or requirements in biomedical and pharmaceutical contexts.
""")
def search_from_s3vectors_by_embeddings(
    input_text: str = "", 
    limit: int = 3
):
    """
    Search for tools using semantic similarity in the S3 Vectors database.
    
    Args:
        input_text (str): The text question/query describing the desired functionality or tool requirements.
        limit (int): The maximum number of similar tools to return. Defaults to 3.
    Returns:
        List[Dict]: A list of dictionaries containing:
            - key (str): The unique identifier/key of the tool
            - metadata (Dict): Tool metadata including:
                - id (str): Tool identifier
                - source_text (str): Tool description
                - genre (str): Tool category/genre
            - distance (float): Similarity distance score (lower is more similar)
            - data (Dict, optional): Vector data if requested
    """
    try:
        # Initialize AWS clients
        bedrock_client = get_bedrock_client()
        s3vectors_client = get_s3vectors_client()
        
        # Validate input parameters
        if not input_text.strip():
            raise ValueError("input_text cannot be empty")
        if not s3vectors_bucket.strip():
            raise ValueError("s3vectors_bucket cannot be empty")
        
        # Generate embedding vector from input text using Bedrock
        request_body = json.dumps({"inputText": input_text.strip()})
        
        print(f"Generating embedding for query: '{input_text[:100]}...'")
        response = bedrock_client.invoke_model(
            modelId=modelId, 
            body=request_body
        )

        # Parse the embedding response
        model_response = json.loads(response["body"].read())
        embedding_vector = model_response["embedding"]

        # Perform similarity search in S3 Vectors
        query_response = s3vectors_client.query_vectors(
            vectorBucketName=s3vectors_bucket,
            indexName=indexName,
            queryVector={"float32": embedding_vector},
            topK=limit,
            returnDistance=True,
            returnMetadata=True
        )
        
        # Extract and format results
        search_results = query_response["vectors"]
        
        print(f"Found {len(search_results)} similar tools:")
        print("--------------------------------")
        print(json.dumps(search_results, indent=2))
        print("--------------------------------")
        return search_results
        
    except Exception as e:
        error_msg = f"Search failed: {str(e)}"
        print(error_msg)
        raise Exception(error_msg)

if __name__ == "__main__":
    """
    Test the tool search functionality with different biomedical queries
    """
    test_queries = [
        "get_pillow_info: Get information about the pillow package. Python Imaging Library fork", 
        "A 25-year-old woman presents with uncomplicated urethral infection caused by *Chlamydia trachomatis*. She is not pregnant and has no known drug allergies. Which of the following is the most appropriate treatment option for her condition?",
        "In pediatric patients aged 6 to 11 years, which dose of Levalbuterol showed the highest mean change in heart rate 30 minutes after the first dose?"
    ]
    
    print("=== Testing Biomedical Tool Search Functionality ===\n")
    
    for i, query in enumerate(test_queries, 1):
        print(f"Test Query {i}: {query}")
        try:
            results = search_from_s3vectors_by_embeddings(
                input_text=query,
                limit=3
            )
            print(f"✓ Successfully found {len(results)} tools for query {i}\n")
        except Exception as e:
            print(f"✗ Test {i} failed: {e}\n")
    
    print("=== Test Complete ===")