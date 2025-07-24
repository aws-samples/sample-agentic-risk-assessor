/**
 * AudioManager - Handles microphone access, recording, and audio playback
 * for the Voice Interactive Profile Builder
 */

export interface AudioSettings {
  sampleRate: number;
  channelCount: number;
  echoCancellation: boolean;
  noiseSuppression: boolean;
  autoGainControl: boolean;
  volume: number;
  sensitivity: number;
}

export interface AudioQualityMetrics {
  averageVolume: number;
  peakVolume: number;
  signalToNoiseRatio: number;
  quality: 'poor' | 'fair' | 'good' | 'excellent';
  issues: string[];
}

export class AudioManager {
  private mediaStream: MediaStream | null = null;
  private mediaRecorder: MediaRecorder | null = null;
  private audioContext: AudioContext | null = null;
  private analyser: AnalyserNode | null = null;
  private microphone: MediaStreamAudioSourceNode | null = null;
  private audioChunks: Blob[] = [];
  private isRecording = false;
  private isMonitoring = false;
  private volumeCallback: ((volume: number) => void) | null = null;
  private qualityCallback: ((metrics: AudioQualityMetrics) => void) | null = null;
  
  // Default audio settings optimized for voice
  private settings: AudioSettings = {
    sampleRate: 16000, // Optimal for speech recognition
    channelCount: 1, // Mono for voice
    echoCancellation: true,
    noiseSuppression: true,
    autoGainControl: true,
    volume: 1.0,
    sensitivity: 0.5
  };

  // Audio playback
  private currentAudio: HTMLAudioElement | null = null;
  private audioQueue: string[] = [];
  private isPlaying = false;

  constructor(settings?: Partial<AudioSettings>) {
    if (settings) {
      this.settings = { ...this.settings, ...settings };
    }
  }

