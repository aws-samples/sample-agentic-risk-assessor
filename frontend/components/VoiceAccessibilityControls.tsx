import { useState, useEffect, useRef } from 'react';

interface VoiceAccessibilityControlsProps {
  isVoiceMode: boolean;
  isListening: boolean;
  isPlaying: boolean;
  currentVolume: number;
  playbackSpeed: number;
  onVolumeChange: (volume: number) => void;
  onSpeedChange: (speed: number) => void;
  onPause: () => void;
  onResume: () => void;
  onStop: () => void;
  onSkipForward: () => void;
  onSkipBackward: () => void;
  onToggleListening: () => void;
  className?: string;
}

export default function VoiceAccessibilityControls({
  isVoiceMode,
  isListening,
  isPlaying,
  currentVolume,
  playbackSpeed,
  onVolumeChange,
  onSpeedChange,
  onPause,
  onResume,
  onStop,
  onSkipForward,
  onSkipBackward,
  onToggleListening,
  className
}: VoiceAccessibilityControlsProps) {
  const [showControls, setShowControls] = useState(false);
  const [keyboardShortcutsEnabled, setKeyboardShortcutsEnabled] = useState(true);
  const controlsRef = useRef<HTMLDivElement>(null);

  // Keyboard shortcuts
  useEffect(() => {
    if (!keyboardShortcutsEnabled || !isVoiceMode) return;

    const handleKeyDown = (event: KeyboardEvent) => {
      // Only handle shortcuts when not typing in input fields
      if (event.target instanceof HTMLInputElement || 
          event.target instanceof HTMLTextAreaElement) {
        return;
      }

      // Check for modifier keys to avoid conflicts
      if (event.ctrlKey || event.metaKey) {
        switch (event.key.toLowerCase()) {
          case 'space':
            event.preventDefault();
            if (isPlaying) {
              onPause();
            } else {
              onResume();
            }
            break;
          case 'm':
            event.preventDefault();
            onToggleListening();
            break;
          case 's':
            event.preventDefault();
            onStop();
            break;
          case 'arrowleft':
            event.preventDefault();
            onSkipBackward();
            break;
          case 'arrowright':
            event.preventDefault();
            onSkipForward();
            break;
          case 'arrowup':
            event.preventDefault();
            onVolumeChange(Math.min(1, currentVolume + 0.1));
            break;
          case 'arrowdown':
            event.preventDefault();
            onVolumeChange(Math.max(0, currentVolume - 0.1));
            break;
        }
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [
    keyboardShortcutsEnabled,
    isVoiceMode,
    isPlaying,
    currentVolume,
    onPause,
    onResume,
    onStop,
    onSkipForward,
    onSkipBackward,
    onToggleListening,
    onVolumeChange
  ]);

  // Auto-hide controls after inactivity
  useEffect(() => {
    let timeout: NodeJS.Timeout;
    
    if (showControls) {
      timeout = setTimeout(() => {
        setShowControls(false);
      }, 5000); // Hide after 5 seconds of inactivity
    }

    return () => {
      if (timeout) clearTimeout(timeout);
    };
  }, [showControls]);

  if (!isVoiceMode) return null;

  return (
    <div className={className}>
      {/* Floating Controls Toggle */}
      <button
        onClick={() => setShowControls(!showControls)}
        style={{
          position: 'fixed',
          bottom: '20px',
          right: '20px',
          width: '60px',
          height: '60px',
          borderRadius: '50%',
          backgroundColor: '#ff6b35',
          color: 'white',
          border: 'none',
          fontSize: '1.5rem',
          cursor: 'pointer',
          boxShadow: '0 4px 12px rgba(0, 0, 0, 0.15)',
          zIndex: 1000,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          transition: 'all 0.3s ease'
        }}
        title="Voice Controls (Ctrl+H)"
        aria-label="Toggle voice accessibility controls"
      >
        🎛️
      </button>

      {/* Floating Controls Panel */}
      {showControls && (
        <div
          ref={controlsRef}
          style={{
            position: 'fixed',
            bottom: '90px',
            right: '20px',
            backgroundColor: 'white',
            borderRadius: '12px',
            padding: '1.5rem',
            boxShadow: '0 8px 24px rgba(0, 0, 0, 0.15)',
            zIndex: 1000,
            minWidth: '300px',
            border: '1px solid #e9ecef'
          }}
          onMouseEnter={() => setShowControls(true)}
          onMouseLeave={() => setShowControls(false)}
        >
          {/* Header */}
          <div style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: '1rem',
            paddingBottom: '0.5rem',
            borderBottom: '1px solid #e9ecef'
          }}>
            <h4 style={{ margin: 0, color: '#333' }}>Voice Controls</h4>
            <button
              onClick={() => setShowControls(false)}
              style={{
                backgroundColor: 'transparent',
                border: 'none',
                fontSize: '1.2rem',
                cursor: 'pointer',
                color: '#6c757d'
              }}
              aria-label="Close controls"
            >
              ×
            </button>
          </div>

          {/* Status Indicators */}
          <div style={{
            display: 'flex',
            gap: '1rem',
            marginBottom: '1rem',
            padding: '0.5rem',
            backgroundColor: '#f8f9fa',
            borderRadius: '6px'
          }}>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.3rem',
              fontSize: '0.9rem'
            }}>
              <div style={{
                width: '8px',
                height: '8px',
                borderRadius: '50%',
                backgroundColor: isListening ? '#28a745' : '#6c757d'
              }} />
              <span>{isListening ? 'Listening' : 'Not Listening'}</span>
            </div>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.3rem',
              fontSize: '0.9rem'
            }}>
              <div style={{
                width: '8px',
                height: '8px',
                borderRadius: '50%',
                backgroundColor: isPlaying ? '#007bff' : '#6c757d'
              }} />
              <span>{isPlaying ? 'Playing' : 'Stopped'}</span>
            </div>
          </div>

          {/* Playback Controls */}
          <div style={{ marginBottom: '1rem' }}>
            <div style={{
              display: 'flex',
              justifyContent: 'center',
              gap: '0.5rem',
              marginBottom: '1rem'
            }}>
              <button
                onClick={onSkipBackward}
                style={{
                  backgroundColor: '#6c757d',
                  color: 'white',
                  border: 'none',
                  borderRadius: '6px',
                  padding: '0.5rem',
                  cursor: 'pointer',
                  fontSize: '1rem'
                }}
                title="Skip backward (Ctrl+←)"
                aria-label="Skip backward"
              >
                ⏪
              </button>
              
              {isPlaying ? (
                <button
                  onClick={onPause}
                  style={{
                    backgroundColor: '#ffc107',
                    color: 'white',
                    border: 'none',
                    borderRadius: '6px',
                    padding: '0.5rem 1rem',
                    cursor: 'pointer',
                    fontSize: '1rem'
                  }}
                  title="Pause (Ctrl+Space)"
                  aria-label="Pause playback"
                >
                  ⏸️
                </button>
              ) : (
                <button
                  onClick={onResume}
                  style={{
                    backgroundColor: '#28a745',
                    color: 'white',
                    border: 'none',
                    borderRadius: '6px',
                    padding: '0.5rem 1rem',
                    cursor: 'pointer',
                    fontSize: '1rem'
                  }}
                  title="Play (Ctrl+Space)"
                  aria-label="Resume playback"
                >
                  ▶️
                </button>
              )}
              
              <button
                onClick={onStop}
                style={{
                  backgroundColor: '#dc3545',
                  color: 'white',
                  border: 'none',
                  borderRadius: '6px',
                  padding: '0.5rem',
                  cursor: 'pointer',
                  fontSize: '1rem'
                }}
                title="Stop (Ctrl+S)"
                aria-label="Stop playback"
              >
                ⏹️
              </button>
              
              <button
                onClick={onSkipForward}
                style={{
                  backgroundColor: '#6c757d',
                  color: 'white',
                  border: 'none',
                  borderRadius: '6px',
                  padding: '0.5rem',
                  cursor: 'pointer',
                  fontSize: '1rem'
                }}
                title="Skip forward (Ctrl+→)"
                aria-label="Skip forward"
              >
                ⏩
              </button>
            </div>

            {/* Microphone Toggle */}
            <div style={{ textAlign: 'center', marginBottom: '1rem' }}>
              <button
                onClick={onToggleListening}
                style={{
                  backgroundColor: isListening ? '#dc3545' : '#28a745',
                  color: 'white',
                  border: 'none',
                  borderRadius: '6px',
                  padding: '0.5rem 1rem',
                  cursor: 'pointer',
                  fontSize: '0.9rem',
                  fontWeight: '500'
                }}
                title="Toggle microphone (Ctrl+M)"
                aria-label={isListening ? 'Stop listening' : 'Start listening'}
              >
                🎤 {isListening ? 'Stop Listening' : 'Start Listening'}
              </button>
            </div>
          </div>

          {/* Volume Control */}
          <div style={{ marginBottom: '1rem' }}>
            <label style={{
              display: 'block',
              marginBottom: '0.5rem',
              fontSize: '0.9rem',
              fontWeight: '500'
            }}>
              Volume: {Math.round(currentVolume * 100)}%
            </label>
            <input
              type="range"
              min="0"
              max="1"
              step="0.1"
              value={currentVolume}
              onChange={(e) => onVolumeChange(parseFloat(e.target.value))}
              style={{
                width: '100%',
                marginBottom: '0.5rem'
              }}
              aria-label="Volume control"
            />
            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              fontSize: '0.8rem',
              color: '#6c757d'
            }}>
              <span>0%</span>
              <span>100%</span>
            </div>
          </div>

          {/* Speed Control */}
          <div style={{ marginBottom: '1rem' }}>
            <label style={{
              display: 'block',
              marginBottom: '0.5rem',
              fontSize: '0.9rem',
              fontWeight: '500'
            }}>
              Playback Speed: {playbackSpeed}x
            </label>
            <input
              type="range"
              min="0.5"
              max="2"
              step="0.1"
              value={playbackSpeed}
              onChange={(e) => onSpeedChange(parseFloat(e.target.value))}
              style={{
                width: '100%',
                marginBottom: '0.5rem'
              }}
              aria-label="Playback speed control"
            />
            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              fontSize: '0.8rem',
              color: '#6c757d'
            }}>
              <span>0.5x</span>
              <span>1x</span>
              <span>2x</span>
            </div>
          </div>

          {/* Quick Speed Buttons */}
          <div style={{
            display: 'flex',
            gap: '0.5rem',
            marginBottom: '1rem'
          }}>
            {[0.75, 1, 1.25, 1.5].map(speed => (
              <button
                key={speed}
                onClick={() => onSpeedChange(speed)}
                style={{
                  flex: 1,
                  backgroundColor: playbackSpeed === speed ? '#ff6b35' : '#f8f9fa',
                  color: playbackSpeed === speed ? 'white' : '#333',
                  border: '1px solid #e9ecef',
                  borderRadius: '4px',
                  padding: '0.3rem',
                  cursor: 'pointer',
                  fontSize: '0.8rem'
                }}
                aria-label={`Set speed to ${speed}x`}
              >
                {speed}x
              </button>
            ))}
          </div>

          {/* Keyboard Shortcuts Toggle */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            marginBottom: '1rem'
          }}>
            <input
              type="checkbox"
              id="keyboard-shortcuts"
              checked={keyboardShortcutsEnabled}
              onChange={(e) => setKeyboardShortcutsEnabled(e.target.checked)}
            />
            <label htmlFor="keyboard-shortcuts" style={{
              fontSize: '0.9rem',
              cursor: 'pointer'
            }}>
              Enable keyboard shortcuts
            </label>
          </div>

          {/* Keyboard Shortcuts Help */}
          <details style={{ fontSize: '0.8rem', color: '#6c757d' }}>
            <summary style={{ cursor: 'pointer', marginBottom: '0.5rem' }}>
              Keyboard Shortcuts
            </summary>
            <div style={{ paddingLeft: '1rem' }}>
              <div>Ctrl+Space: Play/Pause</div>
              <div>Ctrl+M: Toggle Microphone</div>
              <div>Ctrl+S: Stop</div>
              <div>Ctrl+←/→: Skip Backward/Forward</div>
              <div>Ctrl+↑/↓: Volume Up/Down</div>
            </div>
          </details>
        </div>
      )}

      {/* Screen Reader Announcements */}
      <div
        aria-live="polite"
        aria-atomic="true"
        style={{
          position: 'absolute',
          left: '-10000px',
          width: '1px',
          height: '1px',
          overflow: 'hidden'
        }}
      >
        {isListening && 'Voice input is active'}
        {isPlaying && 'Audio is playing'}
      </div>

      {/* Visual Feedback for Listening State */}
      {isListening && (
        <div
          style={{
            position: 'fixed',
            top: '20px',
            left: '50%',
            transform: 'translateX(-50%)',
            backgroundColor: '#28a745',
            color: 'white',
            padding: '0.5rem 1rem',
            borderRadius: '20px',
            fontSize: '0.9rem',
            zIndex: 1000,
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            boxShadow: '0 2px 8px rgba(0, 0, 0, 0.15)'
          }}
          role="status"
          aria-label="Currently listening for voice input"
        >
          <div
            style={{
              width: '8px',
              height: '8px',
              borderRadius: '50%',
              backgroundColor: 'white',
              animation: 'pulse 1s infinite'
            }}
          />
          Listening...
        </div>
      )}

      {/* CSS for animations */}
      <style jsx>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.5; }
        }
      `}</style>
    </div>
  );
}

// Hook for managing voice accessibility state
export function useVoiceAccessibility() {
  const [volume, setVolume] = useState(1);
  const [speed, setSpeed] = useState(1);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isListening, setIsListening] = useState(false);

  const handleVolumeChange = (newVolume: number) => {
    setVolume(Math.max(0, Math.min(1, newVolume)));
  };

  const handleSpeedChange = (newSpeed: number) => {
    setSpeed(Math.max(0.5, Math.min(2, newSpeed)));
  };

  return {
    volume,
    speed,
    isPlaying,
    isListening,
    setIsPlaying,
    setIsListening,
    handleVolumeChange,
    handleSpeedChange
  };
}