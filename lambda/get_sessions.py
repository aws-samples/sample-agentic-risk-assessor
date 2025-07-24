import json
import boto3
import os
from datetime import datetime
from boto3.dynamodb.conditions import Key, Attr

def lambda_handler(event, context):
    """Get user sessions from DynamoDB"""
    try:
        # Handle OPTIONS requests
        if event.get('requestContext', {}).get('http', {}).get('method') == 'OPTIONS':
            return {
                'statusCode': 200,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': 'accept,authorization,content-type,origin,x-amz-date,x-amz-security-token,x-api-key',
                    'Access-Control-Allow-Methods': 'GET,OPTIONS'
                },
                'body': json.dumps({})
            }
        
        # Extract user_id from JWT token (API Gateway v2 HTTP API format)
        user_id = event.get('requestContext', {}).get('authorizer', {}).get('jwt', {}).get('claims', {}).get('sub')
        print(f"DEBUG: JWT user_id extracted: '{user_id}'")
        if not user_id:
            return {
                'statusCode': 401,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({'error': 'Unauthorized'})
            }
        
        # Get DynamoDB table
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table(os.environ.get('SESSIONS_TABLE', 'Sessions'))
        
        # Scan sessions for this user (since we need all agents)
        all_items = []
        scan_kwargs = {
            'FilterExpression': Attr('user_id').eq(user_id) & Attr('IsActive').eq(True)
        }
        
        while True:
            response = table.scan(**scan_kwargs)
            all_items.extend(response.get('Items', []))
            if 'LastEvaluatedKey' not in response:
                break
            scan_kwargs['ExclusiveStartKey'] = response['LastEvaluatedKey']
        
        print(f"DynamoDB total items found: {len(all_items)}")
        
        sessions = []
        session_groups = {}
        
        # Group messages by session_id only (FIXED)
        message_count = 0
        for item in all_items:
            # Handle DynamoDB nested structure for record_type
            record_type = item.get('record_type')
            if isinstance(record_type, dict) and 'S' in record_type:
                record_type = record_type['S']
            
            if record_type == 'message':
                message_count += 1
                # Extract fields with DynamoDB format handling
                session_id = item.get('session_id', {})
                if isinstance(session_id, dict) and 'S' in session_id:
                    session_id = session_id['S']
                
                agent_id = item.get('agent_id', {})
                if isinstance(agent_id, dict) and 'S' in agent_id:
                    agent_id = agent_id['S']
                
                original_agent_id = item.get('original_agent_id', {})
                if isinstance(original_agent_id, dict) and 'S' in original_agent_id:
                    original_agent_id = original_agent_id['S']
                else:
                    original_agent_id = agent_id
                
                # FIXED: Group by session_id only
                session_key = session_id
                
                if session_key not in session_groups:
                    session_groups[session_key] = {
                        'session_id': session_id,
                        'primary_agent': original_agent_id,
                        'participating_agents': [],
                        'messages': [],
                        'last_updated': 0
                    }
                    print(f"DEBUG: Created session group for {session_id} with primary agent: {original_agent_id}")
                
                # Track agent participation
                if agent_id not in session_groups[session_key]['participating_agents']:
                    session_groups[session_key]['participating_agents'].append(agent_id)
                
                # Parse message content from the data field
                data = item.get('data', {})
                
                # Handle DynamoDB nested structure
                if 'M' in data:
                    data = data['M']
                    message = data.get('message', {})
                    if 'M' in message:
                        message = message['M']
                else:
                    message = data.get('message', {})
                
                # Extract role and content from the message structure
                role = message.get('role', {}).get('S', 'user') if isinstance(message.get('role'), dict) else message.get('role', 'user')
                content_blocks = message.get('content', [])
                
                # Handle DynamoDB list structure
                if isinstance(content_blocks, dict) and 'L' in content_blocks:
                    content_blocks = content_blocks['L']
                
                # Extract text from content blocks
                content_text = ''
                if isinstance(content_blocks, list) and len(content_blocks) > 0:
                    first_block = content_blocks[0]
                    if isinstance(first_block, dict) and 'M' in first_block:
                        text_field = first_block['M'].get('text', {})
                        content_text = text_field.get('S', '') if isinstance(text_field, dict) else str(text_field)
                    else:
                        content_text = first_block.get('text', '')
                elif isinstance(content_blocks, str):
                    content_text = content_blocks
                
                # Convert Decimal to int for JSON serialization
                message_id = item.get('message_id', {})
                if isinstance(message_id, dict) and 'N' in message_id:
                    try:
                        message_id = int(message_id['N'])
                    except (ValueError, TypeError):
                        message_id = 0
                else:
                    try:
                        message_id = int(message_id)
                    except (ValueError, TypeError):
                        message_id = 0
                    
                session_groups[session_key]['messages'].append({
                    'role': role,
                    'content': content_text,
                    'message_id': message_id,
                    'agent_id': agent_id  # Track which agent handled this message
                })
                
                # Update timestamp - convert ISO string to Unix timestamp
                timestamp_field = item.get('timestamp', {})
                if isinstance(timestamp_field, dict) and 'S' in timestamp_field:
                    timestamp_str = timestamp_field['S']
                else:
                    timestamp_str = str(timestamp_field) if timestamp_field else None
                
                if timestamp_str:
                    try:
                        from datetime import datetime
                        dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                        timestamp = int(dt.timestamp())
                    except (ValueError, TypeError):
                        timestamp = message_id
                else:
                    timestamp = message_id
                    
                if timestamp > session_groups[session_key]['last_updated']:
                    session_groups[session_key]['last_updated'] = timestamp
        
        print(f"DEBUG: Processed {message_count} message records")
        print(f"DEBUG: Created {len(session_groups)} session groups")
        
        # Convert to list and sort by last_updated (ensure all values are integers)
        sessions = list(session_groups.values())
        
        # Filter out sessions with no messages
        sessions = [s for s in sessions if len(s['messages']) > 0]
        
        # Debug: Check multi-agent sessions
        multi_agent_sessions = [s for s in sessions if len(s['participating_agents']) > 1]
        print(f"DEBUG: Multi-agent sessions found: {len(multi_agent_sessions)}")
        for session in multi_agent_sessions:
            agents_str = ', '.join(session['participating_agents'])
            print(f"DEBUG: Session {session['session_id'][-20:]} has agents: {agents_str} ({len(session['messages'])} messages)")
        # Sort messages within each session by message_id (ascending)
        for session in sessions:
            session['messages'].sort(key=lambda msg: int(msg.get('message_id', 0)))
            if not isinstance(session['last_updated'], (int, float)):
                session['last_updated'] = 0
        # Sort sessions by last_updated (descending - most recent first)
        sessions.sort(key=lambda x: int(x['last_updated']), reverse=True)
        
        print(f"Total unique sessions found: {len(sessions)}")
        for i, session in enumerate(sessions[:5]):  # Log first 5 sessions
            agents_str = ', '.join(session['participating_agents'])
            print(f"Session {i+1}: ID={session['session_id'][-20:]}, Primary={session['primary_agent']}, Agents=[{agents_str}], Messages={len(session['messages'])}, LastUpdated={session['last_updated']}")
            # Log first message content for debugging
            if session['messages']:
                first_msg = session['messages'][0]['content'][:100]
                print(f"DEBUG: First message: {first_msg}...")
        
        # Log primary agent distribution
        primary_agent_counts = {}
        for session in sessions:
            primary = session['primary_agent']
            primary_agent_counts[primary] = primary_agent_counts.get(primary, 0) + 1
        print(f"DEBUG: Primary agent distribution: {primary_agent_counts}")
        
        # Log the final JSON being returned
        response_body = json.dumps(sessions)
        print(f"DEBUG: Returning {len(sessions)} sessions in response")
        print(f"DEBUG: Response body length: {len(response_body)} characters")
        
        # Add 'agent' field for frontend compatibility
        for session in sessions:
            session['agent'] = session['primary_agent']
        
        response_body = json.dumps(sessions)
        
        # Return all sessions
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': response_body
        }
        
    except Exception as e:
        print(f"Error getting sessions: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({'error': 'Internal server error'})
        }