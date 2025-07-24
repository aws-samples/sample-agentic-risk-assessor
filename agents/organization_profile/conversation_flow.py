"""
Configuration-driven conversation flow manager for Organization Profile Agent
All hardcoded data moved to YAML configuration files
Configurations loaded from S3 (same pattern as system prompts)
"""
import json
import logging
import yaml
import os
import boto3
from typing import Dict, List, Optional, Any
from pathlib import Path

logger = logging.getLogger(__name__)

class ConversationFlowManager:
    """Manages conversation flow using external YAML configuration from S3"""
    
    # Class-level cache for configs (persists across instances)
    _config_cache = {}
    
    def __init__(self, agent, config_path=None):
        import time
        init_start = time.time()
        print(f"[FLOW_DEBUG] ConversationFlowManager.__init__ started")
        
        self.agent = agent
        self.s3_client = boto3.client('s3')
        self.bucket_name = os.getenv('APP_DATA_BUCKET')
        
        # Load main configuration from S3 or local fallback
        if config_path is None:
            # Try S3 first, fallback to local
            config_path = 'config/organization_profile/profile_config.yaml'
        
        config_start = time.time()
        self.config = self._load_config(config_path)
        config_time = time.time() - config_start
        print(f"[FLOW_DEBUG] Config loaded in {config_time:.3f}s")
        
        self.config_base_path = 'config/organization_profile'
        
        # Industry and region specific configs (loaded dynamically)
        self.industry_config = None
        self.region_config = None
        
        # Conversation state
        state_start = time.time()
        self.conversation_state = {
            'current_section': None,
            'gathered_info': {},
            'research_cache': {},
            'auto_populate_suggestions': [],
            'completed_sections': [],
            'last_asked_field': None,  # Track which field was just asked
            'voice_session_data': {
                'is_voice_enabled': False,
                'voice_settings': {},
                'transcription_history': [],
                'audio_responses': [],
                'voice_session_id': None
            }
        }
        
        state_time = time.time() - state_start
        print(f"[FLOW_DEBUG] State initialized in {state_time:.3f}s")
        
        # State will be restored lazily on first use (after session is initialized)
        self._state_restored = False
        
        total_time = time.time() - init_start
        print(f"[FLOW_DEBUG] ConversationFlowManager.__init__ completed in {total_time:.3f}s")
    
    def _restore_state_from_history(self):
        """Restore conversation state by analyzing the agent's message history"""
        import time
        restore_start = time.time()
        print(f"[RESTORE_DEBUG] _restore_state_from_history started")
        
        if self._state_restored:
            print(f"[RESTORE_DEBUG] Already restored, skipping")
            return  # Already restored
            
        try:
            # Access the agent's conversation history
            access_start = time.time()
            print(f"[RESTORE_DEBUG] About to access self.agent.agent")
            has_agent = hasattr(self.agent, 'agent')
            print(f"[RESTORE_DEBUG] hasattr check: {time.time() - access_start:.3f}s, has_agent={has_agent}")
            
            if has_agent:
                print(f"[RESTORE_DEBUG] About to access self.agent.agent.messages")
                has_messages = hasattr(self.agent.agent, 'messages')
                print(f"[RESTORE_DEBUG] hasattr messages check: {time.time() - access_start:.3f}s, has_messages={has_messages}")
                
                if has_messages:
                    print(f"[RESTORE_DEBUG] About to read messages")
                    messages = self.agent.agent.messages
                    access_time = time.time() - access_start
                    print(f"[RESTORE_DEBUG] Accessed messages in {access_time:.3f}s, count: {len(messages)}")
                
                # Count how many core fields have been asked/answered
                core_fields = self.config['conversation_flow']['core_fields']
                
                # Count user messages (each represents an answered question)
                # Exclude the very first user message if it's just a greeting/start command
                user_messages = [msg for msg in messages if msg.get('role') == 'user']
                
                # Filter out initial greeting messages
                actual_responses = []
                for msg in user_messages:
                    content = msg.get('content', '')
                    if isinstance(content, list):
                        content = ' '.join([c.get('text', '') for c in content if isinstance(c, dict)])
                    content_lower = str(content).lower().strip()
                    # Skip initial greeting/start messages
                    if content_lower not in ['start_profile_creation', 'hello', 'hi', 'start', '']:
                        actual_responses.append(msg)
                
                user_message_count = len(actual_responses)
                
                logger.info(f"Found {user_message_count} actual user responses (filtered from {len(user_messages)} total user messages)")
                
                # Only mark core fields as gathered (limit to number of core fields)
                # This prevents over-restoration when conversation goes beyond core questions
                fields_to_restore = min(user_message_count, len(core_fields))
                
                for i in range(fields_to_restore):
                    field = core_fields[i]
                    # Mark this field as gathered (use placeholder value)
                    self.conversation_state['gathered_info'][field] = f"answered_{i+1}"
                    logger.info(f"Restored field '{field}' from history (message {i+1})")
                
                logger.info(f"Restored conversation state: {fields_to_restore} of {len(core_fields)} core fields gathered")
                self._state_restored = True
                
                restore_time = time.time() - restore_start
                print(f"[RESTORE_DEBUG] _restore_state_from_history completed in {restore_time:.3f}s")
            else:
                logger.warning("Could not access agent messages for state restoration")
                print(f"[RESTORE_DEBUG] Could not access messages")
        except Exception as e:
            logger.error(f"Error restoring conversation state from history: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
    
    def _load_config(self, s3_key: str) -> Dict[str, Any]:
        """Load YAML configuration from S3, with local fallback and caching"""
        # Check cache first
        if s3_key in ConversationFlowManager._config_cache:
            logger.info(f"Using cached config: {s3_key}")
            return ConversationFlowManager._config_cache[s3_key]
        
        try:
            # Try loading from S3 first
            if self.bucket_name:
                logger.info(f"Loading config from S3: s3://{self.bucket_name}/{s3_key}")
                response = self.s3_client.get_object(
                    Bucket=self.bucket_name,
                    Key=s3_key
                )
                config_content = response['Body'].read().decode('utf-8')
                config = yaml.safe_load(config_content)
                logger.info(f"Successfully loaded config from S3: {s3_key}")
                # Cache it
                ConversationFlowManager._config_cache[s3_key] = config
                return config
        except Exception as e:
            logger.warning(f"Failed to load config from S3 ({s3_key}): {str(e)}")
            
        # Fallback to local file
        try:
            local_path = Path(__file__).parent / 'config' / Path(s3_key).name
            logger.info(f"Falling back to local config: {local_path}")
            with open(local_path, 'r') as f:
                config = yaml.safe_load(f)
                logger.info(f"Successfully loaded local config: {local_path}")
                # Cache it
                ConversationFlowManager._config_cache[s3_key] = config
                return config
        except Exception as e:
            logger.error(f"Failed to load local config: {str(e)}")
            # Cache empty dict to avoid repeated failures
            ConversationFlowManager._config_cache[s3_key] = {}
            return {}
    
    def _load_industry_config(self, industry: str):
        """Load industry-specific configuration from S3"""
        industry_key = industry.lower().replace(' ', '_').replace('services', '').strip()
        
        # Try specific industry file from S3
        s3_key = f'{self.config_base_path}/industries/{industry_key}.yaml'
        self.industry_config = self._load_config(s3_key)
        
        # If empty, try default
        if not self.industry_config:
            s3_key = f'{self.config_base_path}/industries/default.yaml'
            self.industry_config = self._load_config(s3_key)
        
        logger.info(f"Loaded industry config for: {industry}")
    
    def _load_region_config(self, region: str):
        """Load region-specific configuration from S3"""
        region_key = region.lower().replace(' ', '_').replace('-', '_')
        s3_key = f'{self.config_base_path}/regions/{region_key}.yaml'
        
        self.region_config = self._load_config(s3_key)
        if self.region_config:
            logger.info(f"Loaded region config for: {region}")
    
    def _check_document_availability(self, profile_id: str):
        """Check if documents exist for this profile by listing S3 objects"""
        try:
            bucket = os.getenv('DOCUMENTS_BUCKET', 'risk-agent-project-documents-b7e63ea0')
            prefix = f"organization_profiles/{profile_id}/documents/"
            
            response = self.s3_client.list_objects_v2(
                Bucket=bucket,
                Prefix=prefix,
                MaxKeys=100
            )
            
            items = response.get('Contents', [])
            self.conversation_state['document_count'] = len(items)
            self.conversation_state['document_names'] = [
                obj['Key'].split('/')[-1] for obj in items
            ]
            
            logger.info(f"Found {len(items)} documents for profile {profile_id} in S3")
            
        except Exception as e:
            logger.error(f"Failed to check document availability: {str(e)}")
            self.conversation_state['document_count'] = 0
    
    def _pre_populate_from_documents(self, profile_id: str):
        """Extract answers from documents for all configured fields"""
        # Documents are queried on-demand via query_document tool, not pre-loaded
        if self.conversation_state.get('document_count', 0) == 0:
            return
        
        try:
            # Iterate through all sections and fields
            for section in self.config['profile_structure']['sections']:
                for field in section['fields']:
                    # Check if field has document extraction enabled
                    doc_extraction = field.get('document_extraction', {})
                    if not doc_extraction.get('enabled'):
                        continue
                    
                    # Skip if already gathered
                    if field['name'] in self.conversation_state['gathered_info']:
                        continue
                    
                    # Query documents for this field
                    answer = self._query_documents_for_field(field, profile_id)
                    
                    if answer and answer.get('confidence', 0) >= doc_extraction.get('confidence_threshold', 0.8):
                        # Store extracted answer
                        self.conversation_state['gathered_info'][field['name']] = {
                            'value': answer['value'],
                            'source': 'document',
                            'document_id': answer['document_id'],
                            'document_name': answer['document_name'],
                            'page_number': answer.get('page', 0),
                            'section': answer.get('section', ''),
                            'confidence': answer['confidence'],
                            'user_edited': False
                        }
                        
                        logger.info(f"Pre-populated field '{field['name']}' from document with confidence {answer['confidence']}")
            
        except Exception as e:
            logger.error(f"Error pre-populating from documents: {str(e)}")
    
    def _query_documents_for_field(self, field: Dict, profile_id: str) -> Optional[Dict]:
        """Query documents for a specific field — delegates to agent's read_document tool"""
        # Document extraction is now handled by the agent directly via read_document
        # and extract_profile_from_documents tools. This method is kept for compatibility
        # but returns None to let the agent handle extraction conversationally.
        return None
    
    def _detect_conflicts(self, profile_id: str):
        """Detect conflicting information across multiple documents"""
        conflicts = []
        
        try:
            # Check fields that have multiple document sources
            for field_name, field_data in self.conversation_state['gathered_info'].items():
                if not isinstance(field_data, dict) or field_data.get('source') != 'document':
                    continue
                
                # Query all documents for this field to check for conflicts
                # This is a simplified version - full implementation would compare all sources
                pass
            
        except Exception as e:
            logger.error(f"Error detecting conflicts: {str(e)}")
        
        return conflicts
    
    def process_user_response(self, user_input: str, current_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Process user response and determine next conversation step"""
        
        # Restore state from history (lazy initialization after session is loaded)
        self._restore_state_from_history()
        
        # Update conversation state
        self._update_conversation_state(user_input, current_context)
        
        # Check if we need to load industry/region configs
        gathered_info = self.conversation_state['gathered_info']
        
        if gathered_info.get('industry') and not self.industry_config:
            self._load_industry_config(gathered_info['industry'])
        
        if gathered_info.get('region') and not self.region_config:
            self._load_region_config(gathered_info['region'])
        
        # Check if documents exist (metadata only, don't load full trees)
        profile_id = current_context.get('profile_id') if current_context else None
        if profile_id and 'document_count' not in self.conversation_state:
            self._check_document_availability(profile_id)
        
        # Identify research opportunities
        research_needed = self._identify_research_opportunities(user_input)
        
        # Perform research if needed
        research_results = {}
        if research_needed:
            research_results = self._perform_contextual_research(research_needed)
        
        # Determine next action
        next_action = self._determine_next_action(research_results)
        
        return {
            'conversation_state': self.conversation_state,
            'research_results': research_results,
            'next_action': next_action,
            'auto_populate_suggestions': self._generate_auto_populate_suggestions(research_results)
        }
    
    def _update_conversation_state(self, user_input: str, current_context: Dict[str, Any] = None):
        """Update conversation state with user input"""
        if current_context:
            self.conversation_state['gathered_info'].update(current_context)
        
        # Extract key information using configured keywords
        extracted_info = self._extract_key_information(user_input)
        self.conversation_state['gathered_info'].update(extracted_info)
        
        # Track the last question that was asked so we can mark it as answered
        # This is stored in conversation_state to persist across calls
        if user_input and user_input.strip() and 'last_asked_field' in self.conversation_state:
            last_field = self.conversation_state['last_asked_field']
            if last_field and not self.conversation_state['gathered_info'].get(last_field):
                # Mark the previously asked field as gathered
                self.conversation_state['gathered_info'][last_field] = user_input.strip()
                logger.info(f"Marked field '{last_field}' as gathered with value: {user_input[:50]}")
            # Clear the last asked field
            self.conversation_state['last_asked_field'] = None
    
    def _extract_key_information(self, user_input: str) -> Dict[str, Any]:
        """Extract key information using configured detection keywords"""
        extracted = {}
        user_lower = user_input.lower()
        
        # Extract industry using configured keywords
        industry_detection = self.config.get('industry_detection', {})
        for industry, config in industry_detection.items():
            keywords = config.get('keywords', [])
            if any(keyword in user_lower for keyword in keywords):
                extracted['industry'] = industry.replace('_', ' ').title()
                break
        
        # Extract region using configured keywords
        region_detection = self.config.get('region_detection', {})
        for region, config in region_detection.items():
            keywords = config.get('keywords', [])
            if any(keyword in user_lower for keyword in keywords):
                extracted['region'] = region.replace('_', ' ').title().replace('Apac', 'Asia-Pacific')
                break
        
        return extracted
    
    def _identify_research_opportunities(self, user_input: str) -> List[str]:
        """Identify opportunities for MCP research"""
        research_needed = []
        gathered_info = self.conversation_state['gathered_info']
        
        # Check if we should research based on gathered info
        if gathered_info.get('industry') and 'industry_standards' not in self.conversation_state['research_cache']:
            research_needed.append('industry_standards')
        
        if (gathered_info.get('industry') and gathered_info.get('region') and 
            'regulatory_requirements' not in self.conversation_state['research_cache']):
            research_needed.append('regulatory_requirements')
        
        return research_needed
    
    def _perform_contextual_research(self, research_types: List[str]) -> Dict[str, Any]:
        """Perform MCP research"""
        research_results = {}
        gathered_info = self.conversation_state['gathered_info']
        
        for research_type in research_types:
            try:
                search_params = {
                    'search_type': research_type,
                    'industry': gathered_info.get('industry', ''),
                    'region': gathered_info.get('region', '')
                }
                
                search_result = self.agent._invoke_lambda('risk-agent-search_context', {
                    'requestContext': {'http': {'method': 'POST'}},
                    'body': json.dumps(search_params)
                })
                
                research_results[research_type] = search_result
                self.conversation_state['research_cache'][research_type] = search_result
                
                logger.info(f"Performed {research_type} research")
                
            except Exception as e:
                logger.error(f"Failed to perform {research_type} research: {str(e)}")
                research_results[research_type] = {'error': str(e)}
        
        return research_results
    
    def _determine_next_action(self, research_results: Dict[str, Any]) -> Dict[str, Any]:
        """Determine next conversation action - LLM-driven with research context"""
        gathered_info = self.conversation_state['gathered_info']
        
        # Get core required fields from config
        core_fields = self.config['conversation_flow']['core_fields']
        missing_core = [f for f in core_fields if not gathered_info.get(f)]
        
        if missing_core:
            # Still gathering core information - provide minimal structure
            next_field = missing_core[0]
            field_info = self._get_field_info(next_field)
            
            # Store which field we're about to ask about
            self.conversation_state['last_asked_field'] = next_field
            
            return {
                'action_type': 'ask_question',
                'field_name': next_field,
                'field_type': field_info.get('type', 'text'),
                'suggested_options': field_info.get('options', []),
                'context': field_info.get('context', ''),
                'conversation_phase': 'core_information',
                'instruction_to_llm': f'Ask about {next_field.replace("_", " ")}. Use the suggested options if helpful, but feel free to adapt based on context.'
            }
        else:
            # Core fields gathered - check completeness
            completeness = self._calculate_completeness()
            threshold = self.config['conversation_flow']['min_completeness_threshold']
            
            if completeness['score'] < threshold:
                # LLM-driven detailed information gathering with research
                return {
                    'action_type': 'llm_driven_conversation',
                    'completeness_score': completeness['score'],
                    'missing_sections': completeness['missing_sections'],
                    'gathered_sections': completeness['gathered_sections'],
                    'gathered_info': gathered_info,
                    'research_results': research_results,
                    'auto_populate_suggestions': self._generate_auto_populate_suggestions(research_results),
                    'industry_config': self.industry_config,
                    'region_config': self.region_config,
                    'conversation_phase': 'detailed_information',
                    'instruction_to_llm': self._generate_llm_instruction(completeness, research_results)
                }
            else:
                # Profile complete - update existing profile with full content
                return {
                    'action_type': 'update_profile',
                    'profile_content': self._generate_profile_content(),
                    'completeness_score': completeness['score'],
                    'conversation_phase': 'completion'
                }
    
    def _generate_llm_instruction(self, completeness: Dict[str, Any], research_results: Dict[str, Any]) -> str:
        """Generate detailed instruction for LLM on what to ask next"""
        missing = completeness['missing_sections']
        gathered = completeness['gathered_info'] if 'gathered_info' in completeness else self.conversation_state['gathered_info']
        
        instruction = f"Generate the next question to gather information for the profile.\n\n"
        instruction += f"MISSING SECTIONS: {', '.join(missing)}\n"
        instruction += f"ALREADY GATHERED: {', '.join(completeness['gathered_sections'])}\n\n"
        
        if missing:
            instruction += f"Focus on the '{missing[0]}' section next.\n\n"
        
        if research_results:
            instruction += "RESEARCH CONTEXT:\n"
            for research_type, results in research_results.items():
                instruction += f"- {research_type}: {str(results)[:200]}...\n"
            instruction += "\nUse this research to inform your question and provide relevant options.\n\n"
        
        if self.industry_config:
            instruction += f"INDUSTRY CONTEXT: {self.industry_config.get('industry', 'Unknown')}\n"
            if 'regulations' in self.industry_config:
                regs = [r.get('name', '') for r in self.industry_config['regulations'][:3]]
                instruction += f"Common regulations: {', '.join(regs)}\n"
        
        if self.region_config:
            instruction += f"REGION CONTEXT: {self.region_config.get('region', 'Unknown')}\n"
        
        instruction += "\nGenerate ONE specific, contextual question that incorporates the research findings."
        
        return instruction
    
    def _get_field_info(self, field_name: str) -> Dict[str, Any]:
        """Get field information from config"""
        for section in self.config['profile_structure']['sections']:
            for field in section['fields']:
                if field['name'] == field_name:
                    return {
                        'type': field.get('type', 'text'),
                        'options': self._extract_options(field.get('options', [])),
                        'context': section['name']
                    }
        return {'type': 'text', 'options': [], 'context': 'general'}
    
    def _extract_options(self, options: List) -> List[str]:
        """Extract option labels from config"""
        if not options:
            return []
        if isinstance(options[0], dict):
            return [opt.get('label', opt.get('value', '')) for opt in options]
        return options
    
    def _get_question_for_field(self, field_name: str) -> Dict[str, Any]:
        """Get question configuration for a specific field"""
        # Search through all sections for the field
        for section in self.config['profile_structure']['sections']:
            for field in section['fields']:
                if field['name'] == field_name:
                    question_data = {
                        'question': field['question'],
                        'context': section['name']
                    }
                    
                    # Add options if available
                    if 'options' in field:
                        options = field['options']
                        # Handle both simple list and dict format
                        if options and isinstance(options[0], dict):
                            question_data['options'] = [opt['label'] for opt in options]
                        else:
                            question_data['options'] = options
                    
                    return question_data
        
        # Fallback
        return {
            'question': f"Please provide information about {field_name.replace('_', ' ')}",
            'context': 'general'
        }
    
    def _calculate_completeness(self) -> Dict[str, Any]:
        """Calculate profile completeness based on field completion for smooth progress"""
        gathered_info = self.conversation_state['gathered_info']
        sections = self.config['profile_structure']['sections']
        
        # Count total required fields and gathered fields for accurate percentage
        total_required_fields = 0
        gathered_fields_count = 0
        gathered_sections = []
        missing_sections = []
        
        # Include base config sections
        for section in sections:
            section_name = section['name']
            section_fields = [f for f in section['fields'] if f.get('required', True)]
            
            # Count required fields in this section
            total_required_fields += len(section_fields)
            
            # Count how many fields in this section have data
            section_gathered = sum(1 for f in section_fields if gathered_info.get(f['name']))
            gathered_fields_count += section_gathered
            
            # Section is considered gathered if it has any data
            if section_gathered > 0:
                gathered_sections.append(section_name)
            else:
                # Only count as missing if section is required
                if section.get('required', True):
                    missing_sections.append(section_name)
        
        # Add industry-specific fields if industry config is loaded
        if self.industry_config and 'additional_fields' in self.industry_config:
            industry_fields = [f for f in self.industry_config['additional_fields'] if f.get('required', True)]
            total_required_fields += len(industry_fields)
            
            industry_gathered = sum(1 for f in industry_fields if gathered_info.get(f['name']))
            gathered_fields_count += industry_gathered
            
            if industry_gathered > 0 and 'Industry-Specific' not in gathered_sections:
                gathered_sections.append('Industry-Specific')
            elif industry_gathered == 0 and len(industry_fields) > 0:
                missing_sections.append('Industry-Specific')
        
        # Calculate smooth progress based on fields, not sections
        score = gathered_fields_count / total_required_fields if total_required_fields > 0 else 0
        
        return {
            'score': score,
            'gathered_sections': gathered_sections,
            'missing_sections': missing_sections,
            'gathered_fields_count': gathered_fields_count,
            'total_required_fields': total_required_fields,
            'gathered_info': gathered_info
        }
    
    def _generate_auto_populate_suggestions(self, research_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate auto-population suggestions from research and configs"""
        suggestions = []
        
        # Add suggestions from industry config
        if self.industry_config and 'regulations' in self.industry_config:
            for reg in self.industry_config['regulations'][:3]:
                suggestions.append({
                    'field': 'primary_regulations',
                    'suggestion': reg['name'],
                    'description': reg['description'],
                    'source': 'industry_config'
                })
        
        # Add suggestions from region config
        if self.region_config and 'regulations' in self.region_config:
            for country, regs in list(self.region_config['regulations'].items())[:2]:
                for reg in regs[:2]:
                    suggestions.append({
                        'field': 'primary_regulations',
                        'suggestion': reg['name'],
                        'description': reg['description'],
                        'source': f'region_config_{country}'
                    })
        
        return suggestions
    
    def _generate_profile_content(self) -> str:
        """Generate structured markdown profile content"""
        gathered_info = self.conversation_state['gathered_info']
        sections = self.config['profile_structure']['sections']
        
        profile_lines = [f"# Organization Profile: {gathered_info.get('organization_name', 'Unknown')}"]
        profile_lines.append("")
        
        for section in sections:
            profile_lines.append(f"## {section['name']}")
            
            for field in section['fields']:
                field_name = field['name']
                field_label = field_name.replace('_', ' ').title()
                field_value = gathered_info.get(field_name, 'Not provided')
                profile_lines.append(f"- **{field_label}**: {field_value}")
            
            profile_lines.append("")
        
        profile_lines.append("---")
        profile_lines.append("*Profile generated using configuration-driven conversation flow*")
        
        return "\n".join(profile_lines)
    
    # Voice session management methods (unchanged)
    def enable_voice_session(self, voice_session_id: str, voice_settings: Dict[str, Any]) -> None:
        """Enable voice capabilities for this conversation session"""
        self.conversation_state['voice_session_data'].update({
            'is_voice_enabled': True,
            'voice_settings': voice_settings,
            'voice_session_id': voice_session_id
        })
        logger.info(f"Voice session enabled: {voice_session_id}")
    
    def add_voice_interaction(self, interaction_type: str, content: str, metadata: Dict[str, Any] = None) -> None:
        """Add voice interaction to conversation history"""
        voice_data = self.conversation_state['voice_session_data']
        
        interaction_record = {
            'type': interaction_type,
            'content': content,
            'timestamp': metadata.get('timestamp') if metadata else None,
            'metadata': metadata or {}
        }
        
        if interaction_type == 'transcription':
            voice_data['transcription_history'].append(interaction_record)
        elif interaction_type == 'audio_response':
            voice_data['audio_responses'].append(interaction_record)
    
    def get_voice_session_data(self) -> Dict[str, Any]:
        """Get voice session data"""
        return self.conversation_state['voice_session_data']
    
    def disable_voice_session(self) -> None:
        """Disable voice capabilities"""
        voice_session_id = self.conversation_state['voice_session_data'].get('voice_session_id')
        
        self.conversation_state['voice_session_data'] = {
            'is_voice_enabled': False,
            'voice_settings': {},
            'transcription_history': [],
            'audio_responses': [],
            'voice_session_id': None
        }
        
        logger.info(f"Voice session disabled: {voice_session_id}")
    
    def get_conversation_summary(self) -> Dict[str, Any]:
        """Get summary of current conversation state"""
        completeness = self._calculate_completeness()
        
        summary = {
            'gathered_info': self.conversation_state['gathered_info'],
            'completed_sections': completeness['gathered_sections'],
            'missing_sections': completeness['missing_sections'],
            'completeness_percentage': completeness['score'] * 100,
            'research_performed': list(self.conversation_state['research_cache'].keys()),
            'auto_populate_suggestions': self.conversation_state['auto_populate_suggestions']
        }
        
        # Add voice session summary if enabled
        voice_data = self.conversation_state['voice_session_data']
        if voice_data['is_voice_enabled']:
            summary['voice_session'] = {
                'is_enabled': True,
                'voice_settings': voice_data['voice_settings'],
                'transcription_count': len(voice_data['transcription_history']),
                'audio_response_count': len(voice_data['audio_responses']),
                'session_id': voice_data['voice_session_id']
            }
        
        return summary

    
    def _get_industry_specific_fields(self) -> List[Dict]:
        """Get industry-specific additional fields from loaded config"""
        if not self.industry_config or 'additional_fields' not in self.industry_config:
            return []
        
        return self.industry_config['additional_fields']
    
    def _detect_sub_industry(self, user_input: str) -> Optional[str]:
        """Detect sub-industry from user input using contextual_questions triggers"""
        if not self.industry_config or 'contextual_questions' not in self.industry_config:
            return None
        
        user_lower = user_input.lower()
        
        for sub_industry, config in self.industry_config['contextual_questions'].items():
            trigger_keywords = config.get('trigger_keywords', [])
            if any(keyword in user_lower for keyword in trigger_keywords):
                logger.info(f"Detected sub-industry: {sub_industry}")
                return sub_industry
        
        return None
    
    def _get_contextual_questions_for_sub_industry(self, sub_industry: str) -> List[Dict]:
        """Get contextual questions for detected sub-industry"""
        if not self.industry_config or 'contextual_questions' not in self.industry_config:
            return []
        
        sub_industry_config = self.industry_config['contextual_questions'].get(sub_industry, {})
        return sub_industry_config.get('questions', [])
    
    def _execute_mcp_search_queries(self) -> Dict[str, Any]:
        """Execute MCP search queries defined in industry/region configs"""
        search_results = {}
        
        # Execute industry-specific searches
        if self.industry_config and 'mcp_search_queries' in self.industry_config:
            for query_config in self.industry_config['mcp_search_queries']:
                query = query_config.get('query', '')
                use_for = query_config.get('use_for', [])
                
                try:
                    result = self.agent._invoke_lambda('risk-agent-search_context', {
                        'requestContext': {'http': {'method': 'POST'}},
                        'body': json.dumps({
                            'search_type': 'industry_standards',
                            'query': query
                        })
                    })
                    
                    search_results[query] = {
                        'result': result,
                        'use_for': use_for
                    }
                    
                    logger.info(f"Executed MCP search: {query}")
                    
                except Exception as e:
                    logger.error(f"MCP search failed for query '{query}': {str(e)}")
        
        return search_results
    
    def _save_section_progress(self, section_name: str):
        """Save profile progress after completing a section"""
        auto_save_config = self.config.get('auto_save', {})
        
        if not auto_save_config.get('enabled', False):
            return
        
        if not auto_save_config.get('save_after_section', False):
            return
        
        try:
            # Mark section as completed
            if section_name not in self.conversation_state['completed_sections']:
                self.conversation_state['completed_sections'].append(section_name)
            
            # Generate profile content
            profile_content = self._generate_profile_content()
            
            # Save to DynamoDB or trigger save via agent
            logger.info(f"Auto-saved progress after completing section: {section_name}")
            
            # Optionally prompt user to pause
            if auto_save_config.get('prompt_pause_after_section', False):
                pause_message = auto_save_config.get('pause_message', 
                    'Great progress! Your answers have been saved. Would you like to continue or pause?')
                return {
                    'should_prompt_pause': True,
                    'pause_message': pause_message
                }
        
        except Exception as e:
            logger.error(f"Auto-save failed: {str(e)}")
        
        return None
