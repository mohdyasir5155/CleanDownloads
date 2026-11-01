import React, { useState } from 'react';
import { ShieldCheck, HardDrive, RotateCcw, Clock, Save, Info } from 'lucide-react';
import { AppConfig, StatusResponse } from '../types';

interface SettingsViewProps {
  config: AppConfig | null;
  status: StatusResponse | null;
  onSaveConfig: (updated: Partial<AppConfig>) => void;
  onResetDefaults: () => void;
}

export const SettingsView: React.FC<SettingsViewProps> = ({
  config,
  status,
  onSaveConfig,
  onResetDefaults,
}) => {
  const [recursive, setRecursive] = useState(config?.recursive ?? false);
  const [schedulerFreq, setSchedulerFreq] = useState('hourly');
  const [isSaved, setIsSaved] = useState(false);

  const handleSave = () => {
    onSaveConfig({ recursive });
    setIsSaved(true);
    setTimeout(() => setIsSaved(false), 2000);
  };

  return (
    <div style={{ padding: '32px 40px', overflowY: 'auto', height: '100vh' }} className="animate-fade-in">
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, letterSpacing: '-0.02em', marginBottom: 4 }}>
          Application Settings
        </h1>
        <p style={{ color: 'var(--text-muted)', fontSize: 13 }}>
          Configure behavior, paths, automation, and safety parameters.
        </p>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 20, maxWidth: 680 }}>
        {/* Directories */}
        <div className="glass-surface" style={{ padding: 20, borderRadius: 10 }}>
          <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 12, display: 'flex', alignItems: 'center', gap: 8 }}>
            <HardDrive size={16} color="var(--accent-indigo)" />
            <span>Target Folders</span>
          </h3>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div>
              <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 4 }}>Downloads Folder Path</div>
              <div
                className="font-mono-code"
                style={{
                  padding: '9px 12px',
                  borderRadius: 6,
                  background: 'rgba(0, 0, 0, 0.2)',
                  border: '1px solid var(--border-subtle)',
                  fontSize: 12,
                }}
              >
                {status?.downloads_dir || 'Auto-detected: Downloads'}
              </div>
            </div>

            <div>
              <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 4 }}>Application Data & History SQLite</div>
              <div
                className="font-mono-code"
                style={{
                  padding: '9px 12px',
                  borderRadius: 6,
                  background: 'rgba(0, 0, 0, 0.2)',
                  border: '1px solid var(--border-subtle)',
                  fontSize: 12,
                }}
              >
                {status?.app_data_dir || '%LOCALAPPDATA%\\CleanDownloads'}
              </div>
            </div>
          </div>
        </div>

        {/* Scan Behavior */}
        <div className="glass-surface" style={{ padding: 20, borderRadius: 10 }}>
          <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 12, display: 'flex', alignItems: 'center', gap: 8 }}>
            <ShieldCheck size={16} color="var(--accent-emerald)" />
            <span>Scan Behavior & Safety</span>
          </h3>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            <label style={{ display: 'flex', alignItems: 'flex-start', gap: 12, cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={recursive}
                onChange={(e) => setRecursive(e.target.checked)}
                style={{ marginTop: 3 }}
              />
              <div>
                <div style={{ fontSize: 13, fontWeight: 600 }}>Enable Recursive Scanning</div>
                <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                  Default is disabled (organizes root files only). Enabling will organize subfolders while keeping excluded category folders protected.
                </div>
              </div>
            </label>

            <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10, padding: '10px 12px', background: 'rgba(99, 102, 241, 0.08)', borderRadius: 8 }}>
              <Info size={16} color="var(--accent-indigo)" style={{ flexShrink: 0, marginTop: 2 }} />
              <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                <strong>Zero Overwrite Policy:</strong> When a file with the same name already exists in the target destination, CleanDownloads generates collision-safe suffixes <code>(1), (2)</code> to protect your data.
              </div>
            </div>
          </div>
        </div>

        {/* Automated Background Scheduling */}
        <div className="glass-surface" style={{ padding: 20, borderRadius: 10 }}>
          <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 12, display: 'flex', alignItems: 'center', gap: 8 }}>
            <Clock size={16} color="var(--accent-amber)" />
            <span>Automated Organization</span>
          </h3>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
              Runs automatically in the background using Windows Task Scheduler. Disabled by default.
            </div>

            <div style={{ display: 'flex', gap: 10 }}>
              <select
                value={schedulerFreq}
                onChange={(e) => setSchedulerFreq(e.target.value)}
                style={{
                  flex: 1,
                  padding: '8px 12px',
                  borderRadius: 6,
                  border: '1px solid var(--border-subtle)',
                  background: 'var(--bg-surface)',
                  color: 'var(--text-primary)',
                  fontSize: 13,
                  outline: 'none',
                }}
              >
                <option value="disabled">Disabled (Manual trigger only)</option>
                <option value="30m">Every 30 minutes</option>
                <option value="hourly">Every 1 hour</option>
                <option value="daily">Daily at 09:00</option>
                <option value="logon">On user login</option>
              </select>
            </div>
          </div>
        </div>

        {/* Action Controls */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 10 }}>
          <button
            onClick={onResetDefaults}
            className="btn-secondary"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              padding: '9px 14px',
              borderRadius: 7,
              fontSize: 13,
              cursor: 'pointer',
            }}
          >
            <RotateCcw size={14} />
            <span>Reset Factory Defaults</span>
          </button>

          <button
            onClick={handleSave}
            className="btn-primary"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              padding: '9px 18px',
              borderRadius: 7,
              fontSize: 13,
              fontWeight: 600,
              border: 'none',
              cursor: 'pointer',
            }}
          >
            <Save size={14} />
            <span>{isSaved ? 'Settings Saved!' : 'Save Changes'}</span>
          </button>
        </div>
      </div>
    </div>
  );
};
