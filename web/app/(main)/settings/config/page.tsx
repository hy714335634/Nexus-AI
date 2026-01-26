'use client';

import { useState, useEffect, useCallback } from 'react';
// @ts-ignore - js-yaml types
import yaml from 'js-yaml';
import { Header } from '@/components/layout';
import { Card, Button, Badge, Empty } from '@/components/ui';
import {
  useConfigFilesV2,
  useConfigFileV2,
  useUpdateConfigV2,
  useValidateConfigV2,
  useRestoreConfigV2,
  type ConfigFile,
} from '@/hooks/use-config-v2';
import { formatRelativeTime } from '@/lib/utils';
import { toast } from 'sonner';
import {
  Settings,
  FileText,
  Save,
  RotateCcw,
  Check,
  X,
  AlertCircle,
  RefreshCw,
  Code,
  Eye,
  ChevronRight,
  ChevronDown,
} from 'lucide-react';

type ViewMode = 'visual' | 'text';

export default function ConfigPage() {
  const { data: configFiles, isLoading, refetch } = useConfigFilesV2();
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [editContent, setEditContent] = useState<string>('');
  const [hasChanges, setHasChanges] = useState(false);
  const [validationStatus, setValidationStatus] = useState<'idle' | 'valid' | 'invalid'>('idle');
  const [validationError, setValidationError] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<ViewMode>('visual');

  const { data: fileContent, isLoading: isLoadingContent } = useConfigFileV2(selectedFile || '');
  const updateConfig = useUpdateConfigV2();
  const validateConfig = useValidateConfigV2();
  const restoreConfig = useRestoreConfigV2();

  useEffect(() => {
    if (fileContent?.raw_content) {
      setEditContent(fileContent.raw_content);
      setHasChanges(false);
      setValidationStatus('idle');
      setValidationError(null);
    }
  }, [fileContent]);

  useEffect(() => {
    if (configFiles && configFiles.length > 0 && !selectedFile) {
      setSelectedFile(configFiles[0].name);
    }
  }, [configFiles, selectedFile]);

  const handleContentChange = useCallback((value: string) => {
    setEditContent(value);
    setHasChanges(value !== fileContent?.raw_content);
    setValidationStatus('idle');
  }, [fileContent?.raw_content]);

  const handleValidate = useCallback(async () => {
    if (!selectedFile) return;
    try {
      const result = await validateConfig.mutateAsync({ filename: selectedFile, rawContent: editContent });
      if (result.valid) {
        setValidationStatus('valid');
        setValidationError(null);
        toast.success('配置格式验证通过');
      } else {
        setValidationStatus('invalid');
        setValidationError(result.error || '格式错误');
        toast.error(`配置格式错误: ${result.error}`);
      }
    } catch {
      toast.error('验证失败');
    }
  }, [selectedFile, editContent, validateConfig]);

  const handleSave = useCallback(async () => {
    if (!selectedFile || !hasChanges) return;
    try {
      const result = await validateConfig.mutateAsync({ filename: selectedFile, rawContent: editContent });
      if (!result.valid) {
        toast.error(`配置格式错误，无法保存: ${result.error}`);
        setValidationStatus('invalid');
        setValidationError(result.error || '格式错误');
        return;
      }
    } catch {
      toast.error('验证失败，无法保存');
      return;
    }
    try {
      await updateConfig.mutateAsync({ filename: selectedFile, rawContent: editContent });
      setHasChanges(false);
      setValidationStatus('valid');
      toast.success('配置保存成功');
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '保存失败');
    }
  }, [selectedFile, hasChanges, editContent, validateConfig, updateConfig]);

  const handleRestore = useCallback(async () => {
    if (!selectedFile) return;
    if (!confirm('确定要从备份恢复配置吗？当前未保存的更改将丢失。')) return;
    try {
      await restoreConfig.mutateAsync(selectedFile);
      toast.success('配置已从备份恢复');
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '恢复失败');
    }
  }, [selectedFile, restoreConfig]);

  const handleDiscard = useCallback(() => {
    if (fileContent?.raw_content) {
      setEditContent(fileContent.raw_content);
      setHasChanges(false);
      setValidationStatus('idle');
      setValidationError(null);
    }
  }, [fileContent?.raw_content]);

  return (
    <div className="page-container">
      <Header
        title="配置及规则管理"
        description="管理 Nexus AI 平台配置文件"
        actions={<Button variant="outline" onClick={() => refetch()}><RefreshCw className="w-4 h-4" />刷新</Button>}
      />
      <div className="page-content">
        <div className="grid grid-cols-12 gap-6">
          <div className="col-span-3">
            <Card padding="none">
              <div className="p-4 border-b border-gray-100">
                <h3 className="font-semibold text-gray-900 flex items-center gap-2"><Settings className="w-4 h-4" />配置文件</h3>
              </div>
              <div className="divide-y divide-gray-100">
                {isLoading ? (
                  <div className="p-4 text-center text-gray-500">加载中...</div>
                ) : configFiles && configFiles.length > 0 ? (
                  configFiles.map((file) => (
                    <ConfigFileItem key={file.name} file={file} isSelected={selectedFile === file.name} onClick={() => setSelectedFile(file.name)} />
                  ))
                ) : (
                  <div className="p-4 text-center text-gray-500">暂无配置文件</div>
                )}
              </div>
            </Card>
          </div>
          <div className="col-span-9">
            <Card padding="none">
              <div className="p-4 border-b border-gray-100 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <FileText className="w-5 h-5 text-gray-400" />
                  <span className="font-medium text-gray-900">{selectedFile || '请选择配置文件'}</span>
                  {hasChanges && <Badge variant="warning" size="sm">未保存</Badge>}
                  {validationStatus === 'valid' && <Badge variant="success" size="sm"><Check className="w-3 h-3 mr-1" />格式正确</Badge>}
                  {validationStatus === 'invalid' && <Badge variant="error" size="sm"><X className="w-3 h-3 mr-1" />格式错误</Badge>}
                </div>
                <div className="flex items-center gap-2">
                  <div className="flex bg-gray-100 rounded-lg p-1">
                    <button onClick={() => setViewMode('visual')} className={`px-3 py-1 text-sm rounded-md transition-colors ${viewMode === 'visual' ? 'bg-white shadow text-gray-900' : 'text-gray-600 hover:text-gray-900'}`}><Eye className="w-4 h-4 inline mr-1" />可视化</button>
                    <button onClick={() => setViewMode('text')} className={`px-3 py-1 text-sm rounded-md transition-colors ${viewMode === 'text' ? 'bg-white shadow text-gray-900' : 'text-gray-600 hover:text-gray-900'}`}><Code className="w-4 h-4 inline mr-1" />文本</button>
                  </div>
                  <Button variant="outline" size="sm" onClick={handleValidate} disabled={!selectedFile || validateConfig.isPending}><Check className="w-4 h-4" />验证</Button>
                  <Button variant="outline" size="sm" onClick={handleDiscard} disabled={!hasChanges}><X className="w-4 h-4" />放弃</Button>
                  <Button variant="outline" size="sm" onClick={handleRestore} disabled={!selectedFile || restoreConfig.isPending}><RotateCcw className="w-4 h-4" />恢复备份</Button>
                  <Button variant="primary" size="sm" onClick={handleSave} disabled={!hasChanges || updateConfig.isPending} loading={updateConfig.isPending}><Save className="w-4 h-4" />保存</Button>
                </div>
              </div>
              {validationError && (
                <div className="px-4 py-3 bg-red-50 border-b border-red-100 flex items-start gap-2">
                  <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
                  <div className="text-sm text-red-700"><span className="font-medium">格式错误：</span><pre className="mt-1 whitespace-pre-wrap font-mono text-xs">{validationError}</pre></div>
                </div>
              )}
              <div className="p-0">
                {isLoadingContent ? (
                  <div className="h-[600px] flex items-center justify-center text-gray-500">加载中...</div>
                ) : selectedFile ? (
                  viewMode === 'visual' && fileContent?.content ? (
                    <VisualConfigEditor content={fileContent.content} rawContent={editContent} onChange={handleContentChange} />
                  ) : (
                    <textarea value={editContent} onChange={(e) => handleContentChange(e.target.value)} className="w-full h-[600px] p-4 font-mono text-sm bg-gray-50 border-0 resize-none focus:outline-none focus:ring-0" placeholder="配置内容..." spellCheck={false} />
                  )
                ) : (
                  <Empty icon={Settings} title="请选择配置文件" description="从左侧列表选择一个配置文件进行编辑" />
                )}
              </div>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}

