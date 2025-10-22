# 延迟导入，避免在模块加载时建立网络连接
# from tooluniverse import ToolUniverse
from strands import tool
import json
import yaml
from neo4j import GraphDatabase
import logging
from typing import Dict, List, Any
import os

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Neo4jKnowledgeGraph:
    def __init__(self, config_file="tools/generated_tools/tooluniverse/neo4j/neo4j_config.yaml"):
        """初始化Neo4j知识图谱连接"""
        self.config = self.load_config(config_file)
        self.driver = None
        self.connect()
    
    def load_config(self, config_file: str) -> Dict:
        """加载Neo4j配置"""
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            return config['neo4j']
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            # 使用默认配置
            return {
                'uri': 'bolt://localhost:7687',
                'username': 'neo4j',
                'password': 'neo4jneo4j'
            }
    
    def connect(self):
        """连接到Neo4j数据库"""
        try:
            self.driver = GraphDatabase.driver(
                self.config['uri'],
                auth=(self.config['username'], self.config['password'])
            )
            # 测试连接
            with self.driver.session() as session:
                session.run("RETURN 1")
            logger.info("成功连接到Neo4j数据库")
        except Exception as e:
            logger.error(f"连接Neo4j数据库失败: {e}")
            raise
    
    def close(self):
        """关闭数据库连接"""
        if self.driver:
            self.driver.close()
    
    def clear_database(self):
        """清空数据库"""
        with self.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
            logger.info("已清空数据库")
    
    def create_constraints_and_indexes(self):
        """创建约束和索引"""
        constraints_and_indexes = [
            "CREATE CONSTRAINT tool_name_unique IF NOT EXISTS FOR (t:Tool) REQUIRE t.name IS UNIQUE",
            "CREATE CONSTRAINT parameter_name_unique IF NOT EXISTS FOR (p:Parameter) REQUIRE p.name IS UNIQUE",
            "CREATE CONSTRAINT genre_name_unique IF NOT EXISTS FOR (g:Genre) REQUIRE g.name IS UNIQUE",
            "CREATE INDEX tool_name_index IF NOT EXISTS FOR (t:Tool) ON (t.name)",
            "CREATE INDEX parameter_name_index IF NOT EXISTS FOR (p:Parameter) ON (p.name)",
            "CREATE INDEX genre_name_index IF NOT EXISTS FOR (g:Genre) ON (g.name)"
        ]
        
        with self.driver.session() as session:
            for constraint in constraints_and_indexes:
                try:
                    session.run(constraint)
                    logger.info(f"成功创建约束/索引: {constraint.split('IF NOT EXISTS')[0]}")
                except Exception as e:
                    logger.warning(f"创建约束/索引失败: {e}")
    
    def create_tool_node(self, tool_name: str, tool_desc: str):
        """创建Tool节点"""
        with self.driver.session() as session:
            session.run("""
                MERGE (t:Tool {name: $name})
                SET t.description = $description
                RETURN t
            """, name=tool_name, description=tool_desc)
    
    def create_parameter_node(self, param_name: str, param_desc: str, param_type: str, default_value: Any = None, required: bool = False):
        """创建Parameter节点"""
        with self.driver.session() as session:
            session.run("""
                MERGE (p:Parameter {name: $name})
                SET p.description = $description,
                    p.type = $type,
                    p.default_value = $default_value,
                    p.required = $required
                RETURN p
            """, name=param_name, description=param_desc, type=param_type, default_value=default_value, required=required)
    
    def create_genre_node(self, genre_name: str):
        """创建Genre节点"""
        with self.driver.session() as session:
            session.run("""
                MERGE (g:Genre {name: $name})
                RETURN g
            """, name=genre_name)
    
    def create_tool_parameter_relationship(self, tool_name: str, param_name: str):
        """创建Tool和Parameter之间的关系"""
        with self.driver.session() as session:
            session.run("""
                MATCH (t:Tool {name: $tool_name})
                MATCH (p:Parameter {name: $param_name})
                MERGE (t)-[:HAS_PARAMETER]->(p)
            """, tool_name=tool_name, param_name=param_name)
    
    def create_tool_genre_relationship(self, tool_name: str, genre_name: str):
        """创建Tool和Genre之间的关系"""
        with self.driver.session() as session:
            session.run("""
                MATCH (t:Tool {name: $tool_name})
                MATCH (g:Genre {name: $genre_name})
                MERGE (t)-[:BELONGS_TO_GENRE]->(g)
            """, tool_name=tool_name, genre_name=genre_name)

def load_local_tools_list(graph_tools_list, tools_list_file="embedding/toolslist_from_tooluniverse.json"):
    """加载本地工具列表"""
    with open(tools_list_file, 'r', encoding='utf-8') as f:
        tools_list = json.load(f)
    for i in tools_list:
        graph_tools_list[i["tool_name"]] = {}
        graph_tools_list[i["tool_name"]]["desc"] = i["desc"]
        graph_tools_list[i["tool_name"]]["genre"] = i["genre"]
    return graph_tools_list

