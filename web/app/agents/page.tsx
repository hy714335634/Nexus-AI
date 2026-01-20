'use client';

import { useState, useMemo } from 'react';
import Link from 'next/link';
import { Header } from '@/components/layout';
import { Card, Button, Badge, Input, Empty } from '@/components/ui';
import { StatusBadge } from '@/components/status-badge';
import { useAgentsV2 } from '@/hooks/use-agents-v2';
import { formatRelativeTime, formatNumber, truncate } from '@/lib/utils';
import {
  Bot,
  Plus,
  Search,
  Zap,
  Cloud,
  HardDrive,
  Tag,
  X,
  MessageSquare,
} from 'lucide-react';
import type { AgentStatus, AgentSummary, AgentDeploymentType } from '@/types/api-v2';

export default function AgentsPage() {
  const { data: agents, isLoading, error } = useAgentsV2({ limit: 100 });
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<AgentStatus | 'all'>('all');
  const [deploymentTypeFilter, setDeploymentTypeFilter] = useState<AgentDeploymentType | 'all'>('all');
  const [selectedTags, setSelectedTags] = useState<string[]>([]);

  // Extract all unique tags from agents
  const allTags = useMemo(() => {
    if (!agents) return [];
    const tagSet = new Set<string>();
    agents.forEach((agent) => {
      if (agent.category) tagSet.add(agent.category);
      // Add more tag sources if available in the future
    });
    return Array.from(tagSet).sort();
  }, [agents]);

  const filteredAgents = agents?.filter((agent) => {
    const matchesSearch = agent.agent_name.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesStatus = statusFilter === 'all' || agent.status === statusFilter;
    const matchesDeploymentType = deploymentTypeFilter === 'all' || agent.deployment_type === deploymentTypeFilter;
    const matchesTags = selectedTags.length === 0 || (agent.category && selectedTags.includes(agent.category));
    return matchesSearch && matchesStatus && matchesDeploymentType && matchesTags;
  }) || [];

  const statusCounts = {
    all: agents?.length || 0,
    running: agents?.filter((a) => a.status === 'running').length || 0,
    offline: agents?.filter((a) => a.status === 'offline').length || 0,
    error: agents?.filter((a) => a.status === 'error').length || 0,
    deploying: agents?.filter((a) => a.status === 'deploying').length || 0,
  };

  const deploymentTypeCounts = {
    all: agents?.length || 0,
    local: agents?.filter((a) => a.deployment_type === 'local').length || 0,
    agentcore: agents?.filter((a) => a.deployment_type === 'agentcore').length || 0,
  };

  const toggleTag = (tag: string) => {
    setSelectedTags((prev) =>
      prev.includes(tag) ? prev.filter((t) => t !== tag) : [...prev, tag]
    );
  };

  const clearAllFilters = () => {
    setSearchQuery('');
    setStatusFilter('all');
    setDeploymentTypeFilter('all');
    setSelectedTags([]);
  };

  const hasActiveFilters = searchQuery || statusFilter !== 'all' || deploymentTypeFilter !== 'all' || selectedTags.length > 0;

  return (
    <div className="page-container">
      <Header
        title="Agent"
        description="管理和监控您的智能 Agent"
        actions={
          <Link href="/agents/new">
            <Button className="bg-gradient-to-r from-primary-600 to-accent-600 hover:from-primary-700 hover:to-accent-700">
              <Plus className="w-4 h-4" />
              创建 Agent
            </Button>
          </Link>
        }
      />

      <div className="page-content">
        {/* Search and Filters */}
        <div className="space-y-4 mb-6">
          {/* Search Bar */}
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="relative flex-1 max-w-md">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <Input
                placeholder="搜索 Agent..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10"
              />
            </div>
            {hasActiveFilters && (
              <Button variant="ghost" size="sm" onClick={clearAllFilters}>
                <X className="w-4 h-4 mr-1" />
                清除筛选
              </Button>
            )}
          </div>

          {/* Filter Buttons */}
          <div className="flex gap-2 flex-wrap">
            {/* Deployment Type Filter */}
            {(['all', 'local', 'agentcore'] as const).map((type) => (
              <button
                key={type}
                onClick={() => setDeploymentTypeFilter(type)}
                className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
                  deploymentTypeFilter === type
                    ? 'bg-accent-100 text-accent-700'
                    : 'bg-white text-gray-600 hover:bg-gray-100 border border-gray-200'
                }`}
              >
                {type === 'all' ? '全部类型' : type === 'local' ? '本地部署' : '云端托管'}
                <span className="ml-1.5 text-xs">({deploymentTypeCounts[type]})</span>
              </button>
            ))}
            <div className="w-px bg-gray-200 mx-1" />
            {/* Status Filter */}
            {(['all', 'running', 'offline', 'error'] as const).map((status) => (
              <button
                key={status}
                onClick={() => setStatusFilter(status)}
                className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
                  statusFilter === status
                    ? 'bg-primary-100 text-primary-700'
                    : 'bg-white text-gray-600 hover:bg-gray-100 border border-gray-200'
                }`}
              >
                {status === 'all' ? '全部状态' : status === 'running' ? '运行中' : status === 'offline' ? '离线' : '异常'}
                <span className="ml-1.5 text-xs">({statusCounts[status]})</span>
              </button>
            ))}
          </div>

          {/* Tag Filter */}
          {allTags.length > 0 && (
            <div className="flex items-center gap-2 flex-wrap">
              <div className="flex items-center gap-1 text-sm text-gray-500">
                <Tag className="w-4 h-4" />
                <span>分类:</span>
              </div>
              {allTags.map((tag) => (
                <button
                  key={tag}
                  onClick={() => toggleTag(tag)}
                  className={`px-3 py-1.5 text-sm rounded-full transition-colors ${
                    selectedTags.includes(tag)
                      ? 'bg-agent-100 text-agent-700 border border-agent-300'
                      : 'bg-gray-50 text-gray-600 hover:bg-gray-100 border border-gray-200'
                  }`}
                >
                  {tag}
                  {selectedTags.includes(tag) && <X className="w-3 h-3 ml-1 inline" />}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Agent Grid */}
        {isLoading ? (
          <div className="grid gap-6 grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
            {[1, 2, 3, 4, 5, 6].map((i) => (
              <Card key={i} padding="none">
                <div className="p-6">
                  <div className="flex items-start gap-4 mb-4">
                    <div className="w-12 h-12 rounded-xl bg-gray-100 animate-pulse" />
                    <div className="flex-1">
                      <div className="h-5 w-32 bg-gray-100 rounded animate-pulse mb-2" />
                      <div className="h-4 w-20 bg-gray-100 rounded animate-pulse" />
                    </div>
                  </div>
                  <div className="h-4 w-full bg-gray-100 rounded animate-pulse mb-2" />
                  <div className="h-4 w-3/4 bg-gray-100 rounded animate-pulse" />
                </div>
              </Card>
            ))}
          </div>
        ) : filteredAgents.length === 0 ? (
          <Empty
            icon={Bot}
            title={hasActiveFilters ? '没有找到匹配的 Agent' : '暂无 Agent'}
            description={
              hasActiveFilters
                ? '尝试调整搜索条件或筛选器'
                : '创建您的第一个 Agent，开始自动化业务流程'
            }
            action={
              !hasActiveFilters && (
                <Link href="/agents/new">
                  <Button className="bg-gradient-to-r from-primary-600 to-accent-600 hover:from-primary-700 hover:to-accent-700">
                    <Plus className="w-4 h-4" />
                    创建 Agent
                  </Button>
                </Link>
              )
            }
          />
        ) : (
          <div className="grid gap-6 grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
            {filteredAgents.map((agent) => (
              <AgentCard key={agent.agent_id} agent={agent} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

interface AgentCardProps {
  agent: AgentSummary;
}

function AgentCard({ agent }: AgentCardProps) {
  return (
    <Card hover padding="none" className="h-full group">
      <div className="p-6">
        <div className="flex items-start justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-primary-500 via-accent-500 to-agent-500 flex items-center justify-center relative">
              <Bot className="w-6 h-6 text-white" />
              {agent.status === 'running' && (
                <span className="absolute -top-1 -right-1 w-3 h-3 bg-green-500 rounded-full border-2 border-white animate-pulse" />
              )}
            </div>
            <div>
              <h3 className="font-semibold text-gray-900">{truncate(agent.agent_name, 20)}</h3>
              <div className="flex items-center gap-2 mt-1">
                <StatusBadge status={agent.status as any} size="sm" />
                {agent.version && (
                  <span className="text-xs text-gray-400">{agent.version}</span>
                )}
              </div>
            </div>
          </div>
        </div>

        {(agent.category || agent.deployment_type) && (
          <div className="flex flex-wrap gap-1.5 mb-4">
            {agent.deployment_type && (
              <Badge 
                variant={agent.deployment_type === 'agentcore' ? 'info' : 'default'} 
                size="sm"
              >
                {agent.deployment_type === 'agentcore' ? (
                  <><Cloud className="w-3 h-3 mr-1" />云端托管</>
                ) : (
                  <><HardDrive className="w-3 h-3 mr-1" />本地部署</>
                )}
              </Badge>
            )}
            {agent.category && (
              <Badge variant="outline" size="sm">
                {agent.category}
              </Badge>
            )}
          </div>
        )}

        <div className="flex items-center justify-between pt-4 border-t border-gray-100">
          <div className="flex items-center gap-4 text-sm text-gray-500">
            <span className="flex items-center gap-1">
              <Zap className="w-4 h-4 text-agent-500" />
              {formatNumber(agent.total_invocations || 0)} 次调用
            </span>
          </div>
          <span className="text-xs text-gray-400">
            {formatRelativeTime(agent.created_at)}
          </span>
        </div>

        {/* Action buttons - show on hover */}
        <div className="flex gap-2 mt-4 pt-4 border-t border-gray-100 opacity-0 group-hover:opacity-100 transition-opacity">
          <Link href={`/agents/${agent.agent_id}`} className="flex-1">
            <Button variant="outline" size="sm" className="w-full">
              查看详情
            </Button>
          </Link>
          <Link href={`/chat?agent=${agent.agent_id}`}>
            <Button size="sm" className="bg-gradient-to-r from-primary-600 to-accent-600">
              <MessageSquare className="w-4 h-4" />
              对话
            </Button>
          </Link>
        </div>
      </div>
    </Card>
  );
}
