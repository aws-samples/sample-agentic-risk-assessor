// semgrep:ignore javascript.lang.security.audit.unsafe-formatstring.unsafe-formatstring: Console logging for debugging only, not user-facing
import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import AuthGuard from '../components/AuthGuard';
import Header from '../components/Header';
import Sidebar from '../components/Sidebar';
import { getServiceControls, runServiceControlsMapping, runServiceMapping, getExecutionStatus, addService } from '../utils/api';
import styles from '../styles/Home.module.css';
import adminStyles from '../styles/Admin.module.css';
import ReactMarkdown from 'react-markdown';

// Normalize text for consistent markdown rendering
function normalizeMarkdown(text: string, isCode?: boolean): string {
  if (!text) return '';
  let s = String(text);
  if (isCode) {
    // Wrap in code fence if not already
    s = s.trim();
    if (!s.startsWith('```')) s = '```bash\n' + s + '\n```';
    return s;
  }
  // Fix inline numbered lists: "1. foo 2. bar" → "1. foo\n2. bar"
  s = s.replace(/(\S)\s+(\d+)\.\s/g, '$1\n$2. ');
  return s;
}

interface ServiceControl {
  id: string;
  name?: string;
  category: string;
  priority: string;
  description: string;
  reason?: string;
  // Service-specific capability fields
  lambda_capability?: string;
  ec2_capability?: string;
  sqs_capability?: string;
  snsCapability?: string;
  vpc_capability?: string;
  s3_capability?: string;
  rds_capability?: string;
  iam_capability?: string;
  kms_capability?: string;
  cloudwatch_capability?: string;
  cloudtrail_capability?: string;
  elb_capability?: string;
  elbCapability?: string;
  autoscaling_capability?: string;
  autoScalingCapability?: string;
  cloudformation_capability?: string;
  cloudFormationCapability?: string;
  apigateway_capability?: string;
  apiGatewayCapability?: string;
  // Allow for any additional capability fields
  [key: string]: any;
}

interface Service {
  ServiceName: string;
  ApplicableControls: ServiceControl[];
  NonApplicableControls: ServiceControl[];
  ProcessedAt: string;
  Status?: string;
}

