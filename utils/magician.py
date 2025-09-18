#!/usr/bin/env python3
from utils.agent_factory import create_agent_from_prompt_template
from utils.structured_output_model.agent_orchestration_result import AgentOrchestrationResult
from strands.multiagent import GraphBuilder, Swarm
from strands.telemetry import StrandsTelemetry
import os
import json

os.environ["BYPASS_TOOL_CONSENT"] = "true"
os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = "http://localhost:4318"
strands_telemetry = StrandsTelemetry()
strands_telemetry.setup_otlp_exporter()

class Magician:
    __magician_agent_path = "prompts/system_agents_prompts/magician_orchestrator.yaml"
    def __init__(self, user_input):
        self.magician_agent = self.get_magician_agent(self.__magician_agent_path,nocallback=True)
        self.user_input = user_input
        self.thinking_result = self.magician_agent(self.user_input)

    def build_magician_agent(self):
        print(f"🎯 正在构建Agent")
        self.orchestration_result = self.magician_agent.structured_output(
            AgentOrchestrationResult,
            f"生成编排配置"
        )
        self.magician_agent = self.dynamic_build_magician_agent(self.orchestration_result)
        return self.magician_agent

    def get_magician_agent(self,template_path,nocallback=False):
        # 创建 agent 的通用参数
        agent_params = {
            "env": "production",
            "version": "latest", 
            "model_id": "default"
        }
        if nocallback:
            agent_params["callback_handler"] = None
        magician_agent = create_agent_from_prompt_template(
            agent_name=template_path, 
            **agent_params
        )
        return magician_agent

    def dynamic_build_magician_agent(self,orchestration_result: AgentOrchestrationResult):
        if orchestration_result.orchestration_type == "agent":
            return self.build_single_magician_agent(orchestration_result)
        elif orchestration_result.orchestration_type == "graph":
            return self.build_magician_graph(orchestration_result)
        elif orchestration_result.orchestration_type == "swarm":
            return self.build_magician_swarm(orchestration_result)
        else:
            raise ValueError(f"编排类型不支持: {orchestration_result.orchestration_type}")
        return None

    def build_single_magician_agent(self,orchestration_result: AgentOrchestrationResult):
        """
        构建单个Agent对象
        
        Args:
            orchestration_result: Agent编排结果对象
            
        Returns:
            Agent对象
        """
        try:
            # 从编排结果中提取选中的Agent信息
            agent_info = orchestration_result.orchestration_result.get("agent_info")
            if not agent_info:
                # 如果没有agent_info，尝试从selected_agent获取
                agent_info = orchestration_result.orchestration_result.get("selected_agent")
            
            if not agent_info:
                raise ValueError("编排结果中未找到Agent信息")
            
            # 获取Agent的template_path
            template_path = agent_info.get("template_path")
            if not template_path:
                raise ValueError("Agent信息中未找到template_path")
            
            print(f"🤖 正在创建Agent: {agent_info.get('agent_name', 'Unknown')}")
            print(f"📁 模板路径: {template_path}")
            
            # 使用get_magician_agent创建Agent
            agent = self.get_magician_agent(template_path)
            
            print(f"✅ Agent创建成功")
            return agent
            
        except Exception as e:
            print(f"❌ 创建Agent失败: {e}")
            return None


    def build_magician_graph(self,orchestration_result: AgentOrchestrationResult):
        """
        构建Graph编排对象
        
        Args:
            orchestration_result: Agent编排结果对象
            
        Returns:
            Graph对象
        """
        try:
            orchestration_data = orchestration_result.orchestration_result
            
            # 添加调试信息
            print(f"🔍 调试信息 - orchestration_data type: {type(orchestration_data)}")
            
            # 如果是Pydantic模型，转换为字典
            if hasattr(orchestration_data, 'model_dump'):
                orchestration_data = orchestration_data.model_dump()
            elif hasattr(orchestration_data, 'dict'):
                orchestration_data = orchestration_data.dict()
            else:
                print(f"🔍 调试信息 - 未知类型，尝试直接访问: {orchestration_data}")
            
            # 尝试从新的数据结构中获取nodes和connections
            agents = orchestration_data.get("agents", [])
            connections = orchestration_data.get("connections", [])
            
            # 如果没有找到agents，尝试从nodes获取
            if not agents:
                agents = orchestration_data.get("nodes", [])
            
            # 如果没有找到connections，尝试从edges获取
            if not connections:
                connections = orchestration_data.get("edges", [])
            
            # 如果没有找到agents，尝试从graph_structure获取
            if not agents:
                graph_structure = orchestration_data.get("graph_structure")
                if graph_structure:
                    agents = graph_structure.get("nodes", [])
                    connections = graph_structure.get("edges", [])
            if not agents:
                raise ValueError("编排结果中未找到agents或nodes信息")
            
            print(f"🏗️ 正在构建Graph编排，包含 {len(agents)} 个节点")
            
            # 创建GraphBuilder
            builder = GraphBuilder()
            
            # 创建Agent实例并添加节点
            agent_instances = {}
            for node_data in agents:
                # 处理不同的数据结构格式
                node_id = node_data.get("node_id") or node_data.get("id")
                
                # 处理不同的agent信息格式
                agent_info = None
                if "agent_info" in node_data:
                    agent_info = node_data.get("agent_info")
                elif "agent" in node_data:
                    agent_info = node_data.get("agent")
                else:
                    agent_info = node_data  # 如果agent信息直接在节点中
                
                if not node_id:
                    raise ValueError(f"节点缺少node_id或id: {node_data}")
                
                template_path = agent_info.get("template_path")
                if not template_path:
                    raise ValueError(f"节点 {node_id} 缺少template_path")
                
                print(f"📋 添加节点: {node_id} (模板: {template_path})")
                
                # 创建Agent实例
                agent = self.get_magician_agent(template_path)
                agent_instances[node_id] = agent
                
                # 添加节点到图
                builder.add_node(agent, node_id)
            
            # 添加边 - 定义工作流顺序
            print("🔗 配置工作流连接...")
            
            # 首先处理connections数组
            for connection in connections:
                # 处理不同的连接格式
                source = None
                target = None
                
                # 新格式：connections数组中的对象
                if "from" in connection and "to" in connection:
                    from_data = connection.get("from", {})
                    to_data = connection.get("to", {})
                    source = from_data.get("agent_id") if isinstance(from_data, dict) else from_data
                    target = to_data.get("agent_id") if isinstance(to_data, dict) else to_data
                # 旧格式：edges数组中的对象
                elif "source" in connection and "target" in connection:
                    source = connection.get("source")
                    target = connection.get("target")
                # 兼容格式：from/to字段
                elif "from" in connection:
                    source = connection.get("from")
                    target = connection.get("to")
                
                if not source or not target:
                    print(f"⚠️ 跳过无效连接: {connection}")
                    continue
                
                print(f"  {source} -> {target}")
                builder.add_edge(source, target)
            
            # 如果没有connections，尝试从节点的depends_on字段构建连接
            if not connections:
                print("🔗 从节点的depends_on字段构建连接...")
                for node_data in agents:
                    node_id = node_data.get("node_id") or node_data.get("id")
                    depends_on = node_data.get("depends_on", [])
                    
                    if depends_on and isinstance(depends_on, list):
                        for dependency in depends_on:
                            print(f"  {dependency} -> {node_id}")
                            builder.add_edge(dependency, node_id)
            
            # 构建图
            graph = builder.build()
            print("✅ Graph构建完成")
            
            return graph
            
        except Exception as e:
            print(f"❌ 构建Graph失败: {e}")
            import traceback
            traceback.print_exc()
            return None


    def build_magician_swarm(self,orchestration_result: AgentOrchestrationResult):
        """
        构建Swarm编排对象
        
        Args:
            orchestration_result: Agent编排结果对象
            
        Returns:
            Swarm对象
        """
        try:
            orchestration_data = orchestration_result.orchestration_result
            
            # 尝试从新的数据结构中获取swarm信息
            swarm_structure = orchestration_data.get("swarm_structure")
            if not swarm_structure:
                # 如果没有swarm_structure，尝试直接从orchestration_result获取agents
                swarm_agents = orchestration_data.get("agents", [])
                if not swarm_agents:
                    raise ValueError("编排结果中未找到swarm_structure或agents信息")
            else:
                swarm_agents = swarm_structure.get("agents", [])
            
            if not swarm_agents:
                raise ValueError("Swarm结构中没有Agent")
            
            print(f"🐝 正在构建Swarm编排，包含 {len(swarm_agents)} 个Agent")
            
            # 创建Agent实例列表
            agent_instances = []
            entry_point_agent = None
            
            for swarm_agent in swarm_agents:
                # 处理不同的数据结构格式
                agent_id = swarm_agent.get("agent_id") or swarm_agent.get("id")
                agent_info = swarm_agent.get("agent_info") or swarm_agent
                role = swarm_agent.get("role", "worker")
                priority = swarm_agent.get("priority", 1)
                
                if not agent_id:
                    raise ValueError(f"Swarm Agent缺少agent_id或id: {swarm_agent}")
                
                template_path = agent_info.get("template_path")
                if not template_path:
                    raise ValueError(f"Swarm Agent {agent_id} 缺少template_path")
                
                print(f"📋 添加Swarm Agent: {agent_id} (角色: {role}, 优先级: {priority})")
                
                # 创建Agent实例
                agent = self.get_magician_agent(template_path)
                agent_instances.append(agent)
                
                # 如果是coordinator角色且优先级最高，设为entry_point
                if role == "coordinator" and priority == 1 and entry_point_agent is None:
                    entry_point_agent = agent
                    print(f"🎯 设置入口点Agent: {agent_id}")
            
            # 如果没有找到coordinator，使用第一个Agent作为入口点
            if entry_point_agent is None:
                entry_point_agent = agent_instances[0]
                print(f"🎯 默认设置第一个Agent为入口点")
            
            # 创建Swarm对象
            swarm = Swarm(
                agent_instances,
                entry_point=entry_point_agent, 
                max_handoffs=20,
                max_iterations=20,
                execution_timeout=900.0, 
                node_timeout=300.0, 
                repetitive_handoff_detection_window=8,
                repetitive_handoff_min_unique_agents=3
            )
            
            print("✅ Swarm构建完成")
            return swarm
            
        except Exception as e:
            print(f"❌ 构建Swarm失败: {e}")
            import traceback
            traceback.print_exc()
            return None