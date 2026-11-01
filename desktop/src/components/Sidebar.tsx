import React from 'react';
import {
  LayoutDashboard,
  Eye,
  History,
  Sliders,
  Settings,
  Sun,
  Moon,
  FolderSync,
} from 'lucide-react';

export type TabKey = 'dashboard' | 'preview' | 'history' | 'rules' | 'settings';

interface SidebarProps {
  currentTab: TabKey;
  onSelectTab: (tab: TabKey) => void;
  readyCount: number;
  isDarkMode: boolean;
  onToggleTheme: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  currentTab,
  onSelectTab,
  readyCount,
  isDarkMode,
  onToggleTheme,
}) => {
  const navItems: { key: TabKey; label: string; icon: React.ReactNode; shortcut: string; badge?: number }[] = [
    {
      key: 'dashboard',
      label: 'Dashboard',
      icon: <LayoutDashboard size={18} />,
      shortcut: '1',
    },
    {
      key: 'preview',
      label: 'Preview',
      icon: <Eye size={18} />,
      shortcut: '2',
      badge: readyCount > 0 ? readyCount : undefined,
    },
    {
      key: 'history',
      label: 'History & Undo',
      icon: <History size={18} />,
      shortcut: '3',
    },
    {
      key: 'rules',
      label: 'Custom Rules',
      icon: <Sliders size={18} />,
      shortcut: '4',
    },
    {
      key: 'settings',
      label: 'Settings',
      icon: <Settings size={18} />,
      shortcut: '5',
    },
  ];

  return (
    <aside
      style={{
        width: 250,
        height: '100vh',
        background: 'var(--bg-secondary)',
        borderRight: '1px solid var(--border-subtle)',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        padding: '20px 14px',
      }}
    >
      <div>
        {/* Brand Header */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '6px 10px', marginBottom: 22 }}>
          <div
            style={{
              width: 32,
              height: 32,
              borderRadius: 8,
              background: 'linear-gradient(135deg, #6366f1 0%, #06b6d4 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 2px 8px rgba(99, 102, 241, 0.4)',
            }}
          >
            <FolderSync size={18} color="#fff" />
          </div>
          <div>
            <div style={{ fontWeight: 700, fontSize: 14, letterSpacing: '-0.02em', display: 'flex', alignItems: 'center', gap: 6 }}>
              CleanDownloads
            </div>
            <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>
              One command. Zero clutter.
            </div>
          </div>
        </div>

        {/* Navigation list */}
        <nav style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
          {navItems.map((item) => {
            const isActive = currentTab === item.key;
            return (
              <button
                key={item.key}
                onClick={() => onSelectTab(item.key)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '9px 12px',
                  borderRadius: 7,
                  border: 'none',
                  background: isActive ? 'var(--bg-surface-hover)' : 'transparent',
                  color: isActive ? 'var(--text-primary)' : 'var(--text-secondary)',
                  cursor: 'pointer',
                  fontWeight: isActive ? 600 : 500,
                  fontSize: 13,
                  transition: 'all 0.15s ease',
                  outline: 'none',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <span style={{ color: isActive ? 'var(--accent-indigo)' : 'var(--text-muted)' }}>
                    {item.icon}
                  </span>
                  <span>{item.label}</span>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  {item.badge !== undefined && (
                    <span
                      style={{
                        padding: '1px 6px',
                        borderRadius: 9999,
                        background: 'rgba(99, 102, 241, 0.2)',
                        color: 'var(--accent-indigo)',
                        fontSize: 10,
                        fontWeight: 700,
                      }}
                    >
                      {item.badge}
                    </span>
                  )}
                  <kbd
                    style={{
                      fontSize: 10,
                      color: 'var(--text-muted)',
                      background: 'rgba(255, 255, 255, 0.05)',
                      padding: '1px 5px',
                      borderRadius: 4,
                      border: '1px solid var(--border-subtle)',
                    }}
                  >
                    {item.shortcut}
                  </kbd>
                </div>
              </button>
            );
          })}
        </nav>
      </div>

      {/* Footer Controls */}
      <div style={{ borderTop: '1px solid var(--border-subtle)', paddingTop: 14 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0 8px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <div
              style={{
                width: 7,
                height: 7,
                borderRadius: '50%',
                background: 'var(--accent-emerald)',
                boxShadow: '0 0 8px var(--accent-emerald)',
              }}
            />
            <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>Local Engine Active</span>
          </div>

          <button
            onClick={onToggleTheme}
            title={isDarkMode ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
            style={{
              background: 'transparent',
              border: 'none',
              color: 'var(--text-muted)',
              cursor: 'pointer',
              display: 'flex',
              padding: 4,
              borderRadius: 6,
            }}
          >
            {isDarkMode ? <Sun size={15} /> : <Moon size={15} />}
          </button>
        </div>
      </div>
    </aside>
  );
};
