import React, { useEffect, useRef, useState } from 'react';
import { sanitizeHtml } from '../utils/sanitize';

interface TokenRendererProps {
  content: string[];
  agentName: string;
  isStreaming?: boolean;
}

const TokenRenderer: React.FC<TokenRendererProps> = ({ content, agentName, isStreaming = false }) => {
  const contentRef = useRef<HTMLDivElement>(null);
  const [copied, setCopied] = useState(false);
  
  // Auto-scroll to bottom when new content arrives
  useEffect(() => {
    if (contentRef.current) {
      contentRef.current.scrollTop = contentRef.current.scrollHeight;
    }
  }, [content]);
  
  // Join all tokens and format the text
  const fullText = content.join('');
  
  const copyToClipboard = async () => {
    try {
      await navigator.clipboard.writeText(fullText);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy text: ', err);
    }
  };
  
  // Enhanced formatting for various content types
  const formatText = (text: string) => {
    // Try to detect and format JSON
    const jsonRegex = /\{[\s\S]*?\}/g;
    text = text.replace(jsonRegex, (match) => {
      try {
        const parsed = JSON.parse(match);
        const formatted = JSON.stringify(parsed, null, 2);
        return `<div class="json-block"><pre><code>${formatted}</code></pre></div>`;
      } catch {
        return match; // Return original if not valid JSON
      }
    });
    
    // Handle code blocks
    text = text.replace(/```(\w+)?\n([\s\S]*?)```/g, (match, lang, code) => {
      return `<div class="code-block"><div class="code-lang">${lang || 'text'}</div><pre><code>${code.trim()}</code></pre></div>`;
    });
    
    // Handle inline code
    text = text.replace(/`([^`]+)`/g, '<code class="inline-code">$1</code>');
    
    // Handle bold text
    text = text.replace(/\*\*(.*?)\*\*/g, '<strong class="bold-text">$1</strong>');
    
    // Handle italic text
    text = text.replace(/\*(.*?)\*/g, '<em class="italic-text">$1</em>');
    
    // Handle headers
    text = text.replace(/^### (.+)$/gm, '<h3 class="header-3">$1</h3>');
    text = text.replace(/^## (.+)$/gm, '<h2 class="header-2">$1</h2>');
    text = text.replace(/^# (.+)$/gm, '<h1 class="header-1">$1</h1>');
    
    // Handle bullet points
    text = text.replace(/^- (.+)$/gm, '<div class="bullet-point">• $1</div>');
    
    // Handle numbered lists
    text = text.replace(/^\d+\. (.+)$/gm, '<div class="numbered-point">$1</div>');
    
    // Handle URLs
    text = text.replace(/(https?:\/\/[^\s]+)/g, '<a href="$1" target="_blank" class="link">$1</a>');
    
    // Handle markdown tables
    text = text.replace(/(?:^|\n)((?:\|[^\n]+\|\n)+)/g, (match) => {
      const rows = match.trim().split('\n').filter(r => r.trim());
      if (rows.length < 2) return match;
      
      // Check if second row is separator (|---|---|)
      const isSeparator = (row: string) => /^\|[\s\-:|]+\|$/.test(row.trim());
      
      let html = '<table style="border-collapse:collapse;width:100%;margin:8px 0;font-size:0.8rem;">';
      let headerDone = false;
      
      for (const row of rows) {
        if (isSeparator(row)) { headerDone = true; continue; }
        const cells = row.split('|').filter(c => c !== '').map(c => c.trim());
        const tag = !headerDone ? 'th' : 'td';
        const style = !headerDone 
          ? 'padding:4px 8px;border:1px solid #334155;background:#1e293b;font-weight:600;text-align:left;' 
          : 'padding:4px 8px;border:1px solid #334155;';
        html += '<tr>' + cells.map(c => `<${tag} style="${style}">${c}</${tag}>`).join('') + '</tr>';
        if (!headerDone) headerDone = true;
      }
      
      html += '</table>';
      return html;
    });
    
    // Handle AWS resource names (ARNs, etc.)
    text = text.replace(/(arn:aws:[^\s]+)/g, '<span class="aws-resource">$1</span>');
    
    // Handle line breaks
    text = text.replace(/\n/g, '<br>');
    
    return text;
  };

  const getAgentColor = (name: string) => {
    switch (name.toLowerCase()) {
      case 'risk assessment': return '#ff6b6b';
      case 'architect': return '#4ecdc4';
      case 'security architect': return '#45b7d1';
      case 'auditor': return '#96ceb4';
      default: return '#ffd93d';
    }
  };

  return (
    <div style={{
      backgroundColor: 'rgba(15, 23, 42, 0.9)',
      border: `1px solid ${getAgentColor(agentName)}40`,
      borderRadius: '8px',
      padding: '12px',
      marginTop: '8px'
    }}>
      <div style={{
        display: 'flex',
        alignItems: 'center',
        marginBottom: '8px',
        paddingBottom: '6px',
        borderBottom: `1px solid ${getAgentColor(agentName)}30`
      }}>
        <div style={{
          width: '8px',
          height: '8px',
          borderRadius: '50%',
          backgroundColor: getAgentColor(agentName),
          marginRight: '8px',
          animation: 'pulse 2s infinite'
        }} />
        <span style={{
          fontSize: '0.75rem',
          fontWeight: '600',
          color: getAgentColor(agentName),
          textTransform: 'uppercase',
          letterSpacing: '0.5px'
        }}>
          {agentName} Output
        </span>
        <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{
            fontSize: '0.7rem',
            color: '#64748b'
          }}>
            {content.length} tokens
          </span>
          <button
            onClick={copyToClipboard}
            style={{
              background: 'none',
              border: '1px solid rgba(100, 116, 139, 0.3)',
              borderRadius: '4px',
              padding: '2px 6px',
              fontSize: '0.7rem',
              color: copied ? '#22c55e' : '#94a3b8',
              cursor: 'pointer',
              transition: 'all 0.2s ease'
            }}
            onMouseEnter={(e) => {
              if (!copied) {
                e.currentTarget.style.borderColor = getAgentColor(agentName);
                e.currentTarget.style.color = getAgentColor(agentName);
              }
            }}
            onMouseLeave={(e) => {
              if (!copied) {
                e.currentTarget.style.borderColor = 'rgba(100, 116, 139, 0.3)';
                e.currentTarget.style.color = '#94a3b8';
              }
            }}
          >
            {copied ? '✓ Copied' : '📋 Copy'}
          </button>
        </div>
      </div>
      
      <div 
        ref={contentRef}
        style={{
          fontSize: '0.85rem',
          lineHeight: '1.6',
          color: '#e2e8f0',
          maxHeight: '200px',
          overflowY: 'auto',
          fontFamily: 'Inter, system-ui, sans-serif',
          scrollBehavior: 'smooth'
        }}
        // nosemgrep: typescript.react.security.audit.react-dangerouslysetinnerhtml.react-dangerouslysetinnerhtml
        dangerouslySetInnerHTML={{ __html: sanitizeHtml(formatText(fullText)) }}
      />
      
      {isStreaming && (
        <div style={{
          display: 'flex',
          alignItems: 'center',
          marginTop: '8px',
          padding: '6px 8px',
          backgroundColor: 'rgba(34, 197, 94, 0.1)',
          border: '1px solid rgba(34, 197, 94, 0.3)',
          borderRadius: '4px',
          fontSize: '0.75rem',
          color: '#22c55e'
        }}>
          <div style={{
            width: '6px',
            height: '6px',
            borderRadius: '50%',
            backgroundColor: '#22c55e',
            marginRight: '6px',
            animation: 'pulse 1s infinite'
          }} />
          Streaming live output...
        </div>
      )}
      
      <style jsx>{`
        .code-block {
          background-color: rgba(0, 0, 0, 0.6);
          border: 1px solid rgba(100, 116, 139, 0.3);
          border-radius: 6px;
          padding: 12px;
          margin: 8px 0;
          font-family: 'Monaco', 'Consolas', monospace;
          font-size: 0.8rem;
          overflow-x: auto;
        }
        
        .inline-code {
          background-color: rgba(100, 116, 139, 0.2);
          color: #fbbf24;
          padding: 2px 6px;
          border-radius: 4px;
          font-family: 'Monaco', 'Consolas', monospace;
          font-size: 0.85em;
        }
        
        .bullet-point {
          margin: 4px 0;
          padding-left: 12px;
          color: #cbd5e1;
        }
        
        .numbered-point {
          margin: 4px 0;
          padding-left: 16px;
          color: #cbd5e1;
          position: relative;
        }
        
        .numbered-point::before {
          content: counter(list-counter) '. ';
          counter-increment: list-counter;
          position: absolute;
          left: 0;
          color: ${getAgentColor(agentName)};
          font-weight: 600;
        }
        
        .json-block {
          background-color: rgba(0, 0, 0, 0.8);
          border: 1px solid rgba(34, 197, 94, 0.3);
          border-radius: 6px;
          padding: 12px;
          margin: 8px 0;
          font-family: 'Monaco', 'Consolas', monospace;
          font-size: 0.8rem;
          overflow-x: auto;
        }
        
        .code-lang {
          color: #10b981;
          font-size: 0.7rem;
          font-weight: 600;
          margin-bottom: 4px;
          text-transform: uppercase;
        }
        
        .bold-text {
          color: #fbbf24;
          font-weight: 700;
        }
        
        .italic-text {
          color: #a78bfa;
          font-style: italic;
        }
        
        .header-1, .header-2, .header-3 {
          color: ${getAgentColor(agentName)};
          font-weight: 700;
          margin: 12px 0 6px 0;
        }
        
        .header-1 { font-size: 1.2rem; }
        .header-2 { font-size: 1.1rem; }
        .header-3 { font-size: 1rem; }
        
        .link {
          color: #60a5fa;
          text-decoration: underline;
        }
        
        .aws-resource {
          color: #f97316;
          font-family: 'Monaco', 'Consolas', monospace;
          font-size: 0.85em;
          background-color: rgba(249, 115, 22, 0.1);
          padding: 1px 4px;
          border-radius: 3px;
        }
        
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.5; }
        }
      `}</style>
    </div>
  );
};

export default TokenRenderer;