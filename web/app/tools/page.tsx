'use client';

import { useState } from 'react';
import { Header } from '@/components/layout';
import { Card, CardHeader, CardTitle, CardContent, Button, Input, Badge, Empty } from '@/components/ui';
import {
  Wrench,
  Search,
  Globe,
  Database,
  FileText,
  Code,
  Zap,
  ExternalLink,
  Settings,
  Plus,
} from 'lucide-react';

// Mock tool data - in real app, this would come from API
const tools = [
  {
    id: 'web-search',
    name: 'Web Search',
    description: '搜索互联网获取最新信息',
    category: 'network',
    icon: Globe,
    status: 'active',
    usageCount: 1234,
  },
  {
    id: 'database-query',
    name: 'Database Query',
    description: '查询和操作数据库',
    category: 'data',
    icon: Database,
    status: 'active',
    usageCount: 856,
  },
  {
    id: 'file-reader',
    name: 'File Reader',
    description: '读取和解析各种文件格式',
    category: 'file',
    icon: FileText,
    status: 'active',
    usageCount: 2341,
  },
  {
    id: 'code-executor',
    name: 'Code Executor',
    description: '执行 Python 代码',
    category: 'code',
    icon: Code,
    status: 'active',
    usageCount: 567,
  },
  {
    id: 'api-caller',
    name: 'API Caller',
    description: '调用外部 REST API',
    category: 'network',
    icon: Zap,
    status: 'active',
    usageCount: 1089,
  },
];

const categories = [
  { id: 'all', name: '全部' },
  { id: 'network', name: '网络' },
  { id: 'data', name: '数据' },
  { id: 'file', name: '文件' },
  { id: 'code', name: '代码' },
];

export default function ToolsPage() {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('all');

  const filteredTools = tools.filter((tool) => {
    const matchesSearch = tool.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      tool.description.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesCategory = selectedCategory === 'all' || tool.category === selectedCategory;
    return matchesSearch && matchesCategory;
  });

  return (
    <div className="page-container">
      <Header
        title="工具库"
        description="浏览和管理 Agent 可用的工具"
        actions={
          <Button>
            <Plus className="w-4 h-4" />
            添加工具
          </Button>
        }
      />

      <div className="page-content">
        {/* Filters */}
        <div className="flex flex-col sm:flex-row gap-4 mb-6">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <Input
              placeholder="搜索工具..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10"
            />
          </div>
          <div className="flex gap-2">
            {categories.map((category) => (
              <button
                key={category.id}
                onClick={() => setSelectedCategory(category.id)}
                className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
                  selectedCategory === category.id
                    ? 'bg-primary-100 text-primary-700'
                    : 'bg-white text-gray-600 hover:bg-gray-100 border border-gray-200'
                }`}
              >
                {category.name}
              </button>
            ))}
          </div>
        </div>

        {/* Tools Grid */}
        {filteredTools.length === 0 ? (
          <Empty
            icon={Wrench}
            title="没有找到工具"
            description="尝试调整搜索条件"
          />
        ) : (
          <div className="grid gap-6 grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
            {filteredTools.map((tool) => (
              <Card key={tool.id} hover>
                <div className="flex items-start gap-4">
                  <div className="w-12 h-12 rounded-xl bg-primary-50 flex items-center justify-center flex-shrink-0">
                    <tool.icon className="w-6 h-6 text-primary-600" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <h3 className="font-semibold text-gray-900">{tool.name}</h3>
                      <Badge variant="success" size="sm">可用</Badge>
                    </div>
                    <p className="text-sm text-gray-500 mb-3">{tool.description}</p>
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-gray-400">
                        {tool.usageCount.toLocaleString()} 次调用
                      </span>
                      <Button variant="ghost" size="sm">
                        <Settings className="w-4 h-4" />
                        配置
                      </Button>
                    </div>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        )}

        {/* MCP Configuration */}
        <Card className="mt-8">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Settings className="w-5 h-5 text-gray-500" />
              MCP 服务器配置
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-gray-500 mb-4">
              配置 Model Context Protocol (MCP) 服务器以扩展 Agent 的工具能力
            </p>
            <div className="bg-gray-50 rounded-lg p-4 font-mono text-sm">
              <pre className="text-gray-700 overflow-x-auto">
{`{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/allowed/files"]
    }
  }
}`}
              </pre>
            </div>
            <div className="mt-4 flex gap-3">
              <Button variant="outline">
                <ExternalLink className="w-4 h-4" />
                查看文档
              </Button>
              <Button variant="outline">
                编辑配置
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
