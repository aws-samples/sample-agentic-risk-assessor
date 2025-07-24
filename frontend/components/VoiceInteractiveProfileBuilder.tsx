import { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/router';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { 
  useDocumentEnhancement,
  DocumentPanel,
  PrePopulatedAnswersCard,
  ConflictResolutionCard,
  DocumentReference
} from './EnhancedProfileBuilder';
import { ProfileFieldsPanel, ProfileField } from './ProfileFieldsPanel';
import { SuggestionsPanel } from './SuggestionsPanel';
import { buildWebSocketUrl } from '../utils/websocket';

interface OrganizationProfile {
  id: string;
  name: string;
  createdAt: Date;
  updatedAt: Date;
  filePath: string;
  metadata: {
    industry: string;
    size: string;
    regions: string[];
    completeness: number;
  };
}

interface Message {
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp?: Date;
  streaming?: boolean;
  audioUrl?: string;
  isVoiceInput?: boolean;
  confidence?: number;
  documentReferences?: Array<{
    document_id: string;
    document_name: string;
    page: number;
    section: string;
    confidence?: number;
  }>;
}

interface VoiceSettings {
  voiceId: string;
  speechRate: string;
  volume: string;
  language: string;
}

interface VoiceInteractiveProfileBuilderProps {
  websocketUrl?: string;
  onProfileComplete?: (profile: OrganizationProfile) => void;
  onCancel?: () => void;
  existingProfile?: OrganizationProfile;
  profileId?: string;
  enableVoice?: boolean;
}

