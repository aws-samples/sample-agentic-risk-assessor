import React, { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/router';
import styles from '../styles/FullReview.module.css';
import TokenRenderer from '../components/TokenRenderer';
import logo from '../images/logo-risk.png';
import Image from 'next/image';
import { getProject } from '../utils/api';
import { buildWebSocketUrl } from '../utils/websocket';

interface AgentStatus {
  name: string;
  status: 'idle' | 'active' | 'complete';
  progress: number;
  currentTask?: string;
  content?: string[];
}

interface AssessmentFlowProps {
  projectId?: string;
  framework?: string;
}

export default function AssessmentFlow({ projectId: propProjectId, framework: propFramework }: AssessmentFlowProps = {}) {
  const router = useRouter();
  const { projectId: queryProjectId, framework: queryFramework } = router.query;
  
  // Use props if available, otherwise fall back to router query
  const projectId = propProjectId || queryProjectId;
  const framework = propFramework || queryFramework;
  
  const [agents, setAgents] = useState<AgentStatus[]>([
    { name: 'Risk Assessment', status: 'idle', progress: 0 },
    { name: 'Architect', status: 'idle', progress: 0 },
    { name: 'Security Architect', status: 'idle', progress: 0 },
    { name: 'Validator', status: 'idle', progress: 0 }
  ]);
  
  const [isRunning, setIsRunning] = useState(false);
  const [overallStatus, setOverallStatus] = useState('Ready to start Risk Assessment');
  const [statusDetail, setStatusDetail] = useState('Click start to begin automated security analysis');
  const [projectName, setProjectName] = useState<string>('');
  
  // WebSocket connections for each agent
  const [wsConnections, setWsConnections] = useState<{[key: string]: WebSocket}>({});
  const [a2aCommunications, setA2aCommunications] = useState<any[]>([]);
  const [lineCoords, setLineCoords] = useState({ 
    architect: { x1: 0, y1: 0, x2: 0, y2: 0 },
    security: { x1: 0, y1: 0, x2: 0, y2: 0 },
    auditor: { x1: 0, y1: 0, x2: 0, y2: 0 }
  });
  const [statusPosition, setStatusPosition] = useState({ left: '50%', top: '80%' });
  const riskRef = useRef<HTMLDivElement>(null);
  const architectRef = useRef<HTMLDivElement>(null);
  const securityRef = useRef<HTMLDivElement>(null);
  const auditorRef = useRef<HTMLDivElement>(null);
  const rightPanelRef = useRef<HTMLDivElement>(null);
  const agentRefs = useRef<{[key: string]: HTMLDivElement | null}>({});
  
  // Fetch project details when projectId is available
  useEffect(() => {
    const fetchProjectDetails = async () => {
      if (projectId) {
        const { data: project, error } = await getProject(projectId as string);
        if (project && !error) {
          setProjectName(project.project_name || project.name || `Project ${projectId}`);
        } else {
          setProjectName(`Project ${projectId}`);
        }
      }
    };
    
    fetchProjectDetails();
  }, [projectId]);
  
  useEffect(() => {
    // Initialize WebSocket connections to each agent's progress endpoint immediately
    // (Don't wait for projectId/framework - just connect for monitoring)
    const getJwtToken = async () => {
      try {
        const { Auth } = await import('aws-amplify');
        const session = await Auth.currentSession();
        return session.getAccessToken().getJwtToken();
      } catch (error) {
        console.error('Failed to get JWT token:', error);
        return null;
      }
    };
    
    const initializeConnections = async () => {
      const token = await getJwtToken();
      if (!token) {
        console.error('No JWT token available for WebSocket connections');
        return;
      }
      
      const agentsUrl = process.env.NEXT_PUBLIC_AGENTS_URL;
      if (!agentsUrl) {
        console.error('NEXT_PUBLIC_AGENTS_URL environment variable not set');
        return;
      }
      
      const agentEndpoints = {
        'Risk Assessment': buildWebSocketUrl(agentsUrl, '/risk-assessment/ws/progress', token || undefined),
        'Architect': buildWebSocketUrl(agentsUrl, '/architect/ws/progress', token || undefined),
        'Security Architect': buildWebSocketUrl(agentsUrl, '/security-architect/ws/progress', token || undefined),
        'Validator': buildWebSocketUrl(agentsUrl, '/auditor/ws/progress', token || undefined)
      };
      
      const newConnections: {[key: string]: WebSocket} = {};
      
      Object.entries(agentEndpoints).forEach(([agentName, wsUrl]) => {
        const ws = new WebSocket(wsUrl);
      
      ws.onopen = () => {
        console.log('Connected to progress WebSocket:', agentName, wsUrl);
        setAgents(prev => prev.map(agent => 
          agent.name === agentName 
            ? { ...agent, currentTask: 'Connected - ready for progress updates' }
            : agent
        ));
      };
      
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          console.log('Progress message received:', agentName, data);
          // Use agent_name from the message if available, otherwise fall back to endpoint name
          const messageAgentName = data.agent_name || agentName;
          handleProgressUpdate(messageAgentName, data);
        } catch (error) {
          console.error('Error parsing message:', agentName, error, 'Raw data:', event.data);
        }
      };
      
      ws.onerror = (error) => {
        console.error('WebSocket error:', agentName, wsUrl, error);
        setAgents(prev => prev.map(agent => 
          agent.name === agentName 
            ? { ...agent, status: 'idle', progress: 0, currentTask: 'Connection failed - check agent deployment' }
            : agent
        ));
      };
      
      ws.onclose = (event) => {
        console.log('Disconnected from progress WebSocket:', agentName, 'Code:', event.code, 'Reason:', event.reason);
        if (event.code !== 1000) {
          setAgents(prev => prev.map(agent => 
            agent.name === agentName 
              ? { ...agent, status: 'idle', progress: 0, currentTask: `Connection closed (${event.code}) - agent may not be running` }
              : agent
          ));
        }
      };
      
      newConnections[agentName] = ws;
    });
    
      setWsConnections(newConnections);
      
      return () => {
        Object.values(newConnections).forEach(ws => ws.close());
      };
    };
    
    initializeConnections();
  }, []); // Connect immediately on page load, no dependencies
  
  const handleProgressUpdate = (agentName: string, data: any) => {
    console.log('Status update:', agentName, data.type, data);
    
    // Map agent names to handle case differences
    const normalizeAgentName = (name: string) => {
      const nameMap: {[key: string]: string} = {
        'auditor': 'Validator',
        'Auditor': 'Validator',
        'architect': 'Architect', 
        'Architect': 'Architect',
        'security-architect': 'Security Architect',
        'Security Architect': 'Security Architect',
        'risk-assessment': 'Risk Assessment',
        'Risk Assessment': 'Risk Assessment'
      };
      return nameMap[name] || name;
    };
    
    const normalizedAgentName = normalizeAgentName(agentName);
    
    switch (data.type) {
      case 'agent_active':
        setAgents(prev => prev.map(agent => 
          agent.name === normalizedAgentName 
            ? { ...agent, status: 'active', currentTask: data.task }
            : agent
        ));
        setOverallStatus(data.task);
        setStatusDetail(`${normalizedAgentName} processing`);
        break;
        
      case 'agent_complete':
        setAgents(prev => prev.map(agent => 
          agent.name === normalizedAgentName 
            ? { ...agent, status: 'complete', progress: 100 }
            : agent
        ));
        break;
        
      case 'agent_idle':
        setAgents(prev => prev.map(agent => 
          agent.name === normalizedAgentName 
            ? { ...agent, status: 'idle', progress: 0, currentTask: undefined }
            : agent
        ));
        break;
        
      case 'content_stream':
        setAgents(prev => prev.map(agent => 
          agent.name === normalizedAgentName 
            ? { 
                ...agent, 
                content: [...(agent.content || []), data.content],
                progress: Math.min((agent.content?.length || 0) * 10, 90)
              }
            : agent
        ));
        break;
        
      case 'a2a_communication':
        setA2aCommunications(prev => [...prev, { ...data, timestamp: Date.now() }]);
        break;
    }
  };
  
  const startAssessment = async () => {
    if (!projectId || !framework) {
      alert('Missing project ID or framework');
      return;
    }
    
    setIsRunning(true);
    setOverallStatus('Starting Risk Assessment workflow...');
    setStatusDetail('Initializing agents');
    
    // Send start command via WebSocket chat like the Risk Assessment page
    const getJwtToken = async () => {
      try {
        const { Auth } = await import('aws-amplify');
        const session = await Auth.currentSession();
        return session.getAccessToken().getJwtToken();
      } catch (error) {
        console.error('Failed to get JWT token:', error);
        return null;
      }
    };
    
    const token = await getJwtToken();
    if (!token) {
      alert('Authentication required');
      setIsRunning(false);
      return;
    }
    
    const agentsUrl = process.env.NEXT_PUBLIC_AGENTS_URL;
    if (!agentsUrl) {
      alert('Agents URL not configured');
      setIsRunning(false);
      return;
    }
    
    // Create or get session ID like the risk assessment page does
    let sessionId: string | undefined;
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/sessions/create`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          project_id: projectId,
          agent_id: 'risk-assessment'
        })
      });
      
      if (response.ok) {
        const sessionData = await response.json();
        sessionId = sessionData.session_id;
        console.log('Created session for assessment flow:', sessionId);
      } else {
        console.error('Failed to create session for assessment flow');
      }
    } catch (error) {
      console.error('Error creating session for assessment flow:', error);
    }
    
    const ws = new WebSocket(buildWebSocketUrl(agentsUrl, '/risk-assessment/ws/chat', token || undefined));
    
    ws.onopen = () => {
      console.log('Connected to Risk Assessment agent for starting assessment');
      ws.send(JSON.stringify({
        message: `perform_full_risk_assessment ${projectId} ${framework}`,
        agent: 'risk-assessment',
        project_id: projectId,
        session_id: sessionId
      }));
    };
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      console.log('Assessment response:', data);
      if (data.response) {
        setOverallStatus('Assessment started successfully');
        setStatusDetail('Workflow initiated');
      }
    };
    
    ws.onerror = (error) => {
      console.error('Failed to start assessment:', error);
      setOverallStatus('Failed to start assessment');
      setStatusDetail('WebSocket connection error');
      setIsRunning(false);
    };
  };
  
  const resetAssessment = () => {
    setIsRunning(false);
    setOverallStatus('Ready to start Risk Assessment');
    setStatusDetail('Click start to begin automated security analysis');
    setAgents(prev => prev.map(agent => ({
      ...agent,
      status: 'idle',
      progress: 0,
      currentTask: undefined,
      content: []
    })));
  };
  
  const getAgentIcon = (name: string) => {
    switch (name) {
      case 'Risk Assessment': return <Image src={logo} alt="Risk Assessment" width={20} height={20} />;
      case 'Architect': return '🏗️';
      case 'Security Architect': return '🛡️';
      case 'Validator': return '🔍';
      default: return '🤖';
    }
  };
  
  const updateProgress = (agentName: string, progress: number) => {
    const radius = agentName === 'Risk Assessment' ? 22 : 18;
    const circumference = 2 * Math.PI * radius;
    const offset = circumference - (progress / 100) * circumference;
    
    const circle = document.getElementById(`${agentName.toLowerCase().replace(' ', '-')}-progress`);
    if (circle) {
      circle.style.strokeDasharray = circumference.toString();
      circle.style.strokeDashoffset = offset.toString();
    }
  };
  
  const updateLineCoords = () => {
    if (riskRef.current && architectRef.current && securityRef.current && auditorRef.current) {
      const riskRect = riskRef.current.getBoundingClientRect();
      const architectRect = architectRef.current.getBoundingClientRect();
      const securityRect = securityRef.current.getBoundingClientRect();
      const auditorRect = auditorRef.current.getBoundingClientRect();
      const containerRect = riskRef.current.parentElement?.getBoundingClientRect();
      
      if (containerRect) {
        const riskX = riskRect.left - containerRect.left;
        const riskY = riskRect.top - containerRect.top + riskRect.height / 2;
        
        setLineCoords({
          architect: {
            x1: riskX,
            y1: riskY,
            x2: architectRect.left - containerRect.left + architectRect.width / 2,
            y2: architectRect.top - containerRect.top
          },
          security: {
            x1: riskX + riskRect.width / 2,
            y1: riskY,
            x2: securityRect.left - containerRect.left + securityRect.width / 2,
            y2: securityRect.top - containerRect.top
          },
          auditor: {
            x1: riskX + riskRect.width,
            y1: riskY,
            x2: auditorRect.left - containerRect.left + auditorRect.width / 2,
            y2: auditorRect.top - containerRect.top
          }
        });
        
      }
    }
  };
  
  const updateStatusPosition = () => {
    const activeAgent = agents.find(agent => agent.status === 'active');
    if (activeAgent && riskRef.current && architectRef.current && securityRef.current && auditorRef.current) {
      let activeRef;
      switch(activeAgent.name) {
        case 'Risk Assessment': activeRef = riskRef.current; break;
        case 'Architect': activeRef = architectRef.current; break;
        case 'Security Architect': activeRef = securityRef.current; break;
        case 'Validator': activeRef = auditorRef.current; break;
      }
      if (activeRef) {
        const activeRect = activeRef.getBoundingClientRect();
        const containerRect = riskRef.current.parentElement?.getBoundingClientRect();
        if (containerRect) {
          const centerX = activeRect.left - containerRect.left + activeRect.width / 2;
          const bottomY = activeRect.bottom - containerRect.top + 10;
          setStatusPosition({ 
            left: `${centerX}px`, 
            top: `${bottomY}px`
          });
        }
      }
    }
  };

  useEffect(() => {
    agents.forEach(agent => {
      updateProgress(agent.name, agent.progress);
    });
    setTimeout(updateLineCoords, 100);
  }, [agents]);

  useEffect(() => {
    updateLineCoords();
    updateStatusPosition();
    window.addEventListener('resize', () => {
      updateLineCoords();
      updateStatusPosition();
    });
    return () => window.removeEventListener('resize', () => {
      updateLineCoords();
      updateStatusPosition();
    });
  }, []);
  
  useEffect(() => {
    updateStatusPosition();
  }, [agents]);
  

  
  // Auto-scroll to active agentct:
  useEffect(() => {
    const activeAgent = agents.find(agent => agent.status === 'active');
    if (activeAgent && rightPanelRef.current) {
      const activeAgentElement = agentRefs.current[activeAgent.name];
      if (activeAgentElement) {
        activeAgentElement.scrollIntoView({ 
          behavior: 'smooth', 
          block: 'start' 
        });
      }
    }
  }, [agents]);

  // Debug logging for router query
  useEffect(() => {
    console.log('Router query:', router.query);
  }, [router.query]);

  return (
    <div style={{ 
      position: 'fixed',
      top: 0,
      left: 0,
      width: '100vw', 
      height: '100vh',
      // backgroundColor: 'rgba(0, 0, 0, 0.8)',
      background: 'linear-gradient(90deg,rgba(2, 0, 36, 1) 0%, rgba(9, 9, 121, 1) 51%, rgba(0, 164, 196, 1) 100%)',
      display: 'flex',
      zIndex: 1000
    }}>
      <div className={styles.container} style={{
        width: 'calc(50vw)',
        height: 'calc(100vh - 100px)',
        margin: '50px 25px 50px 25px',
        borderRadius: '20px',
        // border: '2px solid rgba(255, 215, 0, 0.5)',
        boxShadow: '0 20px 60px rgba(0, 0, 0, 0)'
      }}>
      <div style={{ display: 'flex', padding: '20px', fontSize: '1.5rem', fontWeight: '500', justifyContent: 'center', color: '#FFD700' }}>
        Project: {projectName || projectId}
      </div>
      
      {/* Orchestrator Card (Risk Assessment) */}
      <div ref={riskRef} className={`${styles.supervisorCard} ${agents[0].status === 'active' ? styles.active : ''} ${agents[0].status === 'complete' ? styles.completed : ''}`}>
        <div className={styles.supervisorIcon}><Image src={logo} alt='logo' width={40} height={40} /></div>
        <div className={styles.supervisorTitle}>Risk Assessment Agent</div>
        <div className={styles.supervisorExplanation}>Conducting a comprehensive FSI risk assessment. Gathering input from security and architecture assessments. Identifying and assessing risks. Preparing Risk Assessment.</div>
        <div className={styles.supervisorSubtitle}>
          {agents[0].currentTask || 'Orchestrating Workflow'}
        </div>
        <svg className={styles.progressRing} style={{ top: '4px', right: '4px', width: '50px', height: '50px' }}>
          <circle className={styles.progressRingCircle} cx="25" cy="25" r="22" strokeWidth="4"/>
          <circle className={`${styles.progressRingProgress} ${styles.supervisorProgress}`} id="risk-assessment-progress" cx="25" cy="25" r="22" strokeWidth="4"/>
        </svg>
      </div>
      
      {/* Status Overlay */}
      <div className={styles.statusOverlay} style={{
        position: 'absolute',
        left: statusPosition.left,
        top: statusPosition.top,
        transform: 'translateX(-50%) scale(0.67)',
        zIndex: 10
      }}>
        <div className={styles.statusText}>{overallStatus}</div>
        <div className={styles.statusDetail}>{statusDetail}</div>
      </div>
      
      {/* A2A Connection Lines */}
      <svg className={styles.connectionLines} style={{
        position: 'absolute',
        top: 0,
        left: 0,
        width: '100%',
        height: '100%',
        pointerEvents: 'none',
        zIndex: 1
      }}>
        {/* Risk to Architect line - L-shape */}
        <g>
          <path
            d={`M ${lineCoords.architect.x1} ${lineCoords.architect.y1} L ${lineCoords.architect.x2} ${lineCoords.architect.y1} L ${lineCoords.architect.x2} ${lineCoords.architect.y2}`}
            stroke={agents[1].status === 'active' ? '#FFD700' : '#667eea'}
            strokeWidth={agents[1].status === 'active' ? '4' : '3'}
            strokeDasharray="5,5"
            fill="none"
          >
            {agents[1].status === 'active' && (
              <animate attributeName="stroke-dashoffset" values="0;10" dur="1s" repeatCount="indefinite" />
            )}
          </path>
        </g>
        
        {/* Risk to Security line - straight */}
        <g>
          <line
            x1={lineCoords.security.x1}
            y1={lineCoords.security.y1}
            x2={lineCoords.security.x2}
            y2={lineCoords.security.y2}
            stroke={agents[2].status === 'active' ? '#FFD700' : '#667eea'}
            strokeWidth={agents[2].status === 'active' ? '4' : '3'}
            strokeDasharray="5,5"
          >
            {agents[2].status === 'active' && (
              <animate attributeName="stroke-dashoffset" values="0;10" dur="1s" repeatCount="indefinite" />
            )}
          </line>
        </g>
        
        {/* Risk to Auditor line - L-shape */}
        <g>
          <path
            d={`M ${lineCoords.auditor.x1} ${lineCoords.auditor.y1} L ${lineCoords.auditor.x2} ${lineCoords.auditor.y1} L ${lineCoords.auditor.x2} ${lineCoords.auditor.y2}`}
            stroke={agents[3].status === 'active' ? '#FFD700' : '#667eea'}
            strokeWidth={agents[3].status === 'active' ? '4' : '3'}
            strokeDasharray="5,5"
            fill="none"
          >
            {agents[3].status === 'active' && (
              <animate attributeName="stroke-dashoffset" values="0;10" dur="1s" repeatCount="indefinite" />
            )}
          </path>
        </g>
        

        
        {a2aCommunications.length > 0 && a2aCommunications.slice(-3).map((comm, index) => {
          const getAgentPosition = (agentName: string) => {
            switch(agentName) {
              case 'architect': return { x: '25%', y: '40%' };
              case 'security_architect': return { x: '75%', y: '40%' };
              case 'risk_assessment': return { x: '50%', y: '20%' };
              case 'auditor': return { x: '50%', y: '70%' };
              default: return { x: '50%', y: '50%' };
            }
          };
          
          const fromPos = getAgentPosition(comm.from_agent);
          const toPos = getAgentPosition(comm.to_agent);
          
          return (
            <g key={`${comm.timestamp}-${index}`}>
              <line
                x1={fromPos.x}
                y1={fromPos.y}
                x2={toPos.x}
                y2={toPos.y}
                stroke="#FFD700"
                strokeWidth="3"
                className={styles.connectionLine}
                opacity={1 - (index * 0.3)}
              />

            </g>
          );
        })}
      </svg>
      
      {/* Agent Cards */}
      <div ref={architectRef} className={`${styles.agentCard} ${styles.architect} ${agents[1].status === 'active' ? styles.active : ''} ${agents[1].status === 'complete' ? styles.completed : ''}`}>
        <div className={styles.agentIcon}>🏗️</div>
        <div className={styles.agentTitle}>Architect Agent</div>
        <div className={styles.agentExplanation}>Review the solution architecture document for completeness, correctness, and FSI-grade rigor. Providing a brief assessment of the architecture's readiness for deployment, highlighting key strengths and critical gaps.</div>
        <div className={styles.agentStep}>
          {agents[1].currentTask || ''}
        </div>
        <svg className={styles.progressRing}>
          <circle className={styles.progressRingCircle} cx="20" cy="20" r="18"/>
          <circle className={styles.progressRingProgress} id="architect-progress" cx="20" cy="20" r="18"/>
        </svg>
      </div>
      
      <div ref={securityRef} className={`${styles.agentCard} ${styles.security} ${agents[2].status === 'active' ? styles.active : ''} ${agents[2].status === 'complete' ? styles.completed : ''}`}>
        <div className={styles.agentIcon}>🛡️</div>
        <div className={styles.agentTitle}>Security Architect</div>
        <div className={styles.agentExplanation}>Analyzing and identifying security issues, vulnerabilities, and compliance gaps and map  security issues to risk categories.</div>
        <div className={styles.agentStep}>
          {agents[2].currentTask || ''}
        </div>
        <svg className={styles.progressRing}>
          <circle className={styles.progressRingCircle} cx="20" cy="20" r="18"/>
          <circle className={styles.progressRingProgress} id="security-architect-progress" cx="20" cy="20" r="18"/>
        </svg>
      </div>
      
      <div ref={auditorRef} className={`${styles.agentCard} ${styles.risk} ${agents[3].status === 'active' ? styles.active : ''} ${agents[3].status === 'complete' ? styles.completed : ''}`}>
        <div className={styles.agentIcon}>🔍</div>
        <div className={styles.agentTitle}>Validator</div>
        <div className={styles.agentExplanation}>Validating all outputs, reviewing and challenging findings analagous to a Line 2 Risk review.</div>
        <div className={styles.agentStep}>
          {agents[3].currentTask || ''}
        </div>
        <svg className={styles.progressRing}>
          <circle className={styles.progressRingCircle} cx="20" cy="20" r="18"/>
          <circle className={styles.progressRingProgress} id="validator-progress" cx="20" cy="20" r="18"/>
        </svg>
      </div>
      

      </div>
      
      {/* Right-hand streaming content box */}
      <div ref={rightPanelRef} style={{
        width: '60vw',
        height: '100vh',
        backgroundColor: 'rgba(15, 23, 42, 0.4)',
        border: '2px solid rgba(255, 215, 0, 0.3)',
        padding: '20px',
        overflowY: 'auto',
        fontFamily: 'Inter, sans-serif',
        color: 'white'
      }}>
        <h3 style={{ color: '#FFD700', marginBottom: '10px', fontSize: '1.1rem' }}>Live Activity Stream</h3>
        
        <div style={{ marginBottom: '10px', fontSize: '0.75rem' }}>
          <span style={{ fontWeight: '600', color: '#8892b0' }}>Status: </span>
          <span style={{ color: '#FFD700' }}>{overallStatus}</span>
          <span style={{ color: '#64748b' }}> - {statusDetail}</span>
        </div>
        
        <div style={{ borderTop: '1px solid rgba(255, 215, 0, 0.2)', paddingTop: '20px' }}>
          <style jsx global>{`
            th {
              background-color: #ff6b35 !important;
              color: white !important;
              padding: 8px !important;
            }
            td:first-child {
              background-color: #ff6b35 !important;
              color: white !important;
              font-weight: bold !important;
              padding: 8px !important;
            }
          `}</style>
          
          {[...agents].sort((a, b) => {
            if (a.status === 'active') return -1;
            if (b.status === 'active') return 1;
            return 0;
          }).map((agent, index) => (
            <div key={agent.name} style={{
              backgroundColor: agent.status === 'active' ? 'rgba(102, 126, 234, 0.1)' : 'rgba(255,255,255,0.05)',
              border: `1px solid ${agent.status === 'active' ? '#667eea' : 'rgba(255,255,255,0.1)'}`,
              borderRadius: '8px',
              padding: '12px',
              marginBottom: '5px',
              transition: 'all 0.3s ease'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', marginBottom: '8px' }}>
                <span style={{ fontSize: '1rem', marginRight: '5px' }}>{getAgentIcon(agent.name)}</span>
                <span style={{ 
                  fontWeight: '500', 
                  color: agent.status === 'active' ? '#667eea' : agent.status === 'complete' ? '#00d4aa' : '#8892b0',
                  minWidth: '140px'
                }}>
                  {agent.name}
                </span>
                {agent.currentTask && (
                  <span style={{ fontSize: '0.75rem', color: '#64748b', minWidth: '250px'}}>
                    - {agent.currentTask}
                  </span>
                )}
                <span style={{ 
                  marginLeft: 'auto', 
                  fontSize: '0.8rem', 
                  color: agent.status === 'active' ? '#667eea' : agent.status === 'complete' ? '#00d4aa' : '#64748b'
                }}>
                  {agent.status === 'active' ? 'ACTIVE' : agent.status === 'complete' ? 'COMPLETE' : 'IDLE'}
                </span>
              </div>
              
              {agent.content && agent.content.length > 0 && (
                <TokenRenderer 
                  content={agent.content} 
                  agentName={agent.name} 
                  isStreaming={agent.status === 'active'}
                />
              )}
                            
              <div style={{ 
                width: '100%', 
                height: '4px', 
                backgroundColor: 'rgba(255,255,255,0.1)', 
                borderRadius: '2px',
                marginTop: '8px'
              }}>
                <div style={{
                  width: `${agent.progress}%`,
                  height: '100%',
                  backgroundColor: agent.status === 'active' ? '#667eea' : agent.status === 'complete' ? '#00d4aa' : '#64748b',
                  borderRadius: '2px',
                  transition: 'width 0.3s ease'
                }} />
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}