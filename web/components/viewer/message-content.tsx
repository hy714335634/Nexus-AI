'use client';

import { useEffect, useRef, useState, useMemo, memo } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Highlight, themes } from 'prism-react-renderer';
import mermaid from 'mermaid';
import { Copy, Check, ChevronDown, ChevronRight } from 'lucide-react';

// 初始化 mermaid
mermaid.initialize({
  startOnLoad: false,
  theme: 'neutral',
  securityLevel: 'loose',
  fontFamily: 'inherit',
});

interface MessageContentProps {
  content: string;
  className?: string;
  isStreaming?: boolean;
  variant?: 'user' | 'assistant';
}

// Mermaid 图表组件
const MermaidDiagram = memo(({ code }: { code: string }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [svg, setSvg] = useState<string>('');
  const [error, setError] = useState<string>('');
  const [isExpanded, setIsExpanded] = useState(true);

  useEffect(() => {
    const renderDiagram = async () => {
      if (!code.trim()) return;
      
      try {
        const id = `mermaid-${Math.random().toString(36).substr(2, 9)}`;
        const { svg } = await mermaid.render(id, code);
        setSvg(svg);
        setError('');
      } catch (err) {
        setError(err instanceof Error ? err.message : '图表渲染失败');
        setSvg('');
      }
    };

    renderDiagram();
  }, [code]);

  if (error) {
    return (
      <div className="my-3 p-3 bg-red-50 border border-red-200 rounded-lg text-red-600 text-xs">
        <div className="font-medium mb-1">Mermaid 渲染错误</div>
        <div className="opacity-75">{error}</div>
      </div>
    );
  }

  return (
    <div className="my-3 border border-gray-200 rounded-lg overflow-hidden bg-white">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center gap-2 px-3 py-2 bg-gray-50 hover:bg-gray-100 transition-colors text-xs text-gray-600"
      >
        {isExpanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
        <span>Mermaid 图表</span>
      </button>
      {isExpanded && svg && (
        <div
          ref={containerRef}
          className="p-4 overflow-auto flex justify-center"
          dangerouslySetInnerHTML={{ __html: svg }}
        />
      )}
    </div>
  );
});
MermaidDiagram.displayName = 'MermaidDiagram';

// 代码块组件
const CodeBlock = memo(({ 
  code, 
  language 
}: { 
  code: string; 
  language: string;
}) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('复制失败:', err);
    }
  };

  // 检测是否是 mermaid
  if (language === 'mermaid') {
    return <MermaidDiagram code={code} />;
  }

  return (
    <div className="my-3 rounded-lg overflow-hidden border border-gray-200 bg-[#011627]">
      <div className="flex items-center justify-between px-3 py-1.5 bg-[#0d1b2a] border-b border-gray-700">
        <span className="text-xs text-gray-400">{language || 'code'}</span>
        <button
          onClick={handleCopy}
          className="flex items-center gap-1 px-2 py-1 text-xs text-gray-400 hover:text-white transition-colors rounded"
        >
          {copied ? (
            <>
              <Check className="w-3 h-3" />
              <span>已复制</span>
            </>
          ) : (
            <>
              <Copy className="w-3 h-3" />
              <span>复制</span>
            </>
          )}
        </button>
      </div>
      <div className="overflow-auto max-h-[400px]">
        <Highlight theme={themes.nightOwl} code={code.trim()} language={language as any || 'text'}>
          {({ className, style, tokens, getLineProps, getTokenProps }) => (
            <pre 
              className={className} 
              style={{ 
                ...style, 
                margin: 0, 
                padding: '12px 16px',
                fontSize: '13px',
                lineHeight: '1.5',
                background: 'transparent',
              }}
            >
              {tokens.map((line, i) => (
                <div key={i} {...getLineProps({ line })}>
                  <span className="inline-block w-8 text-gray-500 select-none text-right mr-4 text-xs">
                    {i + 1}
                  </span>
                  {line.map((token, key) => (
                    <span key={key} {...getTokenProps({ token })} />
                  ))}
                </div>
              ))}
            </pre>
          )}
        </Highlight>
      </div>
    </div>
  );
});
CodeBlock.displayName = 'CodeBlock';

// 内联代码组件
const InlineCode = memo(({ children }: { children: React.ReactNode }) => (
  <code className="px-1.5 py-0.5 mx-0.5 bg-gray-100 text-gray-800 rounded text-[0.85em] font-mono">
    {children}
  </code>
));
InlineCode.displayName = 'InlineCode';


