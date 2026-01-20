'use client';

import { useEffect, useRef, useState, useMemo, useCallback } from 'react';
import dynamic from 'next/dynamic';

// 动态导入 ForceGraph2D 以避免 SSR 问题
const ForceGraph2D = dynamic(() => import('react-force-graph-2d'), { ssr: false });

export interface GraphNode {
  id: string;
  name: string;
  type: string;
  group?: number;
  val?: number;
  color?: string;
  description?: string;
}

export interface GraphLink {
  source: string;
  target: string;
  label?: string;
  color?: string;
}

export interface GraphData {
  nodes: GraphNode[];
  links: GraphLink[];
}

// 节点类型颜色映射
const NODE_COLORS: Record<string, string> = {
  // 需求分析阶段
  requirement: '#3B82F6',      // 蓝色 - 功能需求
  non_functional: '#8B5CF6',   // 紫色 - 非功能需求
  constraint: '#F59E0B',       // 橙色 - 约束
  assumption: '#10B981',       // 绿色 - 假设
  scope: '#EC4899',            // 粉色 - 范围
  
  // 系统架构阶段
  agent: '#EF4444',            // 红色 - Agent
  data_model: '#06B6D4',       // 青色 - 数据模型
  flow: '#84CC16',             // 黄绿色 - 交互流程
  step: '#A3E635',             // 浅绿色 - 步骤
  
  // Agent设计阶段
  capability: '#F97316',       // 橙色 - 能力
  tool: '#14B8A6',             // 蓝绿色 - 工具
  decision: '#6366F1',         // 靛蓝色 - 决策
  
  // Prompt工程阶段
  prompt_section: '#D946EF',   // 品红色 - Prompt部分
  scenario: '#0EA5E9',         // 天蓝色 - 测试场景
  
  // 通用
  root: '#1F2937',             // 深灰色 - 根节点
  default: '#6B7280',          // 灰色 - 默认
};

// 从需求分析文档提取图数据
function extractRequirementsGraph(data: any): GraphData {
  const nodes: GraphNode[] = [];
  const links: GraphLink[] = [];
  
  const doc = data.requirements_document;
  if (!doc) return { nodes, links };
  
  // 根节点
  const rootId = 'root';
  nodes.push({ id: rootId, name: doc.feature_name || '项目', type: 'root', val: 30 });
  
  // 功能需求
  if (doc.functional_requirements?.length) {
    const frGroupId = 'fr_group';
    nodes.push({ id: frGroupId, name: '功能需求', type: 'requirement', val: 20 });
    links.push({ source: rootId, target: frGroupId, label: '包含' });
    
    doc.functional_requirements.forEach((fr: any, i: number) => {
      const frId = `fr_${i}`;
      nodes.push({ 
        id: frId, 
        name: fr.title || fr.id, 
        type: 'requirement', 
        val: 10,
        description: fr.user_story 
      });
      links.push({ source: frGroupId, target: frId });
      
      // 依赖关系
      if (fr.dependencies?.length) {
        fr.dependencies.forEach((dep: string) => {
          const depIndex = doc.functional_requirements.findIndex((r: any) => r.id === dep);
          if (depIndex >= 0) {
            links.push({ source: frId, target: `fr_${depIndex}`, label: '依赖', color: '#F59E0B' });
          }
        });
      }
    });
  }
  
  // 非功能需求
  if (doc.non_functional_requirements) {
    const nfrGroupId = 'nfr_group';
    nodes.push({ id: nfrGroupId, name: '非功能需求', type: 'non_functional', val: 20 });
    links.push({ source: rootId, target: nfrGroupId, label: '包含' });
    
    Object.entries(doc.non_functional_requirements).forEach(([category, items]: [string, any], i) => {
      const catId = `nfr_${i}`;
      nodes.push({ id: catId, name: category, type: 'non_functional', val: 12 });
      links.push({ source: nfrGroupId, target: catId });
      
      if (Array.isArray(items)) {
        items.forEach((item: string, j: number) => {
          const itemId = `nfr_${i}_${j}`;
          nodes.push({ id: itemId, name: item.substring(0, 30) + (item.length > 30 ? '...' : ''), type: 'non_functional', val: 6, description: item });
          links.push({ source: catId, target: itemId });
        });
      }
    });
  }
  
  // 约束
  if (doc.constraints?.length) {
    const constGroupId = 'const_group';
    nodes.push({ id: constGroupId, name: '约束条件', type: 'constraint', val: 15 });
    links.push({ source: rootId, target: constGroupId, label: '包含' });
    
    doc.constraints.forEach((c: string, i: number) => {
      const cId = `const_${i}`;
      nodes.push({ id: cId, name: c.substring(0, 25) + (c.length > 25 ? '...' : ''), type: 'constraint', val: 6, description: c });
      links.push({ source: constGroupId, target: cId });
    });
  }
  
  // 范围
  if (doc.scope) {
    const scopeGroupId = 'scope_group';
    nodes.push({ id: scopeGroupId, name: '项目范围', type: 'scope', val: 15 });
    links.push({ source: rootId, target: scopeGroupId, label: '定义' });
    
    if (doc.scope.included?.length) {
      const inclId = 'scope_included';
      nodes.push({ id: inclId, name: '包含范围', type: 'scope', val: 10 });
      links.push({ source: scopeGroupId, target: inclId });
      doc.scope.included.slice(0, 5).forEach((item: string, i: number) => {
        const itemId = `scope_incl_${i}`;
        nodes.push({ id: itemId, name: item.substring(0, 20) + '...', type: 'scope', val: 5, description: item });
        links.push({ source: inclId, target: itemId });
      });
    }
    
    if (doc.scope.excluded?.length) {
      const exclId = 'scope_excluded';
      nodes.push({ id: exclId, name: '排除范围', type: 'constraint', val: 10 });
      links.push({ source: scopeGroupId, target: exclId });
      doc.scope.excluded.slice(0, 5).forEach((item: string, i: number) => {
        const itemId = `scope_excl_${i}`;
        nodes.push({ id: itemId, name: item.substring(0, 20) + '...', type: 'constraint', val: 5, description: item });
        links.push({ source: exclId, target: itemId });
      });
    }
  }
  
  return { nodes, links };
}

