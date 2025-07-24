import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import styles from '../styles/DiagramAnalysis.module.css';

interface Node {
  id: string;
  type: string;
  name: string;
  description: string;
}

interface Flow {
  id: string;
  source: string;
  target: string;
  type: string;
  description: string;
}

interface NodeControl {
  node_id: string;
  node_name: string;
  node_type: string;
  mapped_controls: any[];
  mapped_at: string;
  status: string;
}

interface DiagramAnalysisTableProps {
  nodes: Node[];
  flows: Flow[];
  nodeControls?: NodeControl[];
  onNodesChange?: (nodes: Node[]) => void;
  onFlowsChange?: (flows: Flow[]) => void;
  editable?: boolean;
  projectId?: string;
  compact?: boolean;
}

const DiagramAnalysisTable: React.FC<DiagramAnalysisTableProps> = ({
  nodes,
  flows,
  nodeControls = [],
  onNodesChange,
  onFlowsChange,
  editable = false,
  projectId,
  compact = false
}) => {
  const router = useRouter();
  const [localNodes, setLocalNodes] = useState<Node[]>(nodes);
  const [localFlows, setLocalFlows] = useState<Flow[]>(flows);
  const [editingNodeId, setEditingNodeId] = useState<string | null>(null);
  const [editingFlowId, setEditingFlowId] = useState<string | null>(null);
  const [openDropdown, setOpenDropdown] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    setLocalNodes(nodes);
  }, [nodes]);

  useEffect(() => {
    setLocalFlows(flows);
  }, [flows]);

  // Listen for refresh events
  useEffect(() => {
    const handleRefresh = (event: CustomEvent) => {
      if (event.detail.projectId === projectId) {
        // Trigger parent component to refetch data
        if (window.location.pathname.includes('/projects/')) {
          window.dispatchEvent(new CustomEvent('refetchProjectData'));
        }
      }
    };
    
    window.addEventListener('refreshDiagram', handleRefresh as EventListener);
    return () => window.removeEventListener('refreshDiagram', handleRefresh as EventListener);
  }, [projectId]);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (openDropdown && !(event.target as Element).closest(`.${styles.dropdownContainer}`)) {
        setOpenDropdown(null);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [openDropdown]);

  const handleNodeChange = (id: string, field: keyof Node, value: string) => {
    const updatedNodes = localNodes.map(node => 
      node.id === id ? { ...node, [field]: value } : node
    );
    setLocalNodes(updatedNodes);
    if (onNodesChange) {
      onNodesChange(updatedNodes);
    }
  };

  const handleFlowChange = (id: string, field: keyof Flow, value: string) => {
    const updatedFlows = localFlows.map(flow => 
      flow.id === id ? { ...flow, [field]: value } : flow
    );
    setLocalFlows(updatedFlows);
    if (onFlowsChange) {
      onFlowsChange(updatedFlows);
    }
  };

  const addNewNode = () => {
    const newNode: Node = {
      id: `node-${Date.now()}`,
      type: 'generic',
      name: 'New Node',
      description: 'Description'
    };
    const updatedNodes = [...localNodes, newNode];
    setLocalNodes(updatedNodes);
    if (onNodesChange) {
      onNodesChange(updatedNodes);
    }
    setEditingNodeId(newNode.id);
  };

  const addNewFlow = () => {
    if (localNodes.length < 2) {
      alert('You need at least two nodes to create a flow');
      return;
    }
    
    const newFlow: Flow = {
      id: `flow-${Date.now()}`,
      source: localNodes[0].id,
      target: localNodes[1].id,
      type: 'connection',
      description: 'Description'
    };
    const updatedFlows = [...localFlows, newFlow];
    setLocalFlows(updatedFlows);
    if (onFlowsChange) {
      onFlowsChange(updatedFlows);
    }
    setEditingFlowId(newFlow.id);
  };

  const deleteNode = (id: string) => {
    // Also delete any flows connected to this node
    const updatedFlows = localFlows.filter(flow => 
      flow.source !== id && flow.target !== id
    );
    setLocalFlows(updatedFlows);
    if (onFlowsChange) {
      onFlowsChange(updatedFlows);
    }
    
    const updatedNodes = localNodes.filter(node => node.id !== id);
    setLocalNodes(updatedNodes);
    if (onNodesChange) {
      onNodesChange(updatedNodes);
    }
  };

  const deleteFlow = (id: string) => {
    const updatedFlows = localFlows.filter(flow => flow.id !== id);
    setLocalFlows(updatedFlows);
    if (onFlowsChange) {
      onFlowsChange(updatedFlows);
    }
  };

  return (
    <div style={{ backgroundColor: '#f8f9fa', border: '1px solid #ff6b35', borderRadius: '8px', padding: '1rem' }}>
      <div style={{ marginBottom: '2rem' }}>
        <h3 style={{ color: '#ff6b35', margin: compact ? '0 0 8px 0' : '0 0 1rem 0', fontSize: '1.1rem' }}>Nodes</h3>
        <table style={{ width: '100%', borderCollapse: 'collapse', backgroundColor: '#ffffff', border: '1px solid #ddd', borderRadius: '4px' }}>
          <thead>
            <tr>
              <th style={{ backgroundColor: '#ff6b35', color: '#ffffff', padding: '0.75rem', textAlign: 'left', fontSize: '1rem', border: 'none' }}>Node ID</th>
              <th style={{ backgroundColor: '#ff6b35', color: '#ffffff', padding: '0.75rem', textAlign: 'left', fontSize: '1rem', border: 'none' }}>Type</th>
              <th style={{ backgroundColor: '#ff6b35', color: '#ffffff', padding: '0.75rem', textAlign: 'left', fontSize: '1rem', border: 'none' }}>Name</th>
              <th style={{ backgroundColor: '#ff6b35', color: '#ffffff', padding: '0.75rem', textAlign: 'left', fontSize: '1rem', border: 'none' }}>Description</th>
              <th style={{ backgroundColor: '#ff6b35', color: '#ffffff', padding: '0.75rem', textAlign: 'left', fontSize: '1rem', border: 'none' }}>Controls</th>
              {editable && <th style={{ backgroundColor: '#ff6b35', color: '#ffffff', padding: '0.75rem', textAlign: 'left', fontSize: '1rem', border: 'none' }}>Actions</th>}
            </tr>
          </thead>
          <tbody>
            {localNodes.map(node => {
              const nodeControl = nodeControls.find(nc => nc.node_id === node.id);
              return (
                <tr key={node.id} style={{ borderBottom: '1px solid #ddd' }}>
                  <td style={{ padding: '0.75rem', fontSize: '0.85rem', backgroundColor: 'transparent' }}>
                    <code style={{ backgroundColor: '#f8f9fa', padding: '0.25rem', borderRadius: '3px', fontSize: '0.8rem' }}>{node.id}</code>
                  </td>
                  <td style={{ padding: '0.75rem', fontSize: '0.85rem', backgroundColor: 'transparent' }}>
                    {editingNodeId === node.id && editable ? (
                      <input
                        type="text"
                        value={node.type}
                        onChange={(e) => handleNodeChange(node.id, 'type', e.target.value)}
                        style={{ width: '100%', padding: '0.25rem', border: '1px solid #ddd', borderRadius: '3px' }}
                      />
                    ) : (
                      node.type
                    )}
                  </td>
                  <td style={{ padding: '0.75rem', fontSize: '0.85rem', backgroundColor: 'transparent' }}>
                    {editingNodeId === node.id && editable ? (
                      <input
                        type="text"
                        value={node.name}
                        onChange={(e) => handleNodeChange(node.id, 'name', e.target.value)}
                        style={{ width: '100%', padding: '0.25rem', border: '1px solid #ddd', borderRadius: '3px' }}
                      />
                    ) : (
                      node.name
                    )}
                  </td>
                  <td style={{ padding: '0.75rem', fontSize: '0.85rem', backgroundColor: 'transparent' }}>
                    {editingNodeId === node.id && editable ? (
                      <input
                        type="text"
                        value={node.description}
                        onChange={(e) => handleNodeChange(node.id, 'description', e.target.value)}
                        style={{ width: '100%', padding: '0.25rem', border: '1px solid #ddd', borderRadius: '3px' }}
                      />
                    ) : (
                      node.description
                    )}
                  </td>
                  <td style={{ padding: '0.75rem', fontSize: '0.85rem', backgroundColor: 'transparent' }}>
                    {nodeControl && nodeControl.mapped_controls.length > 0 ? (
                      <div>
                        {nodeControl.mapped_controls.slice(0, 2).map((control, index) => (
                          <div key={index} style={{ marginBottom: '0.5rem', padding: '0.25rem', backgroundColor: '#f8f9fa', borderRadius: '3px', fontSize: '0.8rem' }}>
                            <strong style={{ color: '#ff6b35' }}>{control.control_id}</strong>: {control.control_name}
                            <br />
                            <small style={{ color: '#666' }}>{control.category} - {control.priority}</small>
                          </div>
                        ))}
                        {nodeControl.mapped_controls.length > 2 && (
                          <div style={{ fontSize: '0.75rem', color: '#666', fontStyle: 'italic' }}>
                            +{nodeControl.mapped_controls.length - 2} more
                          </div>
                        )}
                      </div>
                    ) : (
                      <span style={{ color: '#999', fontStyle: 'italic', fontSize: '0.8rem' }}>No controls mapped</span>
                    )}
                  </td>
                  {editable && (
                    <td style={{ padding: '0.75rem', fontSize: '0.85rem', backgroundColor: 'transparent' }}>
                      <div style={{ position: 'relative' }}>
                        <button 
                          onClick={() => setOpenDropdown(openDropdown === node.id ? null : node.id)}
                          style={{
                            backgroundColor: '#ff6b35',
                            color: '#ffffff',
                            border: 'none',
                            padding: '0.25rem 0.5rem',
                            borderRadius: '4px',
                            fontSize: '0.8rem',
                            cursor: 'pointer'
                          }}
                        >
                          ⋮
                        </button>
                        {openDropdown === node.id && (
                          <div style={{
                            position: 'absolute',
                            top: '100%',
                            right: 0,
                            backgroundColor: '#ffffff',
                            border: '1px solid #ddd',
                            borderRadius: '4px',
                            boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
                            zIndex: 10,
                            minWidth: '120px'
                          }}>
                            {editingNodeId === node.id ? (
                              <button 
                                onClick={() => { setEditingNodeId(null); setOpenDropdown(null); }}
                                style={{
                                  width: '100%',
                                  padding: '0.5rem',
                                  border: 'none',
                                  backgroundColor: 'transparent',
                                  textAlign: 'left',
                                  cursor: 'pointer',
                                  fontSize: '0.8rem'
                                }}
                              >
                                Done
                              </button>
                            ) : (
                              <button 
                                onClick={() => { setEditingNodeId(node.id); setOpenDropdown(null); }}
                                style={{
                                  width: '100%',
                                  padding: '0.5rem',
                                  border: 'none',
                                  backgroundColor: 'transparent',
                                  textAlign: 'left',
                                  cursor: 'pointer',
                                  fontSize: '0.8rem'
                                }}
                              >
                                Edit
                              </button>
                            )}
                            <button 
                              onClick={() => { deleteNode(node.id); setOpenDropdown(null); }}
                              style={{
                                width: '100%',
                                padding: '0.5rem',
                                border: 'none',
                                backgroundColor: 'transparent',
                                textAlign: 'left',
                                cursor: 'pointer',
                                fontSize: '0.8rem',
                                color: '#dc3545'
                              }}
                            >
                              Delete
                            </button>
                            {projectId && (
                              <button 
                                onClick={() => { router.push(`/node-details/${projectId}/${node.id}`); setOpenDropdown(null); }}
                                style={{
                                  width: '100%',
                                  padding: '0.5rem',
                                  border: 'none',
                                  backgroundColor: 'transparent',
                                  textAlign: 'left',
                                  cursor: 'pointer',
                                  fontSize: '0.8rem'
                                }}
                              >
                                View Details
                              </button>
                            )}
                          </div>
                        )}
                      </div>
                    </td>
                  )}
                </tr>
              );
            })}
          </tbody>
        </table>
        {editable && (
          <button 
            onClick={addNewNode}
            style={{
              backgroundColor: '#ff6b35',
              color: '#ffffff',
              border: 'none',
              padding: '0.5rem 1rem',
              borderRadius: '4px',
              fontSize: '0.9rem',
              cursor: 'pointer',
              marginTop: '1rem'
            }}
          >
            Add Node
          </button>
        )}
      </div>

      <div style={{ marginBottom: '2rem' }}>
        <h3 style={{ color: '#ff6b35', margin: compact ? '0 0 8px 0' : '0 0 1rem 0', fontSize: '1.1rem' }}>Flows</h3>
        <table style={{ width: '100%', borderCollapse: 'collapse', backgroundColor: '#ffffff', border: '1px solid #ddd', borderRadius: '4px' }}>
          <thead>
            <tr>
              <th style={{ backgroundColor: '#ff6b35', color: '#ffffff', padding: '0.75rem', textAlign: 'left', fontSize: '0.9rem', border: 'none' }}>Flow ID</th>
              <th style={{ backgroundColor: '#ff6b35', color: '#ffffff', padding: '0.75rem', textAlign: 'left', fontSize: '0.9rem', border: 'none' }}>Source</th>
              <th style={{ backgroundColor: '#ff6b35', color: '#ffffff', padding: '0.75rem', textAlign: 'left', fontSize: '0.9rem', border: 'none' }}>Target</th>
              <th style={{ backgroundColor: '#ff6b35', color: '#ffffff', padding: '0.75rem', textAlign: 'left', fontSize: '0.9rem', border: 'none' }}>Type</th>
              <th style={{ backgroundColor: '#ff6b35', color: '#ffffff', padding: '0.75rem', textAlign: 'left', fontSize: '0.9rem', border: 'none' }}>Description</th>
              {editable && <th style={{ backgroundColor: '#ff6b35', color: '#ffffff', padding: '0.75rem', textAlign: 'left', fontSize: '0.9rem', border: 'none' }}>Actions</th>}
            </tr>
          </thead>
          <tbody>
            {localFlows.map(flow => {
              const sourceNode = localNodes.find(n => n.id === flow.source);
              const targetNode = localNodes.find(n => n.id === flow.target);
              
              return (
                <tr key={flow.id} style={{ borderBottom: '1px solid #ddd' }}>
                  <td style={{ padding: '0.75rem', fontSize: '0.85rem', backgroundColor: 'transparent' }}>
                    <code style={{ backgroundColor: '#f8f9fa', padding: '0.25rem', borderRadius: '3px', fontSize: '0.8rem' }}>{flow.id}</code>
                  </td>
                  <td style={{ padding: '0.75rem', fontSize: '0.85rem', backgroundColor: 'transparent' }}>
                    {editingFlowId === flow.id && editable ? (
                      <select
                        value={flow.source}
                        onChange={(e) => handleFlowChange(flow.id, 'source', e.target.value)}
                      >
                        {localNodes.map(node => (
                          <option key={node.id} value={node.id}>
                            {node.name}
                          </option>
                        ))}
                      </select>
                    ) : (
                      sourceNode?.name || flow.source
                    )}
                  </td>
                  <td style={{ padding: '0.75rem', fontSize: '0.85rem', backgroundColor: 'transparent' }}>
                    {editingFlowId === flow.id && editable ? (
                      <select
                        value={flow.target}
                        onChange={(e) => handleFlowChange(flow.id, 'target', e.target.value)}
                        style={{ width: '100%', padding: '0.25rem', border: '1px solid #ddd', borderRadius: '3px' }}
                      >
                        {localNodes.map(node => (
                          <option key={node.id} value={node.id}>
                            {node.name}
                          </option>
                        ))}
                      </select>
                    ) : (
                      targetNode?.name || flow.target
                    )}
                  </td>
                  <td style={{ padding: '0.75rem', fontSize: '0.85rem', backgroundColor: 'transparent' }}>
                    {editingFlowId === flow.id && editable ? (
                      <input
                        type="text"
                        value={flow.type}
                        onChange={(e) => handleFlowChange(flow.id, 'type', e.target.value)}
                        style={{ width: '100%', padding: '0.25rem', border: '1px solid #ddd', borderRadius: '3px' }}
                      />
                    ) : (
                      flow.type
                    )}
                  </td>
                  <td style={{ padding: '0.75rem', fontSize: '0.85rem', backgroundColor: 'transparent' }}>
                    {editingFlowId === flow.id && editable ? (
                      <input
                        type="text"
                        value={flow.description}
                        onChange={(e) => handleFlowChange(flow.id, 'description', e.target.value)}
                        style={{ width: '100%', padding: '0.25rem', border: '1px solid #ddd', borderRadius: '3px' }}
                      />
                    ) : (
                      flow.description
                    )}
                  </td>
                  {editable && (
                    <td style={{ padding: '0.75rem', fontSize: '0.85rem', backgroundColor: 'transparent' }}>
                      {editingFlowId === flow.id ? (
                        <button 
                          onClick={() => setEditingFlowId(null)}
                          style={{
                            backgroundColor: '#28a745',
                            color: '#ffffff',
                            border: 'none',
                            padding: '0.25rem 0.5rem',
                            borderRadius: '4px',
                            fontSize: '0.8rem',
                            cursor: 'pointer',
                            marginRight: '0.25rem'
                          }}
                        >
                          Done
                        </button>
                      ) : (
                        <button 
                          onClick={() => setEditingFlowId(flow.id)}
                          style={{
                            backgroundColor: '#ff6b35',
                            color: '#ffffff',
                            border: 'none',
                            padding: '0.25rem 0.5rem',
                            borderRadius: '4px',
                            fontSize: '0.8rem',
                            cursor: 'pointer',
                            marginRight: '0.25rem'
                          }}
                        >
                          Edit
                        </button>
                      )}
                      <button 
                        onClick={() => deleteFlow(flow.id)}
                        style={{
                          backgroundColor: '#dc3545',
                          color: '#ffffff',
                          border: 'none',
                          padding: '0.25rem 0.5rem',
                          borderRadius: '4px',
                          fontSize: '0.8rem',
                          cursor: 'pointer'
                        }}
                      >
                        Delete
                      </button>
                    </td>
                  )}
                </tr>
              );
            })}
          </tbody>
        </table>
        {editable && (
          <button 
            onClick={addNewFlow}
            style={{
              backgroundColor: '#ff6b35',
              color: '#ffffff',
              border: 'none',
              padding: '0.5rem 1rem',
              borderRadius: '4px',
              fontSize: '0.9rem',
              cursor: 'pointer',
              marginTop: '1rem'
            }}
          >
            Add Flow
          </button>
        )}
      </div>
    </div>
  );
};

export default DiagramAnalysisTable;