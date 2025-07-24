import { useState, useEffect } from 'react';

export interface VoiceConfiguration {
  voiceId: string;
  speechRate: string;
  volume: string;
  language: string;
  microphoneSensitivity: number;
  noiseCancellation: boolean;
  autoGainControl: boolean;
  pushToTalk: boolean;
  continuousListening: boolean;
}

interface AvailableVoice {
  id: string;
  name: string;
  gender: string;
  language: string;
  preview?: string;
}

interface VoiceConfigurationPanelProps {
  configuration: VoiceConfiguration;
  availableVoices: AvailableVoice[];
  onConfigurationChange: (config: VoiceConfiguration) => void;
  onTestVoice?: (voiceId: string, text: string) => void;
  onTestMicrophone?: () => void;
  isVisible: boolean;
  onClose: () => void;
}

export default function VoiceConfigurationPanel({
  configuration,
  availableVoices,
  onConfigurationChange,
  onTestVoice,
  onTestMicrophone,
  isVisible,
  onClose
}: VoiceConfigurationPanelProps) {
  const [localConfig, setLocalConfig] = useState<VoiceConfiguration>(configuration);
  const [testText, setTestText] = useState('Hello! This is a test of the selected voice.');
  const [microphoneLevel, setMicrophoneLevel] = useState(0);

  useEffect(() => {
    setLocalConfig(configuration);
  }, [configuration]);

  const handleConfigChange = (updates: Partial<VoiceConfiguration>) => {
    const newConfig = { ...localConfig, ...updates };
    setLocalConfig(newConfig);
    onConfigurationChange(newConfig);
  };

  const handleVoiceTest = () => {
    if (onTestVoice) {
      onTestVoice(localConfig.voiceId, testText);
    }
  };

  const handleMicrophoneTest = () => {
    if (onTestMicrophone) {
      onTestMicrophone();
    }
  };

  const getVoicesByLanguage = () => {
    const grouped: { [key: string]: AvailableVoice[] } = {};
    availableVoices.forEach(voice => {
      if (!grouped[voice.language]) {
        grouped[voice.language] = [];
      }
      grouped[voice.language].push(voice);
    });
    return grouped;
  };

  if (!isVisible) return null;

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      backgroundColor: 'rgba(0, 0, 0, 0.5)',
      display: 'flex',
      justifyContent: 'center',
      alignItems: 'center',
      zIndex: 1000
    }}>
      <div style={{
        backgroundColor: 'white',
        borderRadius: '8px',
        padding: '2rem',
        maxWidth: '600px',
        width: '90%',
        maxHeight: '80vh',
        overflowY: 'auto',
        boxShadow: '0 4px 20px rgba(0, 0, 0, 0.15)'
      }}>
        {/* Header */}
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '2rem',
          paddingBottom: '1rem',
          borderBottom: '1px solid #e9ecef'
        }}>
          <h2 style={{ margin: 0, color: '#333' }}>Voice Configuration</h2>
          <button
            onClick={onClose}
            style={{
              backgroundColor: 'transparent',
              border: 'none',
              fontSize: '1.5rem',
              cursor: 'pointer',
              color: '#6c757d'
            }}
          >
            ×
          </button>
        </div>

        {/* Voice Selection */}
        <div style={{ marginBottom: '2rem' }}>
          <h3 style={{ marginBottom: '1rem', color: '#333' }}>Voice Selection</h3>
          
          <div style={{ marginBottom: '1rem' }}>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '500' }}>
              Language:
            </label>
            <select
              value={localConfig.language}
              onChange={(e) => handleConfigChange({ language: e.target.value })}
              style={{
                width: '100%',
                padding: '0.5rem',
                border: '1px solid #ced4da',
                borderRadius: '4px',
                fontSize: '0.9rem'
              }}
            >
              {Object.keys(getVoicesByLanguage()).map(language => (
                <option key={language} value={language}>
                  {language}
                </option>
              ))}
            </select>
          </div>

          <div style={{ marginBottom: '1rem' }}>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '500' }}>
              Voice:
            </label>
            <select
              value={localConfig.voiceId}
              onChange={(e) => handleConfigChange({ voiceId: e.target.value })}
              style={{
                width: '100%',
                padding: '0.5rem',
                border: '1px solid #ced4da',
                borderRadius: '4px',
                fontSize: '0.9rem'
              }}
            >
              {getVoicesByLanguage()[localConfig.language]?.map(voice => (
                <option key={voice.id} value={voice.id}>
                  {voice.name} ({voice.gender})
                </option>
              ))}
            </select>
          </div>

          <div style={{ marginBottom: '1rem' }}>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '500' }}>
              Test Text:
            </label>
            <textarea
              value={testText}
              onChange={(e) => setTestText(e.target.value)}
              style={{
                width: '100%',
                padding: '0.5rem',
                border: '1px solid #ced4da',
                borderRadius: '4px',
                fontSize: '0.9rem',
                minHeight: '60px',
                resize: 'vertical'
              }}
            />
            <button
              onClick={handleVoiceTest}
              style={{
                marginTop: '0.5rem',
                backgroundColor: '#28a745',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                padding: '0.5rem 1rem',
                fontSize: '0.9rem',
                cursor: 'pointer'
              }}
            >
              🔊 Test Voice
            </button>
          </div>
        </div>

        {/* Speech Settings */}
        <div style={{ marginBottom: '2rem' }}>
          <h3 style={{ marginBottom: '1rem', color: '#333' }}>Speech Settings</h3>
          
          <div style={{ marginBottom: '1rem' }}>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '500' }}>
              Speech Rate:
            </label>
            <select
              value={localConfig.speechRate}
              onChange={(e) => handleConfigChange({ speechRate: e.target.value })}
              style={{
                width: '100%',
                padding: '0.5rem',
                border: '1px solid #ced4da',
                borderRadius: '4px',
                fontSize: '0.9rem'
              }}
            >
              <option value="x-slow">Very Slow</option>
              <option value="slow">Slow</option>
              <option value="medium">Medium</option>
              <option value="fast">Fast</option>
              <option value="x-fast">Very Fast</option>
            </select>
          </div>

          <div style={{ marginBottom: '1rem' }}>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '500' }}>
              Volume:
            </label>
            <select
              value={localConfig.volume}
              onChange={(e) => handleConfigChange({ volume: e.target.value })}
              style={{
                width: '100%',
                padding: '0.5rem',
                border: '1px solid #ced4da',
                borderRadius: '4px',
                fontSize: '0.9rem'
              }}
            >
              <option value="silent">Silent</option>
              <option value="x-soft">Very Soft</option>
              <option value="soft">Soft</option>
              <option value="medium">Medium</option>
              <option value="loud">Loud</option>
              <option value="x-loud">Very Loud</option>
            </select>
          </div>
        </div>

        {/* Microphone Settings */}
        <div style={{ marginBottom: '2rem' }}>
          <h3 style={{ marginBottom: '1rem', color: '#333' }}>Microphone Settings</h3>
          
          <div style={{ marginBottom: '1rem' }}>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '500' }}>
              Microphone Sensitivity: {Math.round(localConfig.microphoneSensitivity * 100)}%
            </label>
            <input
              type="range"
              min="0"
              max="1"
              step="0.1"
              value={localConfig.microphoneSensitivity}
              onChange={(e) => handleConfigChange({ microphoneSensitivity: parseFloat(e.target.value) })}
              style={{
                width: '100%',
                marginBottom: '0.5rem'
              }}
            />
            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              fontSize: '0.8rem',
              color: '#6c757d'
            }}>
              <span>Low</span>
              <span>High</span>
            </div>
          </div>

          <div style={{ marginBottom: '1rem' }}>
            <label style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              cursor: 'pointer'
            }}>
              <input
                type="checkbox"
                checked={localConfig.noiseCancellation}
                onChange={(e) => handleConfigChange({ noiseCancellation: e.target.checked })}
              />
              Enable Noise Cancellation
            </label>
          </div>

          <div style={{ marginBottom: '1rem' }}>
            <label style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              cursor: 'pointer'
            }}>
              <input
                type="checkbox"
                checked={localConfig.autoGainControl}
                onChange={(e) => handleConfigChange({ autoGainControl: e.target.checked })}
              />
              Enable Automatic Gain Control
            </label>
          </div>

          <button
            onClick={handleMicrophoneTest}
            style={{
              backgroundColor: '#007bff',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              padding: '0.5rem 1rem',
              fontSize: '0.9rem',
              cursor: 'pointer'
            }}
          >
            🎤 Test Microphone
          </button>

          {microphoneLevel > 0 && (
            <div style={{ marginTop: '0.5rem' }}>
              <div style={{
                width: '100%',
                height: '8px',
                backgroundColor: '#e9ecef',
                borderRadius: '4px',
                overflow: 'hidden'
              }}>
                <div style={{
                  width: `${microphoneLevel * 100}%`,
                  height: '100%',
                  backgroundColor: microphoneLevel > 0.8 ? '#dc3545' : microphoneLevel > 0.5 ? '#ffc107' : '#28a745',
                  transition: 'width 0.1s ease'
                }} />
              </div>
              <div style={{
                fontSize: '0.8rem',
                color: '#6c757d',
                marginTop: '0.25rem'
              }}>
                Microphone Level: {Math.round(microphoneLevel * 100)}%
              </div>
            </div>
          )}
        </div>

        {/* Listening Mode */}
        <div style={{ marginBottom: '2rem' }}>
          <h3 style={{ marginBottom: '1rem', color: '#333' }}>Listening Mode</h3>
          
          <div style={{ marginBottom: '1rem' }}>
            <label style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              cursor: 'pointer',
              marginBottom: '0.5rem'
            }}>
              <input
                type="radio"
                name="listeningMode"
                checked={localConfig.pushToTalk}
                onChange={() => handleConfigChange({ pushToTalk: true, continuousListening: false })}
              />
              Push-to-Talk Mode
            </label>
            <div style={{
              fontSize: '0.8rem',
              color: '#6c757d',
              marginLeft: '1.5rem',
              marginBottom: '1rem'
            }}>
              Click and hold the record button to speak
            </div>

            <label style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              cursor: 'pointer',
              marginBottom: '0.5rem'
            }}>
              <input
                type="radio"
                name="listeningMode"
                checked={localConfig.continuousListening}
                onChange={() => handleConfigChange({ pushToTalk: false, continuousListening: true })}
              />
              Continuous Listening Mode
            </label>
            <div style={{
              fontSize: '0.8rem',
              color: '#6c757d',
              marginLeft: '1.5rem'
            }}>
              Always listening for voice input (uses more battery)
            </div>
          </div>
        </div>

        {/* Action Buttons */}
        <div style={{
          display: 'flex',
          justifyContent: 'flex-end',
          gap: '1rem',
          paddingTop: '1rem',
          borderTop: '1px solid #e9ecef'
        }}>
          <button
            onClick={() => {
              setLocalConfig(configuration);
              onClose();
            }}
            style={{
              backgroundColor: '#6c757d',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              padding: '0.75rem 1.5rem',
              fontSize: '0.9rem',
              cursor: 'pointer'
            }}
          >
            Cancel
          </button>
          <button
            onClick={onClose}
            style={{
              backgroundColor: '#28a745',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              padding: '0.75rem 1.5rem',
              fontSize: '0.9rem',
              cursor: 'pointer'
            }}
          >
            Save Settings
          </button>
        </div>
      </div>
    </div>
  );
}