// 从系统架构文档提取图数据
function extractArchitectureGraph(data: any): GraphData {
  const nodes: GraphNode[] = [];
  const links: GraphLink[] = [];
  
  const design = data.system_design;
  if (!design) return { nodes, links };
  
  // 根节点
  const rootId = 'root';
  nodes.push({ id: rootId, name: design.design_overview?.project_name || '系统架构', type: 'root', val: 30 });
  
  // Agents
  if (design.agents?.length) {
    design.agents.forEach((agent: any, i: number) => {
      const agentId = `agent_${i}`;
      nodes.push({ id: agentId, name: agent.name, type: 'agent', val: 20, description: agent.purpose });
      links.push({ source: rootId, target: agentId, label: '包含' });
      
      // Agent职责
      if (agent.responsibilities?.length) {
        agent.responsibilities.slice(0, 4).forEach((resp: string, j: number) => {
          const respId = `agent_${i}_resp_${j}`;
          nodes.push({ id: respId, name: resp.substring(0, 20) + '...', type: 'capability', val: 6, description: resp });
          links.push({ source: agentId, target: respId, label: '职责' });
        });
      }
      
      // Agent依赖
      if (agent.dependencies?.length) {
        agent.dependencies.forEach((dep: string, j: number) => {
          const depId = `agent_${i}_dep_${j}`;
          nodes.push({ id: depId, name: dep, type: 'tool', val: 8 });
          links.push({ source: agentId, target: depId, label: '依赖' });
        });
      }
    });
  }
  
  // 数据模型
  if (design.data_models?.length) {
    const dmGroupId = 'dm_group';
    nodes.push({ id: dmGroupId, name: '数据模型', type: 'data_model', val: 18 });
    links.push({ source: rootId, target: dmGroupId, label: '定义' });
    
    design.data_models.forEach((dm: any, i: number) => {
      const dmId = `dm_${i}`;
      nodes.push({ id: dmId, name: dm.name, type: 'data_model', val: 12, description: dm.schema });
      links.push({ source: dmGroupId, target: dmId });
      
      // 数据模型关系
      if (dm.relationships?.length) {
        dm.relationships.forEach((rel: string) => {
          const relatedDm = design.data_models.find((d: any) => rel.includes(d.name));
          if (relatedDm) {
            const relatedIndex = design.data_models.indexOf(relatedDm);
            links.push({ source: dmId, target: `dm_${relatedIndex}`, label: '关联', color: '#06B6D4' });
          }
        });
      }
    });
  }
  
  // 交互流程
  if (design.interaction_flows?.length) {
    const flowGroupId = 'flow_group';
    nodes.push({ id: flowGroupId, name: '交互流程', type: 'flow', val: 18 });
    links.push({ source: rootId, target: flowGroupId, label: '包含' });
    
    design.interaction_flows.forEach((flow: any, i: number) => {
      const flowId = `flow_${i}`;
      nodes.push({ id: flowId, name: flow.name, type: 'flow', val: 12, description: flow.description });
      links.push({ source: flowGroupId, target: flowId });
      
      // 流程步骤
      if (flow.steps?.length) {
        let prevStepId: string | null = null;
        flow.steps.slice(0, 5).forEach((step: any, j: number) => {
          const stepId = `flow_${i}_step_${j}`;
          nodes.push({ id: stepId, name: step.step || `步骤${j+1}`, type: 'step', val: 6, description: step.action });
          links.push({ source: flowId, target: stepId });
          if (prevStepId) {
            links.push({ source: prevStepId, target: stepId, label: '→', color: '#84CC16' });
          }
          prevStepId = stepId;
        });
      }
    });
  }
  
  return { nodes, links };
}

