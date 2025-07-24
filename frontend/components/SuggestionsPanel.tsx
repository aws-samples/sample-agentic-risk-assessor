import React from 'react';

interface Suggestion {
  field: string;
  suggestion: string;
  description?: string;
  source: string;
  auto_populate_content?: string;
}

interface SuggestionsPanelProps {
  suggestions: Suggestion[];
  onApply: (field: string, value: string) => void;
  onDismiss?: () => void;
}

export const SuggestionsPanel: React.FC<SuggestionsPanelProps> = ({
  suggestions,
  onApply,
  onDismiss
}) => {
  if (suggestions.length === 0) return null;

  return (
    <div className="suggestions-panel bg-purple-50 border border-purple-200 rounded-lg p-4 mb-4">
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2">
          <svg
            className="w-5 h-5 text-purple-600"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
            />
          </svg>
          <h3 className="text-lg font-semibold text-purple-900">
            Suggestions from Research
          </h3>
        </div>
        {onDismiss && (
          <button
            onClick={onDismiss}
            className="text-purple-400 hover:text-purple-600"
            aria-label="Dismiss suggestions"
          >
            ✕
          </button>
        )}
      </div>

      <p className="text-sm text-purple-700 mb-4">
        Based on your industry and region, here are some suggestions to help complete your profile:
      </p>

      <div className="space-y-3">
        {suggestions.map((suggestion, index) => (
          <div
            key={index}
            className="bg-white rounded-lg p-3 border border-purple-100 hover:border-purple-300 transition-colors"
          >
            {/* Field Name */}
            <div className="flex items-start justify-between mb-2">
              <div className="flex-1">
                <div className="font-medium text-gray-900 mb-1">
                  {suggestion.field.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                </div>
                <div className="text-sm text-gray-700 mb-1">
                  {suggestion.suggestion}
                </div>
                {suggestion.description && (
                  <div className="text-xs text-gray-500">
                    {suggestion.description}
                  </div>
                )}
              </div>
            </div>

            {/* Source Badge */}
            <div className="flex items-center justify-between">
              <span className="text-xs text-purple-600 bg-purple-100 px-2 py-1 rounded">
                From: {suggestion.source.replace(/_/g, ' ')}
              </span>

              {/* Apply Button */}
              <button
                onClick={() => onApply(
                  suggestion.field,
                  suggestion.auto_populate_content || suggestion.suggestion
                )}
                className="px-3 py-1 bg-purple-600 text-white text-sm rounded hover:bg-purple-700 transition-colors"
              >
                Apply
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
