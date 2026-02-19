'use client';

import { useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { aiApi } from '@/lib/api';
import { Card, CardHeader, CardBody, CardTitle } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { cn } from '@/lib/utils';
import {
  Sparkles,
  ChevronDown,
  ChevronUp,
  AlertTriangle,
  CheckCircle,
  Brain,
  RefreshCw,
} from 'lucide-react';

interface AIRecommendationProps {
  predictionId: number;
  matchInfo?: {
    homeTeam: string;
    awayTeam: string;
  };
}

export function AIRecommendation({ predictionId, matchInfo }: AIRecommendationProps) {
  const [expanded, setExpanded] = useState(false);
  const [selectedProvider, setSelectedProvider] = useState<string>('openai');

  // Get available providers
  const { data: providers } = useQuery({
    queryKey: ['ai-providers'],
    queryFn: aiApi.getProviders,
  });

  // Get existing recommendation
  const {
    data: existingRec,
    isLoading: loadingExisting,
    refetch,
  } = useQuery({
    queryKey: ['ai-recommendation', predictionId],
    queryFn: () => aiApi.getForPrediction(predictionId),
    retry: false,
  });

  // Generate new recommendation
  const generateMutation = useMutation({
    mutationFn: () =>
      aiApi.generate({
        prediction_id: predictionId,
        provider: selectedProvider as 'openai' | 'anthropic' | 'google',
        include_rag: true,
      }),
    onSuccess: () => {
      refetch();
    },
  });

  const recommendation = existingRec || generateMutation.data;
  const isLoading = loadingExisting || generateMutation.isPending;

  return (
    <Card className="border-purple-500/30">
      <div
        className="cursor-pointer"
        onClick={() => setExpanded(!expanded)}
      >
      <CardHeader className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-purple-500/20">
            <Brain className="w-5 h-5 text-purple-400" />
          </div>
          <div>
            <CardTitle className="flex items-center gap-2">
              AI Analysis
              <Sparkles className="w-4 h-4 text-purple-400" />
            </CardTitle>
            <p className="text-sm text-slate-400">
              Get AI-powered insights and recommendations
            </p>
          </div>
        </div>
        <button className="p-2 hover:bg-slate-700/50 rounded-lg transition-colors">
          {expanded ? (
            <ChevronUp className="w-5 h-5 text-slate-400" />
          ) : (
            <ChevronDown className="w-5 h-5 text-slate-400" />
          )}
        </button>
      </CardHeader>
      </div>

      {expanded && (
        <CardBody className="space-y-4">
          {/* Provider selection and generate button */}
          {!recommendation && (
            <div className="flex items-center gap-4">
              <select
                value={selectedProvider}
                onChange={(e) => setSelectedProvider(e.target.value)}
                className="select flex-1"
                disabled={isLoading}
              >
                {providers?.providers?.map((p: string) => (
                  <option key={p} value={p}>
                    {p === 'openai'
                      ? 'OpenAI (GPT-4)'
                      : p === 'anthropic'
                      ? 'Claude'
                      : 'Google Gemini'}
                  </option>
                )) || <option value="openai">OpenAI (GPT-4)</option>}
              </select>

              <button
                onClick={() => generateMutation.mutate()}
                disabled={isLoading}
                className="btn-primary flex items-center gap-2"
              >
                {isLoading ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    Analyzing...
                  </>
                ) : (
                  <>
                    <Sparkles className="w-4 h-4" />
                    Get AI Recommendation
                  </>
                )}
              </button>
            </div>
          )}

          {/* Loading state */}
          {isLoading && (
            <div className="py-8 text-center">
              <LoadingSpinner size="lg" />
              <p className="text-slate-400 mt-4">
                Analyzing match data and generating recommendations...
              </p>
            </div>
          )}

          {/* Error state */}
          {generateMutation.isError && (
            <div className="p-4 rounded-lg bg-red-500/10 border border-red-500/30">
              <div className="flex items-center gap-2 text-red-400">
                <AlertTriangle className="w-5 h-5" />
                <span>Failed to generate recommendation. Please try again.</span>
              </div>
            </div>
          )}

          {/* Recommendation display */}
          {recommendation && !isLoading && (
            <div className="space-y-4">
              {/* Provider badge */}
              <div className="flex items-center justify-between">
                <Badge variant="outline">
                  Powered by{' '}
                  {recommendation.provider === 'openai'
                    ? 'GPT-4'
                    : recommendation.provider === 'anthropic'
                    ? 'Claude'
                    : 'Gemini'}
                </Badge>
                <button
                  onClick={() => generateMutation.mutate()}
                  className="text-sm text-purple-400 hover:text-purple-300 flex items-center gap-1"
                >
                  <RefreshCw className="w-3 h-3" />
                  Regenerate
                </button>
              </div>

              {/* Main recommendation */}
              <div className="p-4 rounded-lg bg-purple-500/10 border border-purple-500/30">
                <h4 className="font-semibold text-white mb-2 flex items-center gap-2">
                  <CheckCircle className="w-4 h-4 text-purple-400" />
                  Recommendation
                </h4>
                <p className="text-slate-300 whitespace-pre-wrap">
                  {recommendation.recommendation}
                </p>
              </div>

              {/* Confidence assessment */}
              {recommendation.confidence_assessment && (
                <div className="p-4 rounded-lg bg-slate-800/50">
                  <h4 className="font-semibold text-white mb-2">
                    Confidence Assessment
                  </h4>
                  <p className="text-slate-400 text-sm whitespace-pre-wrap">
                    {recommendation.confidence_assessment}
                  </p>
                </div>
              )}

              {/* Risk analysis */}
              {recommendation.risk_analysis && (
                <div className="p-4 rounded-lg bg-orange-500/10 border border-orange-500/20">
                  <h4 className="font-semibold text-white mb-2 flex items-center gap-2">
                    <AlertTriangle className="w-4 h-4 text-orange-400" />
                    Risk Analysis
                  </h4>
                  <p className="text-slate-400 text-sm whitespace-pre-wrap">
                    {recommendation.risk_analysis}
                  </p>
                </div>
              )}

              {/* Key factors */}
              {recommendation.key_factors && recommendation.key_factors.length > 0 && (
                <div className="p-4 rounded-lg bg-slate-800/50">
                  <h4 className="font-semibold text-white mb-3">Key Factors</h4>
                  <ul className="space-y-2">
                    {recommendation.key_factors.map((factor: string, i: number) => (
                      <li
                        key={i}
                        className="flex items-start gap-2 text-sm text-slate-400"
                      >
                        <span className="text-purple-400 mt-1">•</span>
                        {factor}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Meta info */}
              <div className="flex items-center justify-between text-xs text-slate-500 pt-2 border-t border-slate-700/50">
                <span>
                  Tokens used: {recommendation.tokens_used || 'N/A'}
                </span>
                <span>
                  Processing time: {recommendation.processing_time_ms || 'N/A'}ms
                </span>
              </div>
            </div>
          )}
        </CardBody>
      )}
    </Card>
  );
}
