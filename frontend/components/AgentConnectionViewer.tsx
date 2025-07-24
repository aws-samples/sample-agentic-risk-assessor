import React, { useState, useEffect } from 'react';

interface A2ACommunication {
  event: 'start' | 'end';
  from_agent: string;
  to_agent: string;
  message?: string;
  response?: string;
  timestamp: number;
}

interface AgentConnectionViewerProps {
  communications: A2ACommunication[];
}

const AgentConnectionViewer: React.FC<AgentConnectionViewerProps> = ({ communications }) => {
  const [activeConnections, setActiveConnections] = useState<Set<string>>(new Set());

  const agents = ['architect', 'risk_assessment', 'security_architect', 'auditor'];
  
  const getAgentPosition = (agent: string) => {
    const index = agents.indexOf(agent);
    const angle = (index * 2 * Math.PI) / agents.length;
    const radius = 120;
    return {
      x: 200 + radius * Math.cos(angle),
      y: 200 + radius * Math.sin(angle)
    };
  };

  useEffect(() => {
    const latest = communications[communications.length - 1];
    if (latest) {
      const connectionKey = `${latest.from_agent}-${latest.to_agent}`;
      
      if (latest.event === 'start') {
        setActiveConnections(prev => new Set(prev).add(connectionKey));
      } else if (latest.event === 'end') {
        setTimeout(() => {
          setActiveConnections(prev => {
            const newSet = new Set(prev);
            newSet.delete(connectionKey);
            return newSet;
          });
        }, 2000);
      }
    }
  }, [communications]);

  return (
    <div className="agent-connection-viewer">
      <svg width="400" height="400" className="connections-svg">
        {/* Agent nodes */}
        {agents.map(agent => {
          const pos = getAgentPosition(agent);
          return (
            <g key={agent}>
              <circle
                cx={pos.x}
                cy={pos.y}
                r="30"
                fill="#3b82f6"
                stroke="#1e40af"
                strokeWidth="2"
              />
              <text
                x={pos.x}
                y={pos.y + 5}
                textAnchor="middle"
                fill="white"
                fontSize="10"
                fontWeight="bold"
              >
                {agent.split('_')[0]}
              </text>
            </g>
          );
        })}
        
        {/* Active connections */}
        {Array.from(activeConnections).map(connectionKey => {
          const [from, to] = connectionKey.split('-');
          const fromPos = getAgentPosition(from);
          const toPos = getAgentPosition(to);
          
          return (
            <g key={connectionKey}>
              <line
                x1={fromPos.x}
                y1={fromPos.y}
                x2={toPos.x}
                y2={toPos.y}
                stroke="#ef4444"
                strokeWidth="3"
                className="animate-pulse"
              />
              <circle
                cx={fromPos.x + (toPos.x - fromPos.x) * 0.5}
                cy={fromPos.y + (toPos.y - fromPos.y) * 0.5}
                r="4"
                fill="#ef4444"
                className="animate-bounce"
              />
            </g>
          );
        })}
      </svg>
      
      {/* Communication log */}
      <div className="communication-log mt-4 max-h-32 overflow-y-auto">
        {communications.slice(-5).map((comm, index) => (
          <div key={index} className="text-xs text-gray-600 mb-1">
            <span className="font-semibold">{comm.from_agent}</span> → 
            <span className="font-semibold">{comm.to_agent}</span>: 
            {comm.event === 'start' ? comm.message : comm.response}
          </div>
        ))}
      </div>
      
      <style jsx>{`
        .agent-connection-viewer {
          border: 1px solid #e5e7eb;
          border-radius: 8px;
          padding: 16px;
          background: #f9fafb;
        }
        .connections-svg {
          display: block;
          margin: 0 auto;
        }
        .animate-pulse {
          animation: pulse 1s infinite;
        }
        .animate-bounce {
          animation: bounce 1s infinite;
        }
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.5; }
        }
        @keyframes bounce {
          0%, 100% { transform: translateY(0); }
          50% { transform: translateY(-4px); }
        }
      `}</style>
    </div>
  );
};

export default AgentConnectionViewer;