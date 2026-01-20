'use client';

import { useState } from 'react';
import Link from 'next/link';
import { Header } from '@/components/layout';
import { Card, CardHeader, CardTitle, CardContent, Button, Progress, Empty } from '@/components/ui';
import { StatusBadge } from '@/components/status-badge';
import { MessageContent } from '@components/viewer';
import { 
  useBuildDashboardV2, 
  useControlProjectV2, 
  useDeleteProjectV2,
  useWorkflowReportV2,
  useStageDocumentV2,
} from '@/hooks/use-projects-v2';
import { formatDuration, formatNumber } from '@/lib/utils';
import { toast } from 'sonner';
import {
  ArrowLeft,
  FolderKanban,
  Play,
  Pause,
  RotateCcw,
  Trash2,
  CheckCircle2,
  XCircle,
  Clock,
  Zap,
  FileText,
  AlertTriangle,
  Loader2,
  ChevronDown,
  ChevronRight,
  Eye,
  X,
  BarChart3,
  Network,
  List,
} from 'lucide-react';
import dynamic from 'next/dynamic';
import { extractGraphData } from '@/components/knowledge-graph';

// 动态导入知识图谱组件
const KnowledgeGraph = dynamic(() => import('@/components/knowledge-graph').then(mod => mod.KnowledgeGraph), { 
  ssr: false,
  loading: () => <div className="flex items-center justify-center py-12"><Loader2 className="w-8 h-8 animate-spin text-primary-600" /></div>
});

interface PageProps {
  params: { id: string };
}