// Default voice configuration
export const defaultVoiceConfiguration: VoiceConfiguration = {
  voiceId: 'Joanna',
  speechRate: 'medium',
  volume: 'medium',
  language: 'en-US',
  microphoneSensitivity: 0.5,
  noiseCancellation: true,
  autoGainControl: true,
  pushToTalk: false,
  continuousListening: true
};

// Available voices (this would typically come from the backend)
export const defaultAvailableVoices: AvailableVoice[] = [
  { id: 'Joanna', name: 'Joanna', gender: 'Female', language: 'en-US' },
  { id: 'Matthew', name: 'Matthew', gender: 'Male', language: 'en-US' },
  { id: 'Ivy', name: 'Ivy', gender: 'Female', language: 'en-US' },
  { id: 'Justin', name: 'Justin', gender: 'Male', language: 'en-US' },
  { id: 'Kendra', name: 'Kendra', gender: 'Female', language: 'en-US' },
  { id: 'Kimberly', name: 'Kimberly', gender: 'Female', language: 'en-US' },
  { id: 'Salli', name: 'Salli', gender: 'Female', language: 'en-US' },
  { id: 'Joey', name: 'Joey', gender: 'Male', language: 'en-US' },
  { id: 'Amy', name: 'Amy', gender: 'Female', language: 'en-GB' },
  { id: 'Emma', name: 'Emma', gender: 'Female', language: 'en-GB' },
  { id: 'Brian', name: 'Brian', gender: 'Male', language: 'en-GB' }
];