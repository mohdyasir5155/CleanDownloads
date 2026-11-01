import React, { useEffect, useState, useCallback } from 'react';
import { Sidebar, TabKey } from './components/Sidebar';
import { Dashboard } from './components/Dashboard';
import { PreviewView } from './components/PreviewView';
import { HistoryView } from './components/HistoryView';
import { RulesView } from './components/RulesView';
import { SettingsView } from './components/SettingsView';
import { api } from './api';
import {
  ScanResponse,
  StatusResponse,
  BatchItem,
  RuleConfig,
  AppConfig,
} from './types';
import { Check, AlertCircle, X } from 'lucide-react';

interface Toast {
  id: string;
  type: 'success' | 'error' | 'info';
  message: string;
}

export const App: React.FC = () => {
  const [currentTab, setCurrentTab] = useState<TabKey>('dashboard');
  const [isDarkMode, setIsDarkMode] = useState<boolean>(true);

  const [scanData, setScanData] = useState<ScanResponse | null>(null);
  const [statusData, setStatusData] = useState<StatusResponse | null>(null);
  const [batches, setBatches] = useState<BatchItem[]>([]);
  const [config, setConfig] = useState<AppConfig | null>(null);

  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isOrganizing, setIsOrganizing] = useState<boolean>(false);
  const [toasts, setToasts] = useState<Toast[]>([]);

  const addToast = (type: 'success' | 'error' | 'info', message: string) => {
    const id = Math.random().toString(36).substring(2, 9);
    setToasts((prev) => [...prev, { id, type, message }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 4000);
  };

  const loadAllData = useCallback(async () => {
    setIsLoading(true);
    try {
      const [scanRes, statusRes, historyRes, configRes] = await Promise.all([
        api.scan(),
        api.status(),
        api.history(20),
        api.config(),
      ]);
      setScanData(scanRes);
      setStatusData(statusRes);
      setBatches(historyRes.batches);
      setConfig(configRes);
    } catch (err) {
      console.error('Data load error:', err);
      addToast('error', 'Failed to refresh downloads status.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadAllData();
  }, [loadAllData]);

  // Global Keyboard Navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Don't trigger if focus is inside input or textarea
      if (['INPUT', 'TEXTAREA', 'SELECT'].includes((e.target as HTMLElement).tagName)) {
        return;
      }
      if (e.key === '1') setCurrentTab('dashboard');
      if (e.key === '2') setCurrentTab('preview');
      if (e.key === '3') setCurrentTab('history');
      if (e.key === '4') setCurrentTab('rules');
      if (e.key === '5') setCurrentTab('settings');
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  // Theme switching
  useEffect(() => {
    if (isDarkMode) {
      document.documentElement.classList.remove('theme-light');
    } else {
      document.documentElement.classList.add('theme-light');
    }
  }, [isDarkMode]);

  const handleOrganize = async () => {
    if (!scanData || scanData.total_ready === 0) return;
    setIsOrganizing(true);
    try {
      const res = await api.organize(false);
      addToast(
        'success',
        `Organized ${res.successful_moves} files safely! Zero clutter.`
      );
      if (res.failed_moves > 0) {
        addToast('error', `${res.failed_moves} files could not be moved.`);
      }
      await loadAllData();
      setCurrentTab('dashboard');
    } catch (err) {
      addToast('error', `Organization failed: ${err}`);
    } finally {
      setIsOrganizing(false);
    }
  };

  const handleUndoBatch = async (batchId: string) => {
    setIsLoading(true);
    try {
      await api.undo(batchId);
      addToast('success', 'Batch successfully restored to original locations.');
      await loadAllData();
    } catch (err) {
      addToast('error', `Undo failed: ${err}`);
    } finally {
      setIsLoading(false);
    }
  };

  const handleAddRule = (newRule: RuleConfig) => {
    if (!config) return;
    const updatedRules = [...config.rules, newRule];
    setConfig({ ...config, rules: updatedRules });
    addToast('success', `Added classification rule: ${newRule.name}`);
  };

  const handleSaveConfig = (updated: Partial<AppConfig>) => {
    if (!config) return;
    setConfig({ ...config, ...updated });
    addToast('success', 'Configuration updated successfully.');
  };

  const handleResetDefaults = () => {
    loadAllData();
    addToast('info', 'Reset settings to factory defaults.');
  };

  return (
    <div style={{ display: 'flex', width: '100vw', height: '100vh', background: 'var(--bg-primary)' }}>
      {/* Navigation Sidebar */}
      <Sidebar
        currentTab={currentTab}
        onSelectTab={setCurrentTab}
        readyCount={scanData?.total_ready ?? 0}
        isDarkMode={isDarkMode}
        onToggleTheme={() => setIsDarkMode(!isDarkMode)}
      />

      {/* Main View Area */}
      <main style={{ flex: 1, height: '100vh', overflow: 'hidden', position: 'relative' }}>
        {currentTab === 'dashboard' && (
          <Dashboard
            scanData={scanData}
            statusData={statusData}
            isLoading={isLoading}
            onRefreshScan={loadAllData}
            onOrganize={handleOrganize}
            onGoToPreview={() => setCurrentTab('preview')}
          />
        )}

        {currentTab === 'preview' && (
          <PreviewView
            scanData={scanData}
            onOrganize={handleOrganize}
            isOrganizing={isOrganizing}
          />
        )}

        {currentTab === 'history' && (
          <HistoryView
            batches={batches}
            isLoading={isLoading}
            onUndoBatch={handleUndoBatch}
          />
        )}

        {currentTab === 'rules' && (
          <RulesView
            rules={config?.rules ?? []}
            onAddRule={handleAddRule}
          />
        )}

        {currentTab === 'settings' && (
          <SettingsView
            config={config}
            status={statusData}
            onSaveConfig={handleSaveConfig}
            onResetDefaults={handleResetDefaults}
          />
        )}

        {/* Global Toast Notifications */}
        <div
          style={{
            position: 'fixed',
            bottom: 24,
            right: 24,
            display: 'flex',
            flexDirection: 'column',
            gap: 8,
            zIndex: 9999,
          }}
        >
          {toasts.map((t) => (
            <div
              key={t.id}
              className="glass-panel"
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 10,
                padding: '10px 16px',
                borderRadius: 8,
                background: 'var(--bg-surface)',
                boxShadow: '0 8px 24px rgba(0, 0, 0, 0.4)',
                border: '1px solid var(--border-highlight)',
                fontSize: 13,
                fontWeight: 500,
                color: 'var(--text-primary)',
              }}
            >
              {t.type === 'success' && <Check size={16} color="var(--accent-emerald)" />}
              {t.type === 'error' && <AlertCircle size={16} color="var(--accent-rose)" />}
              <span>{t.message}</span>
              <button
                onClick={() => setToasts((prev) => prev.filter((item) => item.id !== t.id))}
                style={{
                  background: 'transparent',
                  border: 'none',
                  color: 'var(--text-muted)',
                  cursor: 'pointer',
                  marginLeft: 8,
                }}
              >
                <X size={13} />
              </button>
            </div>
          ))}
        </div>
      </main>
    </div>
  );
};

export default App;
