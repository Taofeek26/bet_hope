'use client';

import { useState } from 'react';
import { useAIRecommendation, useGenerateAIRecommendation } from '@/hooks/useApi';
import type { AIRecommendationResponse } from '@/types';

interface AIEnhancementProps {
  predictionId: number;
  matchInfo?: {
    homeTeam: string;
    awayTeam: string;
  };
}

export function AIEnhancement({ predictionId, matchInfo }: AIEnhancementProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [hasGenerated, setHasGenerated] = useState(false);

  // Check for existing recommendation
  const {
    data: existingRecommendation,
    isLoading: isLoadingExisting,
    error: existingError,
  } = useAIRecommendation(predictionId);

  // Generate new recommendation
  const generateMutation = useGenerateAIRecommendation();

  const recommendation = existingRecommendation as AIRecommendationResponse | undefined;
  const hasExisting = !!recommendation && !existingError;

  const handleGenerate = async () => {
    setHasGenerated(true);
    setIsExpanded(true);
    try {
      await generateMutation.mutateAsync({
        prediction_id: predictionId,
        provider: 'openai',
        include_rag: true,
      });
    } catch (error) {
      console.error('Failed to generate AI recommendation:', error);
    }
  };

  const isLoading = generateMutation.isPending || isLoadingExisting;

  // If we have data from mutation, use that instead
  const displayData = generateMutation.data as AIRecommendationResponse | undefined || recommendation;

  return (
    <div className="mt-4 border-t border-border/50 pt-4">
      {/* Button to generate/show AI suggestions */}
      {!isExpanded && !hasExisting && (
        <button
          onClick={handleGenerate}
          disabled={isLoading}
          className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-gradient-to-r from-brand/10 to-brand/5 border border-brand/20 hover:border-brand/40 hover:bg-brand/15 transition-all duration-200 group disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isLoading ? (
            <>
              <LoadingSpinner />
              <span className="text-sm font-medium text-text-secondary">
                Generating AI Analysis...
              </span>
            </>
          ) : (
            <>
              <SparklesIcon className="w-4 h-4 text-brand group-hover:scale-110 transition-transform" />
              <span className="text-sm font-medium text-text-primary group-hover:text-brand transition-colors">
                Get AI Enhancement Suggestions
              </span>
            </>
          )}
        </button>
      )}

      {/* Show existing recommendation button */}
      {!isExpanded && hasExisting && (
        <button
          onClick={() => setIsExpanded(true)}
          className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-brand/10 border border-brand/30 hover:bg-brand/15 transition-all duration-200"
        >
          <SparklesIcon className="w-4 h-4 text-brand" />
          <span className="text-sm font-medium text-brand">
            View AI Analysis
          </span>
          <ChevronDownIcon className="w-4 h-4 text-brand" />
        </button>
      )}

      {/* Expanded recommendation view */}
      {isExpanded && (
        <div className="space-y-4 animate-in fade-in slide-in-from-top-2 duration-300">
          {/* Header */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <SparklesIcon className="w-5 h-5 text-brand" />
              <h3 className="font-semibold text-text-primary">AI Analysis</h3>
              {displayData?.provider && (
                <span className="text-xs px-2 py-0.5 rounded bg-brand/10 text-brand">
                  {displayData.provider.toUpperCase()}
                </span>
              )}
            </div>
            <button
              onClick={() => setIsExpanded(false)}
              className="p-1 hover:bg-card-hover rounded transition-colors"
            >
              <ChevronUpIcon className="w-4 h-4 text-text-secondary" />
            </button>
          </div>

          {/* Loading state */}
          {isLoading && (
            <div className="flex items-center justify-center py-8">
              <div className="flex flex-col items-center gap-3">
                <LoadingSpinner size="lg" />
                <p className="text-sm text-text-secondary">
                  Analyzing match data with AI...
                </p>
              </div>
            </div>
          )}

          {/* Error state */}
          {generateMutation.isError && (
            <div className="p-4 rounded-lg bg-red-500/10 border border-red-500/20">
              <p className="text-sm text-red-400">
                Failed to generate AI analysis. Please try again.
              </p>
              <button
                onClick={handleGenerate}
                className="mt-2 text-sm text-brand hover:underline"
              >
                Retry
              </button>
            </div>
          )}

          {/* Recommendation content */}
          {displayData && !isLoading && (
            <div className="space-y-4">
              {/* Recommendation */}
              {displayData.recommendation && (
                <div className="p-4 rounded-lg bg-card-hover/50 border border-border/50">
                  <h4 className="text-sm font-medium text-text-secondary mb-2 flex items-center gap-2">
                    <LightbulbIcon className="w-4 h-4" />
                    Recommendation
                  </h4>
                  <p className="text-sm text-text-primary leading-relaxed">
                    {displayData.recommendation}
                  </p>
                </div>
              )}

              {/* Confidence Assessment */}
              {displayData.confidence_assessment && (
                <div className="p-4 rounded-lg bg-card-hover/50 border border-border/50">
                  <h4 className="text-sm font-medium text-text-secondary mb-2 flex items-center gap-2">
                    <ShieldIcon className="w-4 h-4" />
                    Confidence Assessment
                  </h4>
                  <p className="text-sm text-text-primary leading-relaxed">
                    {displayData.confidence_assessment}
                  </p>
                </div>
              )}

              {/* Risk Analysis */}
              {displayData.risk_analysis && (
                <div className="p-4 rounded-lg bg-amber-500/5 border border-amber-500/20">
                  <h4 className="text-sm font-medium text-amber-400 mb-2 flex items-center gap-2">
                    <WarningIcon className="w-4 h-4" />
                    Risk Analysis
                  </h4>
                  <p className="text-sm text-text-primary leading-relaxed">
                    {displayData.risk_analysis}
                  </p>
                </div>
              )}

              {/* Key Factors */}
              {displayData.key_factors && displayData.key_factors.length > 0 && (
                <div className="p-4 rounded-lg bg-card-hover/50 border border-border/50">
                  <h4 className="text-sm font-medium text-text-secondary mb-3 flex items-center gap-2">
                    <ListIcon className="w-4 h-4" />
                    Key Factors
                  </h4>
                  <ul className="space-y-2">
                    {displayData.key_factors.map((factor, index) => (
                      <li
                        key={index}
                        className="flex items-start gap-2 text-sm text-text-primary"
                      >
                        <span className="w-5 h-5 flex-shrink-0 flex items-center justify-center rounded-full bg-brand/10 text-brand text-xs font-medium">
                          {index + 1}
                        </span>
                        <span>{factor}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Regenerate button */}
              <button
                onClick={handleGenerate}
                disabled={isLoading}
                className="w-full flex items-center justify-center gap-2 px-4 py-2 rounded-lg border border-border/50 hover:border-brand/40 hover:bg-brand/5 transition-all duration-200 disabled:opacity-50"
              >
                <RefreshIcon className="w-4 h-4 text-text-secondary" />
                <span className="text-sm text-text-secondary">
                  Regenerate Analysis
                </span>
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// Icon Components
function SparklesIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M12 3l1.912 5.813a2 2 0 001.275 1.275L21 12l-5.813 1.912a2 2 0 00-1.275 1.275L12 21l-1.912-5.813a2 2 0 00-1.275-1.275L3 12l5.813-1.912a2 2 0 001.275-1.275L12 3z" />
    </svg>
  );
}

function ChevronDownIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M6 9l6 6 6-6" />
    </svg>
  );
}

function ChevronUpIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M18 15l-6-6-6 6" />
    </svg>
  );
}

function LightbulbIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M9 18h6M10 22h4M12 2a7 7 0 017 7c0 2.38-1.19 4.47-3 5.74V17a1 1 0 01-1 1H9a1 1 0 01-1-1v-2.26C6.19 13.47 5 11.38 5 9a7 7 0 017-7z" />
    </svg>
  );
}

function ShieldIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
    </svg>
  );
}

function WarningIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M12 9v4M12 17h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
    </svg>
  );
}

function ListIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01" />
    </svg>
  );
}

function RefreshIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M23 4v6h-6M1 20v-6h6M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15" />
    </svg>
  );
}

function LoadingSpinner({ size = 'sm' }: { size?: 'sm' | 'lg' }) {
  const sizeClass = size === 'lg' ? 'w-8 h-8' : 'w-4 h-4';
  return (
    <svg
      className={`${sizeClass} animate-spin text-brand`}
      viewBox="0 0 24 24"
      fill="none"
    >
      <circle
        className="opacity-25"
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="4"
      />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
      />
    </svg>
  );
}

export default AIEnhancement;
