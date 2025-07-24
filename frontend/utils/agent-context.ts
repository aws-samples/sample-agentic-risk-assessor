

const TARGET_AGENTS = [
  'risk-assessment',
  'architect', 
  'security-architect',
  'auditor'
];

export const clearAgentContexts = async (): Promise<{ success: boolean; results?: any; error?: string }> => {
  try {
    const results: Record<string, string> = {};
    
    // Get WebSocket references from the risk assessment page
    const wsRefs = (window as any).wsRefs;
    if (!wsRefs) {
      return {
        success: false,
        error: 'WebSocket connections not available'
      };
    }
    
    // Send clear context message through WebSocket to each agent
    for (const agentName of TARGET_AGENTS) {
      try {
        const ws = wsRefs.current?.[agentName];
        if (ws && ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({
            message: "CLEAR_CONTEXT: Switching projects",
            agent: agentName
          }));
          results[agentName] = 'success';
        } else {
          results[agentName] = 'not_connected';
        }
      } catch (error: any) {
        results[agentName] = `error: ${error.message}`;
      }
    }
    
    const successCount = Object.values(results).filter(r => r === 'success').length;
    
    return {
      success: successCount > 0,
      results
    };
  } catch (error: any) {
    console.error('Error clearing agent contexts:', error);
    return {
      success: false,
      error: error.message || 'Failed to clear agent contexts'
    };
  }
};