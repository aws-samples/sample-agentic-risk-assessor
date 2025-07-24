import axios from 'axios';
import { api } from './api';

// Upload document to a project
export const uploadProjectDocument = async (projectId: string, file: File) => {
  try {
    // Convert file to base64
    const fileBase64 = await fileToBase64(file);
    
    // Check if it's a Word document
    const isWordDoc = file.name.toLowerCase().endsWith('.docx');
    const endpoint = isWordDoc ? '/api/document/word' : '/api/document';
    
    // Send to appropriate API endpoint
    const response = await api.post(endpoint, {
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