export default function ProjectDetailPage({ params }: PageProps) {
  const { id } = params;
  const { data: dashboard, isLoading, refetch } = useBuildDashboardV2(id);
  const { data: workflowReport } = useWorkflowReportV2(id);
  const controlProject = useControlProjectV2();
  const deleteProject = useDeleteProjectV2();
  
  const [selectedStage, setSelectedStage] = useState<string | null>(null);
  const [showWorkflowReport, setShowWorkflowReport] = useState(false);

  const handleControl = async (action: 'pause' | 'resume' | 'stop' | 'restart' | 'cancel') => {
    try {
      await controlProject.mutateAsync({ projectId: id, request: { action } });
      toast.success(`操作成功: ${action}`);
      refetch();
    } catch (error: any) {
      toast.error(`操作失败: ${error.message}`);
    }
  };

  const handleDelete = async () => {
    if (!confirm('确定要删除此项目吗？此操作不可撤销。')) return;
    try {
      await deleteProject.mutateAsync(id);
      toast.success('项目已删除');
      window.location.href = '/projects';
    } catch (error: any) {
      toast.error(`删除失败: ${error.message}`);
    }
  };

  if (isLoading) {
    return (
      <div className="page-container">
        <Header title="加载中..." />
        <div className="page-content">
          <div className="animate-pulse space-y-6">
            <div className="h-32 bg-gray-100 rounded-xl" />
            <div className="h-64 bg-gray-100 rounded-xl" />
          </div>
        </div>
      </div>
    );
  }

  if (!dashboard) {
    return (
      <div className="page-container">
        <Header title="项目详情" />
        <div className="page-content">
          <Empty
            icon={FolderKanban}
            title="项目不存在"
            description="该项目可能已被删除"
            action={
              <Link href="/projects">
                <Button variant="outline">
                  <ArrowLeft className="w-4 h-4" />
                  返回列表
                </Button>
              </Link>
            }
          />
        </div>
      </div>
    );
  }

  const isBuilding = dashboard.status === 'building' || dashboard.status === 'pending' || dashboard.status === 'queued';
  const isPaused = dashboard.status === 'paused';
  const isCompleted = dashboard.status === 'completed';
  const isFailed = dashboard.status === 'failed';

  return (
    <div className="page-container">
      <Header
        title={dashboard.project_name || '项目详情'}
        actions={
          <div className="flex items-center gap-3">
            <Link href="/projects">
              <Button variant="ghost">
                <ArrowLeft className="w-4 h-4" />
                返回
              </Button>
            </Link>
            {workflowReport?.exists && (
              <Button variant="outline" onClick={() => setShowWorkflowReport(true)}>
                <BarChart3 className="w-4 h-4" />
                查看报告
              </Button>
            )}
            {isBuilding && (
              <Button variant="outline" onClick={() => handleControl('pause')}>
                <Pause className="w-4 h-4" />
                暂停
              </Button>
            )}
            {isPaused && (
              <Button onClick={() => handleControl('resume')}>
                <Play className="w-4 h-4" />
                继续
              </Button>
            )}
            {(isCompleted || isFailed) && (
              <Button variant="outline" onClick={() => handleControl('restart')}>
                <RotateCcw className="w-4 h-4" />
                重新构建
              </Button>
            )}
            <Button variant="danger" onClick={handleDelete}>
              <Trash2 className="w-4 h-4" />
              删除
            </Button>
          </div>
        }
      />

      <div className="page-content">
        <Card className="mb-6">
          <div className="flex items-start gap-6">
            <div className="w-16 h-16 rounded-2xl bg-primary-50 flex items-center justify-center flex-shrink-0">
              <FolderKanban className="w-8 h-8 text-primary-600" />
            </div>
            <div className="flex-1">
              <div className="flex items-center gap-3 mb-2">
                <h1 className="text-xl font-bold text-gray-900">
                  {dashboard.project_name || dashboard.project_id}
                </h1>
                <StatusBadge status={dashboard.status as any} />
              </div>
              {dashboard.requirement && (
                <p className="text-gray-600 mb-4 line-clamp-2">{dashboard.requirement}</p>
              )}
              <div className="flex items-center gap-6">
                <div className="flex-1 max-w-md">
                  <div className="flex items-center justify-between text-sm mb-1">
                    <span className="text-gray-500">构建进度</span>
                    <span className="font-medium">{Math.round(dashboard.progress)}%</span>
                  </div>
                  <Progress
                    value={dashboard.progress}
                    variant={isFailed ? 'error' : isCompleted ? 'success' : 'default'}
                    size="lg"
                  />
                </div>
                <div className="text-sm text-gray-500">
                  {dashboard.completed_stages} / {dashboard.total_stages} 阶段完成
                </div>
              </div>
            </div>
          </div>
        </Card>

        {dashboard.metrics && (
          <div className="grid gap-4 grid-cols-2 sm:grid-cols-4 mb-6">
            <MetricCard icon={Clock} label="总耗时" value={formatDuration(dashboard.metrics.total_duration_seconds)} color="blue" />
            <MetricCard icon={FileText} label="输入 Tokens" value={formatNumber(dashboard.metrics.input_tokens)} color="purple" />
            <MetricCard icon={Zap} label="输出 Tokens" value={formatNumber(dashboard.metrics.output_tokens)} color="amber" />
            <MetricCard icon={Zap} label="工具调用" value={formatNumber(dashboard.metrics.tool_calls)} color="green" />
          </div>
        )}

        {dashboard.error_info && (
          <Card className="mb-6 border-red-200 bg-red-50">
            <div className="flex items-start gap-3">
              <AlertTriangle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
              <div>
                <h3 className="font-medium text-red-900 mb-1">构建错误</h3>
                <p className="text-sm text-red-700">
                  {typeof dashboard.error_info === 'string' ? dashboard.error_info : JSON.stringify(dashboard.error_info)}
                </p>
              </div>
            </div>
          </Card>
        )}

        <Card>
          <CardHeader><CardTitle>构建阶段</CardTitle></CardHeader>
          <CardContent>
            <div className="space-y-4">
              {dashboard.stages.map((stage, index) => (
                <StageItem 
                  key={stage.name} 
                  stage={stage} 
                  index={index}
                  isSelected={selectedStage === stage.name}
                  onSelect={() => setSelectedStage(selectedStage === stage.name ? null : stage.name)}
                />
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {showWorkflowReport && workflowReport?.content && (
        <WorkflowReportModal content={workflowReport.content} onClose={() => setShowWorkflowReport(false)} />
      )}

      {selectedStage && (
        <StageDocumentModal projectId={id} stageName={selectedStage} onClose={() => setSelectedStage(null)} />
      )}
    </div>
  );
}

function MetricCard({ icon: Icon, label, value, color }: { icon: React.ElementType; label: string; value: string; color: 'blue' | 'purple' | 'amber' | 'green' }) {
  const colors = { blue: 'bg-blue-50 text-blue-600', purple: 'bg-purple-50 text-purple-600', amber: 'bg-amber-50 text-amber-600', green: 'bg-green-50 text-green-600' };
  return (
    <Card padding="sm">
      <div className="flex items-center gap-3">
        <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${colors[color]}`}><Icon className="w-5 h-5" /></div>
        <div><div className="text-lg font-bold text-gray-900">{value}</div><div className="text-xs text-gray-500">{label}</div></div>
      </div>
    </Card>
  );
}

interface StageItemProps {
  stage: { name: string; display_name: string; order: number; status: string; started_at?: string; completed_at?: string; duration_seconds?: number; error?: string; input_tokens?: number; output_tokens?: number };
  index: number; isSelected: boolean; onSelect: () => void;
}

function StageItem({ stage, index, isSelected, onSelect }: StageItemProps) {
  const isCompleted = stage.status === 'completed';
  const isRunning = stage.status === 'running';
  const isFailed = stage.status === 'failed';

  return (
    <div className={`rounded-lg border transition-all ${isRunning ? 'border-primary-200 bg-primary-50' : isFailed ? 'border-red-200 bg-red-50' : isCompleted ? 'border-green-100 bg-green-50' : 'border-gray-100 bg-gray-50'}`}>
      <div className="flex items-start gap-4 p-4 cursor-pointer" onClick={isCompleted ? onSelect : undefined}>
        <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${isCompleted ? 'bg-green-500 text-white' : isRunning ? 'bg-primary-500 text-white' : isFailed ? 'bg-red-500 text-white' : 'bg-gray-300 text-gray-600'}`}>
          {isCompleted ? <CheckCircle2 className="w-5 h-5" /> : isRunning ? <Loader2 className="w-5 h-5 animate-spin" /> : isFailed ? <XCircle className="w-5 h-5" /> : <span className="text-sm font-medium">{index + 1}</span>}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between mb-1">
            <div className="flex items-center gap-2">
              <h4 className={`font-medium ${isRunning ? 'text-primary-900' : isFailed ? 'text-red-900' : isCompleted ? 'text-green-900' : 'text-gray-600'}`}>{stage.display_name || stage.name}</h4>
              {isCompleted && <button className="text-xs text-primary-600 hover:text-primary-700 flex items-center gap-1" onClick={(e) => { e.stopPropagation(); onSelect(); }}><Eye className="w-3 h-3" />查看文档</button>}
            </div>
            <StatusBadge status={stage.status as any} size="sm" />
          </div>
          <div className="flex items-center gap-4 text-sm text-gray-500">
            {stage.duration_seconds && <span className="flex items-center gap-1"><Clock className="w-3.5 h-3.5" />{formatDuration(stage.duration_seconds)}</span>}
            {(stage.input_tokens || stage.output_tokens) && <span>{formatNumber(stage.input_tokens)} / {formatNumber(stage.output_tokens)} tokens</span>}
          </div>
          {stage.error && <p className="text-sm text-red-600 mt-2">{stage.error}</p>}
        </div>
        {isCompleted && <div className="text-gray-400">{isSelected ? <ChevronDown className="w-5 h-5" /> : <ChevronRight className="w-5 h-5" />}</div>}
      </div>
    </div>
  );
}

function WorkflowReportModal({ content, onClose }: { content: string; onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-4xl max-h-[90vh] flex flex-col">
        <div className="flex items-center justify-between p-4 border-b">
          <h2 className="text-lg font-semibold flex items-center gap-2"><BarChart3 className="w-5 h-5 text-primary-600" />工作流执行报告</h2>
          <button onClick={onClose} className="p-2 hover:bg-gray-100 rounded-lg"><X className="w-5 h-5" /></button>
        </div>
        <div className="flex-1 overflow-auto p-6">
          <MessageContent content={content} variant="assistant" />
        </div>
      </div>
    </div>
  );
}

function StageDocumentModal({ projectId, stageName, onClose }: { projectId: string; stageName: string; onClose: () => void }) {
  const { data: stageDoc, isLoading } = useStageDocumentV2(projectId, stageName);
  const [viewMode, setViewMode] = useState<'text' | 'graph'>('text');
  
  // 获取阶段显示名称（支持两种命名格式）
  const stageDisplayNames: Record<string, string> = {
    requirements_analyzer: '需求分析',
    requirements_analysis: '需求分析',
    system_architect: '系统架构',
    system_architecture: '系统架构',
    agent_designer: 'Agent设计',
    agent_design: 'Agent设计',
    prompt_engineer: 'Prompt工程',
    agent_code_developer: '代码开发',
    agent_developer_manager: '开发管理',
    tools_developer: '工具开发',
    orchestrator: '工作流编排',
    agent_deployer: 'Agent部署',
  };
  
  // 支持知识图谱可视化的阶段（支持两种命名格式）
  const graphSupportedStages = [
    'requirements_analyzer', 'requirements_analysis',
    'system_architect', 'system_architecture',
    'agent_designer', 'agent_design',
    'prompt_engineer',
    'tools_developer',
    'agent_code_developer',
    'agent_developer_manager'
  ];
  const supportsGraph = graphSupportedStages.includes(stageName);
  
  // 提取图数据
  const graphData = stageDoc?.parsed_content && supportsGraph 
    ? extractGraphData(stageName, stageDoc.parsed_content) 
    : { nodes: [], links: [] };
  
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-5xl max-h-[90vh] flex flex-col">
        <div className="flex items-center justify-between p-4 border-b">
          <h2 className="text-lg font-semibold flex items-center gap-2">
            <FileText className="w-5 h-5 text-primary-600" />
            阶段文档: {stageDisplayNames[stageName] || stageName}
          </h2>
          <div className="flex items-center gap-2">
            {/* 视图切换按钮 */}
            {supportsGraph && stageDoc?.parsed_content && (
              <div className="flex items-center bg-gray-100 rounded-lg p-1">
                <button
                  onClick={() => setViewMode('text')}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                    viewMode === 'text' 
                      ? 'bg-white text-primary-600 shadow-sm' 
                      : 'text-gray-600 hover:text-gray-900'
                  }`}
                >
                  <List className="w-4 h-4" />
                  文本
                </button>
                <button
                  onClick={() => setViewMode('graph')}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                    viewMode === 'graph' 
                      ? 'bg-white text-primary-600 shadow-sm' 
                      : 'text-gray-600 hover:text-gray-900'
                  }`}
                >
                  <Network className="w-4 h-4" />
                  知识图谱
                </button>
              </div>
            )}
            <button onClick={onClose} className="p-2 hover:bg-gray-100 rounded-lg">
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>
        <div className="flex-1 overflow-auto p-6">
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-8 h-8 animate-spin text-primary-600" />
            </div>
          ) : stageDoc?.exists && stageDoc.parsed_content ? (
            viewMode === 'graph' && supportsGraph ? (
              <div className="flex flex-col items-center">
                <div className="w-full border rounded-lg overflow-hidden bg-gray-50">
                  <KnowledgeGraph data={graphData} width={900} height={550} />
                </div>
                <p className="text-xs text-gray-500 mt-3">
                  提示：拖拽节点可调整位置，滚轮缩放，悬停查看详情
                </p>
              </div>
            ) : (
              <EnhancedJsonViewer data={stageDoc.parsed_content} stageName={stageName} />
            )
          ) : stageDoc?.exists && stageDoc.content ? (
            <pre className="text-sm bg-gray-50 p-4 rounded-lg overflow-auto">{stageDoc.content}</pre>
          ) : (
            <div className="text-center py-12 text-gray-500">暂无该阶段的设计文档</div>
          )}
        </div>
      </div>
    </div>
  );
}