export default function Admin() {
  const [services, setServices] = useState<Service[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [executionArn, setExecutionArn] = useState('');
  const [executionStatus, setExecutionStatus] = useState('');
  const [isRunning, setIsRunning] = useState(false);
  const [processingServices, setProcessingServices] = useState<{[key: string]: boolean}>({});
  const [activeTab, setActiveTab] = useState<{[key: string]: string}>({});
  const [categoryFilter, setCategoryFilter] = useState('all');
  const [ratingFilter, setRatingFilter] = useState('all');
  const [frameworkFilter, setFrameworkFilter] = useState('all');

  const [showConfirmDialog, setShowConfirmDialog] = useState(false);
  const [confirmAction, setConfirmAction] = useState<() => void>(() => {});
  const [confirmMessage, setConfirmMessage] = useState('');
  const [lastUpdated, setLastUpdated] = useState<Date>(new Date());
  const [isPolling, setIsPolling] = useState(false);
  const [showAddServiceDialog, setShowAddServiceDialog] = useState(false);
  const [newServiceData, setNewServiceData] = useState({
    serviceName: '',
    description: '',
    documentationLink: '',
    isNativeAws: true
  });
  const [isAddingService, setIsAddingService] = useState(false);
  const [showErrorDialog, setShowErrorDialog] = useState(false);
  const [errorDialogMessage, setErrorDialogMessage] = useState('');
  const [tableFilters, setTableFilters] = useState({
    serviceName: '',
    status: '',
    globalSearch: ''
  });
  const [viewMode, setViewMode] = useState<'cards' | 'table'>('cards');
  const [expandedControls, setExpandedControls] = useState<{[key: string]: boolean}>({});
  const [selectedService, setSelectedService] = useState<string>('');
  const [selectedControlIdx, setSelectedControlIdx] = useState<number>(-1);
  const router = useRouter();

  // Background sync without loading state
  const syncServices = async (showLoading = false) => {
    try {
      if (showLoading) setLoading(true);
      const { data, error } = await getServiceControls(frameworkFilter);
      if (error) {
        setError(error.message);
        return;
      }
      
      const newServices = data || [];
      
      // Only update if there are actual changes
      setServices(prevServices => {
        // Check if there are new services or changes to existing services
        const hasNewServices = newServices.length !== prevServices.length;
        const hasChanges = newServices.some((newService: Service) => {
          const oldService = prevServices.find(s => s.ServiceName === newService.ServiceName);
          return !oldService || 
                 oldService.Status !== newService.Status ||
                 oldService.ProcessedAt !== newService.ProcessedAt ||
                 (oldService.ApplicableControls?.length || 0) !== (newService.ApplicableControls?.length || 0);
        });
        
        if (hasNewServices || hasChanges) {
          // Initialize active tabs for new services only
          const newTabs: {[key: string]: string} = {...activeTab};
          newServices.forEach((service: Service) => {
            if (!newTabs[service.ServiceName]) {
              newTabs[service.ServiceName] = 'applicable';
            }
          });
          setActiveTab(newTabs);
          setLastUpdated(new Date());
          return newServices;
        }
        
        return prevServices;
      });
    } catch (err: any) {
      setError(err.message || 'Error fetching services');
      console.error(err);
    } finally {
      if (showLoading) setLoading(false);
    }
  };

  // Show confirmation dialog
  const showConfirmation = (message: string, action: () => void) => {
    setConfirmMessage(message);
    setConfirmAction(() => action);
    setShowConfirmDialog(true);
  };

  // Add new service
  const addNewService = async () => {
    if (!newServiceData.serviceName.trim()) {
      setError('Service name is required');
      return;
    }

    try {
      setIsAddingService(true);
      const { data, error } = await addService(newServiceData);
      
      if (error) {
        setError(error.message);
        return;
      }
      
      // Add new service to state immediately for instant display
      const newService = {
        ServiceName: newServiceData.serviceName,
        Status: 'PENDING',
        ApplicableControls: [],
        NonApplicableControls: [],
        ProcessedAt: new Date().toISOString()
      };
      
      setServices(prevServices => [...prevServices, newService]);
      
      // Initialize active tab for new service
      setActiveTab(prev => ({...prev, [newServiceData.serviceName]: 'applicable'}));
      
      // Reset form and close dialog
      setNewServiceData({
        serviceName: '',
        description: '',
        documentationLink: '',
        isNativeAws: true
      });
      setShowAddServiceDialog(false);
      
      // Update last updated time
      setLastUpdated(new Date());
      
      setError('');
    } catch (err: any) {
      setError(err.message || 'Error adding service');
      console.error(err);
    } finally {
      setIsAddingService(false);
    }
  };

  // Run mapping process for all services
  const runMapping = async () => {
    console.log('runMapping called with frameworkFilter:', frameworkFilter);
    
    // Check if "All" frameworks is selected
    if (frameworkFilter === 'all') {
      console.log('Framework filter is "all", showing error dialog');
      setErrorDialogMessage('Please select a specific framework before running the mapping process. The "All Frameworks" option is only for viewing existing results.');
      setShowErrorDialog(true);
      return;
    }

    try {
      setIsRunning(true);
      console.log('Calling runServiceControlsMapping with framework:', frameworkFilter);
      const { data, error } = await runServiceControlsMapping(frameworkFilter);
      
      if (error) {
        setError(error.message);
        setIsRunning(false);
        return;
      }
      
      setExecutionArn(data.executionArn);
      setExecutionStatus('RUNNING');
      
      // The smart polling will handle status updates automatically
      // No need for separate polling here
    } catch (err: any) {
      setError(err.message || 'Error starting mapping process');
      console.error(err);
      setIsRunning(false);
    }
  };

  // Run mapping process for a specific service
  const runServiceMappingProcess = async (serviceName: string) => {
    // Check if "All" frameworks is selected
    if (frameworkFilter === 'all') {
      setErrorDialogMessage('Please select a specific framework before processing individual services. The "All Frameworks" option is only for viewing existing results.');
      setShowErrorDialog(true);
      return;
    }

    try {
      // Set the service as processing
      setProcessingServices(prev => ({ ...prev, [serviceName]: true }));
      
      // Optimistically update UI immediately
      setServices(prev => 
        prev.map(service => 
          service.ServiceName === serviceName 
            ? { ...service, Status: 'PROCESSING' } 
            : service
        )
      );
      
      const { data, error } = await runServiceMapping(serviceName, frameworkFilter);
      
      if (error) {
        setError(`Error processing ${serviceName}: ${error.message}`);
        setProcessingServices(prev => ({ ...prev, [serviceName]: false }));
        
        // Update failed status immediately
        setServices(prev => 
          prev.map(service => 
            service.ServiceName === serviceName 
              ? { ...service, Status: 'FAILED' } 
              : service
          )
        );
        return;
      }
      else {
        // Finished successfully so we need to set the status as completed
        setIsRunning(false);
        setServices(prev => 
          prev.map(service => 
            service.ServiceName === serviceName 
              ? { ...service, Status: 'COMPLETED' } 
              : service
          )
        )
      }
      
      // The smart polling will handle status updates automatically
      // No need for separate polling here
    } catch (err: any) {
      // nosemgrep
      setError(`Error processing ${serviceName}: ${err.message || 'Unknown error'}`);
      console.error(`Error processing ${serviceName}:`, err);
      setProcessingServices(prev => ({ ...prev, [serviceName]: false }));
      
      // Update failed status immediately
      setServices(prev => 
        prev.map(service => 
          service.ServiceName === serviceName 
            ? { ...service, Status: 'FAILED' } 
            : service
        )
      );
    }
  };

  // Get icon for level fields
  const getLevelIcon = (fieldKey: string) => {
    switch (fieldKey) {
      case 'basic_level': return '🟢';
      case 'managed_level': return '🔵';
      case 'optimized_level': return '🟠';
      case 'predictive_level': return '🟣';
      default: return '';
    }
  };

  // Toggle expanded state for a specific control
  const toggleControlExpansion = (serviceName: string, controlIndex: number) => {
    const key = `${serviceName}-${controlIndex}`;
    setExpandedControls(prev => ({
      ...prev,
      [key]: !prev[key]
    }));
  };

  // Get service status class for styling
  const getServiceStatusClass = (service: Service) => {
    const status = service.Status || 'COMPLETED';
    switch (status) {
      case 'COMPLETED':
      case 'SUCCEEDED':
        return 'statusCompleted';
      case 'PROCESSING':
      case 'RUNNING':
        return 'statusProcessing';
      case 'FAILED':
        return 'statusFailed';
      case 'QUEUED':
        return 'statusPending';
      default:
        return 'statusPending';
    }
  };

  // Get status icon
  const getStatusIcon = (service: Service) => {
    const status = service.Status || 'COMPLETED';
    switch (status) {
      case 'COMPLETE':
      case 'COMPLETED':
      case 'SUCCEEDED':
        return '✅';
      case 'PROCESSING':
      case 'RUNNING':
        return '🔄';
      case 'FAILED':
        return '❌';
      case 'QUEUED':
        return '⏳';
      default:
        return '⏳';
    }
  };

  // Get status label
  const getStatusLabel = (service: Service) => {
    const status = service.Status || 'COMPLETED';
    switch (status) {
      case 'COMPLETE':
      case 'COMPLETED':
      case 'SUCCEEDED':
        return 'Completed';
      case 'PROCESSING':
        return 'Processing with AI';
      case 'RUNNING':
        return 'Running';
      case 'FAILED':
        return 'Failed';
      case 'QUEUED':
        return 'Queued';
      default:
        return 'Pending';
    }
  };

  // Estimate completion time
  const estimateCompletionTime = (service: Service) => {
    const status = service.Status || 'COMPLETED';
    switch (status) {
      case 'COMPLETE':
      case 'COMPLETED':
      case 'SUCCEEDED':
        return 'Ready';
      case 'PROCESSING':
        return 'Est. 2-3 min';
      case 'RUNNING':
        return 'Est. 1-2 min';
      case 'FAILED':
        return 'Click Process to retry';
      case 'QUEUED':
        return 'Waiting in queue';
      default:
        return 'Ready to process';
    }
  };

  // Filter controls based on category and rating
  const filterControls = (controls: ServiceControl[] = []) => {
    if (!controls || !Array.isArray(controls)) return [];
    return controls.filter(control => {
      const categoryMatch = categoryFilter === 'all' || 
        control.category?.toLowerCase().includes(categoryFilter.toLowerCase());
      const ratingMatch = ratingFilter === 'all' || 
        control.priority?.toLowerCase() === ratingFilter.toLowerCase();
      return categoryMatch && ratingMatch;
    });
  };

  // Filter controls within a service based on global search and dropdown filters
  const filterServiceControls = (controls: ServiceControl[]) => {
    if (!controls || !Array.isArray(controls)) return [];
    return controls.filter(control => {
      if (!control) return false;
      
      // Global search filter
      const globalMatch = !tableFilters.globalSearch || (
        control.category?.toLowerCase().includes(tableFilters.globalSearch.toLowerCase()) ||
        control.description?.toLowerCase().includes(tableFilters.globalSearch.toLowerCase()) ||
        control.priority?.toLowerCase().includes(tableFilters.globalSearch.toLowerCase()) ||
        control.id?.toLowerCase().includes(tableFilters.globalSearch.toLowerCase()) ||
        control.name?.toLowerCase().includes(tableFilters.globalSearch.toLowerCase())
      );
      
      // Category filter
      const categoryMatch = categoryFilter === 'all' || 
        control.category?.toLowerCase().includes(categoryFilter.toLowerCase());
      
      // Rating/Priority filter
      const ratingMatch = ratingFilter === 'all' || 
        control.priority?.toLowerCase() === ratingFilter.toLowerCase();
      
      return globalMatch && categoryMatch && ratingMatch;
    });
  };

  // Filter services based on table filters
  const filterServices = (services: Service[]) => {
    return services.filter(service => {
      // Service name filter
      // const serviceNameMatch = !tableFilters.serviceName || 
      //   service.ServiceName.toLowerCase().includes(tableFilters.serviceName.toLowerCase());
      
      // Status filter
      // const statusMatch = !tableFilters.status || 
      //   getStatusLabel(service).toLowerCase().includes(tableFilters.status.toLowerCase());
      
      // Global search across all text in service and controls
      const globalMatch = !tableFilters.globalSearch || (
        service.ServiceName.toLowerCase().includes(tableFilters.globalSearch.toLowerCase()) ||
        getStatusLabel(service).toLowerCase().includes(tableFilters.globalSearch.toLowerCase()) ||
        estimateCompletionTime(service).toLowerCase().includes(tableFilters.globalSearch.toLowerCase()) ||
        service.ApplicableControls?.some(control => 
          control && (
            control.category?.toLowerCase().includes(tableFilters.globalSearch.toLowerCase()) ||
            control.description?.toLowerCase().includes(tableFilters.globalSearch.toLowerCase()) ||
            control.priority?.toLowerCase().includes(tableFilters.globalSearch.toLowerCase()) ||
            control.id?.toLowerCase().includes(tableFilters.globalSearch.toLowerCase()) ||
            control.name?.toLowerCase().includes(tableFilters.globalSearch.toLowerCase())
          )
        )
      );
      
      // Check if service has any controls that match dropdown filters
      const hasMatchingControls = categoryFilter === 'all' && ratingFilter === 'all' ? true :
        service.ApplicableControls?.some(control => {
          if (!control) return false;
          const categoryMatch = categoryFilter === 'all' || 
            control.category?.toLowerCase().includes(categoryFilter.toLowerCase());
          const ratingMatch = ratingFilter === 'all' || 
            control.priority?.toLowerCase() === ratingFilter.toLowerCase();
          return categoryMatch && ratingMatch;
        });
      
      return globalMatch && hasMatchingControls;
    });
  };

  // Get progress summary text
  const getProgressSummary = () => {
    const completed = services.filter(s => s.Status === 'COMPLETE' || s.Status === 'COMPLETED' || s.Status === 'SUCCEEDED').length;
    const processing = services.filter(s => s.Status === 'PROCESSING' || s.Status === 'RUNNING').length;
    const failed = services.filter(s => s.Status === 'FAILED').length;
    const queued = services.filter(s => s.Status === 'QUEUED').length;
    const total = services.length;
    
    // Show initializing only when process just started and no services are processing yet
    if (isRunning && total === 0) {
      return 'Initializing mapping process...';
    }
    
    // Show completed when all services are done (no queued or processing)
    if (processing === 0 && queued === 0 && total > 0 && (completed + failed) === total && !isRunning) {
      return `Completed • ${completed} successful • ${failed > 0 ? `${failed} failed • ` : ''}${total} total services`;
    }
    
    // Show processing status
    if (processing > 0 || queued > 0) {
      return `Processing ${processing} service${processing > 1 ? 's' : ''} • ${completed} of ${total} completed • ${queued} queued`;
    }
    
    // Show failure summary if there are failures
    if (failed > 0) {
      return `${completed} completed • ${failed} failed • ${total} total services`;
    }
    
    return `${completed} of ${total} services ready`;
  };

  // Get progress percentage
  const getProgressPercentage = () => {
    if (services.length === 0) {
      return isRunning ? 5 : 0; // Show small progress when initializing
    }
    const completed = services.filter(s => s.Status === 'COMPLETED' || s.Status === 'SUCCEEDED').length;
    const processing = services.filter(s => s.Status === 'PROCESSING' || s.Status === 'RUNNING').length;
    const failed = services.filter(s => s.Status === 'FAILED').length;
    const queued = services.filter(s => s.Status === 'QUEUED').length;
    const total = services.length;
    
    // If all services are done (no queued or processing), show 100%
    if (processing === 0 && queued === 0 && total > 0 && (completed + failed) === total) {
      return 100;
    }
    
    return Math.round((completed / total) * 100);
  };

  // Get category CSS class
  const getCategoryClass = (category: string) => {
    if (!category) return '';
    
    if (category.toLowerCase().includes('identity')) return adminStyles.identity;
    if (category.toLowerCase().includes('infrastructure')) return adminStyles.infrastructure;
    if (category.toLowerCase().includes('data')) return adminStyles.data;
    if (category.toLowerCase().includes('logging')) return adminStyles.logging;
    if (category.toLowerCase().includes('incident')) return adminStyles.incident;
    if (category.toLowerCase().includes('application')) return adminStyles.application;
    
    return '';
  };

  // Background polling without visual disruption
  useEffect(() => {
    const intervalId = setInterval(() => {
      syncServices(false); // Background sync without loading state
    }, 15000);

    return () => clearInterval(intervalId);
  }, [frameworkFilter]);

  // Check if actively processing
  useEffect(() => {
    const hasActiveProcessing = services.some(service => 
      service.Status === 'PROCESSING' || service.Status === 'RUNNING'
    ) || Object.values(processingServices).some(Boolean);
    
    setIsPolling(hasActiveProcessing || isRunning);
    
    // Reset isRunning when no services are actively processing
    if (isRunning && !hasActiveProcessing && services.length > 0) {
      setIsRunning(false);
    }
  }, [services, isRunning, processingServices]);

  // Initial load with loading state
  useEffect(() => {
    syncServices(true); // Show loading only on initial load
  }, [frameworkFilter]);

  return (
    <AuthGuard>
      <div style={{ 
        fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
        backgroundColor: '#e4e4e4',
        color: '#000000',
        lineHeight: 1.6,
        height: '100vh',
        display: 'flex'
      }}>
        <Sidebar activePage="admin" />

        {/* Main Area */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
          
            {/* Compact toolbar */}
            <div className={adminStyles.compactToolbar}>
              <span className={adminStyles.compactToolbarTitle}>Service Controls Mapping</span>
              <select className={adminStyles.filterSelect} value={frameworkFilter} onChange={(e) => setFrameworkFilter(e.target.value)}>
                <option value="all">All Frameworks</option>
                <option value="nist">NIST 800-53 Rev 5</option>
                <option value="iso27001">ISO 27001:2022</option>
                <option value="soc2">SOC 2 Type II</option>
                <option value="cis">CIS Controls v8</option>
                <option value="pci_dss">PCI DSS 4.0</option>
                <option value="hipaa">HIPAA Security Rule</option>
                <option value="cps234">APRA CPS 234</option>
                <option value="essential8">ACSC Essential Eight</option>
                <option value="cri">CRI Profile 2.0</option>
              </select>
              <span className={adminStyles.compactToolbarSep}></span>
              <button onClick={() => showConfirmation('Re-run mapping for ALL services?', runMapping)} disabled={isRunning} className={`${adminStyles.toolbarBtn} ${adminStyles.primary}`}>
                🔄 {isRunning ? 'Processing...' : 'Run All'}
              </button>
              <button onClick={() => setShowAddServiceDialog(true)} disabled={isRunning} className={`${adminStyles.toolbarBtn} ${adminStyles.outline}`}>
                ➕ Add Service
              </button>
              <span className={adminStyles.compactToolbarSep}></span>
              <span className={adminStyles.compactToolbarStatus}>🎯 {services.length} services · ⏱️ {lastUpdated.toLocaleTimeString()}</span>
            </div>

            {(isRunning || isPolling || services.some(s => s.Status === 'PROCESSING' || s.Status === 'RUNNING' || s.Status === 'QUEUED')) && (
              <div className={adminStyles.progressSummary}>
                <div className={adminStyles.progressInfo}>
                  <span className={adminStyles.progressText}>{getProgressSummary()}</span>
                  <div className={adminStyles.progressBar}>
                    <div className={adminStyles.progressFill} style={{ width: `${getProgressPercentage()}%` }}></div>
                  </div>
                </div>
              </div>
            )}

            {error && <p className={styles.error}>{error}</p>}

            {loading ? (
                <p style={{padding:'2rem',textAlign:'center',color:'#999'}}>Loading services...</p>
              ) : services.length > 0 ? (
                <>
                  {/* Master-Detail Layout */}
                  <div className={adminStyles.masterDetail}>
                    {/* Left column: services + controls */}
                    <div className={adminStyles.leftCol}>
                      <div className={adminStyles.svcList}>
                        {filterServices(services).map((service) => (
                          <div
                            key={service.ServiceName}
                            className={`${adminStyles.svcItem} ${selectedService === service.ServiceName ? adminStyles.svcItemActive : ''}`}
                            onClick={() => { setSelectedService(service.ServiceName); setSelectedControlIdx(-1); }}
                          >
                            <span className={`${adminStyles.statusDot} ${adminStyles[getServiceStatusClass(service)]}`}></span>
                            <span className={adminStyles.svcName}>{service.ServiceName}</span>
                            <span className={adminStyles.svcCount}>{service.ApplicableControls?.length || '—'}</span>
                            <button
                              className={adminStyles.svcRerun}
                              onClick={(e) => {
                                e.stopPropagation();
                                showConfirmation(
                                  `Re-run mapping for ${service.ServiceName}?`,
                                  () => runServiceMappingProcess(service.ServiceName)
                                );
                              }}
                              disabled={processingServices[service.ServiceName] || isRunning}
                            >
                              {processingServices[service.ServiceName] ? '⏳' : '🔄'}
                            </button>
                            {service.ApplicableControls?.length > 0 && (
                              <button
                                className={adminStyles.svcRerun}
                                onClick={async (e) => {
                                  e.stopPropagation();
                                  const safeName = service.ServiceName.replace(/ /g, '_').replace(/\//g, '_');
                                  const fw = frameworkFilter === 'all' ? 'nist' : frameworkFilter;
                                  try {
                                    const axios = (await import('axios')).default;
                                    const { Auth } = await import('aws-amplify');
                                    const session = await Auth.currentSession();
                                    const token = session.getIdToken().getJwtToken();
                                    const resp = await axios.get(`/api/reference/${fw}/${safeName}`, {
                                      headers: { 'Authorization': `Bearer ${token}` },
                                      responseType: 'text'
                                    });
                                    const blob = new Blob([resp.data], { type: 'text/html' });
                                    window.open(URL.createObjectURL(blob), '_blank');
                                  } catch {
                                    alert('Reference not generated yet. Run control mapping first.');
                                  }
                                }}
                                title="View Control Reference"
                              >
                                📄
                              </button>
                            )}
                          </div>
                        ))}
                      </div>
                      {/* Control list for selected service */}
                      {selectedService && (() => {
                        const svc = services.find(s => s.ServiceName === selectedService);
                        const controls = svc ? filterServiceControls(svc.ApplicableControls) : [];
                        return (
                          <div className={adminStyles.ctrlList}>
                            <div className={adminStyles.ctrlListHeader}>
                              <span>{selectedService}</span>
                              <span className={adminStyles.ctrlListSub}>{controls.length} controls</span>
                            </div>
                            <div className={adminStyles.ctrlScroll}>
                              {controls.map((control, idx) => (
                                <div
                                  key={idx}
                                  className={`${adminStyles.ctrlCard} ${selectedControlIdx === idx ? adminStyles.ctrlCardActive : ''}`}
                                  onClick={() => setSelectedControlIdx(idx)}
                                >
                                  <div className={adminStyles.ctrlTop}>
                                    <span className={adminStyles.ctrlId}>{control.id}</span>
                                    <span className={`${adminStyles.badge} ${adminStyles['badge' + (control.priority?.charAt(0).toUpperCase() + control.priority?.slice(1).toLowerCase())]}`}>
                                      {control.priority}
                                    </span>
                                  </div>
                                  <div className={adminStyles.ctrlName}>{control.name || control.id}</div>
                                  <div className={adminStyles.ctrlMeta}>
                                    {control.criticality_score && <span>⚡{control.criticality_score}/10</span>}
                                    {control.complexity && <span>🔧{control.complexity}</span>}
                                  </div>
                                </div>
                              ))}
                            </div>
                          </div>
                        );
                      })()}
                    </div>
                    {/* Right: detail panel */}
                    <div className={adminStyles.detailPanel}>
                      {selectedService && selectedControlIdx >= 0 ? (() => {
                        const svc = services.find(s => s.ServiceName === selectedService);
                        const controls = svc ? filterServiceControls(svc.ApplicableControls) : [];
                        const control = controls[selectedControlIdx];
                        if (!control) return <div className={adminStyles.detailEmpty}>Control not found</div>;

                        const levelFields = [
                          { key: 'basic_level', label: 'Basic', cls: 'lBasic' },
                          { key: 'managed_level', label: 'Managed', cls: 'lManaged' },
                          { key: 'optimized_level', label: 'Optimized', cls: 'lOptimized' },
                          { key: 'predictive_level', label: 'Predictive', cls: 'lPredictive' },
                        ];
                        const sections = [
                          { icon: '📐', title: 'Requirement', key: 'requirement' },
                          { icon: '📋', title: 'Description', key: 'description' },
                          { icon: '✅', title: 'Validation', key: 'validation_procedures' },
                          { icon: '🚀', title: 'Approach', key: 'implementation_approach' },
                          { icon: '🔧', title: 'Capabilities', key: 'capabilities' },
                          { icon: '💻', title: 'CLI Commands', key: 'cli_commands' },
                          { icon: '📝', title: 'Prerequisites', key: 'prerequisites' },
                          { icon: '⚠️', title: 'Conflicts', key: 'conflicts' },
                          { icon: '🔍', title: 'Audit Evidence', key: 'audit_evidence' },
                          { icon: '🤖', title: 'Automated Checks', key: 'automated_checks' },
                          { icon: '📡', title: 'Monitoring', key: 'monitoring_setup' },
                        ];

                        return (
                          <>
                            <div className={adminStyles.detailHeader}>
                              <div className={adminStyles.detailTitle}>
                                <span className={adminStyles.detailHl}>{control.id}</span> — {control.name || control.category}
                              </div>
                              <div className={adminStyles.detailBadges}>
                                {control.priority && <div className={adminStyles.detailBadge}><span className={adminStyles.detailBadgeLabel}>Priority</span><span className={`${adminStyles.badge} ${adminStyles['badge' + (control.priority?.charAt(0).toUpperCase() + control.priority?.slice(1).toLowerCase())]}`}>{control.priority}</span></div>}
                                {control.criticality_score && <div className={adminStyles.detailBadge}><span className={adminStyles.detailBadgeLabel}>Criticality</span><span className={adminStyles.detailBadgeValue}>{control.criticality_score}/10</span></div>}
                                {control.complexity && <div className={adminStyles.detailBadge}><span className={adminStyles.detailBadgeLabel}>Complexity</span><span className={adminStyles.detailBadgeValue}>{control.complexity}</span></div>}
                                {control.cost_category && <div className={adminStyles.detailBadge}><span className={adminStyles.detailBadgeLabel}>Cost</span><span className={adminStyles.detailBadgeValue}>{control.cost_category}</span></div>}
                              </div>
                            </div>
                            <div className={adminStyles.detailBody}>
                              {/* 1. Requirement */}
                              {control.requirement && String(control.requirement).trim() && (
                                <div className={adminStyles.section}>
                                  <div className={adminStyles.sectionTitle}>📐 Requirement</div>
                                  <div className={adminStyles.sectionContent}><ReactMarkdown>{normalizeMarkdown(String(control.requirement))}</ReactMarkdown></div>
                                </div>
                              )}
                              {/* 2. Description */}
                              {control.description && String(control.description).trim() && (
                                <div className={adminStyles.section}>
                                  <div className={adminStyles.sectionTitle}>📋 Description</div>
                                  <div className={adminStyles.sectionContent}><ReactMarkdown>{normalizeMarkdown(String(control.description))}</ReactMarkdown></div>
                                </div>
                              )}
                              {/* 3. Implementation Levels */}
                              {levelFields.some(l => control[l.key]) && (
                                <div className={adminStyles.section}>
                                  <div className={adminStyles.sectionTitle}>📊 Implementation Levels</div>
                                  <div className={adminStyles.implLevels}>
                                    {levelFields.map(l => control[l.key] && (
                                      <div key={l.key} className={`${adminStyles.implLevel} ${adminStyles[l.cls]}`}>
                                        <div className={adminStyles.implLevelLabel}>● {l.label}</div>
                                        <div className={adminStyles.sectionContent}>
                                          <ReactMarkdown>{normalizeMarkdown(String(control[l.key]))}</ReactMarkdown>
                                        </div>
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              )}
                              {/* 4. Validation + rest */}
                              {sections.filter(s => s.key !== 'requirement' && s.key !== 'description').map(s => control[s.key] && String(control[s.key]).trim() && (
                                <div key={s.key} className={adminStyles.section}>
                                  <div className={adminStyles.sectionTitle}>{s.icon} {s.title}</div>
                                  <div className={adminStyles.sectionContent}>
                                    <ReactMarkdown>{normalizeMarkdown(String(control[s.key]), s.key === 'cli_commands')}</ReactMarkdown>
                                  </div>
                                </div>
                              ))}
                            </div>
                          </>
                        );
                      })() : (
                        <div className={adminStyles.detailEmpty}>
                          {selectedService ? '← Select a control' : '← Select a service, then a control'}
                        </div>
                      )}
                    </div>
                  </div>
                </>
              ) : (
                <p style={{padding:'2rem',textAlign:'center',color:'#999'}}>No services found. Run the mapping process to generate service controls.</p>
              )}

        </div>
        
        {/* Confirmation Dialog */}
        {showConfirmDialog && (
          <div className={adminStyles.modalOverlay}>
            <div className={adminStyles.modalContent}>
              <h3>Confirm Action</h3>
              <p>{confirmMessage}</p>
              <div className={adminStyles.modalButtons}>
                <button 
                  className={adminStyles.cancelButton}
                  onClick={() => setShowConfirmDialog(false)}
                >
                  Cancel
                </button>
                <button 
                  className={adminStyles.confirmButton}
                  onClick={() => {
                    setShowConfirmDialog(false);
                    confirmAction();
                  }}
                >
                  Yes, Proceed
                </button>
              </div>
            </div>
          </div>
        )}
        
        {/* Error Dialog */}
        {showErrorDialog && (
          <div className={adminStyles.modalOverlay}>
            <div className={adminStyles.modalContent}>
              <h3>Framework Selection Required</h3>
              <p>{errorDialogMessage}</p>
              <div className={adminStyles.modalButtons}>
                <button 
                  className={adminStyles.confirmButton}
                  onClick={() => setShowErrorDialog(false)}
                >
                  OK
                </button>
              </div>
            </div>
          </div>
        )}
        
        {/* Add Service Dialog */}
        {showAddServiceDialog && (
          <div className={adminStyles.modalOverlay}>
            <div className={adminStyles.modalContent}>
              <h3>Add New Service</h3>
              <div className={adminStyles.formGroup}>
                <label>Service Name *</label>
                <input
                  type="text"
                  value={newServiceData.serviceName}
                  onChange={(e) => setNewServiceData({...newServiceData, serviceName: e.target.value})}
                  placeholder="e.g., CloudFront, DynamoDB"
                  className={adminStyles.formInput}
                />
              </div>
              <div className={adminStyles.formGroup}>
                <label>Description</label>
                <textarea
                  value={newServiceData.description}
                  onChange={(e) => setNewServiceData({...newServiceData, description: e.target.value})}
                  placeholder="Brief description of the service"
                  className={adminStyles.formTextarea}
                  rows={3}
                />
              </div>
              <div className={adminStyles.formGroup}>
                <label>Documentation Link</label>
                <input
                  type="url"
                  value={newServiceData.documentationLink}
                  onChange={(e) => setNewServiceData({...newServiceData, documentationLink: e.target.value})}
                  placeholder="https://docs.aws.amazon.com/..."
                  className={adminStyles.formInput}
                />
              </div>
              <div className={adminStyles.formGroup}>
                <label className={adminStyles.checkboxLabel}>
                  <input
                    type="checkbox"
                    checked={newServiceData.isNativeAws}
                    onChange={(e) => setNewServiceData({...newServiceData, isNativeAws: e.target.checked})}
                    className={adminStyles.formCheckbox}
                  />
                  Native AWS Service
                </label>
              </div>
              <div className={adminStyles.modalButtons}>
                <button 
                  className={adminStyles.cancelButton}
                  onClick={() => {
                    setShowAddServiceDialog(false);
                    setNewServiceData({
                      serviceName: '',
                      description: '',
                      documentationLink: '',
                      isNativeAws: true
                    });
                  }}
                  disabled={isAddingService}
                >
                  Cancel
                </button>
                <button 
                  className={adminStyles.confirmButton}
                  onClick={addNewService}
                  disabled={isAddingService || !newServiceData.serviceName.trim()}
                >
                  {isAddingService ? 'Adding...' : 'Add Service'}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </AuthGuard>
  );
}