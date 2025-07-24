import React, { useState, useEffect, useRef } from 'react';
import styles from '../styles/FullReview.module.css';

interface StepData {
  agent: string;
  label: string;
  icon: string;
}

export default function FullReviewAnimation() {
  const [currentStep, setCurrentStep] = useState(-1);
  const [isRunning, setIsRunning] = useState(false);
  const isRunningRef = useRef(false);
  const [statusText, setStatusText] = useState('Ready to start');
  const [statusDetail, setStatusDetail] = useState('Click start to begin automated security analysis');
  const [agentStates, setAgentStates] = useState({
    supervisor: { active: false, completed: false, progress: 0 },
    architect: { active: false, completed: false, progress: 0 },
    security: { active: false, completed: false, progress: 0 },
    risk: { active: false, completed: false, progress: 0 }
  });

  const totalSteps = 15;
  const stepData: StepData[] = [
    { agent: 'supervisor', label: 'Initializing workflow', icon: '🚀' },
    { agent: 'supervisor', label: 'Orchestrating agents', icon: '🎯' },
    { agent: 'supervisor', label: 'Monitoring progress', icon: '📊' },
    { agent: 'architect', label: 'Analyzing diagram', icon: '📊' },
    { agent: 'architect', label: 'Assessing architecture', icon: '🏗️' },
    { agent: 'architect', label: 'Asking clarifying questions', icon: '❓' },
    { agent: 'architect', label: 'Finalizing assessment', icon: '✅' },
    { agent: 'security', label: 'Loading controls', icon: '📚' },
    { agent: 'security', label: 'Mapping services', icon: '🔗' },
    { agent: 'security', label: 'Setting priorities', icon: '⚡' },
    { agent: 'security', label: 'Validating', icon: '✅' },
    { agent: 'risk', label: 'Analyzing coverage', icon: '🔍' },
    { agent: 'risk', label: 'Scoring risks', icon: '📊' },
    { agent: 'risk', label: 'Finding gaps', icon: '🚨' },
    { agent: 'risk', label: 'Generating report', icon: '📄' }
  ];

  useEffect(() => {
    createParticles();
  }, []);

  const createParticles = () => {
    const container = document.getElementById('particles');
    if (!container) return;
    
    for (let i = 0; i < 20; i++) {
      const particle = document.createElement('div');
      particle.className = styles.particle;
      particle.style.left = Math.random() * 100 + '%';
      particle.style.animationDelay = Math.random() * 8 + 's';
      particle.style.animationDuration = (Math.random() * 4 + 6) + 's';
      container.appendChild(particle);
    }
  };

  const updateProgress = (agent: string, progress: number) => {
    const radius = agent === 'supervisor' ? 22 : 18;
    const circumference = 2 * Math.PI * radius;
    const offset = circumference - (progress / 100) * circumference;
    
    const circle = document.getElementById(`${agent}-progress`);
    if (circle) {
      circle.style.strokeDasharray = circumference.toString();
      circle.style.strokeDashoffset = offset.toString();
    }
  };

  const getCurrentStepForAgent = (agent: string) => {
    if (currentStep < 0) return null;
    const step = stepData[currentStep];
    return step?.agent === agent ? step : null;
  };

  const updateStep = (stepIndex: number) => {
    if (stepIndex < 0 || stepIndex >= totalSteps) return;
    
    const step = stepData[stepIndex];
    const agentSteps = stepData.filter(s => s.agent === step.agent);
    const agentStepIndex = agentSteps.findIndex(s => s === step);
    const agentProgress = ((agentStepIndex + 1) / agentSteps.length) * 100;
    
    setStatusText(step.label);
    setStatusDetail(`Processing ${step.icon}`);
    
    setAgentStates(prev => {
      const newStates = { ...prev };
      
      // Reset all to inactive
      Object.keys(newStates).forEach(key => {
        newStates[key as keyof typeof newStates] = { ...newStates[key as keyof typeof newStates], active: false };
      });
      
      // Set current agent as active
      if (stepIndex >= 0 && stepIndex <= 2) {
        newStates.supervisor = { ...newStates.supervisor, active: true, progress: agentProgress };
      } else if (stepIndex >= 3 && stepIndex <= 6) {
        if (stepIndex === 3) newStates.supervisor.completed = true;
        newStates.architect = { ...newStates.architect, active: true, progress: agentProgress };
      } else if (stepIndex >= 7 && stepIndex <= 10) {
        if (stepIndex === 7) newStates.architect.completed = true;
        newStates.security = { ...newStates.security, active: true, progress: agentProgress };
      } else if (stepIndex >= 11 && stepIndex <= 14) {
        if (stepIndex === 11) newStates.security.completed = true;
        newStates.risk = { ...newStates.risk, active: true, progress: agentProgress };
      }
      
      return newStates;
    });
    
    updateProgress(step.agent, agentProgress);
  };

  const startWorkflow = async () => {
    if (isRunningRef.current) return;
    
    setIsRunning(true);
    isRunningRef.current = true;
    
    for (let i = 0; i < totalSteps; i++) {
      if (!isRunningRef.current) break;
      
      setCurrentStep(i);
      updateStep(i);
      
      await new Promise(resolve => setTimeout(resolve, Math.random() * 1500 + 2000));
    }
    
    if (isRunningRef.current) {
      setAgentStates(prev => ({ ...prev, risk: { ...prev.risk, completed: true, active: false } }));
      setStatusText('🎉 Assessment Complete');
      setStatusDetail('Risk analysis ready for review');
    }
    
    setIsRunning(false);
    isRunningRef.current = false;
  };

  const resetWorkflow = () => {
    setIsRunning(false);
    isRunningRef.current = false;
    setCurrentStep(-1);
    setStatusText('Ready to start');
    setStatusDetail('Click start to begin automated security analysis');
    
    setAgentStates({
      supervisor: { active: false, completed: false, progress: 0 },
      architect: { active: false, completed: false, progress: 0 },
      security: { active: false, completed: false, progress: 0 },
      risk: { active: false, completed: false, progress: 0 }
    });
    
    ['supervisor', 'architect', 'security', 'risk'].forEach(agent => {
      updateProgress(agent, 0);
    });
  };

  const getStatusOverlayClass = () => {
    if (currentStep >= 3 && currentStep <= 6) return styles.toArchitect;
    if (currentStep >= 7 && currentStep <= 10) return styles.toSecurity;
    if (currentStep >= 11 && currentStep <= 14) return styles.toRisk;
    return '';
  };

  return (
    <div className={styles.container} style={{
      width: 'calc(100vw - 200px)',
      height: 'calc(100vh - 200px)',
      margin: '100px',
      borderRadius: '20px',
      border: '2px solid rgba(255, 215, 0, 0.5)',
      boxShadow: '0 20px 60px rgba(0, 0, 0, 0)'
    }}>
      <div className={styles.floatingParticles} id="particles" />
      
      <div className={`${styles.statusOverlay} ${getStatusOverlayClass()}`}>
        <div className={styles.statusText}>{statusText}</div>
        <div className={styles.statusDetail}>{statusDetail}</div>
      </div>
      
      <div className={`${styles.supervisorCard} ${agentStates.supervisor.active ? styles.active : ''} ${agentStates.supervisor.completed ? styles.completed : ''}`}>
        <div className={styles.supervisorIcon}>🎯</div>
        <div>
          <div className={styles.supervisorTitle}>Supervisor</div>
          <div className={styles.supervisorSubtitle}>
            {getCurrentStepForAgent('supervisor')?.label || 'Orchestrating Workflow'}
          </div>
        </div>
        <svg className={styles.progressRing} style={{ top: '-5px', right: '-5px', width: '50px', height: '50px' }}>
          <circle className={styles.progressRingCircle} cx="25" cy="25" r="22" strokeWidth="4"/>
          <circle className={`${styles.progressRingProgress} ${styles.supervisorProgress}`} id="supervisor-progress" cx="25" cy="25" r="22" strokeWidth="4"/>
        </svg>
      </div>
      
      <div className={`${styles.agentCard} ${styles.architect} ${agentStates.architect.active ? styles.active : ''} ${agentStates.architect.completed ? styles.completed : ''}`}>
        <div className={styles.agentIcon}>🏗️</div>
        <div className={styles.agentTitle}>Architect</div>
        <div className={styles.agentStep}>
          {getCurrentStepForAgent('architect')?.label || ''}
        </div>
        <svg className={styles.progressRing}>
          <circle className={styles.progressRingCircle} cx="20" cy="20" r="18"/>
          <circle className={styles.progressRingProgress} id="architect-progress" cx="20" cy="20" r="18"/>
        </svg>
      </div>
      
      <div className={`${styles.agentCard} ${styles.security} ${agentStates.security.active ? styles.active : ''} ${agentStates.security.completed ? styles.completed : ''}`}>
        <div className={styles.agentIcon}>🛡️</div>
        <div className={styles.agentTitle}>Security</div>
        <div className={styles.agentStep}>
          {getCurrentStepForAgent('security')?.label || ''}
        </div>
        <svg className={styles.progressRing}>
          <circle className={styles.progressRingCircle} cx="20" cy="20" r="18"/>
          <circle className={styles.progressRingProgress} id="security-progress" cx="20" cy="20" r="18"/>
        </svg>
      </div>
      
      <div className={`${styles.agentCard} ${styles.risk} ${agentStates.risk.active ? styles.active : ''} ${agentStates.risk.completed ? styles.completed : ''}`}>
        <div className={styles.agentIcon}>⚠️</div>
        <div className={styles.agentTitle}>Risk Assessment</div>
        <div className={styles.agentStep}>
          {getCurrentStepForAgent('risk')?.label || ''}
        </div>
        <svg className={styles.progressRing}>
          <circle className={styles.progressRingCircle} cx="20" cy="20" r="18"/>
          <circle className={styles.progressRingProgress} id="risk-progress" cx="20" cy="20" r="18"/>
        </svg>
      </div>
      
      <div className={styles.controls}>
        <button className={styles.btn} onClick={startWorkflow} disabled={isRunning}>
          🚀 Start
        </button>
        <button className={styles.btn} onClick={resetWorkflow}>
          🔄 Reset
        </button>
      </div>
    </div>
  );
}