function JsonViewer({ data, depth = 0 }: { data: unknown; depth?: number }) {
  if (data === null || data === undefined) return <span className="text-gray-400">null</span>;
  if (typeof data === 'string') {
    if (data.length > 200) return <div className="bg-gray-50 p-3 rounded-lg text-sm whitespace-pre-wrap">{data}</div>;
    return <span className="text-green-600">&quot;{data}&quot;</span>;
  }
  if (typeof data === 'number' || typeof data === 'boolean') return <span className="text-blue-600">{String(data)}</span>;
  if (Array.isArray(data)) {
    if (data.length === 0) return <span className="text-gray-400">[]</span>;
    return <div className="space-y-2">{data.map((item, index) => <div key={index} className="flex gap-2"><span className="text-gray-400 text-sm">{index}:</span><div className="flex-1"><JsonViewer data={item} depth={depth + 1} /></div></div>)}</div>;
  }
  if (typeof data === 'object') {
    const entries = Object.entries(data);
    if (entries.length === 0) return <span className="text-gray-400">{'{}'}</span>;
    return <div className="space-y-3">{entries.map(([key, value]) => <div key={key} className={depth === 0 ? 'bg-gray-50 p-4 rounded-lg' : ''}><div className="font-medium text-gray-700 mb-1">{key}</div><div className="pl-4"><JsonViewer data={value} depth={depth + 1} /></div></div>)}</div>;
  }
  return <span>{String(data)}</span>;
}

