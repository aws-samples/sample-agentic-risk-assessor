// semgrep:ignore javascript.lang.security.audit.unsafe-formatstring.unsafe-formatstring: Console logging for debugging only, not user-facing
import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import { getCurrentUser, getJwtToken } from '../utils/auth';
import Sidebar from '../components/Sidebar';

interface AgentStatus {
  name: string;
  status: 'online' | 'offline' | 'restarting';
  lastCheck: string;
  internalState: 'normal' | 'restart-pending' | 'restart-confirmed-offline' | 'restart-complete';
}

export default function Health() {
  const router = useRouter();
  const [agents, setAgents] = useState<AgentStatus[]>([
    { name: 'Architect', status: 'offline', lastCheck: '', internalState: 'normal' },
    { name: 'Security-Architect', status: 'offline', lastCheck: '', internalState: 'normal' },
    { name: 'Auditor', status: 'offline', lastCheck: '', internalState: 'normal' },
    { name: 'Risk-Assessment', status: 'offline', lastCheck: '', internalState: 'normal' }
  ]);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [restartingAll, setRestartingAll] = useState(false);
  const [restartingSystem, setRestartingSystem] = useState(false);
  
  const hasRestartingAgents = agents.some(agent => agent.status === 'restarting');

  const checkHealth = async () => {
    const token = await getJwtToken();
    
    setAgents(currentAgents => {
      // Process agents asynchronously and update state
      const processAgents = async () => {
        const updatedAgents: AgentStatus[] = await Promise.all(
          currentAgents.map(async (agent): Promise<AgentStatus> => {
            try {
              const response = await fetch('/api/health-proxy', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ agent: agent.name.toLowerCase(), token })
              });
              
              const isOnline = response.ok;
              const newLastCheck = new Date().toLocaleTimeString();
              
              // State machine logic for restart tracking
              if (agent.internalState === 'restart-pending' && !isOnline) {
                // Agent went offline after restart - mark as confirmed offline
                return {
                  ...agent,
                  status: 'restarting' as const,
                  lastCheck: newLastCheck,
                  internalState: 'restart-confirmed-offline' as const
                };
              } else if (agent.internalState === 'restart-confirmed-offline' && isOnline) {
                // Agent came back online after being offline - restart complete
                return {
                  ...agent,
                  status: 'online' as const,
                  lastCheck: newLastCheck,
                  internalState: 'normal' as const
                };
              } else if (agent.internalState === 'restart-pending' || agent.internalState === 'restart-confirmed-offline') {
                // Still in restart cycle - keep restarting status
                return {
                  ...agent,
                  status: 'restarting' as const,
                  lastCheck: newLastCheck
                };
              } else {
                // Normal operation
                return {
                  ...agent,
                  status: isOnline ? 'online' as const : 'offline' as const,
                  lastCheck: newLastCheck
                };
              }
            } catch (error) {
              const newLastCheck = new Date().toLocaleTimeString();
              
              // Handle error case in state machine
              if (agent.internalState === 'restart-pending' || agent.internalState === 'restart-confirmed-offline') {
                return {
                  ...agent,
                  status: 'restarting' as const,
                  lastCheck: newLastCheck
                };
              } else {
                return {
                  ...agent,
                  status: 'offline' as const,
                  lastCheck: newLastCheck
                };
              }
            }
          })
        );
        
        // Update state with the processed agents
        setAgents(updatedAgents);
      };
      
      // Execute the async processing
      processAgents();
      
      // Return current agents immediately (will be updated by processAgents)
      return currentAgents;
    });
  };

  const restartAgent = async (agentName: string) => {
    if (!isAuthenticated) {
      alert('Please login first');
      router.push('/login');
      return;
    }
    
    const confirmed = window.confirm(
      `⚠️ WARNING: This will restart the ${agentName} agent.\n\n` +
      `The agent will be temporarily unavailable during restart.\n\n` +
      `Are you sure you want to continue?`
    );
    
    if (!confirmed) {
      return;
    }
    
    try {
      const token = await getJwtToken();
      if (!token) {
        alert('Authentication token not available. Please login again.');
        router.push('/login');
        return;
      }
      
      console.log('Sending restart request with token:', token.substring(0, 20) + '...');
      
      const response = await fetch('/api/restart-proxy', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ agent: agentName.toLowerCase(), token })
      });
      
      if (response.ok) {
        const data = await response.json();
        console.log('Restart successful:', data);
        
        // Update status to restarting and set restart state
        setAgents(prev => prev.map(agent => 
          agent.name === agentName 
            ? { ...agent, status: 'restarting', internalState: 'restart-pending' }
            : agent
        ));
        
        setTimeout(checkHealth, 3000);
      } else {
        const errorData = await response.json();
        console.error('Restart failed:', errorData);
      }
    } catch (error) {
      console.error('Restart failed:', error);
    }
  };

  const restartAllAgents = async () => {
    if (!isAuthenticated) {
      alert('Please login first');
      router.push('/login');
      return;
    }
    
    const confirmed = window.confirm(
      `⚠️ CRITICAL WARNING: This will restart ALL agents simultaneously.\n\n` +
      `ALL agents will be temporarily unavailable during restart.\n` +
      `This may cause service disruption.\n\n` +
      `Are you absolutely sure you want to restart all agents?`
    );
    
    if (!confirmed) {
      return;
    }
    
    setRestartingAll(true);
    
    // Restart all agents in parallel for faster execution
    const restartPromises = agents.map(async (agent) => {
      try {
        const token = await getJwtToken();
        if (!token) {
          throw new Error('No authentication token');
        }
        
        const response = await fetch('/api/restart-proxy', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ agent: agent.name.toLowerCase(), token })
        });
        
        if (!response.ok) {
          throw new Error(`Failed to restart ${agent.name}`);
        }
        
        return { agent: agent.name, success: true };
      } catch (error) {
        // nosemgrep
        console.error(`Failed to restart ${agent.name}:`, error);
        return { agent: agent.name, success: false, error };
      }
    });
    
    const results = await Promise.all(restartPromises);
    
    // Update all agents to restarting status
    setAgents(prev => prev.map(agent => ({ ...agent, status: 'restarting', internalState: 'restart-pending' })));
    
    // Check results and show summary
    const failed = results.filter(r => !r.success);
    if (failed.length > 0) {
      alert(`Some agents failed to restart: ${failed.map(f => f.agent).join(', ')}`);
    }
    
    setRestartingAll(false);
    
    // Recheck health after delay
    setTimeout(checkHealth, 5000);
  };

  const restartSystem = async () => {
    if (!isAuthenticated) {
      alert('Please login first');
      router.push('/login');
      return;
    }
    
    const confirmed = window.confirm(
      `⚡ SYSTEM RESTART: This will restart all 4 ECS agent services.\n\n` +
      `All agents will be temporarily unavailable during restart.\n\n` +
      `Are you sure you want to restart the system?`
    );
    
    if (!confirmed) {
      return;
    }
    
    setRestartingSystem(true);
    
    try {
      const token = await getJwtToken();
      if (!token) {
        alert('Authentication token not available. Please login again.');
        router.push('/login');
        return;
      }
      
      const response = await fetch('/api/restart-system', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token })
      });
      
      if (response.ok) {
        const data = await response.json();
        alert('System restart initiated successfully. All ECS services are restarting...');
        
        // Update all agents to restarting status
        setAgents(prev => prev.map(agent => ({ ...agent, status: 'restarting', internalState: 'restart-pending' })));
        
        // Recheck health after delay
        setTimeout(checkHealth, 5000);
      } else {
        const errorData = await response.json();
        alert(`System restart failed: ${errorData.error || 'Unknown error'}`);
      }
    } catch (error) {
      console.error('System restart failed:', error);
      alert('Failed to restart system. Please try again.');
    } finally {
      setRestartingSystem(false);
    }
  };

  useEffect(() => {
    const checkAuth = async () => {
      const { user } = await getCurrentUser();
      setIsAuthenticated(!!user);
    };
    
    checkAuth();
    checkHealth();
    const interval = setInterval(checkHealth, 10000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div style={{ 
      fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
      backgroundColor: '#e4e4e4',
      color: '#000000',
      lineHeight: 1.6,
      height: '100vh',
      display: 'flex'
    }}>
      <Sidebar activePage="health" startCollapsed={true} />

      {/* Main Area */}
      <div style={{ flex: 1, padding: '1rem', overflow: 'hidden' }}>
        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'center', marginBottom: '1rem' }}>
          <h1 style={{ color: '#ff6b35', fontSize: '1.5rem', fontWeight: '600', margin: 0 }}>Agent Health Status</h1>
        </div>
        
        {!isAuthenticated && (
          <div style={{ 
            backgroundColor: '#fff3cd', 
            border: '2px solid #ff6b35', 
            padding: '1rem', 
            marginBottom: '1rem', 
            borderRadius: '8px',
            color: '#2a2a2a'
          }}>
            ⚠️ Authentication required for restart functionality. <a href="/login" style={{ color: '#ff6b35' }}>Login here</a>
          </div>
        )}

        {/* Restart Buttons */}
        <div style={{ marginBottom: '1rem', display: 'flex', gap: '1rem' }}>
          <button
            onClick={restartAllAgents}
            disabled={!isAuthenticated || restartingAll}
            style={{
              padding: '0.75rem 1.5rem',
              backgroundColor: isAuthenticated && !restartingAll ? '#dc3545' : '#6c757d',
              color: 'white',
              border: 'none',
              borderRadius: '6px',
              cursor: isAuthenticated && !restartingAll ? 'pointer' : 'not-allowed',
              opacity: isAuthenticated && !restartingAll ? 1 : 0.6,
              fontSize: '1rem',
              fontWeight: '600'
            }}
          >
            {restartingAll ? '🔄 Resetting Context...' : '🔄 Reset Context'}
          </button>
          
          <button
            onClick={restartSystem}
            disabled={!isAuthenticated || restartingSystem || hasRestartingAgents}
            style={{
              padding: '0.75rem 1.5rem',
              backgroundColor: isAuthenticated && !restartingSystem && !hasRestartingAgents ? '#e74c3c' : '#6c757d',
              color: 'white',
              border: 'none',
              borderRadius: '6px',
              cursor: isAuthenticated && !restartingSystem && !hasRestartingAgents ? 'pointer' : 'not-allowed',
              opacity: isAuthenticated && !restartingSystem && !hasRestartingAgents ? 1 : 0.6,
              fontSize: '1rem',
              fontWeight: '600'
            }}
          >
            {restartingSystem ? '⚡ Restarting System...' : '⚡ Restart the System'}
          </button>
        </div>

        {/* Agent Status Cards */}
        <div style={{
          backgroundColor: '#ffffff',
          border: '2px solid #ff6b35',
          borderRadius: '8px',
          padding: '1.5rem',
          overflow: 'hidden'
        }}>
          <div style={{ display: 'grid', gap: '1rem' }}>
            {agents.map(agent => (
              <div key={agent.name} style={{
                backgroundColor: '#f8f8f8',
                border: '1px solid #ddd',
                borderRadius: '8px',
                padding: '1rem',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between'
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                  <div style={{
                    fontSize: '1.1rem',
                    fontWeight: '600',
                    color: '#2a2a2a',
                    minWidth: '150px'
                  }}>
                    {agent.name}
                  </div>
                  <div style={{
                    padding: '0.25rem 0.75rem',
                    borderRadius: '20px',
                    fontSize: '0.8rem',
                    fontWeight: '600',
                    backgroundColor: agent.status === 'online' ? '#d4edda' : 
                                   agent.status === 'restarting' ? '#fff3cd' : '#f8d7da',
                    color: agent.status === 'online' ? '#155724' : 
                           agent.status === 'restarting' ? '#856404' : '#721c24',
                    border: `1px solid ${agent.status === 'online' ? '#c3e6cb' : 
                                        agent.status === 'restarting' ? '#ffeaa7' : '#f5c6cb'}`
                  }}>
                    {agent.status.toUpperCase()}
                  </div>
                  <div style={{ fontSize: '0.9rem', color: '#666' }}>
                    {agent.lastCheck && `Last check: ${agent.lastCheck}`}
                  </div>
                </div>
                <button
                  onClick={() => restartAgent(agent.name)}
                  disabled={!isAuthenticated}
                  style={{
                    padding: '0.5rem 1rem',
                    backgroundColor: isAuthenticated ? '#ff6b35' : '#6c757d',
                    color: 'white',
                    border: 'none',
                    borderRadius: '4px',
                    cursor: isAuthenticated ? 'pointer' : 'not-allowed',
                    opacity: isAuthenticated ? 1 : 0.6,
                    fontSize: '0.9rem',
                    fontWeight: '500'
                  }}
                >
                  🔄 Reset
                </button>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}