// 从Agent设计文档提取图数据
function extractAgentDesignGraph(data: any): GraphData {
  const nodes: GraphNode[] = [];
  const links: GraphLink[] = [];
  
  const design = data.agent_design;
  if (!design) return { nodes, links };
  
  // 根节点
  const rootId = 'root';
  nodes.push({ id: rootId, name: design.design_overview?.project_name || 'Agent设计', type: 'root', val: 30 });
  
  // 关键决策
  if (design.design_overview?.key_design_decisions?.length) {
    const decGroupId = 'dec_group';
    nodes.push({ id: decGroupId, name: '关键决策', type: 'decision', val: 18 });
    links.push({ source: rootId, target: decGroupId, label: '包含' });
    
    design.design_overview.key_design_decisions.forEach((dec: any, i: number) => {
      const decId = `dec_${i}`;
      nodes.push({ id: decId, name: dec.decision?.substring(0, 25) + '...', type: 'decision', val: 10, description: dec.rationale });
      links.push({ source: decGroupId, target: decId });
    });
  }
  
  // Agents
  if (design.agents?.length) {
    design.agents.forEach((agent: any, i: number) => {
      const agentId = `agent_${i}`;
      nodes.push({ id: agentId, name: agent.name, type: 'agent', val: 25, description: agent.purpose });
      links.push({ source: rootId, target: agentId, label: '定义' });
      
      // 核心功能
      if (agent.capabilities?.core_functions?.length) {
        const capGroupId = `agent_${i}_cap`;
        nodes.push({ id: capGroupId, name: '核心功能', type: 'capability', val: 12 });
        links.push({ source: agentId, target: capGroupId });
        
        agent.capabilities.core_functions.slice(0, 5).forEach((func: string, j: number) => {
          const funcId = `agent_${i}_func_${j}`;
          nodes.push({ id: funcId, name: func.substring(0, 20) + '...', type: 'capability', val: 6, description: func });
          links.push({ source: capGroupId, target: funcId });
        });
      }
      
      // 所需工具
      if (agent.capabilities?.tools_required?.length) {
        const toolGroupId = `agent_${i}_tools`;
        nodes.push({ id: toolGroupId, name: '所需工具', type: 'tool', val: 12 });
        links.push({ source: agentId, target: toolGroupId });
        
        agent.capabilities.tools_required.forEach((tool: string, j: number) => {
          const toolId = `agent_${i}_tool_${j}`;
          const toolName = tool.split(' ')[0];
          nodes.push({ id: toolId, name: toolName, type: 'tool', val: 8, description: tool });
          links.push({ source: toolGroupId, target: toolId });
        });
      }
      
      // 知识领域
      if (agent.knowledge_domain?.primary_domains?.length) {
        const kdGroupId = `agent_${i}_kd`;
        nodes.push({ id: kdGroupId, name: '知识领域', type: 'non_functional', val: 12 });
        links.push({ source: agentId, target: kdGroupId });
        
        agent.knowledge_domain.primary_domains.forEach((domain: string, j: number) => {
          const domainId = `agent_${i}_domain_${j}`;
          nodes.push({ id: domainId, name: domain, type: 'non_functional', val: 6 });
          links.push({ source: kdGroupId, target: domainId });
        });
      }
    });
  }
  
  return { nodes, links };
}

// 从Prompt工程文档提取图数据
function extractPromptDesignGraph(data: any): GraphData {
  const nodes: GraphNode[] = [];
  const links: GraphLink[] = [];
  
  // 支持两种键名：prompt_design 和 prompt_engineering
  const design = data.prompt_design || data.prompt_engineering;
  if (!design) return { nodes, links };
  
  // 根节点
  const rootId = 'root';
  nodes.push({ id: rootId, name: design.project_name || 'Prompt设计', type: 'root', val: 30 });
  
  // 概述信息
  if (design.overview) {
    const overviewId = 'overview_group';
    nodes.push({ id: overviewId, name: '设计概述', type: 'requirement', val: 18 });
    links.push({ source: rootId, target: overviewId, label: '包含' });
    
    if (design.overview.key_considerations?.length) {
      design.overview.key_considerations.slice(0, 6).forEach((item: string, i: number) => {
        const itemId = `consideration_${i}`;
        nodes.push({ id: itemId, name: item.substring(0, 25) + '...', type: 'requirement', val: 8, description: item });
        links.push({ source: overviewId, target: itemId });
      });
    }
  }
  
  // 提示词模板设计
  if (design.prompt_template_design) {
    const templateId = 'template_group';
    nodes.push({ id: templateId, name: '模板设计', type: 'prompt_section', val: 18 });
    links.push({ source: rootId, target: templateId, label: '定义' });
    
    if (design.prompt_template_design.design_decisions?.length) {
      design.prompt_template_design.design_decisions.slice(0, 6).forEach((dec: any, i: number) => {
        const decId = `decision_${i}`;
        const decName = dec.aspect || dec.decision?.substring(0, 20) || `决策${i+1}`;
        nodes.push({ id: decId, name: decName, type: 'decision', val: 10, description: dec.rationale || dec.decision });
        links.push({ source: templateId, target: decId });
      });
    }
  }
  
  // 系统提示词结构
  if (design.system_prompt_structure?.sections?.length) {
    const structureId = 'structure_group';
    nodes.push({ id: structureId, name: 'Prompt结构', type: 'prompt_section', val: 18 });
    links.push({ source: rootId, target: structureId, label: '组成' });
    
    design.system_prompt_structure.sections.slice(0, 8).forEach((section: any, i: number) => {
      const sectionId = `section_${i}`;
      nodes.push({ id: sectionId, name: section.section || `部分${i+1}`, type: 'prompt_section', val: 8, description: section.purpose || section.content });
      links.push({ source: structureId, target: sectionId });
    });
  }
  
  // 元数据配置
  if (design.metadata_configuration) {
    const metaId = 'meta_group';
    nodes.push({ id: metaId, name: '元数据配置', type: 'data_model', val: 15 });
    links.push({ source: rootId, target: metaId, label: '配置' });
    
    // 工具依赖
    if (design.metadata_configuration.tools_dependencies?.length) {
      const toolsId = 'tools_dep_group';
      nodes.push({ id: toolsId, name: '工具依赖', type: 'tool', val: 12 });
      links.push({ source: metaId, target: toolsId });
      
      design.metadata_configuration.tools_dependencies.slice(0, 5).forEach((tool: string, i: number) => {
        const toolId = `tool_dep_${i}`;
        const toolName = tool.split('/').pop() || tool;
        nodes.push({ id: toolId, name: toolName, type: 'tool', val: 6, description: tool });
        links.push({ source: toolsId, target: toolId });
      });
    }
    
    // 标签
    if (design.metadata_configuration.tags?.length) {
      const tagsId = 'tags_group';
      nodes.push({ id: tagsId, name: '标签', type: 'non_functional', val: 10 });
      links.push({ source: metaId, target: tagsId });
      
      design.metadata_configuration.tags.slice(0, 6).forEach((tag: string, i: number) => {
        const tagId = `tag_${i}`;
        nodes.push({ id: tagId, name: tag, type: 'non_functional', val: 5 });
        links.push({ source: tagsId, target: tagId });
      });
    }
  }
  
  // 质量保证
  if (design.quality_assurance?.validation_checks?.length) {
    const qaId = 'qa_group';
    nodes.push({ id: qaId, name: '质量验证', type: 'scenario', val: 15 });
    links.push({ source: rootId, target: qaId, label: '验证' });
    
    design.quality_assurance.validation_checks.slice(0, 5).forEach((check: any, i: number) => {
      const checkId = `check_${i}`;
      nodes.push({ id: checkId, name: check.check || `检查${i+1}`, type: 'scenario', val: 6, description: check.details });
      links.push({ source: qaId, target: checkId });
    });
  }
  
  // 设计过程（兼容旧格式）
  const process = design.design_process;
  if (process) {
    // 需求分析发现
    if (process.requirements_analysis?.key_findings?.length) {
      const findingsId = 'findings_group';
      nodes.push({ id: findingsId, name: '关键发现', type: 'requirement', val: 18 });
      links.push({ source: rootId, target: findingsId, label: '分析' });
      
      process.requirements_analysis.key_findings.slice(0, 6).forEach((finding: string, i: number) => {
        const findingId = `finding_${i}`;
        nodes.push({ id: findingId, name: finding.substring(0, 25) + '...', type: 'requirement', val: 8, description: finding });
        links.push({ source: findingsId, target: findingId });
      });
    }
    
    // 用户画像
    if (process.requirements_analysis?.user_personas?.length) {
      const personaGroupId = 'persona_group';
      nodes.push({ id: personaGroupId, name: '用户画像', type: 'agent', val: 15 });
      links.push({ source: rootId, target: personaGroupId, label: '服务' });
      
      process.requirements_analysis.user_personas.forEach((persona: string, i: number) => {
        const personaId = `persona_${i}`;
        const personaName = persona.split(' - ')[0] || persona.substring(0, 15);
        nodes.push({ id: personaId, name: personaName, type: 'agent', val: 8, description: persona });
        links.push({ source: personaGroupId, target: personaId });
      });
    }
    
    // Prompt结构
    const structure = process.prompt_structure;
    if (structure) {
      // 核心能力
      if (structure.core_capabilities?.length) {
        const capGroupId = 'cap_group';
        nodes.push({ id: capGroupId, name: '核心能力', type: 'capability', val: 18 });
        links.push({ source: rootId, target: capGroupId, label: '具备' });
        
        structure.core_capabilities.slice(0, 6).forEach((cap: string, i: number) => {
          const capId = `cap_${i}`;
          nodes.push({ id: capId, name: cap.substring(0, 20) + '...', type: 'capability', val: 8, description: cap });
          links.push({ source: capGroupId, target: capId });
        });
      }
      
      // 工作流步骤
      if (structure.workflow_steps?.length) {
        const wfGroupId = 'wf_group';
        nodes.push({ id: wfGroupId, name: '工作流程', type: 'flow', val: 18 });
        links.push({ source: rootId, target: wfGroupId, label: '执行' });
        
        let prevStepId: string | null = null;
        structure.workflow_steps.forEach((step: string, i: number) => {
          const stepId = `wf_${i}`;
          const stepName = step.split(' - ')[0] || step.substring(0, 15);
          nodes.push({ id: stepId, name: stepName, type: 'step', val: 8, description: step });
          links.push({ source: wfGroupId, target: stepId });
          if (prevStepId) {
            links.push({ source: prevStepId, target: stepId, label: '→', color: '#84CC16' });
          }
          prevStepId = stepId;
        });
      }
      
      // 输出格式
      if (structure.output_formats?.length) {
        const outputGroupId = 'output_group';
        nodes.push({ id: outputGroupId, name: '输出格式', type: 'data_model', val: 15 });
        links.push({ source: rootId, target: outputGroupId, label: '生成' });
        
        structure.output_formats.forEach((format: string, i: number) => {
          const formatId = `format_${i}`;
          const formatName = format.split(' - ')[0] || format.substring(0, 15);
          nodes.push({ id: formatId, name: formatName, type: 'data_model', val: 8, description: format });
          links.push({ source: outputGroupId, target: formatId });
        });
      }
      
      // 约束条件
      if (structure.constraints?.length) {
        const constGroupId = 'const_group';
        nodes.push({ id: constGroupId, name: '约束条件', type: 'constraint', val: 15 });
        links.push({ source: rootId, target: constGroupId, label: '限制' });
        
        structure.constraints.slice(0, 5).forEach((c: string, i: number) => {
          const cId = `const_${i}`;
          nodes.push({ id: cId, name: c.substring(0, 20) + '...', type: 'constraint', val: 6, description: c });
          links.push({ source: constGroupId, target: cId });
        });
      }
    }
  }
  
  return { nodes, links };
}