// 增强版 JSON 查看器，针对不同阶段文档优化显示
function EnhancedJsonViewer({ data, stageName }: { data: any; stageName: string }) {
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set(['root']));
  
  const toggleSection = (key: string) => {
    const newExpanded = new Set(expandedSections);
    if (newExpanded.has(key)) {
      newExpanded.delete(key);
    } else {
      newExpanded.add(key);
    }
    setExpandedSections(newExpanded);
  };
  
  // 如果数据只包含 raw_content，尝试从中提取 JSON
  let processedData = data;
  if (data && data.raw_content && Object.keys(data).length === 1) {
    const extracted = tryExtractJsonFromRawContentLocal(data.raw_content);
    if (extracted) {
      processedData = extracted;
    }
  }
  
  // 根据阶段类型获取主要内容
  const getMainContent = () => {
    switch (stageName) {
      case 'requirements_analyzer':
      case 'requirements_analysis':
        return processedData.requirements_document;
      case 'system_architect':
      case 'system_architecture':
        return processedData.system_design;
      case 'agent_designer':
      case 'agent_design':
        return processedData.agent_design;
      case 'prompt_engineer':
        // 支持两种键名：prompt_design 和 prompt_engineering
        return processedData.prompt_design || processedData.prompt_engineering;
      case 'tools_developer':
        return processedData.tool_development;
      case 'agent_code_developer':
        return processedData.agent_code_development;
      case 'agent_developer_manager':
        // 支持 agent_developer_manager 阶段
        return processedData.agent_developer_manager;
      default:
        return processedData;
    }
  };
  
  const mainContent = getMainContent();
  
  // 如果仍然只有 raw_content，显示原始内容
  if (!mainContent && processedData?.raw_content) {
    return (
      <div className="bg-gray-50 p-4 rounded-lg">
        <div className="text-sm text-gray-500 mb-2">原始输出内容：</div>
        <pre className="text-sm whitespace-pre-wrap overflow-auto max-h-96">{processedData.raw_content}</pre>
      </div>
    );
  }
  
  if (!mainContent) return <JsonViewer data={processedData} />;
  
  return (
    <div className="space-y-4">
      {Object.entries(mainContent).map(([key, value]) => (
        <SectionCard 
          key={key} 
          title={formatSectionTitle(key)} 
          data={value}
          isExpanded={expandedSections.has(key)}
          onToggle={() => toggleSection(key)}
        />
      ))}
    </div>
  );
}

