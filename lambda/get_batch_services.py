import json
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    """Get services for current batch"""
    try:
        logger.info(f"=== GET_BATCH_SERVICES START ===")
        logger.info(f"FULL_EVENT: {json.dumps(event)}")
        
        services = event.get('services', [])
        framework = event.get('framework')
        
        if not framework:
            logger.error('Framework is required')
            return {'error': 'Framework selection is required'}
        batch_size = event.get('batchSize', 3)
        current_batch = event.get('currentBatch', 0)
        
        logger.info(f"BATCH_INPUT: batch={current_batch}, size={batch_size}, total={len(services)}")
        logger.info(f"SERVICES: {services}")
        
        start_index = current_batch * batch_size
        end_index = start_index + batch_size
        has_more = end_index < len(services)
        
        current_batch_services = services[start_index:end_index]
        
        logger.info(f"BATCH_CALC: start={start_index}, end={end_index}, has_more={has_more}")
        logger.info(f"BATCH_SERVICES: {current_batch_services}")
        
        result = {
            'services': services,
            'framework': framework,
            'batchSize': batch_size,
            'currentBatch': current_batch,
            'currentBatchServices': current_batch_services,
            'hasMoreBatches': has_more
        }
        
        logger.info(f"RESULT: {json.dumps(result)}")
        logger.info(f"=== GET_BATCH_SERVICES END ===")
        return result
        
    except Exception as e:
        logger.error(f"ERROR: {str(e)}")
        logger.error(f"ERROR_EVENT: {json.dumps(event)}")
        return {
            'error': str(e)
        }