// 从工具开发文档提取图数据
function extractToolsDevGraph(data: any): GraphData {
  const nodes: GraphNode[] = [];
  const links: GraphLink[] = [];
  
  const dev = data.tool_development;
  if (!dev) return { nodes, links };
  
  // 根节点
  const rootId = 'root';
  nodes.push({ id: rootId, name: dev.development_overview?.project_name || '工具开发', type: 'root', val: 30 });
  
  // 工具列表
  if (dev.tools?.length) {
    dev.tools.forEach((tool: any, i: number) => {
      const toolId = `tool_${i}`;
      nodes.push({ id: toolId, name: tool.tool_name, type: 'tool', val: 15, description: tool.description });
      links.push({ source: rootId, target: toolId, label: '包含' });
      
      // 工具参数
      if (tool.parameters?.length) {
        tool.parameters.slice(0, 3).forEach((param: any, j: number) => {
          const paramId = `tool_${i}_param_${j}`;
          nodes.push({ id: paramId, name: param.name, type: 'data_model', val: 6, description: `${param.type}: ${param.description}` });
          links.push({ source: toolId, target: paramId, label: '参数' });
        });
      }
      
      // 工具依赖
      if (tool.dependencies?.length) {
        tool.dependencies.slice(0, 3).forEach((dep: string, j: number) => {
          const depId = `tool_${i}_dep_${j}`;
          // 检查是否已存在相同依赖节点
          const existingNode = nodes.find(n => n.name === dep && n.type === 'non_functional');
          if (existingNode) {
            links.push({ source: toolId, target: existingNode.id, label: '依赖', color: '#F59E0B' });
          } else {
            nodes.push({ id: depId, name: dep, type: 'non_functional', val: 5 });
            links.push({ source: toolId, target: depId, label: '依赖', color: '#F59E0B' });
          }
        });
      }
    });
  }
  
  // 集成详情
  if (dev.integration_details) {
    // AWS服务
    if (dev.integration_details.aws_services?.length) {
      const awsGroupId = 'aws_group';
      nodes.push({ id: awsGroupId, name: 'AWS服务', type: 'capability', val: 15 });
      links.push({ source: rootId, target: awsGroupId, label: '集成' });
      
      dev.integration_details.aws_services.slice(0, 8).forEach((svc: string, i: number) => {
        const svcId = `aws_${i}`;
        nodes.push({ id: svcId, name: svc, type: 'capability', val: 6 });
        links.push({ source: awsGroupId, target: svcId });
      });
    }
    
    // 数据格式
    if (dev.integration_details.data_formats?.length) {
      const formatGroupId = 'format_group';
      nodes.push({ id: formatGroupId, name: '数据格式', type: 'data_model', val: 12 });
      links.push({ source: rootId, target: formatGroupId, label: '支持' });
      
      dev.integration_details.data_formats.forEach((fmt: string, i: number) => {
        const fmtId = `fmt_${i}`;
        nodes.push({ id: fmtId, name: fmt, type: 'data_model', val: 6 });
        links.push({ source: formatGroupId, target: fmtId });
      });
    }
  }
  
  return { nodes, links };
}

// 从Agent代码开发文档提取图数据
function extractAgentCodeDevGraph(data: any): GraphData {
  const nodes: GraphNode[] = [];
  const links: GraphLink[] = [];
  
  const dev = data.agent_code_development;
  if (!dev) return { nodes, links };
  
  // 根节点
  const rootId = 'root';
  nodes.push({ id: rootId, name: dev.development_overview?.project_name || 'Agent代码', type: 'root', val: 30 });
  
  // Agent实现
  const impl = dev.agent_implementation;
  if (impl) {
    const agentId = 'agent_impl';
    nodes.push({ id: agentId, name: impl.agent_name || 'Agent', type: 'agent', val: 20, description: impl.file_path });
    links.push({ source: rootId, target: agentId, label: '实现' });
    
    // 依赖
    if (impl.dependencies?.length) {
      const depGroupId = 'dep_group';
      nodes.push({ id: depGroupId, name: '依赖', type: 'non_functional', val: 12 });
      links.push({ source: agentId, target: depGroupId });
      
      impl.dependencies.slice(0, 6).forEach((dep: string, i: number) => {
        const depId = `dep_${i}`;
        nodes.push({ id: depId, name: dep.split('.').pop() || dep, type: 'non_functional', val: 6, description: dep });
        links.push({ source: depGroupId, target: depId });
      });
    }
  }
  
  // 核心函数
  if (dev.core_functions?.length) {
    const funcGroupId = 'func_group';
    nodes.push({ id: funcGroupId, name: '核心函数', type: 'capability', val: 18 });
    links.push({ source: rootId, target: funcGroupId, label: '包含' });
    
    dev.core_functions.slice(0, 6).forEach((func: any, i: number) => {
      const funcId = `func_${i}`;
      const funcName = func.function_name.split('.').pop() || func.function_name;
      nodes.push({ id: funcId, name: funcName, type: 'capability', val: 10, description: func.purpose });
      links.push({ source: funcGroupId, target: funcId });
    });
  }
  
  // 工具集成
  const toolInt = dev.tool_integration;
  if (toolInt) {
    // 自定义工具
    if (toolInt.custom_tools?.length) {
      const customToolGroupId = 'custom_tool_group';
      nodes.push({ id: customToolGroupId, name: '自定义工具', type: 'tool', val: 15 });
      links.push({ source: rootId, target: customToolGroupId, label: '使用' });
      
      toolInt.custom_tools.slice(0, 6).forEach((tool: string, i: number) => {
        const toolId = `custom_tool_${i}`;
        const toolName = tool.split('/').pop() || tool;
        nodes.push({ id: toolId, name: toolName, type: 'tool', val: 8, description: tool });
        links.push({ source: customToolGroupId, target: toolId });
      });
    }
    
    // 系统工具
    if (toolInt.system_tools?.length) {
      const sysToolGroupId = 'sys_tool_group';
      nodes.push({ id: sysToolGroupId, name: '系统工具', type: 'tool', val: 12 });
      links.push({ source: rootId, target: sysToolGroupId, label: '调用' });
      
      toolInt.system_tools.forEach((tool: string, i: number) => {
        const toolId = `sys_tool_${i}`;
        const toolName = tool.split('/').pop() || tool;
        nodes.push({ id: toolId, name: toolName, type: 'tool', val: 6, description: tool });
        links.push({ source: sysToolGroupId, target: toolId });
      });
    }
  }
  
  // 测试场景
  if (dev.testing?.test_scenarios?.length) {
    const testGroupId = 'test_group';
    nodes.push({ id: testGroupId, name: '测试场景', type: 'scenario', val: 12 });
    links.push({ source: rootId, target: testGroupId, label: '验证' });
    
    dev.testing.test_scenarios.slice(0, 5).forEach((scenario: string, i: number) => {
      const scenarioId = `scenario_${i}`;
      nodes.push({ id: scenarioId, name: scenario.substring(0, 20) + '...', type: 'scenario', val: 6, description: scenario });
      links.push({ source: testGroupId, target: scenarioId });
    });
  }
  
  return { nodes, links };
}

