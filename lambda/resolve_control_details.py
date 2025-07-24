import json
import boto3
import logging
import os
from botocore.config import Config

logger = logging.getLogger()
logger.setLevel(logging.INFO)

KNOWLEDGE_BASE_ID = os.environ.get('KNOWLEDGE_BASE_ID')
BEDROCK_MODEL_ID = os.environ.get('BEDROCK_MODEL_ID', 'us.anthropic.claude-sonnet-4-6')

bedrock_agent = boto3.client(
    'bedrock-agent-runtime',
    region_name=os.environ.get('AWS_REGION', 'us-east-1'),
    config=Config(read_timeout=120, connect_timeout=10, retries={'max_attempts': 0})
)

FRAMEWORK_PREFIXES = {
    'nist': 'nist-800-53/',
    'iso27001': 'iso-27001/',
    'soc2': 'sox/',
    'pci_dss': 'pci-dss/',
    'cis': 'cis-controls/',
    'apra_cps234': 'cps234/',
    'ci_profile': 'ci-profile/',
    'cri': 'cri/'
}

# Framework-specific retrieval queries
FRAMEWORK_QUERIES = {
    'nist': "NIST 800-53 {control_id}",
    'cri': "CRI Profile {control_id} Control Name Diagnostic Statement",
    'pci_dss': "PCI DSS requirement {control_id} name description",
    'cis': "CIS safeguard {control_id} title description",
    'apra_cps234': "CPS 234 {control_id} requirement",
    'iso27001': "ISO 27001 {control_id} control name description",
    'soc2': "SOC 2 {control_id} criteria description",
}

# Framework-specific generation prompts
FRAMEWORK_PROMPTS = {
    'nist': """Based on the search results: $search_results$

Extract the following for NIST 800-53 control {control_id}. Return ONLY valid JSON:

{{
  "control_name": "the official NIST control name/title (e.g. 'Access Enforcement', 'Audit Events')",
  "diagnostic_statement": "the full control description text starting with the control requirement"
}}

Use the exact text from the NIST 800-53 document. Do not paraphrase.""",

    'cri': """Based on the search results: $search_results$

Extract the following for CRI Profile control {control_id}. Return ONLY valid JSON:

{{
  "control_name": "the Control Name from the CRI Profile (e.g. 'GOVERN / Risk Management Strategy / Risk Management Objectives Agreement')",
  "diagnostic_statement": "the full Diagnostic Statement text for this control"
}}

Use the exact text from the CRI Profile source documents.""",

    'pci_dss': """Based on the search results: $search_results$

Extract the following for PCI DSS requirement {control_id}. Return ONLY valid JSON:

{{
  "control_name": "the requirement title",
  "diagnostic_statement": "the full requirement description and testing procedures"
}}

Use the exact text from the PCI DSS document.""",

    'cis': """Based on the search results: $search_results$

Extract the following for CIS Controls safeguard {control_id}. Return ONLY valid JSON:

{{
  "control_name": "the safeguard title",
  "diagnostic_statement": "the full safeguard description"
}}

Use the exact text from the CIS Controls document.""",
}

# Default for frameworks without specific prompts
DEFAULT_QUERY = "{control_id} control name requirement"
DEFAULT_PROMPT = """Based on the search results: $search_results$

Extract the following for control {control_id}. Return ONLY valid JSON:

{{
  "control_name": "the official name or title of this control",
  "diagnostic_statement": "the full requirement or description text for this control"
}}

Use the exact text from the source documents. Do not paraphrase."""


def get_model_arn():
    region = os.environ.get('AWS_REGION', 'us-east-1')
    if BEDROCK_MODEL_ID.startswith(('us.', 'eu.', 'global.', 'ap.')):
        account_id = boto3.client('sts').get_caller_identity()['Account']
        return f"arn:aws:bedrock:{region}:{account_id}:inference-profile/{BEDROCK_MODEL_ID}"
    return f"arn:aws:bedrock:{region}::foundation-model/{BEDROCK_MODEL_ID}"


def get_framework_filter(framework):
    prefix = FRAMEWORK_PREFIXES.get(framework.lower())
    if not prefix:
        return None
    return {"stringContains": {"key": "x-amz-bedrock-kb-source-uri", "value": prefix}}


def lambda_handler(event, context):
    """Resolve control details from Knowledge Base for a single control ID, filtered by framework."""
    control_id = event.get('control_id')
    framework = event.get('framework', '').lower()

    logger.info(f"Resolving details for control_id={control_id}, framework={framework}")

    if not control_id or not KNOWLEDGE_BASE_ID:
        return {'statusCode': 200, 'body': json.dumps({'control_id': control_id, 'control_name': '', 'diagnostic_statement': ''})}

    try:
        model_arn = get_model_arn()
        retrieval_filter = get_framework_filter(framework)

        retrieval_config = {'vectorSearchConfiguration': {'numberOfResults': 5, 'overrideSearchType': 'HYBRID'}}
        if retrieval_filter:
            retrieval_config['vectorSearchConfiguration']['filter'] = retrieval_filter

        query = FRAMEWORK_QUERIES.get(framework, DEFAULT_QUERY).format(control_id=control_id)
        prompt = (FRAMEWORK_PROMPTS.get(framework, DEFAULT_PROMPT)).format(control_id=control_id)

        response = bedrock_agent.retrieve_and_generate(
            input={'text': query},
            retrieveAndGenerateConfiguration={
                'type': 'KNOWLEDGE_BASE',
                'knowledgeBaseConfiguration': {
                    'knowledgeBaseId': KNOWLEDGE_BASE_ID,
                    'modelArn': model_arn,
                    'retrievalConfiguration': retrieval_config,
                    'generationConfiguration': {
                        'promptTemplate': {'textPromptTemplate': prompt},
                        'inferenceConfig': {'textInferenceConfig': {'maxTokens': 1024}}
                    }
                }
            }
        )

        result_text = response.get('output', {}).get('text', '')
        logger.info(f"RAG response for {control_id}: {result_text[:200]}")

        control_name = ''
        diagnostic_statement = ''

        text = result_text.strip()
        if text.startswith('```json'): text = text[7:]
        elif text.startswith('```'): text = text[3:]
        if text.endswith('```'): text = text[:-3]
        text = text.strip()

        if '{' in text:
            try:
                parsed = json.loads(text[text.find('{'):text.rfind('}') + 1])
                control_name = parsed.get('control_name', '')
                diagnostic_statement = parsed.get('diagnostic_statement', '')
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse JSON for {control_id}: {e}")

        logger.info(f"Resolved {control_id}: name='{control_name[:60]}', statement='{diagnostic_statement[:80]}'")

        return {'statusCode': 200, 'body': json.dumps({'control_id': control_id, 'control_name': control_name, 'diagnostic_statement': diagnostic_statement})}

    except Exception as e:
        logger.error(f"Error resolving control details for {control_id}: {str(e)}")
        return {'statusCode': 200, 'body': json.dumps({'control_id': control_id, 'control_name': '', 'diagnostic_statement': ''})}
