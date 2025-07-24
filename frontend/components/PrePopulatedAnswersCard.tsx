import React from 'react';
import { DocumentReference } from './DocumentReference';

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

interface PrePopulatedAnswersCardProps {
  answers: PrePopulatedAnswer[];
  onConfirm: (field: string, confirmed: boolean, editedValue?: string) => void;
  onDocumentClick: (documentId: string) => void;
}

export const PrePopulatedAnswersCard: React.FC<PrePopulatedAnswersCardProps> = ({
  answers,
  onConfirm,
  onDocumentClick
}) => {
  const [editingField, setEditingField] = React.useState<string | null>(null);
  const [editedValues, setEditedValues] = React.useState<Record<string, string>>({});

  const handleEdit = (field: string, value: string) => {
    setEditingField(field);
    setEditedValues({ ...editedValues, [field]: value });
  };

  const handleSaveEdit = (field: string) => {
    onConfirm(field, true, editedValues[field]);
    setEditingField(null);
  };

  const handleCancelEdit = () => {
    setEditingField(null);
  };

  return (
    <div className="pre-populated-answers-card bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4">
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2">
          <svg
            className="w-5 h-5 text-blue-600"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
          <h3 className="text-lg font-semibold text-blue-900">
            Information Extracted from Documents
          </h3>
        </div>
      </div>

      <p className="text-sm text-blue-700 mb-4">
        I've found the following information in your uploaded documents. Please review and confirm or edit as needed.
      </p>

      <div className="space-y-4">
        {answers.map((answer) => (
          <div
            key={answer.field}
            className="bg-white rounded-lg p-4 border border-blue-100"
          >
            {/* Field Name */}
            <div className="font-medium text-gray-900 mb-2">
              {answer.field.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
            </div>

            {/* Value */}
            {editingField === answer.field ? (
              <div className="mb-3">
                <textarea
                  className="w-full p-2 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  rows={3}
                  value={editedValues[answer.field] || answer.value}
                  onChange={(e) => setEditedValues({ ...editedValues, [answer.field]: e.target.value })}
                />
              </div>
            ) : (
              <div className="text-gray-700 mb-3 p-2 bg-gray-50 rounded">
                {answer.value}
              </div>
            )}

            {/* Source Reference */}
            <div className="flex items-center gap-2 mb-3">
              <span className="text-xs text-gray-500">Source:</span>
              <DocumentReference
                documentName={answer.source.document_name}
                pageNumber={answer.source.page_number}
                section={answer.source.section}
                confidence={answer.source.confidence}
                onClick={() => onDocumentClick(answer.source.document_id)}
              />
            </div>

            {/* Actions */}
            <div className="flex gap-2">
              {editingField === answer.field ? (
                <>
                  <button
                    onClick={() => handleSaveEdit(answer.field)}
                    className="px-3 py-1 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 transition-colors"
                  >
                    Save
                  </button>
                  <button
                    onClick={handleCancelEdit}
                    className="px-3 py-1 bg-gray-200 text-gray-700 text-sm rounded hover:bg-gray-300 transition-colors"
                  >
                    Cancel
                  </button>
                </>
              ) : (
                <>
                  <button
                    onClick={() => onConfirm(answer.field, true)}
                    className="px-3 py-1 bg-green-600 text-white text-sm rounded hover:bg-green-700 transition-colors"
                  >
                    ✓ Confirm
                  </button>
                  <button
                    onClick={() => handleEdit(answer.field, answer.value)}
                    className="px-3 py-1 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 transition-colors"
                  >
                    ✎ Edit
                  </button>
                  <button
                    onClick={() => onConfirm(answer.field, false)}
                    className="px-3 py-1 bg-gray-200 text-gray-700 text-sm rounded hover:bg-gray-300 transition-colors"
                  >
                    ✗ Reject
                  </button>
                </>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