// 主组件
export const MessageContent = memo(({ 
  content, 
  className = '',
  isStreaming = false,
  variant = 'assistant'
}: MessageContentProps) => {
  // 检测内容类型
  const contentType = useMemo(() => {
    if (!content) return 'text';
    
    // 检测是否包含 markdown 特征
    const markdownPatterns = [
      /^#{1,6}\s/m,           // 标题
      /\*\*[^*]+\*\*/,        // 粗体
      /\*[^*]+\*/,            // 斜体
      /```[\s\S]*?```/,       // 代码块
      /`[^`]+`/,              // 内联代码
      /^\s*[-*+]\s/m,         // 无序列表
      /^\s*\d+\.\s/m,         // 有序列表
      /\[.+\]\(.+\)/,         // 链接
      /^\s*>/m,               // 引用
      /\|.+\|/,               // 表格
    ];
    
    const hasMarkdown = markdownPatterns.some(pattern => pattern.test(content));
    return hasMarkdown ? 'markdown' : 'text';
  }, [content]);

  // 用户消息使用简单文本渲染
  if (variant === 'user') {
    return (
      <div className={`whitespace-pre-wrap text-sm ${className}`}>
        {content}
      </div>
    );
  }

  // 纯文本渲染
  if (contentType === 'text') {
    return (
      <div className={`whitespace-pre-wrap text-sm leading-relaxed ${className}`}>
        {content}
        {isStreaming && (
          <span className="inline-block w-0.5 h-[1.1em] ml-0.5 bg-gray-600 align-middle animate-cursor-blink" />
        )}
      </div>
    );
  }

  // Markdown 渲染
  return (
    <div className={`message-content ${className}`}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          // 标题 - 优化字号
          h1: ({ children }) => (
            <h1 className="text-lg font-semibold text-gray-900 mt-4 mb-2 first:mt-0">
              {children}
            </h1>
          ),
          h2: ({ children }) => (
            <h2 className="text-base font-semibold text-gray-900 mt-3 mb-2 first:mt-0">
              {children}
            </h2>
          ),
          h3: ({ children }) => (
            <h3 className="text-sm font-semibold text-gray-900 mt-3 mb-1.5 first:mt-0">
              {children}
            </h3>
          ),
          h4: ({ children }) => (
            <h4 className="text-sm font-medium text-gray-800 mt-2 mb-1 first:mt-0">
              {children}
            </h4>
          ),
          h5: ({ children }) => (
            <h5 className="text-sm font-medium text-gray-700 mt-2 mb-1 first:mt-0">
              {children}
            </h5>
          ),
          h6: ({ children }) => (
            <h6 className="text-xs font-medium text-gray-600 mt-2 mb-1 first:mt-0">
              {children}
            </h6>
          ),
          
          // 段落
          p: ({ children }) => (
            <p className="text-sm leading-relaxed text-gray-700 my-2 first:mt-0 last:mb-0">
              {children}
            </p>
          ),
          
          // 列表
          ul: ({ children }) => (
            <ul className="text-sm my-2 ml-4 space-y-1 list-disc list-outside text-gray-700">
              {children}
            </ul>
          ),
          ol: ({ children }) => (
            <ol className="text-sm my-2 ml-4 space-y-1 list-decimal list-outside text-gray-700">
              {children}
            </ol>
          ),
          li: ({ children }) => (
            <li className="leading-relaxed pl-1">
              {children}
            </li>
          ),
          
          // 代码
          code: ({ node, className, children, ...props }) => {
            const match = /language-(\w+)/.exec(className || '');
            const isInline = !match && !String(children).includes('\n');
            
            if (isInline) {
              return <InlineCode>{children}</InlineCode>;
            }
            
            return (
              <CodeBlock 
                code={String(children).replace(/\n$/, '')} 
                language={match ? match[1] : ''} 
              />
            );
          },
          
          // 预格式化
          pre: ({ children }) => <>{children}</>,
          
          // 引用
          blockquote: ({ children }) => (
            <blockquote className="my-3 pl-3 border-l-3 border-gray-300 text-sm text-gray-600 italic">
              {children}
            </blockquote>
          ),
          
          // 链接
          a: ({ href, children }) => (
            <a 
              href={href} 
              target="_blank" 
              rel="noopener noreferrer"
              className="text-primary-600 hover:text-primary-700 underline underline-offset-2"
            >
              {children}
            </a>
          ),
          
          // 强调
          strong: ({ children }) => (
            <strong className="font-semibold text-gray-900">{children}</strong>
          ),
          em: ({ children }) => (
            <em className="italic">{children}</em>
          ),
          
          // 删除线
          del: ({ children }) => (
            <del className="line-through text-gray-500">{children}</del>
          ),
          
          // 水平线
          hr: () => <hr className="my-4 border-gray-200" />,
          
          // 表格
          table: ({ children }) => (
            <div className="my-3 overflow-auto">
              <table className="min-w-full text-sm border-collapse border border-gray-200 rounded-lg overflow-hidden">
                {children}
              </table>
            </div>
          ),
          thead: ({ children }) => (
            <thead className="bg-gray-50">{children}</thead>
          ),
          tbody: ({ children }) => (
            <tbody className="divide-y divide-gray-200">{children}</tbody>
          ),
          tr: ({ children }) => (
            <tr className="hover:bg-gray-50">{children}</tr>
          ),
          th: ({ children }) => (
            <th className="px-3 py-2 text-left text-xs font-semibold text-gray-700 border-b border-gray-200">
              {children}
            </th>
          ),
          td: ({ children }) => (
            <td className="px-3 py-2 text-gray-600 border-b border-gray-100">
              {children}
            </td>
          ),
          
          // 图片
          img: ({ src, alt }) => (
            // eslint-disable-next-line @next/next/no-img-element
            <img 
              src={src} 
              alt={alt || ''} 
              className="my-3 max-w-full h-auto rounded-lg border border-gray-200"
              loading="lazy"
            />
          ),
        }}
      >
        {content}
      </ReactMarkdown>
      {isStreaming && (
        <span className="inline-block w-0.5 h-[1.1em] ml-0.5 bg-gray-600 align-middle animate-cursor-blink" />
      )}
    </div>
  );
});
MessageContent.displayName = 'MessageContent';

export default MessageContent;
