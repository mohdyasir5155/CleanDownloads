import React, { useState } from 'react';
import { ArrowRight, Search, Play, FileCheck } from 'lucide-react';
import { ScanResponse } from '../types';

interface PreviewViewProps {
  scanData: ScanResponse | null;
  onOrganize: () => void;
  isOrganizing: boolean;
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export const PreviewView: React.FC<PreviewViewProps> = ({
  scanData,
  onOrganize,
  isOrganizing,
}) => {
  const [search, setSearch] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('all');

  const files = scanData?.ready_files ?? [];
  const categories = Array.from(new Set(files.map((f) => f.category)));

  const filtered = files.filter((f) => {
    const matchesSearch = f.filename.toLowerCase().includes(search.toLowerCase());
    const matchesCat = selectedCategory === 'all' || f.category === selectedCategory;
    return matchesSearch && matchesCat;
  });

  return (
    <div style={{ padding: '32px 40px', overflowY: 'auto', height: '100vh' }} className="animate-fade-in">
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 700, letterSpacing: '-0.02em', marginBottom: 4 }}>
            Preview Changes — {files.length} Files Ready
          </h1>
          <p style={{ color: 'var(--text-muted)', fontSize: 13 }}>
            Review destination paths before moving files. No files have been touched yet.
          </p>
        </div>

        {files.length > 0 && (
          <button
            onClick={onOrganize}
            disabled={isOrganizing}
            className="btn-primary"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              padding: '10px 18px',
              borderRadius: 8,
              fontSize: 13,
              fontWeight: 600,
              border: 'none',
              cursor: 'pointer',
            }}
          >
            <Play size={14} fill="#fff" />
            <span>{isOrganizing ? 'Moving Files...' : `Confirm & Organize (${files.length})`}</span>
          </button>
        )}
      </div>

      {/* Filter and Search Bar */}
      <div style={{ display: 'flex', gap: 12, marginBottom: 20 }}>
        <div
          style={{
            flex: 1,
            position: 'relative',
            display: 'flex',
            alignItems: 'center',
          }}
        >
          <Search size={15} color="var(--text-muted)" style={{ position: 'absolute', left: 12 }} />
          <input
            type="text"
            placeholder="Search ready files..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={{
              width: '100%',
              padding: '9px 12px 9px 34px',
              borderRadius: 8,
              border: '1px solid var(--border-subtle)',
              background: 'var(--bg-surface)',
              color: 'var(--text-primary)',
              fontSize: 13,
              outline: 'none',
            }}
          />
        </div>

        <select
          value={selectedCategory}
          onChange={(e) => setSelectedCategory(e.target.value)}
          style={{
            padding: '9px 14px',
            borderRadius: 8,
            border: '1px solid var(--border-subtle)',
            background: 'var(--bg-surface)',
            color: 'var(--text-primary)',
            fontSize: 13,
            outline: 'none',
            cursor: 'pointer',
          }}
        >
          <option value="all">All Categories</option>
          {categories.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
      </div>

      {/* Files List */}
      {files.length === 0 ? (
        <div className="glass-surface" style={{ textAlign: 'center', padding: '60px 20px', borderRadius: 10 }}>
          <FileCheck size={36} color="var(--accent-emerald)" style={{ marginBottom: 12 }} />
          <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 4 }}>Everything is already organized</h3>
          <p style={{ color: 'var(--text-muted)', fontSize: 13 }}>No files waiting to be moved.</p>
        </div>
      ) : filtered.length === 0 ? (
        <div className="glass-surface" style={{ textAlign: 'center', padding: '40px 20px', borderRadius: 10, color: 'var(--text-muted)' }}>
          No files match your search filter.
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {filtered.map((f, i) => (
            <div
              key={i}
              className="glass-surface"
              style={{
                padding: '12px 16px',
                borderRadius: 8,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
              }}
            >
              <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <span style={{ fontWeight: 600, fontSize: 13 }}>{f.filename}</span>
                  <span
                    style={{
                      fontSize: 10,
                      fontWeight: 600,
                      textTransform: 'uppercase',
                      padding: '2px 6px',
                      borderRadius: 4,
                      background: 'rgba(99, 102, 241, 0.15)',
                      color: 'var(--accent-indigo)',
                    }}
                  >
                    {f.category}
                  </span>
                  <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>{formatBytes(f.size_bytes)}</span>
                </div>

                <div
                  className="font-mono-code"
                  style={{ fontSize: 11.5, color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: 8 }}
                >
                  <span>Downloads/{f.filename}</span>
                  <ArrowRight size={12} color="var(--accent-indigo)" />
                  <span style={{ color: 'var(--accent-emerald)', fontWeight: 500 }}>
                    Downloads/{f.target_relative_path}
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
