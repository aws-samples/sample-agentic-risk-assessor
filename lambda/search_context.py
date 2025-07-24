import json
import os
import re
import boto3
import logging
import requests
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from urllib.parse import quote_plus

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

# Configuration from environment variables
MCP_SEARCH_ENDPOINT = os.environ.get('MCP_SEARCH_ENDPOINT')
MCP_API_KEY = os.environ.get('MCP_API_KEY')
SEARCH_RESULTS_BUCKET = os.environ.get('SEARCH_RESULTS_BUCKET')
SEARCH_CACHE_TABLE = os.environ.get('SEARCH_CACHE_TABLE')
MAX_SEARCH_RESULTS = int(os.environ.get('MAX_SEARCH_RESULTS', '10'))
CACHE_TTL_HOURS = int(os.environ.get('CACHE_TTL_HOURS', '24'))

class SearchContextHandler:
    """Handler for MCP internet search integration for organization profile context"""
    
    def __init__(self):
        self.headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'RiskAgent-OrganizationProfile/1.0'
        }
        if MCP_API_KEY:
            self.headers['Authorization'] = f'Bearer {MCP_API_KEY}'
    
    def search_industry_standards(self, industry: str, region: str = None) -> Dict[str, Any]:
        """Search for industry-specific standards and frameworks"""
        try:
            query_parts = [f"{industry} industry standards", "compliance frameworks"]
            if region:
                query_parts.append(f"{region} regulations")
            
            query = " ".join(query_parts)
            
            # Check cache first
            cached_result = self._get_cached_search(query, "industry_standards")
            if cached_result:
                logger.info(f"Returning cached industry standards for {industry}")
                return cached_result
            
            # Perform search
            search_results = self._perform_search(query, search_type="industry_standards")
            
            # Process and structure results
            structured_results = {
                'industry': industry,
                'region': region,
                'standards': [],
                'frameworks': [],
                'best_practices': [],
                'sources': []
            }
            
            for result in search_results:
                if any(keyword in result.get('title', '').lower() for keyword in ['iso', 'nist', 'sox', 'pci', 'hipaa']):
                    structured_results['standards'].append({
                        'name': result.get('title', ''),
                        'description': result.get('snippet', ''),
                        'url': result.get('url', ''),
                        'relevance_score': result.get('score', 0)
                    })
                elif any(keyword in result.get('title', '').lower() for keyword in ['framework', 'guideline', 'control']):
                    structured_results['frameworks'].append({
                        'name': result.get('title', ''),
                        'description': result.get('snippet', ''),
                        'url': result.get('url', ''),
                        'relevance_score': result.get('score', 0)
                    })
                else:
                    structured_results['best_practices'].append({
                        'title': result.get('title', ''),
                        'description': result.get('snippet', ''),
                        'url': result.get('url', ''),
                        'relevance_score': result.get('score', 0)
                    })
                
                structured_results['sources'].append(result.get('url', ''))
            
            # Cache the results
            self._cache_search_results(query, "industry_standards", structured_results)
            
            logger.info(f"Found {len(structured_results['standards'])} standards and {len(structured_results['frameworks'])} frameworks for {industry}")
            return structured_results
            
        except Exception as e:
            logger.error(f"Error searching industry standards for {industry}: {str(e)}")
            return self._get_fallback_industry_standards(industry)
    
    def search_regulatory_requirements(self, industry: str, region: str, organization_size: str = None) -> Dict[str, Any]:
        """Search for regulatory requirements specific to industry and region"""
        try:
            query_parts = [f"{industry} regulatory requirements", f"{region} compliance"]
            if organization_size:
                query_parts.append(f"{organization_size} company regulations")
            
            query = " ".join(query_parts)
            
            # Check cache first
            cached_result = self._get_cached_search(query, "regulatory_requirements")
            if cached_result:
                logger.info(f"Returning cached regulatory requirements for {industry} in {region}")
                return cached_result
            
            # Perform search
            search_results = self._perform_search(query, search_type="regulatory_requirements")
            
            # Process and structure results
            structured_results = {
                'industry': industry,
                'region': region,
                'organization_size': organization_size,
                'mandatory_regulations': [],
                'optional_frameworks': [],
                'data_protection_laws': [],
                'industry_specific_rules': [],
                'sources': []
            }
            
            for result in search_results:
                title_lower = result.get('title', '').lower()
                snippet_lower = result.get('snippet', '').lower()
                
                if any(keyword in title_lower or keyword in snippet_lower for keyword in ['gdpr', 'ccpa', 'privacy', 'data protection']):
                    structured_results['data_protection_laws'].append({
                        'name': result.get('title', ''),
                        'description': result.get('snippet', ''),
                        'url': result.get('url', ''),
                        'mandatory': self._is_mandatory_regulation(result),
                        'relevance_score': result.get('score', 0)
                    })
                elif any(keyword in title_lower for keyword in ['law', 'act', 'regulation', 'mandatory', 'required']):
                    structured_results['mandatory_regulations'].append({
                        'name': result.get('title', ''),
                        'description': result.get('snippet', ''),
                        'url': result.get('url', ''),
                        'enforcement_agency': self._extract_enforcement_agency(result),
                        'relevance_score': result.get('score', 0)
                    })
                elif any(keyword in title_lower for keyword in [industry.lower(), 'sector', 'vertical']):
                    structured_results['industry_specific_rules'].append({
                        'name': result.get('title', ''),
                        'description': result.get('snippet', ''),
                        'url': result.get('url', ''),
                        'applicability': self._determine_applicability(result, organization_size),
                        'relevance_score': result.get('score', 0)
                    })
                else:
                    structured_results['optional_frameworks'].append({
                        'name': result.get('title', ''),
                        'description': result.get('snippet', ''),
                        'url': result.get('url', ''),
                        'relevance_score': result.get('score', 0)
                    })
                
                structured_results['sources'].append(result.get('url', ''))
            
            # Cache the results
            self._cache_search_results(query, "regulatory_requirements", structured_results)
            
            logger.info(f"Found {len(structured_results['mandatory_regulations'])} mandatory regulations for {industry} in {region}")
            return structured_results
            
        except Exception as e:
            logger.error(f"Error searching regulatory requirements for {industry} in {region}: {str(e)}")
            return self._get_fallback_regulatory_requirements(industry, region)
    
    def search_security_best_practices(self, industry: str, technology_stack: List[str] = None) -> Dict[str, Any]:
        """Search for security best practices for specific industry and technology stack"""
        try:
            query_parts = [f"{industry} security best practices", "cybersecurity guidelines"]
            if technology_stack:
                query_parts.extend([f"{tech} security" for tech in technology_stack[:3]])  # Limit to top 3
            
            query = " ".join(query_parts)
            
            # Check cache first
            cached_result = self._get_cached_search(query, "security_best_practices")
            if cached_result:
                logger.info(f"Returning cached security best practices for {industry}")
                return cached_result
            
            # Perform search
            search_results = self._perform_search(query, search_type="security_best_practices")
            
            # Process and structure results
            structured_results = {
                'industry': industry,
                'technology_stack': technology_stack,
                'security_controls': [],
                'implementation_guides': [],
                'threat_intelligence': [],
                'compliance_mappings': [],
                'sources': []
            }
            
            for result in search_results:
                title_lower = result.get('title', '').lower()
                snippet_lower = result.get('snippet', '').lower()
                
                if any(keyword in title_lower or keyword in snippet_lower for keyword in ['control', 'safeguard', 'protection']):
                    structured_results['security_controls'].append({
                        'name': result.get('title', ''),
                        'description': result.get('snippet', ''),
                        'url': result.get('url', ''),
                        'control_type': self._classify_control_type(result),
                        'relevance_score': result.get('score', 0)
                    })
                elif any(keyword in title_lower for keyword in ['implementation', 'guide', 'how to', 'setup']):
                    structured_results['implementation_guides'].append({
                        'title': result.get('title', ''),
                        'description': result.get('snippet', ''),
                        'url': result.get('url', ''),
                        'difficulty_level': self._assess_difficulty_level(result),
                        'relevance_score': result.get('score', 0)
                    })
                elif any(keyword in title_lower or keyword in snippet_lower for keyword in ['threat', 'attack', 'vulnerability']):
                    structured_results['threat_intelligence'].append({
                        'title': result.get('title', ''),
                        'description': result.get('snippet', ''),
                        'url': result.get('url', ''),
                        'threat_level': self._assess_threat_level(result),
                        'relevance_score': result.get('score', 0)
                    })
                else:
                    structured_results['compliance_mappings'].append({
                        'title': result.get('title', ''),
                        'description': result.get('snippet', ''),
                        'url': result.get('url', ''),
                        'relevance_score': result.get('score', 0)
                    })
                
                structured_results['sources'].append(result.get('url', ''))
            
            # Cache the results
            self._cache_search_results(query, "security_best_practices", structured_results)
            
            logger.info(f"Found {len(structured_results['security_controls'])} security controls for {industry}")
            return structured_results
            
        except Exception as e:
            logger.error(f"Error searching security best practices for {industry}: {str(e)}")
            return self._get_fallback_security_practices(industry)
    
    def _perform_search(self, query: str, search_type: str) -> List[Dict[str, Any]]:
        """Perform the actual internet search via MCP endpoint"""
        try:
            if not MCP_SEARCH_ENDPOINT or MCP_SEARCH_ENDPOINT.strip() == '':
                logger.warning("MCP_SEARCH_ENDPOINT not configured, using fallback")
                return []
            
            # Prepare search request
            search_payload = {
                'query': query,
                'max_results': MAX_SEARCH_RESULTS,
                'search_type': search_type,
                'filters': {
                    'language': 'en',
                    'content_type': ['article', 'guide', 'documentation'],
                    'exclude_domains': ['wikipedia.org']  # Exclude for more authoritative sources
                }
            }
            
            logger.info(f"Performing MCP search for: {query}")
            
            # Make the search request
            response = requests.post(
                MCP_SEARCH_ENDPOINT,
                headers=self.headers,
                json=search_payload,
                timeout=30
            )
            
            if response.status_code == 200:
                search_data = response.json()
                results = search_data.get('results', [])
                
                # Sanitize external search results to prevent XSS and indirect prompt injection
                results = [self._sanitize_search_result(r) for r in results]
                
                # Save raw search results to S3 for debugging/analysis
                self._save_search_results_to_s3(query, search_type, search_data)
                
                return results
            else:
                logger.error(f"MCP search failed with status {response.status_code}: {response.text}")
                return []
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error during MCP search: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error during MCP search: {str(e)}")
            return []
    
    def _sanitize_search_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize external search result to prevent XSS and indirect prompt injection."""
        MAX_FIELD_LENGTH = 5000
        
        def clean(text: str) -> str:
            if not isinstance(text, str):
                return ""
            # Strip HTML/script tags
            text = re.sub(r'<[^>]+>', '', text)
            # Truncate
            if len(text) > MAX_FIELD_LENGTH:
                text = text[:MAX_FIELD_LENGTH] + "...[TRUNCATED]"
            return text
        
        return {
            'title': clean(result.get('title', '')),
            'snippet': f"[EXTERNAL DATA] {clean(result.get('snippet', ''))} [/EXTERNAL DATA]",
            'url': result.get('url', '')[:500],
            'score': result.get('score', 0),
        }
    
    def _get_cached_search(self, query: str, search_type: str) -> Optional[Dict[str, Any]]:
        """Check if search results are cached and still valid"""
        try:
            if not SEARCH_CACHE_TABLE:
                return None
            
            table = dynamodb.Table(SEARCH_CACHE_TABLE)
            cache_key = f"{search_type}#{hash(query)}"
            
            response = table.get_item(Key={'cache_key': cache_key})
            
            if 'Item' in response:
                item = response['Item']
                cached_time = datetime.fromisoformat(item['cached_at'])
                current_time = datetime.now()
                
                # Check if cache is still valid
                hours_diff = (current_time - cached_time).total_seconds() / 3600
                if hours_diff < CACHE_TTL_HOURS:
                    return json.loads(item['results'])
            
            return None
            
        except Exception as e:
            logger.error(f"Error checking search cache: {str(e)}")
            return None
    
    def _cache_search_results(self, query: str, search_type: str, results: Dict[str, Any]):
        """Cache search results for future use"""
        try:
            if not SEARCH_CACHE_TABLE:
                return
            
            table = dynamodb.Table(SEARCH_CACHE_TABLE)
            cache_key = f"{search_type}#{hash(query)}"
            
            table.put_item(
                Item={
                    'cache_key': cache_key,
                    'query': query,
                    'search_type': search_type,
                    'results': json.dumps(results),
                    'cached_at': datetime.now().isoformat(),
                    'ttl': int((datetime.now().timestamp() + (CACHE_TTL_HOURS * 3600)))
                }
            )
            
        except Exception as e:
            logger.error(f"Error caching search results: {str(e)}")
    
    def _save_search_results_to_s3(self, query: str, search_type: str, results: Dict[str, Any]):
        """Save raw search results to S3 for analysis and debugging"""
        try:
            if not SEARCH_RESULTS_BUCKET:
                return
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            key = f"search-results/{search_type}/{timestamp}_{uuid.uuid4().hex[:8]}.json"
            
            search_metadata = {
                'query': query,
                'search_type': search_type,
                'timestamp': datetime.now().isoformat(),
                'results': results
            }
            
            s3.put_object(
                Bucket=SEARCH_RESULTS_BUCKET,
                Key=key,
                Body=json.dumps(search_metadata, indent=2),
                ContentType='application/json'
            )
            
        except Exception as e:
            logger.error(f"Error saving search results to S3: {str(e)}")
    
    # Helper methods for result processing
    def _is_mandatory_regulation(self, result: Dict[str, Any]) -> bool:
        """Determine if a regulation is mandatory based on content"""
        content = f"{result.get('title', '')} {result.get('snippet', '')}".lower()
        mandatory_keywords = ['mandatory', 'required', 'must', 'shall', 'law', 'act', 'regulation']
        return any(keyword in content for keyword in mandatory_keywords)
    
    def _extract_enforcement_agency(self, result: Dict[str, Any]) -> str:
        """Extract enforcement agency from search result"""
        content = f"{result.get('title', '')} {result.get('snippet', '')}".lower()
        agencies = {
            'sec': 'Securities and Exchange Commission',
            'fda': 'Food and Drug Administration',
            'ftc': 'Federal Trade Commission',
            'dhs': 'Department of Homeland Security',
            'nist': 'National Institute of Standards and Technology'
        }
        
        for abbr, full_name in agencies.items():
            if abbr in content:
                return full_name
        
        return 'Unknown'
    
    def _determine_applicability(self, result: Dict[str, Any], organization_size: str) -> str:
        """Determine regulation applicability based on organization size"""
        if not organization_size:
            return 'General'
        
        content = f"{result.get('title', '')} {result.get('snippet', '')}".lower()
        size_lower = organization_size.lower()
        
        if 'small' in size_lower and any(keyword in content for keyword in ['small business', 'startup', 'sme']):
            return 'Small Business Specific'
        elif 'large' in size_lower and any(keyword in content for keyword in ['enterprise', 'large corporation']):
            return 'Enterprise Specific'
        else:
            return 'General'
    
    def _classify_control_type(self, result: Dict[str, Any]) -> str:
        """Classify the type of security control"""
        content = f"{result.get('title', '')} {result.get('snippet', '')}".lower()
        
        if any(keyword in content for keyword in ['access', 'authentication', 'authorization']):
            return 'Access Control'
        elif any(keyword in content for keyword in ['encryption', 'crypto', 'key management']):
            return 'Cryptographic'
        elif any(keyword in content for keyword in ['network', 'firewall', 'intrusion']):
            return 'Network Security'
        elif any(keyword in content for keyword in ['audit', 'log', 'monitoring']):
            return 'Audit and Accountability'
        else:
            return 'General'
    
    def _assess_difficulty_level(self, result: Dict[str, Any]) -> str:
        """Assess implementation difficulty level"""
        content = f"{result.get('title', '')} {result.get('snippet', '')}".lower()
        
        if any(keyword in content for keyword in ['easy', 'simple', 'basic', 'beginner']):
            return 'Easy'
        elif any(keyword in content for keyword in ['advanced', 'complex', 'expert', 'difficult']):
            return 'Advanced'
        else:
            return 'Intermediate'
    
    def _assess_threat_level(self, result: Dict[str, Any]) -> str:
        """Assess threat level from content"""
        content = f"{result.get('title', '')} {result.get('snippet', '')}".lower()
        
        if any(keyword in content for keyword in ['critical', 'severe', 'high risk']):
            return 'High'
        elif any(keyword in content for keyword in ['moderate', 'medium']):
            return 'Medium'
        else:
            return 'Low'
    
    # Fallback methods when search is unavailable
    def _get_fallback_industry_standards(self, industry: str) -> Dict[str, Any]:
        """Provide fallback industry standards when search is unavailable"""
        fallback_standards = {
            'financial': ['SOX', 'PCI DSS', 'FFIEC', 'GLBA'],
            'healthcare': ['HIPAA', 'HITECH', 'FDA 21 CFR Part 11'],
            'technology': ['ISO 27001', 'NIST Cybersecurity Framework', 'SOC 2'],
            'manufacturing': ['ISO 27001', 'NIST 800-171', 'IEC 62443'],
            'retail': ['PCI DSS', 'CCPA', 'GDPR'],
            'government': ['FISMA', 'NIST 800-53', 'FedRAMP']
        }
        
        industry_lower = industry.lower()
        standards = []
        
        for key, values in fallback_standards.items():
            if key in industry_lower:
                standards = values
                break
        
        if not standards:
            standards = ['ISO 27001', 'NIST Cybersecurity Framework']  # Default standards
        
        return {
            'industry': industry,
            'region': None,
            'standards': [{'name': std, 'description': f'Industry standard: {std}', 'url': '', 'relevance_score': 0.8} for std in standards],
            'frameworks': [],
            'best_practices': [],
            'sources': ['Fallback data - MCP search unavailable']
        }
    
    def _get_fallback_regulatory_requirements(self, industry: str, region: str) -> Dict[str, Any]:
        """Provide fallback regulatory requirements when search is unavailable"""
        return {
            'industry': industry,
            'region': region,
            'organization_size': None,
            'mandatory_regulations': [
                {'name': 'General Data Protection', 'description': 'Basic data protection requirements', 'url': '', 'mandatory': True, 'relevance_score': 0.7}
            ],
            'optional_frameworks': [],
            'data_protection_laws': [],
            'industry_specific_rules': [],
            'sources': ['Fallback data - MCP search unavailable']
        }
    
    def _get_fallback_security_practices(self, industry: str) -> Dict[str, Any]:
        """Provide fallback security practices when search is unavailable"""
        return {
            'industry': industry,
            'technology_stack': None,
            'security_controls': [
                {'name': 'Access Control', 'description': 'Implement proper access controls', 'url': '', 'control_type': 'Access Control', 'relevance_score': 0.8},
                {'name': 'Encryption', 'description': 'Encrypt data at rest and in transit', 'url': '', 'control_type': 'Cryptographic', 'relevance_score': 0.8}
            ],
            'implementation_guides': [],
            'threat_intelligence': [],
            'compliance_mappings': [],
            'sources': ['Fallback data - MCP search unavailable']
        }


def lambda_handler(event, context):
    """Main Lambda handler for search context operations"""
    
    # CORS headers
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
        'Access-Control-Allow-Methods': 'OPTIONS,POST'
    }
    
    try:
        # Handle OPTIONS request for CORS
        if event.get('requestContext', {}).get('http', {}).get('method') == 'OPTIONS':
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps({})
            }
        
        # Parse request body
        if 'body' not in event:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'Request body is required'})
            }
        
        body = json.loads(event['body'])
        search_type = body.get('search_type')
        
        if not search_type:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'search_type is required'})
            }
        
        # Initialize search handler
        search_handler = SearchContextHandler()
        
        # Route to appropriate search method
        if search_type == 'industry_standards':
            industry = body.get('industry')
            region = body.get('region')
            
            if not industry:
                return {
                    'statusCode': 400,
                    'headers': headers,
                    'body': json.dumps({'error': 'industry is required for industry_standards search'})
                }
            
            results = search_handler.search_industry_standards(industry, region)
            
        elif search_type == 'regulatory_requirements':
            industry = body.get('industry')
            region = body.get('region')
            organization_size = body.get('organization_size')
            
            if not industry or not region:
                return {
                    'statusCode': 400,
                    'headers': headers,
                    'body': json.dumps({'error': 'industry and region are required for regulatory_requirements search'})
                }
            
            results = search_handler.search_regulatory_requirements(industry, region, organization_size)
            
        elif search_type == 'security_best_practices':
            industry = body.get('industry')
            technology_stack = body.get('technology_stack', [])
            
            if not industry:
                return {
                    'statusCode': 400,
                    'headers': headers,
                    'body': json.dumps({'error': 'industry is required for security_best_practices search'})
                }
            
            results = search_handler.search_security_best_practices(industry, technology_stack)
            
        else:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': f'Unsupported search_type: {search_type}'})
            }
        
        # Return successful response
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({
                'search_type': search_type,
                'results': results,
                'timestamp': datetime.now().isoformat()
            })
        }
        
    except json.JSONDecodeError:
        return {
            'statusCode': 400,
            'headers': headers,
            'body': json.dumps({'error': 'Invalid JSON in request body'})
        }
    except Exception as e:
        logger.error(f"Error in search_context handler: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': f'Internal server error: {str(e)}'})
        }