import axios from 'axios';
import { Auth } from 'aws-amplify';

export interface NodeControl {
  node_id: string;
  project_id: string;
  node_type: string;
  node_name: string;
  mapped_controls: any[];
  mapped_at: string;
  mapping_source: string;
  status: string;
}

// Use environment variable for API URL
const API_URL = process.env.NEXT_PUBLIC_API_URL;
if (!API_URL) {
  throw new Error('NEXT_PUBLIC_API_URL environment variable is not set');
}
console.log('Using API URL:', API_URL);

export const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: false,
  timeout: 300000 // 5 minutes timeout
});

// Add request interceptor to include JWT token
api.interceptors.request.use(
  async (config) => {
    try {
      const session = await Auth.currentSession();
      const token = session.getIdToken().getJwtToken();
      config.headers.Authorization = `Bearer ${token}`;
      console.log('✅ JWT token added to request:', config.url, 'Token starts with:', token.substring(0, 20) + '...');
    } catch (error: any) {
      console.log('❌ No valid session found, proceeding without auth header for:', config.url, error?.message || 'Unknown error');
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

export const createProject = async (projectData: any) => {
  try {
    console.log('Creating project with data:', projectData);
    const response = await api.post('/api/projects', projectData);
    console.log('Project creation response:', response.data);
    return { data: response.data, error: null };
  } catch (error: any) {
    console.error('Error creating project:', error);
    console.error('Error details:', error.response?.data);
    return { 
      data: null, 
      error: { 
        message: error.response?.data?.message || 'Failed to create project'
      }
    };
  }
};

// Upload document to a project
export const uploadProjectDocument = async (projectId: string, file: File) => {
  try {
    // Convert file to base64
    const fileBase64 = await fileToBase64(file);
    
    // Send to API
    const response = await api.post('/api/document', {
      project_id: projectId,
      file_name: file.name,
      file_type: file.type,
      file_content: fileBase64
    });
    
    return { data: response.data, error: null };
  } catch (error: any) {
    console.error('Error uploading document:', error);
    return { 
      data: null, 
      error: { 
        message: error.response?.data?.message || 'Failed to upload document'
      }
    };
  }
};

// Get document metadata and download URL
export const getProjectDocument = async (projectId: string) => {
  try {
    const response = await api.get(`/api/projects/${projectId}/document`);
    return { data: response.data, error: null };
  } catch (error: any) {
    // If 404, it means no document exists - this is not an error
    if (error.response?.status === 404) {
      return { data: null, error: null };
    }
    
    console.error('Error fetching document:', error);
    return { 
      data: null, 
      error: { 
        message: error.response?.data?.message || 'Failed to fetch document'
      }
    };
  }
};

// Get document content through backend API to avoid CORS
export const getProjectDocumentContent = async (projectId: string) => {
  try {
    const response = await api.get(`/api/projects/${projectId}/document/content`);
    return { data: response.data, error: null };
  } catch (error: any) {
    console.error('Error fetching document content:', error);
    return { 
      data: null, 
      error: { 
        message: error.response?.data?.message || 'Failed to fetch document content'
      }
    };
  }
};

// Get diagram URL using existing images API
export const getDiagramUrl = async (projectId: string) => {
  try {
    const { data: project, error } = await getProject(projectId);
    if (error || !project || !project.diagram_filename) {
      return { 
        data: null, 
        error: { message: 'No diagram found for this project' }
      };
    }
    
    // Use existing images API endpoint
    const diagramUrl = `${API_URL}/api/images/${project.diagram_filename}`;
    return { data: { diagram_url: diagramUrl }, error: null };
  } catch (error: any) {
    console.error('Error getting diagram URL:', error);
    return { 
      data: null, 
      error: { 
        message: error.response?.data?.message || 'Failed to get diagram URL'
      }
    };
  }
};

// Upload image for project diagram
export const uploadImage = async (projectId: string, imageData: string, imageType: string = 'image/png') => {
  try {
    const response = await api.post('/api/upload-image', {
      project_id: projectId,
      image_data: imageData,
      image_type: imageType
    });
    return { data: response.data, error: null };
  } catch (error: any) {
    console.error('Error uploading image:', error);
    return { 
      data: null, 
      error: { 
        message: error.response?.data?.error || 'Failed to upload image'
      }
    };
  }
};

// Helper function to convert file to base64
const fileToBase64 = (file: File): Promise<string> => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.readAsDataURL(file);
    reader.onload = () => {
      if (typeof reader.result === 'string') {
        // Remove the data URL prefix (e.g., "data:application/pdf;base64,")
        const base64 = reader.result.split(',')[1];
        resolve(base64);
      } else {
        reject(new Error('Failed to convert file to base64'));
      }
    };
    reader.onerror = error => reject(error);
  });
};