// 根据阶段类型提取图数据
export function extractGraphData(stageName: string, data: any): GraphData {
  if (!data) return { nodes: [], links: [] };
  
  // 如果数据只包含 raw_content，尝试从中提取 JSON
  if (data.raw_content && Object.keys(data).length === 1) {
    const extractedData = tryExtractJsonFromRawContent(data.raw_content);
    if (extractedData) {
      data = extractedData;
    } else {
      // 无法提取有效 JSON，返回空图
      return { nodes: [], links: [] };
    }
  }
  
  switch (stageName) {
    case 'requirements_analyzer':
    case 'requirements_analysis':
      return extractRequirementsGraph(data);
    case 'system_architect':
    case 'system_architecture':
      return extractArchitectureGraph(data);
    case 'agent_designer':
    case 'agent_design':
      return extractAgentDesignGraph(data);
    case 'prompt_engineer':
      return extractPromptDesignGraph(data);
    case 'tools_developer':
      return extractToolsDevGraph(data);
    case 'agent_code_developer':
      return extractAgentCodeDevGraph(data);
    case 'agent_developer_manager':
      return extractAgentDevManagerGraph(data);
    default:
      // 通用提取逻辑
      return extractGenericGraph(data);
  }
}

// 从开发管理文档提取图数据
function extractAgentDevManagerGraph(data: any): GraphData {
  const nodes: GraphNode[] = [];
  const links: GraphLink[] = [];
  
  const manager = data.agent_developer_manager;
  if (!manager) return { nodes, links };
  
  // 根节点
  const rootId = 'root';
  nodes.push({ id: rootId, name: manager.project_name || '开发管理', type: 'root', val: 30 });
  
  // 验证摘要
  if (manager.verification_summary) {
    const verifyId = 'verify_group';
    nodes.push({ id: verifyId, name: '验证摘要', type: 'scenario', val: 20 });
    links.push({ source: rootId, target: verifyId, label: '包含' });
    
    // 项目验证
    if (manager.verification_summary.project_verification) {
      const projVerifyId = 'proj_verify';
      const status = manager.verification_summary.project_verification.status || '未知';
      nodes.push({ id: projVerifyId, name: `项目验证: ${status}`, type: 'scenario', val: 10 });
      links.push({ source: verifyId, target: projVerifyId });
    }
    
    // 文件完整性检查
    if (manager.verification_summary.file_integrity_check?.checked_files?.length) {
      const fileCheckId = 'file_check';
      nodes.push({ id: fileCheckId, name: '文件完整性', type: 'data_model', val: 12 });
      links.push({ source: verifyId, target: fileCheckId });
      
      manager.verification_summary.file_integrity_check.checked_files.slice(0, 5).forEach((file: any, i: number) => {
        const fileId = `file_${i}`;
        const fileName = file.file?.split('/').pop() || `文件${i+1}`;
        nodes.push({ id: fileId, name: fileName, type: 'data_model', val: 6, description: file.notes });
        links.push({ source: fileCheckId, target: fileId });
      });
    }
    
    // 依赖验证
    if (manager.verification_summary.dependency_verification?.verified_packages?.length) {
      const depVerifyId = 'dep_verify';
      nodes.push({ id: depVerifyId, name: '依赖验证', type: 'tool', val: 12 });
      links.push({ source: verifyId, target: depVerifyId });
      
      manager.verification_summary.dependency_verification.verified_packages.slice(0, 5).forEach((pkg: any, i: number) => {
        const pkgId = `pkg_${i}`;
        nodes.push({ id: pkgId, name: pkg.package || `包${i+1}`, type: 'tool', val: 6, description: `版本: ${pkg.version}` });
        links.push({ source: depVerifyId, target: pkgId });
      });
    }
    
    // 文档检查
    if (manager.verification_summary.documentation_check?.documents?.length) {
      const docCheckId = 'doc_check';
      nodes.push({ id: docCheckId, name: '文档检查', type: 'requirement', val: 12 });
      links.push({ source: verifyId, target: docCheckId });
      
      manager.verification_summary.documentation_check.documents.slice(0, 6).forEach((doc: any, i: number) => {
        const docId = `doc_${i}`;
        nodes.push({ id: docId, name: doc.document || `文档${i+1}`, type: 'requirement', val: 6, description: doc.stage });
        links.push({ source: docCheckId, target: docId });
      });
    }
  }
  
  // 质量评估
  if (manager.quality_assessment) {
    const qaId = 'qa_group';
    nodes.push({ id: qaId, name: '质量评估', type: 'capability', val: 18 });
    links.push({ source: rootId, target: qaId, label: '评估' });
    
    // 代码质量
    if (manager.quality_assessment.code_quality?.aspects?.length) {
      const codeQaId = 'code_qa';
      nodes.push({ id: codeQaId, name: `代码质量: ${manager.quality_assessment.code_quality.rating || ''}`, type: 'capability', val: 12 });
      links.push({ source: qaId, target: codeQaId });
      
      manager.quality_assessment.code_quality.aspects.slice(0, 4).forEach((aspect: any, i: number) => {
        const aspectId = `code_aspect_${i}`;
        nodes.push({ id: aspectId, name: `${aspect.aspect}: ${aspect.score}`, type: 'capability', val: 6, description: aspect.notes });
        links.push({ source: codeQaId, target: aspectId });
      });
    }
    
    // 提示词质量
    if (manager.quality_assessment.prompt_quality?.aspects?.length) {
      const promptQaId = 'prompt_qa';
      nodes.push({ id: promptQaId, name: `提示词质量: ${manager.quality_assessment.prompt_quality.rating || ''}`, type: 'prompt_section', val: 12 });
      links.push({ source: qaId, target: promptQaId });
    }
    
    // 工具质量
    if (manager.quality_assessment.tool_quality?.aspects?.length) {
      const toolQaId = 'tool_qa';
      nodes.push({ id: toolQaId, name: `工具质量: ${manager.quality_assessment.tool_quality.rating || ''}`, type: 'tool', val: 12 });
      links.push({ source: qaId, target: toolQaId });
    }
  }
  
  // 功能验证
  if (manager.functional_verification?.core_features?.length) {
    const funcId = 'func_group';
    nodes.push({ id: funcId, name: '功能验证', type: 'flow', val: 18 });
    links.push({ source: rootId, target: funcId, label: '验证' });
    
    manager.functional_verification.core_features.slice(0, 6).forEach((feature: any, i: number) => {
      const featureId = `feature_${i}`;
      const status = feature.status === '已实现' ? '✓' : '○';
      nodes.push({ id: featureId, name: `${status} ${feature.feature?.substring(0, 15) || ''}...`, type: 'flow', val: 8, description: feature.verification });
      links.push({ source: funcId, target: featureId });
    });
  }
  
  // 部署就绪
  if (manager.deployment_readiness?.checklist?.length) {
    const deployId = 'deploy_group';
    nodes.push({ id: deployId, name: '部署就绪', type: 'agent', val: 18 });
    links.push({ source: rootId, target: deployId, label: '准备' });
    
    manager.deployment_readiness.checklist.slice(0, 6).forEach((item: any, i: number) => {
      const itemId = `deploy_${i}`;
      const status = item.status?.includes('完成') ? '✓' : '○';
      nodes.push({ id: itemId, name: `${status} ${item.item?.substring(0, 12) || ''}`, type: 'agent', val: 6, description: item.notes });
      links.push({ source: deployId, target: itemId });
    });
  }
  
  // 最终结论
  if (manager.final_verdict) {
    const verdictId = 'verdict';
    const status = manager.final_verdict.overall_status || '未知';
    nodes.push({ id: verdictId, name: `结论: ${status}`, type: 'decision', val: 15, description: manager.final_verdict.summary });
    links.push({ source: rootId, target: verdictId, label: '结论' });
  }
  
  return { nodes, links };
}

