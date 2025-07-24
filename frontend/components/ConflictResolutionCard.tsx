import React, { useState } from 'react';
import { DocumentReference } from './DocumentReference';

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

interface ConflictResolutionCardProps {
  conflicts: Conflict[];
  onResolve: (field: string, selectedValue: string, sourceDocId: string) => void;
  onDocumentClick: (documentId: string) => void;
}

export const ConflictResolutionCard: React.FC<ConflictResolutionCardProps> = ({
  conflicts,
  onResolve,
  onDocumentClick
}) => {
  const [selectedValues, setSelectedValues] = useState<Record<string, number>>({});

  const handleSelect = (field: string, index: number) => {
    setSelectedValues({ ...selectedValues, [field]: index });
  };

  const handleResolve = (field: string) => {
    const selectedIndex = selectedValues[field];
    if (selectedIndex !== undefined) {
      const conflict = conflicts.find(c => c.field === field);
      if (conflict) {
        const selectedValue = conflict.values[selectedIndex];
        onResolve(field, selectedValue.value, selectedValue.source.document_id);
      }
    }
  };

  return (
    <div className="conflict-resolution-card bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-4">
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2">
          <svg
            className="w-5 h-5 text-yellow-600"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
            />
          </svg>
          <h3 className="text-lg font-semibold text-yellow-900">
            Conflicting Information Found
          </h3>
        </div>
      </div>

      <p className="text-sm text-yellow-700 mb-4">
        Different documents contain conflicting information for the following fields. Please select the correct value.
      </p>

      <div className="space-y-4">
        {conflicts.map((conflict) => (
          <div
            key={conflict.field}
            className="bg-white rounded-lg p-4 border border-yellow-100"
          >
            {/* Field Name */}
            <div className="font-medium text-gray-900 mb-3">
              {conflict.field.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
            </div>

            {/* Conflicting Values */}
            <div className="space-y-3 mb-4">
              {conflict.values.map((valueData, index) => (
                <div
                  key={index}
                  className={`p-3 rounded-lg border-2 cursor-pointer transition-all ${
                    selectedValues[conflict.field] === index
                      ? 'border-blue-500 bg-blue-50'
                      : 'border-gray-200 hover:border-gray-300'
                  }`}
                  onClick={() => handleSelect(conflict.field, index)}
                >
                  {/* Radio Button */}
                  <div className="flex items-start gap-3">
                    <div className="mt-1">
                      <div
                        className={`w-5 h-5 rounded-full border-2 flex items-center justify-center ${
                          selectedValues[conflict.field] === index
                            ? 'border-blue-500 bg-blue-500'
                            : 'border-gray-300'
                        }`}
                      >
                        {selectedValues[conflict.field] === index && (
                          <div className="w-2 h-2 bg-white rounded-full"></div>
                        )}
                      </div>
                    </div>

                    <div className="flex-1">
                      {/* Value */}
                      <div className="text-gray-700 mb-2">
                        {valueData.value}
                      </div>

                      {/* Source */}
                      <div className="flex items-center gap-2">
                        <span className="text-xs text-gray-500">From:</span>
                        <DocumentReference
                          documentName={valueData.source.document_name}
                          pageNumber={valueData.source.page_number}
                          section={valueData.source.section}
                          confidence={valueData.source.confidence}
                          onClick={() => onDocumentClick(valueData.source.document_id)}
                        />
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {/* Resolve Button */}
            <button
              onClick={() => handleResolve(conflict.field)}
              disabled={selectedValues[conflict.field] === undefined}
              className={`w-full px-4 py-2 rounded font-medium transition-colors ${
                selectedValues[conflict.field] !== undefined
                  ? 'bg-blue-600 text-white hover:bg-blue-700'
                  : 'bg-gray-200 text-gray-400 cursor-not-allowed'
              }`}
            >
              Resolve Conflict
            </button>
          </div>
        ))}
      </div>
    </div>
  );
};
