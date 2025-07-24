import { useState, useEffect, useRef } from 'react';

export interface TranscriptEntry {
  id: string;
  text: string;
  timestamp: Date;
  isPartial: boolean;
  confidence?: number;
  speaker: 'user' | 'assistant';
  audioUrl?: string;
  isEditable?: boolean;
  originalText?: string;
}

interface TranscriptDisplayProps {
  entries: TranscriptEntry[];
  showPartialResults?: boolean;
  allowEditing?: boolean;
  showConfidence?: boolean;
  showTimestamps?: boolean;
  onEntryEdit?: (id: string, newText: string) => void;
  onPlayAudio?: (audioUrl: string) => void;
  className?: string;
  style?: React.CSSProperties;
}

export default function TranscriptDisplay({
  entries,
  showPartialResults = true,
  allowEditing = true,
  showConfidence = true,
  showTimestamps = true,
  onEntryEdit,
  onPlayAudio,
  className,
  style
}: TranscriptDisplayProps) {
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editText, setEditText] = useState('');
  const scrollRef = useRef<HTMLDivElement>(null);
  const [autoScroll, setAutoScroll] = useState(true);

  // Auto-scroll to bottom when new entries are added
  useEffect(() => {
    if (autoScroll && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [entries, autoScroll]);

  // Check if user has scrolled up to disable auto-scroll
  const handleScroll = () => {
    if (scrollRef.current) {
      const { scrollTop, scrollHeight, clientHeight } = scrollRef.current;
      const isAtBottom = scrollTop + clientHeight >= scrollHeight - 10;
      setAutoScroll(isAtBottom);
    }
  };

  const startEditing = (entry: TranscriptEntry) => {
    if (!allowEditing || entry.isPartial) return;
    
    setEditingId(entry.id);
    setEditText(entry.text);
  };

  const saveEdit = () => {
    if (editingId && onEntryEdit && editText.trim() !== '') {
      onEntryEdit(editingId, editText.trim());
    }
    setEditingId(null);
    setEditText('');
  };

  const cancelEdit = () => {
    setEditingId(null);
    setEditText('');
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      saveEdit();
    } else if (e.key === 'Escape') {
      cancelEdit();
    }
  };

  const formatTimestamp = (timestamp: Date): string => {
    return timestamp.toLocaleTimeString([], { 
      hour: '2-digit', 
      minute: '2-digit', 
      second: '2-digit' 
    });
  };

  const getConfidenceColor = (confidence: number): string => {
    if (confidence >= 0.8) return '#28a745'; // Green
    if (confidence >= 0.6) return '#ffc107'; // Yellow
    return '#dc3545'; // Red
  };

  const getConfidenceText = (confidence: number): string => {
    if (confidence >= 0.8) return 'High';
    if (confidence >= 0.6) return 'Medium';
    return 'Low';
  };

  // Filter entries based on showPartialResults setting
  const displayEntries = showPartialResults 
    ? entries 
    : entries.filter(entry => !entry.isPartial);

  return (
    <div 
      className={className}
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        backgroundColor: '#f8f9fa',
        border: '1px solid #e9ecef',
        borderRadius: '8px',
        overflow: 'hidden',
        ...style
      }}
    >
      {/* Header */}
      <div style={{
        padding: '1rem',
        backgroundColor: '#ffffff',
        borderBottom: '1px solid #e9ecef',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center'
      }}>
        <h3 style={{ margin: 0, fontSize: '1.1rem', color: '#333' }}>
          Conversation Transcript
        </h3>
        <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
          <span style={{ fontSize: '0.9rem', color: '#6c757d' }}>
            {displayEntries.length} entries
          </span>
          {!autoScroll && (
            <button
              onClick={() => {
                setAutoScroll(true);
                if (scrollRef.current) {
                  scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
                }
              }}
              style={{
                backgroundColor: '#007bff',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                padding: '0.25rem 0.5rem',
                fontSize: '0.8rem',
                cursor: 'pointer'
              }}
            >
              ↓ Scroll to bottom
            </button>
          )}
        </div>
      </div>

      {/* Transcript entries */}
      <div
        ref={scrollRef}
        onScroll={handleScroll}
        style={{
          flex: 1,
          padding: '1rem',
          overflowY: 'auto',
          backgroundColor: '#ffffff'
        }}
      >
        {displayEntries.length === 0 ? (
          <div style={{
            textAlign: 'center',
            color: '#6c757d',
            padding: '2rem',
            fontStyle: 'italic'
          }}>
            No transcript entries yet. Start speaking to see your conversation here.
          </div>
        ) : (
          displayEntries.map((entry) => (
            <div
              key={entry.id}
              style={{
                marginBottom: '1rem',
                padding: '1rem',
                backgroundColor: entry.isPartial ? '#fff3cd' : '#ffffff',
                border: `1px solid ${entry.isPartial ? '#ffeaa7' : '#e9ecef'}`,
                borderRadius: '8px',
                borderLeft: `4px solid ${entry.speaker === 'user' ? '#ff6b35' : '#28a745'}`,
                opacity: entry.isPartial ? 0.8 : 1,
                transition: 'all 0.3s ease'
              }}
            >
              {/* Entry header */}
              <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                marginBottom: '0.5rem'
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <span style={{
                    fontSize: '0.9rem',
                    fontWeight: '600',
                    color: entry.speaker === 'user' ? '#ff6b35' : '#28a745'
                  }}>
                    {entry.speaker === 'user' ? '👤 You' : '🤖 Assistant'}
                  </span>
                  
                  {entry.isPartial && (
                    <span style={{
                      fontSize: '0.8rem',
                      color: '#856404',
                      backgroundColor: '#fff3cd',
                      padding: '0.1rem 0.3rem',
                      borderRadius: '3px',
                      border: '1px solid #ffeaa7'
                    }}>
                      Partial
                    </span>
                  )}

                  {showConfidence && entry.confidence !== undefined && (
                    <span style={{
                      fontSize: '0.8rem',
                      color: getConfidenceColor(entry.confidence),
                      fontWeight: '500'
                    }}>
                      {getConfidenceText(entry.confidence)} ({Math.round(entry.confidence * 100)}%)
                    </span>
                  )}
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  {showTimestamps && (
                    <span style={{
                      fontSize: '0.8rem',
                      color: '#6c757d'
                    }}>
                      {formatTimestamp(entry.timestamp)}
                    </span>
                  )}

                  {/* Audio playback button */}
                  {entry.audioUrl && onPlayAudio && (
                    <button
                      onClick={() => onPlayAudio(entry.audioUrl!)}
                      style={{
                        backgroundColor: 'transparent',
                        border: '1px solid #6c757d',
                        borderRadius: '4px',
                        padding: '0.2rem 0.4rem',
                        fontSize: '0.8rem',
                        cursor: 'pointer',
                        color: '#6c757d'
                      }}
                      title="Play audio"
                    >
                      🔊
                    </button>
                  )}

                  {/* Edit button */}
                  {allowEditing && !entry.isPartial && entry.speaker === 'user' && (
                    <button
                      onClick={() => startEditing(entry)}
                      style={{
                        backgroundColor: 'transparent',
                        border: '1px solid #6c757d',
                        borderRadius: '4px',
                        padding: '0.2rem 0.4rem',
                        fontSize: '0.8rem',
                        cursor: 'pointer',
                        color: '#6c757d'
                      }}
                      title="Edit transcript"
                    >
                      ✏️
                    </button>
                  )}
                </div>
              </div>

              {/* Entry content */}
              <div style={{ marginTop: '0.5rem' }}>
                {editingId === entry.id ? (
                  <div>
                    <textarea
                      value={editText}
                      onChange={(e) => setEditText(e.target.value)}
                      onKeyDown={handleKeyPress}
                      style={{
                        width: '100%',
                        minHeight: '60px',
                        padding: '0.5rem',
                        border: '1px solid #ced4da',
                        borderRadius: '4px',
                        fontSize: '0.9rem',
                        fontFamily: 'inherit',
                        resize: 'vertical'
                      }}
                      autoFocus
                    />
                    <div style={{
                      marginTop: '0.5rem',
                      display: 'flex',
                      gap: '0.5rem'
                    }}>
                      <button
                        onClick={saveEdit}
                        style={{
                          backgroundColor: '#28a745',
                          color: 'white',
                          border: 'none',
                          borderRadius: '4px',
                          padding: '0.3rem 0.6rem',
                          fontSize: '0.8rem',
                          cursor: 'pointer'
                        }}
                      >
                        Save
                      </button>
                      <button
                        onClick={cancelEdit}
                        style={{
                          backgroundColor: '#6c757d',
                          color: 'white',
                          border: 'none',
                          borderRadius: '4px',
                          padding: '0.3rem 0.6rem',
                          fontSize: '0.8rem',
                          cursor: 'pointer'
                        }}
                      >
                        Cancel
                      </button>
                    </div>
                    {entry.originalText && entry.originalText !== editText && (
                      <div style={{
                        marginTop: '0.5rem',
                        fontSize: '0.8rem',
                        color: '#6c757d',
                        fontStyle: 'italic'
                      }}>
                        Original: "{entry.originalText}"
                      </div>
                    )}
                  </div>
                ) : (
                  <div>
                    <p style={{
                      margin: 0,
                      fontSize: '0.95rem',
                      lineHeight: '1.4',
                      color: '#333',
                      whiteSpace: 'pre-wrap',
                      wordBreak: 'break-word'
                    }}>
                      {entry.text}
                    </p>
                    
                    {/* Show if text was edited */}
                    {entry.originalText && entry.originalText !== entry.text && (
                      <div style={{
                        marginTop: '0.5rem',
                        fontSize: '0.8rem',
                        color: '#6c757d',
                        fontStyle: 'italic'
                      }}>
                        (Edited from: "{entry.originalText}")
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          ))
        )}
      </div>

      {/* Footer with controls */}
      <div style={{
        padding: '0.5rem 1rem',
        backgroundColor: '#f8f9fa',
        borderTop: '1px solid #e9ecef',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center'
      }}>
        <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
          <label style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.3rem',
            fontSize: '0.9rem',
            color: '#6c757d',
            cursor: 'pointer'
          }}>
            <input
              type="checkbox"
              checked={showPartialResults}
              onChange={(e) => {
                // This would need to be passed as a prop to control from parent
                console.log('Toggle partial results:', e.target.checked);
              }}
              style={{ margin: 0 }}
            />
            Show partial results
          </label>
        </div>

        <div style={{
          fontSize: '0.8rem',
          color: '#6c757d'
        }}>
          {allowEditing && 'Click ✏️ to edit • '}
          {entries.some(e => e.audioUrl) && 'Click 🔊 to play audio'}
        </div>
      </div>
    </div>
  );
}

// Export utility functions for creating transcript entries
export const createTranscriptEntry = (
  text: string,
  speaker: 'user' | 'assistant',
  options: {
    isPartial?: boolean;
    confidence?: number;
    audioUrl?: string;
    isEditable?: boolean;
  } = {}
): TranscriptEntry => ({
  id: `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
  text,
  timestamp: new Date(),
  speaker,
  isPartial: options.isPartial || false,
  confidence: options.confidence,
  audioUrl: options.audioUrl,
  isEditable: options.isEditable !== false, // Default to true
  originalText: text
});

export const updateTranscriptEntry = (
  entry: TranscriptEntry,
  updates: Partial<TranscriptEntry>
): TranscriptEntry => ({
  ...entry,
  ...updates,
  // Preserve original text when editing
  originalText: updates.text && updates.text !== entry.text 
    ? entry.originalText || entry.text 
    : entry.originalText
});