#!/usr/bin/env python3
"""
Organization Profile Agent A2A Server with Voice Capabilities
"""
import sys
sys.path.append('/app')

from agents.shared.base_server import BaseA2AServer
from agents.organization_profile.agent import OrganizationProfileAgent
from agents.organization_profile.voice_handler import VoiceHandler
from fastapi import WebSocket, WebSocketDisconnect, HTTPException, Header
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any, Optional
import json
import logging
import base64
import io
import uuid
import os

# Configure logging
logging.basicConfig(level=logging.INFO)

class OrganizationProfileServer(BaseA2AServer):
    def __init__(self):
        super().__init__(
            agent_name="organization_profile",
            agent_class=OrganizationProfileAgent,
            port=9007
        )
        # Initialize voice handler
        self.voice_handler = VoiceHandler()
    
    def _process_agent_response(self, result: str) -> dict:
        """Process organization profile agent-specific response logic"""
        response_data = {"response": result}
        
        # Check agent instance for profile_id (stateless - always include if available)
        agent_profile_id = getattr(self.agent_instance, 'profile_id', None) if hasattr(self, 'agent_instance') else None
        
        # Always include profile_id if it exists (client decides if it needs it)
        if agent_profile_id:
            response_data["profile_id"] = agent_profile_id
        
        # Check for profile creation completion
        if "PROFILE_CREATED" in result:
            print(f"[ORGANIZATION_PROFILE] ✅ Profile creation completed")
            response_data["profile_created"] = True
            if agent_profile_id:
                print(f"[ORGANIZATION_PROFILE] 📤 Sending profile_id to frontend: {agent_profile_id}")
            # Clean the keyword from response
            response_data["response"] = result.replace("PROFILE_CREATED", "").replace("  ", " ").strip()
        
        # Check for profile update completion
        if "PROFILE_UPDATED" in result:
            print(f"[ORGANIZATION_PROFILE] 🔄 Profile update completed")
            response_data["profile_updated"] = True
            # Clean the keyword from response
            response_data["response"] = result.replace("PROFILE_UPDATED", "").replace("  ", " ").strip()
        
        return response_data
    
    def _enhance_transcript_for_voice(self, transcript: str) -> str:
        """Enhance transcript with voice context for better agent understanding"""
        # Add voice context prefix to help the agent understand this is voice input
        enhanced = f"[Voice Input] {transcript}"
        
        # Add common voice input corrections
        corrections = {
            " period ": ". ",
            " comma ": ", ",
            " question mark ": "? ",
            " exclamation point ": "! ",
            " new line ": "\n",
            " new paragraph ": "\n\n"
        }
        
        for spoken, written in corrections.items():
            enhanced = enhanced.replace(spoken, written)
        
        return enhanced
    
    def _optimize_response_for_voice(self, response: str) -> str:
        """Optimize agent response for voice output"""
        # Remove markdown formatting that doesn't work well in speech
        optimized = response.replace("**", "").replace("*", "")
        optimized = optimized.replace("###", "").replace("##", "").replace("#", "")
        
        # Replace abbreviations with full words for better speech
        abbreviations = {
            "e.g.": "for example",
            "i.e.": "that is",
            "etc.": "and so on",
            "vs.": "versus",
            "&": "and",
            "@": "at",
            "%": "percent",
            "$": "dollars"
        }
        
        for abbrev, full in abbreviations.items():
            optimized = optimized.replace(abbrev, full)
        
        # Add natural speech patterns
        if optimized.startswith("I "):
            optimized = optimized
        elif not optimized.startswith(("Let", "Great", "Perfect", "Thank", "I'll", "That's")):
            optimized = f"I understand. {optimized}"
        
        # Add confirmation phrases for voice interaction
        if "?" in optimized:
            if not optimized.endswith(("?", ".", "!")):
                optimized += ". Please let me know your thoughts."
        
        return optimized
    
    def _determine_voice_context(self, response: str) -> str:
        """Determine appropriate voice context based on response content"""
        response_lower = response.lower()
        
        if any(word in response_lower for word in ["hello", "hi", "welcome", "good"]):
            return "greeting"
        elif any(word in response_lower for word in ["explain", "understand", "because", "reason"]):
            return "explanation"
        elif any(word in response_lower for word in ["confirm", "correct", "yes", "that's right"]):
            return "confirmation"
        elif any(word in response_lower for word in ["question", "ask", "tell me", "what", "how"]):
            return "question"
        elif any(word in response_lower for word in ["complete", "finished", "done", "created"]):
            return "completion"
        else:
            return "default"
    
    def _process_message_for_context(self, message: str, input_mode: str, session_id: str) -> str:
        """Process message to maintain context across input methods"""
        # Get conversation history for context
        session_info = self.voice_handler.get_session_info(session_id)
        
        if input_mode == 'voice_fallback':
            # Add context that this is a fallback from voice
            processed = f"[Switched from voice to text] {message}"
        elif input_mode == 'text' and session_info and session_info.get('conversation_history'):
            # Maintain continuity with previous voice interactions
            recent_voice_messages = [
                msg for msg in session_info['conversation_history'][-3:] 
                if msg.get('type') == 'user_voice'
            ]
            if recent_voice_messages:
                processed = f"[Continuing conversation from voice mode] {message}"
            else:
                processed = message
        else:
            processed = message
        
        return processed
    
    def _is_voice_session(self, session_id: str) -> bool:
        """Check if session is currently in voice mode"""
        session_info = self.voice_handler.get_session_info(session_id)
        return session_info is not None and session_info.get('status') == 'active'
    
    async def _synchronize_conversation_state(self, session_id: str, new_mode: str) -> Dict[str, Any]:
        """Synchronize conversation state when switching input modes"""
        try:
            session_info = self.voice_handler.get_session_info(session_id)
            
            if not session_info:
                return {
                    'status': 'error',
                    'message': 'No session found to synchronize'
                }
            
            # Get conversation history
            conversation_history = session_info.get('conversation_history', [])
            
            if new_mode == 'voice':
                # Switching to voice mode
                if not conversation_history:
                    # First time switching to voice
                    message = "Voice mode activated. You can now speak your responses."
                else:
                    # Resuming voice mode
                    message = "Voice mode resumed. Continuing our conversation."
                
                # Ensure voice session is active
                if session_info.get('status') != 'active':
                    voice_result = await self.voice_handler.start_voice_session(session_id, session_info['user_id'])
                    if voice_result['status'] != 'success':
                        return {
                            'status': 'error',
                            'message': 'Failed to activate voice mode'
                        }
            
            elif new_mode == 'text':
                # Switching to text mode
                message = "Text mode activated. You can type your responses."
                
                # Voice session can remain active for potential audio responses
                # but input will be handled via text
            
            return {
                'status': 'success',
                'message': message,
                'conversation_length': len(conversation_history)
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Failed to synchronize conversation state: {str(e)}'
            }
    
    async def _get_conversation_state(self, session_id: str) -> Dict[str, Any]:
        """Get current conversation state for client synchronization"""
        try:
            session_info = self.voice_handler.get_session_info(session_id)
            
            if not session_info:
                return {
                    'exists': False,
                    'message': 'No active session'
                }
            
            # Get quality metrics
            quality_metrics = await self.voice_handler.get_transcription_quality_metrics(session_id)
            
            return {
                'exists': True,
                'session_id': session_id,
                'status': session_info.get('status'),
                'is_listening': session_info.get('is_listening', False),
                'voice_settings': session_info.get('voice_settings', {}),
                'conversation_length': len(session_info.get('conversation_history', [])),
                'quality_metrics': quality_metrics.get('metrics', {}),
                'created_at': session_info.get('created_at'),
                'last_activity': session_info.get('conversation_history', [{}])[-1].get('timestamp') if session_info.get('conversation_history') else None
            }
            
        except Exception as e:
            return {
                'exists': False,
                'error': str(e)
            }
    
    def _add_enhanced_chat_websocket(self, app):
        """Add voice-enhanced WebSocket endpoint for organization profile agent"""
        @app.websocket("/ws/chat")
        async def websocket_enhanced_chat_alb(websocket: WebSocket):
            import uuid
            from agents.shared.jwt_validator import validate_cognito_token
            
            token = websocket.query_params.get('token')
            if not token:
                await websocket.close(code=1008, reason="JWT token required")
                return
            
            payload = validate_cognito_token(token)
            if not payload:
                await websocket.close(code=1008, reason="Invalid JWT token")
                return
            
            user_id = payload.get('sub', 'unknown')
            await websocket.accept()
            
            # Generate session ID
            session_id = str(uuid.uuid4())
            
            # Initialize voice session for this WebSocket connection
            voice_session_result = await self.voice_handler.start_voice_session(session_id, user_id)
            if voice_session_result['status'] == 'success':
                print(f"[ORGANIZATION_PROFILE] Voice session ready for session: {session_id}")
            
            try:
                while True:
                    data = await websocket.receive_json()
                    message_type = data.get('type', 'message')
                    
                    if message_type == 'switch_input_mode':
                        # Handle voice mode switching
                        new_mode = data.get('mode', 'text')
                        voice_settings_from_frontend = data.get('voice_settings', {})
                        
                        print(f"[ORGANIZATION_PROFILE] Switching input mode to: {new_mode}")
                        print(f"[ORGANIZATION_PROFILE] Voice settings from frontend: {voice_settings_from_frontend}")
                        
                        if new_mode == 'voice':
                            # Map frontend settings to backend format
                            backend_voice_settings = {
                                'engine': 'neural',
                                'voice_id': voice_settings_from_frontend.get('voiceId', 'Joanna'),
                                'speech_rate': voice_settings_from_frontend.get('speechRate', 'medium'),
                                'volume': voice_settings_from_frontend.get('volume', 'medium'),
                                'language_code': voice_settings_from_frontend.get('language', 'en-US'),
                                'output_format': 'mp3',
                                'sample_rate': '22050'
                            }
                            
                            # Initialize voice session if not exists
                            print(f"[ORGANIZATION_PROFILE] Switching to voice mode for session: {session_id}")
                            if session_id not in self.voice_handler.active_sessions:
                                print(f"[ORGANIZATION_PROFILE] Creating new voice session with settings: {backend_voice_settings}")
                                await self.voice_handler.start_voice_session(
                                    session_id=session_id,
                                    user_id='websocket-user',
                                    voice_settings=backend_voice_settings
                                )
                            else:
                                # Update existing session settings
                                print(f"[ORGANIZATION_PROFILE] Updating voice settings for existing session")
                                self.voice_handler.active_sessions[session_id]['voice_settings'].update(backend_voice_settings)
                            
                            # Enable voice mode
                            self.voice_handler.active_sessions[session_id]['voice_mode'] = True
                            print(f"[ORGANIZATION_PROFILE] Voice mode enabled for session: {session_id}")
                            
                            # Start transcription session automatically
                            async def transcription_callback(transcript_data):
                                transcript_data["tab_id"] = tab_id
                                await websocket.send_json(transcript_data)
                            
                            print(f"[ORGANIZATION_PROFILE] Starting streaming transcription for session: {session_id}")
                            transcription_result = await self.voice_handler.start_streaming_transcription(
                                session_id=session_id,
                                websocket_callback=transcription_callback
                            )
                            
                            print(f"[ORGANIZATION_PROFILE] Transcription started: {transcription_result.get('status')}")
                        else:
                            # Disable voice mode
                            if session_id in self.voice_handler.active_sessions:
                                self.voice_handler.active_sessions[session_id]['voice_mode'] = False
                                
                                # Stop transcription
                                await self.voice_handler.stop_streaming_transcription(session_id)
                        
                        await websocket.send_json({
                            "type": "input_mode_switched",
                            "new_mode": new_mode,
                            "session_id": session_id
                        })
                        continue
                    
                    # ===== PHASE 1: ESSENTIAL VOICE INPUT HANDLERS =====
                    
                    elif message_type == 'audio_chunk':
                        # Process incoming audio chunk for real-time transcription
                        print(f"[ORGANIZATION_PROFILE] Received audio chunk for session: {session_id}")
                        try:
                            audio_data = base64.b64decode(data.get('audio_data', ''))
                            print(f"[ORGANIZATION_PROFILE] Audio data decoded: {len(audio_data)} bytes")
                            
                            # Check if session is listening
                            if session_id in self.voice_handler.active_sessions:
                                session_info = self.voice_handler.active_sessions[session_id]
                                print(f"[ORGANIZATION_PROFILE] Session found. is_listening: {session_info.get('is_listening', False)}")
                                print(f"[ORGANIZATION_PROFILE] Session voice_mode: {session_info.get('voice_mode', False)}")
                            else:
                                print(f"[ORGANIZATION_PROFILE] No voice session found for: {session_id}")
                            
                            result = await self.voice_handler.process_audio_chunk(session_id, audio_data)
                            
                            if result['status'] == 'error':
                                await websocket.send_json({
                                    "type": "audio_chunk_error",
                                    "status": result['status'],
                                    "message": result.get('message', ''),
                                    "fallback_available": result.get('fallback_available', False)
                                })
                            elif result['status'] == 'warning':
                                await websocket.send_json({
                                    "type": "audio_quality_warning",
                                    "status": result['status'],
                                    "message": result.get('message', ''),
                                    "audio_quality": result.get('audio_quality', {}),
                                    "suggestion": result.get('suggestion', '')
                                })
                        except Exception as e:
                            await websocket.send_json({
                                "type": "error",
                                "feature": "audio_chunk",
                                "message": str(e)
                            })
                            print(f"[ORGANIZATION_PROFILE] Error in audio_chunk: {e}")
                        continue
                    
                    elif message_type == 'start_transcription':
                        # Start real-time transcription stream
                        try:
                            # Define callback for real-time transcript results
                            async def transcript_callback(session_id: str, result: Dict):
                                await websocket.send_json({
                                    "type": "transcript_result",
                                    "session_id": session_id,
                                    "text": result.get('text', ''),
                                    "confidence": result.get('confidence', 0.0),
                                    "is_final": result.get('is_final', False),
                                    "is_partial": not result.get('is_final', False)
                                })
                                await self.voice_handler.handle_transcript_result(session_id, result)
                            
                            result = await self.voice_handler.start_transcription_stream(
                                session_id, 
                                transcript_callback
                            )
                            
                            await websocket.send_json({
                                "type": "transcription_started",
                                "status": result['status'],
                                "message": result.get('message', '')
                            })
                        except Exception as e:
                            await websocket.send_json({
                                "type": "error",
                                "feature": "start_transcription",
                                "message": str(e)
                            })
                            print(f"[ORGANIZATION_PROFILE] Error in start_transcription: {e}")
                        continue
                    
                    elif message_type == 'stop_transcription':
                        # Stop transcription stream
                        try:
                            result = await self.voice_handler.stop_transcription_stream(session_id)
                            await websocket.send_json({
                                "type": "transcription_stopped",
                                "status": result['status'],
                                "message": result.get('message', '')
                            })
                        except Exception as e:
                            await websocket.send_json({
                                "type": "error",
                                "feature": "stop_transcription",
                                "message": str(e)
                            })
                            print(f"[ORGANIZATION_PROFILE] Error in stop_transcription: {e}")
                        continue
                    
                    elif message_type == 'check_speech_completion':
                        # Check if speech appears to be complete
                        try:
                            result = await self.voice_handler.detect_speech_completion(session_id)
                            await websocket.send_json({
                                "type": "speech_completion_check",
                                "status": result['status'],
                                "speech_complete": result.get('speech_complete', False),
                                "final_transcript": result.get('final_transcript')
                            })
                        except Exception as e:
                            await websocket.send_json({
                                "type": "error",
                                "feature": "check_speech_completion",
                                "message": str(e)
                            })
                            print(f"[ORGANIZATION_PROFILE] Error in check_speech_completion: {e}")
                        continue
                    
                    # ===== END PHASE 1 HANDLERS =====
                    
                    elif message_type == 'apply_suggestion':
                        # Handle suggestion application from frontend
                        print(f"[ORGANIZATION_PROFILE] Received apply_suggestion request")
                        try:
                            field = data.get('field')
                            value = data.get('value')
                            
                            print(f"[ORGANIZATION_PROFILE] Applying suggestion - field: {field}, value: {value[:100] if value else 'None'}...")
                            
                            # Send the suggestion as a message to the agent
                            suggestion_message = f"I'd like to use this suggestion for {field}: {value}"
                            
                            # Process with streaming
                            result = ""
                            async for chunk in self.wrapped_agent.stream_async(suggestion_message, session_id, user_id):
                                if isinstance(chunk, dict) and "data" in chunk:
                                    await websocket.send_json({"type": "stream", "data": chunk["data"], "tab_id": data.get('tab_id')})
                                    result += chunk["data"]
                                elif isinstance(chunk, str):
                                    await websocket.send_json({"type": "stream", "data": chunk, "tab_id": data.get('tab_id')})
                                    result += chunk
                            
                            # Send completion
                            await websocket.send_json({
                                "type": "complete",
                                "response": result,
                                "session_id": session_id,
                                "tab_id": data.get('tab_id'),
                                "suggestion_applied": True,
                                "field": field
                            })
                            
                        except Exception as e:
                            print(f"[ORGANIZATION_PROFILE] Error applying suggestion: {e}")
                            import traceback
                            traceback.print_exc()
                            await websocket.send_json({
                                "type": "error",
                                "feature": "apply_suggestion",
                                "message": f"Failed to apply suggestion: {str(e)}"
                            })
                        continue
                    
                    elif message_type == 'upload_document':
                        # Handle document upload via WebSocket (temporary solution)
                        print(f"[ORGANIZATION_PROFILE] Received document upload request")
                        try:
                            profile_id = data.get('profile_id')
                            
                            # Check if organization name has been provided
                            if not profile_id or profile_id == 'new-profile':
                                await websocket.send_json({
                                    "type": "document_upload_rejected",
                                    "message": "Please provide your organization name before uploading documents. I need to create your profile first."
                                })
                                continue
                            
                            document_id = data.get('document_id')
                            document_name = data.get('document_name')
                            document_content_base64 = data.get('document_content_base64')
                            
                            print(f"[ORGANIZATION_PROFILE] Uploading document: {document_name} for profile: {profile_id}")
                            
                            # Store document in S3 (no async processing needed)
                            import boto3
                            import base64
                            import uuid
                            from datetime import datetime
                            
                            s3_client = boto3.client('s3')
                            bucket_name = os.environ.get('DOCUMENTS_BUCKET', '')
                            
                            # Decode base64 content
                            document_bytes = base64.b64decode(document_content_base64)
                            
                            # Generate S3 key for the document
                            file_extension = os.path.splitext(document_name)[1]
                            s3_key = f"organization_profiles/{profile_id}/documents/{document_id}{file_extension}"
                            
                            # Upload to S3
                            s3_client.put_object(
                                Bucket=bucket_name,
                                Key=s3_key,
                                Body=document_bytes,
                                ContentType='application/vnd.openxmlformats-officedocument.wordprocessingml.document' if file_extension == '.docx' else 'application/octet-stream'
                            )
                            
                            print(f"[ORGANIZATION_PROFILE] Document uploaded to S3: {s3_key}")
                            
                            # Send success response (no processing step needed)
                            await websocket.send_json({
                                "type": "document_upload_success",
                                "document_id": document_id,
                                "profile_id": profile_id,
                                "document_name": document_name,
                                "message": "Document uploaded successfully"
                            })
                            
                        except Exception as e:
                            print(f"[ORGANIZATION_PROFILE] Error uploading document: {e}")
                            import traceback
                            traceback.print_exc()
                            await websocket.send_json({
                                "type": "document_processing_failed",
                                "document_id": data.get('document_id'),
                                "status": "failed",
                                "error": str(e),
                                "message": f"Failed to upload document: {str(e)}"
                            })
                        continue
                    
                    # Handle regular messages (both with and without type field)
                    print(f"[ORGANIZATION_PROFILE] Received data: {data}")
                    message = data.get('message', '')
                    tab_id = data.get('tab_id') or data.get('project_id')
                    input_mode = data.get('input_mode', 'text')
                    
                    print(f"[ORGANIZATION_PROFILE] Extracted - message: '{message}', tab_id: {tab_id}, input_mode: {input_mode}")
                    
                    if not message.strip():
                        print(f"[ORGANIZATION_PROFILE] Skipping empty message")
                        continue
                    
                    print(f"[ORGANIZATION_PROFILE] Processing message: {message}")
                    await websocket.send_json({"status": "processing", "agent": self.agent_name, "tab_id": tab_id})
                    
                    try:
                        # Process message with context
                        processed_message = self._process_message_for_context(message, input_mode, session_id)
                        
                        # Process with streaming and session context
                        result = ""
                        async for chunk in self.wrapped_agent.stream_async(processed_message, session_id, user_id):
                            if isinstance(chunk, dict) and "data" in chunk:
                                await websocket.send_json({"type": "stream", "data": chunk["data"], "tab_id": tab_id})
                                result += chunk["data"]
                            elif isinstance(chunk, dict) and "current_tool_use" in chunk:
                                await websocket.send_json({"type": "tool", "tool": chunk["current_tool_use"]["name"], "tab_id": tab_id})
                            elif isinstance(chunk, str):
                                await websocket.send_json({"type": "stream", "data": chunk, "tab_id": tab_id})
                                result += chunk
                        
                        # Extract progress information from conversation flow
                        progress_data = None
                        try:
                            # Access the actual agent instance (not the wrapped one)
                            actual_agent = self.agent_instance
                            if hasattr(actual_agent, 'conversation_flow') and actual_agent.conversation_flow:
                                completeness = actual_agent.conversation_flow._calculate_completeness()
                                progress_data = {
                                    "completeness": completeness['score'],
                                    "gathered_sections": completeness['gathered_sections'],
                                    "missing_sections": completeness['missing_sections']
                                }
                                print(f"[ORGANIZATION_PROFILE] Progress: {int(completeness['score'] * 100)}% - Gathered: {completeness['gathered_sections']}, Missing: {completeness['missing_sections']}")
                            else:
                                print(f"[ORGANIZATION_PROFILE] No conversation_flow found on agent")
                        except Exception as e:
                            print(f"[ORGANIZATION_PROFILE] Could not extract progress: {e}")
                            import traceback
                            print(f"[ORGANIZATION_PROFILE] Traceback: {traceback.format_exc()}")
                        
                        # Generate appropriate response based on current mode
                        response_data = self._process_agent_response(result)
                        
                        # Send profile fields update
                        try:
                            if hasattr(actual_agent, 'conversation_flow') and actual_agent.conversation_flow:
                                gathered = actual_agent.conversation_flow.conversation_state.get('gathered_info', {})
                                fields = []
                                for field_name, field_data in gathered.items():
                                    if isinstance(field_data, dict):
                                        fields.append({
                                            'name': field_name,
                                            'label': field_name.replace('_', ' ').title(),
                                            'value': str(field_data.get('value', ''))[:100],
                                            'source': field_data.get('source', 'user')
                                        })
                                    elif field_data:
                                        fields.append({
                                            'name': field_name,
                                            'label': field_name.replace('_', ' ').title(),
                                            'value': str(field_data)[:100],
                                            'source': 'user'
                                        })
                                if fields:
                                    await websocket.send_json({
                                        "type": "profile_fields_update",
                                        "fields": fields
                                    })
                        except Exception as e:
                            print(f"[ORGANIZATION_PROFILE] Could not send profile fields: {e}")
                        response_data.update({
                            "type": "complete",
                            "session_id": session_id,
                            "tab_id": tab_id
                        })
                        
                        # Add progress information if available
                        if progress_data:
                            response_data["progress"] = progress_data
                        
                        # Check if voice mode is enabled and generate speech
                        if input_mode == 'voice':
                            # Ensure voice session exists and voice mode is enabled
                            if session_id not in self.voice_handler.active_sessions:
                                await self.voice_handler.start_voice_session(
                                    session_id=session_id,
                                    user_id='websocket-user',
                                    voice_settings={'engine': 'neural', 'voice_id': 'Joanna'}
                                )
                            
                            # Enable voice mode for this session
                            self.voice_handler.active_sessions[session_id]['voice_mode'] = True
                            
                            print(f"[ORGANIZATION_PROFILE] Voice mode enabled for session: {session_id}")
                            print(f"[ORGANIZATION_PROFILE] Generating streaming speech for voice mode")
                            
                            # Optimize response for voice output
                            voice_optimized_response = self._optimize_response_for_voice(result)
                            context = self._determine_voice_context(result)
                            
                            # Use sentence-by-sentence streaming
                            async def websocket_callback(chunk_data):
                                chunk_data["tab_id"] = tab_id
                                await websocket.send_json(chunk_data)
                            
                            streaming_result = await self.voice_handler.generate_streaming_speech(
                                session_id=session_id,
                                text=voice_optimized_response,
                                websocket_callback=websocket_callback,
                                context=context
                            )
                            
                            print(f"[ORGANIZATION_PROFILE] Streaming speech result: {streaming_result.get('status')}")
                            
                            # Add streaming info to response
                            if streaming_result.get('status') == 'success':
                                response_data["streaming_audio"] = True
                                response_data["total_audio_chunks"] = streaming_result.get('total_sentences', 0)
                        
                        await websocket.send_json(response_data)
                        
                    except Exception as e:
                        print(f"[ORGANIZATION_PROFILE] Error processing message: {e}")
                        await websocket.send_json({"response": f"Error: {str(e)}", "status": "error", "tab_id": tab_id})
                    
            except WebSocketDisconnect:
                print(f"[ORGANIZATION_PROFILE] WebSocket disconnected for session: {session_id}")
                # Clean up voice session
                await self.voice_handler.end_voice_session(session_id)
            except Exception as e:
                print(f"[ORGANIZATION_PROFILE] WebSocket error: {str(e)}")
                await websocket.close(code=1011, reason="Internal error")

    def _add_websocket_endpoints(self, app):
        """Override parent method to add voice-enhanced WebSocket endpoints"""
        # Add the enhanced chat WebSocket that includes voice capabilities
        self._add_enhanced_chat_websocket(app)
        
        # Add progress WebSocket (keeping original functionality)
        @app.websocket("/ws/progress")
        async def websocket_progress(websocket: WebSocket):
            token = websocket.query_params.get('token')
            if not token:
                await websocket.close(code=1008, reason="JWT token required")
                return
            
            from agents.shared.jwt_validator import validate_cognito_token
            payload = validate_cognito_token(token)
            if not payload:
                await websocket.close(code=1008, reason="Invalid JWT token")
                return
            
            await websocket.accept()
            self._progress_websocket = websocket
            
            try:
                while True:
                    await websocket.receive_text()
            except Exception as e:
                print(f"[{self.agent_name.upper()}] Progress WebSocket error: {e}")
            finally:
                self._progress_websocket = None

    def _add_http_endpoints(self, app):
        """Add HTTP endpoints for audio streaming"""
        from fastapi import Request
        
        @app.get("/api/voice/audio/{audio_id}")
        async def stream_audio(
            audio_id: str,
            request: Request,
            authorization: Optional[str] = Header(None)
        ):
            """Stream audio via HTTP (through ALB) - industry standard approach"""
            print(f"[ORGANIZATION_PROFILE] Audio request received for: {audio_id}")
            
            # Validate JWT token
            if not authorization:
                print(f"[ORGANIZATION_PROFILE] No authorization header")
                raise HTTPException(status_code=401, detail="Authorization header required")
            
            token = authorization.replace("Bearer ", "")
            
            from agents.shared.jwt_validator import validate_cognito_token
            payload = validate_cognito_token(token)
            if not payload:
                print(f"[ORGANIZATION_PROFILE] Invalid token")
                raise HTTPException(status_code=401, detail="Invalid token")
            
            # Get audio from cache
            audio_info = self.voice_handler.audio_cache.get(audio_id)
            if not audio_info:
                print(f"[ORGANIZATION_PROFILE] Audio not found in cache: {audio_id}")
                print(f"[ORGANIZATION_PROFILE] Available audio IDs: {list(self.voice_handler.audio_cache.keys())}")
                raise HTTPException(status_code=404, detail="Audio not found or expired")
            
            print(f"[ORGANIZATION_PROFILE] Streaming audio: {audio_id}, size: {len(audio_info['data'])} bytes")
            
            # Stream audio with proper headers for browser playback
            # Add CORS headers explicitly like Lambda functions do
            return StreamingResponse(
                io.BytesIO(audio_info['data']),
                media_type=f"audio/{audio_info['format']}",
                headers={
                    "Accept-Ranges": "bytes",
                    "Cache-Control": "private, max-age=3600",
                    "Content-Length": str(len(audio_info['data'])),
                    "X-Audio-Format": audio_info['format'],
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
                    'Access-Control-Allow-Methods': 'OPTIONS,GET'
                }
            )
        
        @app.get("/api/voice/health")
        async def voice_health():
            """Health check for voice services"""
            return {
                "status": "healthy",
                "active_sessions": len(self.voice_handler.active_sessions),
                "cached_audio": len(self.voice_handler.audio_cache)
            }
    
    def create_server(self):
        """Create and return the FastAPI server with voice capabilities"""
        app = super().create_server()
        
        # Add CORS middleware to handle OPTIONS requests with environment-based allowed origins
        allowed_origins = os.getenv('ALLOWED_ORIGINS', '*').split(',')
        app.add_middleware(
            CORSMiddleware,
            allow_origins=allowed_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Add HTTP endpoints for audio streaming
        self._add_http_endpoints(app)
        
        print(f"[ORGANIZATION_PROFILE] Voice-enhanced chat WebSocket ready")
        print(f"[ORGANIZATION_PROFILE] HTTP audio streaming endpoint: /api/voice/audio/{{audio_id}}")
        return app

def create_organization_profile_server():
    """Create and return organization profile server"""
    server = OrganizationProfileServer()
    return server.create_server()


if __name__ == "__main__":
    server = OrganizationProfileServer()
    server.run()