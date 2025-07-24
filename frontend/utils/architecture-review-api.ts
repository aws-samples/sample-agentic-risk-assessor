import { api } from './api';

export const saveArchitectureReview = async (projectId: string, reviewContent: string) => {
  try {
    const response = await api.post('/api/architecture-reviews', {
      project_id: projectId,
      review_content: reviewContent
    });
    return { data: response.data, error: null };
  } catch (error: any) {
    console.error('Error saving architecture review:', error);
    return { 
      data: null, 
      error: { 
        message: error.response?.data?.message || 'Failed to save architecture review'
      }
    };
  }
};

export const getArchitectureReviews = async (projectId: string) => {
  try {
    const response = await api.get(`/api/projects/${projectId}/architecture-reviews`);
    return { data: response.data, error: null };
  } catch (error: any) {
    console.error('Error getting architecture reviews:', error);
    return { 
      data: null, 
      error: { 
        message: error.response?.data?.message || 'Failed to get architecture reviews'
      }
    };
  }
};

export const downloadArchitectureReview = async (projectId: string, reviewId: string) => {
  try {
    const response = await api.get(`/api/projects/${projectId}/architecture-reviews/${reviewId}/download`);
    return { data: response.data, error: null };
  } catch (error: any) {
    console.error('Error downloading architecture review:', error);
    return { 
      data: null, 
      error: { 
        message: error.response?.data?.message || 'Failed to download architecture review'
      }
    };
  }
};