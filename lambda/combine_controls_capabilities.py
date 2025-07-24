import json
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    """Combine framework controls with service capabilities into structured prompt"""
    try:
        service_name = event.get('service')
        framework = event.get('framework')
        framework_controls = event.get('framework_controls', '')
        service_capabilities = event.get('service_capabilities', [])
        
        logger.info(f"Combining controls and capabilities for {service_name} with {framework}")
        
        # Create enhanced prompt combining RAG controls with MCP capabilities
        enhanced_prompt = f"""
Create comprehensive mappings between {framework} controls and {service_name} capabilities.

Framework Controls (from authoritative source):
{framework_controls}

Current Service Capabilities (from AWS documentation):
{json.dumps(service_capabilities, indent=2)}

For each control mapping, provide:
1. CONTROL MAPPING: Control ID, requirement, specific capabilities, implementation approach
2. VERIFICATION CRITERIA: Automated checks, measurable thresholds, audit evidence
3. RISK ASSESSMENT: Criticality score (1-10), complexity, cost category
4. IMPLEMENTATION LEVELS: Basic → Managed → Optimized → Predictive
5. DEPENDENCIES: Prerequisites, enablers, conflicts
6. VALIDATION METHODS: CLI commands, monitoring setup, validation procedures

Return as structured JSON with applicable_controls and non_applicable_controls arrays.
Each control should include: id, category, priority, description, and implementation guidance.
"""
        
        logger.info(f"Combined controls and capabilities into prompt, length: {len(enhanced_prompt)}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'service': service_name,
                'framework': framework,
                'prompt': enhanced_prompt
            })
        }
        
    except Exception as e:
        logger.error(f"Error combining controls and capabilities: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }