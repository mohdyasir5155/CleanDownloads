import React, { useState } from 'react';
import { Plus, Search, Folder, X } from 'lucide-react';
import { RuleConfig } from '../types';

interface RulesViewProps {
  rules: RuleConfig[];
  onAddRule: (rule: RuleConfig) => void;
}

export const RulesView: React.FC<RulesViewProps> = ({ rules, onAddRule }) => {
  const [search, setSearch] = useState('');
  const [isModalOpen, setIsModalOpen] = useState(false);

  const [newName, setNewName] = useState('');
  const [newCategory, setNewCategory] = useState('');
  const [newSubfolder, setNewSubfolder] = useState('');
  const [newExtensions, setNewExtensions] = useState('');

  const filteredRules = rules.filter(
    (r) =>
      r.name.toLowerCase().includes(search.toLowerCase()) ||
      r.category.toLowerCase().includes(search.toLowerCase()) ||
      r.extensions.some((e) => e.toLowerCase().includes(search.toLowerCase()))
  );

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newName || !newCategory || !newSubfolder || !newExtensions) return;

    const exts = newExtensions
      .split(',')
      .map((e) => e.trim().toLowerCase().replace(/^\./, ''))
      .filter(Boolean);

    onAddRule({
      name: newName,
      category: newCategory,
      subfolder: newSubfolder,
      extensions: exts,
    });

    setIsModalOpen(false);
    setNewName('');
    setNewCategory('');
    setNewSubfolder('');
    setNewExtensions('');
  };

  return (
    <div style={{ padding: '32px 40px', overflowY: 'auto', height: '100vh' }} className="animate-fade-in">
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 700, letterSpacing: '-0.02em', marginBottom: 4 }}>
            Classification Rules ({rules.length})
          </h1>
          <p style={{ color: 'var(--text-muted)', fontSize: 13 }}>
            Map file extensions to target category folders. Custom rules take priority.
          </p>
        </div>

        <button
          onClick={() => setIsModalOpen(true)}
          className="btn-primary"
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 6,
            padding: '9px 14px',
            borderRadius: 8,
            fontSize: 13,
            fontWeight: 600,
            border: 'none',
            cursor: 'pointer',
          }}
        >
          <Plus size={15} />
          <span>Add Custom Rule</span>
        </button>
      </div>

      {/* Search Bar */}
      <div style={{ position: 'relative', marginBottom: 20 }}>
        <Search size={15} color="var(--text-muted)" style={{ position: 'absolute', left: 12, top: 12 }} />
        <input
          type="text"
          placeholder="Filter by rule name, category, or extension (e.g. 'pdf', 'Code')..."
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

      {/* Rules Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 14 }}>
        {filteredRules.map((r, i) => (
          <div
            key={i}
            className="glass-surface"
            style={{
              padding: '16px 18px',
              borderRadius: 10,
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between',
              gap: 12,
            }}
          >
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 6 }}>
                <span style={{ fontWeight: 600, fontSize: 14 }}>{r.name}</span>
                <span
                  style={{
                    fontSize: 10,
                    fontWeight: 600,
                    padding: '2px 7px',
                    borderRadius: 9999,
                    background: 'rgba(99, 102, 241, 0.15)',
                    color: 'var(--accent-indigo)',
                  }}
                >
                  {r.category}
                </span>
              </div>

              <div
                className="font-mono-code"
                style={{ fontSize: 11.5, color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: 6 }}
              >
                <Folder size={12} color="var(--accent-indigo)" />
                <span>Downloads/{r.subfolder}</span>
              </div>
            </div>

            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 5 }}>
              {r.extensions.map((ext) => (
                <span
                  key={ext}
                  className="font-mono-code"
                  style={{
                    fontSize: 11,
                    padding: '2px 7px',
                    borderRadius: 4,
                    background: 'rgba(255, 255, 255, 0.05)',
                    border: '1px solid var(--border-subtle)',
                    color: 'var(--text-secondary)',
                  }}
                >
                  .{ext}
                </span>
              ))}
            </div>
          </div>
        ))}
      </div>

      {/* Add Rule Modal */}
      {isModalOpen && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0, 0, 0, 0.7)',
            backdropFilter: 'blur(4px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 100,
          }}
        >
          <div
            className="glass-panel"
            style={{
              width: 440,
              padding: 24,
              borderRadius: 12,
              background: 'var(--bg-secondary)',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 18 }}>
              <h3 style={{ fontSize: 16, fontWeight: 700 }}>Add Custom Rule</h3>
              <button
                onClick={() => setIsModalOpen(false)}
                style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}
              >
                <X size={16} />
              </button>
            </div>

            <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              <div>
                <label style={{ fontSize: 12, color: 'var(--text-secondary)', display: 'block', marginBottom: 4 }}>
                  Rule Name
                </label>
                <input
                  type="text"
                  placeholder="e.g. Photoshop Files"
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  required
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    borderRadius: 6,
                    border: '1px solid var(--border-subtle)',
                    background: 'var(--bg-surface)',
                    color: 'var(--text-primary)',
                    fontSize: 13,
                    outline: 'none',
                  }}
                />
              </div>

              <div>
                <label style={{ fontSize: 12, color: 'var(--text-secondary)', display: 'block', marginBottom: 4 }}>
                  Category
                </label>
                <input
                  type="text"
                  placeholder="e.g. Design"
                  value={newCategory}
                  onChange={(e) => setNewCategory(e.target.value)}
                  required
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    borderRadius: 6,
                    border: '1px solid var(--border-subtle)',
                    background: 'var(--bg-surface)',
                    color: 'var(--text-primary)',
                    fontSize: 13,
                    outline: 'none',
                  }}
                />
              </div>

              <div>
                <label style={{ fontSize: 12, color: 'var(--text-secondary)', display: 'block', marginBottom: 4 }}>
                  Target Subfolder under Downloads
                </label>
                <input
                  type="text"
                  placeholder="e.g. Design/Photoshop"
                  value={newSubfolder}
                  onChange={(e) => setNewSubfolder(e.target.value)}
                  required
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    borderRadius: 6,
                    border: '1px solid var(--border-subtle)',
                    background: 'var(--bg-surface)',
                    color: 'var(--text-primary)',
                    fontSize: 13,
                    outline: 'none',
                  }}
                />
              </div>

              <div>
                <label style={{ fontSize: 12, color: 'var(--text-secondary)', display: 'block', marginBottom: 4 }}>
                  Extensions (comma-separated, without dot)
                </label>
                <input
                  type="text"
                  placeholder="e.g. psd, psb"
                  value={newExtensions}
                  onChange={(e) => setNewExtensions(e.target.value)}
                  required
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    borderRadius: 6,
                    border: '1px solid var(--border-subtle)',
                    background: 'var(--bg-surface)',
                    color: 'var(--text-primary)',
                    fontSize: 13,
                    outline: 'none',
                  }}
                />
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, marginTop: 10 }}>
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="btn-secondary"
                  style={{ padding: '8px 14px', borderRadius: 6, fontSize: 13, cursor: 'pointer' }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn-primary"
                  style={{ padding: '8px 16px', borderRadius: 6, fontSize: 13, border: 'none', cursor: 'pointer' }}
                >
                  Save Rule
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
