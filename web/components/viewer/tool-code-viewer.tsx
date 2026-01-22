'use client';

import { useState, useMemo, useCallback, useEffect, useRef } from 'react';
import { Highlight, themes } from 'prism-react-renderer';
import {
  Wrench,
  ChevronRight,
  FileCode,
  Search,
  Copy,
  Download,
  Edit3,
  Save,
  X,
  CheckCircle2,
  AlertCircle,
  Hash,
} from 'lucide-react';

// 工具函数信息
interface ToolFunction {
  name: string;
  lineNumber: number;
  docstring?: string;
  decorator: string;
}

// 工具文件信息
interface ToolFile {
  name: string;
  path: string;
  content: string;
  exists: boolean;
}

interface ToolCodeViewerProps {
  readonly files: ToolFile[];
  readonly editable?: boolean;
  readonly onSave?: (fileName: string, content: string) => Promise<void>;
  readonly saving?: boolean;
}

// 解析Python代码中的@tool装饰器函数
function parseToolFunctions(content: string): ToolFunction[] {
  const functions: ToolFunction[] = [];
  const lines = content.split('\n');
  
  let i = 0;
  while (i < lines.length) {
    const line = lines[i];
    const trimmed = line.trim();
    
    // 检测@tool装饰器
    if (trimmed.startsWith('@tool')) {
      const decorator = trimmed;
      let j = i + 1;
      
      // 跳过其他装饰器
      while (j < lines.length && lines[j].trim().startsWith('@')) {
        j++;
      }
      
      // 查找def语句
      if (j < lines.length) {
        const defLine = lines[j].trim();
        const defMatch = defLine.match(/^def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(/);
        
        if (defMatch) {
          const funcName = defMatch[1];
          
          // 尝试提取docstring
          let docstring: string | undefined;
          let k = j + 1;
          
          // 跳过函数参数行
          while (k < lines.length && !lines[k].includes(':')) {
            k++;
          }
          k++; // 跳过冒号行
          
          // 检查是否有docstring
          if (k < lines.length) {
            const docLine = lines[k].trim();
            if (docLine.startsWith('"""') || docLine.startsWith("'''")) {
              const quote = docLine.startsWith('"""') ? '"""' : "'''";
              if (docLine.endsWith(quote) && docLine.length > 6) {
                // 单行docstring
                docstring = docLine.slice(3, -3).trim();
              } else {
                // 多行docstring
                const docLines = [docLine.slice(3)];
                k++;
                while (k < lines.length && !lines[k].includes(quote)) {
                  docLines.push(lines[k].trim());
                  k++;
                }
                docstring = docLines.join(' ').trim();
                if (docstring.length > 100) {
                  docstring = docstring.substring(0, 100) + '...';
                }
              }
            }
          }
          
          functions.push({
            name: funcName,
            lineNumber: j + 1, // 1-based line number
            docstring,
            decorator,
          });
        }
      }
    }
    i++;
  }
  
  return functions;
}

export function ToolCodeViewer({
  files,
  editable = false,
  onSave,
  saving = false,
}: ToolCodeViewerProps) {
  const [selectedFileIndex, setSelectedFileIndex] = useState(0);
  const [searchQuery, setSearchQuery] = useState('');
  const [isEditing, setIsEditing] = useState(false);
  const [editedContent, setEditedContent] = useState('');
  const [hasChanges, setHasChanges] = useState(false);
  const [saveMessage, setSaveMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [copied, setCopied] = useState(false);
  const codeContainerRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  
  const selectedFile = files[selectedFileIndex];
  const content = selectedFile?.content || '';
  
  // 解析工具函数
  const toolFunctions = useMemo(() => {
    if (!content) return [];
    return parseToolFunctions(content);
  }, [content]);
  
  // 过滤函数
  const filteredFunctions = useMemo(() => {
    if (!searchQuery) return toolFunctions;
    const query = searchQuery.toLowerCase();
    return toolFunctions.filter(
      f => f.name.toLowerCase().includes(query) || 
           f.docstring?.toLowerCase().includes(query)
    );
  }, [toolFunctions, searchQuery]);
  
  // 当文件变化时重置状态
  useEffect(() => {
    setEditedContent(content);
    setHasChanges(false);
    setIsEditing(false);
  }, [content, selectedFileIndex]);
  
  // 滚动到指定行
  const scrollToLine = useCallback((lineNumber: number) => {
    if (codeContainerRef.current) {
      const lineHeight = 24; // 估算的行高
      const scrollTop = (lineNumber - 1) * lineHeight - 100; // 留一些上边距
      codeContainerRef.current.scrollTo({
        top: Math.max(0, scrollTop),
        behavior: 'smooth',
      });
    }
  }, []);
  
  // 复制代码
  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(isEditing ? editedContent : content);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch (error) {
      console.error('复制失败', error);
    }
  }, [content, editedContent, isEditing]);
  
  // 下载文件
  const handleDownload = useCallback(() => {
    if (!selectedFile) return;
    const blob = new Blob([isEditing ? editedContent : content], { type: 'text/plain;charset=utf-8' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = selectedFile.name;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(link.href);
  }, [selectedFile, content, editedContent, isEditing]);
  
  // 开始编辑
  const handleEdit = useCallback(() => {
    setIsEditing(true);
    setEditedContent(content);
    setTimeout(() => textareaRef.current?.focus(), 100);
  }, [content]);
  
  // 取消编辑
  const handleCancel = useCallback(() => {
    setIsEditing(false);
    setEditedContent(content);
    setHasChanges(false);
  }, [content]);
  
  // 保存
  const handleSave = useCallback(async () => {
    if (!onSave || !selectedFile || !hasChanges) return;
    try {
      await onSave(selectedFile.name, editedContent);
      setSaveMessage({ type: 'success', text: '保存成功' });
      setIsEditing(false);
      setHasChanges(false);
    } catch {
      setSaveMessage({ type: 'error', text: '保存失败' });
    }
    setTimeout(() => setSaveMessage(null), 3000);
  }, [onSave, selectedFile, editedContent, hasChanges]);
  
  // 内容变化
  const handleContentChange = useCallback((e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const newContent = e.target.value;
    setEditedContent(newContent);
    setHasChanges(newContent !== content);
  }, [content]);
  
  // 处理Tab键
  const handleKeyDown = useCallback((e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Tab') {
      e.preventDefault();
      const textarea = e.currentTarget;
      const start = textarea.selectionStart;
      const end = textarea.selectionEnd;
      const newContent = editedContent.substring(0, start) + '    ' + editedContent.substring(end);
      setEditedContent(newContent);
      setHasChanges(newContent !== content);
      setTimeout(() => {
        textarea.selectionStart = textarea.selectionEnd = start + 4;
      }, 0);
    }
    if ((e.ctrlKey || e.metaKey) && e.key === 's') {
      e.preventDefault();
      if (hasChanges) handleSave();
    }
    if (e.key === 'Escape') {
      handleCancel();
    }
  }, [editedContent, content, hasChanges, handleSave, handleCancel]);
  
  if (files.length === 0) {
    return (
      <div className="rounded-xl border border-gray-200 bg-white p-8 text-center">
        <Wrench className="w-12 h-12 text-gray-300 mx-auto mb-3" />
        <p className="text-gray-500">没有工具文件</p>
      </div>
    );
  }
  
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
      
      {/* 文件选择器（多文件时显示） */}
      {files.length > 1 && (
        <div className="px-4 py-2 bg-gray-50 border-b border-gray-200 flex items-center gap-2 overflow-x-auto">
          <FileCode className="w-4 h-4 text-gray-400 flex-shrink-0" />
          {files.map((file, idx) => (
            <button
              key={file.path}
              onClick={() => setSelectedFileIndex(idx)}
              className={`px-3 py-1 text-sm rounded-lg whitespace-nowrap transition-colors ${
                selectedFileIndex === idx
                  ? 'bg-amber-100 text-amber-700 border border-amber-200'
                  : 'bg-white text-gray-600 border border-gray-200 hover:border-amber-200'
              }`}
            >
              {file.name}
            </button>
          ))}
        </div>
      )}
      
      <div className="flex">
        {/* 左侧：函数导航 */}
        <div className="w-64 border-r border-gray-200 bg-gray-50/50 flex-shrink-0">
          <div className="p-3 border-b border-gray-200">
            <div className="relative">
              <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
              <input
                type="text"
                placeholder="搜索函数..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-9 pr-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-amber-500 focus:border-transparent"
              />
            </div>
          </div>
          
          <div className="p-2">
            <div className="text-xs text-gray-400 px-2 py-1 mb-1">
              工具函数 ({filteredFunctions.length})
            </div>
            <div className="space-y-0.5 max-h-[500px] overflow-y-auto">
              {filteredFunctions.length > 0 ? (
                filteredFunctions.map((func, idx) => (
                  <button
                    key={idx}
                    onClick={() => scrollToLine(func.lineNumber)}
                    className="w-full text-left px-2 py-2 rounded-lg hover:bg-amber-50 group transition-colors"
                  >
                    <div className="flex items-center gap-2">
                      <Wrench className="w-4 h-4 text-amber-500 flex-shrink-0" />
                      <span className="font-mono text-sm text-gray-700 truncate">{func.name}</span>
                      <ChevronRight className="w-3 h-3 text-gray-300 ml-auto opacity-0 group-hover:opacity-100" />
                    </div>
                    {func.docstring && (
                      <p className="text-xs text-gray-400 mt-1 pl-6 truncate">{func.docstring}</p>
                    )}
                    <div className="flex items-center gap-1 text-xs text-gray-300 mt-1 pl-6">
                      <Hash className="w-3 h-3" />
                      <span>行 {func.lineNumber}</span>
                    </div>
                  </button>
                ))
              ) : (
                <div className="text-center py-4 text-sm text-gray-400">
                  {searchQuery ? '没有匹配的函数' : '没有检测到@tool函数'}
                </div>
              )}
            </div>
          </div>
        </div>
        
        {/* 右侧：代码区域 */}
        <div className="flex-1 min-w-0">
          {/* 工具栏 */}
          <div className="px-4 py-2 bg-gray-900 border-b border-gray-800 flex items-center justify-between">
            <div className="flex items-center gap-2 text-sm text-gray-400">
              <span>{selectedFile?.name}</span>
              {hasChanges && (
                <span className="text-xs text-amber-400 bg-amber-900/30 px-2 py-0.5 rounded">未保存</span>
              )}
            </div>
            <div className="flex items-center gap-2">
              {isEditing ? (
                <>
                  <button
                    onClick={handleCancel}
                    disabled={saving}
                    className="px-3 py-1 text-xs rounded-lg border border-gray-600 text-gray-300 hover:bg-gray-800 disabled:opacity-50"
                  >
                    取消
                  </button>
                  <button
                    onClick={handleSave}
                    disabled={!hasChanges || saving}
                    className="px-3 py-1 text-xs rounded-lg bg-green-600 text-white hover:bg-green-700 disabled:opacity-50 flex items-center gap-1"
                  >
                    <Save className="w-3 h-3" />
                    {saving ? '保存中...' : '保存'}
                  </button>
                </>
              ) : (
                <>
                  <button
                    onClick={handleCopy}
                    className="px-3 py-1 text-xs rounded-lg border border-gray-600 text-gray-300 hover:bg-gray-800"
                  >
                    {copied ? '已复制' : '复制'}
                  </button>
                  <button
                    onClick={handleDownload}
                    className="px-3 py-1 text-xs rounded-lg border border-gray-600 text-gray-300 hover:bg-gray-800"
                  >
                    下载
                  </button>
                  {editable && (
                    <button
                      onClick={handleEdit}
                      className="px-3 py-1 text-xs rounded-lg bg-amber-600 text-white hover:bg-amber-700 flex items-center gap-1"
                    >
                      <Edit3 className="w-3 h-3" />
                      编辑
                    </button>
                  )}
                </>
              )}
            </div>
          </div>
          
          {/* 代码内容 */}
          <div 
            ref={codeContainerRef}
            className="max-h-[600px] overflow-auto bg-gray-900"
          >
            {isEditing ? (
              <textarea
                ref={textareaRef}
                value={editedContent}
                onChange={handleContentChange}
                onKeyDown={handleKeyDown}
                spellCheck={false}
                className="w-full min-h-[500px] p-4 bg-transparent text-gray-100 font-mono text-sm leading-6 resize-none focus:outline-none"
                style={{ tabSize: 4 }}
              />
            ) : (
              <Highlight theme={themes.nightOwl} code={content} language="python">
                {({ className, style, tokens, getLineProps, getTokenProps }) => (
                  <pre className={className} style={{ ...style, margin: 0, padding: '16px' }}>
                    {tokens.map((line, i) => {
                      // 检查是否是工具函数所在行
                      const isToolLine = toolFunctions.some(f => f.lineNumber === i + 1);
                      return (
                        <div 
                          key={i} 
                          {...getLineProps({ line, key: i })}
                          className={isToolLine ? 'bg-amber-900/20 -mx-4 px-4' : ''}
                        >
                          <span className="inline-block w-10 text-right pr-4 text-gray-500 select-none text-xs">
                            {i + 1}
                          </span>
                          {line.map((token, key) => (
                            <span key={key} {...getTokenProps({ token, key })} />
                          ))}
                        </div>
                      );
                    })}
                  </pre>
                )}
              </Highlight>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
