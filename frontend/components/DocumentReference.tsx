import React, { useState } from 'react';

interface DocumentReferenceProps {
  documentName: string;
  pageNumber: number;
  section: string;
  confidence?: number;
  onClick?: () => void;
}

export const DocumentReference: React.FC<DocumentReferenceProps> = ({
  documentName,
  pageNumber,
  section,
  confidence,
  onClick
}) => {
  const [showTooltip, setShowTooltip] = useState(false);

  return (
    <span
      className="document-reference inline-flex items-center gap-1 px-2 py-1 bg-blue-50 text-blue-700 rounded text-sm cursor-pointer hover:bg-blue-100 transition-colors relative"
      onClick={onClick}
      onMouseEnter={() => setShowTooltip(true)}
      onMouseLeave={() => setShowTooltip(false)}
    >
      {/* Document Icon */}
      <svg
        className="w-4 h-4"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
        />
      </svg>

      {/* Reference Text */}
      <span className="font-medium">
        {documentName.length > 20 ? `${documentName.substring(0, 20)}...` : documentName}
      </span>
      <span className="text-blue-600">p.{pageNumber}</span>

      {/* Confidence Badge */}
      {confidence !== undefined && confidence < 0.9 && (
        <span className="text-xs bg-yellow-100 text-yellow-700 px-1 rounded">
          {Math.round(confidence * 100)}%
        </span>
      )}

      {/* Tooltip */}
      {showTooltip && (
        <div className="absolute bottom-full left-0 mb-2 w-64 p-3 bg-gray-900 text-white text-xs rounded shadow-lg z-10">
          <div className="space-y-1">
            <div>
              <span className="font-semibold">Document:</span> {documentName}
            </div>
            <div>
              <span className="font-semibold">Page:</span> {pageNumber}
            </div>
            <div>
              <span className="font-semibold">Section:</span> {section}
            </div>
            {confidence !== undefined && (
              <div>
                <span className="font-semibold">Confidence:</span> {Math.round(confidence * 100)}%
              </div>
            )}
          </div>
          <div className="absolute bottom-0 left-4 transform translate-y-1/2 rotate-45 w-2 h-2 bg-gray-900"></div>
        </div>
      )}
    </span>
  );
};
