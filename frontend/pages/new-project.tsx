import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
// import styles from '../styles/Home.module.css';
import wizardStyles from '../styles/Wizard.module.css';
import Sidebar from '../components/Sidebar';
import { createProject, analyzeDiagram, getDiagramAnalysis, updateDiagramAnalysis, updateProject, uploadImage } from '../utils/api';
import { uploadProjectDocument } from '../utils/document-api';
// import DiagramAnalysisTable from '../components/DiagramAnalysisTable';
import DocumentUpload from '../components/DocumentUpload';
import { getJwtToken } from '../utils/auth';

export default function NewProject() {
  const router = useRouter();
  const [currentStep, setCurrentStep] = useState(1);
  const [projectName, setProjectName] = useState('');
  const [projectDescription, setProjectDescription] = useState('');
  const [selectedProfileId, setSelectedProfileId] = useState<string>('');
  const [profiles, setProfiles] = useState<any[]>([]);
  const [projectDiagram, setProjectDiagram] = useState<File | null>(null);

  // Load org profiles on mount
  useEffect(() => {
    const loadProfiles = async () => {
      try {
        const token = await getJwtToken();
        if (!token) return;
        const response = await fetch('/api/profiles', {
          headers: { 'Authorization': `Bearer ${token}` },
        });
        if (response.ok) {
          const data = await response.json();
          setProfiles(data.profiles || data || []);
        }
      } catch (e) {
        console.error('Failed to load profiles:', e);
      }
    };
    loadProfiles();
  }, []);
  const [projectDocument, setProjectDocument] = useState<File | null>(null);
  const [diagramPreview, setDiagramPreview] = useState('');
  const [extractedDiagramUrl, setExtractedDiagramUrl] = useState<string | null>(null);
  const [uploadingDocument, setUploadingDocument] = useState(false);

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [projectId, setProjectId] = useState<string | null>(null);
  const [analyzing, setAnalyzing] = useState(false);
  // const [diagramAnalysis, setDiagramAnalysis] = useState<any>({ nodes: [], flows: [] });



  const handleNext = () => {
    if (currentStep === 1 && !projectName.trim()) {
      setError('Project name is required');
      return;
    }
    if (currentStep === 2 && !projectDescription.trim()) {
      setError('Project description is required');
      return;
    }
    setError('');
    
    // If moving from description to next step, create the project and go to review
    if (currentStep === 2) {
      handleCreateProject();
    } else {
      setCurrentStep(currentStep + 1);
    }
  };

  const handleBack = () => {
    setCurrentStep(currentStep - 1);
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setProjectDiagram(file);
      
      // Create preview URL for the image
      const reader = new FileReader();
      reader.onload = () => {
        setDiagramPreview(reader.result as string);
      };
      reader.readAsDataURL(file);
    }
  };

  const handleDocumentUpload = async (file: File) => {
    setProjectDocument(file);
    
    // If it's a Word document, process it immediately to extract diagrams
    if (file.name.toLowerCase().endsWith('.docx')) {
      if (projectId) {
        // Project exists, upload immediately
        const result = await uploadDocument(projectId, file);
        if (result?.diagram_url) {
          setDiagramPreview(result.diagram_url);
          setExtractedDiagramUrl(result.diagram_url);
          setProjectDiagram(file);
        }
      } else {
        // During wizard, create a temporary project to process the document
        setUploadingDocument(true);
        try {
          const tempProjectData = {
            name: projectName || 'Temp Project',
            description: projectDescription || 'Temporary project for document processing',
            diagram_image: '',
            diagram_type: 'image/png',
            data_classification: 'public',
            availability: 'T2',
            has_pii: 'no',
            regulations: []
          };
          
          const { data, error } = await createProject(tempProjectData);
          if (error) throw new Error(error.message);
          
          const tempProjectId = data.project_id;
          const result = await uploadDocument(tempProjectId, file);
          
          if (result?.diagram_url) {
            setDiagramPreview(result.diagram_url);
            setExtractedDiagramUrl(result.diagram_url);
            setProjectDiagram(file);
          }
          
          // Store temp project ID for later cleanup/update
          setProjectId(tempProjectId);
        } catch (err: any) {
          console.error('Error processing Word document:', err);
          setError('Failed to process Word document. Please try again.');
        } finally {
          setUploadingDocument(false);
        }
      }
    }
  };

  const uploadDocument = async (projectId: string, file: File) => {
    setUploadingDocument(true);
    try {
      const { data, error } = await uploadProjectDocument(projectId, file);
      if (error) {
        throw new Error(error.message);
      }
      console.log('Document uploaded successfully:', data);
      return data;
    } catch (err: any) {
      console.error('Error uploading document:', err);
      setError(err.message || 'Failed to upload document. Please try again.');
      return null;
    } finally {
      setUploadingDocument(false);
    }
  };

  const handleCreateProject = async () => {
    setIsSubmitting(true);
    setError('');
    
    try {
      const projectData = {
        name: projectName,
        description: projectDescription,
        profile_id: selectedProfileId || undefined,
        diagram_image: extractedDiagramUrl || diagramPreview,
        diagram_type: extractedDiagramUrl ? 'image/png' : (projectDiagram?.type || 'image/png'),
        data_classification: 'public',
        availability: 'T2',
        has_pii: 'no',
        regulations: []
      };
      
      let finalProjectId;
      
      if (projectId) {
        // Update existing temporary project
        const { error } = await updateProject(projectId, projectData);
        if (error) throw new Error(error.message);
        finalProjectId = projectId;
      } else {
        // Create new project
        const { data, error } = await createProject(projectData);
        if (error) throw new Error(error.message);
        finalProjectId = data.project_id;
        setProjectId(finalProjectId);
        
        // Upload document if not already processed
        if (projectDocument && !extractedDiagramUrl) {
          const result = await uploadDocument(finalProjectId, projectDocument);
          if (result?.diagram_url) {
            setDiagramPreview(result.diagram_url);
            setExtractedDiagramUrl(result.diagram_url);
            setProjectDiagram(projectDocument);
          }
        }
      }
      
      setCurrentStep(4);
    } catch (err: any) {
      console.error('Error creating project:', err);
      setError(err.message || 'Failed to create project. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Analyze diagram after risk details are entered
  // const handleAnalyzeDiagram = async () => {
  //   if (!projectId) return;
    
  //   setAnalyzing(true);
  //   try {
  //     // Show loading message with thinking cursor
  //     const loadingElement = document.createElement('div');
  //     loadingElement.className = styles.loadingOverlay;
  //     loadingElement.innerHTML = `
  //       <div class="${styles.loadingContent}">
  //         <div class="${styles.loadingSpinner}"></div>
  //         <p>Analyzing storage, please wait...</p>
  //       </div>
  //     `;
  //     document.body.appendChild(loadingElement);
      
  //     const analysisResult = await analyzeDiagram(projectId, diagramPreview);
      
  //     // Remove loading message
  //     document.body.removeChild(loadingElement);
      
  //     if (analysisResult.error) {
  //       console.error('Error analyzing diagram:', analysisResult.error);
  //     } else if (analysisResult.data && analysisResult.data.analysis) {
  //       setDiagramAnalysis(analysisResult.data.analysis);
  //     }
      
  //     // Move to confirmation step
  //     setCurrentStep(4);
  //   } catch (err: any) {
  //     console.error('Error analyzing diagram:', err);
  //     setError(err.message || 'Failed to analyze diagram. Please try again.');
      
  //     // Make sure to remove loading message on error
  //     const loadingElement = document.querySelector(`.${styles.loadingOverlay}`);
  //     if (loadingElement) {
  //       document.body.removeChild(loadingElement);
  //     }
  //   } finally {
  //     setAnalyzing(false);
  //   }
  // };

  // const handleUpdateAnalysis = async (nodes: any[], flows: any[]) => {
  //   if (!projectId) return;
    
  //   try {
  //     const { data, error } = await updateDiagramAnalysis(projectId, { nodes, flows });
  //     if (error) {
  //       throw new Error(error.message);
  //     }
  //     setDiagramAnalysis(data.analysis);
  //   } catch (err: any) {
  //     console.error('Error updating diagram analysis:', err);
  //   }
  // };

  const handleSubmit = async () => {
    // If there's a direct image upload (not from DOCX), upload it and update diagram details
    if (projectDiagram && diagramPreview && !extractedDiagramUrl && projectId && 
        projectDocument && projectDocument.name.toLowerCase().endsWith('.md')) {
      try {
        // Upload image using dedicated endpoint
        const { data, error } = await uploadImage(projectId, diagramPreview, projectDiagram.type);
        
        if (error) {
          console.error('Error uploading diagram:', error);
        } else if (data?.diagram_url) {
          setExtractedDiagramUrl(data.diagram_url);
        }
      } catch (error) {
        console.error('Error uploading diagram:', error);
      }
    }
    
    router.push('/');
  };

  return (
    <div style={{ 
      fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
      backgroundColor: '#e4e4e4ff',
      color: '#000000',
      lineHeight: 1.6,
      height: '100vh',
      display: 'flex'
    }}>
      <Sidebar activePage="new-project" />

      {/* Main Area */}
      <div style={{ flex: 1, padding: '1rem', overflow: 'auto' }}>
        <div style={{
          fontSize: '2rem',
          fontWeight: '600',
          color: '#ff6b35',
          marginBottom: '1rem',
          textAlign: 'center'
        }}>
          Create New Project
        </div>
        
        <div style={{ display: 'flex', gap: '1rem', height: 'calc(100vh - 110px)' }}>
          <div style={{
            width: '250px',
            backgroundColor: '#ffffff',
            border: '2px solid #ff6b35',
            borderRadius: '8px',
            padding: '0rem 1rem',
            display: 'flex',
            flexDirection: 'column'
          }}>
            <h3 style={{ color: '#ff6b35', marginBottom: '1rem', fontSize: '1.2rem', fontWeight: 600 }}>Project Progress</h3>
            
            {[
              { step: 1, title: 'Project Name', desc: 'Basic information' },
              { step: 2, title: 'Description', desc: 'Project details' },
              { step: 3, title: 'Confirmation', desc: 'Review & confirm' }
            ].map(({ step, title, desc }) => (
              <div key={step} style={{ display: 'flex', alignItems: 'center', marginBottom: '1.5rem' }}>
                <div style={{
                  width: '32px',
                  height: '32px',
                  borderRadius: '50%',
                  backgroundColor: currentStep >= step ? '#ff6b35' : '#e9ecef',
                  color: currentStep >= step ? '#ffffff' : '#686868ff',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: '1.0rem',
                  fontWeight: '600',
                  marginRight: '1rem',
                  flexShrink: 0
                }}>
                  {currentStep > step ? '✓' : step}
                </div>
                <div style={{ flex: 1 }}>
                  <div style={{
                    fontSize: '0.9rem',
                    fontWeight: '600',
                    color: currentStep >= step ? '#ff6b35' : '#686868ff',
                    marginBottom: '0.25rem'
                  }}>
                    {title}
                  </div>
                  <div style={{
                    fontSize: '0.75rem',
                    color: '#686868ff',
                    lineHeight: 1.2
                  }}>
                    {desc}
                  </div>
                </div>
              </div>
            ))}
            
            <div style={{
              marginTop: '1rem',
              paddingTop: '1rem',
              borderTop: '1px solid #e9ecef'
            }}>
              <div style={{ fontSize: '0.8rem', color: '#666', marginBottom: '0.5rem' }}>Progress</div>
              <div style={{
                width: '100%',
                height: '6px',
                backgroundColor: '#e9ecef',
                borderRadius: '3px',
                overflow: 'hidden'
              }}>
                <div style={{
                  width: `${(currentStep / 3) * 100}%`,
                  height: '100%',
                  backgroundColor: '#ff6b35',
                  transition: 'width 0.3s ease'
                }}></div>
              </div>
              <div style={{ fontSize: '0.75rem', color: '#999', marginTop: '0.5rem' }}>
                Step {currentStep} of 3
              </div>
            </div>
          </div>
          
          <div style={{
            flex: 1,
            backgroundColor: '#ffffff',
            border: '2px solid #ff6b35',
            borderRadius: '8px',
            padding: '1.5rem',
            overflow: 'auto'
          }}>
            {error && <div className={wizardStyles.error}>{error}</div>}
            
            {currentStep === 1 && (
              <>
              <div className={wizardStyles.formGroup}>
                <label htmlFor="projectName">Project Name:</label>
                <input
                  type="text"
                  id="projectName"
                  value={projectName}
                  onChange={(e) => setProjectName(e.target.value)}
                  placeholder="Enter project name"
                  className={wizardStyles.input}
                />
              </div>
              <div className={wizardStyles.formGroup}>
                <label htmlFor="orgProfile">Organization Profile:</label>
                <select
                  id="orgProfile"
                  value={selectedProfileId}
                  onChange={(e) => setSelectedProfileId(e.target.value)}
                  className={wizardStyles.input}
                >
                  <option value="">Select an organization profile...</option>
                  {profiles.map((p: any) => (
                    <option key={p.id || p.profile_id} value={p.id || p.profile_id}>
                      {p.name || p.profile_name || 'Unnamed Profile'}
                    </option>
                  ))}
                </select>
                <small style={{ color: '#666', marginTop: '4px', display: 'block' }}>
                  The org profile provides context for risk assessment (frameworks, risk appetite, crown jewels, etc.)
                </small>
              </div>
              </>
            )}
            
            {currentStep === 2 && (
              <div className={wizardStyles.formGroup}>
                <label htmlFor="projectDescription">Project Description:</label>
                <textarea
                  id="projectDescription"
                  value={projectDescription}
                  onChange={(e) => setProjectDescription(e.target.value)}
                  placeholder="Enter project description"
                  className={wizardStyles.textarea}
                  rows={5}
                />
                
                {/* Document Upload Section */}
                <div className={wizardStyles.documentSection}>
                  <label htmlFor="projectDescription">Project Documentation (Optional):</label>
                  <div style={{ marginBottom: '1rem' }}>Upload a document to provide additional context for the project. This document will be used by the agents for analysis.</div>
                  <DocumentUpload 
                    onUpload={handleDocumentUpload} 
                    acceptedFormats=".docx,.md"
                    maxSizeMB={10}
                  />
                  {projectDocument && (
                    <div className={wizardStyles.documentInfo}>
                      <p>Selected document: {projectDocument.name}</p>
                      {projectDocument.name.toLowerCase().endsWith('.docx') && (
                        <p style={{ fontSize: '0.8rem', color: '#ff6b35', fontStyle: 'italic' }}>
                          ✨ Word document will be processed to extract diagrams and convert to Markdown
                        </p>
                      )}
                    </div>
                  )}
                </div>
              </div>
            )}
            

            

            
            {currentStep === 3 && (
              <div>
                <h3>Project Summary</h3>
                
                <p><strong>Name:</strong> {projectName}</p>
                <p><strong>Description:</strong> {projectDescription}</p>
                
                {projectDocument && (
                  <p><strong>Document:</strong> {projectDocument.name}</p>
                )}
                
                {/* Diagram Upload Section */}
                <div className={wizardStyles.formGroup} style={{ marginTop: '1.5rem' }}>
                  <label htmlFor="projectDiagram">Project Diagram (Optional):</label>
                  <input
                    type="file"
                    id="projectDiagram"
                    accept="image/*,.pdf"
                    onChange={handleFileChange}
                    className={wizardStyles.fileInput}
                  />
                  {diagramPreview && (
                    <div className={wizardStyles.imagePreview}>
                      <img src={diagramPreview} alt="Project Diagram Preview" />
                    </div>
                  )}
                </div>
              </div>
            )}
            
            <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '2rem', gap: '1rem' }}>
              {currentStep > 1 && (
                <button 
                  onClick={handleBack} 
                  disabled={isSubmitting || analyzing}
                  style={{
                    backgroundColor: '#6c757d',
                    color: '#ffffff',
                    border: 'none',
                    padding: '0.75rem 1.5rem',
                    borderRadius: '8px',
                    fontSize: '1rem',
                    fontWeight: '600',
                    cursor: isSubmitting || analyzing ? 'not-allowed' : 'pointer',
                    opacity: isSubmitting || analyzing ? 0.6 : 1
                  }}
                >
                  Back
                </button>
              )}
              
              {currentStep < 3 ? (
                <button 
                  onClick={handleNext} 
                  disabled={isSubmitting || analyzing || uploadingDocument}
                  style={{
                    backgroundColor: '#ff6b35',
                    color: '#ffffff',
                    border: 'none',
                    padding: '0.75rem 1.5rem',
                    borderRadius: '8px',
                    fontSize: '1rem',
                    fontWeight: '600',
                    cursor: isSubmitting || analyzing || uploadingDocument ? 'not-allowed' : 'pointer',
                    opacity: isSubmitting || analyzing || uploadingDocument ? 0.6 : 1,
                    marginLeft: 'auto'
                  }}
                >
                  {currentStep === 2 ? (isSubmitting ? 'Creating...' : 'Create Project') : 'Next'}
                </button>
              ) : (
                <button 
                  onClick={handleSubmit} 
                  disabled={isSubmitting}
                  style={{
                    backgroundColor: '#ff6b35',
                    color: '#ffffff',
                    border: 'none',
                    padding: '0.75rem 1.5rem',
                    borderRadius: '8px',
                    fontSize: '1rem',
                    fontWeight: '600',
                    cursor: isSubmitting ? 'not-allowed' : 'pointer',
                    opacity: isSubmitting ? 0.6 : 1,
                    marginLeft: 'auto'
                  }}
                >
                  {isSubmitting ? 'Creating...' : 'Confirm'}
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}