export const getProjects = async () => {
  try {
    const response = await api.get('/api/projects');
    return { data: response.data, error: null };
  } catch (error: any) {
    console.error('Error fetching projects:', error);
    return { 
      data: null, 
      error: { 
        message: error.response?.data?.message || 'Failed to fetch projects'
      }
    };
  }
};

export const getProject = async (id: string) => {
  try {
    const response = await api.get(`/api/projects/${id}`);
    return { data: response.data, error: null };
  } catch (error: any) {
    // nosemgrep
    console.error(`Error fetching project ${id}:`, error);
    return { 
      data: null, 
      error: { 
        message: error.response?.data?.message || 'Failed to fetch project'
      }
    };
  }
};

export const checkHealth = async () => {
  try {
    const response = await api.get('/api/health');
    return { data: response.data, error: null };
  } catch (error: any) {
    console.error('Error checking health:', error);
    return { 
      data: null, 
      error: { 
        message: error.response?.data?.message || 'Failed to check health'
      }
    };
  }
};

// Diagram Analysis API functions - Direct Lambda call
export const analyzeDiagram = async (projectId: string, imageData: string) => {
  try {
    const response = await api.post(`/api/projects/${projectId}/diagram-analysis`);
    return { data: response.data, error: null };
  } catch (error: any) {
    console.error('Error analyzing diagram:', error);
    return { 
      data: null, 
      error: { 
        message: error.response?.data?.message || 'Failed to analyze diagram'
      }
    };
  }
};

export const getDiagramAnalysis = async (projectId: string) => {
  try {
    const response = await api.get(`/api/projects/${projectId}/diagram-analysis`);
    return { data: response.data, error: null };
  } catch (error: any) {
    console.error('Error fetching diagram analysis:', error);
    return { 
      data: null, 
      error: { 
        message: error.response?.data?.message || 'Failed to fetch diagram analysis'
      }
    };
  }
};

export const updateDiagramAnalysis = async (projectId: string, analysisData: any) => {
  try {
    const response = await api.put(`/api/projects/${projectId}/diagram-analysis`, analysisData);
    return { data: response.data, error: null };
  } catch (error: any) {
    console.error('Error updating diagram analysis:', error);
    return { 
      data: null, 
      error: { 
        message: error.response?.data?.message || 'Failed to update diagram analysis'
      }
    };
  }
};

export const updateProject = async (projectId: string, projectData: any) => {
  try {
    const response = await api.put(`/api/projects/${projectId}`, projectData);
    return { data: response.data, error: null };
  } catch (error: any) {
    console.error('Error updating project:', error);
    return { 
      data: null, 
      error: { 
        message: error.response?.data?.message || 'Failed to update project'
      }
    };
  }
};

// Admin API functions
export const getServiceControls = async (framework: string) => {
  try {
    const response = await api.get(`/admin/services?framework=${framework}`);
    return { data: response.data.services, error: null };
  } catch (error: any) {
    console.error('Error fetching service controls:', error);
    return { 
      data: null, 
      error: { 
        message: error.response?.data?.message || 'Failed to fetch service controls'
      }
    };
  }
};

export const runServiceControlsMapping = async (framework: string) => {
  try {
    console.log('Running service controls mapping with framework:', framework);
    const payload = { framework };
    console.log('API payload:', JSON.stringify(payload));
    const response = await api.post('/admin/run-mapping', payload);
    console.log('Mapping response:', response.data);
    return { data: response.data, error: null };
  } catch (error: any) {
    console.error('Error running service controls mapping:', error);
    console.error('Error details:', error.response?.data);
    return { 
      data: null, 
      error: { 
        message: error.response?.data?.message || 'Failed to run service controls mapping'
      }
    };
  }
};