// 本地版本的 JSON 提取函数
function tryExtractJsonFromRawContentLocal(rawContent: string): any {
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

function SectionCard({ title, data, isExpanded, onToggle }: { 
  title: string; 
  data: any; 
  isExpanded: boolean;
  onToggle: () => void;
}) {
  const isSimpleValue = typeof data === 'string' || typeof data === 'number' || typeof data === 'boolean';
  const isArray = Array.isArray(data);
  const isEmpty = data === null || data === undefined || (isArray && data.length === 0) || (typeof data === 'object' && Object.keys(data).length === 0);
  
  if (isEmpty) return null;
  
  return (
    <div className="border rounded-lg overflow-hidden">
      <button
        onClick={onToggle}
        className="w-full flex items-center justify-between p-4 bg-gray-50 hover:bg-gray-100 transition-colors text-left"
      >
        <div className="flex items-center gap-2">
          {isExpanded ? <ChevronDown className="w-4 h-4 text-gray-500" /> : <ChevronRight className="w-4 h-4 text-gray-500" />}
          <span className="font-medium text-gray-900">{title}</span>
          {isArray && <span className="text-xs text-gray-500 bg-gray-200 px-2 py-0.5 rounded-full">{data.length} 项</span>}
        </div>
      </button>
      
      {isExpanded && (
        <div className="p-4 bg-white">
          {isSimpleValue ? (
            <p className="text-gray-700 whitespace-pre-wrap">{String(data)}</p>
          ) : isArray ? (
            <div className="space-y-3">
              {data.map((item: any, index: number) => (
                <ArrayItemCard key={index} item={item} index={index} />
              ))}
            </div>
          ) : (
            <div className="space-y-3">
              {Object.entries(data).map(([key, value]) => (
                <div key={key} className="border-l-2 border-primary-200 pl-4">
                  <div className="text-sm font-medium text-gray-600 mb-1">{formatSectionTitle(key)}</div>
                  <div className="text-gray-800">
                    {typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean' ? (
                      <span className="whitespace-pre-wrap">{String(value)}</span>
                    ) : Array.isArray(value) ? (
                      <ul className="list-disc list-inside space-y-1">
                        {value.slice(0, 10).map((v: any, i: number) => (
                          <li key={i} className="text-sm">
                            {typeof v === 'string' ? v : JSON.stringify(v)}
                          </li>
                        ))}
                        {value.length > 10 && <li className="text-gray-500 text-sm">...还有 {value.length - 10} 项</li>}
                      </ul>
                    ) : (
                      <JsonViewer data={value} depth={1} />
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function ArrayItemCard({ item, index }: { item: any; index: number }) {
  const [isExpanded, setIsExpanded] = useState(index < 3);
  
  if (typeof item === 'string') {
    return (
      <div className="flex gap-2 items-start">
        <span className="text-xs text-gray-400 mt-1">{index + 1}.</span>
        <span className="text-gray-700">{item}</span>
      </div>
    );
  }
  
  // 安全获取标题，确保返回字符串
  const getStringValue = (val: any): string | null => {
    if (val === null || val === undefined) return null;
    if (typeof val === 'string') return val;
    if (typeof val === 'number' || typeof val === 'boolean') return String(val);
    if (typeof val === 'object') {
      // 如果是对象，尝试获取其 label 或 name 属性
      if (val.label) return String(val.label);
      if (val.name) return String(val.name);
      return null;
    }
    return null;
  };
  
  const title = getStringValue(item.title) || getStringValue(item.name) || getStringValue(item.id) || getStringValue(item.scenario) || getStringValue(item.label) || `项目 ${index + 1}`;
  const description = getStringValue(item.description) || getStringValue(item.user_story) || getStringValue(item.purpose) || getStringValue(item.rationale);
  
  return (
    <div className="border rounded-lg overflow-hidden bg-gray-50">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between p-3 hover:bg-gray-100 transition-colors text-left"
      >
        <div className="flex items-center gap-2">
          {isExpanded ? <ChevronDown className="w-3 h-3 text-gray-400" /> : <ChevronRight className="w-3 h-3 text-gray-400" />}
          <span className="text-sm font-medium text-gray-800">{title}</span>
          {item.priority && (
            <span className={`text-xs px-2 py-0.5 rounded-full ${
              item.priority === 'High' ? 'bg-red-100 text-red-700' :
              item.priority === 'Medium' ? 'bg-yellow-100 text-yellow-700' :
              'bg-green-100 text-green-700'
            }`}>
              {item.priority}
            </span>
          )}
        </div>
      </button>
      
      {isExpanded && (
        <div className="p-3 pt-0 space-y-2">
          {description && (
            <p className="text-sm text-gray-600 bg-white p-2 rounded">{description}</p>
          )}
          {Object.entries(item).filter(([key]) => !['title', 'name', 'id', 'description', 'user_story', 'purpose', 'rationale', 'priority', 'scenario', 'label', 'level', 'parent_id', 'children', 'content'].includes(key)).map(([key, value]) => (
            <div key={key} className="text-sm">
              <span className="text-gray-500">{formatSectionTitle(key)}: </span>
              <span className="text-gray-700">
                {Array.isArray(value) 
                  ? value.map(v => typeof v === 'object' ? JSON.stringify(v) : String(v)).join(', ') 
                  : typeof value === 'object' && value !== null
                    ? JSON.stringify(value)
                    : String(value)}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function formatSectionTitle(key: string): string {
  const titleMap: Record<string, string> = {
    feature_name: '功能名称',
    version: '版本',
    date: '日期',
    overview: '概述',
    business_value: '业务价值',
    workflow_complexity: '工作流复杂度',
    recommended_agent_type: '推荐Agent类型',
    scope: '范围',
    included: '包含',
    excluded: '排除',
    functional_requirements: '功能需求',
    non_functional_requirements: '非功能需求',
    constraints: '约束条件',
    assumptions: '假设',
    success_criteria: '成功标准',
    glossary: '术语表',
    analysis_notes: '分析备注',
    design_overview: '设计概述',
    project_name: '项目名称',
    design_scope: '设计范围',
    design_principles: '设计原则',
    key_decisions: '关键决策',
    workflow_type: '工作流类型',
    recommended_templates: '推荐模板',
    architecture: '架构',
    system_context: '系统上下文',
    agent_topology: 'Agent拓扑',
    interaction_model: '交互模型',
    technology_stack: '技术栈',
    agents: 'Agents',
    data_models: '数据模型',
    interaction_flows: '交互流程',
    security_considerations: '安全考虑',
    error_handling: '错误处理',
    performance_considerations: '性能考虑',
    monitoring_strategy: '监控策略',
    design_rationale: '设计理由',
    design_goals: '设计目标',
    key_design_decisions: '关键设计决策',
    agent_relationships: 'Agent关系',
    system_integration: '系统集成',
    prompt_structure: 'Prompt结构',
    role_definition: '角色定义',
    core_responsibilities: '核心职责',
    professional_skills: '专业技能',
    workflow_steps: '工作流步骤',
    quotation_structure: '报价结构',
    tools_integration: '工具集成',
    sales_thinking_guide: '销售思维指南',
    design_considerations: '设计考虑',
    testing_scenarios: '测试场景',
    prompt_template_evaluation: 'Prompt模板评估',
    strengths: '优势',
    limitations: '限制',
    future_improvements: '未来改进',
  };
  
  return titleMap[key] || key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
}
