import React, { useState, useEffect } from 'react';
import { getSecurityAssessment } from '../utils/security-api';
import { getNodeControls, api } from '../utils/api';
import { Auth } from 'aws-amplify';

interface SecurityAssessmentProps {
  projectId: string;
}

interface NodeControl {
  node_id: string;
  node_name: string;
  node_type: string;
  mapped_controls: string[];
  mapped_at: string;
  status: string;
}

interface DomainScore {
  score: number;
  status: string;
}

interface SecurityAssessment {
  assessment_summary: {
    overall_security_score: number;
    risk_level: string;
    compliance_status: string;
    assessment_date: string;
    key_findings: string[];
  };
  domain_scores: {
    [key: string]: DomainScore;
  };
  risk_findings: Array<{
    finding_id: string;
    title: string;
    severity: string;
    description: string;
    impact: string;
    recommendation: string;
    affected_components: string[];
  }>;
  recommendations: Array<{
    priority: string;
    category: string;
    recommendation: string;
    timeline: string;
    effort: string;
  }>;
}

const SecurityAssessment: React.FC<SecurityAssessmentProps> = ({ projectId }) => {
  const [assessment, setAssessment] = useState<SecurityAssessment | null>(null);
  const [nodeControls, setNodeControls] = useState<NodeControl[]>([]);
  const [loading, setLoading] = useState(true);
  const [controlsLoading, setControlsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadSecurityAssessment();
    loadNodeControls();
  }, [projectId]);

  const loadSecurityAssessment = async () => {
    try {
      setLoading(true);
      const { validatePathParam } = await import('../utils/validatePathParam');
      const validId = validatePathParam(projectId, 'projectId');
      const response = await api.get(`/api/projects/${validId}/security-assessment`);
      setAssessment(response.data.assessment);
      setError(null);
    } catch (err) {
      setError('Failed to load security assessment');
      console.error('Error loading security assessment:', err);
    } finally {
      setLoading(false);
    }
  };

  const loadNodeControls = async () => {
    try {
      setControlsLoading(true);
      const { data, error } = await getNodeControls(projectId);
      if (!error && data) {
        setNodeControls(data.node_controls || []);
      }
    } catch (err) {
      console.error('Error loading node controls:', err);
    } finally {
      setControlsLoading(false);
    }
  };

  const getScoreColor = (score: number) => {
    if (score >= 80) return 'text-green-600';
    if (score >= 60) return 'text-yellow-600';
    return 'text-red-600';
  };

  const getSeverityColor = (severity: string) => {
    switch (severity.toLowerCase()) {
      case 'high': return 'bg-red-100 text-red-800';
      case 'medium': return 'bg-yellow-100 text-yellow-800';
      case 'low': return 'bg-green-100 text-green-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority.toLowerCase()) {
      case 'high': return 'bg-red-100 text-red-800';
      case 'medium': return 'bg-yellow-100 text-yellow-800';
      case 'low': return 'bg-green-100 text-green-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-md p-4">
        <div className="flex">
          <div className="ml-3">
            <h3 className="text-sm font-medium text-red-800">Error</h3>
            <div className="mt-2 text-sm text-red-700">{error}</div>
          </div>
        </div>
      </div>
    );
  }

  if (!assessment) {
    return (
      <div className="text-center py-8">
        <p className="text-gray-500">No security assessment available for this project.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Assessment Summary */}
      <div className="bg-white shadow rounded-lg p-6">
        <h2 className="text-lg font-medium text-gray-900 mb-4">Security Assessment Summary</h2>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="text-center">
            <div className={`text-3xl font-bold ${getScoreColor(assessment.assessment_summary.overall_security_score)}`}>
              {assessment.assessment_summary.overall_security_score}
            </div>
            <div className="text-sm text-gray-500">Overall Score</div>
          </div>
          <div className="text-center">
            <div className="text-lg font-semibold text-gray-900">
              {assessment.assessment_summary.risk_level}
            </div>
            <div className="text-sm text-gray-500">Risk Level</div>
          </div>
          <div className="text-center">
            <div className="text-lg font-semibold text-gray-900">
              {assessment.assessment_summary.compliance_status}
            </div>
            <div className="text-sm text-gray-500">Compliance Status</div>
          </div>
          <div className="text-center">
            <div className="text-lg font-semibold text-gray-900">
              {new Date(assessment.assessment_summary.assessment_date).toLocaleDateString()}
            </div>
            <div className="text-sm text-gray-500">Assessment Date</div>
          </div>
        </div>
        
        {/* Key Findings */}
        <div className="mt-6">
          <h3 className="text-md font-medium text-gray-900 mb-2">Key Findings</h3>
          <ul className="list-disc list-inside space-y-1">
            {assessment.assessment_summary.key_findings.map((finding, index) => (
              <li key={index} className="text-sm text-gray-700">{finding}</li>
            ))}
          </ul>
        </div>
      </div>

      {/* Domain Scores */}
      <div className="bg-white shadow rounded-lg p-6">
        <h2 className="text-lg font-medium text-gray-900 mb-4">Security Domain Scores</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {Object.entries(assessment.domain_scores).map(([domain, score]) => (
            <div key={domain} className="border rounded-lg p-4">
              <div className="flex justify-between items-center">
                <div className="text-sm font-medium text-gray-900 capitalize">
                  {domain.replace('_', ' ')}
                </div>
                <div className={`text-lg font-bold ${getScoreColor(score.score)}`}>
                  {score.score}
                </div>
              </div>
              <div className="text-xs text-gray-500 mt-1">{score.status}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Risk Findings */}
      <div className="bg-white shadow rounded-lg p-6">
        <h2 className="text-lg font-medium text-gray-900 mb-4">Risk Findings</h2>
        <div className="space-y-4">
          {assessment.risk_findings.map((finding) => (
            <div key={finding.finding_id} className="border rounded-lg p-4">
              <div className="flex justify-between items-start mb-2">
                <h3 className="text-md font-medium text-gray-900">{finding.title}</h3>
                <span className={`px-2 py-1 text-xs font-medium rounded-full ${getSeverityColor(finding.severity)}`}>
                  {finding.severity}
                </span>
              </div>
              <p className="text-sm text-gray-700 mb-2">{finding.description}</p>
              <div className="text-sm text-gray-600 mb-2">
                <strong>Impact:</strong> {finding.impact}
              </div>
              <div className="text-sm text-gray-600 mb-2">
                <strong>Recommendation:</strong> {finding.recommendation}
              </div>
              <div className="text-sm text-gray-600">
                <strong>Affected Components:</strong> {finding.affected_components.join(', ')}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Recommendations */}
      <div className="bg-white shadow rounded-lg p-6">
        <h2 className="text-lg font-medium text-gray-900 mb-4">Recommendations</h2>
        <div className="space-y-4">
          {assessment.recommendations.map((rec, index) => (
            <div key={index} className="border rounded-lg p-4">
              <div className="flex justify-between items-start mb-2">
                <div className="text-sm font-medium text-gray-900">{rec.category}</div>
                <span className={`px-2 py-1 text-xs font-medium rounded-full ${getPriorityColor(rec.priority)}`}>
                  {rec.priority}
                </span>
              </div>
              <p className="text-sm text-gray-700 mb-2">{rec.recommendation}</p>
              <div className="flex justify-between text-xs text-gray-500">
                <span>Timeline: {rec.timeline}</span>
                <span>Effort: {rec.effort}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default SecurityAssessment;