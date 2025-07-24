import { api } from './api';

export const getSecurityAssessment = async (projectId: string) => {
  try {
    const response = await api.get(`/api/projects/${projectId}/security-assessments`);
    return { data: response.data, error: null };
  } catch (error: any) {
    console.error('Error getting security assessment:', error);
    return { 
      data: null, 
      error: { 
        message: error.response?.data?.message || 'Failed to get security assessment'
      }
    };
  }
};

export const saveSecurityAssessment = async (projectId: string, assessmentContent: string) => {
  try {
    const response = await api.post(`/api/projects/${projectId}/security-assessments`, {
      project_id: projectId,
      assessment_content: assessmentContent
    });
    return { data: response.data, error: null };
  } catch (error: any) {
    console.error('Error saving security assessment:', error);
    return { 
      data: null, 
      error: { 
        message: error.response?.data?.message || 'Failed to save security assessment'
      }
    };
  }
};

export const downloadSecurityAssessment = async (projectId: string, assessmentId: string) => {
  try {
    const response = await api.get(`/api/projects/${projectId}/security-assessments/${assessmentId}/download`);
    return { data: response.data, error: null };
  } catch (error: any) {
    console.error('Error downloading security assessment:', error);
    return { 
      data: null, 
      error: { 
        message: error.response?.data?.message || 'Failed to download security assessment'
      }
    };
  }
};