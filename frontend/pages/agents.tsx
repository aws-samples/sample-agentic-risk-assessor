import { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/router';
import Sidebar from '../components/Sidebar';
import { buildWebSocketUrl } from '../utils/websocket';

interface Message {
  role: string;
  content: string;
}

const agents = [
  // { id: 'orchestrator', name: '🎩 Orchestrator', description: 'Coordinates workflows and manages project context' },
  { id: 'risk-assessment', name: '📊 Risk Assessment', description: 'Calculates risk scores and identifies gaps' },
  { id: 'architect', name: '🏗️ Architect', description: 'Analyzes diagrams and identifies AWS components' },
  { id: 'security-architect', name: '🔒 Security Architect', description: 'Assigns controls to infrastructure nodes' },
  { id: 'risk-framework', name: '📊 Risk Framework', description: 'Maps security frameworks to AWS services' }
];

export default function Agents() {
  const [selectedAgent, setSelectedAgent] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const chatAreaRef = useRef<HTMLDivElement | null>(null);
  const router = useRouter();

  useEffect(() => {
    if (selectedAgent) {
      const agentPath = selectedAgent.replace('-', '_');
      const agentsUrl = process.env.NEXT_PUBLIC_AGENTS_URL;
      if (!agentsUrl) {
        console.error('NEXT_PUBLIC_AGENTS_URL environment variable not set');
        return;
      }
      const ws = new WebSocket(buildWebSocketUrl(agentsUrl, `/${agentPath}/ws/chat`));
      wsRef.current = ws;
      
      ws.onopen = () => console.log('WebSocket connected');
      ws.onmessage = (event) => {
        console.log('📨 Raw WebSocket message:', event.data);
        const data = JSON.parse(event.data);
        console.log('📨 Parsed WebSocket data:', data);
        console.log('📨 Data keys:', Object.keys(data));
        console.log('📨 refresh_required value:', data.refresh_required);
        
        if (data.response) {
          let message: Message = { role: 'assistant', content: data.response };
          setMessages(prev => [...prev, message]);
          setLoading(false);
          
          // Check for refresh flag and trigger diagram refresh
          if (data.refresh_required || (typeof data.response === 'string' && data.response.includes('refresh_required'))) {
            console.log('🔄 Agent returned refresh_required flag, triggering diagram refresh');
            setTimeout(() => {
              console.log('🔄 Dispatching forceRefreshDiagram event');
              window.dispatchEvent(new CustomEvent('forceRefreshDiagram'));
            }, 500);
          } else {
            console.log('❌ No refresh flag detected in response');
          }
          
          // Auto-scroll to bottom
          setTimeout(() => {
            if (chatAreaRef.current) {
              chatAreaRef.current.scrollTop = chatAreaRef.current.scrollHeight;
            }
          }, 100);
        }
      };
      ws.onerror = () => {
        setMessages(prev => [...prev, { role: 'assistant', content: 'Connection error' }]);
        setLoading(false);
      };
      
      return () => ws.close();
    }
  }, [selectedAgent]);

  const sendMessage = (message?: string) => {
    const messageToSend = message || input;
    if (!messageToSend.trim() || !selectedAgent || !wsRef.current) return;

    const userMessage: Message = { role: 'user', content: messageToSend };
    setMessages(prev => [...prev, userMessage]);
    setLoading(true);
    
    // Auto-scroll to bottom
    setTimeout(() => {
      if (chatAreaRef.current) {
        chatAreaRef.current.scrollTop = chatAreaRef.current.scrollHeight;
      }
    }, 100);
    
    wsRef.current.send(JSON.stringify({
      message: messageToSend,
      agent: selectedAgent
    }));
    
    if (!message) setInput('');
  };



  return (
    <div style={{ 
      fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
      backgroundColor: '#e4e4e4ff',
      color: '#000000',
      lineHeight: 1.6,
      height: '100vh',
      display: 'flex',
      flex: 1
    }}>
      <Sidebar activePage="agents" />

      {/* Main Area */}
      <div style={{ flex: 1, margin: '1rem', overflow: 'hidden', height: '100%' }}>
        <div style={{
          fontSize: '2rem',
          fontWeight: '600',
          color: '#ff6b35',
          marginBottom: '1rem',
          textAlign: 'center'
        }}>
          Chat with AI Agents
        </div>
        
        <div style={{ display: 'flex', gap: '1rem', height: 'calc(100vh - 110px)' }}>
          {/* Agent Selection */}
          <div style={{
            flex: 1,
            backgroundColor: '#ffffff',
            border: '2px solid #ff6b35',
            borderRadius: '8px',
            padding: '1rem',
            overflow: 'auto'
          }}>
            <h3 style={{ color: '#ff6b35', fontSize: '1.3rem', fontWeight: '600' }}>Select Agent</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              {agents.map(agent => (
                <div 
                  key={agent.id}
                  onClick={() => {
                    setSelectedAgent(agent.id);
                    setMessages([]);
                  }}
                  style={{
                    padding: '1rem',
                    border: selectedAgent === agent.id ? '1px solid #ff6b35' : '1px solid #ddd',
                    borderRadius: '8px',
                    cursor: 'pointer',
                    backgroundColor: selectedAgent === agent.id ? '#fff5f0' : '#f8f9fa',
                    transition: 'all 0.2s'
                  }}
                  onMouseEnter={(e) => {
                    if (selectedAgent !== agent.id) {
                      e.currentTarget.style.backgroundColor = '#f0f0f0';
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (selectedAgent !== agent.id) {
                      e.currentTarget.style.backgroundColor = '#f8f9fa';
                    }
                  }}
                >
                  <div style={{
                    color: selectedAgent === agent.id ? '#ff6b35' : '#333',
                    marginBottom: '1rem',
                    fontSize: '1.1rem',
                    fontWeight: '600'
                  }}>
                    {agent.name}
                  </div>
                  <p style={{
                    color: '#666',
                    margin: 0,
                    fontSize: '0.9rem',
                    lineHeight: 1.4
                  }}>
                    {agent.description}
                  </p>
                </div>
              ))}
            </div>
          </div>

          {/* Chat Area */}
          <div style={{
            flex: 2,
            backgroundColor: '#ffffff',
            border: '2px solid #ff6b35',
            borderRadius: '8px',
            padding: '1rem',
            display: 'flex',
            flexDirection: 'column'
          }}>
            {selectedAgent ? (
              <>
                <h3 style={{
                  color: '#ff6b35',
                  marginBottom: '1.5rem',
                  fontSize: '1.3rem',
                  textAlign: 'center', 
                  fontWeight: '600'
                  
                }}>
                  Chat with {agents.find(a => a.id === selectedAgent)?.name}
                </h3>
                
                <div 
                  ref={chatAreaRef}
                  style={{
                    flex: 1,
                    backgroundColor: '#f8f9fa',
                    border: '1px solid #ff6b35',
                    borderRadius: '8px',
                    padding: '1rem',
                    marginBottom: '1rem',
                    overflowY: 'auto',
                    minHeight: 0
                  }}
                >
                  {messages.length === 0 && (
                    <div style={{ fontStyle: 'italic', color: '#6b6b6bff', textAlign: 'center' }}>
                      Start a conversation with {agents.find(a => a.id === selectedAgent)?.name}...
                    </div>
                  )}
                  {messages.map((msg, idx) => (
                    <div key={idx} style={{
                      marginBottom: '1rem',
                      padding: '0.75rem',
                      borderRadius: '8px',
                      fontSize: '0.9rem',
                      backgroundColor: msg.role === 'user' ? '#ff6b35' : '#cdcdcdff',
                      color: msg.role === 'user' ? '#ffffff' : '#000000',
                      marginLeft: msg.role === 'user' ? '1rem' : '0',
                      marginRight: msg.role === 'user' ? '0' : '0'
                    }}>
                      <strong>{msg.role === 'user' ? 'You' : 'Agent'}:</strong>
                      <div style={{ whiteSpace: 'pre-wrap', lineHeight: '1.4', marginTop: '4px' }}>
                        {msg.content}
                      </div>
                    </div>
                  ))}
                  {loading && (
                    <div style={{ fontStyle: 'italic', color: '#ccc', textAlign: 'center' }}>
                      Agent is thinking...
                    </div>
                  )}
                </div>

                <div style={{ display: 'flex', gap: '0.5rem' }}>
                  <input
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
                    placeholder="Type your message..."
                    style={{
                      flex: 1,
                      backgroundColor: '#f8f9fa',
                      color: '#000000',
                      border: '1px solid #ff6b35',
                      padding: '0.75rem',
                      borderRadius: '4px',
                      fontSize: '0.9rem'
                    }}
                  />
                  <button
                    onClick={() => sendMessage()}
                    disabled={loading || !input.trim()}
                    style={{
                      backgroundColor: '#ff6026ff',
                      color: '#ffffff',
                      border: 'none',
                      paddingLeft: '1rem',
                      paddingRight: '1rem',
                      // padding: '0.75rem 1.5rem',
                      borderRadius: '4px',
                      cursor: loading || !input.trim() ? 'not-allowed' : 'pointer',
                      fontSize: '1.3rem',
                      opacity: loading || !input.trim() ? 0.6 : 1
                    }}
                  >
                    {/* <span style={{marginRight: '0.5rem'}}>Send</span> */}
                    ➤
                  </button>
                </div>
              </>
            ) : (
              <div style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                height: '100%',
                textAlign: 'center',
                color: '#666'
              }}>
                <div>
                  <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>🤖</div>
                  <h3 style={{ color: '#ff6b35', marginBottom: '0.5rem' }}>Select an Agent</h3>
                  <p>Choose an AI agent from the left panel to start chatting</p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}