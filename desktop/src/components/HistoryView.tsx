import React from 'react';
import { RotateCcw, Clock, CheckCircle, AlertTriangle, History } from 'lucide-react';
import { BatchItem } from '../types';

interface HistoryViewProps {
  batches: BatchItem[];
  isLoading: boolean;
  onUndoBatch: (batchId: string) => void;
}

export const HistoryView: React.FC<HistoryViewProps> = ({
  batches,
  isLoading,
  onUndoBatch,
}) => {
  return (
    <div style={{ padding: '32px 40px', overflowY: 'auto', height: '100vh' }} className="animate-fade-in">
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, letterSpacing: '-0.02em', marginBottom: 4 }}>
          Organization History & Undo
        </h1>
        <p style={{ color: 'var(--text-muted)', fontSize: 13 }}>
          Every operation is logged in local SQLite. You can safely reverse any batch anytime without data loss.
        </p>
      </div>

      {batches.length === 0 ? (
        <div className="glass-surface" style={{ textAlign: 'center', padding: '60px 20px', borderRadius: 10 }}>
          <History size={36} color="var(--text-muted)" style={{ marginBottom: 12 }} />
          <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 4 }}>No History Yet</h3>
          <p style={{ color: 'var(--text-muted)', fontSize: 13 }}>
            Run your first organization to generate an audit trail.
          </p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {batches.map((b) => {
            const isUndone = b.status === 'UNDONE';
            const isCompleted = b.status === 'COMPLETED';

            return (
              <div
                key={b.id}
                className="glass-surface"
                style={{
                  padding: '16px 20px',
                  borderRadius: 10,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                  <div
                    style={{
                      width: 36,
                      height: 36,
                      borderRadius: 8,
                      background: isUndone
                        ? 'rgba(245, 158, 11, 0.15)'
                        : isCompleted
                        ? 'rgba(16, 185, 129, 0.15)'
                        : 'rgba(244, 63, 94, 0.15)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                    }}
                  >
                    {isUndone ? (
                      <RotateCcw size={18} color="var(--accent-amber)" />
                    ) : isCompleted ? (
                      <CheckCircle size={18} color="var(--accent-emerald)" />
                    ) : (
                      <AlertTriangle size={18} color="var(--accent-rose)" />
                    )}
                  </div>

                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                      <span style={{ fontWeight: 600, fontSize: 14 }}>
                        {b.successful_moves} files moved
                      </span>
                      <span
                        style={{
                          fontSize: 10,
                          fontWeight: 700,
                          padding: '2px 7px',
                          borderRadius: 9999,
                          background: isUndone
                            ? 'rgba(245, 158, 11, 0.2)'
                            : isCompleted
                            ? 'rgba(16, 185, 129, 0.2)'
                            : 'rgba(244, 63, 94, 0.2)',
                          color: isUndone
                            ? 'var(--accent-amber)'
                            : isCompleted
                            ? 'var(--accent-emerald)'
                            : 'var(--accent-rose)',
                        }}
                      >
                        {b.status}
                      </span>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: 14, fontSize: 11, color: 'var(--text-muted)' }}>
                      <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                        <Clock size={12} />
                        {new Date(b.timestamp).toLocaleString()}
                      </span>
                      <span className="font-mono-code">ID: {b.id.slice(0, 8)}...</span>
                      {b.notes && <span>{b.notes}</span>}
                    </div>
                  </div>
                </div>

                {!isUndone && b.successful_moves > 0 && (
                  <button
                    onClick={() => onUndoBatch(b.id)}
                    disabled={isLoading}
                    className="btn-secondary"
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 6,
                      padding: '8px 14px',
                      borderRadius: 7,
                      fontSize: 12.5,
                      fontWeight: 600,
                      cursor: 'pointer',
                    }}
                  >
                    <RotateCcw size={13} />
                    <span>Undo Batch</span>
                  </button>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
