'use client';

import { useState } from 'react';
import { AlertCircle, Copy, Check, RefreshCw } from 'lucide-react';

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  const [copied, setCopied] = useState(false);

  const errorDetails = `Error: ${error.message}${error.digest ? `\nDigest: ${error.digest}` : ''}`;

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
    <html>
      <body style={{
        background: '#030303',
        color: '#FFFFFF',
        fontFamily: 'Inter, -apple-system, sans-serif',
        margin: 0,
        padding: 0,
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center'
      }}>
        <div style={{
          background: '#0A0A0A',
          border: '1px solid rgba(239, 68, 68, 0.3)',
          borderRadius: '16px',
          padding: '32px',
          maxWidth: '480px',
          width: '90%',
          textAlign: 'center'
        }}>
          <div style={{
            width: '64px',
            height: '64px',
            borderRadius: '16px',
            background: 'rgba(239, 68, 68, 0.1)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            margin: '0 auto 20px'
          }}>
            <AlertCircle size={32} color="#ef4444" />
          </div>

          <h1 style={{
            fontSize: '20px',
            fontWeight: 700,
            marginBottom: '8px'
          }}>
            Application Error
          </h1>

          <p style={{
            color: '#A3A3A3',
            fontSize: '14px',
            marginBottom: '24px'
          }}>
            A critical error occurred. Please try refreshing the page.
          </p>

          <div style={{
            background: '#111111',
            border: '1px solid #1A1A1A',
            borderRadius: '8px',
            padding: '16px',
            marginBottom: '24px',
            textAlign: 'left'
          }}>
            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              marginBottom: '8px'
            }}>
              <span style={{
                fontSize: '10px',
                color: '#666666',
                textTransform: 'uppercase',
                letterSpacing: '0.05em'
              }}>
                Error Details
              </span>
              <button
                onClick={handleCopy}
                style={{
                  background: 'none',
                  border: 'none',
                  color: copied ? '#22c55e' : '#666666',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                  fontSize: '11px',
                  padding: '4px'
                }}
              >
                {copied ? <Check size={12} /> : <Copy size={12} />}
                {copied ? 'Copied!' : 'Copy'}
              </button>
            </div>
            <code style={{
              fontSize: '12px',
              color: '#ef4444',
              fontFamily: 'JetBrains Mono, monospace',
              wordBreak: 'break-all'
            }}>
              {error.message}
            </code>
          </div>

          <button
            onClick={reset}
            style={{
              background: '#38BDF8',
              color: '#030303',
              border: 'none',
              borderRadius: '8px',
              padding: '12px 24px',
              fontSize: '14px',
              fontWeight: 600,
              cursor: 'pointer',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '8px',
              width: '100%',
              justifyContent: 'center'
            }}
          >
            <RefreshCw size={16} />
            Refresh Page
          </button>
        </div>
      </body>
    </html>
  );
}
