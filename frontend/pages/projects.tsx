import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import { getProjects } from '../utils/api';
import Sidebar from '../components/Sidebar';
import projectStyles from '../styles/Projects.module.css';

export default function Projects() {
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const projectsPerPage = 20;
  const router = useRouter();

  useEffect(() => {
    const fetchProjects = async () => {
      try {
        const { data, error } = await getProjects();
        if (error) {
          throw new Error(error.message);
        }
        setProjects(data || []);
      } catch (err: any) {
        console.error('Error in fetchProjects:', err);
        setError(err.message || 'Failed to fetch projects');
      } finally {
        setLoading(false);
      }
    };

    fetchProjects();
  }, []);

  const handleViewDetails = async (projectId: string) => {
    // Clear agent contexts when switching projects
    try {
      const { clearAgentContexts } = await import('../utils/agent-context');
      await clearAgentContexts();
    } catch (error) {
      console.warn('Failed to clear agent contexts:', error);
    }
    
    router.push(`/projects/${projectId}`);
  };

  const handleSearch = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchTerm(e.target.value);
    setCurrentPage(1);
  };

  const filteredProjects = projects.filter((project: any) => {
    if (project.name) {
      return project.name.toLowerCase().includes(searchTerm.toLowerCase());
    }
  });

  const indexOfLastProject = currentPage * projectsPerPage;
  const indexOfFirstProject = indexOfLastProject - projectsPerPage;
  const currentProjects = filteredProjects.slice(indexOfFirstProject, indexOfLastProject);
  const totalPages = Math.ceil(filteredProjects.length / projectsPerPage);

  const paginate = (pageNumber: number) => setCurrentPage(pageNumber);

  return (
    <div style={{ 
      fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
      backgroundColor: '#e4e4e4ff',
      color: '#000000',
      lineHeight: 1.6,
      height: '100vh',
      display: 'flex'
    }}>
      <Sidebar activePage="projects" />

      {/* Main Area */}
      <div style={{ flex: 1, padding: '1rem' }}>
        <div style={{ maxWidth: '1200px', margin: '0 auto' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div style={{
              fontSize: '2rem',
              fontWeight: '600',
              color: '#ff6b35',
              marginBottom: '1rem',
              textAlign: 'center'
            }}>
              Projects
            </div>
            <button
              onClick={() => router.push('/new-project')}
              style={{
                backgroundColor: '#ff6b35',
                color: '#ffffff',
                border: 'none',
                padding: '0.75rem 1.1rem',
                borderRadius: '8px',
                fontSize: '1.2rem',
                fontWeight: '500',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem'
              }}
            >
              <span>➕</span>
              New Project
            </button>
          </div>

          {/* Search Bar */}
          <div style={{ marginBottom: '1rem' }}>
            <input
              type="text"
              placeholder="Search projects..."
              value={searchTerm}
              onChange={handleSearch}
              style={{
                width: '100%',
                maxWidth: '400px',
                padding: '0.75rem',
                border: '1px solid #ff6b35',
                borderRadius: '8px',
                fontSize: '1rem',
                color: 'black',
                backgroundColor: '#ffffff'
              }}
            />
          </div>

          {/* Projects Content */}
          <div style={{
            backgroundColor: '#ffffff',
            border: '1px solid #ff4400ff',
            borderRadius: '8px',
            padding: '1.5rem',
            minHeight: '400px',
            overflow: 'auto',
            height: 'calc( 100vh - 230px)'
          }}>
            {loading ? (
              <div style={{ textAlign: 'center', color: '#666', fontSize: '1.1rem' }}>
                Loading projects...
              </div>
            ) : error ? (
              <div style={{ textAlign: 'center', color: '#dc3545', fontSize: '1.1rem' }}>
                {error}
              </div>
            ) : filteredProjects.length === 0 ? (
              <div style={{ textAlign: 'center', color: '#666' }}>
                <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>📊</div>
                <h3 style={{ color: '#ff6b35', marginBottom: '0.5rem' }}>No projects found</h3>
                <p style={{ marginBottom: '2rem' }}>
                  {projects.length === 0 ? 'Create your first project to get started!' : 'No projects match your search.'}
                </p>
                {projects.length === 0 && (
                  <button
                    onClick={() => router.push('/new-project')}
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
                    Create First Project
                  </button>
                )}
              </div>
            ) : (
              <>
                <table className={projectStyles.projectsTable}>
                  <thead>
                    <tr>
                      <th>Project Name</th>
                      <th>Description</th>
                      <th>Created</th>
                      <th className="actions-header">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {currentProjects.map((project: any) => (
                      <tr key={project.id}>
                        <td>{project.name}</td>
                        <td className={projectStyles.description}>{project.description}</td>
                        <td className={projectStyles.date}>{new Date(project.created_at).toLocaleDateString()}</td>
                        <td className={projectStyles.btn}>
                          <button
                            onClick={() => handleViewDetails(project.id)}
                            className={projectStyles.viewDetailsBtn}
                          >
                            View Details
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </>
            )}
          </div>

          {totalPages > 1 && (
            <div className={projectStyles.pagination}>
              <button
                onClick={() => paginate(currentPage - 1)}
                disabled={currentPage === 1}
                className={projectStyles.paginationBtn}
              >
                Previous
              </button>
              <span className={projectStyles.paginationInfo}>
                Page {currentPage} of {totalPages}
              </span>
              <button
                onClick={() => paginate(currentPage + 1)}
                disabled={currentPage === totalPages}
                className={projectStyles.paginationBtn}
              >
                Next
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}