// 尝试从 raw_content 中提取 JSON
function tryExtractJsonFromRawContent(rawContent: string): any {
  if (!rawContent) return null;
  
  // 尝试从 markdown 代码块中提取 JSON
  const jsonPatterns = [
    /```json\s*([\s\S]*?)\s*```/g,
    /```\s*([\s\S]*?)\s*```/g,
  ];
  
  for (const pattern of jsonPatterns) {
    const matches = rawContent.matchAll(pattern);
    for (const match of matches) {
      try {
        const cleaned = match[1].trim();
        if (cleaned.startsWith('{') || cleaned.startsWith('[')) {
          const parsed = JSON.parse(cleaned);
          if (typeof parsed === 'object' && parsed !== null && Object.keys(parsed).length > 0) {
            // 检查是否包含有意义的键
            const meaningfulKeys = Object.keys(parsed).filter(k => k !== 'raw_content');
            if (meaningfulKeys.length > 0) {
              return parsed;
            }
          }
        }
      } catch {
        continue;
      }
    }
  }
  
  // 尝试直接查找 JSON 对象
  let depth = 0;
  let start = -1;
  let inString = false;
  let escapeNext = false;
  
  for (let i = 0; i < Math.min(rawContent.length, 50000); i++) {
    const char = rawContent[i];
    
    if (escapeNext) {
      escapeNext = false;
      continue;
    }
    
    if (char === '\\' && inString) {
      escapeNext = true;
      continue;
    }
    
    if (char === '"' && !escapeNext) {
      inString = !inString;
      continue;
    }
    
    if (inString) continue;
    
    if (char === '{') {
      if (depth === 0) start = i;
      depth++;
    } else if (char === '}') {
      depth--;
      if (depth === 0 && start >= 0) {
        const jsonStr = rawContent.substring(start, i + 1);
        try {
          const obj = JSON.parse(jsonStr);
          if (typeof obj === 'object' && obj !== null) {
            const meaningfulKeys = Object.keys(obj).filter(k => k !== 'raw_content');
            if (meaningfulKeys.length > 0) {
              return obj;
            }
          }
        } catch {
          // 继续查找下一个
        }
        start = -1;
      }
    }
  }
  
  return null;
}

