'use client';

import { useState, useCallback } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { Header } from '@/components/layout';
import { Card, CardContent, Button, Badge, Empty } from '@/components/ui';
import { PromptYamlViewer, ToolCodeViewer, PythonCodeViewer } from '@components/viewer';
import { useAgentDetailV2, useAgentFilesV2 } from '@/hooks/use-agents-v2';
import { 
  saveAgentCode, 
  saveAgentPrompt, 
  saveAgentTool 
} from '@/lib/api-v2';
import {
  ArrowLeft,
  Bot,
  Code,
  FileText,
  Wrench,
  RefreshCw,
  AlertCircle,
  CheckCircle2,
  FolderOpen,
} from 'lucide-react';

type FileTab = 'code' | 'prompt' | 'tools';

export default function AgentFilesPage() {
  const params = useParams();
  const agentId = params.id as string;
  
  const { data: agent, isLoading: agentLoading } = useAgentDetailV2(agentId);
  
  // 获取文件数据
  const { 
    data: filesData, 
    isLoading: filesLoading, 
    error: filesError,
    refetch: refreshFiles 
  } = useAgentFilesV2(agentId);
  
  const [activeTab, setActiveTab] = useState<FileTab>('prompt');
  const [saving, setSaving] = useState(false);
  const [saveMessage, setSaveMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  
  // 显示保存消息
  const showSaveMessage = useCallback((type: 'success' | 'error', text: string) => {
    setSaveMessage({ type, text });
    setTimeout(() => setSaveMessage(null), 3000);
  }, []);
  
  // 保存代码文件
  const handleSaveCode = useCallback(async (content: string) => {
    setSaving(true);
    try {
      await saveAgentCode(agentId, content);
      showSaveMessage('success', '代码文件保存成功');
      refreshFiles();
    } catch (error: unknown) {
      const errorMessage = error instanceof Error ? error.message : '保存失败';
      showSaveMessage('error', errorMessage);
    } finally {
      setSaving(false);
    }
  }, [agentId, refreshFiles, showSaveMessage]);
  
  // 保存提示词文件
  const handleSavePrompt = useCallback(async (content: string) => {
    setSaving(true);
    try {
      await saveAgentPrompt(agentId, content);
      showSaveMessage('success', '提示词文件保存成功');
      refreshFiles();
    } catch (error: unknown) {
      const errorMessage = error instanceof Error ? error.message : '保存失败';
      showSaveMessage('error', errorMessage);
    } finally {
      setSaving(false);
    }
  }, [agentId, refreshFiles, showSaveMessage]);
  
  // 保存工具文件
  const handleSaveTool = useCallback(async (toolName: string, content: string) => {
    setSaving(true);
    try {
      await saveAgentTool(agentId, toolName, content);
      showSaveMessage('success', '工具文件保存成功');
      refreshFiles();
    } catch (error: unknown) {
      const errorMessage = error instanceof Error ? error.message : '保存失败';
      showSaveMessage('error', errorMessage);
    } finally {
      setSaving(false);
    }
  }, [agentId, refreshFiles, showSaveMessage]);
  
  const isLoading = agentLoading || filesLoading;
  
  if (isLoading) {
    return (
      <div className="page-container">
        <Header title="加载中..." />
        <div className="page-content">
          <div className="animate-pulse space-y-6">
            <div className="h-12 bg-gray-100 rounded-xl w-1/3" />
            <div className="h-96 bg-gray-100 rounded-xl" />
          </div>
        </div>
      </div>
    );
  }
  
  if (filesError || !agent) {
    return (
      <div className="page-container">
        <Header title="Agent 文件" />
        <div className="page-content">
          <Empty
            icon={Bot}
            title="无法加载文件"
            description={filesError?.message || "Agent 不存在或无法访问"}
            action={
              <Link href={`/agents/${agentId}`}>
                <Button variant="outline">
                  <ArrowLeft className="w-4 h-4" />
                  返回详情
                </Button>
              </Link>
            }
          />
        </div>
      </div>
    );
  }
  
  const codeFile = filesData?.code_file;
  const promptFile = filesData?.prompt_file;
  const toolFiles = filesData?.tool_files || [];
  
  // 转换工具文件格式供ToolCodeViewer使用
  const toolFilesForViewer = toolFiles.map(t => ({
    name: t.name,
    path: t.path,
    content: t.content || '',
    exists: t.exists,
  }));
  
  return (
    <div className="page-container">
      <Header
        title={`${agent.agent_name} - 文件管理`}
        description="查看和编辑 Agent 的提示词、代码和工具文件"
        actions={
          <div className="flex items-center gap-3">
            <Button 
              variant="ghost" 
              onClick={() => refreshFiles()}
              disabled={filesLoading}
            >
              <RefreshCw className={`w-4 h-4 ${filesLoading ? 'animate-spin' : ''}`} />
              刷新
            </Button>
            <Link href={`/agents/${agentId}`}>
              <Button variant="ghost">
                <ArrowLeft className="w-4 h-4" />
                返回
              </Button>
            </Link>
          </div>
        }
      />
      
      <div className="page-content">
        {/* 保存消息提示 */}
        {saveMessage && (
          <div 
            className={`mb-4 p-3 rounded-lg flex items-center gap-2 ${
              saveMessage.type === 'success' 
                ? 'bg-green-50 text-green-700 border border-green-200' 
                : 'bg-red-50 text-red-700 border border-red-200'
            }`}
          >
            {saveMessage.type === 'success' ? (
              <CheckCircle2 className="w-4 h-4" />
            ) : (
              <AlertCircle className="w-4 h-4" />
            )}
            {saveMessage.text}
          </div>
        )}
        
        {/* 文件概览卡片 */}
        <div className="grid grid-cols-3 gap-4 mb-6">
          <FileOverviewCard
            icon={FileText}
            iconColor="text-purple-500"
            iconBg="bg-purple-50"
            title="提示词 YAML"
            subtitle={promptFile?.exists ? promptFile.name : '不存在'}
            status={promptFile?.exists ? 'available' : 'missing'}
            active={activeTab === 'prompt'}
            onClick={() => setActiveTab('prompt')}
          />
          <FileOverviewCard
            icon={Code}
            iconColor="text-blue-500"
            iconBg="bg-blue-50"
            title="Agent 代码"
            subtitle={codeFile?.exists ? codeFile.name : '不存在'}
            status={codeFile?.exists ? 'available' : 'missing'}
            active={activeTab === 'code'}
            onClick={() => setActiveTab('code')}
          />
          <FileOverviewCard
            icon={Wrench}
            iconColor="text-amber-500"
            iconBg="bg-amber-50"
            title="工具文件"
            subtitle={`${toolFiles.length} 个文件`}
            status={toolFiles.length > 0 ? 'available' : 'empty'}
            active={activeTab === 'tools'}
            onClick={() => setActiveTab('tools')}
          />
        </div>
        
        {/* 文件内容区域 */}
        <div className="space-y-4">
          {activeTab === 'prompt' && (
            <div>
              <div className="flex items-center gap-2 mb-3">
                <FileText className="w-5 h-5 text-purple-500" />
                <h2 className="text-lg font-semibold text-gray-900">提示词配置</h2>
                {promptFile?.path && (
                  <span className="text-sm text-gray-400 font-mono">{promptFile.path}</span>
                )}
              </div>
              {promptFile?.exists && promptFile.content ? (
                <PromptYamlViewer
                  content={promptFile.content}
                  filename={promptFile.name}
                  editable={true}
                  onSave={handleSavePrompt}
                  saving={saving}
                />
              ) : (
                <Card>
                  <CardContent className="py-12">
                    <Empty
                      icon={FileText}
                      title="提示词文件不存在"
                      description={promptFile?.path ? `路径: ${promptFile.path}` : '未找到关联的提示词文件'}
                    />
                  </CardContent>
                </Card>
              )}
            </div>
          )}
          
          {activeTab === 'code' && (
            <div>
              <div className="flex items-center gap-2 mb-3">
                <Code className="w-5 h-5 text-blue-500" />
                <h2 className="text-lg font-semibold text-gray-900">Agent 代码</h2>
                {codeFile?.path && (
                  <span className="text-sm text-gray-400 font-mono">{codeFile.path}</span>
                )}
              </div>
              {codeFile?.exists && codeFile.content ? (
                <PythonCodeViewer
                  content={codeFile.content}
                  filename={codeFile.name}
                  editable={true}
                  onSave={handleSaveCode}
                  saving={saving}
                  maxHeight="650px"
                />
              ) : (
                <Card>
                  <CardContent className="py-12">
                    <Empty
                      icon={Code}
                      title="代码文件不存在"
                      description={codeFile?.path ? `路径: ${codeFile.path}` : '未找到关联的代码文件'}
                    />
                  </CardContent>
                </Card>
              )}
            </div>
          )}
          
          {activeTab === 'tools' && (
            <div>
              <div className="flex items-center gap-2 mb-3">
                <Wrench className="w-5 h-5 text-amber-500" />
                <h2 className="text-lg font-semibold text-gray-900">工具文件</h2>
                <Badge variant="outline" size="sm">{toolFiles.length} 个文件</Badge>
              </div>
              {toolFilesForViewer.length > 0 ? (
                <ToolCodeViewer
                  files={toolFilesForViewer}
                  editable={true}
                  onSave={handleSaveTool}
                  saving={saving}
                />
              ) : (
                <Card>
                  <CardContent className="py-12">
                    <Empty
                      icon={FolderOpen}
                      title="没有工具文件"
                      description="该 Agent 没有关联的工具文件"
                    />
                  </CardContent>
                </Card>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// 文件概览卡片组件
function FileOverviewCard({
  icon: Icon,
  iconColor,
  iconBg,
  title,
  subtitle,
  status,
  active,
  onClick,
}: {
  icon: React.ElementType;
  iconColor: string;
  iconBg: string;
  title: string;
  subtitle: string;
  status: 'available' | 'missing' | 'empty';
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={`p-4 rounded-xl border-2 text-left transition-all ${
        active
          ? 'border-primary-500 bg-primary-50/50 shadow-sm'
          : 'border-gray-100 bg-white hover:border-gray-200 hover:shadow-sm'
      }`}
    >
      <div className="flex items-start gap-3">
        <div className={`w-10 h-10 rounded-lg ${iconBg} flex items-center justify-center flex-shrink-0`}>
          <Icon className={`w-5 h-5 ${iconColor}`} />
        </div>
        <div className="min-w-0 flex-1">
          <div className="font-medium text-gray-900">{title}</div>
          <div className="text-sm text-gray-500 truncate">{subtitle}</div>
          <div className="mt-1">
            {status === 'available' && (
              <span className="inline-flex items-center gap-1 text-xs text-green-600">
                <CheckCircle2 className="w-3 h-3" />
                可用
              </span>
            )}
            {status === 'missing' && (
              <span className="inline-flex items-center gap-1 text-xs text-red-500">
                <AlertCircle className="w-3 h-3" />
                不存在
              </span>
            )}
            {status === 'empty' && (
              <span className="inline-flex items-center gap-1 text-xs text-gray-400">
                <FolderOpen className="w-3 h-3" />
                空
              </span>
            )}
          </div>
        </div>
      </div>
    </button>
  );
}
