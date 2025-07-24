import React from 'react';
import ReactMarkdown from 'react-markdown';
import markdownStyles from '../styles/markdownContent.module.css';

interface DocumentViewerProps {
  documentUrl: string;
  fileName?: string;
  content?: string;
}

export const DocumentViewer: React.FC<DocumentViewerProps> = ({ 
  documentUrl, 
  fileName = 'document.docx',
  content 
}) => {
  return (
    <div style={{ height: '600px', width: '100%' }}>
      <div style={{ 
        backgroundColor: '#f0f0f0', 
        padding: '1rem', 
        borderRadius: '4px', 
        marginBottom: '1rem',
        textAlign: 'center'
      }}>
        <p style={{ margin: '0 0 0.5rem 0', fontSize: '0.9rem' }}>📄 Word Document</p>
        <a 
          href={documentUrl} 
          download={fileName}
          style={{
            backgroundColor: '#ff6b35',
            color: 'white',
            padding: '0.5rem 1rem',
            textDecoration: 'none',
            borderRadius: '4px',
            fontSize: '0.9rem'
          }}
        >
          📥 Download {fileName}
        </a>
      </div>
      
      {content && (
        <div className={markdownStyles['markdown-content']} style={{
          backgroundColor: '#f8f8f8',
          border: '1px solid #ddd',
          borderRadius: '4px',
          padding: '1rem',
          height: 'calc(100% - 100px)',
          overflowY: 'auto',
          fontSize: '0.9rem',
          lineHeight: 1.6
        }}>
          <h4 style={{ color: '#ff6b35', marginBottom: '1rem' }}>📝 Document Content</h4>
          <ReactMarkdown>{content}</ReactMarkdown>
        </div>
      )}
    </div>
  );
};

export default DocumentViewer;