// 通用图数据提取
function extractGenericGraph(data: any): GraphData {
  const nodes: GraphNode[] = [];
  const links: GraphLink[] = [];
  
  const rootId = 'root';
  nodes.push({ id: rootId, name: '文档', type: 'root', val: 30 });
  
  function traverse(obj: any, parentId: string, depth: number = 0) {
    if (depth > 3) return; // 限制深度
    
    if (typeof obj === 'object' && obj !== null) {
      Object.entries(obj).slice(0, 10).forEach(([key, value], i) => {
        const nodeId = `${parentId}_${key}_${i}`;
        
        if (Array.isArray(value)) {
          nodes.push({ id: nodeId, name: key, type: 'default', val: 12 });
          links.push({ source: parentId, target: nodeId });
          
          value.slice(0, 5).forEach((item, j) => {
            const itemId = `${nodeId}_${j}`;
            const itemName = typeof item === 'string' ? item.substring(0, 20) : (item?.name || item?.title || `项目${j+1}`);
            nodes.push({ id: itemId, name: itemName, type: 'default', val: 6 });
            links.push({ source: nodeId, target: itemId });
          });
        } else if (typeof value === 'object' && value !== null) {
          nodes.push({ id: nodeId, name: key, type: 'default', val: 10 });
          links.push({ source: parentId, target: nodeId });
          traverse(value, nodeId, depth + 1);
        }
      });
    }
  }
  
  traverse(data, rootId);
  return { nodes, links };
}

interface KnowledgeGraphProps {
  data: GraphData;
  width?: number;
  height?: number;
}

export function KnowledgeGraph({ data, width = 800, height = 600 }: KnowledgeGraphProps) {
  const graphRef = useRef<any>();
  const [hoveredNode, setHoveredNode] = useState<GraphNode | null>(null);
  
  // 为节点添加颜色
  const graphData = useMemo(() => ({
    nodes: data.nodes.map(node => ({
      ...node,
      color: NODE_COLORS[node.type] || NODE_COLORS.default,
    })),
    links: data.links.map(link => ({
      ...link,
      color: link.color || '#CBD5E1',
    })),
  }), [data]);
  
  // 节点绘制
  const nodeCanvasObject = useCallback((node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
    const label = node.name;
    const fontSize = Math.max(10 / globalScale, 3);
    ctx.font = `${fontSize}px Sans-Serif`;
    
    const nodeSize = node.val || 10;
    
    // 绘制节点圆形
    ctx.beginPath();
    ctx.arc(node.x, node.y, nodeSize / 2, 0, 2 * Math.PI);
    ctx.fillStyle = node.color || '#6B7280';
    ctx.fill();
    
    // 绘制标签
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillStyle = '#1F2937';
    ctx.fillText(label, node.x, node.y + nodeSize / 2 + fontSize);
  }, []);
  
  // 链接绘制
  const linkCanvasObject = useCallback((link: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
    const start = link.source;
    const end = link.target;
    
    if (typeof start !== 'object' || typeof end !== 'object') return;
    
    // 绘制线条
    ctx.beginPath();
    ctx.moveTo(start.x, start.y);
    ctx.lineTo(end.x, end.y);
    ctx.strokeStyle = link.color || '#CBD5E1';
    ctx.lineWidth = 1 / globalScale;
    ctx.stroke();
    
    // 绘制标签
    if (link.label) {
      const midX = (start.x + end.x) / 2;
      const midY = (start.y + end.y) / 2;
      const fontSize = Math.max(8 / globalScale, 2);
      ctx.font = `${fontSize}px Sans-Serif`;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillStyle = '#6B7280';
      ctx.fillText(link.label, midX, midY);
    }
  }, []);
  
  useEffect(() => {
    if (graphRef.current) {
      graphRef.current.d3Force('charge').strength(-100);
      graphRef.current.d3Force('link').distance(50);
    }
  }, []);
  
  return (
    <div className="relative">
      <ForceGraph2D
        ref={graphRef}
        graphData={graphData}
        width={width}
        height={height}
        nodeCanvasObject={nodeCanvasObject}
        linkCanvasObject={linkCanvasObject}
        onNodeHover={(node: any) => setHoveredNode(node)}
        nodeLabel={(node: any) => node.description || node.name}
        linkDirectionalArrowLength={3}
        linkDirectionalArrowRelPos={1}
        cooldownTicks={100}
        onEngineStop={() => graphRef.current?.zoomToFit(400)}
      />
      
      {/* 图例 */}
      <div className="absolute top-2 right-2 bg-white/90 backdrop-blur-sm rounded-lg p-3 shadow-sm border text-xs">
        <div className="font-medium mb-2 text-gray-700">图例</div>
        <div className="space-y-1">
          {Object.entries(NODE_COLORS).slice(0, 8).map(([type, color]) => (
            <div key={type} className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full" style={{ backgroundColor: color }} />
              <span className="text-gray-600">{getTypeLabel(type)}</span>
            </div>
          ))}
        </div>
      </div>
      
      {/* 悬停信息 */}
      {hoveredNode?.description && (
        <div className="absolute bottom-2 left-2 right-2 bg-white/95 backdrop-blur-sm rounded-lg p-3 shadow-lg border max-w-md">
          <div className="font-medium text-gray-900 mb-1">{hoveredNode.name}</div>
          <div className="text-sm text-gray-600">{hoveredNode.description}</div>
        </div>
      )}
    </div>
  );
}

function getTypeLabel(type: string): string {
  const labels: Record<string, string> = {
    requirement: '功能需求',
    non_functional: '非功能需求',
    constraint: '约束条件',
    assumption: '假设',
    scope: '范围',
    agent: 'Agent',
    data_model: '数据模型',
    flow: '交互流程',
    step: '步骤',
    capability: '能力',
    tool: '工具',
    decision: '决策',
    prompt_section: 'Prompt部分',
    scenario: '测试场景',
    root: '根节点',
    default: '其他',
  };
  return labels[type] || type;
}

export default KnowledgeGraph;
