import React, { useState, useEffect } from 'react';
import {
  Layers,
  Plus,
  RefreshCw,
  Edit2,
  CheckCircle,
  XCircle,
  Database,
  Sparkles,
  Save,
  X
} from 'lucide-react';
import { getSectors, createSector, updateSector, deactivateSector, reindexAllSectors } from '../services/api';

export default function SectorAdminPage() {
  const [sectors, setSectors] = useState([]);
  const [loading, setLoading] = useState(true);
  const [reindexing, setReindexing] = useState(false);
  const [reindexMessage, setReindexMessage] = useState('');

  // Add / Edit Modal state
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingSector, setEditingSector] = useState(null);
  const [formId, setFormId] = useState('');
  const [formName, setFormName] = useState('');
  const [formDesc, setFormDesc] = useState('');
  const [formKeywords, setFormKeywords] = useState('');
  const [formExamples, setFormExamples] = useState('');
  const [formNotes, setFormNotes] = useState('');
  const [formSubmitting, setFormSubmitting] = useState(false);

  useEffect(() => {
    loadSectors();
  }, []);

  const loadSectors = async () => {
    try {
      setLoading(true);
      const data = await getSectors(true); // include inactive
      setSectors(data);
    } catch (err) {
      console.error('Failed to load sectors:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleReindexAll = async () => {
    try {
      setReindexing(true);
      setReindexMessage('');
      const res = await reindexAllSectors();
      setReindexMessage(res.message);
      setTimeout(() => setReindexMessage(''), 5000);
    } catch (err) {
      alert('Re-indexing failed: ' + (err.response?.data?.detail || err.message));
    } finally {
      setReindexing(false);
    }
  };

  const openAddModal = () => {
    setEditingSector(null);
    setFormId('');
    setFormName('');
    setFormDesc('');
    setFormKeywords('');
    setFormExamples('');
    setFormNotes('');
    setIsModalOpen(true);
  };

  const openEditModal = (s) => {
    setEditingSector(s);
    setFormId(s.id);
    setFormName(s.name);
    setFormDesc(s.description);
    setFormKeywords((s.keywords || []).join(', '));
    setFormExamples((s.examples || []).join(', '));
    setFormNotes(s.notes || '');
    setIsModalOpen(true);
  };

  const handleFormSubmit = async (e) => {
    e.preventDefault();
    try {
      setFormSubmitting(true);
      const kwList = formKeywords.split(',').map((k) => k.trim()).filter(Boolean);
      const exList = formExamples.split(',').map((x) => x.trim()).filter(Boolean);

      if (editingSector) {
        await updateSector(editingSector.id, {
          name: formName,
          description: formDesc,
          keywords: kwList,
          examples: exList,
          notes: formNotes,
        });
      } else {
        await createSector({
          id: formId.trim().toLowerCase().replace(/\s+/g, '_'),
          name: formName,
          description: formDesc,
          keywords: kwList,
          examples: exList,
          notes: formNotes,
          active: true,
        });
      }

      setIsModalOpen(false);
      loadSectors();
    } catch (err) {
      alert('Save failed: ' + (err.response?.data?.detail || err.message));
    } finally {
      setFormSubmitting(false);
    }
  };

  const handleToggleActive = async (s) => {
    try {
      await updateSector(s.id, { active: !s.active });
      loadSectors();
    } catch (err) {
      alert('Toggle active failed: ' + (err.response?.data?.detail || err.message));
    }
  };

  return (
    <div className="p-8 space-y-6 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-3">
            <span>Sector Knowledge Base Administration</span>
            <span className="text-xs bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 px-2.5 py-0.5 rounded-full font-mono">
              {sectors.length} Sectors
            </span>
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Configure sector definitions, keywords, disambiguation notes, and trigger dynamic vector re-indexing into ChromaDB.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={openAddModal}
            className="px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-xs flex items-center gap-2 transition-all shadow-md shadow-emerald-600/20"
          >
            <Plus className="w-4 h-4" />
            <span>Add Sector</span>
          </button>
          <button
            disabled={reindexing}
            onClick={handleReindexAll}
            className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 font-semibold text-xs flex items-center gap-2 transition-all disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 text-blue-400 ${reindexing ? 'animate-spin' : ''}`} />
            <span>{reindexing ? 'Re-indexing...' : 'Re-index Vector Store'}</span>
          </button>
        </div>
      </div>

      {reindexMessage && (
        <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-xs flex items-center gap-2">
          <CheckCircle className="w-4 h-4" />
          <span>{reindexMessage}</span>
        </div>
      )}

      {/* Sectors Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {sectors.map((s) => (
          <div
            key={s.id}
            className={`p-5 rounded-2xl bg-slate-900 border transition-all space-y-3 ${
              s.active ? 'border-slate-800 hover:border-slate-700' : 'border-slate-850 opacity-60'
            }`}
          >
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-bold text-white flex items-center gap-2">
                  <span>{s.name}</span>
                  {!s.active && (
                    <span className="text-[10px] bg-slate-800 text-slate-400 px-2 py-0.5 rounded-full border border-slate-700">
                      Inactive
                    </span>
                  )}
                </h3>
                <span className="text-[11px] font-mono text-emerald-400">ID: {s.id}</span>
              </div>

              <div className="flex items-center gap-1.5">
                <button
                  onClick={() => openEditModal(s)}
                  className="p-1.5 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-white transition-colors"
                  title="Edit Sector"
                >
                  <Edit2 className="w-3.5 h-3.5" />
                </button>
                <button
                  onClick={() => handleToggleActive(s)}
                  className={`text-[11px] font-semibold px-2.5 py-1 rounded-lg border transition-colors ${
                    s.active
                      ? 'border-emerald-500/30 text-emerald-400 bg-emerald-500/10 hover:bg-emerald-500/20'
                      : 'border-slate-700 text-slate-400 bg-slate-800 hover:bg-slate-750'
                  }`}
                >
                  {s.active ? 'Active' : 'Enable'}
                </button>
              </div>
            </div>

            <p className="text-xs text-slate-300 leading-relaxed line-clamp-2">{s.description}</p>

            {s.keywords && s.keywords.length > 0 && (
              <div className="flex flex-wrap gap-1 text-[11px]">
                {s.keywords.slice(0, 5).map((kw, i) => (
                  <span
                    key={i}
                    className="px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-750 font-mono"
                  >
                    {kw}
                  </span>
                ))}
                {s.keywords.length > 5 && (
                  <span className="text-slate-500 text-[11px] self-center">+{s.keywords.length - 5} more</span>
                )}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Add / Edit Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-3xl p-6 w-full max-w-xl shadow-2xl space-y-4 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-base font-bold text-white">
                {editingSector ? `Edit Sector: ${editingSector.name}` : 'Add New Sector'}
              </h3>
              <button onClick={() => setIsModalOpen(false)} className="text-slate-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleFormSubmit} className="space-y-3.5 text-xs">
              {!editingSector && (
                <div>
                  <label className="text-slate-300 font-semibold block mb-1">Sector ID (snake_case)</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. clean_energy"
                    value={formId}
                    onChange={(e) => setFormId(e.target.value)}
                    className="w-full px-3.5 py-2 rounded-xl bg-slate-800 border border-slate-700 text-white font-mono text-xs focus:outline-none focus:border-emerald-500"
                  />
                </div>
              )}

              <div>
                <label className="text-slate-300 font-semibold block mb-1">Sector Name</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Clean Energy & Utilities"
                  value={formName}
                  onChange={(e) => setFormName(e.target.value)}
                  className="w-full px-3.5 py-2 rounded-xl bg-slate-800 border border-slate-700 text-white text-xs focus:outline-none focus:border-emerald-500"
                />
              </div>

              <div>
                <label className="text-slate-300 font-semibold block mb-1">Description (RAG Chunk 1)</label>
                <textarea
                  rows={3}
                  required
                  placeholder="Detailed description of business types and services in this sector..."
                  value={formDesc}
                  onChange={(e) => setFormDesc(e.target.value)}
                  className="w-full px-3.5 py-2 rounded-xl bg-slate-800 border border-slate-700 text-white text-xs focus:outline-none focus:border-emerald-500 leading-relaxed"
                />
              </div>

              <div>
                <label className="text-slate-300 font-semibold block mb-1">Keywords (Comma separated, RAG Chunk 2)</label>
                <input
                  type="text"
                  placeholder="solar, wind, battery storage, grid modernization"
                  value={formKeywords}
                  onChange={(e) => setFormKeywords(e.target.value)}
                  className="w-full px-3.5 py-2 rounded-xl bg-slate-800 border border-slate-700 text-white text-xs focus:outline-none focus:border-emerald-500"
                />
              </div>

              <div>
                <label className="text-slate-300 font-semibold block mb-1">Example Businesses (Comma separated, RAG Chunk 3)</label>
                <input
                  type="text"
                  placeholder="NextEra Energy, Enphase, Sunrun"
                  value={formExamples}
                  onChange={(e) => setFormExamples(e.target.value)}
                  className="w-full px-3.5 py-2 rounded-xl bg-slate-800 border border-slate-700 text-white text-xs focus:outline-none focus:border-emerald-500"
                />
              </div>

              <div>
                <label className="text-slate-300 font-semibold block mb-1">Disambiguation Notes</label>
                <textarea
                  rows={2}
                  placeholder="Rules for resolving ambiguity with nearby sectors..."
                  value={formNotes}
                  onChange={(e) => setFormNotes(e.target.value)}
                  className="w-full px-3.5 py-2 rounded-xl bg-slate-800 border border-slate-700 text-white text-xs focus:outline-none focus:border-emerald-500 leading-relaxed"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-4 py-2 rounded-xl text-slate-400 hover:text-white hover:bg-slate-800 font-medium"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={formSubmitting}
                  className="px-5 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-semibold flex items-center gap-1.5 transition-all"
                >
                  <Save className="w-4 h-4" />
                  <span>{formSubmitting ? 'Saving...' : 'Save & Re-index'}</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