interface ConfigFileItemProps { file: ConfigFile; isSelected: boolean; onClick: () => void; }

function ConfigFileItem({ file, isSelected, onClick }: ConfigFileItemProps) {
  return (
    <button onClick={onClick} className={`w-full text-left p-4 transition-colors ${isSelected ? 'bg-primary-50 border-l-2 border-primary-500' : 'hover:bg-gray-50 border-l-2 border-transparent'}`}>
      <div className="flex items-center gap-2 mb-1">
        <FileText className={`w-4 h-4 ${isSelected ? 'text-primary-500' : 'text-gray-400'}`} />
        <span className={`font-medium ${isSelected ? 'text-primary-700' : 'text-gray-900'}`}>{file.name}</span>
      </div>
      <div className="text-xs text-gray-500 ml-6">{formatRelativeTime(file.modified_at)} · {formatFileSize(file.size)}</div>
    </button>
  );
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

interface VisualConfigEditorProps { content: Record<string, unknown>; rawContent: string; onChange: (value: string) => void; }

function VisualConfigEditor({ content, rawContent, onChange }: VisualConfigEditorProps) {
  const [expandedKeys, setExpandedKeys] = useState<Set<string>>(new Set(['']));

  const toggleExpand = (key: string) => {
    const newExpanded = new Set(expandedKeys);
    if (newExpanded.has(key)) newExpanded.delete(key);
    else newExpanded.add(key);
    setExpandedKeys(newExpanded);
  };

  const updateValue = (path: string[], newValue: unknown) => {
    try {
      const parsed = yaml.load(rawContent) as Record<string, unknown>;
      let current: Record<string, unknown> = parsed;
      for (let i = 0; i < path.length - 1; i++) {
        current = current[path[i]] as Record<string, unknown>;
      }
      current[path[path.length - 1]] = newValue;
      const newYaml = yaml.dump(parsed, { indent: 2, lineWidth: -1, noRefs: true });
      onChange(newYaml);
    } catch (e) {
      console.error('Failed to update config:', e);
    }
  };

  return (
    <div className="h-[600px] overflow-auto p-4">
      <ConfigNode data={content} path={[]} expandedKeys={expandedKeys} onToggle={toggleExpand} onUpdate={updateValue} />
    </div>
  );
}

interface ConfigNodeProps { data: unknown; path: string[]; expandedKeys: Set<string>; onToggle: (key: string) => void; onUpdate: (path: string[], value: unknown) => void; }

function ConfigNode({ data, path, expandedKeys, onToggle, onUpdate }: ConfigNodeProps) {
  const pathKey = path.join('.');
  const isExpanded = expandedKeys.has(pathKey);

  if (data === null || data === undefined) {
    return <span className="text-gray-400 italic">null</span>;
  }

  if (typeof data === 'string') {
    return (
      <input type="text" value={data} onChange={(e) => onUpdate(path, e.target.value)} className="px-2 py-1 text-sm border border-gray-200 rounded focus:border-primary-500 focus:ring-1 focus:ring-primary-500 w-full max-w-md" />
    );
  }

  if (typeof data === 'number') {
    return (
      <input type="number" value={data} onChange={(e) => onUpdate(path, parseFloat(e.target.value) || 0)} className="px-2 py-1 text-sm border border-gray-200 rounded focus:border-primary-500 focus:ring-1 focus:ring-primary-500 w-32" />
    );
  }

  if (typeof data === 'boolean') {
    return (
      <button onClick={() => onUpdate(path, !data)} className={`px-3 py-1 text-sm rounded-full ${data ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'}`}>
        {data ? 'true' : 'false'}
      </button>
    );
  }

  if (Array.isArray(data)) {
    return (
      <div className="space-y-2">
        <button onClick={() => onToggle(pathKey)} className="flex items-center gap-1 text-sm text-gray-600 hover:text-gray-900">
          {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
          <span className="text-gray-400">[{data.length} 项]</span>
        </button>
        {isExpanded && (
          <div className="pl-4 border-l-2 border-gray-200 space-y-2">
            {data.map((item, index) => (
              <div key={index} className="flex items-start gap-2">
                <span className="text-xs text-gray-400 mt-2">{index}</span>
                <div className="flex-1"><ConfigNode data={item} path={[...path, String(index)]} expandedKeys={expandedKeys} onToggle={onToggle} onUpdate={onUpdate} /></div>
              </div>
            ))}
          </div>
        )}
      </div>
    );
  }

  if (typeof data === 'object') {
    const entries = Object.entries(data);
    return (
      <div className="space-y-3">
        {path.length > 0 && (
          <button onClick={() => onToggle(pathKey)} className="flex items-center gap-1 text-sm text-gray-600 hover:text-gray-900">
            {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
            <span className="text-gray-400">{`{${entries.length} 项}`}</span>
          </button>
        )}
        {(path.length === 0 || isExpanded) && (
          <div className={path.length > 0 ? 'pl-4 border-l-2 border-gray-200 space-y-3' : 'space-y-3'}>
            {entries.map(([key, value]) => (
              <div key={key} className="bg-white rounded-lg border border-gray-100 p-3">
                <div className="flex items-center gap-2 mb-2">
                  <span className="font-medium text-gray-700">{key}</span>
                  <span className="text-xs text-gray-400">{getTypeLabel(value)}</span>
                </div>
                <ConfigNode data={value} path={[...path, key]} expandedKeys={expandedKeys} onToggle={onToggle} onUpdate={onUpdate} />
              </div>
            ))}
          </div>
        )}
      </div>
    );
  }

  return <span className="text-gray-600">{String(data)}</span>;
}

function getTypeLabel(value: unknown): string {
  if (value === null || value === undefined) return 'null';
  if (Array.isArray(value)) return `array[${value.length}]`;
  if (typeof value === 'object') return `object{${Object.keys(value).length}}`;
  return typeof value;
}
