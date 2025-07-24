import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';

interface OrganizationProfile {
  id: string;
  name: string;
  createdAt: Date;
  updatedAt: Date;
  filePath: string;
  metadata: {
    industry: string;
    size: string;
    regions: string[];
    completeness: number;
  };
}

interface ProfileSelectorProps {
  profiles: OrganizationProfile[];
  selectedProfile?: string;
  onSelect: (profileId: string) => void;
  onCreateNew?: () => void;
  onEdit?: (profileId: string) => void;
  onDelete?: (profileId: string) => void;
  loading?: boolean;
  error?: string | null;
  showActions?: boolean;
  multiSelect?: boolean;
  selectedProfiles?: string[];
  onMultiSelect?: (profileIds: string[]) => void;
}

export default function ProfileSelector({
  profiles,
  selectedProfile,
  onSelect,
  onCreateNew,
  onEdit,
  onDelete,
  loading = false,
  error = null,
  showActions = true,
  multiSelect = false,
  selectedProfiles = [],
  onMultiSelect
}: ProfileSelectorProps) {
  const router = useRouter();
  const [searchTerm, setSearchTerm] = useState('');
  const [industryFilter, setIndustryFilter] = useState('');
  const [sizeFilter, setSizeFilter] = useState('');
  const [sortBy, setSortBy] = useState<'name' | 'updated' | 'completeness'>('updated');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');

  // Filter and sort profiles
  const filteredProfiles = profiles
    .filter(profile => {
      const matchesSearch = profile.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                           profile.metadata.industry.toLowerCase().includes(searchTerm.toLowerCase());
      const matchesIndustry = !industryFilter || profile.metadata.industry === industryFilter;
      const matchesSize = !sizeFilter || profile.metadata.size === sizeFilter;
      
      return matchesSearch && matchesIndustry && matchesSize;
    })
    .sort((a, b) => {
      let comparison = 0;
      
      switch (sortBy) {
        case 'name':
          comparison = a.name.localeCompare(b.name);
          break;
        case 'updated':
          comparison = new Date(a.updatedAt).getTime() - new Date(b.updatedAt).getTime();
          break;
        case 'completeness':
          comparison = a.metadata.completeness - b.metadata.completeness;
          break;
      }
      
      return sortOrder === 'asc' ? comparison : -comparison;
    });

  // Get unique values for filters
  const industries = Array.from(new Set(profiles.map(p => p.metadata.industry))).filter(Boolean);
  const sizes = Array.from(new Set(profiles.map(p => p.metadata.size))).filter(Boolean);

  const handleProfileClick = (profileId: string) => {
    if (multiSelect && onMultiSelect) {
      const newSelection = selectedProfiles.includes(profileId)
        ? selectedProfiles.filter(id => id !== profileId)
        : [...selectedProfiles, profileId];
      onMultiSelect(newSelection);
    } else {
      onSelect(profileId);
    }
  };

  const handleCreateNew = () => {
    if (onCreateNew) {
      onCreateNew();
    } else {
      router.push('/organization-profiles/new');
    }
  };

  const formatDate = (date: Date) => {
    return new Date(date).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  };

  const getCompletenessColor = (completeness: number) => {
    if (completeness >= 80) return '#28a745';
    if (completeness >= 60) return '#ffc107';
    return '#dc3545';
  };

  if (loading) {
    return (
      <div style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        padding: '3rem',
        color: '#6c757d'
      }}>
        Loading organization profiles...
      </div>
    );
  }

  if (error) {
    return (
      <div style={{
        padding: '2rem',
        backgroundColor: '#f8d7da',
        color: '#721c24',
        border: '1px solid #f5c6cb',
        borderRadius: '8px',
        textAlign: 'center'
      }}>
        <h3 style={{ margin: '0 0 1rem 0' }}>Error Loading Profiles</h3>
        <p style={{ margin: 0 }}>{error}</p>
      </div>
    );
  }

  return (
    <div style={{
      backgroundColor: '#ffffff',
      border: '2px solid #ff6b35',
      borderRadius: '8px',
      overflow: 'hidden'
    }}>
      {/* Header */}
      <div style={{
        padding: '1rem',
        backgroundColor: '#ff6b35',
        color: 'white',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center'
      }}>
        <h2 style={{ margin: 0, fontSize: '1.2rem' }}>
          Organization Profiles ({filteredProfiles.length})
        </h2>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <button
            onClick={() => setViewMode(viewMode === 'grid' ? 'list' : 'grid')}
            style={{
              backgroundColor: 'transparent',
              color: 'white',
              border: '1px solid white',
              borderRadius: '4px',
              padding: '0.25rem 0.5rem',
              fontSize: '0.8rem',
              cursor: 'pointer'
            }}
          >
            {viewMode === 'grid' ? '☰' : '⊞'}
          </button>
          {showActions && (
            <button
              onClick={handleCreateNew}
              style={{
                backgroundColor: 'white',
                color: '#ff6b35',
                border: 'none',
                borderRadius: '4px',
                padding: '0.25rem 0.75rem',
                fontSize: '0.9rem',
                cursor: 'pointer',
                fontWeight: '600'
              }}
            >
              Create New
            </button>
          )}
        </div>
      </div>

      {/* Filters and Search */}
      <div style={{
        padding: '1rem',
        backgroundColor: '#f8f9fa',
        borderBottom: '1px solid #e9ecef'
      }}>
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
          gap: '1rem',
          marginBottom: '1rem'
        }}>
          <input
            type="text"
            placeholder="Search profiles..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            style={{
              padding: '0.5rem',
              border: '1px solid #ced4da',
              borderRadius: '4px',
              fontSize: '0.9rem'
            }}
          />
          
          <select
            value={industryFilter}
            onChange={(e) => setIndustryFilter(e.target.value)}
            style={{
              padding: '0.5rem',
              border: '1px solid #ced4da',
              borderRadius: '4px',
              fontSize: '0.9rem'
            }}
          >
            <option value="">All Industries</option>
            {industries.map(industry => (
              <option key={industry} value={industry}>{industry}</option>
            ))}
          </select>

          <select
            value={sizeFilter}
            onChange={(e) => setSizeFilter(e.target.value)}
            style={{
              padding: '0.5rem',
              border: '1px solid #ced4da',
              borderRadius: '4px',
              fontSize: '0.9rem'
            }}
          >
            <option value="">All Sizes</option>
            {sizes.map(size => (
              <option key={size} value={size}>{size}</option>
            ))}
          </select>

          <select
            value={`${sortBy}-${sortOrder}`}
            onChange={(e) => {
              const [field, order] = e.target.value.split('-');
              setSortBy(field as 'name' | 'updated' | 'completeness');
              setSortOrder(order as 'asc' | 'desc');
            }}
            style={{
              padding: '0.5rem',
              border: '1px solid #ced4da',
              borderRadius: '4px',
              fontSize: '0.9rem'
            }}
          >
            <option value="updated-desc">Recently Updated</option>
            <option value="updated-asc">Oldest First</option>
            <option value="name-asc">Name A-Z</option>
            <option value="name-desc">Name Z-A</option>
            <option value="completeness-desc">Most Complete</option>
            <option value="completeness-asc">Least Complete</option>
          </select>
        </div>

        {(searchTerm || industryFilter || sizeFilter) && (
          <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
            {searchTerm && (
              <span style={{
                backgroundColor: '#ff6b35',
                color: 'white',
                padding: '0.25rem 0.5rem',
                borderRadius: '12px',
                fontSize: '0.8rem'
              }}>
                Search: "{searchTerm}"
                <button
                  onClick={() => setSearchTerm('')}
                  style={{
                    backgroundColor: 'transparent',
                    border: 'none',
                    color: 'white',
                    marginLeft: '0.25rem',
                    cursor: 'pointer'
                  }}
                >
                  ×
                </button>
              </span>
            )}
            {industryFilter && (
              <span style={{
                backgroundColor: '#6c757d',
                color: 'white',
                padding: '0.25rem 0.5rem',
                borderRadius: '12px',
                fontSize: '0.8rem'
              }}>
                Industry: {industryFilter}
                <button
                  onClick={() => setIndustryFilter('')}
                  style={{
                    backgroundColor: 'transparent',
                    border: 'none',
                    color: 'white',
                    marginLeft: '0.25rem',
                    cursor: 'pointer'
                  }}
                >
                  ×
                </button>
              </span>
            )}
            {sizeFilter && (
              <span style={{
                backgroundColor: '#6c757d',
                color: 'white',
                padding: '0.25rem 0.5rem',
                borderRadius: '12px',
                fontSize: '0.8rem'
              }}>
                Size: {sizeFilter}
                <button
                  onClick={() => setSizeFilter('')}
                  style={{
                    backgroundColor: 'transparent',
                    border: 'none',
                    color: 'white',
                    marginLeft: '0.25rem',
                    cursor: 'pointer'
                  }}
                >
                  ×
                </button>
              </span>
            )}
          </div>
        )}
      </div>

      {/* Profile List */}
      <div style={{
        padding: '1rem',
        maxHeight: '600px',
        overflowY: 'auto'
      }}>
        {filteredProfiles.length === 0 ? (
          <div style={{
            textAlign: 'center',
            padding: '3rem',
            color: '#6c757d'
          }}>
            <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>🏢</div>
            <h3 style={{ margin: '0 0 0.5rem 0' }}>No profiles found</h3>
            <p style={{ margin: '0 0 1rem 0' }}>
              {profiles.length === 0 
                ? "You haven't created any organization profiles yet."
                : "No profiles match your current filters."
              }
            </p>
            {showActions && profiles.length === 0 && (
              <button
                onClick={handleCreateNew}
                style={{
                  backgroundColor: '#ff6b35',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  padding: '0.75rem 1.5rem',
                  fontSize: '0.9rem',
                  cursor: 'pointer',
                  fontWeight: '600'
                }}
              >
                Create Your First Profile
              </button>
            )}
          </div>
        ) : (
          <div style={{
            display: viewMode === 'grid' ? 'grid' : 'block',
            gridTemplateColumns: viewMode === 'grid' ? 'repeat(auto-fill, minmax(300px, 1fr))' : '1fr',
            gap: '1rem'
          }}>
            {filteredProfiles.map(profile => (
              <div
                key={profile.id}
                onClick={() => handleProfileClick(profile.id)}
                style={{
                  backgroundColor: (multiSelect ? selectedProfiles.includes(profile.id) : selectedProfile === profile.id) 
                    ? '#fff3e0' : '#ffffff',
                  border: `2px solid ${
                    (multiSelect ? selectedProfiles.includes(profile.id) : selectedProfile === profile.id) 
                      ? '#ff6b35' : '#e9ecef'
                  }`,
                  borderRadius: '8px',
                  padding: '1rem',
                  cursor: 'pointer',
                  transition: 'all 0.2s',
                  display: viewMode === 'list' ? 'flex' : 'block',
                  alignItems: viewMode === 'list' ? 'center' : 'stretch',
                  gap: viewMode === 'list' ? '1rem' : '0'
                }}
                onMouseEnter={(e) => {
                  if (!(multiSelect ? selectedProfiles.includes(profile.id) : selectedProfile === profile.id)) {
                    e.currentTarget.style.borderColor = '#ff6b35';
                    e.currentTarget.style.backgroundColor = '#f8f9fa';
                  }
                }}
                onMouseLeave={(e) => {
                  if (!(multiSelect ? selectedProfiles.includes(profile.id) : selectedProfile === profile.id)) {
                    e.currentTarget.style.borderColor = '#e9ecef';
                    e.currentTarget.style.backgroundColor = '#ffffff';
                  }
                }}
              >
                <div style={{ flex: viewMode === 'list' ? 1 : 'none' }}>
                  <div style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'flex-start',
                    marginBottom: '0.5rem'
                  }}>
                    <h3 style={{
                      margin: 0,
                      fontSize: '1.1rem',
                      color: '#333',
                      fontWeight: '600'
                    }}>
                      {profile.name}
                    </h3>
                    {multiSelect && (
                      <div style={{
                        width: '20px',
                        height: '20px',
                        borderRadius: '3px',
                        border: '2px solid #ff6b35',
                        backgroundColor: selectedProfiles.includes(profile.id) ? '#ff6b35' : 'white',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        color: 'white',
                        fontSize: '0.8rem',
                        fontWeight: 'bold'
                      }}>
                        {selectedProfiles.includes(profile.id) ? '✓' : ''}
                      </div>
                    )}
                  </div>

                  <div style={{
                    display: 'flex',
                    gap: '1rem',
                    marginBottom: '0.75rem',
                    fontSize: '0.9rem',
                    color: '#6c757d'
                  }}>
                    <span>{profile.metadata.industry}</span>
                    <span>•</span>
                    <span>{profile.metadata.size}</span>
                    <span>•</span>
                    <span>{profile.metadata.regions.join(', ')}</span>
                  </div>

                  <div style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    marginBottom: viewMode === 'grid' ? '1rem' : '0'
                  }}>
                    <div style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.5rem'
                    }}>
                      <div style={{
                        width: '60px',
                        height: '8px',
                        backgroundColor: '#e9ecef',
                        borderRadius: '4px',
                        overflow: 'hidden'
                      }}>
                        <div style={{
                          width: `${profile.metadata.completeness}%`,
                          height: '100%',
                          backgroundColor: getCompletenessColor(profile.metadata.completeness),
                          transition: 'width 0.3s'
                        }} />
                      </div>
                      <span style={{
                        fontSize: '0.8rem',
                        color: getCompletenessColor(profile.metadata.completeness),
                        fontWeight: '600'
                      }}>
                        {profile.metadata.completeness}%
                      </span>
                    </div>

                    <span style={{
                      fontSize: '0.8rem',
                      color: '#6c757d'
                    }}>
                      Updated {formatDate(profile.updatedAt)}
                    </span>
                  </div>
                </div>

                {showActions && viewMode === 'grid' && (
                  <div style={{
                    display: 'flex',
                    gap: '0.5rem',
                    marginTop: '1rem'
                  }}>
                    {onEdit && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onEdit(profile.id);
                        }}
                        style={{
                          flex: 1,
                          padding: '0.5rem',
                          backgroundColor: 'transparent',
                          color: '#ff6b35',
                          border: '1px solid #ff6b35',
                          borderRadius: '4px',
                          fontSize: '0.8rem',
                          cursor: 'pointer'
                        }}
                      >
                        Edit
                      </button>
                    )}
                    {onDelete && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          if (confirm(`Are you sure you want to delete "${profile.name}"?`)) {
                            onDelete(profile.id);
                          }
                        }}
                        style={{
                          padding: '0.5rem',
                          backgroundColor: 'transparent',
                          color: '#dc3545',
                          border: '1px solid #dc3545',
                          borderRadius: '4px',
                          fontSize: '0.8rem',
                          cursor: 'pointer'
                        }}
                      >
                        Delete
                      </button>
                    )}
                  </div>
                )}

                {showActions && viewMode === 'list' && (
                  <div style={{
                    display: 'flex',
                    gap: '0.5rem'
                  }}>
                    {onEdit && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onEdit(profile.id);
                        }}
                        style={{
                          padding: '0.25rem 0.75rem',
                          backgroundColor: 'transparent',
                          color: '#ff6b35',
                          border: '1px solid #ff6b35',
                          borderRadius: '4px',
                          fontSize: '0.8rem',
                          cursor: 'pointer'
                        }}
                      >
                        Edit
                      </button>
                    )}
                    {onDelete && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          if (confirm(`Are you sure you want to delete "${profile.name}"?`)) {
                            onDelete(profile.id);
                          }
                        }}
                        style={{
                          padding: '0.25rem 0.75rem',
                          backgroundColor: 'transparent',
                          color: '#dc3545',
                          border: '1px solid #dc3545',
                          borderRadius: '4px',
                          fontSize: '0.8rem',
                          cursor: 'pointer'
                        }}
                      >
                        Delete
                      </button>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}