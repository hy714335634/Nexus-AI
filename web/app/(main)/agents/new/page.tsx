'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { Header } from '@/components/layout';
import { Card, CardHeader, CardTitle, CardContent, Button, Input, Textarea } from '@/components/ui';
import { useCreateProjectV2 } from '@/hooks/use-projects-v2';
import { toast } from 'sonner';
import {
  ArrowLeft,
  Sparkles,
  Lightbulb,
  FileText,
  Database,
  Globe,
  Code,
  MessageSquare,
  Bot,
  Brain,
  Target,
} from 'lucide-react';

const templates = [
  {
    id: 'data-analyzer',
    name: '数据分析 Agent',
    description: '分析数据、生成报告和可视化图表',
    icon: Database,
    prompt: '创建一个数据分析 Agent，能够读取CSV/Excel文件，进行数据清洗、统计分析，并生成可视化图表和分析报告。',
  },
  {
    id: 'content-generator',
    name: '内容创作 Agent',
    description: '生成文章、文案和营销内容',
    icon: FileText,
    prompt: '创建一个内容创作 Agent，能够根据主题和关键词生成高质量的文章、营销文案和社交媒体内容。',
  },
  {
    id: 'web-researcher',
    name: '市场调研 Agent',
    description: '搜索和整理网络信息',
    icon: Globe,
    prompt: '创建一个市场调研 Agent，能够搜索互联网获取最新信息，整理和总结研究结果，生成研究报告。',
  },
  {
    id: 'code-assistant',
    name: '技术开发 Agent',
    description: '编写、审查和优化代码',
    icon: Code,
    prompt: '创建一个技术开发 Agent，能够编写代码、进行代码审查、提供优化建议，支持多种编程语言。',
  },
];

export default function NewAgentPage() {
  const router = useRouter();
  const [requirement, setRequirement] = useState('');
  const [projectName, setProjectName] = useState('');
  const [selectedTemplate, setSelectedTemplate] = useState<string | null>(null);

  const createProject = useCreateProjectV2({
    onSuccess: (data) => {
      toast.success('项目创建成功，开始构建 Agent');
      router.push(`/projects/${data.project_id}`);
    },
    onError: (error) => {
      toast.error(`创建失败: ${error.message}`);
    },
  });

  const handleTemplateSelect = (template: typeof templates[0]) => {
    setSelectedTemplate(template.id);
    setRequirement(template.prompt);
    setProjectName(template.name);
  };

  const handleSubmit = () => {
    if (!requirement.trim()) {
      toast.error('请输入需求描述');
      return;
    }

    // 如果用户指定了项目名称，将其拼接到需求描述中，约束 Agent 使用此名称
    let finalRequirement = requirement.trim();
    const trimmedProjectName = projectName.trim();
    
    if (trimmedProjectName) {
      finalRequirement = `[项目名称约束: ${trimmedProjectName}] 请务必使用 "${trimmedProjectName}" 作为项目名称（project_name），不要自行生成其他名称。\n\n${finalRequirement}`;
    }

    createProject.mutate({
      requirement: finalRequirement,
      project_name: trimmedProjectName || undefined,
    });
  };

  return (
    <div className="page-container">
      <Header
        title="创建 Agent"
        description="用自然语言描述业务需求，AI 将自动构建专属 Agent"
        actions={
          <Link href="/agents">
            <Button variant="ghost">
              <ArrowLeft className="w-4 h-4" />
              返回列表
            </Button>
          </Link>
        }
      />

      <div className="page-content max-w-4xl mx-auto">
        {/* Hero Section */}
        <div className="mb-8 p-6 rounded-2xl bg-gradient-to-br from-primary-50 via-accent-50 to-agent-50 border border-primary-100">
          <div className="flex items-start gap-4">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-primary-500 to-accent-600 flex items-center justify-center">
              <Brain className="w-6 h-6 text-white" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-gray-900 mb-1">从想法到 Agent 自动化构建</h2>
              <p className="text-gray-600 text-sm">
                无需编程，只需描述业务场景和需求，系统将自动设计、开发并部署您的专属 Agent。
                业务人员也能轻松创建智能助手，实现业务流程自动化。
              </p>
            </div>
          </div>
        </div>

        {/* Templates */}
        <div className="mb-8">
          <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <Lightbulb className="w-5 h-5 text-agent-500" />
            快速开始 - 选择 Agent 模板
          </h2>
          <div className="grid gap-4 grid-cols-1 sm:grid-cols-2">
            {templates.map((template) => (
              <button
                key={template.id}
                onClick={() => handleTemplateSelect(template)}
                className={`text-left p-4 rounded-xl border-2 transition-all ${
                  selectedTemplate === template.id
                    ? 'border-primary-500 bg-gradient-to-br from-primary-50 to-accent-50'
                    : 'border-gray-200 hover:border-primary-200 bg-white hover:bg-gray-50'
                }`}
              >
                <div className="flex items-start gap-3">
                  <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                    selectedTemplate === template.id
                      ? 'bg-gradient-to-br from-primary-500 to-accent-500 text-white'
                      : 'bg-gray-100 text-gray-600'
                  }`}>
                    <template.icon className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="font-medium text-gray-900">{template.name}</h3>
                    <p className="text-sm text-gray-500 mt-0.5">{template.description}</p>
                  </div>
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Requirement Input */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Target className="w-5 h-5 text-primary-600" />
              业务需求描述
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Agent 名称 <span className="text-gray-400">(可选)</span>
              </label>
              <Input
                placeholder="例如：客服 Agent、数据分析 Agent、内容编辑 Agent..."
                value={projectName}
                onChange={(e) => setProjectName(e.target.value)}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                详细业务需求 <span className="text-red-500">*</span>
              </label>
              <Textarea
                placeholder="请详细描述您希望 Agent 具备的能力和工作职责...&#10;&#10;例如：&#10;- 能够读取和分析销售数据&#10;- 自动生成周报和月报&#10;- 识别异常数据并预警&#10;- 支持自然语言查询"
                value={requirement}
                onChange={(e) => setRequirement(e.target.value)}
                rows={8}
              />
              <p className="text-xs text-gray-500 mt-2">
                提示：描述越详细，构建的 Agent 越符合您的业务需求
              </p>
            </div>

            <div className="flex items-center justify-between pt-4 border-t border-gray-100">
              <div className="text-sm text-gray-500">
                {requirement.length} 字符
                {requirement.length < 10 && requirement.length > 0 && (
                  <span className="text-amber-600 ml-2">建议至少 10 个字符</span>
                )}
              </div>
              <Button
                onClick={handleSubmit}
                disabled={!requirement.trim() || requirement.length < 10}
                loading={createProject.isPending}
                className="bg-gradient-to-r from-primary-600 to-accent-600 hover:from-primary-700 hover:to-accent-700"
              >
                <Sparkles className="w-4 h-4" />
                开始构建
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Tips */}
        <div className="mt-6 p-4 bg-gradient-to-r from-primary-50 to-accent-50 rounded-xl border border-primary-100">
          <h3 className="font-medium text-primary-900 mb-2 flex items-center gap-2">
            <MessageSquare className="w-4 h-4" />
            构建提示
          </h3>
          <ul className="text-sm text-primary-800 space-y-1">
            <li>• 明确说明 Agent 的主要职责和工作场景</li>
            <li>• 列出需要处理的具体业务任务</li>
            <li>• 说明需要对接的数据源或系统</li>
            <li>• 描述期望的输入输出格式和交互方式</li>
          </ul>
        </div>
      </div>
    </div>
  );
}