export const runServiceMapping = async (serviceName: string, framework: string) => {
  try {
    console.log(`Running mapping for service: ${serviceName}`);
    const response = await api.post('/admin/run-service-mapping', { service: serviceName, framework });
    console.log('Service mapping response:', response.data);
    return { data: response.data, error: null };
  } catch (error: any) {
    // nosemgrep
    console.error(`Error running mapping for service ${serviceName}:`, error);
    return { 
      data: null, 
      error: { 
        message: error.response?.data?.message || 'Failed to run service mapping'
      }
    };
  }
};

export const getExecutionStatus = async (executionArn: string) => {
  try {
    const response = await api.get(`/admin/execution-status/${executionArn}`);
    return { data: response.data, error: null };
  } catch (error: any) {
    console.error('Error getting execution status:', error);
    return { 
      data: null, 
      error: { 
        message: error.response?.data?.message || 'Failed to get execution status'
      }
    };
  }
};





export const getServices = async () => {
  try {
    const response = await api.get('/admin/services');
    return { data: response.data.services, error: null };
  } catch (error: any) {
    console.error('Error fetching services:', error);
    return { 
      data: null, 
      error: { 
        message: error.response?.data?.message || 'Failed to fetch services'
      }
    };
  }
};

export const addService = async (serviceData: {
  serviceName: string;
  description: string;
  documentationLink: string;
  isNativeAws: boolean;
}) => {
  try {
    console.log('Adding service with data:', serviceData);
    const response = await api.post('/admin/services', serviceData);
    console.log('Add service response:', response.data);
    return { data: response.data, error: null };
  } catch (error: any) {
    console.error('Error adding service:', error);
    console.error('Error response:', error.response);
    console.error('Error status:', error.response?.status);
    console.error('Error data:', error.response?.data);
    return { 
      data: null, 
      error: { 
        message: error.response?.data?.error || error.response?.data?.message || error.message || 'Failed to add service'
      }
    };
  }
};

export const mapControls = async (projectId: string, nodes: any[], framework: string) => {
  try {
    const response = await api.post('/api/map-controls', {
      project_id: projectId,
      nodes: nodes,
      framework: framework
    });
    return { data: response.data, error: null };
  } catch (error: any) {
    console.error('Error mapping controls:', error);
    return { 
      data: null, 
      error: { 
        message: error.response?.data?.message || 'Failed to map controls'
      }
    };
  }
};

export const getNodeControls = async (projectId: string) => {
  try {
    const response = await api.get(`/api/projects/${projectId}/node-controls`);
    return { data: response.data, error: null };
  } catch (error: any) {
    console.error('Error fetching node controls:', error);
    return { 
      data: null, 
      error: { 
        message: error.response?.data?.message || 'Failed to fetch node controls'
      }
    };
  }
};

export const getNodeDetails = async (projectId: string, nodeId: string) => {
  try {
    const response = await api.get(`/api/projects/${projectId}/nodes/${nodeId}`);
    return { data: response.data, error: null };
  } catch (error: any) {
    console.error('Error fetching node details:', error);
    return { 
      data: null, 
      error: { 
        message: error.response?.data?.message || 'Failed to fetch node details'
      }
    };
  }
};

// New Orchestrator API Functions
export const startRiskAssessment = async (projectId: string, framework: string = 'nist') => {
  try {
    const response = await api.post('/api/orchestrator/start-risk-assessment', {
      project_id: projectId,
      framework: framework
    });
    return { data: response.data, error: null };
  } catch (error: any) {
    console.error('Error starting risk assessment:', error);
    return { 
      data: null, 
      error: { 
        message: error.response?.data?.message || 'Failed to start risk assessment'
      }
    };
  }
};

