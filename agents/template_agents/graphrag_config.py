"""
GraphRAG 配置管理模块
管理 Neptune 和向量存储的连接配置
"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class GraphRAGConfig:
    """GraphRAG 配置类"""

    # ========== 必需字段（无默认值） ==========
    # Neptune 配置
    neptune_endpoint: str

    # 向量存储配置
    vector_store_endpoint: str

    # ========== 可选字段（有默认值） ==========
    # Neptune 配置
    neptune_type: str = "database"  # "database" 或 "analytics"

    # 向量存储配置
    vector_store_type: str = "aoss"  # "aoss" (OpenSearch Serverless) 或其他

    # Agent 配置文件路径
    agent_config_path: str = "agent_templates_config.yaml"

    # AWS 配置
    aws_region: Optional[str] = None
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None

    # 索引配置
    collection_id: str = "agent_templates"
    tenant_id: str = "default"

    # LLM 配置（用于提取图结构和查询响应）
    llm_model: str = "us.anthropic.claude-3-5-sonnet-20240620-v1:0"

    # Embedding 配置
    embedding_model: str = "cohere.embed-english-v3"
    embedding_dimensions: int = 1024  # Cohere v3 默认 1024 维

    @classmethod
    def from_env(cls) -> "GraphRAGConfig":
        """从环境变量加载配置"""
        return cls(
            # Neptune 配置
            neptune_endpoint=os.getenv(
                "NEPTUNE_ENDPOINT",
                "neptune-db://your-cluster.region.neptune.amazonaws.com:8182"
            ),
            neptune_type=os.getenv("NEPTUNE_TYPE", "database"),

            # 向量存储配置
            vector_store_endpoint=os.getenv(
                "VECTOR_STORE_ENDPOINT",
                "aoss://https://your-aoss.region.aoss.amazonaws.com"
            ),
            vector_store_type=os.getenv("VECTOR_STORE_TYPE", "aoss"),

            # Agent 配置
            agent_config_path=os.getenv(
                "AGENT_CONFIG_PATH",
                "agent_templates_config.yaml"
            ),

            # AWS 配置
            aws_region=os.getenv("AWS_DEFAULT_REGION", "us-east-1"),
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),

            # 索引配置
            collection_id=os.getenv("COLLECTION_ID", "agent_templates"),
            tenant_id=os.getenv("TENANT_ID", "default"),

            # LLM 配置
            llm_model=os.getenv("LLM_MODEL", "us.anthropic.claude-3-5-sonnet-20240620-v1:0"),

            # Embedding 配置
            embedding_model=os.getenv("EMBEDDING_MODEL", "cohere.embed-english-v3"),
            embedding_dimensions=int(os.getenv("EMBEDDING_DIMENSIONS", "1024")),
        )

    def get_neptune_connection_string(self) -> str:
        """获取 Neptune 连接字符串"""
        if self.neptune_type == "database":
            return f"neptune-db://{self.neptune_endpoint}"
        elif self.neptune_type == "analytics":
            return f"neptune-graph://{self.neptune_endpoint}"
        else:
            raise ValueError(f"不支持的 Neptune 类型: {self.neptune_type}")

    def get_vector_store_connection_string(self) -> str:
        """获取向量存储连接字符串"""
        if self.vector_store_type == "aoss":
            return f"aoss://{self.vector_store_endpoint}"
        else:
            return self.vector_store_endpoint

    def validate(self) -> bool:
        """验证配置是否完整"""
        required_fields = [
            "neptune_endpoint",
            "vector_store_endpoint",
            "agent_config_path"
        ]

        for field in required_fields:
            value = getattr(self, field)
            if not value or value.startswith("your-"):
                print(f"[WARNING] {field} 配置不完整")
                return False

        return True

    def print_config(self):
        """打印当前配置"""
        print("=" * 60)
        print("GraphRAG 配置信息")
        print("=" * 60)
        print(f"Neptune 端点: {self.neptune_endpoint}")
        print(f"Neptune 类型: {self.neptune_type}")
        print(f"向量存储端点: {self.vector_store_endpoint}")
        print(f"向量存储类型: {self.vector_store_type}")
        print(f"Agent 配置文件: {self.agent_config_path}")
        print(f"AWS 区域: {self.aws_region}")
        print(f"Collection ID: {self.collection_id}")
        print(f"Tenant ID: {self.tenant_id}")
        print(f"LLM 模型: {self.llm_model}")
        print(f"Embedding 模型: {self.embedding_model}")
        print(f"Embedding 维度: {self.embedding_dimensions}")
        print("=" * 60)


# 创建默认配置实例
default_config = GraphRAGConfig.from_env()


if __name__ == "__main__":
    # 测试配置
    config = GraphRAGConfig.from_env()
    config.print_config()

    if config.validate():
        print("\n[OK] 配置验证通过")
    else:
        print("\n[ERROR] 配置验证失败，请检查环境变量")
