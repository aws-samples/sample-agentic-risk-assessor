"""
Organization Profile Agent - Conversational profile creation and management
"""
import sys
import os
import json
import boto3
sys.path.append('/app')

from agents.shared.base_agent import BaseAgent
from strands.tools import tool
from .conversation_flow import ConversationFlowManager

class OrganizationProfileAgent(BaseAgent):
    def __init__(self, bedrock_model=None):
        import time
        agent_init_start = time.time()
        print(f"[AGENT_DEBUG] OrganizationProfileAgent.__init__ started")
        
        # Initialize conversation flow manager
        self.conversation_flow = None  # Will be initialized after super().__init__
        
        # Create native Strands tools
        tools_start = time.time()
        tools = [
            self._create_create_profile_tool(),
            self._create_update_profile_tool(),
            self._create_get_profile_tool(),
            self._create_list_profiles_tool(),
            self._create_delete_profile_tool(),
            self._create_search_context_tool(),
            self._create_generate_industry_questions_tool(),
            self._create_validate_profile_completeness_tool(),
            self._create_process_conversation_tool(),
            self._create_upload_document_tool(),
            self._create_read_document_tool(),
            self._create_extract_profile_from_documents_tool()
        ]
        tools_time = time.time() - tools_start
        print(f"[AGENT_DEBUG] Tools created in {tools_time:.3f}s")
        
        # Initialize without YAML configuration
        super_start = time.time()
        super().__init__(
            agent_name="OrganizationProfile",
            bedrock_model=bedrock_model,
            system_prompt_key="system_prompts/organization_profile_system_prompt.xml",
            tools=tools
        )
        super_time = time.time() - super_start
        print(f"[AGENT_DEBUG] BaseAgent.__init__ completed in {super_time:.3f}s")
        
        # Initialize conversation flow manager after agent is created
        flow_start = time.time()
        self.conversation_flow = ConversationFlowManager(self)
        flow_time = time.time() - flow_start
        print(f"[AGENT_DEBUG] ConversationFlowManager created in {flow_time:.3f}s")
        
        total_time = time.time() - agent_init_start
        print(f"[AGENT_DEBUG] OrganizationProfileAgent.__init__ completed in {total_time:.3f}s")
    
    def _create_create_profile_tool(self):
        @tool
        def create_profile(profile_name: str, profile_content: str, metadata: dict = None) -> dict:
            """Create a new organization profile with structured markdown content"""
            result = self._invoke_lambda('risk-agent-create_profile', {
                'requestContext': {'http': {'method': 'POST'}},
                'body': json.dumps({
                    'profile_name': profile_name,
                    'profile_content': profile_content,
                    'metadata': metadata or {}
                })
            })
            # Extract and store profile_id from the response
            # The _invoke_lambda method already unwraps the body, so result is the direct data
            if result and isinstance(result, dict) and 'profile' in result:
                profile_data = result['profile']
                if 'id' in profile_data:
                    self.profile_id = profile_data['id']
                    print(f"[ORGANIZATION_PROFILE] ✅ Stored profile_id: {self.profile_id}")
                else:
                    print(f"[ORGANIZATION_PROFILE] ❌ 'id' not found in profile data")
            else:
                print(f"[ORGANIZATION_PROFILE] ❌ Invalid result format or 'profile' not found")
            return result
        return create_profile
    
    def _create_update_profile_tool(self):
        @tool
        def update_profile(profile_id: str, profile_content: str, metadata: dict = None) -> dict:
            """Update an existing organization profile"""
            return self._invoke_lambda('risk-agent-update_profile', {
                'requestContext': {'http': {'method': 'PUT'}},
                'pathParameters': {'id': profile_id},
                'body': json.dumps({
                    'profile_content': profile_content,
                    'metadata': metadata or {}
                })
            })
        return update_profile
    
    def _create_get_profile_tool(self):
        @tool
        def get_profile(profile_id: str) -> dict:
            """Get organization profile content by ID"""
            return self._invoke_lambda('risk-agent-get_profile', {
                'requestContext': {'http': {'method': 'GET'}},
                'pathParameters': {'id': profile_id}
            })
        return get_profile
    
    def _create_list_profiles_tool(self):
        @tool
        def list_profiles() -> dict:
            """List all available organization profiles with metadata"""
            return self._invoke_lambda('risk-agent-list_profiles', {
                'requestContext': {'http': {'method': 'GET'}}
            })
        return list_profiles
    
    def _create_delete_profile_tool(self):
        @tool
        def delete_profile(profile_id: str) -> dict:
            """Delete an organization profile"""
            return self._invoke_lambda('risk-agent-delete_profile', {
                'requestContext': {'http': {'method': 'DELETE'}},
                'pathParameters': {'id': profile_id}
            })
        return delete_profile
    
    def _create_search_context_tool(self):
        @tool
        def search_context(search_type: str, industry: str = None, region: str = None, organization_size: str = None, technology_stack: list = None) -> dict:
            """Search for contextual information using MCP internet search
            
            Args:
                search_type: Type of search - 'industry_standards', 'regulatory_requirements', or 'security_best_practices'
                industry: Industry name for context
                region: Geographic region for regulatory context
                organization_size: Size of organization (small, medium, large)
                technology_stack: List of technologies used
            """
            payload = {
                'search_type': search_type
            }
            
            if industry:
                payload['industry'] = industry
            if region:
                payload['region'] = region
            if organization_size:
                payload['organization_size'] = organization_size
            if technology_stack:
                payload['technology_stack'] = technology_stack
                
            return self._invoke_lambda('risk-agent-search_context', {
                'requestContext': {'http': {'method': 'POST'}},
                'body': json.dumps(payload)
            })
        return search_context
    
    def _create_generate_industry_questions_tool(self):
        @tool
        def generate_industry_questions(industry: str, current_context: dict = None) -> dict:
            """Generate context-aware questions based on industry and current conversation context
            
            Args:
                industry: Industry name for context-specific questions
                current_context: Current conversation context and gathered information
            """
            # Use search to get industry-specific context for question generation
            search_results = self._invoke_lambda('risk-agent-search_context', {
                'requestContext': {'http': {'method': 'POST'}},
                'body': json.dumps({
                    'search_type': 'industry_standards',
                    'industry': industry
                })
            })
            
            # Generate contextual questions based on search results and current context
            return {
                'industry': industry,
                'search_results': search_results,
                'current_context': current_context or {},
                'suggested_questions': self._generate_contextual_questions(industry, search_results, current_context)
            }
        return generate_industry_questions
    
    def _create_validate_profile_completeness_tool(self):
        @tool
        def validate_profile_completeness(profile_content: str, industry: str = None) -> dict:
            """Validate organization profile completeness and suggest improvements
            
            Args:
                profile_content: Current profile content in markdown format
                industry: Industry for context-specific validation
            """
            # Parse profile content to check completeness
            completeness_score = self._calculate_completeness_score(profile_content)
            missing_sections = self._identify_missing_sections(profile_content)
            
            # Get industry-specific suggestions if industry provided
            suggestions = []
            if industry:
                search_results = self._invoke_lambda('risk-agent-search_context', {
                    'requestContext': {'http': {'method': 'POST'}},
                    'body': json.dumps({
                        'search_type': 'industry_standards',
                        'industry': industry
                    })
                })
                suggestions = self._generate_industry_suggestions(search_results, missing_sections)
            
            return {
                'completeness_score': completeness_score,
                'missing_sections': missing_sections,
                'industry_suggestions': suggestions,
                'validation_passed': completeness_score >= 0.8
            }
        return validate_profile_completeness
    
    def _generate_contextual_questions(self, industry: str, search_results: dict, current_context: dict = None) -> list:
        """Generate context-aware questions based on industry research and conversation state"""
        questions = []
        
        # Extract industry standards from search results
        if 'results' in search_results and 'standards' in search_results['results']:
            standards = search_results['results']['standards']
            if standards:
                questions.append({
                    'question': f"Which of these industry standards does your organization currently follow: {', '.join([s.get('name', '') for s in standards[:3]])}?",
                    'context': 'regulatory_compliance',
                    'auto_populate_options': [s.get('name', '') for s in standards],
                    'research_source': 'industry_standards_search'
                })
        
        # Generate questions based on current context gaps
        if current_context:
            if not current_context.get('organization_size'):
                questions.append({
                    'question': "What is the size of your organization (number of employees or annual revenue)?",
                    'context': 'basic_information',
                    'auto_populate_options': ['Small (< 100 employees)', 'Medium (100-1000 employees)', 'Large (1000+ employees)']
                })
            
            if not current_context.get('primary_regions'):
                questions.append({
                    'question': "In which geographic regions does your organization primarily operate?",
                    'context': 'regulatory_environment',
                    'auto_populate_options': ['North America', 'Europe', 'Asia-Pacific', 'Global']
                })
        
        # Industry-specific questions
        industry_questions = self._get_industry_specific_questions(industry)
        questions.extend(industry_questions)
        
        return questions[:5]  # Limit to 5 most relevant questions
    
    def _get_industry_specific_questions(self, industry: str) -> list:
        """Get industry-specific questions based on common requirements"""
        industry_lower = industry.lower()
        questions = []
        
        if 'financial' in industry_lower or 'banking' in industry_lower:
            questions.extend([
                {
                    'question': "Does your organization handle payment card data (requiring PCI DSS compliance)?",
                    'context': 'regulatory_compliance',
                    'auto_populate_options': ['Yes - Level 1 Merchant', 'Yes - Level 2-4 Merchant', 'No']
                },
                {
                    'question': "Are you subject to SOX compliance requirements?",
                    'context': 'regulatory_compliance',
                    'auto_populate_options': ['Yes - Public company', 'Yes - Subsidiary', 'No']
                }
            ])
        
        elif 'healthcare' in industry_lower or 'medical' in industry_lower:
            questions.extend([
                {
                    'question': "Does your organization handle Protected Health Information (PHI)?",
                    'context': 'data_classification',
                    'auto_populate_options': ['Yes - Covered Entity', 'Yes - Business Associate', 'No']
                },
                {
                    'question': "What types of healthcare data do you process?",
                    'context': 'data_classification',
                    'auto_populate_options': ['Patient Records', 'Medical Imaging', 'Billing Information', 'Research Data']
                }
            ])
        
        elif 'technology' in industry_lower or 'software' in industry_lower:
            questions.extend([
                {
                    'question': "What cloud platforms does your organization primarily use?",
                    'context': 'technology_environment',
                    'auto_populate_options': ['AWS', 'Microsoft Azure', 'Google Cloud', 'Multi-cloud', 'On-premises']
                },
                {
                    'question': "What is your primary development methodology?",
                    'context': 'business_processes',
                    'auto_populate_options': ['Agile/Scrum', 'DevOps/CI-CD', 'Waterfall', 'Hybrid']
                }
            ])
        
        return questions
    
    def _calculate_completeness_score(self, profile_content: str) -> float:
        """Calculate profile completeness score based on required sections"""
        required_sections = [
            'Basic Information', 'Regulatory Environment', 'Risk Profile',
            'Security Maturity', 'Technology Environment', 'Business Context'
        ]
        
        sections_found = 0
        for section in required_sections:
            if section.lower() in profile_content.lower():
                sections_found += 1
        
        return sections_found / len(required_sections)
    
    def _identify_missing_sections(self, profile_content: str) -> list:
        """Identify missing sections in the profile"""
        required_sections = [
            'Basic Information', 'Regulatory Environment', 'Risk Profile',
            'Security Maturity', 'Technology Environment', 'Business Context'
        ]
        
        missing_sections = []
        for section in required_sections:
            if section.lower() not in profile_content.lower():
                missing_sections.append(section)
        
        return missing_sections
    
    def _generate_industry_suggestions(self, search_results: dict, missing_sections: list) -> list:
        """Generate industry-specific suggestions for missing sections"""
        suggestions = []
        
        if 'results' in search_results:
            results = search_results['results']
            
            # Suggest standards for regulatory environment
            if 'Regulatory Environment' in missing_sections and 'standards' in results:
                standards = results['standards'][:3]  # Top 3 standards
                suggestions.append({
                    'section': 'Regulatory Environment',
                    'suggestion': f"Consider including these industry standards: {', '.join([s.get('name', '') for s in standards])}",
                    'auto_populate_content': '\n'.join([f"- **{s.get('name', '')}**: {s.get('description', '')}" for s in standards])
                })
            
            # Suggest frameworks for security maturity
            if 'Security Maturity' in missing_sections and 'frameworks' in results:
                frameworks = results['frameworks'][:2]  # Top 2 frameworks
                suggestions.append({
                    'section': 'Security Maturity',
                    'suggestion': f"Consider these security frameworks: {', '.join([f.get('name', '') for f in frameworks])}",
                    'auto_populate_content': '\n'.join([f"- **{f.get('name', '')}**: {f.get('description', '')}" for f in frameworks])
                })
        
        return suggestions
    
    def _create_process_conversation_tool(self):
        @tool
        def process_conversation(user_input: str, current_context: dict = None) -> str:
            """Process user input through conversation flow with MCP search integration
            
            This tool performs MCP research and returns formatted guidance for your next question.
            
            Args:
                user_input: User's response or input
                current_context: Current conversation context and gathered information
            
            Returns:
                Formatted string with research results and instructions for next question
            """
            if not self.conversation_flow:
                return 'ERROR: Conversation flow manager not initialized'
            
            try:
                # Process user response through conversation flow manager
                flow_result = self.conversation_flow.process_user_response(user_input, current_context)
                next_action = flow_result['next_action']
                
                # Format response as clear instructions for LLM
                if next_action['action_type'] == 'llm_driven_conversation':
                    response = "=== RESEARCH-ENHANCED CONVERSATION GUIDANCE ===\n\n"
                    response += f"Profile Completeness: {int(next_action['completeness_score'] * 100)}%\n"
                    response += f"Missing Sections: {', '.join(next_action['missing_sections'])}\n"
                    response += f"Completed Sections: {', '.join(next_action['gathered_sections'])}\n\n"
                    
                    # Add research results
                    if flow_result['research_results']:
                        response += "=== MCP RESEARCH RESULTS ===\n"
                        for research_type, results in flow_result['research_results'].items():
                            response += f"\n{research_type.upper()}:\n"
                            response += f"{json.dumps(results, indent=2)}\n"
                    
                    # Add auto-populate suggestions
                    if flow_result['auto_populate_suggestions']:
                        response += "\n=== AUTO-POPULATE SUGGESTIONS ===\n"
                        for suggestion in flow_result['auto_populate_suggestions'][:5]:
                            response += f"- {suggestion['suggestion']}: {suggestion.get('description', '')}\n"
                    
                    # Add industry/region context
                    if next_action.get('industry_config'):
                        response += f"\n=== INDUSTRY CONTEXT ===\n"
                        response += f"{json.dumps(next_action['industry_config'], indent=2)}\n"
                    
                    if next_action.get('region_config'):
                        response += f"\n=== REGION CONTEXT ===\n"
                        response += f"{json.dumps(next_action['region_config'], indent=2)}\n"
                    
                    # Clear instruction
                    response += f"\n=== YOUR TASK ===\n"
                    response += f"{next_action['instruction_to_llm']}\n\n"
                    response += "Generate ONE research-enhanced question that incorporates the findings above.\n"
                    response += "Make it specific to their industry, region, and context.\n"
                    response += "Provide options based on the research results when applicable.\n"
                    
                    return response
                
                elif next_action['action_type'] == 'ask_question':
                    # Core information phase - simpler response
                    response = f"Ask about: {next_action['field_name']}\n"
                    if next_action.get('suggested_options'):
                        response += f"Suggested options: {', '.join(next_action['suggested_options'])}\n"
                    return response
                
                elif next_action['action_type'] == 'create_profile':
                    return f"Profile is {int(next_action['completeness_score'] * 100)}% complete. Ready to create profile."
                
                elif next_action['action_type'] == 'update_profile':
                    return f"Profile is {int(next_action['completeness_score'] * 100)}% complete. Call update_profile tool with the complete profile content to save all gathered information."
                
                else:
                    return json.dumps(next_action, indent=2)
                    
            except Exception as e:
                return f'ERROR: {str(e)}'
        return process_conversation
 
   
    def _create_upload_document_tool(self):
        @tool
        def upload_document(profile_id: str, document_name: str, document_content_base64: str) -> dict:
            """Upload a document to S3 for profile context extraction.
            
            Stores the document — no async processing. Use read_document or
            extract_profile_from_documents to read content when needed.
            
            Args:
                profile_id: The profile ID to associate the document with
                document_name: Name of the document file
                document_content_base64: Base64-encoded document content
            
            Returns:
                Dictionary with upload status and document_id
            """
            try:
                import uuid
                document_id = str(uuid.uuid4())
                
                result = self._invoke_lambda('risk-agent-document_manager', {
                    'requestContext': {'http': {'method': 'POST'}},
                    'rawPath': '/upload',
                    'body': json.dumps({
                        'profile_id': profile_id,
                        'document_id': document_id,
                        'file_name': document_name,
                        'file_content': document_content_base64,
                        'file_type': self._get_mime_type(document_name)
                    })
                })
                
                if isinstance(result, dict) and result.get('statusCode') == 200:
                    body = json.loads(result['body']) if isinstance(result.get('body'), str) else result
                    return {
                        'status': 'success',
                        'message': f'Document "{document_name}" uploaded successfully',
                        'document_id': document_id,
                        's3_key': body.get('document_key', '')
                    }
                
                return {
                    'status': 'success',
                    'message': f'Document "{document_name}" uploaded',
                    'document_id': document_id
                }
            except Exception as e:
                return {'status': 'error', 'message': f'Upload failed: {str(e)}'}
        return upload_document

    def _create_read_document_tool(self):
        @tool
        def read_document(profile_id: str, document_name: str = None) -> dict:
            """Read a document's full text content directly from S3.
            
            Downloads from S3 and extracts text from PDF/DOCX/TXT.
            If document_name is not provided, reads the first document found.
            
            Args:
                profile_id: The profile ID
                document_name: Optional filename to read (reads first doc if not specified)
            
            Returns:
                Dictionary with document text content
            """
            try:
                from io import BytesIO
                
                bucket = os.environ.get('DOCUMENTS_BUCKET', 'risk-agent-project-documents-b7e63ea0')
                prefix = f"organization_profiles/{profile_id}/documents/"
                
                s3 = boto3.client('s3')
                response = s3.list_objects_v2(Bucket=bucket, Prefix=prefix, MaxKeys=100)
                objects = response.get('Contents', [])
                
                if not objects:
                    return {'status': 'error', 'message': 'No documents found for this profile'}
                
                # Find requested document or use first one
                target_key = None
                target_name = None
                for obj in objects:
                    fname = obj['Key'].split('/')[-1]
                    if document_name and document_name.lower() in fname.lower():
                        target_key = obj['Key']
                        target_name = fname
                        break
                if not target_key:
                    target_key = objects[0]['Key']
                    target_name = objects[0]['Key'].split('/')[-1]
                
                # Download and extract text
                file_obj = s3.get_object(Bucket=bucket, Key=target_key)
                file_bytes = file_obj['Body'].read()
                ext = target_name.lower().split('.')[-1]
                
                if ext == 'pdf':
                    from PyPDF2 import PdfReader
                    reader = PdfReader(BytesIO(file_bytes))
                    text = '\n\n'.join(page.extract_text() or '' for page in reader.pages)
                elif ext == 'docx':
                    import zipfile
                    import xml.etree.ElementTree as ET
                    with zipfile.ZipFile(BytesIO(file_bytes)) as z:
                        xml_content = z.read('word/document.xml')
                        tree = ET.XML(xml_content)
                        ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
                        text = '\n'.join(
                            ''.join(n.text for n in p.findall('.//w:t', ns) if n.text)
                            for p in tree.findall('.//w:p', ns)
                        )
                else:
                    text = file_bytes.decode('utf-8', errors='replace')
                
                return {
                    'status': 'success',
                    'document_name': target_name,
                    'text': text,
                    'character_count': len(text)
                }
            except Exception as e:
                return {'status': 'error', 'message': f'Read failed: {str(e)}'}
        return read_document

    def _create_extract_profile_from_documents_tool(self):
        @tool
        def extract_profile_from_documents(profile_id: str, fields_to_extract: list) -> dict:
            """Read all uploaded documents and extract specified profile fields in one pass.
            
            Pulls document text into context and extracts all requested fields.
            
            Args:
                profile_id: The profile ID
                fields_to_extract: List of field names to extract
            
            Returns:
                Dictionary with combined document text for extraction
            """
            try:
                from io import BytesIO
                
                bucket = os.environ.get('DOCUMENTS_BUCKET', 'risk-agent-project-documents-b7e63ea0')
                prefix = f"organization_profiles/{profile_id}/documents/"
                
                s3 = boto3.client('s3')
                response = s3.list_objects_v2(Bucket=bucket, Prefix=prefix, MaxKeys=100)
                objects = response.get('Contents', [])
                
                if not objects:
                    return {'status': 'no_documents', 'message': 'No documents uploaded yet.'}
                
                all_text = []
                for obj in objects:
                    fname = obj['Key'].split('/')[-1]
                    try:
                        file_obj = s3.get_object(Bucket=bucket, Key=obj['Key'])
                        file_bytes = file_obj['Body'].read()
                        ext = fname.lower().split('.')[-1]
                        
                        if ext == 'pdf':
                            from PyPDF2 import PdfReader
                            reader = PdfReader(BytesIO(file_bytes))
                            text = '\n\n'.join(page.extract_text() or '' for page in reader.pages)
                        elif ext == 'docx':
                            import zipfile
                            import xml.etree.ElementTree as ET
                            with zipfile.ZipFile(BytesIO(file_bytes)) as z:
                                xml_content = z.read('word/document.xml')
                                tree = ET.XML(xml_content)
                                ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
                                text = '\n'.join(
                                    ''.join(n.text for n in p.findall('.//w:t', ns) if n.text)
                                    for p in tree.findall('.//w:p', ns)
                                )
                        else:
                            text = file_bytes.decode('utf-8', errors='replace')
                        
                        all_text.append(f"=== Document: {fname} ===\n{text}")
                    except Exception as e:
                        all_text.append(f"=== Document: {fname} === [ERROR: {str(e)}]")
                
                combined_text = '\n\n'.join(all_text)
                if len(combined_text) > 150000:
                    combined_text = combined_text[:150000] + "\n\n[... truncated]"
                
                return {
                    'status': 'success',
                    'document_count': len(all_text),
                    'fields_requested': fields_to_extract,
                    'text': combined_text,
                    'instruction': 'Extract the requested fields from the document text above. For each field provide: value, confidence (0-1), and source (document name + section).'
                }
            except Exception as e:
                return {'status': 'error', 'message': f'Extraction failed: {str(e)}'}
        return extract_profile_from_documents
    
    def _get_mime_type(self, filename):
        """Get MIME type from filename"""
        import mimetypes
        mime_type, _ = mimetypes.guess_type(filename)
        return mime_type or 'application/octet-stream'
