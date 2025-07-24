/**
 * Enhanced Profile Builder with Document Management
 * Extends VoiceInteractiveProfileBuilder with document upload, processing, and extraction features
 */
import React, { useState, useEffect, useRef } from 'react';
import { DocumentPanel } from './DocumentPanel';
import { PrePopulatedAnswersCard } from './PrePopulatedAnswersCard';
import { ConflictResolutionCard } from './ConflictResolutionCard';
import { DocumentReference } from './DocumentReference';

// Document-related interfaces
interface Document {
  document_id: string;
  document_name: string;
  upload_time: string;
  processing_status: string;
  page_count?: number;
  file_size?: number;
}

interface PrePopulatedAnswer {
  field: string;
  value: string;
  source: {
    document_id: string;
    document_name: string;
    page_number: number;
    section: string;
    confidence: number;
  };
}

interface ConflictingValue {
  value: string;
  source: {
    document_id: string;
    document_name: string;
    page_number: number;
    section: string;
    confidence: number;
  };
}

interface Conflict {
  field: string;
  values: ConflictingValue[];
}

interface DocumentEnhancementProps {
  profileId: string;
  websocket: WebSocket | null;
  onDocumentProcessed?: (documentId: string) => void;
  onDocumentError?: (documentId: string, error: string) => void;
}

