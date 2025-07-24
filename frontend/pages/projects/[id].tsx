import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import styles from '../../styles/Home.module.css';
import Sidebar from '../../components/Sidebar';
import { getProject, analyzeDiagram, getDiagramAnalysis, updateDiagramAnalysis, mapControls, getNodeControls, uploadProjectDocument, getProjectDocument, getDiagramUrl, getRiskAssessments } from '../../utils/api';
import DiagramAnalysisTable from '../../components/DiagramAnalysisTable';
import DocumentUpload from '../../components/DocumentUpload';
import ZoomableDiagram from '../../components/ZoomableDiagram';

export default function ProjectDetails() {
  const router = useRouter();
  const { id } = router.query;
  
  console.log('ProjectDetails component rendering with router query:', router.query);
  
  const [project, setProject] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [analyzing, setAnalyzing] = useState(false);
  const [diagramAnalysis, setDiagramAnalysis] = useState<any>(null);
  const [mappingControls, setMappingControls] = useState(false);
  const [nodeControls, setNodeControls] = useState<any[]>([]);
  const [selectedFramework, setSelectedFramework] = useState('');
  const [projectDocument, setProjectDocument] = useState<any>(null);
  const [uploadingDocument, setUploadingDocument] = useState(false);
  const [diagramUrl, setDiagramUrl] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);
  const [riskAssessments, setRiskAssessments] = useState<any[]>([]);
  
  useEffect(() => {
    console.log('ProjectDetails useEffect triggered with id:', id);
    if (id) {
      console.log('Fetching project data for id:', id);
      fetchProject();
      fetchDiagramAnalysis();
      fetchNodeControls();
      fetchProjectDocument();
      fetchDiagramUrl();
      fetchRiskAssessments();
    }
  }, [id, refreshKey]);

  // Listen for refresh events from agent chat
  useEffect(() => {
    const handleForceRefresh = () => {
      console.log('🔄 Received forceRefreshDiagram event, fetching diagram analysis');
      fetchDiagramAnalysis();
    };
    
    window.addEventListener('forceRefreshDiagram', handleForceRefresh);
    return () => window.removeEventListener('forceRefreshDiagram', handleForceRefresh);
  }, []);
  
  const fetchProject = async () => {
    setLoading(true);
    try {
      console.log('Making API call to getProject with id:', id);
      const { data, error } = await getProject(id as string);
      console.log('API response for project details:', data, error);
      if (error) {
        throw new Error(error.message);
      }
      setProject(data);
    } catch (err: any) {
      console.error('Error fetching project:', err);
      setError(err.message || 'Failed to fetch project');
    } finally {
      setLoading(false);
    }
  };
  
  const fetchDiagramAnalysis = async () => {
    try {
      console.log('🔄 Fetching diagram analysis for project:', id);
      const { data, error } = await getDiagramAnalysis(id as string);
      if (error) {
        console.error('Error fetching diagram analysis:', error);
        return;
      }
      console.log('🔄 Diagram analysis fetched successfully:', data);
      setDiagramAnalysis(data);
    } catch (err) {
      console.error('Error fetching diagram analysis:', err);
    }
  };
  
  const fetchNodeControls = async () => {
    try {
      const { data, error } = await getNodeControls(id as string);
      if (error) {
        console.error('Error fetching node controls:', error);
        return;
      }
      setNodeControls(data.node_controls || []);
    } catch (err) {
      console.error('Error fetching node controls:', err);
    }
  };
  
  const fetchProjectDocument = async () => {
    try {
      const { data, error } = await getProjectDocument(id as string);
      if (error) {
        console.error('Error fetching project document:', error);
        return;
      }
      if (data) {
        setProjectDocument(data);
      }
    } catch (err) {
      console.error('Error fetching project document:', err);
    }
  };
  
  const fetchDiagramUrl = async () => {
    try {
      const { data, error } = await getDiagramUrl(id as string);
      if (error) {
        console.error('Error fetching diagram URL:', error);
        return;
      }
      if (data && data.diagram_url) {
        console.log('Setting diagram URL:', data.diagram_url);
        setDiagramUrl(data.diagram_url);
      }
    } catch (err) {
      console.error('Error fetching diagram URL:', err);
    }
  };
  
  const fetchRiskAssessments = async () => {
    try {
      console.log('Fetching risk assessments for project:', id);
      const { data, error } = await getRiskAssessments(id as string);
      if (error) {
        console.error('Error fetching risk assessments:', error);
        return;
      }
      console.log('Risk assessments fetched:', data);
      setRiskAssessments(data?.assessments || []);
    } catch (err) {
      console.error('Error fetching risk assessments:', err);
    }
  };
  
  const handleDocumentUpload = async (file: File) => {
    setUploadingDocument(true);
    try {
      const { data, error } = await uploadProjectDocument(id as string, file);
      if (error) {
        throw new Error(error.message);
      }
      console.log('Document uploaded successfully:', data);
      // Refresh document data
      fetchProjectDocument();
    } catch (err: any) {
      console.error('Error uploading document:', err);
      alert('Failed to upload document: ' + (err.message || 'Unknown error'));
    } finally {
      setUploadingDocument(false);
    }
  };
  
  const handleAnalyzeDiagram = async () => {
    setAnalyzing(true);
    try {
      // Show loading message with thinking cursor
      // Create loading overlay using DOM manipulation (not innerHTML for security)
      const loadingElement = document.createElement('div');
      loadingElement.className = styles.loadingOverlay;
      
      const loadingContent = document.createElement('div');
      loadingContent.className = styles.loadingContent;
      
      const spinner = document.createElement('div');
      spinner.className = styles.loadingSpinner;
      
      const message = document.createElement('p');
      message.textContent = 'Analyzing storage, please wait...';
      
      loadingContent.appendChild(spinner);
      loadingContent.appendChild(message);
      loadingElement.appendChild(loadingContent);
      document.body.appendChild(loadingElement);
      
      const { data, error } = await analyzeDiagram(id as string, project.diagram_url);
      if (error) {
        throw new Error(error.message);
      }
      console.log('Analyze diagram response:', data);
      // Handle different response structures
      if (data.analysis) {
        setDiagramAnalysis(data.analysis);
      } else if (data.nodes || data.flows) {
        setDiagramAnalysis(data);
      } else {
        console.error('Unexpected response structure:', data);
        throw new Error('Invalid response structure from diagram analysis');
      }
      
      // Remove loading message when done
      document.body.removeChild(loadingElement);
    } catch (err: any) {
      console.error('Error analyzing diagram:', err);
      alert('Failed to analyze diagram: ' + (err.message || 'Unknown error'));
      
      // Make sure to remove loading message on error
      const loadingElement = document.querySelector(`.${styles.loadingOverlay}`);
      if (loadingElement) {
        document.body.removeChild(loadingElement);
      }
    } finally {
      setAnalyzing(false);
    }
  };
  
  const handleUpdateAnalysis = async (nodes: any[], flows: any[]) => {
    try {
      const { data, error } = await updateDiagramAnalysis(id as string, { nodes, flows });
      if (error) {
        throw new Error(error.message);
      }
      setDiagramAnalysis(data.analysis);
    } catch (err: any) {
      console.error('Error updating diagram analysis:', err);
      alert('Failed to update analysis: ' + (err.message || 'Unknown error'));
    }
  };
  
  if (loading) {
    return (
      <div style={{ 
        fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
        backgroundColor: '#d0d0d0',
        color: '#000000',
        height: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center'
      }}>
        <p>Loading project details...</p>
      </div>
    );
  }
  
  if (error) {
    return (
      <div style={{ 
        fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
        backgroundColor: '#d0d0d0',
        color: '#000000',
        height: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        flexDirection: 'column'
      }}>
        <p style={{ color: '#dc3545', marginBottom: '1rem' }}>{error}</p>
        <button 
          onClick={() => router.push('/projects')}
          style={{
            backgroundColor: '#ff6b35',
            color: '#ffffff',
            border: 'none',
            padding: '0.75rem 1.5rem',
            borderRadius: '8px',
            cursor: 'pointer'
          }}
        >
          Back to Projects
        </button>
      </div>
    );
  }
  
  if (!project) {
    return (
      <div style={{ 
        fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
        backgroundColor: '#d0d0d0',
        color: '#000000',
        height: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        flexDirection: 'column'
      }}>
        <p style={{ marginBottom: '1rem' }}>Project not found</p>
        <button 
          onClick={() => router.push('/projects')}
          style={{
            backgroundColor: '#ff6b35',
            color: '#ffffff',
            border: 'none',
            padding: '0.75rem 1.5rem',
            borderRadius: '8px',
            cursor: 'pointer'
          }}
        >
          Back to Projects
        </button>
      </div>
    );
  }
  
  return (
    <div style={{ 
      fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
      backgroundColor: '#d0d0d0',
      color: '#000000',
      lineHeight: 1.6,
      height: '100vh',
      display: 'flex'
    }}>
      <Sidebar activePage="projects" />

      {/* Main Area */}
      <div style={{ flex: 1, padding: '1rem', overflow: 'auto' }}>
        <h1 style={{
          fontSize: '2rem',
          fontWeight: '600',
          color: '#ff6b35',
          marginBottom: '1rem',
          textAlign: 'center'
        }}>
          Project Details: {project.name}
        </h1>
        
        <div style={{
          backgroundColor: '#ffffff',
          border: '2px solid #ff6b35',
          borderRadius: '8px',
          padding: '2rem',
          marginBottom: '2rem'
        }}>
          <div style={{ marginBottom: '0.75rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', lineHeight: "1rem" }}>
              <p><span style={{ color: '#ff6b35', fontSize: "1.1rem", fontWeight: "500"}}>Project Description:</span> {project.description}</p>
              <div style={{ textAlign: 'center' }}>
                <button 
                  onClick={() => router.push('/projects')}
                  style={{
                    backgroundColor: '#ff6b35',
                    color: '#ffffff',
                    border: 'none',
                    padding: '0.75rem 1.5rem',
                    borderRadius: '8px',
                    fontSize: '1rem',
                    fontWeight: '600',
                    cursor: 'pointer'
                  }}
                >
                  Back to Projects
                </button>
              </div>            
            </div>
            
            <div style={{ marginBottom: '1rem', lineHeight: "1rem" }}><span style={{ color: '#ff6b35', fontSize: "1.1rem", fontWeight: "500"}}>Created:</span> {new Date(project.created_at).toLocaleString()}</div>
            
            <div style={{ marginTop: '1rem' }}>
              <div style={{ color: '#ff6b35', marginBottom: '1rem', fontSize: '1.1rem', lineHeight: "1rem", fontWeight: "500" }}>Project Document:</div>
              {projectDocument ? (
                <div className={styles.documentInfo}>
                  <p><strong>Document:</strong> {projectDocument.document_name}</p>
                  <p><strong>Uploaded:</strong> {new Date(projectDocument.document_uploaded_at).toLocaleString()}</p>
                  <a 
                    href={projectDocument.download_url} 
                    target="_blank" 
                    rel="noopener noreferrer"
                    style={{
                      backgroundColor: '#ff6b35',
                      color: '#ffffff',
                      textDecoration: 'none',
                      padding: '0.5rem 1rem',
                      borderRadius: '6px',
                      fontSize: '0.9rem',
                      fontWeight: '600',
                      display: 'inline-block',
                      marginTop: '0.5rem'
                    }}
                  >
                    Download Document
                  </a>
                </div>
              ) : (
                <div>
                  <p>No document uploaded. Upload a document to provide additional context for the project.</p>
                  <DocumentUpload 
                    onUpload={handleDocumentUpload} 
                    acceptedFormats=".pdf,.docx,.txt,.md,.rtf"
                    maxSizeMB={10}
                  />
                  {uploadingDocument && <p>Uploading document...</p>}
                </div>
              )}
            </div>
            
            <div style={{ marginTop: '2rem' }}>
              
              {riskAssessments.length > 0 ? (
                <div>
                  <h3 style={{ color: '#ff6b35', marginBottom: '1rem', fontSize: '1.1rem' }}>{riskAssessments.length} Risk Assessment(s)</h3>
                  <div style={{ marginBottom: '1rem', borderRadius: '8px', border: '1px solid #ff6b35', padding: '1rem', backgroundColor: "rgb(248, 249, 250)" }}>
                    <table style={{ 
                      width: '100%', 
                      borderCollapse: 'collapse', 
                      marginTop: '0.5rem',
                      border: '2px solid #ff6b35',
                      borderRadius: '8px'
                    }}>
                      <thead>
                        <tr style={{ backgroundColor: '#ff6b35', color: '#ffffff' }}>
                          <th style={{ padding: '0.75rem', textAlign: 'left', border: '1px solid #ff6b35' }}>Version</th>
                          <th style={{ padding: '0.75rem', textAlign: 'left', border: '1px solid #ff6b35' }}>Filename</th>
                          <th style={{ padding: '0.75rem', textAlign: 'left', border: '1px solid #ff6b35' }}>Created</th>
                          <th style={{ padding: '0.75rem', textAlign: 'left', border: '1px solid #ff6b35' }}>Size</th>
                        </tr>
                      </thead>
                      <tbody>
                        {riskAssessments.map((assessment, index) => (
                          <tr key={assessment.assessment_id} style={{ 
                            backgroundColor: index % 2 === 0 ? '#ffffff' : '#f8f9fa',
                            borderBottom: '1px solid #ff6b35'
                          }}>
                            <td style={{ padding: '0.75rem', border: '1px solid #ff6b35' }}>
                              Version {assessment.version}
                            </td>
                            <td style={{ padding: '0.75rem', border: '1px solid #ff6b35' }}>
                              {assessment.filename}
                            </td>
                            <td style={{ padding: '0.75rem', border: '1px solid #ff6b35' }}>
                              {new Date(assessment.created_at).toLocaleString()}
                            </td>
                            <td style={{ padding: '0.75rem', border: '1px solid #ff6b35' }}>
                              {Math.round(assessment.file_size / 1024)} KB
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              ) : (
                <p>No risk assessments found for this project.</p>
              )}
            </div>
          </div>
          
          {diagramAnalysis && (
            <div style={{ marginBottom: '2rem' }}>
              <DiagramAnalysisTable 
                nodes={diagramAnalysis.nodes || []} 
                flows={diagramAnalysis.flows || []}
                nodeControls={nodeControls}
                onNodesChange={(nodes) => handleUpdateAnalysis(nodes, diagramAnalysis.flows || [])}
                onFlowsChange={(flows) => handleUpdateAnalysis(diagramAnalysis.nodes || [], flows)}
                editable={true}
                projectId={id as string}
              />
            </div>
          )}
        </div>
        
        <div style={{ textAlign: 'center', marginTop: '2rem' }}>
          <button 
            onClick={() => router.push('/projects')}
            style={{
              backgroundColor: '#ff6b35',
              color: '#ffffff',
              border: 'none',
              padding: '0.75rem 1.5rem',
              borderRadius: '8px',
              fontSize: '1rem',
              fontWeight: '600',
              cursor: 'pointer'
            }}
          >
            Back to Projects
          </button>
        </div>
      </div>
    </div>
  );
}