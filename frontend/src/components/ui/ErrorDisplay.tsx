'use client';

import { useState } from 'react';
import { AlertCircle, Copy, Check, RefreshCw } from 'lucide-react';

interface ErrorDisplayProps {
  title?: string;
  message: string;
  details?: string;
  onRetry?: () => void;
}

export function ErrorDisplay({
  title = 'Something went wrong',
  message,
  details,
  onRetry,
}: ErrorDisplayProps) {
  const [copied, setCopied] = useState(false);

  const fullError = details ? `${message}\n\n${details}` : message;

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(fullError);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  return (
    <div className="card border-red-500/30">
      <div className="flex items-start gap-4">
        <div className="w-10 h-10 rounded-lg bg-red-500/10 flex items-center justify-center flex-shrink-0">
          <AlertCircle className="w-5 h-5 text-red-500" />
        </div>
        <div className="flex-1 min-w-0">
          <h3 className="text-base font-semibold text-text mb-1">{title}</h3>
          <p className="text-sm text-text-sec mb-3">{message}</p>

          {details && (
            <div className="relative">
              <pre className="text-xs bg-surface border border-border-dim rounded-lg p-3 overflow-x-auto text-text-muted font-mono">
                {details}
              </pre>
            </div>
          )}

          <div className="flex items-center gap-2 mt-4">
            <button
              onClick={handleCopy}
              className="btn btn-secondary btn-sm"
            >
              {copied ? (
                <>
                  <Check className="w-3.5 h-3.5" />
                  Copied!
                </>
              ) : (
                <>
                  <Copy className="w-3.5 h-3.5" />
                  Copy Error
                </>
              )}
            </button>

            {onRetry && (
              <button
                onClick={onRetry}
                className="btn btn-primary btn-sm"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                Retry
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// Inline error for smaller displays
export function InlineError({ message, onCopy }: { message: string; onCopy?: () => void }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(message);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  return (
    <div className="flex items-center gap-2 p-3 rounded-lg bg-red-500/10 border border-red-500/20">
      <AlertCircle className="w-4 h-4 text-red-500 flex-shrink-0" />
      <span className="text-sm text-red-400 flex-1">{message}</span>
      <button
        onClick={onCopy || handleCopy}
        className="p-1.5 rounded hover:bg-red-500/20 transition-colors"
        title="Copy error"
      >
        {copied ? (
          <Check className="w-3.5 h-3.5 text-green-400" />
        ) : (
          <Copy className="w-3.5 h-3.5 text-red-400" />
        )}
      </button>
    </div>
  );
}