export const useDocumentEnhancement = ({ profileId, websocket, onDocumentProcessed, onDocumentError }: DocumentEnhancementProps) => {
  // Document state
  const [documents, setDocuments] = useState<Document[]>([]);
  const [processingStatus, setProcessingStatus] = useState<Map<string, string>>(new Map());
  const [uploadingDocument, setUploadingDocument] = useState(false);
  const [selectedDocumentId, setSelectedDocumentId] = useState<string | null>(null);
  
  // Pre-populated answers and conflicts
  const [prePopulatedAnswers, setPrePopulatedAnswers] = useState<PrePopulatedAnswer[]>([]);
  const [conflicts, setConflicts] = useState<Conflict[]>([]);
  
  // Auto-populate suggestions
  const [autoPopulateSuggestions, setAutoPopulateSuggestions] = useState<any[]>([]);
  
  // Document panel visibility
  const [showDocumentPanel, setShowDocumentPanel] = useState(true);
  
  // Use ref to track current profileId so it always has the latest value
  const profileIdRef = useRef(profileId);
  useEffect(() => {
    profileIdRef.current = profileId;
  }, [profileId]);

  // Handle document upload
  const handleDocumentUpload = async (file: File) => {
    if (!websocket || websocket.readyState !== WebSocket.OPEN) {
      console.error('WebSocket not connected');
      alert('Please wait for connection to establish');
      return;
    }

    setUploadingDocument(true);
    
    // Generate document ID outside try block so it's accessible in catch
    const documentId = `doc_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

    try {
      // Convert file to base64
      const base64Content = await fileToBase64(file);
      
      // Add document to list with pending status
      const newDocument: Document = {
        document_id: documentId,
        document_name: file.name,
        upload_time: new Date().toISOString(),
        processing_status: 'completed' as const,
        file_size: file.size
      };
      
      setDocuments(prev => [...prev, newDocument]);
      
      // Send upload request via WebSocket
      websocket.send(JSON.stringify({
        type: 'upload_document',
        profile_id: profileIdRef.current,
        document_id: documentId,
        document_name: file.name,
        document_content_base64: base64Content
      }));
      
      console.log(`Document upload request sent: ${file.name}`);
      
    } catch (error) {
      console.error('Document upload failed:', error);
      alert(`Failed to upload document: ${error}`);
      
      // Remove failed document from list
      setDocuments(prev => prev.filter(doc => doc.document_id === documentId));
    } finally {
      setUploadingDocument(false);
    }
  };

  // Handle WebSocket messages for documents
  const handleDocumentMessage = (data: any) => {
    switch (data.type) {
      case 'document_processing_status':
        setProcessingStatus(prev => {
          const newMap = new Map(prev);
          newMap.set(data.document_id, data.status);
          return newMap;
        });
        
        // Update document in list
        setDocuments(prev => prev.map(doc => 
          doc.document_id === data.document_id
            ? { ...doc, processing_status: data.status }
            : doc
        ));
        break;
        
      case 'document_processing_complete':
        setProcessingStatus(prev => {
          const newMap = new Map(prev);
          newMap.set(data.document_id, 'completed');
          return newMap;
        });
        
        setDocuments(prev => prev.map(doc => 
          doc.document_id === data.document_id
            ? { 
                ...doc, 
                processing_status: 'completed',
                tree_generated: true,
                page_count: data.page_count
              }
            : doc
        ));
        
        if (onDocumentProcessed) {
          onDocumentProcessed(data.document_id);
        }
        break;
        
      case 'document_processing_failed':
        setProcessingStatus(prev => {
          const newMap = new Map(prev);
          newMap.set(data.document_id, 'failed');
          return newMap;
        });
        
        setDocuments(prev => prev.map(doc => 
          doc.document_id === data.document_id
            ? { 
                ...doc, 
                processing_status: 'failed',
                error_message: data.error
              }
            : doc
        ));
        
        // Call error callback if provided
        if (onDocumentError) {
          onDocumentError(data.document_id, data.error || 'Document processing failed');
        }
        break;
        
      case 'pre_populated_answers':
        setPrePopulatedAnswers(data.answers || []);
        break;
        
      case 'conflicting_answers':
        setConflicts(data.conflicts || []);
        break;
        
      case 'auto_populate_suggestions':
        setAutoPopulateSuggestions(data.suggestions || []);
        break;
    }
  };

  // Handle pre-populated answer confirmation
  const handleConfirmPrePopulated = async (field: string, confirmed: boolean, editedValue?: string) => {
    if (!websocket || websocket.readyState !== WebSocket.OPEN) return;

    websocket.send(JSON.stringify({
      type: 'confirm_pre_populated_answer',
      field,
      confirmed,
      edited_value: editedValue
    }));

    // Remove from pre-populated list
    setPrePopulatedAnswers(prev => prev.filter(a => a.field !== field));
  };

  // Handle conflict resolution
  const handleResolveConflict = async (field: string, selectedValue: string, sourceDocId: string) => {
    if (!websocket || websocket.readyState !== WebSocket.OPEN) return;

    websocket.send(JSON.stringify({
      type: 'resolve_conflict',
      field,
      selected_value: selectedValue,
      source_document_id: sourceDocId
    }));

    // Remove from conflicts list
    setConflicts(prev => prev.filter(c => c.field !== field));
  };

  // Handle document selection
  const handleDocumentSelect = (documentId: string) => {
    setSelectedDocumentId(documentId);
  };

  // Handle document reference click
  const handleDocumentReferenceClick = (documentId: string) => {
    setSelectedDocumentId(documentId);
    setShowDocumentPanel(true);
  };

  return {
    // State
    documents,
    processingStatus,
    uploadingDocument,
    selectedDocumentId,
    prePopulatedAnswers,
    conflicts,
    autoPopulateSuggestions,
    showDocumentPanel,
    
    // Handlers
    handleDocumentUpload,
    handleDocumentMessage,
    handleConfirmPrePopulated,
    handleResolveConflict,
    handleDocumentSelect,
    handleDocumentReferenceClick,
    setShowDocumentPanel,
    setSelectedDocumentId
  };
};

// Helper function to convert file to base64
const fileToBase64 = (file: File): Promise<string> => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.readAsDataURL(file);
    reader.onload = () => {
      const result = reader.result as string;
      // Remove data URL prefix (e.g., "data:application/pdf;base64,")
      const base64 = result.split(',')[1];
      resolve(base64);
    };
    reader.onerror = error => reject(error);
  });
};

// Export components for use in VoiceInteractiveProfileBuilder
export {
  DocumentPanel,
  PrePopulatedAnswersCard,
  ConflictResolutionCard,
  DocumentReference
};
