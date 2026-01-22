'use client';

import { useState, useMemo, useCallback, useEffect, useRef } from 'react';
import { Highlight, themes } from 'prism-react-renderer';
import {
  Code,
  ChevronRight,
  Search,
  Copy,
  Download,
  Edit3,
  Save,
  CheckCircle2,
  AlertCircle,
  Hash,
  Box,
  Braces,
  FileCode,
  List,
} from 'lucide-react';

// Python代码结构信息
interface CodeStructure {
  type: 'class' | 'function' | 'method' | 'import';
  name: string;
  lineNumber: number;
  endLine?: number;
  docstring?: string;
  decorator?: string;
  parent?: string; // 类方法的父类名
}

interface PythonCodeViewerProps {
  readonly content: string;
  readonly filename?: string;
  readonly editable?: boolean;
  readonly onSave?: (content: string) => Promise<void>;
  readonly saving?: boolean;
  readonly maxHeight?: string;
}

// 解析Python代码结构
function parsePythonStructure(content: string): CodeStructure[] {
  const structures: CodeStructure[] = [];
  const lines = content.split('\n');
  
  let currentClass: string | null = null;
  let currentClassIndent = 0;
  let i = 0;
  
  while (i < lines.length) {
    const line = lines[i];
    const trimmed = line.trim();
    const indent = line.search(/\S/);
    
    // 跳过空行和注释
    if (!trimmed || trimmed.startsWith('#')) {
      i++;
      continue;
    }
    
    // 检测import语句（只记录前几个）
    if (structures.filter(s => s.type === 'import').length < 3) {
      if (trimmed.startsWith('import ') || trimmed.startsWith('from ')) {
        const importMatch = trimmed.match(/^(?:from\s+(\S+)\s+)?import\s+(.+)/);
        if (importMatch) {
          structures.push({
            type: 'import',
            name: importMatch[1] || importMatch[2].split(',')[0].trim(),
            lineNumber: i + 1,
          });
        }
        i++;
        continue;
      }
    }
    
    // 检测类定义
    const classMatch = trimmed.match(/^class\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*[\(:]?/);
    if (classMatch && indent === 0) {
      currentClass = classMatch[1];
      currentClassIndent = indent;
      
      // 尝试提取docstring
      let docstring: string | undefined;
      let j = i + 1;
      while (j < lines.length && !lines[j].trim()) j++;
      if (j < lines.length) {
        const docLine = lines[j].trim();
        if (docLine.startsWith('"""') || docLine.startsWith("'''")) {
          const quote = docLine.startsWith('"""') ? '"""' : "'''";
          if (docLine.endsWith(quote) && docLine.length > 6) {
            docstring = docLine.slice(3, -3).trim();
          } else {
            const docLines = [docLine.slice(3)];
            j++;
            while (j < lines.length && !lines[j].includes(quote)) {
              docLines.push(lines[j].trim());
              j++;
            }
            docstring = docLines.join(' ').trim().substring(0, 80);
          }
        }
      }
      
      structures.push({
        type: 'class',
        name: currentClass,
        lineNumber: i + 1,
        docstring,
      });
      i++;
      continue;
    }
    
    // 检测函数/方法定义
    let decorator: string | undefined;
    let defLineIndex = i;
    
    // 检查是否有装饰器
    if (trimmed.startsWith('@')) {
      decorator = trimmed;
      defLineIndex = i + 1;
      // 跳过多个装饰器
      while (defLineIndex < lines.length && lines[defLineIndex].trim().startsWith('@')) {
        defLineIndex++;
      }
    }
    
    if (defLineIndex < lines.length) {
      const defLine = lines[defLineIndex].trim();
      const defIndent = lines[defLineIndex].search(/\S/);
      const funcMatch = defLine.match(/^(?:async\s+)?def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(/);
      
      if (funcMatch) {
        const funcName = funcMatch[1];
        const isMethod = currentClass && defIndent > currentClassIndent;
        
        // 尝试提取docstring
        let docstring: string | undefined;
        let j = defLineIndex + 1;
        // 跳过函数参数行直到找到冒号
        while (j < lines.length && !lines[j - 1].includes(':')) {
          j++;
        }
        // 跳过空行
        while (j < lines.length && !lines[j].trim()) j++;
        
        if (j < lines.length) {
          const docLine = lines[j].trim();
          if (docLine.startsWith('"""') || docLine.startsWith("'''")) {
            const quote = docLine.startsWith('"""') ? '"""' : "'''";
            if (docLine.endsWith(quote) && docLine.length > 6) {
              docstring = docLine.slice(3, -3).trim();
            } else {
              const docLines = [docLine.slice(3)];
              j++;
              while (j < lines.length && !lines[j].includes(quote)) {
                docLines.push(lines[j].trim());
                j++;
              }
              docstring = docLines.join(' ').trim();
              if (docstring.length > 60) {
                docstring = docstring.substring(0, 60) + '...';
              }
            }
          }
        }
        
        structures.push({
          type: isMethod ? 'method' : 'function',
          name: funcName,
          lineNumber: decorator ? i + 1 : defLineIndex + 1,
          docstring,
          decorator,
          parent: isMethod ? currentClass || undefined : undefined,
        });
        
        i = defLineIndex + 1;
        continue;
      }
    }
    
    // 检查是否离开了当前类
    if (currentClass && indent === 0 && !trimmed.startsWith('@') && !trimmed.startsWith('class ')) {
      currentClass = null;
    }
    
    i++;
  }
  
  return structures;
}

export function PythonCodeViewer({
  content,
  filename,
  editable = false,
  onSave,
  saving = false,
  maxHeight = '600px',
}: PythonCodeViewerProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [isEditing, setIsEditing] = useState(false);
  const [editedContent, setEditedContent] = useState(content);
  const [hasChanges, setHasChanges] = useState(false);
  const [saveMessage, setSaveMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [copied, setCopied] = useState(false);
  const [showNav, setShowNav] = useState(true);
  const codeContainerRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  
  // 解析代码结构
  const codeStructure = useMemo(() => {
    if (!content) return [];
    return parsePythonStructure(content);
  }, [content]);
  
  // 过滤结构
  const filteredStructure = useMemo(() => {
    if (!searchQuery) return codeStructure;
    const query = searchQuery.toLowerCase();
    return codeStructure.filter(
      s => s.name.toLowerCase().includes(query) || 
           s.docstring?.toLowerCase().includes(query)
    );
  }, [codeStructure, searchQuery]);
  
  // 按类型分组
  const groupedStructure = useMemo(() => {
    const classes = filteredStructure.filter(s => s.type === 'class');
    const functions = filteredStructure.filter(s => s.type === 'function');
    const methods = filteredStructure.filter(s => s.type === 'method');
    return { classes, functions, methods };
  }, [filteredStructure]);
  
  // 当content变化时重置状态
  useEffect(() => {
    setEditedContent(content);
    setHasChanges(false);
    setIsEditing(false);
  }, [content]);
  
  // 滚动到指定行
  const scrollToLine = useCallback((lineNumber: number) => {
    if (codeContainerRef.current) {
      const lineHeight = 24;
      const scrollTop = (lineNumber - 1) * lineHeight - 100;
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
    const blob = new Blob([isEditing ? editedContent : content], { type: 'text/plain;charset=utf-8' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = filename || 'agent.py';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(link.href);
  }, [content, editedContent, isEditing, filename]);
  
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
    if (!onSave || !hasChanges) return;
    try {
      await onSave(editedContent);
      setSaveMessage({ type: 'success', text: '保存成功' });
      setIsEditing(false);
      setHasChanges(false);
    } catch {
      setSaveMessage({ type: 'error', text: '保存失败' });
    }
    setTimeout(() => setSaveMessage(null), 3000);
  }, [onSave, editedContent, hasChanges]);
  
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
  
  // 获取结构行号集合用于高亮
  const structureLines = useMemo(() => {
    return new Set(codeStructure.map(s => s.lineNumber));
  }, [codeStructure]);
  
  if (!content?.trim()) {
    return (
      <div className="rounded-xl border border-gray-200 bg-white p-8 text-center">
        <Code className="w-12 h-12 text-gray-300 mx-auto mb-3" />
        <p className="text-gray-500">暂无代码内容</p>
      </div>
    );
  }
  
  const hasStructure = codeStructure.length > 0;
  
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
      
      <div className="flex">
        {/* 左侧：代码结构导航 */}
        {hasStructure && showNav && !isEditing && (
          <div className="w-56 border-r border-gray-200 bg-gray-50/50 flex-shrink-0">
            <div className="p-2 border-b border-gray-200">
              <div className="relative">
                <Search className="w-4 h-4 absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-400" />
                <input
                  type="text"
                  placeholder="搜索..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-8 pr-3 py-1.5 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>
            </div>
            
            <div className="p-2 max-h-[550px] overflow-y-auto">
              {/* 类 */}
              {groupedStructure.classes.length > 0 && (
                <div className="mb-3">
                  <div className="text-xs text-gray-400 px-2 py-1 flex items-center gap-1">
                    <Box className="w-3 h-3" />
                    类 ({groupedStructure.classes.length})
                  </div>
                  {groupedStructure.classes.map((item, idx) => (
                    <NavItem key={idx} item={item} onClick={() => scrollToLine(item.lineNumber)} />
                  ))}
                </div>
              )}
              
              {/* 函数 */}
              {groupedStructure.functions.length > 0 && (
                <div className="mb-3">
                  <div className="text-xs text-gray-400 px-2 py-1 flex items-center gap-1">
                    <Braces className="w-3 h-3" />
                    函数 ({groupedStructure.functions.length})
                  </div>
                  {groupedStructure.functions.map((item, idx) => (
                    <NavItem key={idx} item={item} onClick={() => scrollToLine(item.lineNumber)} />
                  ))}
                </div>
              )}
              
              {/* 方法 */}
              {groupedStructure.methods.length > 0 && (
                <div>
                  <div className="text-xs text-gray-400 px-2 py-1 flex items-center gap-1">
                    <FileCode className="w-3 h-3" />
                    方法 ({groupedStructure.methods.length})
                  </div>
                  {groupedStructure.methods.map((item, idx) => (
                    <NavItem key={idx} item={item} onClick={() => scrollToLine(item.lineNumber)} />
                  ))}
                </div>
              )}
              
              {filteredStructure.length === 0 && searchQuery && (
                <div className="text-center py-4 text-sm text-gray-400">
                  没有匹配结果
                </div>
              )}
            </div>
          </div>
        )}
        
        {/* 右侧：代码区域 */}
        <div className="flex-1 min-w-0">
          {/* 工具栏 */}
          <div className="px-4 py-2 bg-gray-900 border-b border-gray-800 flex items-center justify-between">
            <div className="flex items-center gap-2 text-sm text-gray-400">
              {hasStructure && (
                <button
                  onClick={() => setShowNav(!showNav)}
                  className={`p-1 rounded hover:bg-gray-800 ${showNav ? 'text-blue-400' : ''}`}
                  title={showNav ? '隐藏导航' : '显示导航'}
                >
                  <List className="w-4 h-4" />
                </button>
              )}
              <span>{filename || 'agent.py'}</span>
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
                      className="px-3 py-1 text-xs rounded-lg bg-blue-600 text-white hover:bg-blue-700 flex items-center gap-1"
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
            style={{ maxHeight }}
            className="overflow-auto bg-gray-900"
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
                      const isStructureLine = structureLines.has(i + 1);
                      return (
                        <div 
                          key={i} 
                          {...getLineProps({ line, key: i })}
                          className={isStructureLine ? 'bg-blue-900/20 -mx-4 px-4' : ''}
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

// 导航项组件
function NavItem({ 
  item, 
  onClick 
}: { 
  item: CodeStructure; 
  onClick: () => void;
}) {
  const getIcon = () => {
    switch (item.type) {
      case 'class': return <Box className="w-3.5 h-3.5 text-yellow-500" />;
      case 'function': return <Braces className="w-3.5 h-3.5 text-blue-500" />;
      case 'method': return <FileCode className="w-3.5 h-3.5 text-purple-500" />;
      default: return <Code className="w-3.5 h-3.5 text-gray-500" />;
    }
  };
  
  return (
    <button
      onClick={onClick}
      className="w-full text-left px-2 py-1.5 rounded-lg hover:bg-blue-50 group transition-colors"
    >
      <div className="flex items-center gap-2">
        {getIcon()}
        <span className="font-mono text-sm text-gray-700 truncate flex-1">
          {item.parent && <span className="text-gray-400">{item.parent}.</span>}
          {item.name}
        </span>
        <ChevronRight className="w-3 h-3 text-gray-300 opacity-0 group-hover:opacity-100" />
      </div>
      {item.docstring && (
        <p className="text-xs text-gray-400 mt-0.5 pl-5 truncate">{item.docstring}</p>
      )}
      <div className="flex items-center gap-1 text-xs text-gray-300 pl-5">
        <Hash className="w-3 h-3" />
        <span>{item.lineNumber}</span>
        {item.decorator && (
          <span className="text-amber-500 ml-1">{item.decorator}</span>
        )}
      </div>
    </button>
  );
}
