'use client';

import { useState, useMemo } from 'react';
import { useToolList, useToolCategories, useMCPServers, useTestTool, useUpdateMCPServer } from '@/hooks/use-agents-v2';
import type { ToolInfo, ToolParameter } from '@/types/api-v2';
import { 
  Search, 
  Wrench, 
  Package, 
  Server,
  Play,
  Settings,
  ChevronRight,
  CheckCircle,
  XCircle,
  Loader2,
  Zap,
  Box,
  Layers,
  RotateCcw
} from 'lucide-react';

// 工具类型图标和颜色映射
const toolTypeConfig: Record<string, { icon: React.ElementType; color: string; label: string }> = {
  builtin: { icon: Package, color: 'bg-blue-100 text-blue-600', label: '内置工具' },
  generated: { icon: Zap, color: 'bg-green-100 text-green-600', label: '生成工具' },
  system: { icon: Settings, color: 'bg-purple-100 text-purple-600', label: '系统工具' },
  template: { icon: Layers, color: 'bg-orange-100 text-orange-600', label: '模板工具' },
  mcp: { icon: Server, color: 'bg-cyan-100 text-cyan-600', label: 'MCP 工具' },
};

export default function ToolsPage() {
  // 状态管理
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedType, setSelectedType] = useState<string>('');
  const [selectedCategory, setSelectedCategory] = useState<string>('');
  const [selectedTool, setSelectedTool] = useState<ToolInfo | null>(null);
  const [activeTab, setActiveTab] = useState<'tools' | 'mcp'>('tools');
  const [testParams, setTestParams] = useState<Record<string, string>>({});  // 测试参数

  // 数据获取
  const { data: toolsData, isLoading: toolsLoading } = useToolList({
    type: selectedType || undefined,
    category: selectedCategory || undefined,
    search: searchQuery || undefined,
  });
  
  const { data: categoriesData } = useToolCategories();
  const { data: mcpData, isLoading: mcpLoading } = useMCPServers();
  
  // 工具测试
  const testToolMutation = useTestTool();
  const updateMCPMutation = useUpdateMCPServer();

  // 按类型分组工具
  const groupedTools = useMemo(() => {
    if (!toolsData?.tools) return {};
    
    const groups: Record<string, ToolInfo[]> = {};
    toolsData.tools.forEach(tool => {
      const type = tool.type;
      if (!groups[type]) groups[type] = [];
      groups[type].push(tool);
    });
    return groups;
  }, [toolsData]);

  // 渲染工具卡片
  const renderToolCard = (tool: ToolInfo) => {
    const config = toolTypeConfig[tool.type] || toolTypeConfig.builtin;
    const Icon = config.icon;
    const isSelected = selectedTool?.name === tool.name && selectedTool?.type === tool.type;
    
    return (
      <div
        key={`${tool.type}-${tool.name}`}
        onClick={() => {
          setSelectedTool(tool);
          setTestParams({});  // 切换工具时清空测试参数
          testToolMutation.reset();  // 清空之前的测试结果
        }}
        className={`p-3 rounded-lg border cursor-pointer transition-all hover:shadow-md ${
          isSelected ? 'border-blue-500 bg-blue-50' : 'border-gray-200 hover:border-gray-300'
        }`}
      >
        <div className="flex items-start gap-3">
          <div className={`p-2 rounded-lg ${config.color}`}>
            <Icon className="w-4 h-4" />
          </div>
          <div className="flex-1 min-w-0">
            <h4 className="font-medium text-gray-900 truncate">{tool.name}</h4>
            <p className="text-xs text-gray-500 mt-0.5 line-clamp-2">
              {tool.description || '暂无描述'}
            </p>
            {tool.category && (
              <span className="inline-block mt-1 px-2 py-0.5 text-xs bg-gray-100 text-gray-600 rounded">
                {tool.category}
              </span>
            )}
          </div>
          <ChevronRight className="w-4 h-4 text-gray-400 flex-shrink-0" />
        </div>
      </div>
    );
  };


  // 渲染工具详情面板
  const renderToolDetail = () => {
    if (!selectedTool) {
      return (
        <div className="flex flex-col items-center justify-center h-full text-gray-400">
          <Wrench className="w-12 h-12 mb-3" />
          <p>选择一个工具查看详情</p>
        </div>
      );
    }

    const config = toolTypeConfig[selectedTool.type] || toolTypeConfig.builtin;
    const Icon = config.icon;
    
    // 检查是否有必填参数未填写
    const hasRequiredParams = selectedTool.parameters?.some(p => p.required) || false;
    const allRequiredFilled = selectedTool.parameters
      ?.filter(p => p.required)
      .every(p => testParams[p.name]?.trim()) || !hasRequiredParams;

    // 构建测试参数对象（转换类型）
    const buildTestParameters = () => {
      const params: Record<string, unknown> = {};
      selectedTool.parameters?.forEach(param => {
        const value = testParams[param.name];
        if (value !== undefined && value !== '') {
          // 根据类型转换值
          if (param.type === 'int' || param.type === 'float' || param.type === 'number') {
            params[param.name] = Number(value);
          } else if (param.type === 'bool' || param.type === 'boolean') {
            params[param.name] = value.toLowerCase() === 'true';
          } else if (param.type.startsWith('List') || param.type.startsWith('list')) {
            try {
              params[param.name] = JSON.parse(value);
            } catch {
              params[param.name] = value.split(',').map(s => s.trim());
            }
          } else if (param.type.startsWith('Dict') || param.type.startsWith('dict')) {
            try {
              params[param.name] = JSON.parse(value);
            } catch {
              params[param.name] = value;
            }
          } else {
            params[param.name] = value;
          }
        }
      });
      return params;
    };

    return (
      <div className="h-full flex flex-col">
        {/* 工具头部 */}
        <div className="p-4 border-b">
          <div className="flex items-center gap-3">
            <div className={`p-3 rounded-lg ${config.color}`}>
              <Icon className="w-6 h-6" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-gray-900">{selectedTool.name}</h2>
              <span className={`inline-block px-2 py-0.5 text-xs rounded ${config.color}`}>
                {config.label}
              </span>
            </div>
          </div>
        </div>

        {/* 工具信息 */}
        <div className="flex-1 overflow-auto p-4 space-y-4">
          {/* 描述 */}
          <div>
            <h3 className="text-sm font-medium text-gray-700 mb-1">描述</h3>
            <p className="text-sm text-gray-600">{selectedTool.description || '暂无描述'}</p>
          </div>

          {/* 分类 */}
          {selectedTool.category && (
            <div>
              <h3 className="text-sm font-medium text-gray-700 mb-1">分类</h3>
              <span className="inline-block px-2 py-1 text-sm bg-gray-100 text-gray-700 rounded">
                {selectedTool.category}
              </span>
            </div>
          )}

          {/* 包信息（内置工具） */}
          {selectedTool.package && (
            <div>
              <h3 className="text-sm font-medium text-gray-700 mb-1">安装包</h3>
              <code className="text-sm bg-gray-100 px-2 py-1 rounded">{selectedTool.package}</code>
            </div>
          )}

          {/* 参数列表 */}
          {selectedTool.parameters && selectedTool.parameters.length > 0 && (
            <div>
              <h3 className="text-sm font-medium text-gray-700 mb-2">参数</h3>
              <div className="space-y-2">
                {selectedTool.parameters.map((param, idx) => (
                  <div key={idx} className="p-2 bg-gray-50 rounded text-sm">
                    <div className="flex items-center gap-2">
                      <span className="font-mono font-medium text-gray-900">{param.name}</span>
                      <span className="text-xs text-gray-500">: {param.type}</span>
                      {param.required && (
                        <span className="text-xs text-red-500">*必填</span>
                      )}
                    </div>
                    {param.description && (
                      <p className="text-xs text-gray-500 mt-1">{param.description}</p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 返回值类型 */}
          {selectedTool.return_type && (
            <div>
              <h3 className="text-sm font-medium text-gray-700 mb-1">返回值</h3>
              <code className="text-sm bg-green-50 text-green-700 px-2 py-1 rounded">
                {selectedTool.return_type}
              </code>
            </div>
          )}

          {/* 文件路径 */}
          {selectedTool.file_path && (
            <div>
              <h3 className="text-sm font-medium text-gray-700 mb-1">文件路径</h3>
              <code className="text-xs bg-gray-100 px-2 py-1 rounded block overflow-x-auto">
                {selectedTool.file_path}
              </code>
            </div>
          )}

          {/* 源代码预览 */}
          {selectedTool.source_code && (
            <div>
              <h3 className="text-sm font-medium text-gray-700 mb-2">源代码</h3>
              <pre className="text-xs bg-gray-900 text-gray-100 p-3 rounded-lg overflow-x-auto max-h-64">
                <code>{selectedTool.source_code}</code>
              </pre>
            </div>
          )}
        </div>

        {/* 测试区域 */}
        {selectedTool.type !== 'builtin' && selectedTool.type !== 'mcp' && (
          <div className="p-4 border-t bg-gray-50">
            <h3 className="text-sm font-medium text-gray-700 mb-3">测试工具</h3>
            
            {/* 参数输入表单 */}
            {selectedTool.parameters && selectedTool.parameters.length > 0 && (
              <div className="space-y-3 mb-4">
                {selectedTool.parameters.map((param, idx) => (
                  <div key={idx}>
                    <label className="block text-xs font-medium text-gray-600 mb-1">
                      {param.name}
                      {param.required && <span className="text-red-500 ml-1">*</span>}
                      <span className="text-gray-400 ml-2">({param.type})</span>
                    </label>
                    {param.type.startsWith('Dict') || param.type.startsWith('dict') || 
                     param.type.startsWith('List') || param.type.startsWith('list') ? (
                      <textarea
                        value={testParams[param.name] || ''}
                        onChange={(e) => setTestParams(prev => ({
                          ...prev,
                          [param.name]: e.target.value
                        }))}
                        placeholder={param.description || `输入 ${param.name}（JSON 格式）`}
                        className="w-full px-3 py-2 text-sm border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono"
                        rows={3}
                      />
                    ) : (
                      <input
                        type={param.type === 'int' || param.type === 'float' || param.type === 'number' ? 'number' : 'text'}
                        value={testParams[param.name] || ''}
                        onChange={(e) => setTestParams(prev => ({
                          ...prev,
                          [param.name]: e.target.value
                        }))}
                        placeholder={param.description || `输入 ${param.name}`}
                        className="w-full px-3 py-2 text-sm border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                      />
                    )}
                  </div>
                ))}
              </div>
            )}
            
            {/* 测试按钮 */}
            <div className="flex gap-2">
              <button
                onClick={() => {
                  testToolMutation.mutate({
                    toolName: selectedTool.name,
                    parameters: buildTestParameters(),
                  });
                }}
                disabled={testToolMutation.isPending || !allRequiredFilled}
                className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {testToolMutation.isPending ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Play className="w-4 h-4" />
                )}
                {testToolMutation.isPending ? '执行中...' : '执行测试'}
              </button>
              
              {Object.keys(testParams).length > 0 && (
                <button
                  onClick={() => {
                    setTestParams({});
                    testToolMutation.reset();
                  }}
                  className="px-3 py-2 text-gray-600 border rounded-lg hover:bg-gray-100"
                  title="重置参数"
                >
                  <RotateCcw className="w-4 h-4" />
                </button>
              )}
            </div>
            
            {!allRequiredFilled && hasRequiredParams && (
              <p className="text-xs text-amber-600 mt-2">请填写所有必填参数后再执行测试</p>
            )}
            
            {/* 测试结果 */}
            {testToolMutation.data && (
              <div className={`mt-3 p-3 rounded-lg text-sm ${
                testToolMutation.data.success ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'
              }`}>
                {testToolMutation.data.success ? (
                  <div className="flex items-start gap-2">
                    <CheckCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
                    <div className="flex-1 min-w-0">
                      <p className="font-medium">执行成功</p>
                      {testToolMutation.data.output && (
                        <pre className="mt-1 text-xs whitespace-pre-wrap break-all bg-green-100 p-2 rounded">
                          {testToolMutation.data.output}
                        </pre>
                      )}
                      {testToolMutation.data.duration_ms && (
                        <p className="text-xs mt-1">耗时: {testToolMutation.data.duration_ms}ms</p>
                      )}
                    </div>
                  </div>
                ) : (
                  <div className="flex items-start gap-2">
                    <XCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
                    <div className="flex-1 min-w-0">
                      <p className="font-medium">执行失败</p>
                      {testToolMutation.data.error && (
                        <pre className="mt-1 text-xs whitespace-pre-wrap break-all bg-red-100 p-2 rounded">
                          {testToolMutation.data.error}
                        </pre>
                      )}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    );
  };


  // 渲染 MCP 服务器列表
  const renderMCPServers = () => {
    if (mcpLoading) {
      return (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
        </div>
      );
    }

    if (!mcpData?.servers || mcpData.servers.length === 0) {
      return (
        <div className="text-center py-12 text-gray-500">
          <Server className="w-12 h-12 mx-auto mb-3 text-gray-300" />
          <p>暂无 MCP 服务器配置</p>
        </div>
      );
    }

    return (
      <div className="space-y-3">
        {mcpData.servers.map((server) => (
          <div
            key={server.name}
            className="p-4 border rounded-lg hover:shadow-md transition-shadow"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className={`p-2 rounded-lg ${server.disabled ? 'bg-gray-100 text-gray-400' : 'bg-cyan-100 text-cyan-600'}`}>
                  <Server className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="font-medium text-gray-900">{server.name}</h3>
                  <p className="text-xs text-gray-500 font-mono">
                    {server.command} {server.args.join(' ')}
                  </p>
                </div>
              </div>
              
              <div className="flex items-center gap-2">
                <span className={`px-2 py-1 text-xs rounded ${
                  server.disabled ? 'bg-gray-100 text-gray-500' : 'bg-green-100 text-green-600'
                }`}>
                  {server.disabled ? '已禁用' : '已启用'}
                </span>
                
                <button
                  onClick={() => {
                    updateMCPMutation.mutate({
                      serverName: server.name,
                      config: { disabled: !server.disabled },
                    });
                  }}
                  disabled={updateMCPMutation.isPending}
                  className={`px-3 py-1 text-sm rounded transition-colors ${
                    server.disabled
                      ? 'bg-green-600 text-white hover:bg-green-700'
                      : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                  }`}
                >
                  {server.disabled ? '启用' : '禁用'}
                </button>
              </div>
            </div>
            
            {/* 环境变量 */}
            {Object.keys(server.env).length > 0 && (
              <div className="mt-3 pt-3 border-t">
                <p className="text-xs text-gray-500 mb-1">环境变量:</p>
                <div className="flex flex-wrap gap-1">
                  {Object.entries(server.env).map(([key, value]) => (
                    <span key={key} className="text-xs bg-gray-100 px-2 py-0.5 rounded font-mono">
                      {key}={value}
                    </span>
                  ))}
                </div>
              </div>
            )}
            
            {/* 自动批准工具 */}
            {server.auto_approve.length > 0 && (
              <div className="mt-2">
                <p className="text-xs text-gray-500 mb-1">自动批准:</p>
                <div className="flex flex-wrap gap-1">
                  {server.auto_approve.map((tool) => (
                    <span key={tool} className="text-xs bg-blue-100 text-blue-600 px-2 py-0.5 rounded">
                      {tool}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    );
  };


  return (
    <div className="min-h-screen bg-gray-50">
      {/* 页面头部 */}
      <div className="bg-white border-b px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold text-gray-900">能力工具</h1>
            <p className="text-sm text-gray-500 mt-1">
              管理和测试 Agent 可用的工具能力
            </p>
          </div>
          
          {/* 统计信息 */}
          {toolsData && (
            <div className="flex items-center gap-4 text-sm">
              <div className="flex items-center gap-1.5">
                <Box className="w-4 h-4 text-gray-400" />
                <span className="text-gray-600">共 {toolsData.total} 个工具</span>
              </div>
              {mcpData && (
                <div className="flex items-center gap-1.5">
                  <Server className="w-4 h-4 text-gray-400" />
                  <span className="text-gray-600">{mcpData.enabled} 个 MCP 服务器</span>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Tab 切换 */}
        <div className="flex gap-4 mt-4">
          <button
            onClick={() => setActiveTab('tools')}
            className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
              activeTab === 'tools'
                ? 'bg-blue-100 text-blue-700'
                : 'text-gray-600 hover:bg-gray-100'
            }`}
          >
            <div className="flex items-center gap-2">
              <Wrench className="w-4 h-4" />
              工具列表
            </div>
          </button>
          <button
            onClick={() => setActiveTab('mcp')}
            className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
              activeTab === 'mcp'
                ? 'bg-blue-100 text-blue-700'
                : 'text-gray-600 hover:bg-gray-100'
            }`}
          >
            <div className="flex items-center gap-2">
              <Server className="w-4 h-4" />
              MCP 服务器
            </div>
          </button>
        </div>
      </div>

      {/* 主内容区 */}
      {activeTab === 'tools' ? (
        <div className="flex h-[calc(100vh-160px)]">
          {/* 左侧：工具列表 */}
          <div className="w-1/2 border-r bg-white overflow-hidden flex flex-col">
            {/* 搜索和筛选 */}
            <div className="p-4 border-b space-y-3">
              {/* 搜索框 */}
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                <input
                  type="text"
                  placeholder="搜索工具..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-10 pr-4 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              
              {/* 筛选器 */}
              <div className="flex gap-2">
                <select
                  value={selectedType}
                  onChange={(e) => setSelectedType(e.target.value)}
                  className="px-3 py-1.5 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">全部类型</option>
                  <option value="builtin">内置工具</option>
                  <option value="generated">生成工具</option>
                  <option value="system">系统工具</option>
                  <option value="template">模板工具</option>
                  <option value="mcp">MCP 工具</option>
                </select>
                
                <select
                  value={selectedCategory}
                  onChange={(e) => setSelectedCategory(e.target.value)}
                  className="px-3 py-1.5 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">全部分类</option>
                  {categoriesData?.categories.map((cat) => (
                    <option key={cat} value={cat}>{cat}</option>
                  ))}
                </select>
              </div>
            </div>

            {/* 工具列表 */}
            <div className="flex-1 overflow-auto p-4">
              {toolsLoading ? (
                <div className="flex items-center justify-center py-12">
                  <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
                </div>
              ) : !toolsData?.tools || toolsData.tools.length === 0 ? (
                <div className="text-center py-12 text-gray-500">
                  <Wrench className="w-12 h-12 mx-auto mb-3 text-gray-300" />
                  <p>没有找到匹配的工具</p>
                </div>
              ) : (
                <div className="space-y-6">
                  {Object.entries(groupedTools).map(([type, tools]) => (
                    <div key={type}>
                      <div className="flex items-center gap-2 mb-2">
                        <span className={`px-2 py-0.5 text-xs rounded ${toolTypeConfig[type]?.color || 'bg-gray-100 text-gray-600'}`}>
                          {toolTypeConfig[type]?.label || type}
                        </span>
                        <span className="text-xs text-gray-400">({tools.length})</span>
                      </div>
                      <div className="space-y-2">
                        {tools.map(renderToolCard)}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* 右侧：工具详情 */}
          <div className="w-1/2 bg-white">
            {renderToolDetail()}
          </div>
        </div>
      ) : (
        <div className="p-6 max-w-4xl mx-auto">
          {renderMCPServers()}
        </div>
      )}
    </div>
  );
}
