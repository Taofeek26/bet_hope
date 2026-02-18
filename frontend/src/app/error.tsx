'use client';

import { useEffect, useState } from 'react';
import { AlertCircle, Copy, Check, RefreshCw, Home } from 'lucide-react';

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    console.error('Application Error:', error);
  }, [error]);

  const errorDetails = `Error: ${error.message}${error.digest ? `\nDigest: ${error.digest}` : ''}${error.stack ? `\n\nStack Trace:\n${error.stack}` : ''}`;

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(errorDetails);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  return (
    <div className="min-h-[60vh] flex items-center justify-center p-6">
      <div className="card max-w-lg w-full border-red-500/30">
        <div className="text-center mb-6">
          <div className="w-16 h-16 rounded-2xl bg-red-500/10 flex items-center justify-center mx-auto mb-4">
            <AlertCircle className="w-8 h-8 text-red-500" />
          </div>
          <h1 className="text-xl font-bold text-text mb-2">Something went wrong</h1>
          <p className="text-text-sec text-sm">
            An unexpected error occurred. You can try again or go back to the dashboard.
          </p>
        </div>

        {/* Error Details */}
        <div className="mb-6">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-medium text-text-muted uppercase tracking-wide">
              Error Details
            </span>
            <button
              onClick={handleCopy}
              className="flex items-center gap-1.5 text-xs text-text-muted hover:text-brand transition-colors"
            >
              {copied ? (
                <>
                  <Check className="w-3 h-3 text-green-400" />
                  <span className="text-green-400">Copied!</span>
                </>
              ) : (
                <>
                  <Copy className="w-3 h-3" />
                  <span>Copy</span>
                </>
              )}
            </button>
          </div>
          <div className="bg-surface border border-border-dim rounded-lg p-4 max-h-40 overflow-auto">
            <code className="text-xs text-red-400 font-mono whitespace-pre-wrap break-all">
              {error.message}
            </code>
            {error.digest && (
              <p className="text-xs text-text-muted mt-2 font-mono">
                Digest: {error.digest}
              </p>
            )}
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-3">
          <button
            onClick={reset}
            className="btn btn-primary flex-1"
          >
            <RefreshCw className="w-4 h-4" />
            Try Again
          </button>
          <a
            href="/"
            className="btn btn-secondary flex-1"
          >
            <Home className="w-4 h-4" />
            Dashboard
          </a>
        </div>
      </div>
    </div>
  );
}
