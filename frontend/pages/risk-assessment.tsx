// semgrep:ignore javascript.lang.security.audit.unsafe-formatstring.unsafe-formatstring: Console logging for debugging only, not user-facing
import { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/router';
import DiagramAnalysisTable from '../components/DiagramAnalysisTable';
import ZoomableDiagram from '../components/ZoomableDiagram';
import Sidebar from '../components/Sidebar';
import { getProjects, getProject, getDiagramAnalysis, analyzeDiagram, getProjectDocument, getProjectDocumentContent, uploadProjectDocument, getDiagramUrl, api } from '../utils/api';
import { saveArchitectureReview, getArchitectureReviews, downloadArchitectureReview } from '../utils/architecture-review-api';
import { saveRiskAssessment, getRiskAssessments, downloadRiskAssessment } from '../utils/api';
import { saveSecurityAssessment, getSecurityAssessments, downloadSecurityAssessment } from '../utils/security-assessment-api';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeRaw from 'rehype-raw';
import DocumentViewer from '../components/DocumentViewer';
import AssessmentFlow from './assessment-flow';
import markDownStyle from '../styles/markdownContent.module.css'
import logo from '../images/logo-risk.png';
import Image from 'next/image';
import { buildWebSocketUrl } from '../utils/websocket';

const agentTabs = [
  { id: 'architect', name: 'Architect Agent', description: 'Analyzes diagrams and identifies AWS components' },
  { id: 'security-architect', name: 'Security Architect Agent', description: 'Assigns controls to infrastructure nodes' },
  { id: 'risk-assessment', name: 'Risk Officer Agent', description: 'Calculates risk scores and identifies gaps' }
];

// Dynamic agent capabilities - fetched from backend
interface AgentCapability {
  name: string;
  message: string;
  tool_name?: string;
  description?: string;
}

type AgentCapabilities = {
  [key: string]: AgentCapability[];
};

interface MultipleChoiceQuestion {
  type: 'multiple_choice';
  question: string;
  options: Array<{ id: string; text: string; }>;
  questionNumber?: number;
  totalQuestions?: number;
  category?: string;
  priority?: string;
}

interface Message {
  role: string;
  content: string;
  multipleChoice?: MultipleChoiceQuestion;
  streaming?: boolean;
}

export default function DemoPageNew() {
  const router = useRouter();
  const [projects, setProjects] = useState<any[]>([]);
  const [selectedProject, setSelectedProject] = useState<string>('');
  const [selectedAgent, setSelectedAgent] = useState<string>('architect');
  
  // Agent-specific state objects
  const [agentMessages, setAgentMessages] = useState<{[key: string]: Message[]}>({});
  const [agentInputs, setAgentInputs] = useState<{[key: string]: string}>({});
  const [agentLoading, setAgentLoading] = useState<{[key: string]: boolean}>({});
  
  const [projectsLoading, setProjectsLoading] = useState(true);
  const [project, setProject] = useState<any>(null);
  const [diagramAnalysis, setDiagramAnalysis] = useState<any>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [projectDocument, setProjectDocument] = useState<any>(null);
  const [documentUploading, setDocumentUploading] = useState(false);
  const [diagramUrl, setDiagramUrl] = useState<string | null>(null);
  const [selectedTab, setSelectedTab] = useState<string>('document');
  const [rightTab, setRightTab] = useState<string>('nodes');
  const [architectureReview, setArchitectureReview] = useState<string>('');
  const [reviewLoading, setReviewLoading] = useState(false);
  const [architectureReviews, setArchitectureReviews] = useState<any[]>([]);
  const [riskAssessments, setRiskAssessments] = useState<any[]>([]);
  const [riskAssessmentContent, setRiskAssessmentContent] = useState<string>('');
  const [securityAssessments, setSecurityAssessments] = useState<any[]>([]);
  const [securityAssessmentContent, setSecurityAssessmentContent] = useState<string>('');
  const [selectedArchitectureReview, setSelectedArchitectureReview] = useState<string>('');
  const [selectedSecurityAssessment, setSelectedSecurityAssessment] = useState<string>('');
  const [selectedRiskAssessment, setSelectedRiskAssessment] = useState<string>('');
  const [savingReview, setSavingReview] = useState(false);
  const [progressMessage, setProgressMessage] = useState<string>('');
  const [showFullReview, setShowFullReview] = useState<string>('');
  const [progress, setProgress] = useState<number>(0);
  const wsRefs = useRef<{[key: string]: WebSocket | null}>({});
  
  // Expose wsRefs globally for context clearing utility
  useEffect(() => {
    (window as any).wsRefs = wsRefs;
    return () => {
      delete (window as any).wsRefs;
    };
  }, []);
  const chatAreaRef = useRef<HTMLDivElement | null>(null);
  const [tabContainerColor, setTabContainerColor] = useState<string>('#FFFFFF');
  const [showFlowModal, setShowFlowModal] = useState(false);
  const [showAssessmentDialog, setShowAssessmentDialog] = useState(false);
  const [activeChatTab, setActiveChatTab] = useState<number>(1);
  const [chatTabs, setChatTabs] = useState<{[key: number]: {messages: Message[], agent: string, sessionId?: string}}>({});
  const [showCapabilities, setShowCapabilities] = useState<boolean>(false);
  const [agentCapabilities, setAgentCapabilities] = useState<AgentCapabilities>({});
  const [sessionsLoading, setSessionsLoading] = useState<boolean>(false);

  // Fetch agent capabilities dynamically
  const fetchAgentCapabilities = async () => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/agent-capabilities`);
      if (response.ok) {
        const data = await response.json();
        setAgentCapabilities(data.capabilities || {});
      } else {
        console.error('Failed to fetch agent capabilities:', response.statusText);
        // Fallback to empty capabilities
        setAgentCapabilities({});
      }
    } catch (error) {
      console.error('Error fetching agent capabilities:', error);
      // Fallback to empty capabilities
      setAgentCapabilities({});
    }
  };

  // Fetch projects and capabilities on component mount
  useEffect(() => {
    const fetchProjects = async () => {
      try {
        const { data, error } = await getProjects();
        if (error) {
          console.error('Error fetching projects:', error);
        } else {
          setProjects(data || []);
          if (data && data.length > 0) {
            setSelectedProject(data[0].id);
          }
        }
      } catch (err) {
        console.error('Error in fetchProjects:', err);
      } finally {
        setProjectsLoading(false);
      }
    };
    
    fetchProjects();
    fetchAgentCapabilities();
  }, []);

  // Fetch project details when selected project changes
  useEffect(() => {
    if (selectedProject) {
      fetchProject();
      fetchDiagramAnalysis();
      fetchProjectDocument();
      fetchArchitectureReviews();
      fetchRiskAssessments();
      fetchSecurityAssessments();
      loadSessionChats();
    }
  }, [selectedProject]);

  const loadSessionChats = async () => {
    setSessionsLoading(true);
    try {
      const { getJwtToken } = await import('../utils/auth');
      const token = await getJwtToken();
      if (!token) return;

      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/sessions?t=${Date.now()}`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      if (response.ok) {
        const sessions = await response.json();
        console.log('✅ [LOAD] Total sessions:', sessions.length);
        
        // Log last_updated values
        console.log('🕒 [LOAD] Session timestamps:', sessions.map((s: any) => 
          `${s.session_id?.substring(0, 8)}: ${s.last_updated}`
        ));
        
        // Sort sessions: older first, newer last
        sessions.sort((a: any, b: any) => (a.last_updated || 0) - (b.last_updated || 0));
        
        console.log('🔄 [LOAD] After sort:', sessions.map((s: any) => 
          `${s.session_id?.substring(0, 8)}: ${s.last_updated}`
        ));
        
        // Create one tab per session
        const newChatTabs: {[key: number]: {messages: Message[], agent: string, sessionId?: string}} = {};
        let tabNum = 1;
        
        sessions.forEach((session: any) => {
          const agent = session.primary_agent || session.agent;
          if (!agent) return;
          
          // Filter and sort messages for this agent
          const agentMessages = (session.messages || [])
            .filter((msg: any) => msg.agent_id === agent && msg.content && msg.content.trim())
            .sort((a: any, b: any) => (a.message_id || 0) - (b.message_id || 0))
            .map((msg: any) => ({
              role: msg.role || 'user',
              content: msg.content || ''
            }));
          
          if (agentMessages.length > 0) {
            newChatTabs[tabNum] = {
              messages: agentMessages,
              agent,
              sessionId: session.session_id
            };
            console.log(`📋 [LOAD] Tab ${tabNum}: ${agent} session ${session.session_id?.substring(0, 8)} (${agentMessages.length} msgs, last_updated: ${session.last_updated})`);
            tabNum++;
          }
        });

        setChatTabs(newChatTabs);
        if (Object.keys(newChatTabs).length > 0) {
          setActiveChatTab(1);
          setSelectedAgent(newChatTabs[1].agent);
        }
      }
    } catch (error) {
      console.error('❌ [LOAD] Error:', error);
      setChatTabs({});
    } finally {
      setSessionsLoading(false);
    }
  };

  const loadAgentConversation = async (agentId: string, tabNum: number) => {
    console.log(`🔄 [SWITCH] Switching to agent ${agentId}`);
    setSelectedAgent(agentId);
    
    // Find first tab for this agent
    const agentTab = Object.entries(chatTabs).find(([_, tab]) => tab.agent === agentId);
    if (agentTab) {
      console.log(`✅ [SWITCH] Found tab ${agentTab[0]} for agent ${agentId}`);
      setActiveChatTab(parseInt(agentTab[0]));
    } else {
      console.log(`⚠️ [SWITCH] No existing tab for agent ${agentId}, keeping current tab ${activeChatTab}`);
      // Don't modify chatTabs - just keep the current tab active
      // The useEffect will handle updating the tab's agent if needed
    }
  };

  const fetchProject = async () => {
    try {
      const { data, error } = await getProject(selectedProject);
      if (!error && data) {
        setProject(data);
      }
    } catch (err) {
      console.error('Error fetching project:', err);
    }
  };

  const fetchDiagramAnalysis = async () => {
    try {
      const { data, error } = await getDiagramAnalysis(selectedProject);
      if (!error && data) {
        setDiagramAnalysis(data);
      }
    } catch (err) {
      console.error('Error fetching diagram analysis:', err);
    }
  };
  
  const fetchProjectDocument = async () => {
    try {
      const { data, error } = await getProjectDocument(selectedProject);
      if (!error && data) {
        const { data: contentData, error: contentError } = await getProjectDocumentContent(selectedProject);
        if (!contentError && contentData) {
          setProjectDocument({ ...data, content: contentData.content });
        } else {
          setProjectDocument(data);
        }
        
        if (data.diagram_filename) {
          const { data: diagramData, error: diagramError } = await getDiagramUrl(selectedProject);
          if (!diagramError && diagramData) {
            setDiagramUrl(diagramData.diagram_url);
          }
        } else if (data.diagram_url) {
          setDiagramUrl(data.diagram_url);
        }
      }
    } catch (err) {
      console.error('Error fetching project document:', err);
    }
  };
  
  const fetchArchitectureReviews = async () => {
    console.log('🔍 fetchArchitectureReviews called for project:', selectedProject);
    try {
      const { data, error } = await getArchitectureReviews(selectedProject);
      console.log('📊 Architecture reviews API response:', { data, error });
      if (!error && data) {
        setArchitectureReviews(data.assessments || []);
        console.log('📁 Reviews count:', data.assessments?.length || 0);
        if (data.assessments && data.assessments.length > 0) {
          const latestReview = data.assessments[0];
          console.log('🆕 Latest review ID:', latestReview.review_id);
          setSelectedArchitectureReview(latestReview.review_id);
          try {
            const { data: contentData } = await api.get(`/api/projects/${selectedProject}/architecture-reviews/${latestReview.review_id}/content`);
            console.log('📝 Content length:', contentData.content?.length || 0);
            setArchitectureReview(contentData.content);
            console.log('✅ Architecture review state updated');
          } catch (fetchError) {
            console.error('❌ Error fetching review content:', fetchError);
          }
        }
      }
    } catch (err) {
      console.error('❌ Error fetching architecture reviews:', err);
    }
  };

  const fetchRiskAssessments = async () => {
    console.log('🔍 fetchRiskAssessments called for project:', selectedProject);
    try {
      const { data, error } = await getRiskAssessments(selectedProject);
      console.log('📊 Risk assessments API response:', { data, error });
      if (error) {
        console.error('❌ Error from getRiskAssessments:', error);
        return;
      }
      
      if (data) {
        setRiskAssessments(data.assessments || []);
        console.log('📁 Assessments count:', data.assessments?.length || 0);
        if (data.assessments && data.assessments.length > 0) {
          const latestAssessment = data.assessments[0];
          console.log('🆕 Latest assessment ID:', latestAssessment.assessment_id);
          setSelectedRiskAssessment(latestAssessment.assessment_id);
          try {
            const { data: contentData } = await api.get(`/api/projects/${selectedProject}/risk-assessments/${latestAssessment.assessment_id}/content`);
            console.log('📝 Content length:', contentData.content?.length || 0);
            setRiskAssessmentContent(contentData.content);
            console.log('✅ Risk assessment state updated');
          } catch (fetchError) {
            console.error('❌ Error fetching risk assessment content:', fetchError);
          }
        } else {
          setRiskAssessmentContent('');
          setSelectedRiskAssessment('');
        }
      }
    } catch (err) {
      console.error('❌ Exception in fetchRiskAssessments:', err);
    }
  };

  const fetchSecurityAssessments = async () => {
    console.log('🔍 fetchSecurityAssessments called for project:', selectedProject);
    try {
      const { data, error } = await getSecurityAssessments(selectedProject);
      console.log('🔒 Security assessments API response:', { data, error });
      if (!error && data) {
        setSecurityAssessments(data.assessments || []);
        console.log('📁 Assessments count:', data.assessments?.length || 0);
        if (data.assessments && data.assessments.length > 0) {
          const latestAssessment = data.assessments[0];
          console.log('🆕 Latest assessment ID:', latestAssessment.assessment_id);
          setSelectedSecurityAssessment(latestAssessment.assessment_id);
          try {
            const { data: contentData } = await api.get(`/api/projects/${selectedProject}/security-assessments/${latestAssessment.assessment_id}/content`);
            console.log('📝 Content length:', contentData.content?.length || 0);
            setSecurityAssessmentContent(contentData.content);
            console.log('✅ Security assessment state updated');
          } catch (fetchError) {
            console.error('❌ Error fetching security assessment content:', fetchError);
          }
        }
      }
    } catch (err) {
      console.error('❌ Error fetching security assessments:', err);
    }
  };

  // Setup persistent WebSocket connections for all agents
  useEffect(() => {
    if (selectedProject) {
      const agents = ['architect', 'security-architect', 'risk-assessment'];
      
      agents.forEach(async agentId => {
        const { getJwtToken } = await import('../utils/auth');
        const token = await getJwtToken();
        const agentsUrl = process.env.NEXT_PUBLIC_AGENTS_URL;
        if (!agentsUrl) {
          console.error('NEXT_PUBLIC_AGENTS_URL environment variable not set');
          return;
        }
        
        const wsEndpoint = buildWebSocketUrl(agentsUrl, `/${agentId}/ws/chat`, token || undefined);
        const ws = new WebSocket(wsEndpoint);
        wsRefs.current[agentId] = ws;
        
        ws.onopen = () => {
          console.log(`WebSocket connected to ${agentId}`);
        };
        
        ws.onmessage = (event) => {
          const data = JSON.parse(event.data);
          const targetTab = data.tab_id || activeChatTab;
          
          // Universal refresh handler - check all message content for refresh signals
          const checkForRefreshSignals = (content: string) => {
            if (!content) return;
            
            if (content.includes('REFRESH_ARCHITECTURE_REVIEW')) {
              console.log('🔄 REFRESH_ARCHITECTURE_REVIEW signal received from', agentId);
              console.log('📋 Current selectedTab:', selectedTab);
              console.log('📄 Current architectureReview length:', architectureReview?.length || 0);
              fetchArchitectureReviews();
              fetchProjectDocument();
              console.log('✅ Refresh functions called');
            }
            
            if (content.includes('REFRESH_SECURITY_ASSESSMENT')) {
              console.log('🔄 REFRESH_SECURITY_ASSESSMENT signal received from', agentId);
              console.log('📋 Current selectedTab:', selectedTab);
              console.log('🔒 Current securityAssessmentContent length:', securityAssessmentContent?.length || 0);
              fetchSecurityAssessments();
              fetchProjectDocument();
              console.log('✅ Refresh functions called');
            }
            
            if (content.includes('REFRESH_RISK_ASSESSMENT') || content.includes('FSI risk assessment saved successfully')) {
              console.log('🔄 REFRESH_RISK_ASSESSMENT signal received from', agentId);
              console.log('📋 Current selectedTab:', selectedTab);
              console.log('📊 Current riskAssessmentContent length:', riskAssessmentContent?.length || 0);
              fetchRiskAssessments();
              fetchProjectDocument();
              console.log('✅ Refresh functions called');
            }
          };
          
          // Check all possible content fields
          checkForRefreshSignals(data.data);
          checkForRefreshSignals(data.response);
          checkForRefreshSignals(data.message);
          checkForRefreshSignals(data.content);
          
          // Handle streaming text chunks
          if (data.type === 'stream' && data.data) {
            setChatTabs(prev => {
              if (!targetTab || !prev[targetTab] || prev[targetTab].agent !== agentId) return prev;
              
              const currentMessages = prev[targetTab].messages || [];
              const lastMsg = currentMessages[currentMessages.length - 1];
              
              if (lastMsg && lastMsg.role === 'assistant' && lastMsg.streaming) {
                return {
                  ...prev,
                  [targetTab]: {
                    ...prev[targetTab],
                    messages: [...currentMessages.slice(0, -1), { ...lastMsg, content: lastMsg.content + data.data }]
                  }
                };
              } else {
                return {
                  ...prev,
                  [targetTab]: {
                    ...prev[targetTab],
                    messages: [...currentMessages, { role: 'assistant', content: data.data, streaming: true }]
                  }
                };
              }
            });
            return;
          }
          
          // Handle tool execution status
          if (data.type === 'tool') {
            setProgressMessage(`🔧 Using tool: ${data.tool}`);
            return;
          }
          
          // Handle completion
          if (data.type === 'complete') {
            setChatTabs(prev => {
              if (!targetTab || !prev[targetTab]) return prev;
              
              const currentMessages = prev[targetTab].messages || [];
              const lastMsg = currentMessages[currentMessages.length - 1];
              
              if (lastMsg && lastMsg.streaming) {
                return {
                  ...prev,
                  [targetTab]: {
                    ...prev[targetTab],
                    messages: [...currentMessages.slice(0, -1), { role: 'assistant', content: lastMsg.content }]
                  }
                };
              }
              return prev;
            });
            setAgentLoading(prev => ({ ...prev, [agentId]: false }));
            setProgressMessage('');
            setProgress(0);
            
            if (data.refresh_required) {
              fetchDiagramAnalysis();
              if (agentId === 'risk-assessment') {
                fetchRiskAssessments();
              }
            }
            
            // Check for refresh messages in completion data
            if (data.message && data.message.includes('REFRESH_ARCHITECTURE_REVIEW')) {
              fetchArchitectureReviews();
              fetchProjectDocument();
            }
            
            if (data.message && data.message.includes('REFRESH_SECURITY_ASSESSMENT')) {
              fetchSecurityAssessments();
              fetchProjectDocument();
            }
            
            if (data.message && (data.message.includes('REFRESH_RISK_ASSESSMENT') || data.message.includes('FSI risk assessment saved successfully'))) {
              fetchRiskAssessments();
              fetchProjectDocument();
            }
            
            return;
          }
          
          // Handle progress updates
          if (data.status === 'progress') {
            setProgressMessage(data.message);
            setProgress(data.progress || 0);
            return;
          }
          
          if (data.response) {
            let message: Message = { role: 'assistant', content: data.response };
            if (data.multipleChoice) {
              message.multipleChoice = data.multipleChoice;
            }
            setChatTabs(prev => {
              if (!targetTab || !prev[targetTab]) return prev;
              
              return {
                ...prev,
                [targetTab]: {
                  ...prev[targetTab],
                  messages: [...(prev[targetTab]?.messages || []), message]
                }
              };
            });
            setAgentLoading(prev => ({ ...prev, [agentId]: false }));
            setProgressMessage('');
            setProgress(0);
            
            if (data.refresh_required) {
              fetchDiagramAnalysis();
              if (agentId === 'risk-assessment') {
                fetchRiskAssessments();
              }
            }
            
            // Handle refresh messages from any agent
            if (data.response && data.response.includes('REFRESH_ARCHITECTURE_REVIEW')) {
              fetchArchitectureReviews();
              fetchProjectDocument();
            }
            
            if (data.response && data.response.includes('REFRESH_SECURITY_ASSESSMENT')) {
              fetchSecurityAssessments();
              fetchProjectDocument();
            }
            
            if (data.response && (data.response.includes('REFRESH_RISK_ASSESSMENT') || data.response.includes('FSI risk assessment saved successfully'))) {
              fetchRiskAssessments();
              fetchProjectDocument();
            }
          }
        };
        
        ws.onerror = (error) => {
          // nosemgrep
          console.error(`WebSocket error with ${agentId}:`, error);
          // Show error in active tab for this agent
          const activeTabForAgent = Object.keys(chatTabs).find(k => chatTabs[parseInt(k)].agent === agentId);
          if (activeTabForAgent) {
            setChatTabs(prev => ({
              ...prev,
              [parseInt(activeTabForAgent)]: {
                ...prev[parseInt(activeTabForAgent)],
                messages: [...(prev[parseInt(activeTabForAgent)]?.messages || []), { role: 'assistant', content: `Connection error to ${agentId}` }]
              }
            }));
          }
          setAgentLoading(prev => ({ ...prev, [agentId]: false }));
        };
      });
      
      return () => {
        agents.forEach(agentId => {
          const ws = wsRefs.current[agentId];
          if (ws && ws.readyState === WebSocket.OPEN) {
            ws.close();
          }
        });
        wsRefs.current = {};
      };
    }
  }, [selectedProject]);

  const sendMessage = async () => {
    const currentAgent = chatTabs[activeChatTab]?.agent || 'architect';
    const currentInput = agentInputs[currentAgent] || '';
    const currentTab = chatTabs[activeChatTab];
    if (!currentInput.trim() || !currentAgent || !wsRefs.current[currentAgent] || !selectedProject) return;
    
    const ws = wsRefs.current[currentAgent];
    if (ws.readyState !== WebSocket.OPEN) {
      setChatTabs(prev => ({
        ...prev,
        [activeChatTab]: {
          ...prev[activeChatTab],
          messages: [...(prev[activeChatTab]?.messages || []), { role: 'assistant', content: 'Connection not ready. Please try again.' }]
        }
      }));
      return;
    }

    // Get or create session ID for this tab
    let sessionId = currentTab?.sessionId;
    if (!sessionId) {
      // Create new session via backend API
      try {
        const { getJwtToken } = await import('../utils/auth');
        const token = await getJwtToken();
        const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/sessions/create`, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            project_id: selectedProject,
            agent_id: currentAgent
          })
        });
        
        if (response.ok) {
          const sessionData = await response.json();
          sessionId = sessionData.session_id;
          setChatTabs(prev => ({
            ...prev,
            [activeChatTab]: {
              ...prev[activeChatTab],
              sessionId
            }
          }));
        } else {
          console.error('Failed to create session');
          return;
        }
      } catch (error) {
        console.error('Error creating session:', error);
        return;
      }
    }

    let contextualMessage = `Project: ${selectedProject} - ${currentInput}`;
    if (projectDocument && projectDocument.document_name) {
      contextualMessage = `Project: ${selectedProject} - Document: ${projectDocument.document_name} - ${currentInput}`;
    }
    
    const userMessage: Message = { role: 'user', content: currentInput };
    setChatTabs(prev => ({
      ...prev,
      [activeChatTab]: {
        ...prev[activeChatTab],
        messages: [...(prev[activeChatTab]?.messages || []), userMessage]
      }
    }));
    setAgentLoading(prev => ({ ...prev, [currentAgent]: true }));
    
    ws.send(JSON.stringify({
      message: contextualMessage,
      agent: currentAgent,
      document_context: projectDocument ? true : false,
      tab_id: activeChatTab,
      session_id: sessionId
    }));
    
    setAgentInputs(prev => ({ ...prev, [currentAgent]: '' }));
  };

  const handleAgentChange = (agentId: string) => {
    setSelectedAgent(agentId);
  };

  const handleProjectChange = async (projectId: string) => {
    // Clear agent contexts when switching projects
    try {
      const { clearAgentContexts } = await import('../utils/agent-context');
      await clearAgentContexts();
    } catch (error) {
      console.warn('Failed to clear agent contexts:', error);
    }
    
    setSelectedProject(projectId);
    setAgentMessages({});
    setAgentInputs({});
    setAgentLoading({});
    setProject(null);
    setDiagramAnalysis(null);
    setProjectDocument(null);
    setDiagramUrl(null);
    setArchitectureReview('');
    setArchitectureReviews([]);
    setSelectedArchitectureReview('');
    setRiskAssessments([]);
    setRiskAssessmentContent('');
    setSelectedRiskAssessment('');
    setSecurityAssessments([]);
    setSecurityAssessmentContent('');
    setSelectedSecurityAssessment('');
    setChatTabs({1: {messages: [], agent: 'architect'}});
    setActiveChatTab(1);
  };

  // Update tab container color based on selected tab
  useEffect(() => {
    if (selectedTab === 'architecture') {
      setTabContainerColor('#f2fbffff');
    } else if (selectedTab === 'security') {
      setTabContainerColor('#fff3efff');
    } else if (selectedTab === 'risk') {
      setTabContainerColor('#e1ffdfa3');
    } else if (selectedTab === 'document') {
      setTabContainerColor('#FFFFFF');
    }
  }, [selectedTab]);

  // Update active chat tab when agent changes
  useEffect(() => {
    const agentTabs = Object.keys(chatTabs).filter(k => chatTabs[parseInt(k)].agent === selectedAgent).map(k => parseInt(k));
    const currentTabAgent = chatTabs[activeChatTab]?.agent;
    
    console.log(`🔄 [EFFECT] Agent changed to ${selectedAgent}, available tabs:`, agentTabs, 'current active:', activeChatTab, 'current tab agent:', currentTabAgent);
    
    // If current tab doesn't match selected agent
    if (currentTabAgent !== selectedAgent) {
      if (agentTabs.length > 0) {
        // Switch to first tab for this agent
        const newActiveTab = Math.min(...agentTabs);
        console.log(`✅ [EFFECT] Switching to tab ${newActiveTab} for agent ${selectedAgent}`);
        setActiveChatTab(newActiveTab);
      } else {
        // No tabs for this agent, create a NEW tab instead of reusing current one
        const existingTabNums = Object.keys(chatTabs).map(k => parseInt(k));
        const newTabNum = existingTabNums.length > 0 ? Math.max(...existingTabNums) + 1 : 1;
        console.log(`📝 [EFFECT] No tabs for agent ${selectedAgent}, creating new tab ${newTabNum}`);
        setChatTabs(prev => ({
          ...prev,
          [newTabNum]: {
            messages: [],
            agent: selectedAgent
          }
        }));
        setActiveChatTab(newTabNum);
      }
    }
  }, [selectedAgent, activeChatTab]);

  // Close capabilities dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (showCapabilities) {
        setShowCapabilities(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [showCapabilities]);

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    if (chatAreaRef.current) {
      chatAreaRef.current.scrollTop = chatAreaRef.current.scrollHeight;
    }
  }, [chatTabs[activeChatTab]?.messages, activeChatTab]);

  return (
    <div style={{ 
      fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
      backgroundColor: '#e4e4e4',
      color: '#000000',
      lineHeight: 1.6,
      height: '100vh',
      display: 'flex'
    }}>
      <Sidebar activePage="risk-assessment" startCollapsed={true} />

      {/* Main Area */}
      <div style={{ flex: 1, padding: '1rem', overflow: 'hidden' }}>
        {/* Project Selection */}
        <div style={{ display: 'flex', flex: 1, color: '#000000', padding: '0.5rem', marginBottom: '0.5rem' }}>
          <label htmlFor="project-select" style={{ marginRight: '1rem', fontWeight: '600', color: '#ff6b35', fontSize: '1.25rem' }}>Select Project:</label>
          {projectsLoading ? (
            <span>Loading projects...</span>
          ) : (
            <select
              id="project-select"
              value={selectedProject}
              onChange={(e) => handleProjectChange(e.target.value)}
              disabled={projects.length === 0}
              style={{
                backgroundColor: '#ffffffff',
                color: '#000000',
                border: '1px solid #ff6b35',
                padding: '0.5rem',
                borderRadius: '4px',
                fontSize: '0.9rem'
              }}
            >
              {projects.length === 0 ? (
                <option value="">No projects available</option>
              ) : (
                projects.map(project => (
                  <option key={project.id} value={project.id}>
                    {project.name}{project.profile_id ? ' 🏢' : ''}
                  </option>
                ))
              )}
            </select>
          )}

          <button 
            onClick={() => setShowAssessmentDialog(true)}
            disabled={reviewLoading || !projectDocument}
            style={{ 
              fontSize: '1rem', 
              padding: '0.5rem 1rem',
              backgroundColor: '#ff6b35',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              marginLeft: 'auto',
              cursor: reviewLoading || !projectDocument ? 'not-allowed' : 'pointer',
              opacity: reviewLoading || !projectDocument ? 0.6 : 1
            }}
          >
            {reviewLoading ? 'Reviewing...' : '🔍 Start Risk Assessment'}
          </button>
        </div>

        {/* Content Layout */}
        <div style={{ display: 'flex', height: 'calc(100vh - 100px)', width: '100%' }}>
          {/* Document Section */}
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
            {/* Document Tabs */}
            <div style={{
              display: 'flex',
              marginBottom: '-2px',
              zIndex: 10,
              position: 'relative'
            }}>
              {[
                { id: 'document', name: '📄 Original Document' },
                { id: 'architecture', name: '🏗️ Architecture Assessment' },
                { id: 'security', name: '🔒 Security Assessment' },
                { id: 'risk', name: '📊 Risk Assessment' }
              ].map(tab => (
                <div
                  key={tab.id}
                  onClick={async () => {
                    if (sessionsLoading) return; // Prevent tab switching while loading
                    console.log(`🔖 [TAB CLICK] User clicked on tab: ${tab.name}`);
                    setSelectedTab(tab.id);
                    
                    // Update chat agent and load conversation when switching to assessment tabs
                    if (tab.id === 'architecture') {
                      const newAgent = 'architect';
                      console.log(`🔄 [TAB CLICK] Switching to agent: ${newAgent}`);
                      setSelectedAgent(newAgent);
                      console.log(`⏳ [TAB CLICK] Loading conversation for ${newAgent} in tab ${activeChatTab}`);
                      await loadAgentConversation(newAgent, activeChatTab);
                      console.log(`✅ [TAB CLICK] Conversation loaded for ${newAgent}`);
                    } else if (tab.id === 'security') {
                      const newAgent = 'security-architect';
                      console.log(`🔄 [TAB CLICK] Switching to agent: ${newAgent}`);
                      setSelectedAgent(newAgent);
                      console.log(`⏳ [TAB CLICK] Loading conversation for ${newAgent} in tab ${activeChatTab}`);
                      await loadAgentConversation(newAgent, activeChatTab);
                      console.log(`✅ [TAB CLICK] Conversation loaded for ${newAgent}`);
                    } else if (tab.id === 'risk') {
                      const newAgent = 'risk-assessment';
                      console.log(`🔄 [TAB CLICK] Switching to agent: ${newAgent}`);
                      setSelectedAgent(newAgent);
                      console.log(`⏳ [TAB CLICK] Loading conversation for ${newAgent} in tab ${activeChatTab}`);
                      await loadAgentConversation(newAgent, activeChatTab);
                      console.log(`✅ [TAB CLICK] Conversation loaded for ${newAgent}`);
                    }
                  }}
                  style={{
                    backgroundColor: selectedTab === tab.id ? tabContainerColor : '#e6e6e6ff',
                    color: '#2a2a2a',
                    border: '2px solid #ff6b35',
                    borderBottom: selectedTab === tab.id ? '2px solid ' + tabContainerColor : 'none',
                    padding: '0.5rem 0.75rem',
                    cursor: sessionsLoading ? 'not-allowed' : 'pointer',
                    opacity: sessionsLoading ? 0.6 : 1,
                    fontSize: '0.8rem',
                    borderTopLeftRadius: '8px',
                    borderTopRightRadius: '8px',
                    marginRight: '2px',
                    zIndex: selectedTab === tab.id ? 11 : 10,
                    whiteSpace: 'nowrap'
                  }}
                >
                  {tab.name}
                </div>
              ))}
            </div>
            
            <div style={{
              backgroundColor: tabContainerColor,
              border: '2px solid #ff6b35',
              borderRadius: '8px',
              borderTopLeftRadius: 0,
              padding: '1.5rem',
              overflow: 'hidden',
              flex: "1",
              display: 'flex',
              flexDirection: 'column'
            }}>
              {selectedTab === 'document' && (
                <>
                  {diagramUrl && (
                    <div style={{
                      marginBottom: '1rem',
                      backgroundColor: '#f8f8f8',
                      border: '1px solid #ddd',
                      borderRadius: '4px',
                      padding: '1rem',
                      textAlign: 'center'
                    }}>
                      <h4 style={{ color: '#ff6b35', marginBottom: '0.5rem', fontSize: '0.9rem' }}>📊 Architecture Diagram</h4>
                      <img 
                        src={diagramUrl} 
                        alt="Architecture Diagram" 
                        style={{
                          maxWidth: '100%',
                          maxHeight: '200px',
                          objectFit: 'contain',
                          border: '1px solid #ddd',
                          borderRadius: '4px'
                        }}
                      />
                    </div>
                  )}
                  
                  <div style={{
                    flex: 1,
                    backgroundColor: '#f8f8f8',
                    border: '1px solid #ddd',
                    borderRadius: '4px',
                    padding: '1.5rem',
                    overflowY: 'auto',
                    fontSize: '0.9rem',
                    lineHeight: 1.6,
                    color: '#333'
                  }}>
                    {projectDocument ? (
                      <div>
                        <h2 style={{ color: '#ff6b35', marginBottom: '1rem' }}>{projectDocument.document_name}</h2>
                        {projectDocument.document_name?.endsWith('.docx') && projectDocument.document_url ? (
                          <DocumentViewer 
                            documentUrl={projectDocument.document_url} 
                            fileName={projectDocument.document_name}
                            content={projectDocument.content}
                          />
                        ) : (
                          <div className={markDownStyle['markdown-content']}>
                            <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeRaw]}
                              components={{
                                img: ({node, ...props}) => {
                                  const src = props.src || '';
                                  const imageUrl = src && !src.includes('/') && !src.startsWith('http') 
                                    ? `${process.env.NEXT_PUBLIC_API_URL}/api/images/${src}`
                                    : src;
                                  return (
                                    <div style={{maxWidth: '100%', height: '300px'}}>
                                      <ZoomableDiagram 
                                        src={imageUrl} 
                                        alt={props.alt || 'Document Image'}
                                      />
                                    </div>
                                  );
                                }
                              }}
                            >
                              {projectDocument.content || 'Document content not available'}
                            </ReactMarkdown>
                          </div>
                        )}
                      </div>
                    ) : (
                      <div style={{ textAlign: 'center', color: '#666', fontStyle: 'italic' }}>
                        No document available for this project
                      </div>
                    )}
                  </div>
                </>
              )}
              
              {(selectedTab === 'architecture' || selectedTab === 'security' || selectedTab === 'risk') && (
                <div style={{ height: '100%', display: 'flex', flex: "1", flexDirection: 'row' }}>
                  <div style={{ display: 'flex', flex: 1, flexDirection: 'column', width: '50%', marginRight: '0.5rem', overflowY: 'auto'}}>
                    <div style={{ display: 'flex', marginBottom: '0.5rem' }}>
                      <div style={{ color: '#ff6b35', fontSize: '1rem', fontWeight: '600', width: '100%', display: 'flex'}}>
                        {selectedTab === 'architecture' && 'Architecture Review Result Versions: '}
                        {selectedTab === 'security' && 'Security Assessment Result Versions: '}
                        {selectedTab === 'risk' && 'Risk Assessment Result Versions: '}
                        
                        {selectedTab === 'architecture' && (
                          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                            {architectureReviews.length > 0 ? (
                              <select 
                                value={selectedArchitectureReview}
                                onChange={async (e) => {
                                  setSelectedArchitectureReview(e.target.value);
                                  try {
                                    const { data: contentData } = await api.get(`/api/projects/${selectedProject}/architecture-reviews/${e.target.value}/content`);
                                    setArchitectureReview(contentData.content);
                                  } catch (error) {
                                    console.error('Error loading review content:', error);
                                  }
                                }}
                                style={{
                                  padding: '0.25rem 0.25rem',
                                  border: '1px solid #ff6b35',
                                  borderRadius: '4px',
                                  fontSize: '0.8rem',
                                  color: '#2a2a2a',
                                  marginLeft: '10px',
                                  backgroundColor: 'white'
                                }}
                              >
                                {architectureReviews.map((review, index) => (
                                  <option key={review.review_id} value={review.review_id}>{index === 0 ? '🆕' : '📄'} v{review.version}</option>
                                ))}
                              </select>
                            ) : (
                              <div style={{ fontSize: '1rem', color: '#2a2a2a', marginLeft: '10px'}}>No versions created yet</div>
                            )}
                            <button 
                              onClick={async () => {
                                if (!selectedProject) return;
                                
                                const ws = wsRefs.current['architect'];
                                if (ws && ws.readyState === WebSocket.OPEN) {
                                  // Get or create session ID like chat box does
                                  let sessionId = chatTabs[activeChatTab]?.sessionId;
                                  if (!sessionId) {
                                    try {
                                      const { getJwtToken } = await import('../utils/auth');
                                      const token = await getJwtToken();
                                      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/sessions/create`, {
                                        method: 'POST',
                                        headers: {
                                          'Authorization': `Bearer ${token}`,
                                          'Content-Type': 'application/json'
                                        },
                                        body: JSON.stringify({
                                          project_id: selectedProject,
                                          agent_id: 'architect'
                                        })
                                      });
                                      
                                      if (response.ok) {
                                        const sessionData = await response.json();
                                        sessionId = sessionData.session_id;
                                        setChatTabs(prev => ({
                                          ...prev,
                                          [activeChatTab]: {
                                            ...prev[activeChatTab],
                                            sessionId
                                          }
                                        }));
                                      }
                                    } catch (error) {
                                      console.error('Error creating session:', error);
                                    }
                                  }
                                  
                                  // Send message with proper project context like normal chat messages
                                  let contextualMessage = `Project: ${selectedProject} - perform_architecture_assessment`;
                                  if (projectDocument && projectDocument.document_name) {
                                    contextualMessage = `Project: ${selectedProject} - Document: ${projectDocument.document_name} - perform_architecture_assessment`;
                                  }
                                  
                                  // Add user message to chat
                                  setAgentMessages(prev => ({
                                    ...prev,
                                    ['architect']: [...(prev['architect'] || []), { role: 'user', content: 'Start Architecture Review' }]
                                  }));
                                  setAgentLoading(prev => ({ ...prev, ['architect']: true }));
                                  
                                  ws.send(JSON.stringify({
                                    message: contextualMessage,
                                    agent: 'architect',
                                    document_context: projectDocument ? true : false,
                                    session_id: sessionId
                                  }));
                                } else {
                                  setAgentMessages(prev => ({
                                    ...prev,
                                    ['architect']: [...(prev['architect'] || []), { role: 'assistant', content: 'Connection to architect agent not available.' }]
                                  }));
                                }
                              }}
                              disabled={reviewLoading || !selectedProject}
                              style={{ 
                                fontSize: '0.7rem', 
                                padding: '0.3rem 0.8rem',
                                backgroundColor: '#ff6b35',
                                color: 'white',
                                border: 'none',
                                borderRadius: '4px',
                                cursor: reviewLoading || !selectedProject ? 'not-allowed' : 'pointer',
                                opacity: reviewLoading || !selectedProject ? 0.6 : 1
                              }}
                            >
                              {reviewLoading ? 'Reviewing...' : '🔍 New Architecture Review'}
                            </button>
                          </div>
                        )}
                        
                        {selectedTab === 'security' && (
                          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                            {securityAssessments.length > 0 ? (
                              <select 
                                value={selectedSecurityAssessment}
                                onChange={async (e) => {
                                  setSelectedSecurityAssessment(e.target.value);
                                  try {
                                    const { data: contentData } = await api.get(`/api/projects/${selectedProject}/security-assessments/${e.target.value}/content`);
                                    setSecurityAssessmentContent(contentData.content);
                                  } catch (error) {
                                    console.error('Error loading assessment content:', error);
                                  }
                                }}
                                style={{
                                  padding: '0.25rem 0.25rem',
                                  border: '1px solid #ff6b35',
                                  borderRadius: '4px',
                                  fontSize: '0.8rem',
                                  color: '#2a2a2a',
                                  backgroundColor: 'white',
                                  marginLeft: '10px'
                                }}
                              >
                                {securityAssessments.map((assessment, index) => (
                                  <option key={assessment.assessment_id} value={assessment.assessment_id}>{index === 0 ? '🆕' : '📄'} v{assessment.version}</option>
                                ))}
                              </select>
                            ) : (
                              <div style={{ marginLeft: '10px', fontSize: '1rem', color: '#2a2a2a'}}>No versions created yet</div>
                            )}
                            <button 
                              onClick={async () => {
                                if (!selectedProject) return;
                                
                                const ws = wsRefs.current['security-architect'];
                                if (ws && ws.readyState === WebSocket.OPEN) {
                                  // Get or create session ID like chat box does
                                  let sessionId = chatTabs[activeChatTab]?.sessionId;
                                  if (!sessionId) {
                                    try {
                                      const { getJwtToken } = await import('../utils/auth');
                                      const token = await getJwtToken();
                                      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/sessions/create`, {
                                        method: 'POST',
                                        headers: {
                                          'Authorization': `Bearer ${token}`,
                                          'Content-Type': 'application/json'
                                        },
                                        body: JSON.stringify({
                                          project_id: selectedProject,
                                          agent_id: 'security-architect'
                                        })
                                      });
                                      
                                      if (response.ok) {
                                        const sessionData = await response.json();
                                        sessionId = sessionData.session_id;
                                        setChatTabs(prev => ({
                                          ...prev,
                                          [activeChatTab]: {
                                            ...prev[activeChatTab],
                                            sessionId
                                          }
                                        }));
                                      }
                                    } catch (error) {
                                      console.error('Error creating session:', error);
                                    }
                                  }
                                  
                                  // Send message with proper project context like normal chat messages
                                  let contextualMessage = `Project: ${selectedProject} - perform_security_assessment`;
                                  if (projectDocument && projectDocument.document_name) {
                                    contextualMessage = `Project: ${selectedProject} - Document: ${projectDocument.document_name} - perform_security_assessment`;
                                  }
                                  
                                  // Add user message to chat
                                  setAgentMessages(prev => ({
                                    ...prev,
                                    ['security-architect']: [...(prev['security-architect'] || []), { role: 'user', content: 'Start Security Review' }]
                                  }));
                                  setAgentLoading(prev => ({ ...prev, ['security-architect']: true }));
                                  
                                  ws.send(JSON.stringify({
                                    message: contextualMessage,
                                    agent: 'security-architect',
                                    document_context: projectDocument ? true : false,
                                    session_id: sessionId
                                  }));
                                } else {
                                  setAgentMessages(prev => ({
                                    ...prev,
                                    ['security-architect']: [...(prev['security-architect'] || []), { role: 'assistant', content: 'Connection to security architect agent not available.' }]
                                  }));
                                }
                              }}
                              disabled={reviewLoading || !selectedProject}
                              style={{ 
                                fontSize: '0.7rem', 
                                padding: '0.3rem 0.8rem',
                                backgroundColor: '#ff6b35',
                                color: 'white',
                                border: 'none',
                                borderRadius: '4px',
                                cursor: reviewLoading || !selectedProject ? 'not-allowed' : 'pointer',
                                opacity: reviewLoading || !selectedProject ? 0.6 : 1
                              }}
                            >
                              {reviewLoading ? 'Reviewing...' : '🔍 New Security Review'}
                            </button>
                          </div>                          
                        )}
                        
                        {selectedTab === 'risk' && (
                          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                            {riskAssessments.length > 0 ? (
                              <select 
                                value={selectedRiskAssessment}
                                onChange={async (e) => {
                                  setSelectedRiskAssessment(e.target.value);
                                  try {
                                    const { data: contentData } = await api.get(`/api/projects/${selectedProject}/risk-assessments/${e.target.value}/content`);
                                    setRiskAssessmentContent(contentData.content);
                                  } catch (error) {
                                    console.error('Error loading assessment content:', error);
                                  }
                                }}
                                style={{
                                  padding: '0.25rem 0.25rem',
                                  border: '1px solid #ff6b35',
                                  borderRadius: '4px',
                                  fontSize: '0.8rem',
                                  color: '#2a2a2a',
                                  backgroundColor: 'white',
                                  marginLeft: '10px'
                                }}
                              >
                                {riskAssessments.map((assessment, index) => (
                                  <option key={assessment.assessment_id} value={assessment.assessment_id}>{index === 0 ? '🆕' : '📄'} v{assessment.version}</option>
                                ))}
                              </select>
                            ) : (
                              <div style={{ marginLeft: '10px', fontSize: '1rem', color: '#2a2a2a'}}>No versions created yet</div>
                            )}
                            <button 
                              onClick={async () => {
                                if (!selectedProject) return;
                                
                                const ws = wsRefs.current['risk-assessment'];
                                if (ws && ws.readyState === WebSocket.OPEN) {
                                  // Get or create session ID like chat box does
                                  let sessionId = chatTabs[activeChatTab]?.sessionId;
                                  if (!sessionId) {
                                    try {
                                      const { getJwtToken } = await import('../utils/auth');
                                      const token = await getJwtToken();
                                      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/sessions/create`, {
                                        method: 'POST',
                                        headers: {
                                          'Authorization': `Bearer ${token}`,
                                          'Content-Type': 'application/json'
                                        },
                                        body: JSON.stringify({
                                          project_id: selectedProject,
                                          agent_id: 'risk-assessment'
                                        })
                                      });
                                      
                                      if (response.ok) {
                                        const sessionData = await response.json();
                                        sessionId = sessionData.session_id;
                                        setChatTabs(prev => ({
                                          ...prev,
                                          [activeChatTab]: {
                                            ...prev[activeChatTab],
                                            sessionId
                                          }
                                        }));
                                      }
                                    } catch (error) {
                                      console.error('Error creating session:', error);
                                    }
                                  }
                                  
                                  // Send message with proper project context like normal chat messages
                                  let contextualMessage = `Project: ${selectedProject} - perform_risk_assessment`;
                                  if (projectDocument && projectDocument.document_name) {
                                    contextualMessage = `Project: ${selectedProject} - Document: ${projectDocument.document_name} - perform_risk_assessment`;
                                  }
                                  
                                  // Add user message to chat
                                  setAgentMessages(prev => ({
                                    ...prev,
                                    ['risk-assessment']: [...(prev['risk-assessment'] || []), { role: 'user', content: 'Start Risk Review' }]
                                  }));
                                  setAgentLoading(prev => ({ ...prev, ['risk-assessment']: true }));
                                  
                                  ws.send(JSON.stringify({
                                    message: contextualMessage,
                                    agent: 'risk-assessment',
                                    document_context: projectDocument ? true : false,
                                    session_id: sessionId
                                  }));
                                } else {
                                  setAgentMessages(prev => ({
                                    ...prev,
                                    ['risk-assessment']: [...(prev['risk-assessment'] || []), { role: 'assistant', content: 'Connection to risk assessment agent not available.' }]
                                  }));
                                }
                              }}
                              disabled={reviewLoading || !selectedProject}
                              style={{ 
                                fontSize: '0.7rem', 
                                padding: '0.3rem 0.8rem',
                                backgroundColor: '#ff6b35',
                                color: 'white',
                                border: 'none',
                                borderRadius: '4px',
                                cursor: reviewLoading || !selectedProject ? 'not-allowed' : 'pointer',
                                opacity: reviewLoading || !selectedProject ? 0.6 : 1
                              }}
                            >
                              {reviewLoading ? 'Reviewing...' : '🔍 New Risk Review'}
                            </button>
                          </div>                          
                          )}
                      </div>
                    </div>

                    <div style={{ 
                      flex: "1",
                      backgroundColor: '#f0f0f0',
                      border: '1px solid #ff6b35',
                      borderRadius: '4px',
                      padding: '0.5rem',
                      overflowY: 'auto',
                      fontSize: '0.8rem',
                      lineHeight: 1.4
                    }}>
                      {selectedTab === 'architecture' ? (
                        architectureReview ? (
                          <div className={markDownStyle['markdown-content']}>
                            <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeRaw]}>
                              {architectureReview}
                            </ReactMarkdown>
                          </div>
                        ) : (
                          <div style={{ fontStyle: 'italic', color: '#666' }}>
                            No architecture review results yet. Use the chat to generate a review.
                          </div>
                        )
                      ) : selectedTab === 'risk' ? (
                        riskAssessmentContent ? (
                          <div className={markDownStyle['markdown-content']}>
                            <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeRaw]}>
                              {riskAssessmentContent}
                            </ReactMarkdown>
                          </div>
                        ) : (
                          <div style={{ fontStyle: 'italic', color: '#666' }}>
                            No risk assessment results yet. Use the chat to generate an assessment.
                          </div>
                        )
                      ) : selectedTab === 'security' ? (
                        securityAssessmentContent ? (
                          <div className={markDownStyle['markdown-content']}>
                            <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeRaw]}>
                              {securityAssessmentContent}
                            </ReactMarkdown>
                          </div>
                        ) : (
                          <div style={{ fontStyle: 'italic', color: '#666' }}>
                            No security assessment results yet. Use the chat to generate an assessment.
                          </div>
                        )
                      ) : (
                        <div style={{ fontStyle: 'italic', color: '#666' }}>
                          No assessment results yet. Use the chat to generate an assessment.
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Chat Section */}
                  <div style={{ display: 'flex', flex: 1, flexDirection: 'column', width: '50%', marginLeft: '0.5rem', minHeight: 0, height:'100%' }}>
                    <div style={{ color: '#ff6b35', marginBottom: '0.5rem', fontSize: '1rem', fontWeight: '600', display: 'flex', alignItems: 'center', gap: '0.5rem', width: '100%', justifyContent: 'space-between'}}>
                      <div>
                        Chat with: 
                        <select 
                          value={chatTabs[activeChatTab]?.agent || 'architect'} 
                          disabled={sessionsLoading}
                          onChange={async (e) => {
                            const newAgent = e.target.value;
                            const oldAgent = chatTabs[activeChatTab]?.agent;
                            console.log(`🔄 [USER ACTION] Agent dropdown changed from ${oldAgent} to ${newAgent} in tab ${activeChatTab}`);
                            setSelectedAgent(newAgent);
                            
                            // Update the current tab to use the new agent and load its conversation
                            console.log(`⏳ [USER ACTION] Initiating agent conversation load...`);
                            await loadAgentConversation(newAgent, activeChatTab);
                            console.log(`✅ [USER ACTION] Agent conversation load completed for ${newAgent}`);
                            
                            // Force a re-render by updating the tab container color based on agent
                            if (newAgent === 'architect') {
                              console.log(`🎨 [USER ACTION] Switching to architecture tab`);
                              setSelectedTab('architecture');
                            } else if (newAgent === 'security-architect') {
                              console.log(`🎨 [USER ACTION] Switching to security tab`);
                              setSelectedTab('security');
                            } else if (newAgent === 'risk-assessment') {
                              console.log(`🎨 [USER ACTION] Switching to risk tab`);
                              setSelectedTab('risk');
                            }
                          }}
                          style={{
                            padding: '0.25rem 0.5rem',
                            border: '1px solid #ff6b35',
                            borderRadius: '4px',
                            fontSize: '0.9rem',
                            color: '#2a2a2a',
                            backgroundColor: 'white',
                            marginLeft: '10px'
                          }}
                        >
                          {agentTabs.map(agent => (
                            <option key={agent.id} value={agent.id}>{agent.name}</option>
                          ))}
                        </select>
                      </div>
                      <button 
                        onClick={async () => {
                          if (!selectedProject || !selectedAgent) return;
                          
                          const ws = wsRefs.current[selectedAgent];
                          if (ws && ws.readyState === WebSocket.OPEN) {
                            // Get or create session ID like chat box does
                            let sessionId = chatTabs[activeChatTab]?.sessionId;
                            if (!sessionId) {
                              try {
                                const { getJwtToken } = await import('../utils/auth');
                                const token = await getJwtToken();
                                const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/sessions/create`, {
                                  method: 'POST',
                                  headers: {
                                    'Authorization': `Bearer ${token}`,
                                    'Content-Type': 'application/json'
                                  },
                                  body: JSON.stringify({
                                    project_id: selectedProject,
                                    agent_id: selectedAgent
                                  })
                                });
                                
                                if (response.ok) {
                                  const sessionData = await response.json();
                                  sessionId = sessionData.session_id;
                                  setChatTabs(prev => ({
                                    ...prev,
                                    [activeChatTab]: {
                                      ...prev[activeChatTab],
                                      sessionId
                                    }
                                  }));
                                }
                              } catch (error) {
                                console.error('Error creating session:', error);
                              }
                            }
                            
                            // Send triage message with proper project context
                            let contextualMessage = `Project: ${selectedProject} - triage assessment`;
                            if (projectDocument && projectDocument.document_name) {
                              contextualMessage = `Project: ${selectedProject} - Document: ${projectDocument.document_name} - triage assessment`;
                            }
                            
                            // Add user message to chat
                            setAgentMessages(prev => ({
                              ...prev,
                              [selectedAgent]: [...(prev[selectedAgent] || []), { role: 'user', content: 'Start Triage Assessment' }]
                            }));
                            setAgentLoading(prev => ({ ...prev, [selectedAgent]: true }));
                            
                            ws.send(JSON.stringify({
                              message: contextualMessage,
                              agent: selectedAgent,
                              document_context: projectDocument ? true : false,
                              session_id: sessionId
                            }));
                          } else {
                            setAgentMessages(prev => ({
                              ...prev,
                              [selectedAgent]: [...(prev[selectedAgent] || []), { role: 'assistant', content: `Connection to ${selectedAgent} agent not available.` }]
                            }));
                          }
                        }}
                        disabled={reviewLoading || !selectedProject || !selectedAgent}
                        style={{ 
                          fontSize: '0.7rem', 
                          padding: '0.3rem 0.8rem',
                          backgroundColor: '#ff6b35',
                          color: 'white',
                          border: 'none',
                          borderRadius: '4px',
                          cursor: reviewLoading || !selectedProject || !selectedAgent ? 'not-allowed' : 'pointer',
                          opacity: reviewLoading || !selectedProject || !selectedAgent ? 0.6 : 1,
                          textAlign: 'right'
                        }}
                      >
                        {'🔍 Agent Triage'}
                      </button>
                    </div>
                    
                    {/* Chat Tabs - Only show tabs for the currently selected agent */}
                    <div style={{ display: 'flex', marginBottom: '0.5rem', alignItems: 'center' }}>
                      {Object.keys(chatTabs).filter(tabKey => chatTabs[parseInt(tabKey)].agent === selectedAgent).map((tabKey, index) => {
                        const tabNum = parseInt(tabKey);
                        const tab = chatTabs[tabNum];
                        const agentTabs = Object.keys(chatTabs).filter(k => chatTabs[parseInt(k)].agent === selectedAgent);
                        const tabLabel = agentTabs.length > 1 ? `Chat ${index + 1}` : 'Chat';
                        return (
                          <div
                            key={tabNum}
                            onClick={() => {
                              setActiveChatTab(tabNum);
                            }}
                            style={{
                              padding: '0.25rem 0.5rem',
                              backgroundColor: activeChatTab === tabNum ? '#ff6b35' : '#f0f0f0',
                              color: activeChatTab === tabNum ? 'white' : '#666',
                              border: '1px solid #ff6b35',
                              borderRadius: '4px',
                              marginRight: '0.25rem',
                              cursor: 'pointer',
                              fontSize: '0.75rem',
                              fontWeight: '600'
                            }}
                          >
                            {tabLabel}
                            <span
                              onClick={async (e) => {
                                e.stopPropagation();
                                const agentTabs = Object.keys(chatTabs).filter(k => chatTabs[parseInt(k)].agent === selectedAgent);
                                if (agentTabs.length > 1) {
                                  // Create custom dialog with three options
                                  const result = await new Promise<'delete' | 'close' | 'cancel'>((resolve) => {
                                    const dialog = document.createElement('div');
                                    dialog.style.cssText = `
                                      position: fixed; top: 0; left: 0; width: 100%; height: 100%; 
                                      background: rgba(0,0,0,0.5); display: flex; align-items: center; 
                                      justify-content: center; z-index: 1000;
                                    `;
                                    
                                    dialog.innerHTML = `
                                      <div style="background: white; padding: 2rem; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.3); max-width: 400px;">
                                        <h3 style="margin: 0 0 1rem 0; color: #333;">Close Chat Tab</h3>
                                        <p style="margin: 0 0 1.5rem 0; color: #666;">What would you like to do with this chat?</p>
                                        <div style="display: flex; gap: 0.5rem; justify-content: flex-end;">
                                          <button id="cancel-btn" style="padding: 0.5rem 1rem; border: 1px solid #ccc; background: white; border-radius: 4px; cursor: pointer;">Cancel</button>
                                          <button id="close-btn" style="padding: 0.5rem 1rem; border: 1px solid #ff6b35; background: white; color: #ff6b35; border-radius: 4px; cursor: pointer;">Only Close</button>
                                          <button id="delete-btn" style="padding: 0.5rem 1rem; border: none; background: #ff6b35; color: white; border-radius: 4px; cursor: pointer;">Close & Delete</button>
                                        </div>
                                      </div>
                                    `;
                                    
                                    document.body.appendChild(dialog);
                                    
                                    dialog.querySelector('#cancel-btn')?.addEventListener('click', () => {
                                      document.body.removeChild(dialog);
                                      resolve('cancel');
                                    });
                                    
                                    dialog.querySelector('#close-btn')?.addEventListener('click', () => {
                                      document.body.removeChild(dialog);
                                      resolve('close');
                                    });
                                    
                                    dialog.querySelector('#delete-btn')?.addEventListener('click', () => {
                                      document.body.removeChild(dialog);
                                      resolve('delete');
                                    });
                                  });
                                  
                                  if (result === 'cancel') {
                                    return; // Do nothing
                                  }
                                  
                                  if (result === 'delete') {
                                    // Delete from DynamoDB
                                    try {
                                      const { getJwtToken } = await import('../utils/auth');
                                      const token = await getJwtToken();
                                      const sessionId = chatTabs[tabNum]?.sessionId;
                                      
                                      const { validatePathParam } = await import('../utils/validatePathParam');
                                      await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/sessions/${validatePathParam(sessionId, 'sessionId')}`, {
                                        method: 'DELETE',
                                        headers: {
                                          'Authorization': `Bearer ${token}`,
                                          'Content-Type': 'application/json'
                                        }
                                      });
                                    } catch (error) {
                                      console.error('Error deleting session:', error);
                                    }
                                  }
                                  
                                  // Remove tab from UI (for both 'close' and 'delete')
                                  const newTabs = { ...chatTabs };
                                  delete newTabs[tabNum];
                                  setChatTabs(newTabs);
                                  if (activeChatTab === tabNum) {
                                    const remainingAgentTabs = Object.keys(newTabs).filter(k => newTabs[parseInt(k)].agent === selectedAgent).map(k => parseInt(k));
                                    if (remainingAgentTabs.length > 0) {
                                      setActiveChatTab(Math.min(...remainingAgentTabs));
                                    }
                                  }
                                }
                              }}
                              style={{
                                marginLeft: '0.5rem',
                                cursor: 'pointer',
                                fontSize: '0.8rem',
                                opacity: Object.keys(chatTabs).filter(k => chatTabs[parseInt(k)].agent === selectedAgent).length > 1 ? 1 : 0.3
                              }}
                            >
                              ×
                            </span>
                          </div>
                        );
                      })}
                      <button
                        onClick={async () => {
                          const existingTabNums = Object.keys(chatTabs).map(k => parseInt(k));
                          const newTabNum = existingTabNums.length > 0 ? Math.max(...existingTabNums) + 1 : 1;
                          
                          // Create new session via backend API
                          try {
                            const { getJwtToken } = await import('../utils/auth');
                            const token = await getJwtToken();
                            const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/sessions/create`, {
                              method: 'POST',
                              headers: {
                                'Authorization': `Bearer ${token}`,
                                'Content-Type': 'application/json'
                              },
                              body: JSON.stringify({
                                project_id: selectedProject,
                                agent_id: selectedAgent
                              })
                            });
                            
                            if (response.ok) {
                              const sessionData = await response.json();
                              setChatTabs(prev => ({
                                ...prev,
                                [newTabNum]: { 
                                  messages: [], 
                                  agent: selectedAgent,
                                  sessionId: sessionData.session_id
                                }
                              }));
                              setActiveChatTab(newTabNum);
                            } else {
                              console.error('Failed to create new chat session');
                            }
                          } catch (error) {
                            console.error('Error creating new chat session:', error);
                          }
                        }}
                        style={{
                          padding: '0.25rem 0.5rem',
                          backgroundColor: '#e0e0e0',
                          color: '#666',
                          border: '1px solid #ccc',
                          borderRadius: '4px',
                          cursor: 'pointer',
                          fontSize: '0.75rem'
                        }}
                      >
                        + New Chat
                      </button>
                    </div>
                    
                    {/* Chat Area */}
                    <div 
                      ref={chatAreaRef}
                      key={`chat-${activeChatTab}-${chatTabs[activeChatTab]?.agent}`} // Force re-render when tab or agent changes
                      style={{
                        display: 'flex',
                        flex: 1,
                        flexDirection: 'column',
                        backgroundColor: '#f0f0f0',
                        border: '1px solid #ff6b35',
                        borderRadius: '4px',
                        padding: '1rem',
                        marginBottom: '1rem',
                        overflowY: 'auto',
                        minHeight: 0
                      }}>
                      {(() => {
                        const currentTab = chatTabs[activeChatTab];
                        const messageCount = currentTab?.messages?.length || 0;
                        console.log(`🎨 [RENDER] Rendering chat area for tab ${activeChatTab}, agent: ${currentTab?.agent}, messages: ${messageCount}`);
                        return null;
                      })()}
                      {(chatTabs[activeChatTab]?.messages || []).length === 0 && (
                        <div style={{ fontStyle: 'italic', color: '#ccc' }}>
                          Chat with {agentTabs.find(a => a.id === chatTabs[activeChatTab]?.agent)?.name}...
                        </div>
                      )}
                      
                      {(chatTabs[activeChatTab]?.messages || []).map((msg, idx) => (
                        <div key={idx} style={{
                          marginBottom: '.75rem',
                          padding: '0.5rem',
                          borderRadius: '8px',
                          fontSize: '0.9rem',
                          backgroundColor: msg.role === 'user' ? '#ff6b35' : '#dededeff',
                          color: msg.role === 'user' ? '#ffffff' : '#000000',
                          marginLeft: msg.role === 'user' ? '2rem' : '0',
                          marginRight: msg.role === 'user' ? '0' : '2rem'
                        }}>
                          <div style={{ lineHeight: '1.5'}}>
                            <strong>{msg.role === 'user' ? 'You ' : 'Agent '}:</strong>
                            <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
                          </div>
                          
                          {msg.multipleChoice && (
                            <div style={{ marginTop: '1rem' }}>
                              {msg.multipleChoice.questionNumber && (
                                <div style={{ fontSize: '0.7rem', color: '#ccc', marginBottom: '6px' }}>
                                  Question {msg.multipleChoice.questionNumber} of {msg.multipleChoice.totalQuestions}
                                  {msg.multipleChoice.category && ` • ${msg.multipleChoice.category}`}
                                  {msg.multipleChoice.priority && ` • Priority: ${msg.multipleChoice.priority}`}
                                </div>
                              )}
                              <div style={{
                                fontWeight: 'bold',
                                marginBottom: '8px',
                                fontSize: '0.85rem',
                                color: '#fff'
                              }}>
                                {msg.multipleChoice.question}
                              </div>
                              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                                {msg.multipleChoice.options.map((option) => (
                                  <button
                                    key={option.id}
                                    onClick={() => {
                                      const ws = wsRefs.current[selectedAgent];
                                      if (ws && ws.readyState === WebSocket.OPEN) {
                                        const contextualMessage = `Project: ${selectedProject} - Document: ${projectDocument?.document_name || 'N/A'} - ${option.text}`;
                                        setAgentMessages(prev => ({
                                          ...prev,
                                          [selectedAgent]: [...(prev[selectedAgent] || []), { role: 'user', content: option.text }]
                                        }));
                                        setAgentLoading(prev => ({ ...prev, [selectedAgent]: true }));
                                        
                                        ws.send(JSON.stringify({
                                          message: contextualMessage,
                                          agent: selectedAgent
                                        }));
                                      }
                                    }}
                                    style={{
                                      padding: '6px 10px',
                                      backgroundColor: '#ff6b35',
                                      color: 'white',
                                      border: 'none',
                                      borderRadius: '4px',
                                      cursor: 'pointer',
                                      fontSize: '0.75rem',
                                      fontWeight: '500'
                                    }}
                                  >
                                    {option.text}
                                  </button>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      ))}
                      {agentLoading[chatTabs[activeChatTab]?.agent] && <div style={{ fontStyle: 'italic', color: '#ccc' }}>Thinking...</div>}
                    </div>

                    {/* Chat Input */}
                    <div style={{ display: 'flex', gap: '0.5rem', position: 'relative' }}>
                      <input
                        type="text"
                        value={agentInputs[chatTabs[activeChatTab]?.agent] || ''}
                        onChange={(e) => setAgentInputs(prev => ({ ...prev, [chatTabs[activeChatTab]?.agent]: e.target.value }))}
                        onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
                        placeholder="Type your message..."
                        style={{
                          flex: 1,
                          backgroundColor: '#f0f0f0',
                          color: '#000000',
                          border: '1px solid #ff6b35',
                          padding: '0.75rem',
                          borderRadius: '4px',
                          fontSize: '0.9rem'
                        }}
                      />
                      <div style={{ position: 'relative' }}>
                        <button
                          onClick={() => setShowCapabilities(!showCapabilities)}
                          style={{
                            backgroundColor: '#e0e0e0',
                            color: '#666',
                            border: '1px solid #ccc',
                            padding: '0.75rem 0.5rem',
                            borderRadius: '4px 0 0 4px',
                            cursor: 'pointer',
                            fontSize: '0.9rem',
                            borderRight: 'none'
                          }}
                        >
                          🛠️
                        </button>
                        {showCapabilities && (
                          <div style={{
                            position: 'absolute',
                            bottom: '100%',
                            right: 0,
                            backgroundColor: 'white',
                            border: '1px solid #ccc',
                            borderRadius: '4px',
                            boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
                            zIndex: 1000,
                            minWidth: '200px',
                            marginBottom: '5px'
                          }}>
                            {agentCapabilities[chatTabs[activeChatTab]?.agent]?.map((capability, index) => (
                              <div
                                key={index}
                                onMouseDown={(e) => {
                                  e.preventDefault();
                                  const currentAgent = chatTabs[activeChatTab]?.agent || 'architect';
                                  const message = capability.message || capability.name || 'Unknown capability';
                                  console.log('🛠️ Capability clicked:', capability.name, 'Message:', message);
                                  setAgentInputs(prev => ({ ...prev, [currentAgent]: message }));
                                  setShowCapabilities(false);
                                }}
                                style={{
                                  padding: '0.5rem 0.75rem',
                                  cursor: 'pointer',
                                  borderBottom: index < agentCapabilities[chatTabs[activeChatTab]?.agent].length - 1 ? '1px solid #eee' : 'none',
                                  fontSize: '0.85rem',
                                  color: '#333'
                                }}
                                onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#f5f5f5'}
                                onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'white'}
                              >
                                {capability.name}
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                      <button
                        onClick={sendMessage}
                        disabled={agentLoading[chatTabs[activeChatTab]?.agent] || !(agentInputs[chatTabs[activeChatTab]?.agent] || '').trim() || !selectedProject}
                        style={{
                          backgroundColor: '#ff6b35',
                          color: '#ffffff',
                          border: 'none',
                          padding: '0.75rem 1.5rem',
                          borderRadius: '0 4px 4px 0',
                          cursor: agentLoading[chatTabs[activeChatTab]?.agent] || !(agentInputs[chatTabs[activeChatTab]?.agent] || '').trim() || !selectedProject ? 'not-allowed' : 'pointer',
                          fontSize: '0.9rem',
                          opacity: agentLoading[chatTabs[activeChatTab]?.agent] || !(agentInputs[chatTabs[activeChatTab]?.agent] || '').trim() || !selectedProject ? 0.6 : 1
                        }}
                      >
                        Send
                      </button>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
      {showAssessmentDialog && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          width: '100vw',
          height: '100vh',
          zIndex: 9999,
          backgroundColor: 'rgba(0,0,0,0.5)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center'
        }}>
          <div style={{
            backgroundColor: 'white',
            padding: '2rem',
            borderRadius: '8px',
            boxShadow: '0 4px 20px rgba(0,0,0,0.3)',
            maxWidth: '400px',
            width: '90%'
          }}>
            <h3 style={{ color: '#ff6b35', marginBottom: '1rem', textAlign: 'center' }}>Choose Assessment Type</h3>
            <p style={{ color: '#666', marginBottom: '1.5rem', textAlign: 'center', fontSize: '0.9rem' }}>
              Select the type of risk assessment you'd like to perform:
            </p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <button
                onClick={async () => {
                  setShowAssessmentDialog(false);
                  setShowFlowModal(true);
                  setSelectedAgent('risk-assessment');
                  
                  const sendMessage = async () => {
                    const ws = wsRefs.current['risk-assessment'];
                    if (ws && ws.readyState === WebSocket.OPEN) {
                      // Get or create session ID like chat box does
                      let sessionId = chatTabs[activeChatTab]?.sessionId;
                      if (!sessionId) {
                        try {
                          const { getJwtToken } = await import('../utils/auth');
                          const token = await getJwtToken();
                          const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/sessions/create`, {
                            method: 'POST',
                            headers: {
                              'Authorization': `Bearer ${token}`,
                              'Content-Type': 'application/json'
                            },
                            body: JSON.stringify({
                              project_id: selectedProject,
                              agent_id: 'risk-assessment'
                            })
                          });
                          
                          if (response.ok) {
                            const sessionData = await response.json();
                            sessionId = sessionData.session_id;
                            setChatTabs(prev => ({
                              ...prev,
                              [activeChatTab]: {
                                ...prev[activeChatTab],
                                sessionId
                              }
                            }));
                          }
                        } catch (error) {
                          console.error('Error creating session:', error);
                        }
                      }
                      
                      const message = { 
                        message: `perform_demo_risk_assessment ${selectedProject} FSI`, 
                        agent: 'risk-assessment',
                        project_id: selectedProject,
                        session_id: sessionId
                      };
                      setAgentMessages(prev => ({
                        ...prev,
                        ['risk-assessment']: [...(prev['risk-assessment'] || []), { role: 'user', content: 'Start Demo Risk Assessment' }]
                      }));
                      setAgentLoading(prev => ({ ...prev, ['risk-assessment']: true }));
                      ws.send(JSON.stringify(message));
                    } else {
                      setTimeout(sendMessage, 100);
                    }
                  };
                  setTimeout(sendMessage, 100);
                }}
                style={{
                  padding: '1rem',
                  backgroundColor: '#4CAF50',
                  color: 'white',
                  border: 'none',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  fontSize: '1rem',
                  fontWeight: '500'
                }}
              >
                ⚡ Demo Assessment
                <div style={{ fontSize: '0.8rem', opacity: 0.9, marginTop: '0.25rem' }}>
                  Fast demo with token limits (~1 minute)
                </div>
              </button>
              {/* <button
                onClick={() => {
                  setShowAssessmentDialog(false);
                  setShowFlowModal(true);
                  setSelectedAgent('risk-assessment');
                  
                  const sendMessage = () => {
                    const ws = wsRefs.current['risk-assessment'];
                    if (ws && ws.readyState === WebSocket.OPEN) {
                      const message = { 
                        message: `perform_full_risk_assessment ${selectedProject} FSI is_quick=true`, 
                        agent: 'risk-assessment',
                        project_id: selectedProject
                      };
                      setAgentMessages(prev => ({
                        ...prev,
                        ['risk-assessment']: [...(prev['risk-assessment'] || []), { role: 'user', content: 'Start Quick Risk Assessment' }]
                      }));
                      setAgentLoading(prev => ({ ...prev, ['risk-assessment']: true }));
                      ws.send(JSON.stringify(message));
                    } else {
                      setTimeout(sendMessage, 100);
                    }
                  };
                  setTimeout(sendMessage, 100);
                }}
                style={{
                  padding: '1rem',
                  backgroundColor: '#4CAF50',
                  color: 'white',
                  border: 'none',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  fontSize: '1rem',
                  fontWeight: '500'
                }}
              >
                ⚡ Quick Assessment
                <div style={{ fontSize: '0.8rem', opacity: 0.9, marginTop: '0.25rem' }}>
                  Condensed risk analysis with key findings
                </div>
              </button> */}
              <button
                onClick={async () => {
                  setShowAssessmentDialog(false);
                  setShowFlowModal(true);
                  setSelectedAgent('risk-assessment');
                  
                  const sendMessage = async () => {
                    const ws = wsRefs.current['risk-assessment'];
                    if (ws && ws.readyState === WebSocket.OPEN) {
                      // Get or create session ID like chat box does
                      let sessionId = chatTabs[activeChatTab]?.sessionId;
                      if (!sessionId) {
                        try {
                          const { getJwtToken } = await import('../utils/auth');
                          const token = await getJwtToken();
                          const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/sessions/create`, {
                            method: 'POST',
                            headers: {
                              'Authorization': `Bearer ${token}`,
                              'Content-Type': 'application/json'
                            },
                            body: JSON.stringify({
                              project_id: selectedProject,
                              agent_id: 'risk-assessment'
                            })
                          });
                          
                          if (response.ok) {
                            const sessionData = await response.json();
                            sessionId = sessionData.session_id;
                            setChatTabs(prev => ({
                              ...prev,
                              [activeChatTab]: {
                                ...prev[activeChatTab],
                                sessionId
                              }
                            }));
                          }
                        } catch (error) {
                          console.error('Error creating session:', error);
                        }
                      }
                      
                      const message = { 
                        message: `perform_full_risk_assessment ${selectedProject} FSI`, 
                        agent: 'risk-assessment',
                        project_id: selectedProject,
                        session_id: sessionId
                      };
                      setAgentMessages(prev => ({
                        ...prev,
                        ['risk-assessment']: [...(prev['risk-assessment'] || []), { role: 'user', content: 'Start Full Risk Assessment' }]
                      }));
                      setAgentLoading(prev => ({ ...prev, ['risk-assessment']: true }));
                      ws.send(JSON.stringify(message));
                    } else {
                      setTimeout(sendMessage, 100);
                    }
                  };
                  setTimeout(sendMessage, 100);
                }}
                style={{
                  padding: '1rem',
                  backgroundColor: '#ff6b35',
                  color: 'white',
                  border: 'none',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  fontSize: '1rem',
                  fontWeight: '500'
                }}
              >
                📊 Full Assessment
                <div style={{ fontSize: '0.8rem', opacity: 0.9, marginTop: '0.25rem' }}>
                  Comprehensive analysis with detailed matrices
                </div>
              </button>
              <button
                onClick={() => {
                  setShowAssessmentDialog(false);
                  setShowFlowModal(true);
                }}
                style={{
                  padding: '1rem',
                  backgroundColor: '#6c757d',
                  color: 'white',
                  border: 'none',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  fontSize: '1rem',
                  fontWeight: '500'
                }}
              >
                👁️ Monitor Current Assessment
                <div style={{ fontSize: '0.8rem', opacity: 0.9, marginTop: '0.25rem' }}>
                  View progress of ongoing assessment
                </div>
              </button>
            </div>
            <button
              onClick={() => setShowAssessmentDialog(false)}
              style={{
                marginTop: '1rem',
                width: '100%',
                padding: '0.5rem',
                backgroundColor: 'transparent',
                color: '#666',
                border: '1px solid #ddd',
                borderRadius: '4px',
                cursor: 'pointer',
                fontSize: '0.9rem'
              }}
            >
              Cancel
            </button>
          </div>
        </div>
      )}
      {showFlowModal && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          width: '100vw',
          height: '100vh',
          zIndex: 9999,
          backgroundColor: 'rgba(0,0,0,0.4)'
        }}>
          <AssessmentFlow projectId={selectedProject} framework="FSI" />
          <button
            onClick={() => setShowFlowModal(false)}
            style={{
              position: 'absolute',
              top: '20px',
              right: '20px',
              background: 'rgba(159, 157, 157, 0.62)',
              color: 'white',
              border: '2px solid white',
              borderRadius: '50%',
              width: '50px',
              height: '50px',
              cursor: 'pointer',
              fontSize: '1.5rem',
              zIndex: 10000
            }}
          >
            ×
          </button>
        </div>
      )}
    </div>
  );
}