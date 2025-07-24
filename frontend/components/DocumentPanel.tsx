import React, { useState, useRef } from 'react';

interface Document {
  document_id: string;
  document_name: string;
  upload_time: string;
  processing_status: string;
  page_count?: number;
  file_size?: number;
}

interface DocumentPanelProps {
  profileId: string;
  documents: Document[];
  processingStatus: Map<string, string>;
  onUpload: (file: File) => Promise<void>;
  uploading: boolean;
  selectedDocumentId?: string;
  onDocumentSelect?: (documentId: string) => void;
}

export const DocumentPanel: React.FC<DocumentPanelProps> = ({
  profileId,
  documents,
  processingStatus,
  onUpload,
  uploading,
  selectedDocumentId,
  onDocumentSelect
}) => {
  const [isExpanded, setIsExpanded] = useState(true);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const getFileIcon = (filename: string) => {
    const ext = filename.split('.').pop()?.toLowerCase();
    switch (ext) {
      case 'pdf':
        return (
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <path d="M4 2h8l2 2v10H4V2z" fill="#E74C3C" />
            <path d="M12 2v2h2" stroke="#C0392B" strokeWidth="1" fill="none" />
            <text x="8" y="11" fontSize="5" fill="white" textAnchor="middle" fontWeight="bold">PDF</text>
          </svg>
        );
      case 'doc':
      case 'docx':
        return (
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <path d="M4 2h8l2 2v10H4V2z" fill="#2B579A" />
            <path d="M12 2v2h2" stroke="#1B4477" strokeWidth="1" fill="none" />
            <text x="8" y="11" fontSize="4" fill="white" textAnchor="middle" fontWeight="bold">DOC</text>
          </svg>
        );
      case 'txt':
        return (
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <path d="M4 2h8l2 2v10H4V2z" fill="#95A5A6" />
            <path d="M12 2v2h2" stroke="#7F8C8D" strokeWidth="1" fill="none" />
            <path d="M6 7h4M6 9h4M6 11h3" stroke="white" strokeWidth="0.8" />
          </svg>
        );
      default:
        return (
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <path d="M4 2h8l2 2v10H4V2z" fill="#7F8C8D" />
            <path d="M12 2v2h2" stroke="#5D6D7E" strokeWidth="1" fill="none" />
          </svg>
        );
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return (
          <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
            <circle cx="6" cy="6" r="5" fill="#28a745" />
            <path d="M3.5 6L5.5 8L8.5 4" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        );
      case 'processing':
        return (
          <svg width="12" height="12" viewBox="0 0 12 12" className="animate-spin">
            <circle cx="6" cy="6" r="5" stroke="#007ACC" strokeWidth="1.5" fill="none" strokeDasharray="20" />
          </svg>
        );
      case 'failed':
        return (
          <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
            <circle cx="6" cy="6" r="5" fill="#dc3545" />
            <path d="M4 4L8 8M8 4L4 8" stroke="white" strokeWidth="1.5" strokeLinecap="round" />
          </svg>
        );
      default:
        return (
          <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
            <circle cx="6" cy="6" r="5" stroke="#6c757d" strokeWidth="1.5" fill="none" />
          </svg>
        );
    }
  };

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      await onUpload(file);
      // Reset input
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  return (
    <div 
      style={{
        width: isExpanded ? '260px' : '48px',
        backgroundColor: '#252526',
        borderRight: '1px solid #3e3e42',
        display: 'flex',
        flexDirection: 'column',
        transition: 'width 0.2s ease',
        fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
        fontSize: '13px',
        color: '#cccccc'
      }}
    >
      {/* Header */}
      <div 
        style={{
          height: '35px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0 8px',
          backgroundColor: '#252526',
          borderBottom: '1px solid #3e3e42',
          textTransform: 'uppercase',
          fontSize: '11px',
          fontWeight: 600,
          letterSpacing: '0.5px',
          color: '#cccccc'
        }}
      >
        {isExpanded ? (
          <>
            <span>Documents</span>
            <div style={{ display: 'flex', gap: '4px' }}>
              <button
                onClick={() => fileInputRef.current?.click()}
                disabled={uploading}
                style={{
                  background: 'none',
                  border: 'none',
                  color: uploading ? '#6c757d' : '#cccccc',
                  cursor: uploading ? 'not-allowed' : 'pointer',
                  padding: '4px',
                  display: 'flex',
                  alignItems: 'center',
                  opacity: uploading ? 0.5 : 1
                }}
                title="Upload document"
              >
                <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                  <path d="M14 2v12H2V2h12zm0-1H2c-.55 0-1 .45-1 1v12c0 .55.45 1 1 1h12c.55 0 1-.45 1-1V2c0-.55-.45-1-1-1z"/>
                  <path d="M8 4v8M4 8h8" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
                </svg>
              </button>
              <button
                onClick={() => setIsExpanded(false)}
                style={{
                  background: 'none',
                  border: 'none',
                  color: '#cccccc',
                  cursor: 'pointer',
                  padding: '4px',
                  display: 'flex',
                  alignItems: 'center'
                }}
                title="Collapse"
              >
                <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                  <path d="M6 4l4 4-4 4" stroke="currentColor" strokeWidth="1.5" fill="none" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
              </button>
            </div>
          </>
        ) : (
          <button
            onClick={() => setIsExpanded(true)}
            style={{
              background: 'none',
              border: 'none',
              color: '#cccccc',
              cursor: 'pointer',
              padding: '4px',
              margin: '0 auto',
              display: 'flex',
              alignItems: 'center'
            }}
            title="Expand"
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
              <path d="M10 4l-4 4 4 4" stroke="currentColor" strokeWidth="1.5" fill="none" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </button>
        )}
      </div>

      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf,.doc,.docx,.txt"
        onChange={handleFileSelect}
        style={{ display: 'none' }}
      />

      {isExpanded && (
        <>
          {/* Document Tree */}
          <div style={{ flex: 1, overflow: 'auto' }}>
            {documents.length === 0 ? (
              <div style={{
                padding: '20px 12px',
                textAlign: 'center',
                color: '#858585',
                fontSize: '12px'
              }}>
                <div style={{ marginBottom: '8px' }}>No documents yet</div>
                <div style={{ fontSize: '11px', opacity: 0.8 }}>
                  Click + to upload
                </div>
              </div>
            ) : (
              <div style={{ padding: '4px 0' }}>
                {documents.map((doc) => {
                  const currentStatus = processingStatus.get(doc.document_id) || doc.processing_status;
                  const isSelected = selectedDocumentId === doc.document_id;

                  return (
                    <div
                      key={doc.document_id}
                      onClick={() => onDocumentSelect?.(doc.document_id)}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        padding: '4px 8px 4px 20px',
                        cursor: 'pointer',
                        backgroundColor: isSelected ? '#37373d' : 'transparent',
                        color: isSelected ? '#ffffff' : '#cccccc',
                        position: 'relative'
                      }}
                      onMouseEnter={(e) => {
                        if (!isSelected) {
                          e.currentTarget.style.backgroundColor = '#2a2d2e';
                        }
                      }}
                      onMouseLeave={(e) => {
                        if (!isSelected) {
                          e.currentTarget.style.backgroundColor = 'transparent';
                        }
                      }}
                    >
                      {/* Selection indicator */}
                      {isSelected && (
                        <div style={{
                          position: 'absolute',
                          left: 0,
                          top: 0,
                          bottom: 0,
                          width: '2px',
                          backgroundColor: '#007ACC'
                        }} />
                      )}
                      
                      {/* File icon */}
                      <div style={{ marginRight: '6px', display: 'flex', alignItems: 'center' }}>
                        {getFileIcon(doc.document_name)}
                      </div>
                      
                      {/* File name */}
                      <div style={{ 
                        flex: 1, 
                        overflow: 'hidden', 
                        textOverflow: 'ellipsis', 
                        whiteSpace: 'nowrap',
                        fontSize: '13px'
                      }}>
                        {doc.document_name}
                      </div>
                      
                      {/* Status icon */}
                      <div style={{ marginLeft: '6px', display: 'flex', alignItems: 'center' }}>
                        {getStatusIcon(currentStatus)}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Footer */}
          {documents.length > 0 && (
            <div style={{
              padding: '6px 12px',
              borderTop: '1px solid #3e3e42',
              fontSize: '11px',
              color: '#858585',
              display: 'flex',
              justifyContent: 'space-between'
            }}>
              <span>{documents.length} document{documents.length !== 1 ? 's' : ''}</span>
              <span>
                {documents.filter(d => (processingStatus.get(d.document_id) || d.processing_status) === 'completed').length} ready
              </span>
            </div>
          )}
        </>
      )}
    </div>
  );
};
