#!/usr/bin/env python3
"""
Voice Handler for Organization Profile Agent
Handles voice input/output processing using AWS Transcribe and Polly
"""
import asyncio
import json
import logging
import os
import uuid
import base64
import re
from typing import Dict, Any, Optional, AsyncGenerator, Callable
from datetime import datetime, timedelta
import boto3
from botocore.exceptions import ClientError
import websockets
import threading
import queue
# Simplified approach - remove amazon-transcribe dependency for now
# from amazon_transcribe.client import TranscribeStreamingClient
# from amazon_transcribe.handlers import TranscriptResultStreamHandler
# from amazon_transcribe.model import TranscriptEvent

logger = logging.getLogger(__name__)

class TranscribeStreamHandler:
    """Handler for AWS Transcribe streaming results with accuracy and error handling"""
    
    def __init__(self, session_id: str, callback: Callable[[str, Dict], None]):
        self.session_id = session_id
        self.callback = callback
        self.partial_transcript = ""
        self.final_transcript = ""
        self.speech_end_timeout = 2.0  # seconds
        self.last_speech_time = None
        
        # Quality tracking
        self.confidence_threshold = 0.7  # Minimum confidence for good quality
        self.low_confidence_count = 0
        self.total_transcripts = 0
        self.confidence_scores = []
        
        # Error handling
        self.consecutive_errors = 0
        self.max_consecutive_errors = 3
        self.retry_count = 0
        self.max_retries = 2
        
    async def handle_transcript_event(self, transcript_data: dict):
        """Simplified transcript event handler for testing"""
        try:
            # Simplified handling for testing
            transcript = transcript_data.get('text', '')
            confidence = transcript_data.get('confidence', 0.95)
            is_final = transcript_data.get('is_final', True)
            
            if is_final:
                self.final_transcript = transcript
                self.total_transcripts += 1
                self.confidence_scores.append(confidence)
                
                # Send final result to callback
                await self.callback(self.session_id, {
                    'type': 'process_final_transcript',  # Changed to trigger agent flow
                    'transcript': transcript,  # Changed key name to match server expectation
                    'confidence': confidence,
                    'is_final': True
                })
            else:
                # Handle partial results
                self.partial_transcript = transcript
                await self.callback(self.session_id, {
                    'type': 'partial_transcript',
                    'text': transcript,
                    'confidence': confidence,
                    'is_final': False
                })
                        
        except Exception as e:
            logger.error(f"Error handling transcript event for session {self.session_id}: {str(e)}")
            await self.callback(self.session_id, {
                'type': 'transcription_error',
                'message': f'Transcription error: {str(e)}'
            })
    
    def _assess_transcript_quality(self, transcript: str, confidence: float) -> Dict[str, Any]:
        """Assess the quality of a transcript"""
        quality_score = 'high'
        issues = []
        
        # Confidence-based assessment
        if confidence < 0.5:
            quality_score = 'poor'
            issues.append('very_low_confidence')
        elif confidence < self.confidence_threshold:
            quality_score = 'medium'
            issues.append('low_confidence')
        
        # Text-based assessment
        if len(transcript.strip()) == 0:
            quality_score = 'poor'
            issues.append('empty_transcript')
        elif len(transcript.split()) < 2:
            issues.append('very_short')
        
        # Check for common transcription artifacts
        if '[inaudible]' in transcript.lower() or '[unclear]' in transcript.lower():
            quality_score = 'poor'
            issues.append('inaudible_content')
        
        return {
            'score': quality_score,
            'confidence': confidence,
            'issues': issues,
            'word_count': len(transcript.split()),
            'character_count': len(transcript)
        }
    
    def _should_trigger_fallback(self) -> bool:
        """Determine if we should suggest fallback to text input"""
        if self.total_transcripts < 3:
            return False
        
        # Calculate recent quality metrics
        recent_scores = self.confidence_scores[-5:] if len(self.confidence_scores) >= 5 else self.confidence_scores
        avg_confidence = sum(recent_scores) / len(recent_scores)
        
        # Trigger fallback if average confidence is consistently low
        return avg_confidence < 0.6 or (self.low_confidence_count / self.total_transcripts) > 0.7
    
    async def _handle_transcription_failure(self):
        """Handle repeated transcription failures"""
        logger.error(f"Multiple consecutive transcription errors for session {self.session_id}")
        
        await self.callback(self.session_id, {
            'type': 'transcription_failure',
            'message': 'Multiple transcription errors detected. Please check your microphone and network connection.',
            'suggestion': 'restart_session',
            'fallback_available': True
        })
        
        # Reset error count after handling
        self.consecutive_errors = 0
    
    def is_speech_complete(self) -> bool:
        """Check if speech appears to be complete based on timeout"""
        if self.last_speech_time is None:
            return False
            
        time_since_speech = (datetime.utcnow() - self.last_speech_time).total_seconds()
        return time_since_speech >= self.speech_end_timeout

