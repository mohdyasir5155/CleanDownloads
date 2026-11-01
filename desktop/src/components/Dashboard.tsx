import React from 'react';
import {
  FolderCheck,
  RefreshCw,
  Play,
  Eye,
  FileText,
  Image,
  Video,
  Archive,
  Terminal,
  Code2,
  HardDrive,
  CheckCircle2,
} from 'lucide-react';
import { ScanResponse, StatusResponse } from '../types';

interface DashboardProps {
  scanData: ScanResponse | null;
  statusData: StatusResponse | null;
  isLoading: boolean;
  onRefreshScan: () => void;
  onOrganize: () => void;
  onGoToPreview: () => void;
}

const categoryIcons: Record<string, React.ReactNode> = {
  Documents: <FileText size={16} color="#6366f1" />,
  Images: <Image size={16} color="#38bdf8" />,
  Videos: <Video size={16} color="#ec4899" />,
  Audio: <HardDrive size={16} color="#f59e0b" />,
  Archives: <Archive size={16} color="#10b981" />,
  Software: <Terminal size={16} color="#8b5cf6" />,
  Code: <Code2 size={16} color="#14b8a6" />,
};

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
}

export const Dashboard: React.FC<DashboardProps> = ({
  scanData,
  statusData,
  isLoading,
  onRefreshScan,
  onOrganize,
  onGoToPreview,
}) => {
  const readyCount = scanData?.total_ready ?? 0;
  const readyBytes = scanData?.total_ready_bytes ?? 0;
  const alreadyCount = scanData?.already_organized_count ?? 0;
  const breakdown = scanData?.category_breakdown ?? {};

  return (
    <div style={{ padding: '32px 40px', overflowY: 'auto', height: '100vh' }} className="animate-fade-in">
      {/* Top Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 28 }}>
        <div>
          <h1 style={{ fontSize: 24, fontWeight: 700, letterSpacing: '-0.02em', marginBottom: 4 }}>
            Downloads Overview
          </h1>
          <p style={{ color: 'var(--text-muted)', fontSize: 13, display: 'flex', alignItems: 'center', gap: 6 }}>
            <span>Target directory:</span>
            <span className="font-mono-code" style={{ color: 'var(--text-secondary)' }}>
              {scanData?.downloads_dir || 'Resolving Downloads...'}
            </span>
          </p>
        </div>

        <div style={{ display: 'flex', gap: 10 }}>
          <button
            onClick={onRefreshScan}
            disabled={isLoading}
            className="btn-secondary"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              padding: '9px 14px',
              borderRadius: 7,
              fontSize: 13,
              fontWeight: 500,
              cursor: 'pointer',
            }}
          >
            <RefreshCw size={14} className={isLoading ? 'animate-spin' : ''} />
            <span>Scan Now</span>
          </button>

          {readyCount > 0 && (
            <>
              <button
                onClick={onGoToPreview}
                className="btn-secondary"
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                  padding: '9px 14px',
                  borderRadius: 7,
                  fontSize: 13,
                  fontWeight: 500,
                  cursor: 'pointer',
                }}
              >
                <Eye size={14} />
                <span>Preview</span>
              </button>

              <button
                onClick={onOrganize}
                className="btn-primary"
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                  padding: '9px 16px',
                  borderRadius: 7,
                  fontSize: 13,
                  fontWeight: 600,
                  border: 'none',
                  cursor: 'pointer',
                }}
              >
                <Play size={14} fill="#fff" />
                <span>Organize {readyCount} Files</span>
              </button>
            </>
          )}
        </div>
      </div>

      {/* KPI Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 14, marginBottom: 28 }}>
        <div className="glass-surface" style={{ padding: 18, borderRadius: 10 }}>
          <div style={{ fontSize: 12, color: 'var(--text-muted)', fontWeight: 500, marginBottom: 6 }}>
            Files Ready to Organize
          </div>
          <div style={{ fontSize: 26, fontWeight: 700, color: readyCount > 0 ? 'var(--accent-indigo)' : 'var(--text-primary)' }}>
            {readyCount}
          </div>
          <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>
            In root Downloads
          </div>
        </div>

        <div className="glass-surface" style={{ padding: 18, borderRadius: 10 }}>
          <div style={{ fontSize: 12, color: 'var(--text-muted)', fontWeight: 500, marginBottom: 6 }}>
            Total Clutter Size
          </div>
          <div style={{ fontSize: 26, fontWeight: 700 }}>
            {formatBytes(readyBytes)}
          </div>
          <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>
            Eligible unorganized data
          </div>
        </div>

        <div className="glass-surface" style={{ padding: 18, borderRadius: 10 }}>
          <div style={{ fontSize: 12, color: 'var(--text-muted)', fontWeight: 500, marginBottom: 6 }}>
            Already Organized
          </div>
          <div style={{ fontSize: 26, fontWeight: 700, color: 'var(--accent-emerald)' }}>
            {alreadyCount}
          </div>
          <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>
            In category subfolders
          </div>
        </div>

        <div className="glass-surface" style={{ padding: 18, borderRadius: 10 }}>
          <div style={{ fontSize: 12, color: 'var(--text-muted)', fontWeight: 500, marginBottom: 6 }}>
            Automated Scheduler
          </div>
          <div style={{ fontSize: 16, fontWeight: 600, marginTop: 4, display: 'flex', alignItems: 'center', gap: 6 }}>
            {statusData?.scheduler?.is_enabled ? (
              <>
                <span style={{ color: 'var(--accent-emerald)' }}>Active</span>
                <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                  ({statusData.scheduler.next_run_time ? 'Next: ' + statusData.scheduler.next_run_time.slice(0, 16) : 'Scheduled'})
                </span>
              </>
            ) : (
              <span style={{ color: 'var(--text-muted)', fontSize: 14 }}>Disabled</span>
            )}
          </div>
          <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 6 }}>
            Task Scheduler integration
          </div>
        </div>
      </div>

      {/* Main Content: Breakdown & Status */}
      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 20 }}>
        {/* Category Breakdown */}
        <div className="glass-surface" style={{ padding: 22, borderRadius: 10 }}>
          <h2 style={{ fontSize: 15, fontWeight: 600, marginBottom: 16 }}>
            Unorganized File Breakdown
          </h2>

          {Object.keys(breakdown).length === 0 ? (
            <div style={{ textAlign: 'center', padding: '40px 20px', color: 'var(--text-muted)' }}>
              <CheckCircle2 size={32} color="var(--accent-emerald)" style={{ marginBottom: 12 }} />
              <div style={{ fontWeight: 600, fontSize: 15, color: 'var(--text-primary)', marginBottom: 4 }}>
                Downloads folder is clean!
              </div>
              <div style={{ fontSize: 13 }}>No unorganized files found. Zero clutter.</div>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {Object.entries(breakdown)
                .sort((a, b) => b[1] - a[1])
                .map(([cat, count]) => {
                  const percentage = readyCount > 0 ? Math.round((count / readyCount) * 100) : 0;
                  return (
                    <div
                      key={cat}
                      style={{
                        padding: '10px 14px',
                        background: 'rgba(255, 255, 255, 0.02)',
                        borderRadius: 8,
                        border: '1px solid var(--border-subtle)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                        {categoryIcons[cat] || <FolderCheck size={16} color="#94a3b8" />}
                        <span style={{ fontSize: 13, fontWeight: 500 }}>{cat}</span>
                      </div>

                      <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                        <div
                          style={{
                            width: 100,
                            height: 6,
                            background: 'var(--border-subtle)',
                            borderRadius: 9999,
                            overflow: 'hidden',
                          }}
                        >
                          <div
                            style={{
                              width: `${percentage}%`,
                              height: '100%',
                              background: 'var(--accent-indigo)',
                              borderRadius: 9999,
                            }}
                          />
                        </div>
                        <span style={{ fontSize: 13, fontWeight: 600, minWidth: 40, textAlign: 'right' }}>
                          {count} {count === 1 ? 'file' : 'files'}
                        </span>
                      </div>
                    </div>
                  );
                })}
            </div>
          )}
        </div>

        {/* Safety & Integrity Guarantee Panel */}
        <div className="glass-surface" style={{ padding: 22, borderRadius: 10 }}>
          <h2 style={{ fontSize: 15, fontWeight: 600, marginBottom: 14 }}>
            Safety Guarantees
          </h2>
          <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: 12, fontSize: 12.5, color: 'var(--text-secondary)' }}>
            <li style={{ display: 'flex', alignItems: 'flex-start', gap: 8 }}>
              <span style={{ color: 'var(--accent-emerald)', fontWeight: 'bold' }}>✓</span>
              <span><strong>Zero Deletions:</strong> Files are never deleted or truncated under any circumstance.</span>
            </li>
            <li style={{ display: 'flex', alignItems: 'flex-start', gap: 8 }}>
              <span style={{ color: 'var(--accent-emerald)', fontWeight: 'bold' }}>✓</span>
              <span><strong>Zero Overwrites:</strong> Conflicts automatically append (1), (2) suffixes.</span>
            </li>
            <li style={{ display: 'flex', alignItems: 'flex-start', gap: 8 }}>
              <span style={{ color: 'var(--accent-emerald)', fontWeight: 'bold' }}>✓</span>
              <span><strong>Download Guard:</strong> Incomplete (.crdownload, .part) and locked files are protected.</span>
            </li>
            <li style={{ display: 'flex', alignItems: 'flex-start', gap: 8 }}>
              <span style={{ color: 'var(--accent-emerald)', fontWeight: 'bold' }}>✓</span>
              <span><strong>100% Reversible:</strong> Every move is audited locally in SQLite for instant undo.</span>
            </li>
          </ul>
        </div>
      </div>
    </div>
  );
};
