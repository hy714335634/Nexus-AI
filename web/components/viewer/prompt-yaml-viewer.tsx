'use client';

import { useState, useMemo, useCallback, useEffect } from 'react';
import { 
  ChevronDown, 
  ChevronRight, 
  FileText, 
  Tag, 
  Settings, 
  Clock,
  User,
  Layers,
  Edit3,
  Save,
  X,
  CheckCircle2,
  AlertCircle,
  Cpu,
  Wrench,
  Info,
} from 'lucide-react';

// YAML解析结果类型
interface ParsedPromptYaml {
  agent: {
    name?: string;
    description?: string;
    category?: string;
    environments?: Record<string, {
      max_tokens?: number;
      temperature?: number;
      streaming?: boolean;
    }>;
    versions?: Array<{
      version?: string;
      status?: string;
      created_date?: string;
      author?: string;
      description?: string;
      system_prompt?: string;
      metadata?: {
        tags?: string[];
        supported_models?: string[];
        tools_dependencies?: string[];
      };
    }>;
  };
}

interface PromptYamlViewerProps {
  readonly content: string;
  readonly filename?: string;
  readonly editable?: boolean;
  readonly onSave?: (content: string) => Promise<void>;
  readonly saving?: boolean;
}

// 简单的YAML解析器（处理基本结构）
function parseYaml(content: string): ParsedPromptYaml | null {
  try {
    const lines = content.split('\n');
    const result: ParsedPromptYaml = { agent: {} };
    
    let currentPath: string[] = [];
    let inSystemPrompt = false;
    let systemPromptLines: string[] = [];
    let systemPromptIndent = 0;
    let currentVersion: Record<string, unknown> | null = null;
    let currentMetadata: Record<string, unknown> | null = null;
    let currentEnvironment: string | null = null;
    let currentEnvData: Record<string, unknown> | null = null;
    // 跟踪当前正在处理的数组类型
    let currentArrayType: 'tags' | 'supported_models' | 'tools_dependencies' | null = null;
    
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      const trimmed = line.trim();
      
      // 跳过空行和注释
      if (!trimmed || trimmed.startsWith('#')) continue;
      
      // 计算缩进
      const indent = line.search(/\S/);
      
      // 处理system_prompt多行文本
      if (inSystemPrompt) {
        if (indent > systemPromptIndent || trimmed === '') {
          systemPromptLines.push(line.substring(systemPromptIndent + 2) || '');
          continue;
        } else {
          // system_prompt结束
          if (currentVersion) {
            currentVersion.system_prompt = systemPromptLines.join('\n').trim();
          }
          inSystemPrompt = false;
          systemPromptLines = [];
        }
      }
      
      // 解析键值对
      const keyMatch = trimmed.match(/^([a-z_]+):\s*(.*)$/i);
      if (keyMatch) {
        const [, key, value] = keyMatch;
        
        // 处理顶层agent
        if (key === 'agent' && indent === 0) {
          currentPath = ['agent'];
          continue;
        }
        
        // 处理agent下的属性
        if (currentPath[0] === 'agent') {
          if (indent === 2) {
            if (key === 'name') result.agent.name = value.replace(/['"]/g, '');
            else if (key === 'description') result.agent.description = value.replace(/['"]/g, '');
            else if (key === 'category') result.agent.category = value.replace(/['"]/g, '');
            else if (key === 'environments') {
              result.agent.environments = {};
              currentPath = ['agent', 'environments'];
            }
            else if (key === 'versions') {
              result.agent.versions = [];
              currentPath = ['agent', 'versions'];
            }
          }
          
          // 处理environments
          if (currentPath[1] === 'environments' && indent === 4) {
            currentEnvironment = key;
            currentEnvData = {};
            if (result.agent.environments) {
              result.agent.environments[key] = currentEnvData as NonNullable<ParsedPromptYaml['agent']['environments']>[string];
            }
          }
          
          if (currentEnvironment && currentEnvData && indent === 6) {
            if (key === 'max_tokens') currentEnvData.max_tokens = parseInt(value);
            else if (key === 'temperature') currentEnvData.temperature = parseFloat(value);
            else if (key === 'streaming') currentEnvData.streaming = value === 'True' || value === 'true';
          }
          
          // 处理versions数组项
          if (currentPath[1] === 'versions') {
            if (trimmed.startsWith('- version:')) {
              currentVersion = { version: value.replace(/['"]/g, '') };
              if (result.agent.versions) {
                result.agent.versions.push(currentVersion as NonNullable<ParsedPromptYaml['agent']['versions']>[number]);
              }
              currentMetadata = null;
              currentArrayType = null;
            } else if (currentVersion && indent >= 6) {
              if (key === 'status') currentVersion.status = value.replace(/['"]/g, '');
              else if (key === 'created_date') currentVersion.created_date = value.replace(/['"]/g, '');
              else if (key === 'author') currentVersion.author = value.replace(/['"]/g, '');
              else if (key === 'description') currentVersion.description = value.replace(/['"]/g, '');
              else if (key === 'system_prompt' && value === '|') {
                inSystemPrompt = true;
                systemPromptIndent = indent;
                systemPromptLines = [];
              }
              else if (key === 'metadata') {
                currentMetadata = {};
                currentVersion.metadata = currentMetadata as NonNullable<ParsedPromptYaml['agent']['versions']>[number]['metadata'];
              }
              // 处理metadata下的数组声明
              else if (currentMetadata && key === 'tags') {
                currentArrayType = 'tags';
                currentMetadata.tags = [];
              }
              else if (currentMetadata && key === 'supported_models') {
                currentArrayType = 'supported_models';
                currentMetadata.supported_models = [];
              }
              else if (currentMetadata && key === 'tools_dependencies') {
                currentArrayType = 'tools_dependencies';
                currentMetadata.tools_dependencies = [];
              }
            }
          }
        }
      }
      
      // 处理数组项（tags, supported_models, tools_dependencies）
      if (currentMetadata && trimmed.startsWith('- ') && indent >= 10) {
        const arrayValue = trimmed.substring(2).replace(/['"]/g, '');
        
        if (currentArrayType && currentMetadata[currentArrayType]) {
          (currentMetadata[currentArrayType] as string[]).push(arrayValue);
        }
      }
    }
    
    // 处理最后的system_prompt
    if (inSystemPrompt && currentVersion) {
      currentVersion.system_prompt = systemPromptLines.join('\n').trim();
    }
    
    return result;
  } catch (e) {
    console.error('YAML解析错误:', e);
    return null;
  }
}

export function PromptYamlViewer({
  content,
  filename,
  editable = false,
  onSave,
  saving = false,
}: PromptYamlViewerProps) {
  const [selectedVersion, setSelectedVersion] = useState(0);
  const [expandedSections, setExpandedSections] = useState<Set<string>>(
    new Set(['system_prompt']) // 默认只展开System Prompt
  );
  const [editingSection, setEditingSection] = useState<string | null>(null);
  const [editedContent, setEditedContent] = useState(content);
  const [saveMessage, setSaveMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  
  // 解析YAML
  const parsed = useMemo(() => parseYaml(content), [content]);
  
  // 当content变化时更新editedContent
  useEffect(() => {
    setEditedContent(content);
  }, [content]);
  
  const toggleSection = useCallback((section: string) => {
    setExpandedSections(prev => {
      const next = new Set(prev);
      if (next.has(section)) {
        next.delete(section);
      } else {
        next.add(section);
      }
      return next;
    });
  }, []);
  
  const handleSaveRaw = useCallback(async () => {
    if (onSave) {
      try {
        await onSave(editedContent);
        setSaveMessage({ type: 'success', text: '保存成功' });
        setEditingSection(null);
      } catch {
        setSaveMessage({ type: 'error', text: '保存失败' });
      }
      setTimeout(() => setSaveMessage(null), 3000);
    }
  }, [onSave, editedContent]);
  
  if (!parsed) {
    // 解析失败，显示原始内容
    return (
      <div className="rounded-xl border border-gray-200 bg-white overflow-hidden">
        <div className="px-4 py-3 bg-gray-50 border-b border-gray-200 flex items-center justify-between">
          <span className="text-sm text-gray-600">{filename || 'prompt.yaml'}</span>
          <span className="text-xs text-amber-600 bg-amber-50 px-2 py-1 rounded">YAML解析失败，显示原始内容</span>
        </div>
        <pre className="p-4 text-sm font-mono overflow-auto max-h-[600px] bg-gray-900 text-gray-100">
          {content}
        </pre>
      </div>
    );
  }
  
  const currentVersionData = parsed.agent.versions?.[selectedVersion];
  
  return (
    <div className="rounded-xl border border-gray-200 bg-white overflow-hidden">
      {/* 保存消息 */}
      {saveMessage && (
        <div className={`px-4 py-2 flex items-center gap-2 text-sm ${
          saveMessage.type === 'success' ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'
        }`}>
          {saveMessage.type === 'success' ? <CheckCircle2 className="w-4 h-4" /> : <AlertCircle className="w-4 h-4" />}
          {saveMessage.text}
        </div>
      )}
      
      {/* 编辑原始YAML模式 */}
      {editingSection === 'raw' ? (
        <div className="p-4">
          <div className="flex items-center justify-between mb-3">
            <span className="text-sm font-medium text-gray-700">编辑原始 YAML</span>
            <div className="flex gap-2">
              <button
                onClick={() => {
                  setEditingSection(null);
                  setEditedContent(content);
                }}
                className="px-3 py-1.5 text-sm rounded-lg border border-gray-200 hover:bg-gray-50"
              >
                取消
              </button>
              <button
                onClick={handleSaveRaw}
                disabled={saving || editedContent === content}
                className="px-3 py-1.5 text-sm rounded-lg bg-purple-600 text-white hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1.5"
              >
                <Save className="w-4 h-4" />
                {saving ? '保存中...' : '保存'}
              </button>
            </div>
          </div>
          <textarea
            value={editedContent}
            onChange={(e) => setEditedContent(e.target.value)}
            className="w-full h-[550px] p-4 font-mono text-sm bg-gray-900 text-gray-100 rounded-lg border-0 focus:ring-2 focus:ring-purple-500"
            spellCheck={false}
          />
        </div>
      ) : (
        <>
          {/* 头部：Agent概览信息 - 直接展示 */}
          <div className="p-4 bg-gradient-to-r from-purple-50 to-indigo-50 border-b border-gray-200">
            <div className="flex items-start justify-between gap-4">
              <div className="flex items-start gap-3 flex-1">
                <div className="w-12 h-12 rounded-xl bg-purple-100 flex items-center justify-center flex-shrink-0">
                  <FileText className="w-6 h-6 text-purple-600" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <h3 className="font-semibold text-gray-900 text-lg">{parsed.agent.name || 'Unknown Agent'}</h3>
                    {parsed.agent.category && (
                      <span className="px-2 py-0.5 text-xs rounded-full bg-purple-100 text-purple-700">
                        {parsed.agent.category}
                      </span>
                    )}
                  </div>
                  {parsed.agent.description && (
                    <p className="mt-1 text-sm text-gray-600 line-clamp-2">{parsed.agent.description}</p>
                  )}
                </div>
              </div>
              {editable && (
                <button
                  onClick={() => setEditingSection('raw')}
                  className="px-3 py-1.5 text-sm rounded-lg border border-gray-200 bg-white hover:bg-gray-50 flex items-center gap-1.5 flex-shrink-0"
                >
                  <Edit3 className="w-4 h-4" />
                  编辑YAML
                </button>
              )}
            </div>
            
            {/* 版本信息和基本信息 - 直接展示 */}
            <div className="mt-4 flex flex-wrap gap-4">
              {/* 版本选择 */}
              {parsed.agent.versions && parsed.agent.versions.length > 0 && (
                <div className="flex items-center gap-2">
                  <span className="text-xs text-gray-500">版本:</span>
                  {parsed.agent.versions.map((v, idx) => (
                    <button
                      key={idx}
                      onClick={() => setSelectedVersion(idx)}
                      className={`px-2.5 py-1 text-xs rounded-full transition-colors ${
                        selectedVersion === idx
                          ? 'bg-purple-600 text-white'
                          : 'bg-white text-gray-600 border border-gray-200 hover:border-purple-300'
                      }`}
                    >
                      {v.version || `v${idx + 1}`}
                      {v.status === 'stable' && selectedVersion === idx && (
                        <CheckCircle2 className="w-3 h-3 ml-1 inline" />
                      )}
                    </button>
                  ))}
                </div>
              )}
              
              {/* 版本元信息 */}
              {currentVersionData?.created_date && (
                <div className="flex items-center gap-1.5 text-xs text-gray-500">
                  <Clock className="w-3.5 h-3.5" />
                  {currentVersionData.created_date}
                </div>
              )}
              {currentVersionData?.author && (
                <div className="flex items-center gap-1.5 text-xs text-gray-500">
                  <User className="w-3.5 h-3.5" />
                  {currentVersionData.author}
                </div>
              )}
              {currentVersionData?.status && (
                <span className={`px-2 py-0.5 text-xs rounded-full ${
                  currentVersionData.status === 'stable' 
                    ? 'bg-green-100 text-green-700' 
                    : 'bg-amber-100 text-amber-700'
                }`}>
                  {currentVersionData.status}
                </span>
              )}
            </div>
          </div>
          
          {/* 快速信息栏 - 直接展示环境配置和标签 */}
          <div className="px-4 py-3 bg-gray-50/70 border-b border-gray-100 flex flex-wrap gap-6">
            {/* 环境配置摘要 */}
            {parsed.agent.environments && Object.keys(parsed.agent.environments).length > 0 && (
              <div className="flex items-center gap-3">
                <Settings className="w-4 h-4 text-gray-400" />
                <div className="flex gap-2">
                  {Object.entries(parsed.agent.environments).map(([env, config]) => (
                    <span key={env} className="px-2 py-1 text-xs rounded bg-white border border-gray-200 text-gray-600">
                      <span className="font-medium capitalize">{env}</span>
                      {config.max_tokens && <span className="text-gray-400 ml-1">({(config.max_tokens/1000).toFixed(0)}k)</span>}
                    </span>
                  ))}
                </div>
              </div>
            )}
            
            {/* 标签 */}
            {currentVersionData?.metadata?.tags && currentVersionData.metadata.tags.length > 0 && (
              <div className="flex items-center gap-2">
                <Tag className="w-4 h-4 text-gray-400" />
                <div className="flex gap-1.5">
                  {currentVersionData.metadata.tags.map((tag, idx) => (
                    <span key={idx} className="px-2 py-0.5 text-xs rounded-full bg-blue-50 text-blue-600">
                      {tag}
                    </span>
                  ))}
                </div>
              </div>
            )}
            
            {/* 支持的模型数量 */}
            {currentVersionData?.metadata?.supported_models && currentVersionData.metadata.supported_models.length > 0 && (
              <div className="flex items-center gap-1.5 text-xs text-gray-500">
                <Cpu className="w-4 h-4 text-gray-400" />
                <span>{currentVersionData.metadata.supported_models.length} 个模型</span>
              </div>
            )}
            
            {/* 工具依赖数量 */}
            {currentVersionData?.metadata?.tools_dependencies && currentVersionData.metadata.tools_dependencies.length > 0 && (
              <div className="flex items-center gap-1.5 text-xs text-gray-500">
                <Wrench className="w-4 h-4 text-gray-400" />
                <span>{currentVersionData.metadata.tools_dependencies.length} 个工具</span>
              </div>
            )}
          </div>
          
          {/* 内容区域 - 可折叠部分 */}
          <div className="divide-y divide-gray-100">
            {/* System Prompt - 默认展开 */}
            {currentVersionData?.system_prompt && (
              <CollapsibleSection
                title="System Prompt"
                icon={<FileText className="w-4 h-4" />}
                expanded={expandedSections.has('system_prompt')}
                onToggle={() => toggleSection('system_prompt')}
                badge={`${currentVersionData.system_prompt.length.toLocaleString()} 字符`}
              >
                <div className="bg-gray-900 rounded-lg p-4 max-h-[400px] overflow-auto">
                  <pre className="text-sm text-gray-100 whitespace-pre-wrap font-mono leading-relaxed">
                    {currentVersionData.system_prompt}
                  </pre>
                </div>
              </CollapsibleSection>
            )}
            
            {/* 支持的模型 - 可折叠 */}
            {currentVersionData?.metadata?.supported_models && currentVersionData.metadata.supported_models.length > 0 && (
              <CollapsibleSection
                title="支持的模型"
                icon={<Cpu className="w-4 h-4" />}
                expanded={expandedSections.has('models')}
                onToggle={() => toggleSection('models')}
                badge={`${currentVersionData.metadata.supported_models.length} 个`}
              >
                <div className="flex flex-wrap gap-2">
                  {currentVersionData.metadata.supported_models.map((model, idx) => (
                    <span key={idx} className="px-3 py-1.5 text-xs rounded-lg bg-green-50 text-green-700 border border-green-100 font-mono">
                      {model}
                    </span>
                  ))}
                </div>
              </CollapsibleSection>
            )}
            
            {/* 工具依赖 - 可折叠 */}
            {currentVersionData?.metadata?.tools_dependencies && currentVersionData.metadata.tools_dependencies.length > 0 && (
              <CollapsibleSection
                title="工具依赖"
                icon={<Wrench className="w-4 h-4" />}
                expanded={expandedSections.has('tools')}
                onToggle={() => toggleSection('tools')}
                badge={`${currentVersionData.metadata.tools_dependencies.length} 个`}
              >
                <div className="bg-gray-50 rounded-lg p-3 max-h-[250px] overflow-auto">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-1">
                    {currentVersionData.metadata.tools_dependencies.map((tool, idx) => (
                      <div key={idx} className="text-xs font-mono text-gray-600 py-1 px-2 rounded hover:bg-gray-100">
                        {tool}
                      </div>
                    ))}
                  </div>
                </div>
              </CollapsibleSection>
            )}
            
            {/* 环境配置详情 - 可折叠 */}
            {parsed.agent.environments && Object.keys(parsed.agent.environments).length > 0 && (
              <CollapsibleSection
                title="环境配置详情"
                icon={<Settings className="w-4 h-4" />}
                expanded={expandedSections.has('environments')}
                onToggle={() => toggleSection('environments')}
              >
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                  {Object.entries(parsed.agent.environments).map(([env, config]) => (
                    <div key={env} className="p-3 rounded-lg bg-gray-50 border border-gray-100">
                      <div className="font-medium text-sm text-gray-700 mb-2 capitalize flex items-center gap-2">
                        {env}
                        {env === 'production' && <span className="w-2 h-2 rounded-full bg-green-500" />}
                      </div>
                      <div className="space-y-1 text-xs text-gray-500">
                        {config.max_tokens && (
                          <div className="flex justify-between">
                            <span>Max Tokens</span>
                            <span className="font-mono">{config.max_tokens.toLocaleString()}</span>
                          </div>
                        )}
                        {config.temperature !== undefined && (
                          <div className="flex justify-between">
                            <span>Temperature</span>
                            <span className="font-mono">{config.temperature}</span>
                          </div>
                        )}
                        {config.streaming !== undefined && (
                          <div className="flex justify-between">
                            <span>Streaming</span>
                            <span className={config.streaming ? 'text-green-600' : 'text-gray-400'}>
                              {config.streaming ? 'Yes' : 'No'}
                            </span>
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </CollapsibleSection>
            )}
          </div>
        </>
      )}
    </div>
  );
}

// 可折叠区块组件
function CollapsibleSection({
  title,
  icon,
  expanded,
  onToggle,
  badge,
  children,
}: {
  title: string;
  icon: React.ReactNode;
  expanded: boolean;
  onToggle: () => void;
  badge?: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <button
        onClick={onToggle}
        className="w-full px-4 py-3 flex items-center justify-between hover:bg-gray-50 transition-colors"
      >
        <div className="flex items-center gap-2 text-gray-700">
          {icon}
          <span className="font-medium">{title}</span>
          {badge && (
            <span className="text-xs text-gray-400 bg-gray-100 px-2 py-0.5 rounded">{badge}</span>
          )}
        </div>
        {expanded ? (
          <ChevronDown className="w-4 h-4 text-gray-400" />
        ) : (
          <ChevronRight className="w-4 h-4 text-gray-400" />
        )}
      </button>
      {expanded && (
        <div className="px-4 pb-4">
          {children}
        </div>
      )}
    </div>
  );
}