export default function VoiceInteractiveProfileBuilder({
  websocketUrl,
  onProfileComplete,
  onCancel,
  existingProfile,
  profileId,
  enableVoice = true
}: VoiceInteractiveProfileBuilderProps) {
  const router = useRouter();
  const [conversationStarted, setConversationStarted] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [profileFields, setProfileFields] = useState<ProfileField[]>([]);
  const wsRef = useRef<WebSocket | null>(null);
  const chatAreaRef = useRef<HTMLDivElement | null>(null);
  
  // Track current profile ID (can be updated when profile is created)
  const [currentProfileId, setCurrentProfileId] = useState(profileId || 'new-profile');

  // Voice-specific state
  const [voiceMode, setVoiceMode] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [speechSpeed, setSpeechSpeed] = useState<'slow' | 'medium' | 'fast' | 'faster' | 'fastest'>('medium');
  const [voiceSettings, setVoiceSettings] = useState<VoiceSettings>({
    voiceId: 'Joanna',
    speechRate: 'medium',
    volume: 'medium',
    language: 'en-US'
  });
  const [transcript, setTranscript] = useState('');
  const [partialTranscript, setPartialTranscript] = useState('');
  const [audioQuality, setAudioQuality] = useState<string>('unknown');
  const [voiceSessionId, setVoiceSessionId] = useState<string | null>(null);
  const [userInterrupted, setUserInterrupted] = useState(false);
  const inputRef = useRef<HTMLTextAreaElement | null>(null);
  
  // Progress tracking
  const [completeness, setCompleteness] = useState(0);
  const [gatheredSections, setGatheredSections] = useState<string[]>([]);
  const [missingSections, setMissingSections] = useState<string[]>([
    'Basic Information',
    'Regulatory Environment',
    'Risk Profile',
    'Security Maturity',
    'Technology Environment',
    'Business Context'
  ]);

  // Notification state
  const [notification, setNotification] = useState<{message: string; type: 'success' | 'error' | 'info'} | null>(null);

  // Document enhancement hook
  const documentEnhancement = useDocumentEnhancement({
    profileId: currentProfileId,
    websocket: wsRef.current,
    onDocumentProcessed: (documentId) => {
      console.log('[Documents] Document processed:', documentId);
      const doc = documentEnhancement.documents.find(d => d.document_id === documentId);
      if (doc) {
        setNotification({
          message: `Document "${doc.document_name}" processed successfully and ready for extraction!`,
          type: 'success'
        });
        // Auto-hide notification after 5 seconds
        setTimeout(() => setNotification(null), 5000);
      }
    },
    onDocumentError: (documentId, error) => {
      console.error('[Documents] Document processing failed:', documentId, error);
      const doc = documentEnhancement.documents.find(d => d.document_id === documentId);
      if (doc) {
        setNotification({
          message: `Failed to process "${doc.document_name}": ${error}`,
          type: 'error'
        });
        // Auto-hide error notification after 8 seconds
        setTimeout(() => setNotification(null), 8000);
      }
    }
  });

  // Suggestions state
  const [showSuggestions, setShowSuggestions] = useState(true);

  // Update voice settings when speech speed changes
  useEffect(() => {
    setVoiceSettings(prev => ({
      ...prev,
      speechRate: speechSpeed
    }));
  }, [speechSpeed]);

  // Audio refs
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioStreamRef = useRef<MediaStream | null>(null);
  const audioPlayerRef = useRef<HTMLAudioElement | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const audioContextRef = useRef<AudioContext | null>(null);
  const audioDestinationRef = useRef<MediaStreamAudioDestinationNode | null>(null);
  
  // Audio streaming state
  const [audioChunks, setAudioChunks] = useState<string[]>([]);
  const [audioFormat, setAudioFormat] = useState<string>('mp3');
  const [isReceivingAudio, setIsReceivingAudio] = useState(false);
  const [audioQueue, setAudioQueue] = useState<string[]>([]);
  const [isProcessingQueue, setIsProcessingQueue] = useState(false);

  // Process audio queue
  useEffect(() => {
    const processQueue = async () => {
      if (audioQueue.length > 0 && !isProcessingQueue && !isPlaying) {
        setIsProcessingQueue(true);
        const nextAudioId = audioQueue[0];
        console.log('[Voice] Playing from queue:', nextAudioId);
        
        try {
          await playAudioViaHTTP(nextAudioId);
          setAudioQueue(prev => prev.slice(1));
        } catch (error) {
          console.error('[Voice] Queue playback error:', error);
          setAudioQueue(prev => prev.slice(1));
        }
        
        setIsProcessingQueue(false);
      }
    };
    
    processQueue();
  }, [audioQueue, isProcessingQueue, isPlaying]);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (chatAreaRef.current) {
      chatAreaRef.current.scrollTop = chatAreaRef.current.scrollHeight;
    }
  }, [messages]);

  // Setup WebSocket connection
  useEffect(() => {
    const setupWebSocket = async () => {
      try {
        const { getJwtToken } = await import('../utils/auth');
        const token = await getJwtToken();
        const agentsUrl = process.env.NEXT_PUBLIC_AGENTS_URL;
        
        if (!agentsUrl) {
          setError('NEXT_PUBLIC_AGENTS_URL environment variable not set');
          return;
        }

        // Always use the chat WebSocket endpoint and handle voice mode through messages
        const wsEndpoint = buildWebSocketUrl(agentsUrl, '/organization_profile/ws/chat', token || undefined);
        
        console.log(`Connecting to Organization Profile Agent: ${wsEndpoint}`);
        
        const ws = new WebSocket(wsEndpoint);
        wsRef.current = ws;

        ws.onopen = () => {
          console.log('WebSocket connected to Organization Profile Agent');
          setConnected(true);
          setError(null);
          
          // Don't send initial message - wait for user to click Start button
          if (existingProfile) {
            // Only auto-start for editing existing profiles
            const initialMessage = `edit_profile ${existingProfile.id}`;
            ws.send(JSON.stringify({
              message: initialMessage,
              agent: 'organization_profile',
              project_id: currentProfileId
            }));
          }
        };

        ws.onmessage = (event) => {
          console.log('📨 Raw WebSocket message:', event.data);
          
          try {
            const data = JSON.parse(event.data);
            console.log('📨 Parsed WebSocket data:', data);

            // Handle document-related messages
            if (data.type && [
              'document_processing_status',
              'document_processing_complete',
              'document_processing_failed',
              'pre_populated_answers',
              'conflicting_answers',
              'auto_populate_suggestions',
              'profile_fields_update'
            ].includes(data.type)) {
              if (data.type === 'profile_fields_update' && data.fields) {
                setProfileFields(data.fields);
              } else {
                documentEnhancement.handleDocumentMessage(data);
              }
              return;
            }

            // Handle all voice-related messages through the unified handler
            if (data.type && [
              'input_mode_switched', 
              'transcription_started', 
              'transcription_stopped', 
              'transcript_result', 
              'speech_completion_check',
              'audio_chunk_error',
              'audio_quality_warning',
              'voice_response_complete',
              'audio_chunk',  // New: Handle streaming audio chunks
              'streaming_started',  // New: Streaming transcription started
              'streaming_stopped',  // New: Streaming transcription stopped
              'partial_transcript',  // New: Real-time partial results
              'final_transcript',   // New: Real-time final results
              'error'
            ].includes(data.type)) {
              handleVoiceMessage(data);
              return;
            }

            // Handle standard messages (stream, complete, etc.)
            handleTextMessage(data);

          } catch (err) {
            console.error('Error parsing WebSocket message:', err);
            setMessages(prev => [...prev, {
              role: 'assistant',
              content: 'Sorry, I encountered an error processing that response. Please try again.',
              timestamp: new Date()
            }]);
            setLoading(false);
          }
        };

        ws.onerror = (error) => {
          console.error('WebSocket error:', error);
          setError('Connection error. Please check your network and try again.');
          setConnected(false);
          setLoading(false);
        };

        ws.onclose = (event) => {
          console.log('WebSocket disconnected:', event.code, event.reason);
          setConnected(false);
          if (event.code !== 1000) {
            setError('Connection lost. Please refresh the page to reconnect.');
          }
        };

      } catch (err) {
        console.error('Error setting up WebSocket:', err);
        setError('Failed to establish connection. Please try again.');
      }
    };

    setupWebSocket();

    // Cleanup on unmount
    return () => {
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.close();
      }
      stopRecording();
      stopAudioPlayback();
      
      // Clean up Web Audio API
      if (audioContextRef.current && audioContextRef.current.state !== 'closed') {
        audioContextRef.current.close().catch(console.error);
      }
    };
  }, [websocketUrl, existingProfile, profileId, enableVoice]);

  const handleTextMessage = (data: any) => {
    console.log('🚨 handleTextMessage CALLED with:', data.type, data.data?.substring(0, 20));
    
    // Check for profile_id and update if we don't have it yet (client-side tracking)
    if (data.profile_id && currentProfileId === 'new-profile') {
      console.log('✅ Profile ID received, updating from new-profile to:', data.profile_id);
      setCurrentProfileId(data.profile_id);
      // Update the URL to reflect the new profile ID
      if (typeof window !== 'undefined' && window.history) {
        const newUrl = `/organization-profiles/${data.profile_id}`;
        window.history.replaceState({}, '', newUrl);
      }
    }
    
    // Handle progress updates
    if (data.type === 'progress' || data.progress) {
      const progressData = data.progress || data;
      console.log('📊 Progress data received:', progressData);
      if (progressData.completeness !== undefined) {
        const newCompleteness = Math.round(progressData.completeness * 100);
        console.log('📊 Setting completeness to:', newCompleteness);
        setCompleteness(newCompleteness);
      }
      if (progressData.gathered_sections) {
        console.log('📊 Gathered sections:', progressData.gathered_sections);
        setGatheredSections(progressData.gathered_sections);
      }
      if (progressData.missing_sections) {
        console.log('📊 Missing sections:', progressData.missing_sections);
        setMissingSections(progressData.missing_sections);
      }
    }
    
    // Handle streaming content chunks
    if (data.type === 'stream' && data.data) {
      console.log('🔥 STREAM CHUNK:', data.data);
      console.log('🔥 Current loading state:', loading);
      
      setMessages(prev => {
        const currentMessages = [...prev];
        const lastMsg = currentMessages[currentMessages.length - 1];
        
        console.log('🔥 Last message:', lastMsg);
        console.log('🔥 Is last message streaming?', lastMsg?.streaming);
        
        if (lastMsg && lastMsg.role === 'assistant' && lastMsg.streaming) {
          console.log('🔥 APPENDING to existing message');
          // Append to existing streaming message
          return [...currentMessages.slice(0, -1), { 
            ...lastMsg, 
            content: lastMsg.content + data.data 
          }];
        } else {
          console.log('🔥 STARTING new streaming message');
          // Start new streaming message
          return [...currentMessages, { 
            role: 'assistant', 
            content: data.data, 
            streaming: true,
            timestamp: new Date()
          }];
        }
      });
      
      // Hide loading only when first stream chunk arrives
      setLoading(false);
      return;
    }

    // Handle agent completion
    if (data.type === 'complete') {
      console.log('[Voice] Received complete message:', { 
        hasStreamingAudio: !!data.streaming_audio,
        totalChunks: data.total_audio_chunks,
        hasProgress: !!data.progress
      });
      
      // Check if progress data is included in complete message
      if (data.progress) {
        console.log('📊 Progress in complete message:', data.progress);
        const progressData = data.progress;
        if (progressData.completeness !== undefined) {
          const newCompleteness = Math.round(progressData.completeness * 100);
          console.log('📊 Setting completeness to:', newCompleteness);
          setCompleteness(newCompleteness);
        }
        if (progressData.gathered_sections) {
          console.log('📊 Gathered sections:', progressData.gathered_sections);
          setGatheredSections(progressData.gathered_sections);
        }
        if (progressData.missing_sections) {
          console.log('📊 Missing sections:', progressData.missing_sections);
          setMissingSections(progressData.missing_sections);
        }
      }
      
      setMessages(prev => {
        const currentMessages = [...prev];
        const lastMsg = currentMessages[currentMessages.length - 1];
        
        console.log('[Voice Debug] Last message:', { 
          hasLastMsg: !!lastMsg, 
          isStreaming: lastMsg?.streaming,
          role: lastMsg?.role 
        });
        
        if (lastMsg && lastMsg.streaming) {
          // Mark streaming as complete
          const updatedMsg = { 
            ...lastMsg, 
            streaming: false 
          };
          
          // Audio chunks are handled separately via audio_chunk messages
          if (data.streaming_audio) {
            console.log('[Voice] Streaming audio in progress, chunks handled separately');
          } else {
            console.log('[Voice] No streaming audio for this response');
          }
          
          return [...currentMessages.slice(0, -1), updatedMsg];
        }
        
        return currentMessages;
      });
      setLoading(false);
      return;
    }

    // Handle other response formats (fallback)
    let content = '';
    if (data.response) {
      content = data.response;
    } else if (data.data) {
      content = data.data;
    } else if (data.message) {
      content = data.message;
    } else if (data.content) {
      content = data.content;
    }

    if (content) {
      // Check for profile completion signal
      if (content.includes('PROFILE_COMPLETE')) {
        console.log('🎉 Profile creation completed');
        setLoading(false);
        
        // Extract profile data if available
        try {
          const profileMatch = content.match(/PROFILE_DATA:([\s\S]+?)(?:PROFILE_END|$)/);
          if (profileMatch && onProfileComplete) {
            const profileData = JSON.parse(profileMatch[1]);
            onProfileComplete(profileData);
          }
        } catch (err) {
          console.error('Error parsing profile data:', err);
        }
        
        // Add completion message
        setMessages(prev => [...prev, {
          role: 'assistant',
          content: 'Your organization profile has been created successfully! You can now use it for tailored security recommendations.',
          timestamp: new Date()
        }]);
        
        return;
      }

      // Add regular message (non-streaming)
      const newMessage: Message = {
        role: 'assistant' as const,
        content: content,
        timestamp: new Date()
      };

      // Check for audio_id and play if in voice mode
      if (data.audio_id && voiceMode) {
        console.log('[Voice] Playing audio for message:', data.audio_id);
        playAudioViaHTTP(data.audio_id);
      }

      setMessages(prev => [...prev, newMessage]);
    }
  };

  const handleVoiceMessage = (data: any) => {
    switch (data.type) {
      case 'input_mode_switched':
        console.log('[Voice] Input mode switched to:', data.new_mode);
        if (data.new_mode === 'voice') {
          setVoiceMode(true);
          console.log('[Voice] Voice mode enabled via server confirmation');
        } else {
          setVoiceMode(false);
          console.log('[Voice] Voice mode disabled via server confirmation');
        }
        break;

      case 'stop_audio_playback':
        console.log('[Voice] Stopping audio playback due to mode switch');
        stopAudioPlayback();
        break;

      case 'transcription_started':
        setIsListening(true);
        console.log('[Voice] Transcription started successfully');
        break;

      case 'transcription_stopped':
        setIsListening(false);
        console.log('[Voice] Transcription stopped');
        break;

      case 'transcript_result':
        // Handle real-time transcript results from Phase 1 implementation
        console.log('[Voice] Transcript result:', {
          text: data.text,
          confidence: data.confidence,
          is_final: data.is_final,
          is_partial: data.is_partial
        });
        
        if (data.is_partial) {
          // Show partial transcript as user speaks
          setPartialTranscript(data.text);
        } else if (data.is_final) {
          // Final transcript received
          setTranscript(data.text);
          setPartialTranscript('');
          
          // Add user message to chat
          setMessages(prev => [...prev, {
            role: 'user',
            content: data.text,
            timestamp: new Date(),
            isVoiceInput: true,
            confidence: data.confidence
          }]);
          
          // Send the final transcript as a message to the agent
          setLoading(true);
          if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify({
              message: data.text,
              input_mode: 'voice',
              agent: 'organization_profile',
              project_id: currentProfileId
            }));
          }
        }
        break;

      case 'speech_completion_check':
        // Handle speech completion detection from Phase 1
        console.log('[Voice] Speech completion check:', {
          speech_complete: data.speech_complete,
          has_final_transcript: !!data.final_transcript
        });
        
        if (data.speech_complete && data.final_transcript) {
          // User finished speaking, process final transcript
          setTranscript(data.final_transcript);
          setPartialTranscript('');
          
          // Stop recording automatically
          if (isRecording) {
            stopRecording();
          }
        }
        break;

      case 'audio_chunk_error':
        // Handle audio chunk processing errors from Phase 1
        console.error('[Voice] Audio chunk error:', data.message);
        setError(`Audio error: ${data.message}`);
        setIsReceivingAudio(false);
        
        // Offer fallback to text mode if available
        if (data.fallback_available) {
          setError(`${data.message}. You can switch to text mode or try again.`);
        }
        break;

      case 'audio_quality_warning':
        // Handle audio quality warnings from Phase 1
        console.warn('[Voice] Audio quality warning:', data.message);
        setAudioQuality(data.audio_quality?.level || 'poor');
        
        // Show warning to user with suggestion
        if (data.suggestion) {
          setError(`Audio quality issue: ${data.message}. ${data.suggestion}`);
        }
        break;

      case 'streaming_started':
        console.log('[Voice] Streaming transcription started:', data.status);
        setIsListening(true);
        break;
      
      case 'streaming_stopped':
        console.log('[Voice] Streaming transcription stopped');
        setIsListening(false);
        break;
      
      case 'partial_transcript':
        // Show real-time partial results as user speaks
        console.log('[Voice] Partial transcript:', data.text);
        setPartialTranscript(data.text);
        break;
      
      case 'final_transcript':
        // Handle final transcript from streaming
        console.log('[Voice] Final transcript:', data.text);
        setTranscript(data.text);
        setPartialTranscript('');
        
        // Add user message to chat
        setMessages(prev => [...prev, {
          role: 'user',
          content: data.text,
          timestamp: new Date(),
          isVoiceInput: true,
          confidence: data.confidence
        }]);
        
        // Process through agent immediately
        setLoading(true);
        if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
          wsRef.current.send(JSON.stringify({
            message: data.text,
            input_mode: 'voice',
            agent: 'organization_profile',
            project_id: currentProfileId
          }));
        }
        break;

      case 'audio_chunk':
        // Handle streaming audio chunks (sentence-by-sentence)
        console.log('[Voice] Audio chunk received:', {
          audio_id: data.audio_id,
          sentence: data.sentence,
          chunk_index: data.chunk_index,
          is_final: data.is_final
        });
        
        console.log('[Voice] Current voiceMode:', voiceMode);
        console.log('[Voice] Audio stream active:', !!audioStreamRef.current);
        
        // Play audio chunk immediately (check voiceMode OR if audio stream is active)
        if (data.audio_id && (voiceMode || audioStreamRef.current)) {
          console.log('[Voice] Adding to queue:', data.audio_id);
          setAudioQueue(prev => [...prev, data.audio_id]);
        } else {
          console.log('[Voice] Not playing - voiceMode:', voiceMode, 'audioStream:', !!audioStreamRef.current, 'audio_id:', !!data.audio_id);
        }
        
        // Update UI to show streaming progress
        if (data.is_final) {
          console.log('[Voice] All audio chunks received');
          setIsPlaying(false);
        } else {
          setIsPlaying(true);
        }
        break;

      case 'voice_response_complete':
        // Handle agent response with audio
        setMessages(prev => [...prev, {
          role: 'assistant',
          content: data.response,
          timestamp: new Date(),
          audioUrl: data.audio_id ? `/api/voice/audio/${data.audio_id}` : undefined
        }]);
        
        // Auto-play audio response via HTTP streaming
        if (data.audio_id && voiceMode) {
          playAudioViaHTTP(data.audio_id);
        }
        setLoading(false);
        break;



      case 'complete':
        // Handle completion (both text and voice modes)
        console.log('[Voice] Received complete message:', { 
          hasAudioId: !!data.audio_id, 
          audioId: data.audio_id,
          voiceMode 
        });
        
        setMessages(prev => {
          const currentMessages = [...prev];
          const lastMsg = currentMessages[currentMessages.length - 1];
          
          if (lastMsg && lastMsg.streaming) {
            // Mark streaming as complete and add audio if available
            const updatedMsg = { 
              ...lastMsg, 
              streaming: false 
            };
            
            if (data.audio_id) {
              console.log('[Voice] Playing audio for message:', data.audio_id);
              updatedMsg.audioUrl = `/api/voice/audio/${data.audio_id}`;
              // Only auto-play audio when voice mode is enabled
              if (voiceMode) {
                playAudioViaHTTP(data.audio_id);
              }
            } else {
              console.log('[Voice] No audio_id in response');
            }
            
            return [...currentMessages.slice(0, -1), updatedMsg];
          }
          
          // Handle audio_id even when no streaming message
          if (data.audio_id && voiceMode) {
            console.log('[Voice] Playing audio for message:', data.audio_id);
            playAudioViaHTTP(data.audio_id);
          }
          
          return currentMessages;
        });
        setLoading(false);
        break;

      case 'error':
        // Handle general errors from Phase 1 handlers
        console.error('[Voice] Error:', data.feature, data.message);
        setError(`${data.feature}: ${data.message}`);
        setLoading(false);
        break;

      default:
        console.log('[Voice] Unhandled message type:', data.type);
    }
  };

  const toggleVoiceMode = async () => {
    console.log('[Voice Debug] toggleVoiceMode called', { 
      enableVoice, 
      currentVoiceMode: voiceMode 
    });
    
    if (!enableVoice) return;

    if (voiceMode) {
      // Switching to text mode
      console.log('[Voice Debug] Switching to text mode');
      stopRecording();
      stopAudioPlayback(); // Stop any playing audio
      setVoiceMode(false);
      setIsListening(false);
      setIsRecording(false);
      
      // Send switch mode message to existing WebSocket
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({
          type: 'switch_input_mode',
          mode: 'text'
        }));
      }
    } else {
      // Switching to voice mode
      console.log('[Voice Debug] Switching to voice mode, requesting microphone access');
      try {
        // Request microphone permission with enhanced echo cancellation
        const stream = await navigator.mediaDevices.getUserMedia({ 
          audio: {
            echoCancellation: true,
            noiseSuppression: true,
            autoGainControl: true,
            sampleRate: 48000,
            channelCount: 1,
            latency: 0,
            // Chrome-specific advanced constraints
            googEchoCancellation: true,
            googAutoGainControl: true,
            googNoiseSuppression: true,
            googHighpassFilter: true,
            // Firefox-specific advanced constraints
            mozEchoCancellation: true,
            mozAutoGainControl: true,
            mozNoiseSuppression: true
          } as any  // Use 'any' to allow vendor-specific properties
        });
        console.log('[Voice Debug] Microphone access granted with enhanced AEC', {
          streamId: stream.id,
          audioTracks: stream.getAudioTracks().length,
          settings: stream.getAudioTracks()[0]?.getSettings()
        });
        
        audioStreamRef.current = stream;
        
        // Initialize Web Audio API for echo cancellation
        const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
        audioContextRef.current = audioContext;
        
        // Create a destination for routing audio through Web Audio API
        const destination = audioContext.createMediaStreamDestination();
        audioDestinationRef.current = destination;
        
        console.log('[Voice Debug] Web Audio API initialized for AEC');
        
        setVoiceMode(true);
        
        // Send switch mode message to existing WebSocket
        if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
          console.log('[Voice Debug] Sending switch_input_mode message');
          wsRef.current.send(JSON.stringify({
            type: 'switch_input_mode',
            mode: 'voice',
            voice_settings: voiceSettings
          }));
        } else {
          console.error('[Voice Debug] WebSocket not ready:', {
            exists: !!wsRef.current,
            readyState: wsRef.current?.readyState
          });
        }
      } catch (err) {
        console.error('[Voice Debug] Microphone access denied:', err);
        setError('Microphone access is required for voice mode. Please allow microphone access and try again.');
      }
    }
  };

  const startContinuousAudioStream = () => {
    if (!audioStreamRef.current) return;
    
    console.log('[Voice] Starting continuous audio stream');
    setIsListening(true);
    
    // Create AudioContext for real-time processing
    const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
    const source = audioContext.createMediaStreamSource(audioStreamRef.current);
    const processor = audioContext.createScriptProcessor(4096, 1, 1);
    
    processor.onaudioprocess = (event) => {
      if (!voiceMode || !wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
        return;
      }
      
      // Get audio data
      const inputBuffer = event.inputBuffer;
      const inputData = inputBuffer.getChannelData(0);
      
      // Convert to 16-bit PCM
      const pcmData = new Int16Array(inputData.length);
      for (let i = 0; i < inputData.length; i++) {
        pcmData[i] = Math.max(-32768, Math.min(32767, inputData[i] * 32768));
      }
      
      // Send to server as base64
      const uint8Array = new Uint8Array(pcmData.buffer);
      const base64Audio = btoa(String.fromCharCode.apply(null, Array.from(uint8Array)));
      
      wsRef.current.send(JSON.stringify({
        type: 'audio_stream',
        audio_data: base64Audio
      }));
    };
    
    source.connect(processor);
    processor.connect(audioContext.destination);
    
    // Store for cleanup
    (audioStreamRef.current as any).audioContext = audioContext;
    (audioStreamRef.current as any).processor = processor;
  };
  
  const stopContinuousAudioStream = () => {
    console.log('[Voice] Stopping continuous audio stream');
    setIsListening(false);
    
    if (audioStreamRef.current) {
      // Clean up audio processing
      const audioContext = (audioStreamRef.current as any).audioContext;
      const processor = (audioStreamRef.current as any).processor;
      
      if (processor) {
        processor.disconnect();
      }
      if (audioContext) {
        audioContext.close();
      }
      
      // Stop tracks
      audioStreamRef.current.getTracks().forEach(track => track.stop());
      audioStreamRef.current = null;
    }
  };

  const startRecording = async () => {
    console.log('[Voice] Starting browser speech recognition');
    
    if (!audioStreamRef.current || !wsRef.current) {
      console.error('[Voice] Missing requirements');
      return;
    }

    try {
      // Use browser's Web Speech API instead of AWS Transcribe
      const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
      
      if (!SpeechRecognition) {
        setError('Speech recognition not supported in this browser. Please use Chrome, Edge, or Safari.');
        return;
      }

      const recognition = new SpeechRecognition();
      recognition.continuous = true;
      recognition.interimResults = true;
      recognition.lang = 'en-US';

      recognition.onstart = () => {
        console.log('[Voice] Speech recognition started');
        setIsRecording(true);
        setIsListening(true);
      };

      recognition.onresult = (event: any) => {
        let interimTranscript = '';
        let finalTranscript = '';

        for (let i = event.resultIndex; i < event.results.length; i++) {
          const transcript = event.results[i][0].transcript;
          if (event.results[i].isFinal) {
            finalTranscript += transcript + ' ';
          } else {
            interimTranscript += transcript;
          }
        }

        // Show partial transcript
        if (interimTranscript) {
          console.log('[Voice] Partial transcript:', interimTranscript);
          setPartialTranscript(interimTranscript);
          
          // INTERRUPTION DETECTION: If user starts speaking while agent is playing, stop playback
          if (isPlaying) {
            console.log('[Voice Interruption] User started speaking, stopping agent playback');
            setUserInterrupted(true);
            stopAudioPlayback();
            // Clear the audio queue to prevent continuation
            setAudioQueue([]);
            
            // Clear interruption flag after a short delay
            setTimeout(() => setUserInterrupted(false), 2000);
          }
        }

        // Handle final transcript
        if (finalTranscript) {
          console.log('[Voice] Final transcript:', finalTranscript);
          setTranscript(prev => prev + finalTranscript);
          setPartialTranscript('');
          
          // Add user message to chat
          setMessages(prev => [...prev, {
            role: 'user' as const,
            content: finalTranscript.trim(),
            timestamp: new Date(),
            isVoiceInput: true,
            confidence: event.results[event.resultIndex][0].confidence
          }]);
          
          // Send to backend
          setLoading(true);
          wsRef.current?.send(JSON.stringify({
            message: finalTranscript.trim(),
            agent: 'organization_profile',
            project_id: currentProfileId,
            input_mode: 'voice'
          }));
        }
      };

      recognition.onerror = (event: any) => {
        console.error('[Voice] Speech recognition error:', event.error);
        if (event.error === 'no-speech') {
          setError('No speech detected. Please try again.');
        } else if (event.error === 'audio-capture') {
          setError('Microphone not accessible. Please check permissions.');
        } else if (event.error === 'not-allowed') {
          setError('Microphone permission denied. Please allow microphone access.');
        } else {
          setError(`Speech recognition error: ${event.error}`);
        }
        setIsRecording(false);
        setIsListening(false);
      };

      recognition.onend = () => {
        console.log('[Voice] Speech recognition ended');
        setIsRecording(false);
        setIsListening(false);
      };

      // Store recognition instance
      (mediaRecorderRef as any).current = recognition;
      
      recognition.start();
      console.log('[Voice] Browser speech recognition started successfully');
      
    } catch (err) {
      console.error('[Voice] Failed to start speech recognition:', err);
      setError('Failed to start speech recognition. Please try again.');
    }
  };

  const stopRecording = () => {
    console.log('[Voice] Stopping speech recognition');
    
    if (mediaRecorderRef.current) {
      // Stop browser speech recognition
      try {
        (mediaRecorderRef.current as any).stop();
      } catch (err) {
        console.error('[Voice] Error stopping recognition:', err);
      }
    }
    
    setIsRecording(false);
    setIsListening(false);
    setPartialTranscript('');
  };

  const playAudioViaHTTP = async (audioId: string) => {
    // Stop any currently playing audio to prevent overlap
    if (audioPlayerRef.current) {
      audioPlayerRef.current.pause();
      audioPlayerRef.current.currentTime = 0;
    }

    try {
      const { getJwtToken } = await import('../utils/auth');
      const token = await getJwtToken();
      const agentsUrl = process.env.NEXT_PUBLIC_AGENTS_URL;
      
      if (!agentsUrl) {
        console.error('NEXT_PUBLIC_AGENTS_URL not configured');
        return;
      }

      // Convert agents URL to HTTP URL for audio fetch
      let httpUrl = agentsUrl;
      if (!agentsUrl.startsWith('http')) {
        const protocol = window.location.protocol === 'https:' ? 'https:' : 'http:';
        httpUrl = `${protocol}//${agentsUrl}`;
      }
      
      // Remove /ws/chat or /ws/voice from the URL if present
      httpUrl = httpUrl.replace(/\/ws\/(chat|voice)$/, '');
      
      // Fetch audio via HTTP through organization profile agent
      const audioUrl = `${httpUrl}/api/voice/audio/${audioId}`;
      console.log('[Voice] Fetching audio from:', audioUrl);
      
      // Add authorization header via fetch and create object URL
      const response = await fetch(audioUrl, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      console.log('[Voice] Fetch response:', {
        status: response.status,
        statusText: response.statusText,
        ok: response.ok,
        headers: Object.fromEntries(response.headers.entries())
      });
      
      if (!response.ok) {
        const errorText = await response.text();
        console.error('[Voice] Fetch failed:', errorText);
        throw new Error(`Failed to fetch audio: ${response.status} ${response.statusText}`);
      }
      
      const audioBlob = await response.blob();
      const blobUrl = URL.createObjectURL(audioBlob);
      
      const audioElement = new Audio(blobUrl);
      audioPlayerRef.current = audioElement;
      
      // Apply speech speed to playback rate
      const speedMap: Record<string, number> = {
        'slow': 0.75,
        'medium': 1.0,
        'fast': 1.25,
        'faster': 1.5,
        'fastest': 2.0
      };
      audioElement.playbackRate = speedMap[speechSpeed] || 1.0;
      console.log('[Voice] Applied playback rate:', audioElement.playbackRate);
      
      // Route audio through Web Audio API for echo cancellation
      if (audioContextRef.current && audioDestinationRef.current) {
        try {
          const source = audioContextRef.current.createMediaElementSource(audioElement);
          
          // Create a gain node for volume control and ducking
          const gainNode = audioContextRef.current.createGain();
          gainNode.gain.value = 1.0;
          
          // Connect: source -> gain -> destination (speakers)
          source.connect(gainNode);
          gainNode.connect(audioContextRef.current.destination);
          
          console.log('[Voice AEC] Audio routed through Web Audio API for echo cancellation');
        } catch (err) {
          // If already connected or error, just play normally
          console.log('[Voice AEC] Using direct audio playback (already connected or error):', err);
        }
      }
      
      audioElement.onplay = () => {
        setIsPlaying(true);
        console.log('[Voice AEC] HTTP audio playback started with echo cancellation');
      };
      
      audioElement.onended = () => {
        setIsPlaying(false);
        URL.revokeObjectURL(blobUrl);
        console.log('[Voice] Audio chunk ended:', audioId);
      };
      
      audioElement.onerror = (err) => {
        setIsPlaying(false);
        URL.revokeObjectURL(blobUrl);
        console.error('HTTP audio playback failed:', err);
      };
      
      audioElement.play().catch(err => {
        console.error('Failed to play HTTP audio:', err);
        setIsPlaying(false);
        URL.revokeObjectURL(blobUrl);
      });
    } catch (err) {
      console.error('Failed to fetch audio via HTTP:', err);
      setError('Failed to play audio');
    }
  };

  const playAudio = (audioUrl?: string, audioData?: string) => {
    if (audioPlayerRef.current) {
      audioPlayerRef.current.pause();
    }

    let audioSrc = audioUrl;
    
    // If no URL but we have base64 data, create a blob URL
    if (!audioSrc && audioData) {
      try {
        const binaryString = atob(audioData);
        const bytes = new Uint8Array(binaryString.length);
        for (let i = 0; i < binaryString.length; i++) {
          bytes[i] = binaryString.charCodeAt(i);
        }
        const blob = new Blob([bytes], { type: 'audio/mpeg' });
        audioSrc = URL.createObjectURL(blob);
      } catch (err) {
        console.error('Failed to create audio blob:', err);
        return;
      }
    }

    if (!audioSrc) {
      console.error('No audio source available');
      return;
    }

    const audio = new Audio(audioSrc);
    audioPlayerRef.current = audio;
    
    // Apply speech speed to playback rate
    const speedMap: Record<string, number> = {
      'slow': 0.75,
      'medium': 1.0,
      'fast': 1.25,
      'faster': 1.5,
      'fastest': 2.0
    };
    audio.playbackRate = speedMap[speechSpeed] || 1.0;
    console.log('[Voice] Applied playback rate:', audio.playbackRate);
    
    // Route audio through Web Audio API for echo cancellation
    if (audioContextRef.current && audioDestinationRef.current) {
      try {
        const source = audioContextRef.current.createMediaElementSource(audio);
        
        // Create a gain node for volume control
        const gainNode = audioContextRef.current.createGain();
        gainNode.gain.value = 1.0;
        
        // Connect: source -> gain -> destination (speakers)
        source.connect(gainNode);
        gainNode.connect(audioContextRef.current.destination);
        
        console.log('[Voice AEC] Audio routed through Web Audio API for echo cancellation');
      } catch (err) {
        // If already connected or error, just play normally
        console.log('[Voice AEC] Using direct audio playback (already connected or error):', err);
      }
    }
    
    audio.onplay = () => setIsPlaying(true);
    audio.onended = () => {
      setIsPlaying(false);
      // Clean up blob URL if we created one
      if (!audioUrl && audioData) {
        URL.revokeObjectURL(audioSrc!);
      }
    };
    audio.onerror = () => {
      setIsPlaying(false);
      console.error('Audio playback failed');
      // Clean up blob URL if we created one
      if (!audioUrl && audioData) {
        URL.revokeObjectURL(audioSrc!);
      }
    };
    
    audio.play().catch(err => {
      console.error('Failed to play audio:', err);
      setIsPlaying(false);
      // Clean up blob URL if we created one
      if (!audioUrl && audioData) {
        URL.revokeObjectURL(audioSrc!);
      }
    });
  };

  const stopAudioPlayback = () => {
    console.log('[Voice] Stopping audio playback');
    if (audioPlayerRef.current) {
      audioPlayerRef.current.pause();
      audioPlayerRef.current.currentTime = 0;
      audioPlayerRef.current = null;
    }
    setIsPlaying(false);
    // Clear any queued audio chunks
    setAudioQueue([]);
    console.log('[Voice] Audio playback stopped and queue cleared');
  };

  const sendMessage = () => {
    console.log('[SendMessage] Called', {
      hasInput: !!input.trim(),
      hasWs: !!wsRef.current,
      wsState: wsRef.current?.readyState,
      connected,
      loading,
      voiceMode
    });
    
    if (!input.trim() || !wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      console.log('[SendMessage] Blocked - conditions not met');
      return;
    }

    const userMessage = input.trim();
    console.log('[SendMessage] Sending message:', userMessage);
    
    // Add user message to chat
    setMessages(prev => [...prev, {
      role: 'user',
      content: userMessage,
      timestamp: new Date()
    }]);

    // Send to WebSocket
    setLoading(true);
    setInput('');

    // FIX: Always use same format, just change input_mode based on voiceMode
    const payload = {
      message: userMessage,
      agent: 'organization_profile',
      project_id: currentProfileId,
      input_mode: voiceMode ? 'voice' : 'text'  // ← FIX: Use voiceMode state
    };
    
    console.log('[SendMessage] Payload:', payload);
    wsRef.current.send(JSON.stringify(payload));
    
    // Keep focus on input after sending
    setTimeout(() => {
      if (inputRef.current) {
        inputRef.current.focus();
      }
    }, 100);
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const handleCancel = () => {
    if (onCancel) {
      onCancel();
    } else {
      router.push('/organization-profiles');
    }
  };

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'row',
      height: '100%',
      backgroundColor: '#ffffff',
      border: '2px solid #ff6b35',
      borderRadius: '8px',
      overflow: 'hidden'
    }}>
      {/* Document Panel - Left Sidebar */}
      {documentEnhancement.showDocumentPanel && (
        <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
          <DocumentPanel
            profileId={currentProfileId}
            documents={documentEnhancement.documents}
            processingStatus={documentEnhancement.processingStatus}
            onUpload={documentEnhancement.handleDocumentUpload}
            uploading={documentEnhancement.uploadingDocument}
            selectedDocumentId={documentEnhancement.selectedDocumentId || undefined}
            onDocumentSelect={(docId) => documentEnhancement.setSelectedDocumentId(docId)}
          />
          <ProfileFieldsPanel
            fields={profileFields}
            onFieldClick={(fieldName) => {
              setInput(`Tell me about the ${fieldName.replace(/_/g, ' ')} field`);
            }}
          />
        </div>
      )}
      
      {/* Main Content Area */}
      <div style={{
        display: 'flex',
        flexDirection: 'column',
        flex: 1,
        height: '100%',
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
          {existingProfile ? 'Edit Organization Profile' : 'Create Organization Profile'}
          {voiceMode && ' (Voice Mode)'}
        </h2>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          {/* Document Panel Toggle */}
          <button
            onClick={() => documentEnhancement.setShowDocumentPanel(!documentEnhancement.showDocumentPanel)}
            style={{
              backgroundColor: documentEnhancement.showDocumentPanel ? '#28a745' : 'transparent',
              color: 'white',
              border: '1px solid white',
              borderRadius: '4px',
              padding: '0.25rem 0.5rem',
              fontSize: '0.8rem',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '0.25rem'
            }}
            title={documentEnhancement.showDocumentPanel ? 'Hide Documents' : 'Show Documents'}
          >
            📄 {documentEnhancement.showDocumentPanel ? 'Docs' : 'Docs'}
            {documentEnhancement.documents.length > 0 && (
              <span style={{
                backgroundColor: 'white',
                color: '#ff6b35',
                borderRadius: '50%',
                width: '18px',
                height: '18px',
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '0.7rem',
                fontWeight: 'bold',
                marginLeft: '0.25rem'
              }}>
                {documentEnhancement.documents.length}
              </span>
            )}
          </button>
          
          {/* Voice Mode Toggle */}
          {enableVoice && (
            <button
              onClick={toggleVoiceMode}
              style={{
                backgroundColor: voiceMode ? '#28a745' : 'transparent',
                color: 'white',
                border: '1px solid white',
                borderRadius: '4px',
                padding: '0.25rem 0.5rem',
                fontSize: '0.8rem',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '0.25rem'
              }}
            >
              🎤 {voiceMode ? 'Voice On' : 'Voice Off'}
            </button>
          )}
          
          {/* Connection Status */}
          <div style={{
            width: '8px',
            height: '8px',
            borderRadius: '50%',
            backgroundColor: connected ? '#28a745' : '#dc3545'
          }} />
          <span style={{ fontSize: '0.9rem' }}>
            {connected ? 'Connected' : 'Disconnected'}
          </span>
          
          <button
            onClick={handleCancel}
            style={{
              backgroundColor: 'transparent',
              color: 'white',
              border: '1px solid white',
              borderRadius: '4px',
              padding: '0.25rem 0.5rem',
              fontSize: '0.8rem',
              cursor: 'pointer'
            }}
          >
            Cancel
          </button>
        </div>
      </div>

      {/* Notification Banner */}
      {notification && (
        <div style={{
          padding: '0.75rem 1rem',
          backgroundColor: notification.type === 'success' ? '#d4edda' : notification.type === 'error' ? '#f8d7da' : '#d1ecf1',
          borderBottom: '1px solid ' + (notification.type === 'success' ? '#c3e6cb' : notification.type === 'error' ? '#f5c6cb' : '#bee5eb'),
          color: notification.type === 'success' ? '#155724' : notification.type === 'error' ? '#721c24' : '#0c5460',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          fontSize: '0.9rem'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span>{notification.type === 'success' ? '✓' : notification.type === 'error' ? '✗' : 'ℹ'}</span>
            <span>{notification.message}</span>
          </div>
          <button
            onClick={() => setNotification(null)}
            style={{
              background: 'none',
              border: 'none',
              color: 'inherit',
              cursor: 'pointer',
              fontSize: '1.2rem',
              padding: '0 0.5rem'
            }}
          >
            ×
          </button>
        </div>
      )}
      
      {/* Voice Status Bar */}
      {voiceMode && (
        <div style={{
          padding: '0.5rem 1rem',
          backgroundColor: isListening ? '#d4edda' : '#f8f9fa',
          borderBottom: '1px solid #e9ecef',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          fontSize: '0.9rem'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <span style={{ color: isListening ? '#155724' : '#6c757d' }}>
              {isListening ? '🎤 Listening...' : '🎤 Ready'}
            </span>
            {userInterrupted && (
              <span style={{ 
                color: '#ff6b35', 
                fontWeight: 'bold',
                animation: 'fadeIn 0.3s ease-in'
              }}>
                ✋ Interrupted
              </span>
            )}
            {partialTranscript && (
              <span style={{ color: '#6c757d', fontStyle: 'italic' }}>
                "{partialTranscript}"
              </span>
            )}
          </div>
          <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
            {/* Speech Speed Control */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <span style={{ fontSize: '0.8rem', color: '#6c757d' }}>Speed:</span>
              <select
                value={speechSpeed}
                onChange={(e) => setSpeechSpeed(e.target.value as 'slow' | 'medium' | 'fast' | 'faster' | 'fastest')}
                style={{
                  padding: '0.25rem 0.5rem',
                  fontSize: '0.8rem',
                  borderRadius: '4px',
                  border: '1px solid #ced4da',
                  backgroundColor: 'white',
                  cursor: 'pointer'
                }}
              >
                <option value="slow">🐢 0.75x Slow</option>
                <option value="medium">🚶 1.0x Normal</option>
                <option value="fast">🏃 1.25x Fast</option>
                <option value="faster">⚡ 1.5x Faster</option>
                <option value="fastest">🚀 2.0x Fastest</option>
              </select>
            </div>
            <button
              onClick={isRecording ? stopRecording : startRecording}
              disabled={!connected}
              style={{
                backgroundColor: isRecording ? '#dc3545' : '#28a745',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                padding: '0.25rem 0.5rem',
                fontSize: '0.8rem',
                cursor: connected ? 'pointer' : 'not-allowed'
              }}
            >
              {isRecording ? 'Stop' : 'Record'}
            </button>
          </div>
        </div>
      )}

      {/* Error Display */}
      {error && (
        <div style={{
          padding: '1rem',
          backgroundColor: '#f8d7da',
          color: '#721c24',
          borderBottom: '1px solid #f5c6cb',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center'
        }}>
          <span>{error}</span>
          <button
            onClick={() => setError(null)}
            style={{
              backgroundColor: 'transparent',
              color: '#721c24',
              border: 'none',
              cursor: 'pointer',
              fontSize: '1rem'
            }}
          >
            ×
          </button>
        </div>
      )}

      {/* Pre-Populated Answers Card */}
      {documentEnhancement.prePopulatedAnswers.length > 0 && (
        <div style={{ padding: '1rem', paddingBottom: '0' }}>
          <PrePopulatedAnswersCard
            answers={documentEnhancement.prePopulatedAnswers}
            onConfirm={documentEnhancement.handleConfirmPrePopulated}
            onDocumentClick={documentEnhancement.handleDocumentReferenceClick}
          />
        </div>
      )}
      
      {/* Conflict Resolution Card */}
      {documentEnhancement.conflicts.length > 0 && (
        <div style={{ padding: '1rem', paddingBottom: '0' }}>
          <ConflictResolutionCard
            conflicts={documentEnhancement.conflicts}
            onResolve={documentEnhancement.handleResolveConflict}
            onDocumentClick={documentEnhancement.handleDocumentReferenceClick}
          />
        </div>
      )}
      
      {/* Auto-Populate Suggestions Panel */}
      {showSuggestions && documentEnhancement.autoPopulateSuggestions.length > 0 && (
        <div style={{ padding: '1rem', paddingBottom: '0' }}>
          <SuggestionsPanel
            suggestions={documentEnhancement.autoPopulateSuggestions}
            onApply={(field, value) => {
              // Send suggestion application to agent via WebSocket
              if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
                wsRef.current.send(JSON.stringify({
                  type: 'apply_suggestion',
                  field,
                  value
                }));
              }
            }}
            onDismiss={() => setShowSuggestions(false)}
          />
        </div>
      )}
      
      {/* Chat Area */}
      <div
        ref={chatAreaRef}
        style={{
          flex: 1,
          padding: '1rem',
          overflowY: 'auto',
          backgroundColor: '#f8f9fa'
        }}
      >
        {!conversationStarted && messages.length === 0 && connected && (
          <div style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '4rem 2rem',
            textAlign: 'center'
          }}>
            <h2 style={{
              fontSize: '2rem',
              fontWeight: '600',
              color: '#ff6b35',
              marginBottom: '1rem'
            }}>
              Create Your Organization Profile
            </h2>
            <p style={{
              fontSize: '1.1rem',
              color: '#495057',
              maxWidth: '600px',
              marginBottom: '2rem',
              lineHeight: '1.6'
            }}>
              I'll help you create a comprehensive organization profile through an interactive conversation. 
              This profile will enable tailored security and risk assessments specific to your organization.
            </p>
            <button
              onClick={() => {
                setConversationStarted(true);
                setInput('start_profile_creation');
                setTimeout(() => sendMessage(), 100);
              }}
              style={{
                backgroundColor: '#ff6b35',
                color: '#ffffff',
                border: 'none',
                padding: '1rem 3rem',
                borderRadius: '8px',
                fontSize: '1.2rem',
                fontWeight: '600',
                cursor: 'pointer',
                boxShadow: '0 4px 6px rgba(0,0,0,0.1)',
                transition: 'all 0.3s ease'
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.backgroundColor = '#e55a2b';
                e.currentTarget.style.transform = 'translateY(-2px)';
                e.currentTarget.style.boxShadow = '0 6px 12px rgba(0,0,0,0.15)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.backgroundColor = '#ff6b35';
                e.currentTarget.style.transform = 'translateY(0)';
                e.currentTarget.style.boxShadow = '0 4px 6px rgba(0,0,0,0.1)';
              }}
            >
              Start Conversation
            </button>
          </div>
        )}

        {conversationStarted && messages.length === 0 && connected && (
          <div style={{
            textAlign: 'center',
            color: '#6c757d',
            padding: '2rem',
            fontStyle: 'italic'
          }}>
            Starting conversation...
          </div>
        )}

        {messages.map((message, index) => (
          <div
            key={index}
            style={{
              marginBottom: '1rem',
              display: 'flex',
              justifyContent: message.role === 'user' ? 'flex-end' : 'flex-start'
            }}
          >
            <div
              style={{
                maxWidth: '80%',
                padding: '0.75rem 1rem',
                borderRadius: '8px',
                backgroundColor: message.role === 'user' ? '#ff6b35' : '#ffffff',
                color: message.role === 'user' ? 'white' : '#333',
                border: message.role === 'assistant' ? '1px solid #e9ecef' : 'none',
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-word',
                position: 'relative'
              }}
            >
              {/* Voice indicators */}
              {message.isVoiceInput && (
                <div style={{
                  fontSize: '0.7rem',
                  color: message.role === 'user' ? 'rgba(255,255,255,0.8)' : '#6c757d',
                  marginBottom: '0.25rem'
                }}>
                  🎤 Voice input {message.confidence && `(${Math.round(message.confidence * 100)}% confidence)`}
                </div>
              )}
              
              {message.content && (
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
              )}
              
              {/* Document References */}
              {message.documentReferences && message.documentReferences.length > 0 && (
                <div style={{ marginTop: '0.5rem', display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                  {message.documentReferences.map((ref: any, refIndex: number) => (
                    <DocumentReference
                      key={refIndex}
                      documentName={ref.document_name}
                      pageNumber={ref.page}
                      section={ref.section}
                      confidence={ref.confidence}
                      onClick={() => documentEnhancement.handleDocumentReferenceClick(ref.document_id)}
                    />
                  ))}
                </div>
              )}
              
              {/* Audio playback button */}
              {message.audioUrl && (
                <div style={{ marginTop: '0.5rem' }}>
                  <button
                    onClick={() => playAudio(message.audioUrl)}
                    style={{
                      backgroundColor: '#28a745',
                      color: 'white',
                      border: 'none',
                      borderRadius: '4px',
                      padding: '0.25rem 0.5rem',
                      fontSize: '0.8rem',
                      cursor: 'pointer'
                    }}
                  >
                    🔊 Play Audio
                  </button>
                </div>
              )}
            </div>
          </div>
        ))}

        {loading && (
          <div style={{
            display: 'flex',
            justifyContent: 'flex-start',
            marginBottom: '1rem'
          }}>
            <div style={{
              padding: '0.75rem 1rem',
              borderRadius: '8px',
              backgroundColor: '#ffffff',
              border: '1px solid #e9ecef',
              color: '#6c757d',
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem'
            }}>
              <div style={{
                width: '8px',
                height: '8px',
                borderRadius: '50%',
                backgroundColor: '#ff6b35',
                animation: 'pulse 1.5s ease-in-out infinite'
              }} />
              <span style={{ fontStyle: 'italic' }}>
                {voiceMode ? 'Processing your voice input...' : 'Thinking...'}
              </span>
              <style>{`
                @keyframes pulse {
                  0%, 100% { opacity: 0.3; transform: scale(0.8); }
                  50% { opacity: 1; transform: scale(1.2); }
                }
              `}</style>
            </div>
          </div>
        )}
      </div>

      {/* Input Area */}
      <div style={{
        padding: '1rem',
        borderTop: '1px solid #e9ecef',
        backgroundColor: '#ffffff'
      }}>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder={
              !connected ? "Connecting..." :
              voiceMode ? "Type your response or use voice recording..." :
              "Type your response..."
            }
            disabled={!connected || loading}
            autoFocus
            style={{
              flex: 1,
              padding: '0.75rem',
              border: '1px solid #ced4da',
              borderRadius: '4px',
              resize: 'none',
              minHeight: '60px',
              fontFamily: 'inherit',
              fontSize: '0.9rem'
            }}
          />
          <button
            onClick={sendMessage}
            disabled={!input.trim() || !connected || loading}
            style={{
              padding: '0.75rem 1.5rem',
              backgroundColor: '#ff6b35',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: !input.trim() || !connected || loading ? 'not-allowed' : 'pointer',
              opacity: !input.trim() || !connected || loading ? 0.6 : 1,
              fontSize: '0.9rem',
              fontWeight: '600'
            }}
          >
            Send
          </button>
        </div>
        <div style={{
          fontSize: '0.8rem',
          color: '#6c757d',
          marginTop: '0.5rem'
        }}>
          {voiceMode 
            ? 'Press Enter to send, Shift+Enter for new line, or use voice recording'
            : 'Press Enter to send, Shift+Enter for new line'
          }
        </div>
      </div>
      </div> {/* Close Main Content Area */}
    </div>
  );
}