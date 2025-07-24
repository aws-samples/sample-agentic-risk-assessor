import React, { useState, useEffect } from 'react';
import styles from '../styles/Home.module.css';

interface ClarificationQuestion {
  id: string;
  category: string;
  question: string;
  type: string;
  priority: string;
  options?: string[];
  gap_info?: any;
}

interface ArchitectureClarificationProps {
  projectId: string;
  onComplete: (responses: any[]) => void;
  wsRef: React.MutableRefObject<WebSocket | null>;
  onArchitectureReviewRefresh?: () => void;
}

const ArchitectureClarification: React.FC<ArchitectureClarificationProps> = ({
  projectId,
  onComplete,
  wsRef,
  onArchitectureReviewRefresh
}) => {
  const [questions, setQuestions] = useState<ClarificationQuestion[]>([]);
  const [responses, setResponses] = useState<Record<string, string>>({});
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [loading, setLoading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [completed, setCompleted] = useState(false);
  const [completionResult, setCompletionResult] = useState<any>(null);

  const startArchitectureAnalysis = async () => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      return;
    }

    setAnalyzing(true);
    
    // Call generate_clarification_questions which now runs architecture analysis first
    const message = {
      message: `generate_clarification_questions ${projectId}`,
      agent: 'architect'
    };

    wsRef.current.send(JSON.stringify(message));

    const originalOnMessage = wsRef.current.onmessage;
    wsRef.current.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.response) {
        console.log('Raw agent response:', data.response);
        console.log('Response type:', typeof data.response);
        
        let result;
        if (typeof data.response === 'string') {
          result = JSON.parse(data.response);
        } else {
          result = data.response;
        }
        
        if (result.questions) {
          setQuestions(result.questions);
        } else {
          throw new Error(`No questions found in response: ${JSON.stringify(result)}`);
        }
        setAnalyzing(false);
        if (wsRef.current) {
          wsRef.current.onmessage = originalOnMessage;
        }
      }
    };
  };

  // No longer used - generate_clarification_questions now handles everything
  const generateClarificationQuestions = async (gaps: any[]) => {
    // This function is deprecated - the new flow calls generate_clarification_questions directly
    // which runs architecture analysis first, then generates questions based on the results
  };

  const handleResponseChange = (questionId: string, answer: string) => {
    setResponses(prev => ({
      ...prev,
      [questionId]: answer
    }));
  };

  const handleNext = () => {
    if (currentQuestionIndex < questions.length - 1) {
      setCurrentQuestionIndex(currentQuestionIndex + 1);
    }
  };

  const handlePrevious = () => {
    if (currentQuestionIndex > 0) {
      setCurrentQuestionIndex(currentQuestionIndex - 1);
    }
  };

  const handleSubmit = async () => {
    const responseArray = Object.entries(responses).map(([questionId, answer]) => ({
      question_id: questionId,
      answer: answer,
      confidence: 'high'
    }));

    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      return;
    }

    setLoading(true);
    
    const message = {
      message: `process_clarification_responses ${projectId} ${JSON.stringify(responseArray)}`,
      agent: 'architect'
    };

    wsRef.current.send(JSON.stringify(message));

    const originalOnMessage = wsRef.current.onmessage;
    wsRef.current.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.response) {
        console.log('Submit response received:', data.response);
        
        // Check if response contains refresh keyword
        const responseText = typeof data.response === 'string' ? data.response : JSON.stringify(data.response);
        if (responseText.includes('REFRESH_ARCHITECTURE_REVIEW') && onArchitectureReviewRefresh) {
          console.log('Triggering architecture review refresh');
          onArchitectureReviewRefresh();
        }
        
        try {
          let result;
          if (typeof data.response === 'string') {
            result = JSON.parse(data.response);
          } else {
            result = data.response;
          }
          console.log('Parsed submit result:', result);
          setCompleted(true);
          setCompletionResult(result);
          onComplete([result]);
        } catch (e) {
          console.error('Error parsing completion result:', e);
          // Still call onComplete with a success message since the backend worked
          const fallbackResult = {
            project_id: projectId,
            status: 'completed',
            message: 'Architecture clarification completed successfully',
            responses_submitted: Object.keys(responses).length
          };
          setCompleted(true);
          setCompletionResult(fallbackResult);
          onComplete([fallbackResult]);
        }
        setLoading(false);
        if (wsRef.current) {
          wsRef.current.onmessage = originalOnMessage;
        }
      }
    };
  };

  const currentQuestion = questions[currentQuestionIndex];
  const progress = questions.length > 0 ? ((currentQuestionIndex + 1) / questions.length) * 100 : 0;
  const answeredCount = Object.keys(responses).length;

  if (analyzing) {
    return (
      <div className={styles.card}>
        <h3>🔍 Analyzing Architecture Quality</h3>
        <p>Analyzing both diagram and document for completeness and accuracy...</p>
        <div style={{ textAlign: 'center', padding: '2rem' }}>
          <div style={{ fontSize: '2rem' }}>⏳</div>
        </div>
      </div>
    );
  }

  if (questions.length === 0) {
    return (
      <div className={styles.card}>
        <h3>🏗️ Architecture Quality Assessment</h3>
        <p>Start interactive architecture analysis to improve documentation quality.</p>
        <button 
          onClick={startArchitectureAnalysis}
          className={styles.button}
          style={{ backgroundColor: '#0070f3', color: 'white' }}
        >
          Start Architecture Analysis
        </button>
      </div>
    );
  }

  if (loading) {
    return (
      <div className={styles.card}>
        <h3>Processing...</h3>
        <div style={{ textAlign: 'center', padding: '2rem' }}>
          <div style={{ fontSize: '2rem' }}>⏳</div>
        </div>
      </div>
    );
  }

  if (completed && completionResult) {
    return (
      <div className={styles.card}>
        <h3>✅ Architecture Analysis Completed</h3>
        <p style={{ color: '#28a745', fontWeight: 'bold' }}>
          {completionResult.message || 'Architecture clarification completed successfully'}
        </p>
        
        {completionResult.assessment && (
          <div style={{ marginTop: '2rem' }}>
            <h4>📋 Architecture Assessment Document</h4>
            
            {completionResult.assessment.architecture_strengths?.length > 0 && (
              <div style={{ marginBottom: '1rem' }}>
                <h5 style={{ color: '#28a745' }}>✅ Strengths:</h5>
                <ul>
                  {completionResult.assessment.architecture_strengths.map((strength: string, index: number) => (
                    <li key={index}>{strength}</li>
                  ))}
                </ul>
              </div>
            )}
            
            {completionResult.assessment.architecture_weaknesses?.length > 0 && (
              <div style={{ marginBottom: '1rem' }}>
                <h5 style={{ color: '#dc3545' }}>⚠️ Areas for Improvement:</h5>
                <ul>
                  {completionResult.assessment.architecture_weaknesses.map((weakness: string, index: number) => (
                    <li key={index}>{weakness}</li>
                  ))}
                </ul>
              </div>
            )}
            
            {completionResult.assessment.recommendations?.length > 0 && (
              <div style={{ marginBottom: '1rem' }}>
                <h5 style={{ color: '#0070f3' }}>💡 Recommendations:</h5>
                <ul>
                  {completionResult.assessment.recommendations.map((rec: string, index: number) => (
                    <li key={index}>{rec}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
        
        <div style={{ marginTop: '2rem', textAlign: 'center' }}>
          <button 
            onClick={() => {
              setCompleted(false);
              setCompletionResult(null);
              setQuestions([]);
              setResponses({});
              setCurrentQuestionIndex(0);
            }}
            className={styles.button}
            style={{ backgroundColor: '#6c757d', color: 'white' }}
          >
            Start New Analysis
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.card}>
      <div style={{ marginBottom: '1rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
          <h3>🏗️ Architecture Clarification</h3>
          <span style={{ fontSize: '0.9rem', color: '#666' }}>
            Question {currentQuestionIndex + 1} of {questions.length}
          </span>
        </div>
        
        {/* Progress Bar */}
        <div style={{ width: '100%', backgroundColor: '#f0f0f0', borderRadius: '4px', height: '8px', marginBottom: '1rem' }}>
          <div 
            style={{ 
              width: `${progress}%`, 
              backgroundColor: '#0070f3', 
              height: '100%', 
              borderRadius: '4px',
              transition: 'width 0.3s ease'
            }}
          />
        </div>

        {/* Question Stats */}
        <div style={{ display: 'flex', gap: '1rem', marginBottom: '1rem', fontSize: '0.85rem' }}>
          <span>📊 Answered: {answeredCount}/{questions.length}</span>
          <span>🎯 Priority: {currentQuestion?.priority}</span>
          <span>📋 Category: {currentQuestion?.category}</span>
        </div>
      </div>

      {currentQuestion && (
        <div style={{ marginBottom: '2rem' }}>
          <div style={{ 
            backgroundColor: '#f8f9fa', 
            padding: '1rem', 
            borderRadius: '8px', 
            marginBottom: '1rem',
            border: '1px solid #e9ecef'
          }}>
            <h4 style={{ margin: '0 0 0.5rem 0', color: '#0070f3' }}>
              {currentQuestion.question}
            </h4>
            {currentQuestion.gap_info && (
              <p style={{ margin: 0, fontSize: '0.85rem', color: '#666' }}>
                Context: {currentQuestion.gap_info.type}
              </p>
            )}
          </div>

          {/* Answer Input */}
          {currentQuestion.options ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              {currentQuestion.options.map((option, index) => (
                <label key={index} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <input
                    type="radio"
                    name={currentQuestion.id}
                    value={option}
                    checked={responses[currentQuestion.id] === option}
                    onChange={(e) => handleResponseChange(currentQuestion.id, e.target.value)}
                  />
                  <span style={{ textTransform: 'capitalize' }}>{option.replace('_', ' ')}</span>
                </label>
              ))}
            </div>
          ) : (
            <textarea
              value={responses[currentQuestion.id] || ''}
              onChange={(e) => handleResponseChange(currentQuestion.id, e.target.value)}
              placeholder="Enter your answer..."
              style={{
                width: '100%',
                minHeight: '80px',
                padding: '0.5rem',
                border: '1px solid #ddd',
                borderRadius: '4px',
                fontSize: '0.9rem'
              }}
            />
          )}
        </div>
      )}

      {/* Navigation */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <button
          onClick={handlePrevious}
          disabled={currentQuestionIndex === 0}
          className={styles.button}
          style={{ 
            backgroundColor: currentQuestionIndex === 0 ? '#ccc' : '#6c757d',
            color: 'white'
          }}
        >
          ← Previous
        </button>

        {/* Answer Status */}
        <div style={{ fontSize: '0.85rem', color: responses[currentQuestion?.id] ? '#28a745' : '#666' }}>
          {responses[currentQuestion?.id] ? '✓ Answered' : 'Please answer to continue'}
        </div>

        <div style={{ display: 'flex', gap: '0.5rem' }}>
          {currentQuestionIndex < questions.length - 1 ? (
            <button
              onClick={handleNext}
              className={styles.button}
              style={{ 
                backgroundColor: '#0070f3', 
                color: 'white',
                padding: '0.5rem 1rem',
                fontWeight: 'bold'
              }}
            >
              Next →
            </button>
          ) : (
            <button
              onClick={handleSubmit}
              disabled={answeredCount === 0}
              className={styles.button}
              style={{ 
                backgroundColor: answeredCount === 0 ? '#ccc' : '#28a745',
                color: 'white',
                padding: '0.5rem 1rem',
                fontWeight: 'bold'
              }}
            >
              Complete Analysis ✓
            </button>
          )}
        </div>
      </div>

      {/* Skip Option */}
      <div style={{ textAlign: 'center', marginTop: '1rem' }}>
        <button
          onClick={() => {
            if (currentQuestionIndex < questions.length - 1) {
              handleNext();
            } else {
              handleSubmit();
            }
          }}
          style={{
            background: 'none',
            border: 'none',
            color: '#666',
            fontSize: '0.85rem',
            cursor: 'pointer',
            textDecoration: 'underline'
          }}
        >
          Skip this question
        </button>
      </div>
    </div>
  );
};

export default ArchitectureClarification;