class VoiceHandler:
    """Handles voice processing for the Organization Profile Agent"""
    
    def __init__(self):
        self.transcribe_client = boto3.client('transcribe')
        try:
            from amazon_transcribe.client import TranscribeStreamingClient
            self.transcribe_streaming_client = TranscribeStreamingClient(region=os.getenv('AWS_DEFAULT_REGION', 'us-east-1'))
            logger.info("Transcribe streaming client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize transcribe streaming client: {str(e)}")
            self.transcribe_streaming_client = None
        self.polly_client = boto3.client('polly')
        self.s3_client = boto3.client('s3')
        
        # Configuration from environment variables
        self.voice_audio_bucket = os.getenv('VOICE_AUDIO_BUCKET', 'risk-agent-voice-audio-7ep7ngxz')  # Use voice bucket from Terraform
        self.transcribe_vocabulary = os.getenv('TRANSCRIBE_VOCABULARY_NAME', 'risk-agent-org-profile-vocab')
        self.region = os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
        
        # Voice session storage
        self.active_sessions: Dict[str, Dict] = {}
        self.streaming_sessions: Dict[str, Dict] = {}
        
        # Audio cache for HTTP streaming (TTL: 1 hour)
        self.audio_cache: Dict[str, Dict] = {}
        
        # Default voice settings with neural voice support
        self.default_voice_settings = {
            'voice_id': 'Joanna',  # AWS Polly neural voice
            'engine': 'neural',
            'language_code': 'en-US',
            'speech_rate': 'medium',
            'volume': 'medium',
            'output_format': 'mp3',
            'sample_rate': '22050'
        }
        
        # Available neural voices for different use cases
        self.available_voices = {
            'en-US': {
                'female': ['Joanna', 'Kimberly', 'Salli', 'Kendra', 'Ivy'],
                'male': ['Matthew', 'Justin', 'Joey']
            },
            'en-GB': {
                'female': ['Amy', 'Emma'],
                'male': ['Brian']
            }
        }
        
        # Voice characteristics for different conversation contexts
        self.voice_profiles = {
            'professional': {
                'voice_id': 'Joanna',
                'speech_rate': 'medium',
                'volume': 'medium',
                'pitch': 'medium'
            },
            'friendly': {
                'voice_id': 'Kimberly',
                'speech_rate': 'medium',
                'volume': 'medium',
                'pitch': 'medium'
            },
            'authoritative': {
                'voice_id': 'Matthew',
                'speech_rate': 'slow',
                'volume': 'loud',
                'pitch': 'low'
            }
        }
        
        # Default transcription settings
        self.default_transcription_settings = {
            'language_code': 'en-US',
            'media_sample_rate_hz': 16000,
            'media_encoding': 'pcm',
            'enable_partial_results_stabilization': True,
            'partial_results_stability': 'medium'
        }
        
        # Organization-specific vocabulary for better accuracy
        self.organization_vocabulary = [
            'organization', 'profile', 'compliance', 'governance', 'risk',
            'assessment', 'framework', 'controls', 'audit', 'security',
            'infrastructure', 'cloud', 'AWS', 'Azure', 'GCP',
            'NIST', 'ISO', 'SOC', 'GDPR', 'HIPAA', 'PCI'
        ]
    
    async def start_voice_session(self, session_id: str, user_id: str, voice_settings: Dict = None, transcription_settings: Dict = None) -> Dict[str, Any]:
        """Initialize a new voice session with streaming transcription"""
        try:
            # Merge with default settings
            voice_config = {**self.default_voice_settings, **(voice_settings or {})}
            transcription_config = {**self.default_transcription_settings, **(transcription_settings or {})}
            
            session_data = {
                'session_id': session_id,
                'user_id': user_id,
                'voice_settings': voice_config,
                'transcription_settings': transcription_config,
                'transcription_stream': None,
                'stream_handler': None,
                'audio_chunks': [],
                'conversation_history': [],
                'created_at': datetime.utcnow(),
                'status': 'active',
                'is_listening': False,
                'voice_mode': False  # Initialize to text mode by default
            }
            
            self.active_sessions[session_id] = session_data
            
            logger.info(f"Voice session started: {session_id}")
            return {
                'status': 'success',
                'session_id': session_id,
                'voice_settings': voice_config,
                'transcription_settings': transcription_config
            }
            
        except Exception as e:
            logger.error(f"Failed to start voice session {session_id}: {str(e)}")
            return {
                'status': 'error',
                'message': f'Failed to start voice session: {str(e)}'
            }
    
    async def create_custom_vocabulary(self, vocabulary_name: str = None) -> Dict[str, Any]:
        """Create or update custom vocabulary for organization profiles"""
        try:
            if not vocabulary_name:
                vocabulary_name = f"organization-profile-vocab-{int(datetime.utcnow().timestamp())}"
            
            # Create vocabulary with organization-specific terms
            vocabulary_params = {
                'VocabularyName': vocabulary_name,
                'LanguageCode': 'en-US',
                'Phrases': self.organization_vocabulary
            }
            
            # Check if vocabulary already exists
            try:
                existing_vocab = self.transcribe_client.get_vocabulary(VocabularyName=vocabulary_name)
                if existing_vocab['VocabularyState'] == 'READY':
                    logger.info(f"Using existing vocabulary: {vocabulary_name}")
                    return {
                        'status': 'success',
                        'vocabulary_name': vocabulary_name,
                        'message': 'Using existing vocabulary'
                    }
            except ClientError as e:
                if e.response['Error']['Code'] != 'BadRequestException':
                    raise e
            
            # Create new vocabulary
            self.transcribe_client.create_vocabulary(**vocabulary_params)
            
            logger.info(f"Created custom vocabulary: {vocabulary_name}")
            return {
                'status': 'success',
                'vocabulary_name': vocabulary_name,
                'message': 'Custom vocabulary created'
            }
            
        except Exception as e:
            logger.error(f"Failed to create custom vocabulary: {str(e)}")
            return {
                'status': 'error',
                'message': f'Failed to create vocabulary: {str(e)}'
            }
    
    async def start_streaming_transcription(self, session_id: str, websocket_callback) -> Dict[str, Any]:
        """Start real-time streaming transcription using AWS Transcribe Streaming"""
        try:
            if session_id not in self.active_sessions:
                return {'status': 'error', 'message': 'Voice session not found'}
            
            session = self.active_sessions[session_id]
            
            # Try to import AWS Transcribe Streaming
            try:
                from amazon_transcribe.client import TranscribeStreamingClient
                from amazon_transcribe.handlers import TranscriptResultStreamHandler
                from amazon_transcribe.model import TranscriptEvent
                logger.info("AWS Transcribe Streaming available - using real-time transcription")
                
                # Create streaming transcribe client
                client = TranscribeStreamingClient(region=self.region)
                
                # Start streaming transcription
                stream = await client.start_stream_transcription(
                    language_code='en-US',
                    media_sample_rate_hz=16000,
                    media_encoding='pcm'
                )
                
                # Create stream handler for real-time results with proper initialization
                class StreamingHandler(TranscriptResultStreamHandler):
                    def __init__(self, transcript_result_stream, callback_func):
                        super().__init__(transcript_result_stream)
                        self.callback = callback_func
                        self.partial_transcript = ""
                        self.sentence_buffer = ""
                    
                    async def handle_transcript_event(self, transcript_event: TranscriptEvent):
                        results = transcript_event.transcript.results
                        
                        for result in results:
                            if result.alternatives:
                                transcript = result.alternatives[0].transcript
                                confidence = getattr(result.alternatives[0], 'confidence', 0.95)
                                
                                if result.is_partial:
                                    # Send partial results for real-time feedback
                                    await self.callback({
                                        'type': 'partial_transcript',
                                        'text': transcript,
                                        'confidence': confidence,
                                        'is_partial': True
                                    })
                                    self.partial_transcript = transcript
                                else:
                                    # Final result - check for sentence completion
                                    self.sentence_buffer += transcript + " "
                                    
                                    # Send if we have a complete sentence or phrase
                                    if any(punct in transcript for punct in ['.', '!', '?']) or len(self.sentence_buffer.strip()) > 50:
                                        final_text = self.sentence_buffer.strip()
                                        self.sentence_buffer = ""
                                        
                                        await self.callback({
                                            'type': 'final_transcript',
                                            'text': final_text,
                                            'confidence': confidence,
                                            'is_final': True
                                        })
                
                # Initialize handler with the transcript result stream
                stream_handler = StreamingHandler(stream.output_stream, websocket_callback)
                
                # Store stream info
                session['streaming_transcribe'] = {
                    'client': client,
                    'stream': stream,
                    'handler': stream_handler,
                    'active': True
                }
                
                # Handle stream in background
                asyncio.create_task(self._handle_streaming_transcription(session_id, stream, stream_handler))
                
                logger.info(f"Real-time streaming transcription started for session: {session_id}")
                return {
                    'status': 'success',
                    'message': 'Real-time streaming transcription started',
                    'mode': 'streaming'
                }
                
            except ImportError as e:
                logger.warning(f"AWS Transcribe Streaming not available: {e}")
                # Use simplified streaming approach
                return await self._start_simplified_streaming(session_id, websocket_callback)
            
        except Exception as e:
            logger.error(f"Failed to start streaming transcription: {str(e)}")
            # Fallback to simplified streaming
            logger.info("Falling back to simplified streaming")
            return await self._start_simplified_streaming(session_id, websocket_callback)
    
    async def _handle_streaming_transcription(self, session_id: str, stream, handler):
        """Handle streaming transcription events"""
        try:
            async for event in stream.output_stream:
                await handler.handle_transcript_event(event)
        except Exception as e:
            logger.error(f"Streaming transcription error for session {session_id}: {str(e)}")
            if session_id in self.active_sessions:
                session = self.active_sessions[session_id]
                if 'streaming_transcribe' in session:
                    session['streaming_transcribe']['active'] = False
                
                # Fall back to simplified streaming to keep voice working
                logger.info(f"Falling back to simplified streaming for session {session_id}")
                try:
                    # Set up simplified streaming as fallback
                    session['streaming_active'] = True
                    session['audio_buffer'] = []
                    session['is_listening'] = True  # Keep listening active
                    logger.info(f"Simplified streaming fallback activated for session {session_id}")
                except Exception as fallback_error:
                    logger.error(f"Failed to activate simplified streaming fallback: {str(fallback_error)}")
                    session['is_listening'] = False
    
    async def _start_simplified_streaming(self, session_id: str, websocket_callback) -> Dict[str, Any]:
        """Start simplified streaming transcription without AWS Transcribe Streaming dependency"""
        try:
            session = self.active_sessions[session_id]
            
            # Set up simplified streaming
            session['streaming_active'] = True
            session['streaming_callback'] = websocket_callback
            session['audio_buffer'] = []
            session['is_listening'] = True  # ← Fix: Set listening flag
            
            logger.info(f"Simplified streaming transcription started for session: {session_id}")
            return {
                'status': 'success',
                'message': 'Simplified streaming transcription started',
                'mode': 'simplified'
            }
            
        except Exception as e:
            logger.error(f"Failed to start simplified streaming: {str(e)}")
            return {
                'status': 'error',
                'message': f'Failed to start simplified streaming: {str(e)}'
            }
    
    async def send_audio_to_stream(self, session_id: str, audio_data: bytes) -> Dict[str, Any]:
        """Send audio data to streaming transcription"""
        try:
            if session_id not in self.active_sessions:
                return {'status': 'error', 'message': 'Session not found'}
            
            session = self.active_sessions[session_id]
            streaming_info = session.get('streaming_transcribe')
            
            if not streaming_info or not streaming_info.get('active'):
                return {'status': 'error', 'message': 'Streaming transcription not active'}
            
            # Send audio to stream
            stream = streaming_info['stream']
            await stream.input_stream.send_audio_event(audio_chunk=audio_data)
            
            return {'status': 'success', 'bytes_sent': len(audio_data)}
            
        except Exception as e:
            logger.error(f"Failed to send audio to stream: {str(e)}")
            return {'status': 'error', 'message': str(e)}
    
    async def stop_streaming_transcription(self, session_id: str) -> Dict[str, Any]:
        """Stop streaming transcription"""
        try:
            if session_id not in self.active_sessions:
                return {'status': 'error', 'message': 'Session not found'}
            
            session = self.active_sessions[session_id]
            streaming_info = session.get('streaming_transcribe')
            
            if streaming_info:
                streaming_info['active'] = False
                
                # Close stream
                if 'stream' in streaming_info:
                    await streaming_info['stream'].input_stream.end_stream()
                
                # Clean up
                del session['streaming_transcribe']
            
            logger.info(f"Streaming transcription stopped for session: {session_id}")
            return {'status': 'success', 'message': 'Streaming transcription stopped'}
            
        except Exception as e:
            logger.error(f"Failed to stop streaming transcription: {str(e)}")
            return {'status': 'error', 'message': str(e)}
    
    async def _handle_streaming_transcription(self, session_id: str, stream, handler):
        """Handle streaming transcription events"""
        try:
            async for event in stream.output_stream:
                await handler.handle_transcript_event(event)
        except Exception as e:
            logger.error(f"Streaming transcription error for session {session_id}: {str(e)}")
            if session_id in self.active_sessions:
                session = self.active_sessions[session_id]
                if 'streaming_transcribe' in session:
                    session['streaming_transcribe']['active'] = False
    
    async def send_audio_to_stream(self, session_id: str, audio_data: bytes) -> Dict[str, Any]:
        """Process streaming audio data and simulate real-time transcription"""
        try:
            if session_id not in self.active_sessions:
                return {'status': 'error', 'message': 'Session not found'}
            
            session = self.active_sessions[session_id]
            
            if not session.get('streaming_active'):
                return {'status': 'error', 'message': 'Streaming not active'}
            
            # Accumulate audio for processing
            if 'audio_buffer' not in session:
                session['audio_buffer'] = []
            
            session['audio_buffer'].append(audio_data)
            
            # Process when we have enough audio (~1 second worth)
            if len(session['audio_buffer']) >= 50:  # ~1 second at 50 chunks/sec
                # Simulate real-time transcription with accumulated audio
                combined_audio = b''.join(session['audio_buffer'])
                session['audio_buffer'] = []
                
                # For now, simulate partial transcription
                callback = session.get('streaming_callback')
                if callback:
                    await callback({
                        'type': 'partial_transcript',
                        'text': 'Listening...',
                        'confidence': 0.8,
                        'is_partial': True
                    })
            
            return {'status': 'success', 'bytes_processed': len(audio_data)}
            
        except Exception as e:
            logger.error(f"Failed to process streaming audio: {str(e)}")
            return {'status': 'error', 'message': str(e)}
    
    async def stop_streaming_transcription(self, session_id: str) -> Dict[str, Any]:
        """Stop streaming transcription"""
        try:
            if session_id not in self.active_sessions:
                return {'status': 'error', 'message': 'Session not found'}
            
            session = self.active_sessions[session_id]
            session['streaming_active'] = False
            session['is_listening'] = False  # ← Fix: Set listening flag to false
            
            # Clean up
            if 'audio_buffer' in session:
                del session['audio_buffer']
            if 'streaming_callback' in session:
                del session['streaming_callback']
            
            logger.info(f"Streaming transcription stopped for session: {session_id}")
            return {'status': 'success', 'message': 'Streaming transcription stopped'}
            
        except Exception as e:
            logger.error(f"Failed to stop streaming transcription: {str(e)}")
            return {'status': 'error', 'message': str(e)}
        """Start real-time transcription stream using AWS Transcribe"""
        try:
            if session_id not in self.active_sessions:
                return {
                    'status': 'error',
                    'message': 'Voice session not found'
                }
            
            if not self.transcribe_streaming_client:
                logger.error("Transcribe streaming client not available")
                return {
                    'status': 'error',
                    'message': 'Transcribe streaming client not initialized'
                }
            
            session = self.active_sessions[session_id]
            
            # Create stream handler
            stream_handler = TranscribeStreamHandler(session_id, callback)
            session['stream_handler'] = stream_handler
            session['is_listening'] = True
            session['transcript_callback'] = callback
            
            # Actually create the AWS Transcribe stream
            try:
                stream = await self.transcribe_streaming_client.start_stream_transcription(
                    language_code=session['transcription_settings']['language_code'],
                    media_sample_rate_hz=session['transcription_settings']['media_sample_rate_hz'],
                    media_encoding=session['transcription_settings']['media_encoding'],
                    enable_partial_results_stabilization=True,
                    partial_results_stability='medium'
                )
                session['transcription_stream'] = stream
                
                # Start handling the stream in background
                import asyncio
                asyncio.create_task(self._handle_transcription_stream(session_id, stream, stream_handler))
                
            except Exception as stream_error:
                logger.error(f"Failed to create transcription stream: {str(stream_error)}")
                return {
                    'status': 'error',
                    'message': f'Failed to create transcription stream: {str(stream_error)}'
                }
            
            logger.info(f"Real transcription stream started for session: {session_id}")
            return {
                'status': 'success',
                'message': 'Real-time transcription stream started',
                'vocabulary': self.transcribe_vocabulary
            }
            
        except Exception as e:
            logger.error(f"Failed to start transcription stream for session {session_id}: {str(e)}")
            return {
                'status': 'error',
                'message': f'Failed to start transcription stream: {str(e)}'
            }
    
    async def _check_vocabulary_status(self, vocabulary_name: str) -> str:
        """Check the status of a custom vocabulary"""
        try:
            response = self.transcribe_client.get_vocabulary(VocabularyName=vocabulary_name)
            return response['VocabularyState']
        except Exception as e:
            logger.error(f"Failed to check vocabulary status: {str(e)}")
            return 'FAILED'
    
    async def _check_transcription_jobs(self, session_id: str):
        """Check for completed transcription jobs and process results"""
        try:
            if session_id not in self.active_sessions:
                return
            
            session = self.active_sessions[session_id]
            pending_jobs = session.get('pending_jobs', [])
            completed_jobs = []
            
            for job_info in pending_jobs:
                job_name = job_info['job_name']
                
                try:
                    response = self.transcribe_client.get_transcription_job(
                        TranscriptionJobName=job_name
                    )
                    
                    job_status = response['TranscriptionJob']['TranscriptionJobStatus']
                    
                    if job_status == 'COMPLETED':
                        # Get transcript
                        transcript_uri = response['TranscriptionJob']['Transcript']['TranscriptFileUri']
                        
                        # Download and parse transcript
                        import requests
                        transcript_response = requests.get(transcript_uri, timeout=30)
                        transcript_data = transcript_response.json()
                        
                        # Extract transcript text
                        transcript_text = ""
                        confidence = 0.0
                        
                        if 'results' in transcript_data and 'transcripts' in transcript_data['results']:
                            transcripts = transcript_data['results']['transcripts']
                            if transcripts:
                                transcript_text = transcripts[0].get('transcript', '')
                        
                        # Calculate average confidence
                        if 'results' in transcript_data and 'items' in transcript_data['results']:
                            items = transcript_data['results']['items']
                            confidences = [float(item.get('alternatives', [{}])[0].get('confidence', 0)) 
                                         for item in items if item.get('alternatives')]
                            if confidences:
                                confidence = sum(confidences) / len(confidences)
                        
                        # Send transcript to callback
                        callback = session.get('transcript_callback')
                        if callback and transcript_text.strip():
                            await callback(session_id, {
                                'type': 'final_transcript',
                                'text': transcript_text,
                                'confidence': confidence,
                                'is_final': True,
                                'job_name': job_name
                            })
                        
                        completed_jobs.append(job_info)
                        logger.info(f"Transcription completed for session {session_id}: {transcript_text}")
                        
                    elif job_status == 'FAILED':
                        logger.error(f"Transcription job failed: {job_name}")
                        completed_jobs.append(job_info)
                        
                except Exception as job_error:
                    logger.error(f"Error checking transcription job {job_name}: {str(job_error)}")
                    # Don't remove from pending jobs yet, might be temporary error
            
            # Remove completed jobs from pending list
            for completed_job in completed_jobs:
                if completed_job in pending_jobs:
                    pending_jobs.remove(completed_job)
            
        except Exception as e:
            logger.error(f"Error checking transcription jobs for session {session_id}: {str(e)}")
    
    async def _handle_transcription_stream(self, session_id: str, stream, handler: TranscribeStreamHandler):
        """Handle the transcription stream events"""
        try:
            # Use the correct method to iterate over transcription events
            async for event in stream.output_stream:
                await handler.handle_transcript_event(event)
                
        except Exception as e:
            logger.error(f"Error in transcription stream for session {session_id}: {str(e)}")
            # Notify about stream error
            if session_id in self.active_sessions:
                session = self.active_sessions[session_id]
                session['is_listening'] = False
    
    async def _handle_transcription_stream_with_recovery(self, session_id: str, stream, handler: TranscribeStreamHandler):
        """Handle transcription stream with automatic recovery"""
        retry_count = 0
        max_retries = 2
        
        while retry_count <= max_retries:
            try:
                async for event in stream:
                    await handler.handle_transcript_event(event)
                break  # Stream completed successfully
                
            except Exception as e:
                retry_count += 1
                logger.error(f"Transcription stream error for session {session_id} (attempt {retry_count}): {str(e)}")
                
                if session_id in self.active_sessions:
                    session = self.active_sessions[session_id]
                    
                    if retry_count <= max_retries:
                        # Attempt recovery
                        logger.info(f"Attempting to recover transcription stream for session {session_id}")
                        
                        # Notify client about recovery attempt
                        await handler.callback(session_id, {
                            'type': 'stream_recovery',
                            'message': f'Recovering from connection issue (attempt {retry_count})',
                            'retry_count': retry_count
                        })
                        
                        # Wait before retry
                        await asyncio.sleep(2 ** retry_count)  # Exponential backoff
                        
                        # Try to restart the stream
                        try:
                            stream = await self.transcribe_streaming_client.start_stream_transcription(
                                language_code=session['transcription_settings']['language_code'],
                                media_sample_rate_hz=session['transcription_settings']['media_sample_rate_hz'],
                                media_encoding=session['transcription_settings']['media_encoding'],
                                enable_partial_results_stabilization=True,
                                partial_results_stability='medium'
                            )
                            session['transcription_stream'] = stream
                        except Exception as restart_error:
                            logger.error(f"Failed to restart stream: {str(restart_error)}")
                            break
                    else:
                        # Max retries reached
                        session['is_listening'] = False
                        await handler.callback(session_id, {
                            'type': 'stream_failure',
                            'message': 'Unable to maintain transcription connection. Please restart voice session.',
                            'fallback_available': True
                        })
                        break
    
    async def stop_transcription_stream(self, session_id: str) -> Dict[str, Any]:
        """Stop the transcription stream for a session"""
        try:
            if session_id not in self.active_sessions:
                return {
                    'status': 'error',
                    'message': 'Voice session not found'
                }
            
            session = self.active_sessions[session_id]
            
            if session.get('transcription_stream'):
                # Close the stream
                await session['transcription_stream'].input_stream.end_stream()
                session['transcription_stream'] = None
                session['stream_handler'] = None
                session['is_listening'] = False
                
                logger.info(f"Transcription stream stopped for session: {session_id}")
                return {
                    'status': 'success',
                    'message': 'Transcription stream stopped'
                }
            else:
                return {
                    'status': 'warning',
                    'message': 'No active transcription stream found'
                }
                
        except Exception as e:
            logger.error(f"Failed to stop transcription stream for session {session_id}: {str(e)}")
            return {
                'status': 'error',
                'message': f'Failed to stop transcription stream: {str(e)}'
            }
    
    async def process_audio_chunk(self, session_id: str, audio_data: bytes) -> Dict[str, Any]:
        """Process audio chunk for real-time transcription"""
        try:
            if session_id not in self.active_sessions:
                return {
                    'status': 'error',
                    'message': 'Voice session not found'
                }
            
            session = self.active_sessions[session_id]
            
            if not session.get('is_listening'):
                return {
                    'status': 'error',
                    'message': 'Not listening for audio'
                }
            
            # Store audio chunk for batch processing
            session['audio_chunks'].append(audio_data)
            
            logger.info(f"Processing audio chunk for session {session_id}: {len(audio_data)} bytes")
            
            # Send audio to real-time transcription stream if available
            if session.get('transcription_stream'):
                try:
                    # Send audio chunk to AWS Transcribe stream
                    await session['transcription_stream'].input_stream.send_audio_event(audio_chunk=audio_data)
                    logger.info(f"Sent audio chunk to transcription stream: {len(audio_data)} bytes")
                except Exception as stream_error:
                    logger.error(f"Failed to send audio to stream: {str(stream_error)}")
            
            # Assess audio quality
            audio_quality = self._assess_audio_quality(audio_data)
            session.setdefault('audio_quality_history', []).append(audio_quality)
            
            # Process accumulated chunks when we have enough data
            if len(session['audio_chunks']) >= 20:  # Process every 20 chunks (~2 seconds of audio)
                # Combine chunks for transcription
                combined_audio = b''.join(session['audio_chunks'])
                
                # Save to S3 and start transcription job
                try:
                    audio_key = f"voice-realtime/{session_id}/{uuid.uuid4()}.wav"
                    
                    self.s3_client.put_object(
                        Bucket=self.voice_audio_bucket,
                        Key=audio_key,
                        Body=combined_audio,
                        ContentType='audio/wav'
                    )
                    
                    # Start transcription job
                    job_name = f"realtime-{session_id}-{int(datetime.utcnow().timestamp())}"
                    job_uri = f"s3://{self.voice_audio_bucket}/{audio_key}"
                    
                    transcribe_params = {
                        'TranscriptionJobName': job_name,
                        'Media': {'MediaFileUri': job_uri},
                        'MediaFormat': 'wav',
                        'LanguageCode': 'en-US'
                    }
                    
                    # Add custom vocabulary if available
                    if self.transcribe_vocabulary:
                        transcribe_params['Settings'] = {
                            'VocabularyName': self.transcribe_vocabulary
                        }
                    
                    self.transcribe_client.start_transcription_job(**transcribe_params)
                    
                    # Store job info for later retrieval
                    session.setdefault('pending_jobs', []).append({
                        'job_name': job_name,
                        'started_at': datetime.utcnow(),
                        'audio_key': audio_key
                    })
                    
                    # Clear processed chunks
                    session['audio_chunks'] = []
                    
                    # Check for completed jobs asynchronously
                    asyncio.create_task(self._check_transcription_jobs(session_id))
                    
                except Exception as transcribe_error:
                    logger.error(f"Transcription error for session {session_id}: {str(transcribe_error)}")
                    # Continue without failing - audio generation still works
            
            return {
                'status': 'success',
                'message': 'Audio chunk processed',
                'audio_quality': audio_quality,
                'chunks_accumulated': len(session['audio_chunks'])
            }
            
        except Exception as e:
            logger.error(f"Failed to process audio chunk for session {session_id}: {str(e)}")
            return {
                'status': 'error',
                'message': f'Failed to process audio: {str(e)}'
            }
    
    def _assess_audio_quality(self, audio_data: bytes) -> Dict[str, Any]:
        """Assess the quality of incoming audio data"""
        try:
            # Basic audio quality assessment
            # In a production system, you might use more sophisticated audio analysis
            
            data_length = len(audio_data)
            
            # Check for silence (all zeros or very low amplitude)
            if data_length == 0:
                return {
                    'score': 'poor',
                    'issues': ['no_audio_data'],
                    'data_length': data_length
                }
            
            # Simple amplitude analysis
            # Convert bytes to integers for analysis
            if data_length >= 2:
                # Assume 16-bit PCM audio
                samples = []
                for i in range(0, min(data_length - 1, 1000), 2):  # Sample first 500 16-bit values
                    sample = int.from_bytes(audio_data[i:i+2], byteorder='little', signed=True)
                    samples.append(abs(sample))
                
                if samples:
                    avg_amplitude = sum(samples) / len(samples)
                    max_amplitude = max(samples)
                    
                    # Assess quality based on amplitude
                    if max_amplitude < 100:  # Very quiet
                        return {
                            'score': 'poor',
                            'issues': ['very_low_volume'],
                            'avg_amplitude': avg_amplitude,
                            'max_amplitude': max_amplitude
                        }
                    elif max_amplitude > 30000:  # Likely clipping
                        return {
                            'score': 'medium',
                            'issues': ['possible_clipping'],
                            'avg_amplitude': avg_amplitude,
                            'max_amplitude': max_amplitude
                        }
                    elif avg_amplitude < 500:  # Low volume
                        return {
                            'score': 'medium',
                            'issues': ['low_volume'],
                            'avg_amplitude': avg_amplitude,
                            'max_amplitude': max_amplitude
                        }
                    else:
                        return {
                            'score': 'good',
                            'issues': [],
                            'avg_amplitude': avg_amplitude,
                            'max_amplitude': max_amplitude
                        }
            
            # Default assessment for short chunks
            return {
                'score': 'medium',
                'issues': ['insufficient_data'],
                'data_length': data_length
            }
            
        except Exception as e:
            logger.error(f"Error assessing audio quality: {str(e)}")
            return {
                'score': 'unknown',
                'issues': ['assessment_error'],
                'error': str(e)
            }
    
    async def detect_speech_completion(self, session_id: str) -> Dict[str, Any]:
        """Check if speech appears to be complete based on timeout"""
        try:
            if session_id not in self.active_sessions:
                return {
                    'status': 'error',
                    'message': 'Voice session not found'
                }
            
            session = self.active_sessions[session_id]
            handler = session.get('stream_handler')
            
            if not handler:
                return {
                    'status': 'error',
                    'message': 'No stream handler found'
                }
            
            is_complete = handler.is_speech_complete()
            
            return {
                'status': 'success',
                'speech_complete': is_complete,
                'final_transcript': handler.final_transcript if is_complete else None
            }
            
        except Exception as e:
            logger.error(f"Failed to detect speech completion for session {session_id}: {str(e)}")
            return {
                'status': 'error',
                'message': f'Failed to detect speech completion: {str(e)}'
            }
    
    async def transcribe_audio(self, session_id: str) -> Dict[str, Any]:
        """Transcribe accumulated audio chunks"""
        try:
            if session_id not in self.active_sessions:
                return {
                    'status': 'error',
                    'message': 'Voice session not found'
                }
            
            session = self.active_sessions[session_id]
            
            if not session['audio_chunks']:
                return {
                    'status': 'error',
                    'message': 'No audio data to transcribe'
                }
            
            # Combine audio chunks
            combined_audio = b''.join(session['audio_chunks'])
            
            # Save audio to S3 for transcription
            audio_key = f"voice-sessions/{session_id}/{uuid.uuid4()}.wav"
            
            if self.voice_audio_bucket:
                self.s3_client.put_object(
                    Bucket=self.voice_audio_bucket,
                    Key=audio_key,
                    Body=combined_audio,
                    ContentType='audio/wav'
                )
                
                # Start transcription job
                job_name = f"transcribe-{session_id}-{int(datetime.utcnow().timestamp())}"
                job_uri = f"s3://{self.voice_audio_bucket}/{audio_key}"
                
                transcribe_params = {
                    'TranscriptionJobName': job_name,
                    'Media': {'MediaFileUri': job_uri},
                    'MediaFormat': 'wav',
                    'LanguageCode': 'en-US'
                }
                
                # Add custom vocabulary if available
                if self.transcribe_vocabulary:
                    transcribe_params['Settings'] = {
                        'VocabularyName': self.transcribe_vocabulary
                    }
                
                self.transcribe_client.start_transcription_job(**transcribe_params)
                
                # Wait for transcription to complete (simplified approach)
                # In production, you'd use webhooks or polling
                await asyncio.sleep(5)  # Give it time to process
                
                try:
                    response = self.transcribe_client.get_transcription_job(
                        TranscriptionJobName=job_name
                    )
                    
                    if response['TranscriptionJob']['TranscriptionJobStatus'] == 'COMPLETED':
                        # Get transcript
                        transcript_uri = response['TranscriptionJob']['Transcript']['TranscriptFileUri']
                        
                        # Fetch and parse the actual transcript
                        import requests
                        transcript_response = requests.get(transcript_uri, timeout=30)
                        transcript_data = transcript_response.json()
                        
                        # Extract the actual transcript text
                        transcript_text = ""
                        if 'results' in transcript_data and 'transcripts' in transcript_data['results']:
                            transcripts = transcript_data['results']['transcripts']
                            if transcripts and len(transcripts) > 0:
                                transcript_text = transcripts[0].get('transcript', '')
                        
                        if not transcript_text:
                            transcript_text = "No speech detected in audio"
                        
                        # Clear audio chunks after successful transcription
                        session['audio_chunks'] = []
                        
                        return {
                            'status': 'success',
                            'transcript': transcript_text,
                            'confidence': 0.95,
                            'job_name': job_name
                        }
                    else:
                        return {
                            'status': 'processing',
                            'message': 'Transcription in progress',
                            'job_name': job_name
                        }
                        
                except ClientError as e:
                    if e.response['Error']['Code'] == 'BadRequestException':
                        return {
                            'status': 'processing',
                            'message': 'Transcription still in progress'
                        }
                    raise e
            else:
                # Fallback: return placeholder transcript
                return {
                    'status': 'success',
                    'transcript': 'Voice transcription placeholder - configure VOICE_AUDIO_BUCKET for full functionality',
                    'confidence': 0.5
                }
                
        except Exception as e:
            logger.error(f"Failed to transcribe audio for session {session_id}: {str(e)}")
            return {
                'status': 'error',
                'message': f'Transcription failed: {str(e)}'
            }
    
    async def generate_speech(self, session_id: str, text: str, context: str = 'default') -> Dict[str, Any]:
        """Generate speech from text using AWS Polly - returns audio_id for HTTP streaming"""
        try:
            if session_id not in self.active_sessions:
                return {
                    'status': 'error',
                    'message': 'Voice session not found'
                }
            
            session = self.active_sessions[session_id]
            voice_settings = session['voice_settings']
            
            # Prepare advanced SSML for natural speech
            ssml_text = self._create_ssml_text(text, voice_settings, context)
            
            # Determine optimal output format for web streaming
            output_format = voice_settings.get('output_format', 'mp3')
            sample_rate = voice_settings.get('sample_rate', '22050')
            
            # Generate speech using Polly with neural engine
            polly_params = {
                'Text': ssml_text,
                'TextType': 'ssml',
                'OutputFormat': output_format,
                'VoiceId': voice_settings['voice_id'],
                'Engine': voice_settings.get('engine', 'neural'),
                'LanguageCode': voice_settings.get('language_code', 'en-US')
            }
            
            # Add sample rate for supported formats
            if output_format in ['pcm', 'ogg_vorbis']:
                polly_params['SampleRate'] = sample_rate
            
            response = self.polly_client.synthesize_speech(**polly_params)
            
            # Get audio stream
            audio_stream = response['AudioStream'].read()
            
            # Optimize audio for web streaming
            optimized_audio = self._optimize_audio_for_streaming(audio_stream, output_format)
            
            # Generate unique audio ID
            audio_id = str(uuid.uuid4())
            
            # Store in memory cache with TTL (1 hour)
            self.audio_cache[audio_id] = {
                'data': optimized_audio,
                'format': output_format,
                'created_at': datetime.utcnow(),
                'session_id': session_id,
                'text': text,
                'voice_settings': voice_settings
            }
            
            # Store in conversation history with enhanced metadata
            session['conversation_history'].append({
                'type': 'agent_response',
                'text': text,
                'audio_id': audio_id,
                'voice_settings': voice_settings,
                'context': context,
                'audio_format': output_format,
                'audio_size': len(optimized_audio),
                'timestamp': datetime.utcnow().isoformat()
            })
            
            # Return audio_id for HTTP streaming (frontend fetches via HTTP)
            # Frontend should NEVER access S3 directly - all audio goes through backend HTTP endpoint
            return {
                'status': 'success',
                'audio_id': audio_id,
                'text': text,
                'voice_settings': voice_settings,
                'audio_format': output_format,
                'audio_size': len(optimized_audio),
                'generation_time': response.get('ResponseMetadata', {}).get('HTTPHeaders', {}).get('x-amzn-requestid')
            }
            
        except Exception as e:
            logger.error(f"Failed to generate speech for session {session_id}: {str(e)}")
            return {
                'status': 'error',
                'message': f'Speech generation failed: {str(e)}',
                'fallback_available': True
            }

    async def generate_streaming_speech(self, session_id: str, text: str, websocket_callback, context: str = 'default') -> Dict[str, Any]:
        """Generate speech sentence-by-sentence and stream via WebSocket"""
        try:
            if session_id not in self.active_sessions:
                return {
                    'status': 'error',
                    'message': 'Voice session not found'
                }
            
            # Split text into sentences
            sentences = self._split_into_sentences(text)
            audio_ids = []
            
            for i, sentence in enumerate(sentences):
                if not sentence.strip():
                    continue
                
                # Generate audio for this sentence
                result = await self.generate_speech(session_id, sentence, context)
                
                if result['status'] == 'success':
                    audio_ids.append(result['audio_id'])
                    
                    # Send audio chunk via WebSocket immediately
                    await websocket_callback({
                        'type': 'audio_chunk',
                        'audio_id': result['audio_id'],
                        'sentence': sentence,
                        'chunk_index': i,
                        'total_chunks': len(sentences),
                        'is_final': i == len(sentences) - 1
                    })
                    
                    # Small delay for natural pacing
                    await asyncio.sleep(0.1)
                else:
                    logger.error(f"Failed to generate audio for sentence: {sentence}")
            
            return {
                'status': 'success',
                'audio_ids': audio_ids,
                'total_sentences': len(sentences),
                'streaming': True
            }
            
        except Exception as e:
            logger.error(f"Failed to generate streaming speech: {str(e)}")
            return {
                'status': 'error',
                'message': f'Streaming speech generation failed: {str(e)}'
            }
    
    def _create_ssml_text(self, text: str, voice_settings: Dict, context: str = 'default') -> str:
        """Create SSML text compatible with neural voices"""
        # Clean and prepare text
        cleaned_text = self._clean_text_for_speech(text)
        
        # Apply context-specific speech patterns
        speech_rate = voice_settings.get('speech_rate', 'medium')
        
        # Adjust speech parameters based on context
        if context == 'greeting':
            speech_rate = 'medium'
        elif context == 'explanation':
            speech_rate = 'slow'
        elif context == 'confirmation':
            speech_rate = 'medium'
        
        # Create simple SSML compatible with neural voices
        # Neural voices don't support pitch or volume in prosody
        ssml_parts = ['<speak>']
        
        # Only use rate for neural voices
        ssml_parts.append(f'<prosody rate="{speech_rate}">')
        
        # Process text for natural speech patterns
        sentences = self._split_into_sentences(cleaned_text)
        
        for i, sentence in enumerate(sentences):
            # Add natural pauses between sentences
            if i > 0:
                ssml_parts.append('<break time="0.5s"/>')
            
            # Just add the sentence without emphasis (neural voices don't support it well)
            ssml_parts.append(sentence)
        
        ssml_parts.append('</prosody>')
        ssml_parts.append('</speak>')
        
        return ''.join(ssml_parts)
    
    def _clean_text_for_speech(self, text: str) -> str:
        """Clean text for better speech synthesis"""
        # Remove or replace problematic characters
        cleaned = text.replace('&', ' and ')
        cleaned = cleaned.replace('<', ' less than ')
        cleaned = cleaned.replace('>', ' greater than ')
        cleaned = cleaned.replace('"', '')
        cleaned = cleaned.replace("'", "'")
        
        # Handle common abbreviations
        abbreviations = {
            'e.g.': 'for example',
            'i.e.': 'that is',
            'etc.': 'and so on',
            'vs.': 'versus',
            'Mr.': 'Mister',
            'Mrs.': 'Missus',
            'Dr.': 'Doctor'
        }
        
        for abbrev, expansion in abbreviations.items():
            cleaned = cleaned.replace(abbrev, expansion)
        
        return cleaned
    
    def _split_into_sentences(self, text: str) -> list:
        """Split text into sentences for natural speech pacing"""
        import re
        # Simple sentence splitting
        sentences = re.split(r'[.!?]+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def _add_emphasis(self, sentence: str) -> str:
        """Add SSML emphasis to important words"""
        # Words that should be emphasized in organization profile context
        emphasis_words = [
            'important', 'critical', 'essential', 'required', 'mandatory',
            'security', 'compliance', 'risk', 'governance', 'audit'
        ]
        
        for word in emphasis_words:
            pattern = r'\b' + re.escape(word) + r'\b'
            replacement = f'<emphasis level="moderate">{word}</emphasis>'
            sentence = re.sub(pattern, replacement, sentence, flags=re.IGNORECASE)
        
        return sentence
    
    def _optimize_audio_for_streaming(self, audio_data: bytes, format: str) -> bytes:
        """Optimize audio data for web streaming"""
        # For now, return as-is. In production, you might:
        # - Compress audio further
        # - Normalize volume levels
        # - Add streaming-friendly headers
        return audio_data
    
    def _get_content_type(self, format: str) -> str:
        """Get appropriate content type for audio format"""
        content_types = {
            'mp3': 'audio/mpeg',
            'ogg_vorbis': 'audio/ogg',
            'pcm': 'audio/pcm',
            'json': 'application/x-json-stream'
        }
        return content_types.get(format, 'audio/mpeg')
    
    async def get_available_voices(self, language_code: str = 'en-US') -> Dict[str, Any]:
        """Get available neural voices for a language"""
        try:
            # Get voices from Polly
            response = self.polly_client.describe_voices(
                Engine='neural',
                LanguageCode=language_code
            )
            
            voices = []
            for voice in response.get('Voices', []):
                voices.append({
                    'id': voice['Id'],
                    'name': voice['Name'],
                    'gender': voice['Gender'],
                    'language_code': voice['LanguageCode'],
                    'language_name': voice['LanguageName'],
                    'supported_engines': voice.get('SupportedEngines', [])
                })
            
            return {
                'status': 'success',
                'voices': voices,
                'language_code': language_code
            }
            
        except Exception as e:
            logger.error(f"Failed to get available voices: {str(e)}")
            return {
                'status': 'error',
                'message': f'Failed to get voices: {str(e)}',
                'fallback_voices': self.available_voices.get(language_code, {})
            }
    
    async def set_voice_profile(self, session_id: str, profile_name: str) -> Dict[str, Any]:
        """Set voice profile for a session"""
        try:
            if session_id not in self.active_sessions:
                return {
                    'status': 'error',
                    'message': 'Voice session not found'
                }
            
            if profile_name not in self.voice_profiles:
                return {
                    'status': 'error',
                    'message': f'Voice profile "{profile_name}" not found',
                    'available_profiles': list(self.voice_profiles.keys())
                }
            
            session = self.active_sessions[session_id]
            profile_settings = self.voice_profiles[profile_name].copy()
            
            # Merge with existing settings
            session['voice_settings'].update(profile_settings)
            
            logger.info(f"Voice profile '{profile_name}' applied to session {session_id}")
            
            return {
                'status': 'success',
                'profile_name': profile_name,
                'voice_settings': session['voice_settings']
            }
            
        except Exception as e:
            logger.error(f"Failed to set voice profile for session {session_id}: {str(e)}")
            return {
                'status': 'error',
                'message': f'Failed to set voice profile: {str(e)}'
            }
    
    async def create_audio_stream(self, session_id: str, text: str, chunk_size: int = 1024) -> Dict[str, Any]:
        """Create streaming audio response for real-time playback"""
        try:
            if session_id not in self.active_sessions:
                return {
                    'status': 'error',
                    'message': 'Voice session not found'
                }
            
            session = self.active_sessions[session_id]
            voice_settings = session['voice_settings']
            
            # Generate speech
            speech_result = await self.generate_speech(session_id, text)
            
            if speech_result['status'] != 'success':
                return speech_result
            
            # Create streaming chunks for smooth playback
            audio_data = base64.b64decode(speech_result['audio_data']) if speech_result.get('audio_data') else None
            
            if not audio_data and speech_result.get('audio_url'):
                # Download from S3 for streaming
                try:
                    import requests
                    response = requests.get(speech_result['audio_url'], timeout=30)
                    audio_data = response.content
                except Exception as e:
                    logger.error(f"Failed to download audio for streaming: {str(e)}")
                    return {
                        'status': 'error',
                        'message': 'Failed to prepare audio for streaming'
                    }
            
            if not audio_data:
                return {
                    'status': 'error',
                    'message': 'No audio data available for streaming'
                }
            
            # Create audio chunks for streaming
            chunks = []
            for i in range(0, len(audio_data), chunk_size):
                chunk = audio_data[i:i + chunk_size]
                chunks.append({
                    'chunk_id': i // chunk_size,
                    'data': base64.b64encode(chunk).decode('utf-8'),
                    'size': len(chunk),
                    'is_final': i + chunk_size >= len(audio_data)
                })
            
            # Store streaming session
            stream_id = str(uuid.uuid4())
            session['audio_streams'] = session.get('audio_streams', {})
            session['audio_streams'][stream_id] = {
                'chunks': chunks,
                'total_chunks': len(chunks),
                'created_at': datetime.utcnow(),
                'text': text,
                'voice_settings': voice_settings
            }
            
            return {
                'status': 'success',
                'stream_id': stream_id,
                'total_chunks': len(chunks),
                'chunk_size': chunk_size,
                'total_size': len(audio_data),
                'audio_format': voice_settings.get('output_format', 'mp3')
            }
            
        except Exception as e:
            logger.error(f"Failed to create audio stream for session {session_id}: {str(e)}")
            return {
                'status': 'error',
                'message': f'Failed to create audio stream: {str(e)}'
            }
    
    async def get_audio_chunk(self, session_id: str, stream_id: str, chunk_id: int) -> Dict[str, Any]:
        """Get specific audio chunk for streaming playback"""
        try:
            if session_id not in self.active_sessions:
                return {
                    'status': 'error',
                    'message': 'Voice session not found'
                }
            
            session = self.active_sessions[session_id]
            audio_streams = session.get('audio_streams', {})
            
            if stream_id not in audio_streams:
                return {
                    'status': 'error',
                    'message': 'Audio stream not found'
                }
            
            stream = audio_streams[stream_id]
            chunks = stream['chunks']
            
            if chunk_id >= len(chunks):
                return {
                    'status': 'error',
                    'message': 'Chunk ID out of range'
                }
            
            chunk = chunks[chunk_id]
            
            return {
                'status': 'success',
                'chunk_id': chunk['chunk_id'],
                'data': chunk['data'],
                'size': chunk['size'],
                'is_final': chunk['is_final'],
                'stream_id': stream_id
            }
            
        except Exception as e:
            logger.error(f"Failed to get audio chunk for session {session_id}: {str(e)}")
            return {
                'status': 'error',
                'message': f'Failed to get audio chunk: {str(e)}'
            }
    
    async def create_buffered_playback(self, session_id: str, text: str, buffer_size: int = 3) -> Dict[str, Any]:
        """Create buffered audio playback for smooth experience"""
        try:
            if session_id not in self.active_sessions:
                return {
                    'status': 'error',
                    'message': 'Voice session not found'
                }
            
            session = self.active_sessions[session_id]
            
            # Split text into smaller segments for buffering
            segments = self._split_text_for_buffering(text)
            
            # Generate audio for first few segments
            buffer_id = str(uuid.uuid4())
            session['audio_buffers'] = session.get('audio_buffers', {})
            
            buffer_data = {
                'buffer_id': buffer_id,
                'segments': segments,
                'generated_segments': [],
                'current_segment': 0,
                'buffer_size': buffer_size,
                'created_at': datetime.utcnow(),
                'status': 'generating'
            }
            
            session['audio_buffers'][buffer_id] = buffer_data
            
            # Generate initial buffer
            await self._generate_buffer_segments(session_id, buffer_id, buffer_size)
            
            return {
                'status': 'success',
                'buffer_id': buffer_id,
                'total_segments': len(segments),
                'buffer_size': buffer_size,
                'initial_segments_ready': min(buffer_size, len(segments))
            }
            
        except Exception as e:
            logger.error(f"Failed to create buffered playback for session {session_id}: {str(e)}")
            return {
                'status': 'error',
                'message': f'Failed to create buffered playback: {str(e)}'
            }
    
    def _split_text_for_buffering(self, text: str, max_segment_length: int = 200) -> list:
        """Split text into segments suitable for audio buffering"""
        sentences = self._split_into_sentences(text)
        segments = []
        current_segment = ""
        
        for sentence in sentences:
            if len(current_segment + sentence) <= max_segment_length:
                current_segment += sentence + ". "
            else:
                if current_segment:
                    segments.append(current_segment.strip())
                current_segment = sentence + ". "
        
        if current_segment:
            segments.append(current_segment.strip())
        
        return segments
    
    async def _generate_buffer_segments(self, session_id: str, buffer_id: str, count: int):
        """Generate audio for buffer segments"""
        try:
            session = self.active_sessions[session_id]
            buffer_data = session['audio_buffers'][buffer_id]
            
            segments = buffer_data['segments']
            current_segment = buffer_data['current_segment']
            
            for i in range(count):
                segment_index = current_segment + i
                if segment_index >= len(segments):
                    break
                
                segment_text = segments[segment_index]
                
                # Generate speech for segment
                speech_result = await self.generate_speech(session_id, segment_text)
                
                if speech_result['status'] == 'success':
                    buffer_data['generated_segments'].append({
                        'segment_index': segment_index,
                        'text': segment_text,
                        'audio_url': speech_result.get('audio_url'),
                        'audio_data': speech_result.get('audio_data'),
                        'generated_at': datetime.utcnow().isoformat()
                    })
            
            buffer_data['status'] = 'ready'
            
        except Exception as e:
            logger.error(f"Failed to generate buffer segments: {str(e)}")
            if session_id in self.active_sessions:
                session = self.active_sessions[session_id]
                if buffer_id in session.get('audio_buffers', {}):
                    session['audio_buffers'][buffer_id]['status'] = 'error'
    
    async def get_next_buffer_segment(self, session_id: str, buffer_id: str) -> Dict[str, Any]:
        """Get next audio segment from buffer"""
        try:
            if session_id not in self.active_sessions:
                return {
                    'status': 'error',
                    'message': 'Voice session not found'
                }
            
            session = self.active_sessions[session_id]
            audio_buffers = session.get('audio_buffers', {})
            
            if buffer_id not in audio_buffers:
                return {
                    'status': 'error',
                    'message': 'Audio buffer not found'
                }
            
            buffer_data = audio_buffers[buffer_id]
            generated_segments = buffer_data['generated_segments']
            current_segment = buffer_data['current_segment']
            
            if current_segment >= len(generated_segments):
                return {
                    'status': 'complete',
                    'message': 'All segments played'
                }
            
            segment = generated_segments[current_segment]
            buffer_data['current_segment'] += 1
            
            # Generate more segments if needed
            remaining_segments = len(buffer_data['segments']) - buffer_data['current_segment']
            if remaining_segments > 0 and len(generated_segments) - buffer_data['current_segment'] < 2:
                asyncio.create_task(self._generate_buffer_segments(session_id, buffer_id, 2))
            
            return {
                'status': 'success',
                'segment_index': segment['segment_index'],
                'text': segment['text'],
                'audio_url': segment.get('audio_url'),
                'audio_data': segment.get('audio_data'),
                'is_final': buffer_data['current_segment'] >= len(buffer_data['segments'])
            }
            
        except Exception as e:
            logger.error(f"Failed to get next buffer segment for session {session_id}: {str(e)}")
            return {
                'status': 'error',
                'message': f'Failed to get buffer segment: {str(e)}'
            }
    
    async def cleanup_audio_cache(self, max_age_minutes: int = 60):
        """Clean up old audio from cache"""
        try:
            current_time = datetime.utcnow()
            cache_to_remove = []
            
            for audio_id, audio_info in self.audio_cache.items():
                age = (current_time - audio_info['created_at']).total_seconds() / 60
                if age > max_age_minutes:
                    cache_to_remove.append(audio_id)
            
            for audio_id in cache_to_remove:
                del self.audio_cache[audio_id]
            
            if cache_to_remove:
                logger.info(f"Cleaned up {len(cache_to_remove)} audio files from cache")
            
        except Exception as e:
            logger.error(f"Failed to cleanup audio cache: {str(e)}")
    
    async def cleanup_audio_streams(self, session_id: str, max_age_minutes: int = 60):
        """Clean up old audio streams and buffers"""
        try:
            if session_id not in self.active_sessions:
                return
            
            session = self.active_sessions[session_id]
            current_time = datetime.utcnow()
            
            # Clean up audio streams
            audio_streams = session.get('audio_streams', {})
            streams_to_remove = []
            
            for stream_id, stream_data in audio_streams.items():
                age = (current_time - stream_data['created_at']).total_seconds() / 60
                if age > max_age_minutes:
                    streams_to_remove.append(stream_id)
            
            for stream_id in streams_to_remove:
                del audio_streams[stream_id]
            
            # Clean up audio buffers
            audio_buffers = session.get('audio_buffers', {})
            buffers_to_remove = []
            
            for buffer_id, buffer_data in audio_buffers.items():
                age = (current_time - buffer_data['created_at']).total_seconds() / 60
                if age > max_age_minutes:
                    buffers_to_remove.append(buffer_id)
            
            for buffer_id in buffers_to_remove:
                del audio_buffers[buffer_id]
            
            logger.info(f"Cleaned up {len(streams_to_remove)} streams and {len(buffers_to_remove)} buffers for session {session_id}")
            
        except Exception as e:
            logger.error(f"Failed to cleanup audio streams for session {session_id}: {str(e)}")
    
    async def end_voice_session(self, session_id: str) -> Dict[str, Any]:
        """End a voice session and cleanup resources"""
        try:
            if session_id not in self.active_sessions:
                return {
                    'status': 'error',
                    'message': 'Voice session not found'
                }
            
            session = self.active_sessions[session_id]
            
            # Stop transcription stream if active
            if session.get('transcription_stream'):
                await self.stop_transcription_stream(session_id)
            
            session['status'] = 'ended'
            session['ended_at'] = datetime.utcnow()
            
            # Cleanup temporary audio files (optional - S3 lifecycle will handle this)
            # You could implement cleanup logic here if needed
            
            # Remove from active sessions
            del self.active_sessions[session_id]
            
            logger.info(f"Voice session ended: {session_id}")
            return {
                'status': 'success',
                'message': 'Voice session ended successfully',
                'conversation_history': session.get('conversation_history', [])
            }
            
        except Exception as e:
            logger.error(f"Failed to end voice session {session_id}: {str(e)}")
            return {
                'status': 'error',
                'message': f'Failed to end session: {str(e)}'
            }
    
    async def handle_transcript_result(self, session_id: str, result: Dict[str, Any]) -> None:
        """Handle transcript results from the stream handler"""
        try:
            if session_id not in self.active_sessions:
                logger.warning(f"Received transcript for unknown session: {session_id}")
                return
            
            session = self.active_sessions[session_id]
            
            # Add to conversation history if it's a final transcript
            if result.get('is_final', False):
                session['conversation_history'].append({
                    'type': 'user_voice',
                    'text': result['text'],
                    'confidence': result.get('confidence', 0.0),
                    'timestamp': datetime.utcnow().isoformat()
                })
                
                logger.info(f"Final transcript for session {session_id}: {result['text']}")
            
        except Exception as e:
            logger.error(f"Error handling transcript result for session {session_id}: {str(e)}")
    
    def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a voice session"""
        session = self.active_sessions.get(session_id)
        if session:
            return {
                'session_id': session['session_id'],
                'user_id': session['user_id'],
                'status': session['status'],
                'is_listening': session.get('is_listening', False),
                'created_at': session['created_at'].isoformat(),
                'voice_settings': session['voice_settings'],
                'transcription_settings': session['transcription_settings'],
                'conversation_history': session['conversation_history']
            }
        return None
    
    def list_active_sessions(self) -> Dict[str, Dict[str, Any]]:
        """List all active voice sessions"""
        return {
            session_id: {
                'user_id': session['user_id'],
                'status': session['status'],
                'is_listening': session.get('is_listening', False),
                'created_at': session['created_at'].isoformat(),
                'voice_settings': session['voice_settings']
            }
            for session_id, session in self.active_sessions.items()
        }
    
    async def get_transcription_quality_metrics(self, session_id: str) -> Dict[str, Any]:
        """Get comprehensive transcription quality metrics for a session"""
        try:
            if session_id not in self.active_sessions:
                return {
                    'status': 'error',
                    'message': 'Voice session not found'
                }
            
            session = self.active_sessions[session_id]
            history = session.get('conversation_history', [])
            audio_quality_history = session.get('audio_quality_history', [])
            
            # Calculate transcription metrics
            voice_messages = [msg for msg in history if msg['type'] == 'user_voice']
            
            transcription_metrics = {
                'total_messages': len(voice_messages),
                'average_confidence': 0.0,
                'low_confidence_count': 0,
                'very_low_confidence_count': 0,
                'quality_score': 'unknown'
            }
            
            if voice_messages:
                confidences = [msg.get('confidence', 0.0) for msg in voice_messages]
                average_confidence = sum(confidences) / len(confidences)
                low_confidence_count = sum(1 for conf in confidences if conf < 0.7)
                very_low_confidence_count = sum(1 for conf in confidences if conf < 0.5)
                
                transcription_metrics.update({
                    'average_confidence': round(average_confidence, 3),
                    'low_confidence_count': low_confidence_count,
                    'very_low_confidence_count': very_low_confidence_count,
                    'quality_score': 'high' if average_confidence > 0.8 else 'medium' if average_confidence > 0.6 else 'low',
                    'confidence_distribution': {
                        'high': sum(1 for conf in confidences if conf > 0.8),
                        'medium': sum(1 for conf in confidences if 0.6 <= conf <= 0.8),
                        'low': sum(1 for conf in confidences if conf < 0.6)
                    }
                })
            
            # Calculate audio quality metrics
            audio_metrics = {
                'total_chunks': len(audio_quality_history),
                'poor_quality_count': 0,
                'good_quality_count': 0,
                'common_issues': []
            }
            
            if audio_quality_history:
                poor_count = sum(1 for quality in audio_quality_history if quality.get('score') == 'poor')
                good_count = sum(1 for quality in audio_quality_history if quality.get('score') == 'good')
                
                # Collect common issues
                all_issues = []
                for quality in audio_quality_history:
                    all_issues.extend(quality.get('issues', []))
                
                # Count issue frequency
                issue_counts = {}
                for issue in all_issues:
                    issue_counts[issue] = issue_counts.get(issue, 0) + 1
                
                # Get most common issues
                common_issues = sorted(issue_counts.items(), key=lambda x: x[1], reverse=True)[:3]
                
                audio_metrics.update({
                    'poor_quality_count': poor_count,
                    'good_quality_count': good_count,
                    'quality_percentage': {
                        'poor': round((poor_count / len(audio_quality_history)) * 100, 1),
                        'good': round((good_count / len(audio_quality_history)) * 100, 1)
                    },
                    'common_issues': [{'issue': issue, 'count': count} for issue, count in common_issues]
                })
            
            # Overall assessment and recommendations
            recommendations = []
            overall_score = 'good'
            
            if transcription_metrics['quality_score'] == 'low':
                overall_score = 'poor'
                recommendations.append('Consider using text input for better accuracy')
            
            if audio_metrics['poor_quality_count'] > audio_metrics['total_chunks'] * 0.3:
                overall_score = 'poor'
                recommendations.append('Check microphone settings and reduce background noise')
            
            if transcription_metrics.get('very_low_confidence_count', 0) > 2:
                recommendations.append('Speak more clearly and at a moderate pace')
            
            # Get stream handler metrics if available
            stream_metrics = {}
            if session.get('stream_handler'):
                handler = session['stream_handler']
                stream_metrics = {
                    'consecutive_errors': handler.consecutive_errors,
                    'retry_count': handler.retry_count,
                    'total_transcripts': handler.total_transcripts,
                    'low_confidence_rate': handler.low_confidence_count / max(handler.total_transcripts, 1)
                }
            
            return {
                'status': 'success',
                'metrics': {
                    'transcription': transcription_metrics,
                    'audio_quality': audio_metrics,
                    'stream': stream_metrics,
                    'overall_score': overall_score,
                    'recommendations': recommendations,
                    'session_duration': (datetime.utcnow() - session['created_at']).total_seconds()
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get transcription metrics for session {session_id}: {str(e)}")
            return {
                'status': 'error',
                'message': f'Failed to get metrics: {str(e)}'
            }
    
    async def trigger_fallback_mode(self, session_id: str, reason: str = 'quality_issues') -> Dict[str, Any]:
        """Trigger fallback to text input mode"""
        try:
            if session_id not in self.active_sessions:
                return {
                    'status': 'error',
                    'message': 'Voice session not found'
                }
            
            session = self.active_sessions[session_id]
            
            # Stop transcription stream
            if session.get('transcription_stream'):
                await self.stop_transcription_stream(session_id)
            
            # Mark session as in fallback mode
            session['fallback_mode'] = True
            session['fallback_reason'] = reason
            session['fallback_triggered_at'] = datetime.utcnow()
            
            logger.info(f"Fallback mode triggered for session {session_id}: {reason}")
            
            return {
                'status': 'success',
                'message': 'Fallback mode activated',
                'reason': reason,
                'text_input_available': True
            }
            
        except Exception as e:
            logger.error(f"Failed to trigger fallback mode for session {session_id}: {str(e)}")
            return {
                'status': 'error',
                'message': f'Failed to trigger fallback: {str(e)}'
            }
    
    async def get_session_performance_metrics(self, session_id: str) -> Dict[str, Any]:
        """Get performance metrics for monitoring"""
        try:
            if session_id not in self.active_sessions:
                return {
                    'status': 'error',
                    'message': 'Voice session not found'
                }
            
            session = self.active_sessions[session_id]
            current_time = datetime.utcnow()
            session_duration = (current_time - session['created_at']).total_seconds()
            
            # Calculate response times
            conversation_history = session.get('conversation_history', [])
            response_times = []
            
            for i in range(1, len(conversation_history)):
                prev_msg = conversation_history[i-1]
                curr_msg = conversation_history[i]
                
                if (prev_msg.get('type') == 'user_voice' and 
                    curr_msg.get('type') == 'agent_response'):
                    prev_time = datetime.fromisoformat(prev_msg['timestamp'])
                    curr_time = datetime.fromisoformat(curr_msg['timestamp'])
                    response_time = (curr_time - prev_time).total_seconds()
                    response_times.append(response_time)
            
            avg_response_time = sum(response_times) / len(response_times) if response_times else 0
            
            # Get transcription metrics
            transcription_metrics = await self.get_transcription_quality_metrics(session_id)
            
            # Calculate cost estimates (simplified)
            audio_minutes = session_duration / 60
            transcribe_cost = audio_minutes * 0.024  # AWS Transcribe pricing
            polly_characters = sum(len(msg.get('text', '')) for msg in conversation_history if msg.get('type') == 'agent_response')
            polly_cost = (polly_characters / 1000000) * 4.00  # AWS Polly pricing
            
            return {
                'status': 'success',
                'metrics': {
                    'session_duration_seconds': session_duration,
                    'total_messages': len(conversation_history),
                    'voice_messages': len([m for m in conversation_history if m.get('type') == 'user_voice']),
                    'agent_responses': len([m for m in conversation_history if m.get('type') == 'agent_response']),
                    'average_response_time_seconds': round(avg_response_time, 2),
                    'transcription_quality': transcription_metrics.get('metrics', {}),
                    'estimated_costs': {
                        'transcribe_usd': round(transcribe_cost, 4),
                        'polly_usd': round(polly_cost, 4),
                        'total_usd': round(transcribe_cost + polly_cost, 4)
                    },
                    'session_health': {
                        'is_active': session.get('status') == 'active',
                        'is_listening': session.get('is_listening', False),
                        'error_count': session.get('error_count', 0),
                        'last_activity': conversation_history[-1].get('timestamp') if conversation_history else None
                    }
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get performance metrics for session {session_id}: {str(e)}")
            return {
                'status': 'error',
                'message': f'Failed to get performance metrics: {str(e)}'
            }
    
    async def log_session_event(self, session_id: str, event_type: str, event_data: Dict[str, Any] = None):
        """Log session events for monitoring and analytics"""
        try:
            if session_id not in self.active_sessions:
                return
            
            session = self.active_sessions[session_id]
            
            # Initialize session logs if not exists
            if 'session_logs' not in session:
                session['session_logs'] = []
            
            log_entry = {
                'timestamp': datetime.utcnow().isoformat(),
                'event_type': event_type,
                'event_data': event_data or {},
                'session_id': session_id
            }
            
            session['session_logs'].append(log_entry)
            
            # Keep only recent logs to prevent memory issues
            max_logs = 100
            if len(session['session_logs']) > max_logs:
                session['session_logs'] = session['session_logs'][-max_logs:]
            
            # Log to CloudWatch (in production, you'd use actual CloudWatch logging)
            logger.info(f"Voice session event - {event_type}: {json.dumps(log_entry)}")
            
        except Exception as e:
            logger.error(f"Failed to log session event: {str(e)}")
    
    def get_all_sessions_summary(self) -> Dict[str, Any]:
        """Get summary of all active sessions for monitoring dashboard"""
        try:
            total_sessions = len(self.active_sessions)
            active_sessions = len([s for s in self.active_sessions.values() if s.get('status') == 'active'])
            listening_sessions = len([s for s in self.active_sessions.values() if s.get('is_listening', False)])
            
            # Calculate total usage
            total_duration = 0
            total_messages = 0
            total_errors = 0
            
            for session in self.active_sessions.values():
                if session.get('created_at'):
                    duration = (datetime.utcnow() - session['created_at']).total_seconds()
                    total_duration += duration
                
                total_messages += len(session.get('conversation_history', []))
                total_errors += session.get('error_count', 0)
            
            return {
                'summary': {
                    'total_sessions': total_sessions,
                    'active_sessions': active_sessions,
                    'listening_sessions': listening_sessions,
                    'total_duration_hours': round(total_duration / 3600, 2),
                    'total_messages': total_messages,
                    'total_errors': total_errors,
                    'average_session_duration_minutes': round((total_duration / max(total_sessions, 1)) / 60, 2)
                },
                'sessions': {
                    session_id: {
                        'user_id': session['user_id'],
                        'status': session['status'],
                        'is_listening': session.get('is_listening', False),
                        'duration_minutes': round((datetime.utcnow() - session['created_at']).total_seconds() / 60, 2),
                        'message_count': len(session.get('conversation_history', [])),
                        'error_count': session.get('error_count', 0)
                    }
                    for session_id, session in self.active_sessions.items()
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get sessions summary: {str(e)}")
            return {
                'summary': {
                    'total_sessions': 0,
                    'active_sessions': 0,
                    'error': str(e)
                },
                'sessions': {}
            }
