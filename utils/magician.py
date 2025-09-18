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
    __magician_agent_path = "prompts/system_agents_prompts/magician_workflow/magician_orchestrator.yaml"
    
    # Agent缓存，避免重复创建相同的Agent
    _agent_cache = {}
    
    def __init__(self, user_input):
        self.magician_agent = self.get_magician_agent(self.__magician_agent_path, nocallback=True)
        self.user_input = user_input
        self.thinking_result = self.magician_agent(self.user_input)
    
    @classmethod
    def clear_agent_cache(cls):
        """清空Agent缓存"""
        cls._agent_cache.clear()
        print("🧹 Agent缓存已清空")
    
    @classmethod
    def get_cache_info(cls):
        """获取缓存信息"""
        return {
            "cached_agents": len(cls._agent_cache),
            "cache_keys": list(cls._agent_cache.keys())
        }

    def get_magician_description(self):
        # 编写一个总结信息，能够说明当前构建好的magician的类型、参与的agent、基础描述，根据类型不同，graph还应能给出具体agent关系，swarm还应能给出具体agent角色
        # 要尽可能易读而不是json内容
        print("🎯 正在获取Magician描述")
        print("当前支持团队类型为:",self.orchestration_result.orchestration_type)
        print("当前支持团队数量为:",len(self.orchestration_result.orchestration_result.agents))
        if self.orchestration_result.orchestration_type == "agent":
            print("当前支持团队为:",self.orchestration_result.orchestration_result.agent.agent_name)
        elif self.orchestration_result.orchestration_type == "graph":
            print("当前支持团队关系为:",self.orchestration_result.orchestration_result.connections.source)
            print("当前支持团队关系为:",self.orchestration_result.orchestration_result.connections.target)
            print("当前支持团队关系为:",self.orchestration_result.orchestration_result.connections.edge_type)
            print("当前支持团队关系为:",self.orchestration_result.orchestration_result.connections.condition)
            print("当前支持团队关系为:",self.orchestration_result.orchestration_result.connections.source_agent.agent_name)
            print("当前支持团队关系为:",self.orchestration_result.orchestration_result.connections.target_agent.agent_name)
        elif self.orchestration_result.orchestration_type == "swarm":
            print("当前支持团队角色为:",self.orchestration_result.orchestration_result.swarm_roles.role)
            print("当前支持团队入口点为:",self.orchestration_result.orchestration_result.swarm_roles.agent.agent_name)
            print("当前支持团队通信模式为:",self.orchestration_result.orchestration_result.swarm_roles.communication_pattern)
            print("当前支持团队优先级为:",self.orchestration_result.orchestration_result.swarm_roles.priority)

    def build_magician_agent(self):
        print(f"🎯 正在构建Agent")
        self.orchestration_result = self.magician_agent.structured_output(
            AgentOrchestrationResult,
            f"生成编排配置"
        )
        self.magician_agent = self.dynamic_build_magician_agent(self.orchestration_result)
        print(self.orchestration_result)
        return self.magician_agent

    def get_magician_agent(self, template_path, nocallback=False, custom_params=None):
        """
        创建Magician Agent实例（带缓存）
        
        Args:
            template_path: Agent模板路径
            nocallback: 是否禁用回调处理器
            custom_params: 自定义参数
            
        Returns:
            Agent实例
        """
        try:
            # 创建缓存键
            cache_key = f"{template_path}_{nocallback}_{hash(str(custom_params)) if custom_params else 'default'}"
            
            # 检查缓存
            if cache_key in self._agent_cache:
                print(f"📦 使用缓存的Agent: {template_path}")
                return self._agent_cache[cache_key]
            
            # 创建 agent 的通用参数
            agent_params = {
                "env": "production",
                "version": "latest", 
                "model_id": "default"
            }
            
            # 合并自定义参数
            if custom_params:
                agent_params.update(custom_params)
            
            # 禁用回调处理器
            if nocallback:
                agent_params["callback_handler"] = None
            
            # 验证模板路径
            if not template_path:
                raise ValueError("模板路径不能为空")
            
            print(f"🏗️ 创建新Agent: {template_path}")
            
            # 创建Agent实例
            magician_agent = create_agent_from_prompt_template(
                agent_name=template_path, 
                **agent_params
            )
            
            # 缓存Agent实例
            self._agent_cache[cache_key] = magician_agent
            print(f"💾 Agent已缓存: {template_path}")
            
            return magician_agent
            
        except Exception as e:
            print(f"❌ 创建Agent失败 (模板: {template_path}): {e}")
            raise

    def dynamic_build_magician_agent(self, orchestration_result: AgentOrchestrationResult):
        if orchestration_result.orchestration_type == "agent":
            return self.build_single_magician_agent(orchestration_result)
        elif orchestration_result.orchestration_type == "graph":
            return self.build_magician_graph(orchestration_result)
        elif orchestration_result.orchestration_type == "swarm":
            return self.build_magician_swarm(orchestration_result)
        else:
            raise ValueError(f"编排类型不支持: {orchestration_result.orchestration_type}")

    def build_single_magician_agent(self,orchestration_result: AgentOrchestrationResult):
        """
        构建单个Agent对象
        
        Args:
            orchestration_result: Agent编排结果对象
            
        Returns:
            Agent对象
        """
        try:
            orchestration_data = orchestration_result.orchestration_result
            
            # 如果是Pydantic模型，转换为字典
            if hasattr(orchestration_data, 'model_dump'):
                orchestration_data = orchestration_data.model_dump()
            elif hasattr(orchestration_data, 'dict'):
                orchestration_data = orchestration_data.dict()
            
            # 尝试多种方式获取Agent信息
            agent_info = None
            
            # 方式1：直接从orchestration_result获取
            if isinstance(orchestration_data, dict):
                agent_info = orchestration_data.get("agent_info")
                
                # 方式2：从selected_agent获取
                if not agent_info:
                    agent_info = orchestration_data.get("selected_agent")
                
                # 方式3：从agent字段获取
                if not agent_info:
                    agent_info = orchestration_data.get("agent")
                
                # 方式4：从available_agents中获取第一个
                if not agent_info:
                    available_agents = orchestration_data.get("available_agents", [])
                    if available_agents and len(available_agents) > 0:
                        agent_info = available_agents[0]
                
                # 方式5：如果orchestration_data本身就是agent信息
                if not agent_info and "template_path" in orchestration_data:
                    agent_info = orchestration_data
            
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
            import traceback
            traceback.print_exc()
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
            
            # 如果是Pydantic模型，转换为字典
            if hasattr(orchestration_data, 'model_dump'):
                orchestration_data = orchestration_data.model_dump()
            elif hasattr(orchestration_data, 'dict'):
                orchestration_data = orchestration_data.dict()
            
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
                
                # 尝试多种可能的字段名
                template_path = agent_info.get("template_path") or agent_info.get("agent_template")
                if not template_path:
                    raise ValueError(f"节点 {node_id} 缺少template_path或agent_template")
                
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


    def build_magician_swarm(self, orchestration_result: AgentOrchestrationResult):
        """
        构建Swarm编排对象
        
        Args:
            orchestration_result: Agent编排结果对象
            
        Returns:
            Swarm对象
        """
        try:
            orchestration_data = orchestration_result.orchestration_result
            
            # 如果是Pydantic模型，转换为字典
            if hasattr(orchestration_data, 'model_dump'):
                orchestration_data = orchestration_data.model_dump()
            elif hasattr(orchestration_data, 'dict'):
                orchestration_data = orchestration_data.dict()
            
            # 尝试多种方式获取swarm信息
            swarm_agents = []
            swarm_config = {}
            
            # 方式1：从swarm_structure获取
            swarm_structure = orchestration_data.get("swarm_structure")
            if swarm_structure:
                swarm_agents = swarm_structure.get("agents", [])
                swarm_config = swarm_structure.get("config", {})
            
            # 方式2：直接从orchestration_result获取agents
            if not swarm_agents:
                swarm_agents = orchestration_data.get("agents", [])
                swarm_config = orchestration_data.get("swarm_config", {})
            
            # 方式3：从alternative_solutions中获取swarm方案
            if not swarm_agents and orchestration_result.alternative_solutions:
                for solution in orchestration_result.alternative_solutions:
                    if solution.get("orchestration_type") == "swarm":
                        swarm_agents = solution.get("agents", [])
                        swarm_config = solution.get("swarm_config", {})
                        break
            
            if not swarm_agents:
                raise ValueError("编排结果中未找到swarm_structure、agents或alternative_solutions信息")
            
            print(f"🐝 正在构建Swarm编排，包含 {len(swarm_agents)} 个Agent")
            
            # 解析Swarm配置参数
            swarm_params = self._parse_swarm_config(swarm_config, len(swarm_agents))
            
            # 创建Agent实例列表和角色映射
            agent_instances = []
            agent_roles = {}
            entry_point_agent = None
            coordinator_candidates = []
            
            # 按优先级排序Agent（优先级数字越小越优先）
            sorted_agents = sorted(swarm_agents, key=lambda x: x.get("priority", 999))
            
            for swarm_agent in sorted_agents:
                # 处理不同的数据结构格式
                agent_id = swarm_agent.get("agent_id") or swarm_agent.get("id") or f"agent_{len(agent_instances)}"
                agent_info = swarm_agent.get("agent_info") or swarm_agent
                role = swarm_agent.get("role", "worker")
                priority = swarm_agent.get("priority", 999)
                capabilities = swarm_agent.get("capabilities", [])
                communication_pattern = swarm_agent.get("communication_pattern", "broadcast")
                
                # 验证必要信息
                if not agent_info:
                    raise ValueError(f"Swarm Agent {agent_id} 缺少agent_info")
                
                template_path = agent_info.get("template_path")
                if not template_path:
                    raise ValueError(f"Swarm Agent {agent_id} 缺少template_path")
                
                print(f"📋 添加Swarm Agent: {agent_id}")
                print(f"   ├─ 角色: {role}")
                print(f"   ├─ 优先级: {priority}")
                print(f"   ├─ 模板: {template_path}")
                if capabilities:
                    print(f"   ├─ 能力: {', '.join(capabilities[:3])}{'...' if len(capabilities) > 3 else ''}")
                print(f"   └─ 通信模式: {communication_pattern}")
                
                # 创建Agent实例
                try:
                    agent = self.get_magician_agent(template_path)
                    if agent is not None:  # 确保Agent创建成功
                        agent_instances.append(agent)
                        agent_roles[agent_id] = {
                            "role": role,
                            "priority": priority,
                            "capabilities": capabilities,
                            "communication_pattern": communication_pattern,
                            "agent": agent
                        }
                        
                        # 收集coordinator候选
                        if role in ["coordinator", "leader", "manager"]:
                            coordinator_candidates.append({
                                "agent_id": agent_id,
                                "agent": agent,
                                "priority": priority
                            })
                    else:
                        print(f"⚠️ Agent {agent_id} 创建失败，返回None")
                        continue
                        
                except Exception as e:
                    print(f"⚠️ 创建Agent {agent_id} 失败: {e}")
                    continue
            
            if not agent_instances:
                raise ValueError("没有成功创建任何Agent实例")
            
            # 智能选择入口点Agent
            entry_point_agent = self._select_entry_point_agent(coordinator_candidates, agent_instances, agent_roles)
            
            # 创建Swarm对象
            swarm = Swarm(
                agent_instances,
                **swarm_params
            )
            
            print("✅ Swarm构建完成")
            print(f"🎯 入口点Agent: {getattr(entry_point_agent, 'name', 'Unknown')}")
            print(f"📊 Swarm配置: {swarm_params}")
            
            return swarm
            
        except Exception as e:
            print(f"❌ 构建Swarm失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _parse_swarm_config(self, config: dict, agent_count: int) -> dict:
        """
        解析Swarm配置参数
        
        Args:
            config: Swarm配置字典
            agent_count: Agent数量
            
        Returns:
            解析后的Swarm参数
        """
        # 默认配置
        default_config = {
            "max_handoffs": min(agent_count * 3, 20),
            "max_iterations": min(agent_count * 5, 30),
            "execution_timeout": 900.0,
            "node_timeout": 300.0,
            "repetitive_handoff_detection_window": min(agent_count, 8),
            "repetitive_handoff_min_unique_agents": min(max(agent_count // 2, 2), 5)
        }
        
        # 合并用户配置
        swarm_params = {**default_config}
        
        # 映射配置字段
        config_mapping = {
            "max_handoffs": "max_handoffs",
            "max_iterations": "max_iterations", 
            "execution_timeout": "execution_timeout",
            "node_timeout": "node_timeout",
            "handoff_detection_window": "repetitive_handoff_detection_window",
            "min_unique_agents": "repetitive_handoff_min_unique_agents"
        }
        
        for config_key, param_key in config_mapping.items():
            if config_key in config:
                swarm_params[param_key] = config[config_key]
        
        return swarm_params
    
    def _select_entry_point_agent(self, coordinator_candidates: list, agent_instances: list, agent_roles: dict):
        """
        智能选择入口点Agent
        
        Args:
            coordinator_candidates: coordinator候选列表
            agent_instances: Agent实例列表
            agent_roles: Agent角色映射
            
        Returns:
            选中的入口点Agent
        """
        # 策略1：如果有coordinator角色，选择优先级最高的
        if coordinator_candidates:
            # 按优先级排序
            sorted_candidates = sorted(coordinator_candidates, key=lambda x: x["priority"])
            entry_point = sorted_candidates[0]["agent"]
            print(f"🎯 选择coordinator角色作为入口点: {sorted_candidates[0]['agent_id']}")
            return entry_point
        
        # 策略2：选择优先级最高的Agent
        highest_priority_agent = None
        highest_priority = float('inf')
        
        for agent_id, role_info in agent_roles.items():
            if role_info["priority"] < highest_priority:
                highest_priority = role_info["priority"]
                highest_priority_agent = role_info["agent"]
        
        if highest_priority_agent:
            print(f"🎯 选择最高优先级Agent作为入口点 (优先级: {highest_priority})")
            return highest_priority_agent
        
        # 策略3：默认选择第一个Agent
        print(f"🎯 默认选择第一个Agent作为入口点")
        return agent_instances[0]