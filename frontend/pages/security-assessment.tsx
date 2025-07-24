import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import Header from '../components/Header';
import SecurityAssessment from '../components/SecurityAssessment';

const SecurityAssessmentPage: React.FC = () => {
  const router = useRouter();
  const { projectId } = router.query;

  return (
    <div className="min-h-screen bg-gray-50">
      <Header />
      <div className="max-w-6xl mx-auto py-8 px-4">
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-gray-900">Security Assessment</h1>
          <p className="text-gray-600 mt-2">
            Comprehensive security evaluation for Project {projectId}
          </p>
          <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded-md">
            <p className="text-sm text-blue-800">
              💡 <strong>How to start:</strong> Use the Security Architect chat to begin the security assessment triage process. 
              The agent will guide you through security questionnaires based on your architecture artifacts.
            </p>
          </div>
        </div>

        <SecurityAssessment projectId={projectId as string} />
      </div>
    </div>
  );
};

export default SecurityAssessmentPage;