export const assignControls = async (projectId: string, framework: string = 'nist') => {
  try {
    const response = await api.post('/api/orchestrator/assign-controls', {
      project_id: projectId,
      framework: framework
    });
    return { data: response.data, error: null };
  } catch (error: any) {
    console.error('Error assigning controls:', error);
    return { 
      data: null, 
      error: { 
        message: error.response?.data?.message || 'Failed to assign controls'
      }
    };
  }
};

export const assessRisks = async (projectId: string) => {
  try {
    const response = await api.post('/api/orchestrator/assess-risks', {
      project_id: projectId
    });
    return { data: response.data, error: null };
  } catch (error: any) {
    console.error('Error assessing risks:', error);
    return { 
      data: null, 
      error: { 
        message: error.response?.data?.message || 'Failed to assess risks'
      }
    };
  }
};

export const getWorkflowStatus = async (workflowId: string) => {
  try {
    const response = await api.get(`/api/orchestrator/workflow-status/${workflowId}`);
    return { data: response.data, error: null };
  } catch (error: any) {
    console.error('Error getting workflow status:', error);
    return { 
      data: null, 
      error: { 
        message: error.response?.data?.message || 'Failed to get workflow status'
      }
    };
  }
};

// Architect Agent API Functions - Via CloudFront (HTTPS)
const AGENTS_URL = process.env.NEXT_PUBLIC_AGENTS_URL || process.env.NEXT_PUBLIC_CLOUDFRONT_URL;
if (!AGENTS_URL) {
  console.warn('NEXT_PUBLIC_AGENTS_URL or NEXT_PUBLIC_CLOUDFRONT_URL not set, agent calls may fail');
}

export const getProjectDetailsFromArchitect = async (projectId: string) => {
  try {
    const response = await axios.get(`${AGENTS_URL}/architect/get_project_details?project_id=${projectId}`, {
      timeout: 300000
    });
    return { data: response.data, error: null };
  } catch (error: any) {
    console.error('Error getting project details from architect:', error);
    return { 
      data: null, 
      error: { 
        message: error.response?.data?.message || 'Failed to get project details from architect'
      }
    };
  }
};

// Risk Assessment API Functions
export interface RiskAssessment {
  assessment_id: string;
  filename: string;
  s3_key: string;
  version: string;
  created_at: string;
  file_size: number;
}

export interface RiskAssessmentsResponse {
  project_id: string;
  assessments: RiskAssessment[];
  count: number;
}

export const saveRiskAssessment = async (projectId: string, assessmentContent: string) => {
  try {
    const response = await api.post(`/api/projects/${projectId}/risk-assessments`, {
      project_id: projectId,
      assessment_content: assessmentContent
    });
    return { data: response.data, error: null };
  } catch (error: any) {
    console.error('Error saving risk assessment:', error);
    return { 
      data: null, 
      error: { 
        message: error.response?.data?.message || 'Failed to save risk assessment'
      }
    };
  }
};

export const getRiskAssessments = async (projectId: string) => {
  try {
    console.log('🚀 getRiskAssessments API call starting for project:', projectId);
    console.log('🚀 API URL:', `${API_URL}/api/projects/${projectId}/risk-assessments`);
    
    const response = await api.get(`/api/projects/${projectId}/risk-assessments`);
    
    console.log('✅ getRiskAssessments API response status:', response.status);
    console.log('✅ getRiskAssessments API response data:', response.data);
    
    return { data: response.data, error: null };
  } catch (error: any) {
    console.error('❌ Error getting risk assessments:', error);
    console.error('❌ Error response status:', error.response?.status);
    console.error('❌ Error response data:', error.response?.data);
    console.error('❌ Error message:', error.message);
    
    return { 
      data: null, 
      error: { 
        message: error.response?.data?.message || 'Failed to get risk assessments'
      }
    };
  }
};

export const downloadRiskAssessment = async (projectId: string, assessmentId: string) => {
  try {
    const response = await api.get(`/api/projects/${projectId}/risk-assessments/${assessmentId}`);
    return { data: response.data, error: null };
  } catch (error: any) {
    console.error('Error downloading risk assessment:', error);
    return { 
      data: null, 
      error: { 
        message: error.response?.data?.message || 'Failed to download risk assessment'
      }
    };
  }
};