def load_tools_parameters(graph_tools_list, tu):
    """加载工具参数信息"""
    for tool_name in graph_tools_list:
        try:
            tool_desc = tu.get_tool_description(tool_name=tool_name)
            if 'parameter' in tool_desc and 'properties' in tool_desc['parameter']:
                # 获取参数属性和必需参数列表
                properties = tool_desc["parameter"]['properties']
                required_params = tool_desc["parameter"].get('required', [])
                
                # 为每个参数添加required字段
                for param_name, param_info in properties.items():
                    param_info['required'] = param_name in required_params
                
                graph_tools_list[tool_name]["parameter"] = properties
            else:
                graph_tools_list[tool_name]["parameter"] = {}
        except Exception as e:
            logger.warning(f"获取工具 {tool_name} 的参数信息失败: {e}")
            graph_tools_list[tool_name]["parameter"] = {}
    return graph_tools_list

def create_knowledge_graph(graph_tools_list, neo4j_kg):
    """创建知识图谱"""
    logger.info(f"开始创建知识图谱，共 {len(graph_tools_list)} 个工具")
    
    # 清空数据库（可选）
    if neo4j_kg.config.get('knowledge_graph', {}).get('clear_database_before_build', False):
        neo4j_kg.clear_database()
    
    # 创建约束和索引
    neo4j_kg.create_constraints_and_indexes()
    
    # 收集所有唯一的Genre
    unique_genres = set()
    for tool_data in graph_tools_list.values():
        if 'genre' in tool_data:
            unique_genres.add(tool_data['genre'])
    
    # 创建Genre节点
    logger.info(f"创建 {len(unique_genres)} 个Genre节点")
    for genre in unique_genres:
        neo4j_kg.create_genre_node(genre)
    
    # 创建Tool节点和Parameter节点，并建立关系
    for tool_name, tool_data in graph_tools_list.items():
        logger.info(f"处理工具: {tool_name}")
        
        # 创建Tool节点
        tool_desc = tool_data.get('desc', '')
        neo4j_kg.create_tool_node(tool_name, tool_desc)
        
        # 创建Tool-Genre关系
        if 'genre' in tool_data:
            neo4j_kg.create_tool_genre_relationship(tool_name, tool_data['genre'])
        
        # 创建Parameter节点和Tool-Parameter关系
        if 'parameter' in tool_data and tool_data['parameter']:
            for param_name, param_info in tool_data['parameter'].items():
                # 创建Parameter节点
                param_desc = param_info.get('description', '')
                param_type = param_info.get('type', 'string')
                default_value = param_info.get('default', None)
                required = param_info.get('required', False)
                
                neo4j_kg.create_parameter_node(param_name, param_desc, param_type, default_value, required)
                
                # 创建Tool-Parameter关系
                neo4j_kg.create_tool_parameter_relationship(tool_name, param_name)
    
    logger.info("知识图谱创建完成")

def get_graph_statistics(neo4j_kg):
    """获取图谱统计信息"""
    with neo4j_kg.driver.session() as session:
        stats = {}
        
        # 统计节点数量
        result = session.run("MATCH (n) RETURN labels(n)[0] as label, count(n) as count")
        for record in result:
            label = record['label']
            count = record['count']
            stats[f"{label}_count"] = count
        
        # 统计关系数量
        result = session.run("MATCH ()-[r]->() RETURN type(r) as relationship_type, count(r) as count")
        for record in result:
            rel_type = record['relationship_type']
            count = record['count']
            stats[f"{rel_type}_count"] = count
        
        return stats

if __name__ == "__main__":
    try:
        # 延迟导入ToolUniverse，避免网络连接问题
        try:
            from tooluniverse import ToolUniverse
            tu = ToolUniverse()
        except Exception as e:
            logger.warning(f"无法初始化ToolUniverse: {e}")
            exit(1)
        tu.load_tools()
        
        # 初始化Neo4j知识图谱
        neo4j_kg = Neo4jKnowledgeGraph()
        
        # 加载工具数据
        graph_tools_list = {}
        load_local_tools_list(graph_tools_list)
        load_tools_parameters(graph_tools_list, tu)
        
        # 创建知识图谱
        create_knowledge_graph(graph_tools_list, neo4j_kg)
        
        # 显示统计信息
        stats = get_graph_statistics(neo4j_kg)
        logger.info("知识图谱统计信息:")
        for key, value in stats.items():
            logger.info(f"  {key}: {value}")
        
    except Exception as e:
        logger.error(f"执行过程中发生错误: {e}")
    finally:
        if 'neo4j_kg' in locals():
            neo4j_kg.close()