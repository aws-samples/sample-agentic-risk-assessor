import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import Header from '../../../components/Header';
import styles from '../../../styles/Home.module.css';
import nodeStyles from '../../../styles/NodeDetails.module.css';
import { getNodeDetails, getProject } from '../../../utils/api';

interface NodeControl {
  control_id: string;
  control_name: string;
  control_description?: string;
  category: string;
  priority: string;
  rationale?: string;
  implementation_guidance?: string;
  assessment_procedures?: string;
}

interface NodeDetails {
  node_id: string;
  node_name: string;
  node_type: string;
  node_description: string;
  project_id: string;
  mapped_controls: NodeControl[];
  mapped_at: string;
  mapping_source: string;
  status: string;
}

export default function NodeDetailsPage() {
  const router = useRouter();
  const { projectId, nodeId } = router.query;
  
  const [nodeDetails, setNodeDetails] = useState<NodeDetails | null>(null);
  const [project, setProject] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('all');
  const [priorityFilter, setPriorityFilter] = useState('all');

  useEffect(() => {
    if (projectId && nodeId) {
      fetchNodeDetails();
      fetchProject();
    }
  }, [projectId, nodeId]);

  const fetchNodeDetails = async () => {
    try {
      setLoading(true);
      const { data, error } = await getNodeDetails(projectId as string, nodeId as string);
      if (error) {
        setError(error.message);
      } else {
        setNodeDetails(data);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to fetch node details');
    } finally {
      setLoading(false);
    }
  };

  const fetchProject = async () => {
    try {
      const { data, error } = await getProject(projectId as string);
      if (!error) {
        setProject(data);
      }
    } catch (err) {
      console.error('Error fetching project:', err);
    }
  };

  const filterControls = (controls: NodeControl[]) => {
    return controls.filter(control => {
      const categoryMatch = categoryFilter === 'all' || 
        control.category?.toLowerCase().includes(categoryFilter.toLowerCase());
      const priorityMatch = priorityFilter === 'all' || 
        control.priority?.toLowerCase() === priorityFilter.toLowerCase();
      return categoryMatch && priorityMatch;
    });
  };

  const getCategoryClass = (category: string) => {
    if (!category) return '';
    
    if (category.toLowerCase().includes('identity')) return nodeStyles.identity;
    if (category.toLowerCase().includes('infrastructure')) return nodeStyles.infrastructure;
    if (category.toLowerCase().includes('data')) return nodeStyles.data;
    if (category.toLowerCase().includes('logging')) return nodeStyles.logging;
    if (category.toLowerCase().includes('incident')) return nodeStyles.incident;
    if (category.toLowerCase().includes('application')) return nodeStyles.application;
    
    return '';
  };

  if (loading) {
    return (
      <div className={styles.container}>
        <Header />
        <main className={styles.main}>
          <p>Loading node details...</p>
        </main>
      </div>
    );
  }

  if (error) {
    return (
      <div className={styles.container}>
        <Header />
        <main className={styles.main}>
          <p className={styles.error}>{error}</p>
          <button onClick={() => router.back()}>Go Back</button>
        </main>
      </div>
    );
  }

  if (!nodeDetails) {
    return (
      <div className={styles.container}>
        <Header />
        <main className={styles.main}>
          <p>Node details not found</p>
          <button onClick={() => router.back()}>Go Back</button>
        </main>
      </div>
    );
  }

  const filteredControls = filterControls(nodeDetails.mapped_controls || []);

  return (
    <div className={styles.container}>
      <Header />
      <main className={styles.main}>
        <div className={nodeStyles.breadcrumb}>
          <button onClick={() => router.push('/projects')} className={nodeStyles.breadcrumbLink}>
            Projects
          </button>
          <span className={nodeStyles.breadcrumbSeparator}>/</span>
          <button 
            onClick={() => router.push(`/projects/${projectId}`)} 
            className={nodeStyles.breadcrumbLink}
          >
            {project?.name || 'Project'}
          </button>
          <span className={nodeStyles.breadcrumbSeparator}>/</span>
          <span className={nodeStyles.breadcrumbCurrent}>Node Details</span>
        </div>

        <h1 className={styles.title}>Node Details</h1>
        
        <div className={nodeStyles.nodeDetailsContainer}>
          <div className={nodeStyles.nodeInfo}>
            <h2>Node Information</h2>
            <div className={nodeStyles.infoGrid}>
              <div className={nodeStyles.infoItem}>
                <label>Node ID:</label>
                <code className={nodeStyles.nodeId}>{nodeDetails.node_id}</code>
              </div>
              <div className={nodeStyles.infoItem}>
                <label>Name:</label>
                <span>{nodeDetails.node_name}</span>
              </div>
              <div className={nodeStyles.infoItem}>
                <label>Type:</label>
                <span className={nodeStyles.nodeType}>{nodeDetails.node_type}</span>
              </div>
              <div className={nodeStyles.infoItem}>
                <label>Description:</label>
                <span>{nodeDetails.node_description}</span>
              </div>
              <div className={nodeStyles.infoItem}>
                <label>Status:</label>
                <span className={`${nodeStyles.status} ${nodeStyles[nodeDetails.status?.toLowerCase()]}`}>
                  {nodeDetails.status}
                </span>
              </div>
              <div className={nodeStyles.infoItem}>
                <label>Mapped At:</label>
                <span>{new Date(nodeDetails.mapped_at).toLocaleString()}</span>
              </div>
              <div className={nodeStyles.infoItem}>
                <label>Mapping Source:</label>
                <span>{nodeDetails.mapping_source}</span>
              </div>
            </div>
          </div>

          <div className={nodeStyles.controlsSection}>
            <div className={nodeStyles.controlsHeader}>
              <h2>Applicable Controls ({nodeDetails.mapped_controls?.length || 0})</h2>
              
              <div className={nodeStyles.filterContainer}>
                <select 
                  className={nodeStyles.filterSelect}
                  value={categoryFilter}
                  onChange={(e) => setCategoryFilter(e.target.value)}
                >
                  <option value="all">All Categories</option>
                  <option value="identity">Identity & Access Management</option>
                  <option value="infrastructure">Infrastructure Protection</option>
                  <option value="data">Data Protection</option>
                  <option value="logging">Logging & Monitoring</option>
                  <option value="incident">Incident Response</option>
                  <option value="application">Application Protection</option>
                </select>
                
                <select 
                  className={nodeStyles.filterSelect}
                  value={priorityFilter}
                  onChange={(e) => setPriorityFilter(e.target.value)}
                >
                  <option value="all">All Priorities</option>
                  <option value="baseline">Baseline</option>
                  <option value="optional">Optional</option>
                </select>
              </div>
            </div>

            {filteredControls.length > 0 ? (
              <div className={nodeStyles.controlsList}>
                {filteredControls.map((control, index) => (
                  <div key={index} className={nodeStyles.controlCard}>
                    <div className={nodeStyles.controlHeader}>
                      <div className={nodeStyles.controlTitle}>
                        <strong className={nodeStyles.controlId}>{control.control_id}</strong>
                        <h3 className={nodeStyles.controlName}>{control.control_name}</h3>
                      </div>
                      <div className={nodeStyles.controlBadges}>
                        <span className={`${nodeStyles.categoryBadge} ${getCategoryClass(control.category)}`}>
                          {control.category}
                        </span>
                        <span className={`${nodeStyles.priorityBadge} ${control.priority?.toLowerCase() === 'baseline' ? nodeStyles.baseline : nodeStyles.optional}`}>
                          {control.priority}
                        </span>
                      </div>
                    </div>
                    
                    <div className={nodeStyles.controlContent}>
                      {(control.control_description || control.rationale) && (
                        <div className={nodeStyles.controlDescription}>
                          <h4>Description</h4>
                          <p>{control.control_description || control.rationale}</p>
                        </div>
                      )}
                      
                      {control.implementation_guidance && (
                        <div className={nodeStyles.controlGuidance}>
                          <h4>Implementation Guidance</h4>
                          <p>{control.implementation_guidance}</p>
                        </div>
                      )}
                      
                      {control.assessment_procedures && (
                        <div className={nodeStyles.controlAssessment}>
                          <h4>Assessment Procedures</h4>
                          <p>{control.assessment_procedures}</p>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className={nodeStyles.noControls}>
                {nodeDetails.mapped_controls?.length === 0 ? (
                  <p>No controls have been mapped to this node yet.</p>
                ) : (
                  <p>No controls match the current filters.</p>
                )}
              </div>
            )}
          </div>
        </div>
        
        <div className={styles.buttonContainer}>
          <button onClick={() => router.back()} className={styles.backButton}>
            Back
          </button>
        </div>
      </main>
    </div>
  );
}