  /**
   * Initialize audio context and request microphone access
   */
  async initialize(): Promise<boolean> {
    try {
      // Check if browser supports required APIs
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        throw new Error('Browser does not support audio recording');
      }

      // Request microphone access
      const constraints: MediaStreamConstraints = {
        audio: {
          sampleRate: this.settings.sampleRate,
          channelCount: this.settings.channelCount,
          echoCancellation: this.settings.echoCancellation,
          noiseSuppression: this.settings.noiseSuppression,
          autoGainControl: this.settings.autoGainControl
        }
      };

      this.mediaStream = await navigator.mediaDevices.getUserMedia(constraints);

      // Initialize audio context for analysis
      this.audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
      this.analyser = this.audioContext.createAnalyser();
      this.analyser.fftSize = 256;
      this.analyser.smoothingTimeConstant = 0.8;

      // Connect microphone to analyser
      this.microphone = this.audioContext.createMediaStreamSource(this.mediaStream);
      this.microphone.connect(this.analyser);

      console.log('AudioManager initialized successfully');
      return true;

    } catch (error) {
      console.error('Failed to initialize AudioManager:', error);
      throw new Error(`Microphone access denied or not available: ${error}`);
    }
  }

  /**
   * Start recording audio
   */
  async startRecording(): Promise<void> {
    if (!this.mediaStream) {
      throw new Error('AudioManager not initialized. Call initialize() first.');
    }

    if (this.isRecording) {
      console.warn('Recording already in progress');
      return;
    }

    try {
      // Create MediaRecorder
      const options: MediaRecorderOptions = {
        mimeType: this.getSupportedMimeType(),
        audioBitsPerSecond: 16000 // Optimized for speech
      };

      this.mediaRecorder = new MediaRecorder(this.mediaStream, options);
      this.audioChunks = [];

      // Set up event handlers
      this.mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          this.audioChunks.push(event.data);
        }
      };

      this.mediaRecorder.onstart = () => {
        console.log('Recording started');
        this.isRecording = true;
      };

      this.mediaRecorder.onstop = () => {
        console.log('Recording stopped');
        this.isRecording = false;
      };

      this.mediaRecorder.onerror = (event) => {
        console.error('MediaRecorder error:', event);
        this.isRecording = false;
      };

      // Start recording
      this.mediaRecorder.start(100); // Collect data every 100ms

      // Start monitoring audio levels
      this.startMonitoring();

    } catch (error) {
      console.error('Failed to start recording:', error);
      throw new Error(`Recording failed: ${error}`);
    }
  }

  /**
   * Stop recording audio
   */
  stopRecording(): Promise<Blob> {
    return new Promise((resolve, reject) => {
      if (!this.mediaRecorder || !this.isRecording) {
        reject(new Error('No active recording to stop'));
        return;
      }

      this.mediaRecorder.onstop = () => {
        const audioBlob = new Blob(this.audioChunks, { 
          type: this.getSupportedMimeType() 
        });
        this.audioChunks = [];
        this.stopMonitoring();
        resolve(audioBlob);
      };

      this.mediaRecorder.stop();
    });
  }

  /**
   * Get audio chunks for streaming
   */
  getAudioChunks(): Blob[] {
    return [...this.audioChunks];
  }

  /**
   * Clear audio chunks
   */
  clearAudioChunks(): void {
    this.audioChunks = [];
  }

  /**
   * Start monitoring audio levels and quality
   */
  private startMonitoring(): void {
    if (!this.analyser || this.isMonitoring) return;

    this.isMonitoring = true;
    const bufferLength = this.analyser.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);

    const monitor = () => {
      if (!this.isMonitoring || !this.analyser) return;

      this.analyser.getByteFrequencyData(dataArray);

      // Calculate volume metrics
      const sum = dataArray.reduce((acc, value) => acc + value, 0);
      const average = sum / bufferLength;
      const peak = Math.max.apply(null, Array.from(dataArray));
      const volume = average / 255; // Normalize to 0-1

      // Call volume callback
      if (this.volumeCallback) {
        this.volumeCallback(volume);
      }

      // Calculate quality metrics
      const metrics = this.calculateQualityMetrics(dataArray, average, peak);
      if (this.qualityCallback) {
        this.qualityCallback(metrics);
      }

      // Continue monitoring
      requestAnimationFrame(monitor);
    };

    monitor();
  }

  /**
   * Stop monitoring audio levels
   */
  private stopMonitoring(): void {
    this.isMonitoring = false;
  }

  /**
   * Calculate audio quality metrics
   */
  private calculateQualityMetrics(
    frequencyData: Uint8Array, 
    average: number, 
    peak: number
  ): AudioQualityMetrics {
    const issues: string[] = [];
    let quality: 'poor' | 'fair' | 'good' | 'excellent' = 'good';

    // Check volume levels
    const normalizedAverage = average / 255;
    const normalizedPeak = peak / 255;

    if (normalizedAverage < 0.1) {
      issues.push('Volume too low');
      quality = 'poor';
    } else if (normalizedAverage > 0.9) {
      issues.push('Volume too high - possible clipping');
      quality = 'fair';
    }

    if (normalizedPeak > 0.95) {
      issues.push('Audio clipping detected');
      quality = 'poor';
    }

    // Estimate signal-to-noise ratio
    const signalPower = frequencyData.slice(10, 50).reduce((acc, val) => acc + val * val, 0);
    const noisePower = frequencyData.slice(100, 128).reduce((acc, val) => acc + val * val, 0);
    const snr = noisePower > 0 ? 10 * Math.log10(signalPower / noisePower) : 0;

    if (snr < 10) {
      issues.push('High background noise');
      quality = quality === 'good' ? 'fair' : quality;
    }

    // Check for silence
    if (normalizedAverage < 0.05 && normalizedPeak < 0.1) {
      issues.push('No audio signal detected');
      quality = 'poor';
    }

    // Determine overall quality
    if (issues.length === 0 && snr > 20 && normalizedAverage > 0.2) {
      quality = 'excellent';
    }

    return {
      averageVolume: normalizedAverage,
      peakVolume: normalizedPeak,
      signalToNoiseRatio: snr,
      quality,
      issues
    };
  }

  /**
   * Set volume callback for real-time monitoring
   */
  setVolumeCallback(callback: (volume: number) => void): void {
    this.volumeCallback = callback;
  }

  /**
   * Set quality callback for real-time monitoring
   */
  setQualityCallback(callback: (metrics: AudioQualityMetrics) => void): void {
    this.qualityCallback = callback;
  }

  /**
   * Play audio from base64 data chunks (streamed from backend)
   */
  async playAudioFromChunks(chunks: string[], audioFormat: string = 'mp3'): Promise<void> {
    return new Promise((resolve, reject) => {
      try {
        // Stop current audio if playing
        this.stopAudio();

        // Combine all chunks into single base64 string
        const combinedBase64 = chunks.join('');
        
        // Convert base64 to blob
        const binaryString = atob(combinedBase64);
        const bytes = new Uint8Array(binaryString.length);
        for (let i = 0; i < binaryString.length; i++) {
          bytes[i] = binaryString.charCodeAt(i);
        }
        
        const mimeType = this.getMimeTypeForFormat(audioFormat);
        const audioBlob = new Blob([bytes], { type: mimeType });
        const audioUrl = URL.createObjectURL(audioBlob);

        const audio = new Audio(audioUrl);
        this.currentAudio = audio;
        audio.volume = this.settings.volume;
        
        audio.onloadeddata = () => {
          console.log('Streamed audio loaded successfully');
        };

        audio.onplay = () => {
          this.isPlaying = true;
          console.log('Streamed audio playback started');
        };

        audio.onended = () => {
          this.isPlaying = false;
          this.currentAudio = null;
          URL.revokeObjectURL(audioUrl);
          console.log('Streamed audio playback ended');
          
          // Play next audio in queue if available
          this.playNextInQueue();
          resolve();
        };

        audio.onerror = (error) => {
          this.isPlaying = false;
          this.currentAudio = null;
          URL.revokeObjectURL(audioUrl);
          console.error('Streamed audio playback error:', error);
          reject(new Error('Audio playback failed'));
        };

        audio.onpause = () => {
          this.isPlaying = false;
          console.log('Streamed audio playback paused');
        };

        // Start playback
        audio.play().catch(reject);

      } catch (error) {
        reject(error);
      }
    });
  }

  /**
   * Get MIME type for audio format
   */
  private getMimeTypeForFormat(format: string): string {
    const mimeTypes: { [key: string]: string } = {
      'mp3': 'audio/mpeg',
      'ogg': 'audio/ogg',
      'ogg_vorbis': 'audio/ogg',
      'wav': 'audio/wav',
      'pcm': 'audio/pcm'
    };
    return mimeTypes[format] || 'audio/mpeg';
  }

  /**
   * Play audio from URL (legacy support - not recommended)
   */
  async playAudio(audioUrl: string): Promise<void> {
    return new Promise((resolve, reject) => {
      try {
        // Stop current audio if playing
        this.stopAudio();

        const audio = new Audio(audioUrl);
        this.currentAudio = audio;

        audio.volume = this.settings.volume;
        
        audio.onloadeddata = () => {
          console.log('Audio loaded successfully');
        };

        audio.onplay = () => {
          this.isPlaying = true;
          console.log('Audio playback started');
        };

        audio.onended = () => {
          this.isPlaying = false;
          this.currentAudio = null;
          console.log('Audio playback ended');
          
          // Play next audio in queue if available
          this.playNextInQueue();
          resolve();
        };

        audio.onerror = (error) => {
          this.isPlaying = false;
          this.currentAudio = null;
          console.error('Audio playback error:', error);
          reject(new Error('Audio playback failed'));
        };

        audio.onpause = () => {
          this.isPlaying = false;
          console.log('Audio playback paused');
        };

        // Start playback
        audio.play().catch(reject);

      } catch (error) {
        reject(error);
      }
    });
  }

  /**
   * Play audio from blob data
   */
  async playAudioBlob(audioBlob: Blob): Promise<void> {
    const audioUrl = URL.createObjectURL(audioBlob);
    try {
      await this.playAudio(audioUrl);
    } finally {
      URL.revokeObjectURL(audioUrl);
    }
  }

  /**
   * Queue audio for sequential playback
   */
  queueAudio(audioUrl: string): void {
    if (this.isPlaying) {
      this.audioQueue.push(audioUrl);
    } else {
      this.playAudio(audioUrl).catch(console.error);
    }
  }

  /**
   * Play next audio in queue
   */
  private playNextInQueue(): void {
    if (this.audioQueue.length > 0) {
      const nextUrl = this.audioQueue.shift()!;
      this.playAudio(nextUrl).catch(console.error);
    }
  }

  /**
   * Stop current audio playback
   */
  stopAudio(): void {
    if (this.currentAudio) {
      this.currentAudio.pause();
      this.currentAudio.currentTime = 0;
      this.currentAudio = null;
    }
    this.isPlaying = false;
  }

  /**
   * Pause current audio playback
   */
  pauseAudio(): void {
    if (this.currentAudio && !this.currentAudio.paused) {
      this.currentAudio.pause();
    }
  }

  /**
   * Resume audio playback
   */
  resumeAudio(): void {
    if (this.currentAudio && this.currentAudio.paused) {
      this.currentAudio.play().catch(console.error);
    }
  }

  /**
   * Set audio volume (0.0 to 1.0)
   */
  setVolume(volume: number): void {
    this.settings.volume = Math.max(0, Math.min(1, volume));
    if (this.currentAudio) {
      this.currentAudio.volume = this.settings.volume;
    }
  }

  /**
   * Set microphone sensitivity
   */
  setMicrophoneSensitivity(sensitivity: number): void {
    this.settings.sensitivity = Math.max(0, Math.min(1, sensitivity));
    // Note: Actual sensitivity adjustment would require audio processing
    console.log(`Microphone sensitivity set to: ${sensitivity}`);
  }

  /**
   * Enable/disable noise cancellation
   */
  async setNoiseCancellation(enabled: boolean): Promise<void> {
    this.settings.noiseSuppression = enabled;
    
    // To apply this setting, we need to restart the media stream
    if (this.mediaStream) {
      await this.reinitializeStream();
    }
  }

  /**
   * Get current audio settings
   */
  getSettings(): AudioSettings {
    return { ...this.settings };
  }

  /**
   * Update audio settings
   */
  async updateSettings(newSettings: Partial<AudioSettings>): Promise<void> {
    const oldSettings = { ...this.settings };
    this.settings = { ...this.settings, ...newSettings };

    // Check if we need to reinitialize the stream
    const streamSettings = ['sampleRate', 'channelCount', 'echoCancellation', 'noiseSuppression', 'autoGainControl'];
    const needsReinit = streamSettings.some(key => 
      oldSettings[key as keyof AudioSettings] !== this.settings[key as keyof AudioSettings]
    );

    if (needsReinit && this.mediaStream) {
      await this.reinitializeStream();
    }
  }

  /**
   * Reinitialize media stream with new settings
   */
  private async reinitializeStream(): Promise<void> {
    const wasRecording = this.isRecording;
    
    // Stop current recording if active
    if (wasRecording) {
      this.stopRecording().catch(console.error);
    }

    // Clean up current stream
    this.cleanup();

    // Reinitialize with new settings
    await this.initialize();

    // Resume recording if it was active
    if (wasRecording) {
      await this.startRecording();
    }
  }

  /**
   * Get supported MIME type for recording
   */
  private getSupportedMimeType(): string {
    const types = [
      'audio/webm;codecs=opus',
      'audio/webm',
      'audio/mp4',
      'audio/ogg;codecs=opus',
      'audio/wav'
    ];

    for (const type of types) {
      if (MediaRecorder.isTypeSupported(type)) {
        return type;
      }
    }

    return 'audio/webm'; // Fallback
  }

  /**
   * Check if currently recording
   */
  isCurrentlyRecording(): boolean {
    return this.isRecording;
  }

  /**
   * Check if currently playing audio
   */
  isCurrentlyPlaying(): boolean {
    return this.isPlaying;
  }

  /**
   * Get current volume level (0.0 to 1.0)
   */
  getCurrentVolume(): number {
    return this.settings.volume;
  }

  /**
   * Check if microphone is available
   */
  static async checkMicrophoneAvailability(): Promise<boolean> {
    try {
      const devices = await navigator.mediaDevices.enumerateDevices();
      return devices.some(device => device.kind === 'audioinput');
    } catch (error) {
      console.error('Error checking microphone availability:', error);
      return false;
    }
  }

  /**
   * Get available audio input devices
   */
  static async getAudioInputDevices(): Promise<MediaDeviceInfo[]> {
    try {
      const devices = await navigator.mediaDevices.enumerateDevices();
      return devices.filter(device => device.kind === 'audioinput');
    } catch (error) {
      console.error('Error getting audio input devices:', error);
      return [];
    }
  }

  /**
   * Clean up resources
   */
  cleanup(): void {
    // Stop recording
    if (this.isRecording && this.mediaRecorder) {
      this.mediaRecorder.stop();
    }

    // Stop monitoring
    this.stopMonitoring();

    // Stop audio playback
    this.stopAudio();

    // Clean up audio context
    if (this.audioContext && this.audioContext.state !== 'closed') {
      this.audioContext.close().catch(console.error);
    }

    // Clean up media stream
    if (this.mediaStream) {
      this.mediaStream.getTracks().forEach(track => track.stop());
    }

    // Reset references
    this.mediaStream = null;
    this.mediaRecorder = null;
    this.audioContext = null;
    this.analyser = null;
    this.microphone = null;
    this.audioChunks = [];
    this.isRecording = false;
    this.isMonitoring = false;
    this.volumeCallback = null;
    this.qualityCallback = null;
    this.currentAudio = null;
    this.audioQueue = [];
    this.isPlaying = false;

    console.log('AudioManager cleaned up');
  }
}

export default AudioManager;