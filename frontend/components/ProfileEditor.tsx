import { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import markdownStyles from '../styles/markdownContent.module.css';

interface ValidationError {
  line?: number;
  section?: string;
  message: string;
  severity: 'error' | 'warning' | 'info';
}

interface DocumentReference {
  field: string;
  document_id: string;
  document_name: string;
  page_number: number;
  section: string;
  confidence: number;
  user_edited?: boolean;
  original_value?: string;
}

interface ProfileEditorProps {
  profileContent: string;
  onSave: (content: string) => void;
  onPreview?: () => void;
  validationErrors?: ValidationError[];
  readOnly?: boolean;
  profileName?: string;
  documentReferences?: DocumentReference[];
  onFieldEdit?: (field: string, newValue: string, originalValue: string) => void;
}

// Organization profile template structure
const PROFILE_TEMPLATE = `# Organization Profile: [Organization Name]

## Basic Information
- **Organization Name**: 
- **Industry**: 
- **Size**: 
- **Primary Regions**: 
- **Business Model**: 

## Regulatory Environment
- **Primary Regulations**: 
- **Compliance Frameworks**: 
- **Audit Requirements**: 
- **Data Residency Requirements**: 

## Risk Profile
- **Risk Appetite**: 
- **Business Criticality Factors**: 
- **Data Classification Levels**: 
- **Threat Landscape**: 

## Security Maturity
- **Current Security Level**: 
- **Existing Controls**: 
- **Security Tools**: 
- **Governance Structure**: 

## Technology Environment
- **Cloud Platforms**: 
- **Infrastructure Type**: 
- **Data Storage**: 
- **Integration Requirements**: 

## Business Context
- **Key Business Processes**: 
- **Stakeholder Requirements**: 
- **Budget Constraints**: 
- **Timeline Considerations**: 
`;

export default function ProfileEditor({
  profileContent,
  onSave,
  onPreview,
  validationErrors = [],
  readOnly = false,
  profileName,
  documentReferences = [],
  onFieldEdit
}: ProfileEditorProps) {
  const [content, setContent] = useState(profileContent || PROFILE_TEMPLATE);
  const [showPreview, setShowPreview] = useState(false);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [showDocumentReferences, setShowDocumentReferences] = useState(true);
  const [editedFields, setEditedFields] = useState<Set<string>>(new Set());

  useEffect(() => {
    setContent(profileContent || PROFILE_TEMPLATE);
    setHasUnsavedChanges(false);
  }, [profileContent]);

  const handleContentChange = (newContent: string) => {
    setContent(newContent);
    setHasUnsavedChanges(newContent !== profileContent);
    
    // Track edits to document-sourced fields
    if (onFieldEdit && documentReferences.length > 0) {
      documentReferences.forEach(ref => {
        // Check if this field's value changed in the content
        // Escape special regex characters and use hardcoded pattern
        const escapedField = ref.field.replace(/[.*+?^${}()|[\]\\]/g, '\\$&').replace(/_/g, ' ');
        // nosemgrep: javascript.lang.security.audit.detect-non-literal-regexp.detect-non-literal-regexp
        const fieldPattern = new RegExp(`\\*\\*${escapedField}\\*\\*:\\s*(.+?)(?=\\n|$)`, 'i');
        const oldMatch = profileContent.match(fieldPattern);
        const newMatch = newContent.match(fieldPattern);
        
        if (oldMatch && newMatch && oldMatch[1] !== newMatch[1] && !editedFields.has(ref.field)) {
          // Field was edited
          setEditedFields(prev => new Set(prev).add(ref.field));
          onFieldEdit(ref.field, newMatch[1].trim(), oldMatch[1].trim());
        }
      });
    }
  };

  const handleSave = async () => {
    if (readOnly || !hasUnsavedChanges) return;
    
    setIsSaving(true);
    try {
      await onSave(content);
      setHasUnsavedChanges(false);
    } catch (error) {
      console.error('Error saving profile:', error);
    } finally {
      setIsSaving(false);
    }
  };

  const handlePreview = () => {
    setShowPreview(!showPreview);
    if (onPreview) {
      onPreview();
    }
  };

  const validateContent = (content: string): ValidationError[] => {
    const errors: ValidationError[] = [];
    const lines = content.split('\n');
    
    // Check for required sections
    const requiredSections = [
      'Basic Information',
      'Regulatory Environment', 
      'Risk Profile',
      'Security Maturity',
      'Technology Environment',
      'Business Context'
    ];

    requiredSections.forEach(section => {
      const sectionExists = lines.some(line => 
        line.includes(`## ${section}`) || line.includes(`# ${section}`)
      );
      
      if (!sectionExists) {
        errors.push({
          section,
          message: `Missing required section: ${section}`,
          severity: 'error'
        });
      }
    });

    // Check for empty required fields
    const requiredFields = [
      'Organization Name',
      'Industry',
      'Size',
      'Primary Regions'
    ];

    requiredFields.forEach(field => {
      // Escape special regex characters to prevent ReDoS
      const escapedField = field.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
      // nosemgrep: javascript.lang.security.audit.detect-non-literal-regexp.detect-non-literal-regexp
      const fieldPattern = new RegExp(`\\*\\*${escapedField}\\*\\*:\\s*$`, 'm');
      if (fieldPattern.test(content)) {
        errors.push({
          section: 'Basic Information',
          message: `${field} is required but appears to be empty`,
          severity: 'warning'
        });
      }
    });

    // Check for proper markdown structure
    const hasMainTitle = lines.some(line => line.startsWith('# Organization Profile:'));
    if (!hasMainTitle) {
      errors.push({
        line: 1,
        message: 'Profile should start with "# Organization Profile: [Name]"',
        severity: 'error'
      });
    }

    return errors;
  };

  const currentErrors = [...validationErrors, ...validateContent(content)];
  const errorCount = currentErrors.filter(e => e.severity === 'error').length;
  const warningCount = currentErrors.filter(e => e.severity === 'warning').length;

  const insertTemplate = (templateText: string) => {
    const textarea = document.getElementById('profile-editor') as HTMLTextAreaElement;
    if (textarea) {
      const start = textarea.selectionStart;
      const end = textarea.selectionEnd;
      const newContent = content.substring(0, start) + templateText + content.substring(end);
      handleContentChange(newContent);
      
      // Restore cursor position
      setTimeout(() => {
        textarea.focus();
        textarea.setSelectionRange(start + templateText.length, start + templateText.length);
      }, 0);
    }
  };

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      height: '100%',
      backgroundColor: '#ffffff',
      border: '2px solid #ff6b35',
      borderRadius: '8px',
      overflow: 'hidden'
    }}>
      {/* Header */}
      <div style={{
        padding: '1rem',
        backgroundColor: '#ff6b35',
        color: 'white',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center'
      }}>
        <h2 style={{ margin: 0, fontSize: '1.2rem' }}>
          {profileName ? `Edit: ${profileName}` : 'Organization Profile Editor'}
        </h2>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          {hasUnsavedChanges && (
            <span style={{ fontSize: '0.9rem', fontStyle: 'italic' }}>
              Unsaved changes
            </span>
          )}
          {documentReferences.length > 0 && (
            <button
              onClick={() => setShowDocumentReferences(!showDocumentReferences)}
              style={{
                backgroundColor: showDocumentReferences ? 'white' : 'transparent',
                color: showDocumentReferences ? '#0066cc' : 'white',
                border: '1px solid white',
                borderRadius: '4px',
                padding: '0.25rem 0.75rem',
                fontSize: '0.9rem',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '0.25rem'
              }}
              title={showDocumentReferences ? 'Hide document sources' : 'Show document sources'}
            >
              📄 {documentReferences.length}
            </button>
          )}
          <button
            onClick={handlePreview}
            style={{
              backgroundColor: 'transparent',
              color: 'white',
              border: '1px solid white',
              borderRadius: '4px',
              padding: '0.25rem 0.75rem',
              fontSize: '0.9rem',
              cursor: 'pointer'
            }}
          >
            {showPreview ? 'Edit' : 'Preview'}
          </button>
          <button
            onClick={handleSave}
            disabled={readOnly || !hasUnsavedChanges || isSaving}
            style={{
              backgroundColor: readOnly || !hasUnsavedChanges ? 'rgba(255,255,255,0.3)' : 'white',
              color: readOnly || !hasUnsavedChanges ? 'rgba(255,255,255,0.7)' : '#ff6b35',
              border: 'none',
              borderRadius: '4px',
              padding: '0.25rem 0.75rem',
              fontSize: '0.9rem',
              cursor: readOnly || !hasUnsavedChanges ? 'not-allowed' : 'pointer',
              fontWeight: '600'
            }}
          >
            {isSaving ? 'Saving...' : 'Save'}
          </button>
        </div>
      </div>

      {/* Validation Status */}
      {currentErrors.length > 0 && (
        <div style={{
          padding: '0.75rem 1rem',
          backgroundColor: errorCount > 0 ? '#f8d7da' : '#fff3cd',
          color: errorCount > 0 ? '#721c24' : '#856404',
          borderBottom: '1px solid #e9ecef',
          fontSize: '0.9rem'
        }}>
          {errorCount > 0 && `${errorCount} error${errorCount !== 1 ? 's' : ''}`}
          {errorCount > 0 && warningCount > 0 && ', '}
          {warningCount > 0 && `${warningCount} warning${warningCount !== 1 ? 's' : ''}`}
          {' found in profile'}
        </div>
      )}

      {/* Main Content Area */}
      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        {/* Editor Panel */}
        {!showPreview && (
          <div style={{
            flex: 1,
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden'
          }}>
            {/* Toolbar */}
            <div style={{
              padding: '0.5rem 1rem',
              backgroundColor: '#f8f9fa',
              borderBottom: '1px solid #e9ecef',
              display: 'flex',
              gap: '0.5rem',
              flexWrap: 'wrap'
            }}>
              <button
                onClick={() => insertTemplate('\n## New Section\n- **Field**: \n')}
                style={{
                  padding: '0.25rem 0.5rem',
                  fontSize: '0.8rem',
                  backgroundColor: 'white',
                  border: '1px solid #ced4da',
                  borderRadius: '3px',
                  cursor: 'pointer'
                }}
              >
                Add Section
              </button>
              <button
                onClick={() => insertTemplate('- **New Field**: ')}
                style={{
                  padding: '0.25rem 0.5rem',
                  fontSize: '0.8rem',
                  backgroundColor: 'white',
                  border: '1px solid #ced4da',
                  borderRadius: '3px',
                  cursor: 'pointer'
                }}
              >
                Add Field
              </button>
              <button
                onClick={() => insertTemplate('**Bold Text**')}
                style={{
                  padding: '0.25rem 0.5rem',
                  fontSize: '0.8rem',
                  backgroundColor: 'white',
                  border: '1px solid #ced4da',
                  borderRadius: '3px',
                  cursor: 'pointer'
                }}
              >
                Bold
              </button>
              <button
                onClick={() => insertTemplate('*Italic Text*')}
                style={{
                  padding: '0.25rem 0.5rem',
                  fontSize: '0.8rem',
                  backgroundColor: 'white',
                  border: '1px solid #ced4da',
                  borderRadius: '3px',
                  cursor: 'pointer'
                }}
              >
                Italic
              </button>
            </div>

            {/* Text Editor */}
            <textarea
              id="profile-editor"
              value={content}
              onChange={(e) => handleContentChange(e.target.value)}
              readOnly={readOnly}
              style={{
                flex: 1,
                padding: '1rem',
                border: 'none',
                resize: 'none',
                fontFamily: 'Monaco, Menlo, "Ubuntu Mono", monospace',
                fontSize: '0.9rem',
                lineHeight: '1.5',
                backgroundColor: readOnly ? '#f8f9fa' : 'white',
                color: '#212529',
                outline: 'none'
              }}
              placeholder="Enter your organization profile content in Markdown format..."
            />
          </div>
        )}

        {/* Preview Panel */}
        {showPreview && (
          <div style={{
            flex: 1,
            padding: '1rem',
            overflow: 'auto',
            backgroundColor: '#f8f9fa'
          }}>
            <div className={markdownStyles['markdown-content']}>
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {content}
              </ReactMarkdown>
            </div>
          </div>
        )}

        {/* Document References Panel */}
        {documentReferences.length > 0 && showDocumentReferences && (
          <div style={{
            width: '320px',
            borderLeft: '1px solid #e9ecef',
            backgroundColor: '#f8f9fa',
            overflow: 'auto',
            display: 'flex',
            flexDirection: 'column'
          }}>
            <div style={{
              padding: '1rem',
              borderBottom: '1px solid #e9ecef',
              backgroundColor: '#ffffff',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center'
            }}>
              <h4 style={{ margin: 0, fontSize: '1rem', color: '#0066cc' }}>
                📄 Document Sources
              </h4>
              <button
                onClick={() => setShowDocumentReferences(false)}
                style={{
                  background: 'none',
                  border: 'none',
                  color: '#6c757d',
                  cursor: 'pointer',
                  fontSize: '1.2rem',
                  padding: '0 0.5rem'
                }}
                title="Hide document references"
              >
                ×
              </button>
            </div>
            <div style={{ padding: '0.5rem', flex: 1, overflow: 'auto' }}>
              <div style={{
                fontSize: '0.75rem',
                color: '#6c757d',
                padding: '0.5rem',
                marginBottom: '0.5rem'
              }}>
                {documentReferences.length} field{documentReferences.length !== 1 ? 's' : ''} extracted from documents
              </div>
              {documentReferences.map((ref, index) => (
                <div
                  key={index}
                  style={{
                    padding: '0.75rem',
                    margin: '0.5rem',
                    backgroundColor: 'white',
                    border: ref.user_edited ? '2px solid #ffc107' : '1px solid #b3d9ff',
                    borderRadius: '4px',
                    fontSize: '0.85rem'
                  }}
                >
                  {/* Field Name */}
                  <div style={{
                    fontWeight: '600',
                    color: '#212529',
                    marginBottom: '0.5rem',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.5rem'
                  }}>
                    <span>{ref.field.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}</span>
                    {ref.user_edited && (
                      <span style={{
                        fontSize: '0.7rem',
                        padding: '0.1rem 0.4rem',
                        backgroundColor: '#fff3cd',
                        color: '#856404',
                        borderRadius: '8px',
                        border: '1px solid #ffeaa7'
                      }}>
                        Edited
                      </span>
                    )}
                  </div>
                  
                  {/* Document Source */}
                  <div style={{
                    fontSize: '0.75rem',
                    color: '#495057',
                    marginBottom: '0.5rem',
                    padding: '0.5rem',
                    backgroundColor: '#f8f9fa',
                    borderRadius: '3px'
                  }}>
                    <div style={{ marginBottom: '0.25rem' }}>
                      <strong>Source:</strong> {ref.document_name}
                    </div>
                    <div style={{ marginBottom: '0.25rem' }}>
                      <strong>Page:</strong> {ref.page_number} • <strong>Section:</strong> {ref.section}
                    </div>
                    <div>
                      <strong>Confidence:</strong>{' '}
                      <span style={{
                        color: ref.confidence >= 0.8 ? '#28a745' : ref.confidence >= 0.6 ? '#ffc107' : '#dc3545'
                      }}>
                        {Math.round(ref.confidence * 100)}%
                      </span>
                    </div>
                  </div>
                  
                  {/* Edit Indicator */}
                  {ref.user_edited && ref.original_value && (
                    <div style={{
                      fontSize: '0.7rem',
                      color: '#6c757d',
                      padding: '0.5rem',
                      backgroundColor: '#fff3cd',
                      borderRadius: '3px',
                      marginTop: '0.5rem'
                    }}>
                      <div style={{ fontWeight: '600', marginBottom: '0.25rem' }}>
                        Original value:
                      </div>
                      <div style={{ fontStyle: 'italic' }}>
                        {ref.original_value}
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
        
        {/* Validation Errors Panel */}
        {currentErrors.length > 0 && (
          <div style={{
            width: '300px',
            borderLeft: '1px solid #e9ecef',
            backgroundColor: '#f8f9fa',
            overflow: 'auto'
          }}>
            <div style={{
              padding: '1rem',
              borderBottom: '1px solid #e9ecef',
              backgroundColor: '#ffffff'
            }}>
              <h4 style={{ margin: 0, fontSize: '1rem', color: '#ff6b35' }}>
                Validation Issues
              </h4>
            </div>
            <div style={{ padding: '0.5rem' }}>
              {currentErrors.map((error, index) => (
                <div
                  key={index}
                  style={{
                    padding: '0.75rem',
                    margin: '0.5rem',
                    backgroundColor: 'white',
                    border: `1px solid ${
                      error.severity === 'error' ? '#dc3545' : 
                      error.severity === 'warning' ? '#ffc107' : '#17a2b8'
                    }`,
                    borderRadius: '4px',
                    fontSize: '0.85rem'
                  }}
                >
                  <div style={{
                    fontWeight: '600',
                    color: error.severity === 'error' ? '#dc3545' : 
                           error.severity === 'warning' ? '#856404' : '#0c5460',
                    marginBottom: '0.25rem'
                  }}>
                    {error.severity.toUpperCase()}
                    {error.section && ` - ${error.section}`}
                    {error.line && ` (Line ${error.line})`}
                  </div>
                  <div style={{ color: '#495057' }}>
                    {error.message}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Footer */}
      <div style={{
        padding: '0.5rem 1rem',
        backgroundColor: '#f8f9fa',
        borderTop: '1px solid #e9ecef',
        fontSize: '0.8rem',
        color: '#6c757d',
        display: 'flex',
        justifyContent: 'space-between'
      }}>
        <span>
          {content.split('\n').length} lines, {content.length} characters
        </span>
        <span>
          Markdown format • Use **bold** and *italic* for emphasis
        </span>
      </div>
    </div>
  );
}