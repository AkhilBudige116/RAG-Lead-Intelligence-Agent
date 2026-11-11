import React, { useState, useEffect } from 'react';
import {
  CopyCheck,
  GitMerge,
  Undo2,
  Trash2,
  Building2,
  CheckCircle,
  AlertTriangle,
  ArrowRight,
  ShieldAlert,
  History
} from 'lucide-react';
import { getDuplicates, confirmMerge, rejectDuplicate, undoMerge } from '../services/api';

export default function DuplicateManagementPage() {
  const [data, setData] = useState({ potential_duplicates: [], confirmed_merges: [] });
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('potential'); // 'potential' or 'history'
  const [actionLoading, setActionLoading] = useState(false);

  useEffect(() => {
    loadDuplicates();
  }, []);

  const loadDuplicates = async () => {
    try {
      setLoading(true);
      const res = await getDuplicates();
      setData(res);
    } catch (err) {
      console.error('Failed to load duplicates:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleMerge = async (keptId, mergedId) => {
    try {
      setActionLoading(true);
      await confirmMerge(keptId, mergedId);
      loadDuplicates();
    } catch (err) {
      alert('Merge failed: ' + (err.response?.data?.detail || err.message));
    } finally {
      setActionLoading(false);
    }
  };

  const handleReject = async (logId) => {
    try {
      setActionLoading(true);
      await rejectDuplicate(logId);
      loadDuplicates();
    } catch (err) {
      alert('Reject failed: ' + (err.response?.data?.detail || err.message));
    } finally {
      setActionLoading(false);
    }
  };

  const handleUndo = async (logId) => {
    try {
      setActionLoading(true);
      await undoMerge(logId);
      loadDuplicates();
    } catch (err) {
      alert('Undo merge failed: ' + (err.response?.data?.detail || err.message));
    } finally {
      setActionLoading(false);
    }
  };

  return (
    <div className="p-8 space-y-6 max-w-6xl mx-auto">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-3">
          <span>Duplicate Detection & Consolidation</span>
          <span className="text-xs bg-purple-500/20 text-purple-400 border border-purple-500/30 px-2.5 py-0.5 rounded-full font-mono">
            {data.potential_duplicates.length} Flagged
          </span>
        </h1>
        <p className="text-sm text-slate-400 mt-1">
          Review potential duplicate companies flagged by fuzzy matching (Rule 3) and manage audit merge history with full undo support.
        </p>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-2 border-b border-slate-800 pb-2">
        <button
          onClick={() => setActiveTab('potential')}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-all ${
            activeTab === 'potential'
              ? 'bg-purple-500/20 text-purple-400 border border-purple-500/30'
              : 'text-slate-400 hover:text-white'
          }`}
        >
          <AlertTriangle className="w-4 h-4" />
          <span>Potential Duplicate Pairs ({data.potential_duplicates.length})</span>
        </button>
        <button
          onClick={() => setActiveTab('history')}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-all ${
            activeTab === 'history'
              ? 'bg-purple-500/20 text-purple-400 border border-purple-500/30'
              : 'text-slate-400 hover:text-white'
          }`}
        >
          <History className="w-4 h-4" />
          <span>Consolidated Audit Log ({data.confirmed_merges.length})</span>
        </button>
      </div>

      {activeTab === 'potential' ? (
        loading ? (
          <div className="space-y-4">
            {[...Array(2)].map((_, i) => (
              <div key={i} className="h-44 bg-slate-900 rounded-2xl border border-slate-800 animate-pulse"></div>
            ))}
          </div>
        ) : data.potential_duplicates.length === 0 ? (
          <div className="p-12 text-center rounded-3xl bg-slate-900 border border-slate-800">
            <CopyCheck className="w-12 h-12 text-emerald-400 mx-auto mb-3" />
            <h3 className="text-base font-semibold text-white">No Uncertain Duplicate Flags</h3>
            <p className="text-xs text-slate-400 mt-1">
              Exact email and domain matches have been automatically consolidated.
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {data.potential_duplicates.map((pair) => (
              <div
                key={pair.log_id}
                className="p-6 rounded-2xl bg-slate-900 border border-slate-800 space-y-4"
              >
                <div className="flex items-center justify-between text-xs border-b border-slate-800/80 pb-3">
                  <div className="flex items-center gap-2">
                    <span className="font-mono bg-purple-500/10 text-purple-400 px-2.5 py-0.5 rounded border border-purple-500/20">
                      Rule: {pair.rule}
                    </span>
                    <span className="text-slate-400">
                      Fuzzy Name Similarity: <strong className="text-white">{pair.similarity}%</strong>
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      disabled={actionLoading}
                      onClick={() => handleMerge(pair.company_a.id, pair.company_b.id)}
                      className="px-3.5 py-1.5 rounded-xl bg-purple-600 hover:bg-purple-500 text-white font-semibold text-xs flex items-center gap-1.5 transition-all shadow-md shadow-purple-600/20"
                    >
                      <GitMerge className="w-3.5 h-3.5" />
                      <span>Merge Companies</span>
                    </button>
                    <button
                      disabled={actionLoading}
                      onClick={() => handleReject(pair.log_id)}
                      className="px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold flex items-center gap-1.5 transition-all"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                      <span>Reject Flag</span>
                    </button>
                  </div>
                </div>

                {/* Side by side comparison */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {/* Company A */}
                  <div className="p-4 rounded-xl bg-slate-850/80 border border-slate-800 space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] uppercase font-bold tracking-wider text-slate-400">
                        Primary Record (Kept)
                      </span>
                      <span className="text-xs font-mono text-slate-500">ID: {pair.company_a.id}</span>
                    </div>
                    <p className="text-base font-bold text-white">{pair.company_a.name}</p>
                    <div className="text-xs text-slate-400 space-y-1">
                      <p>Domain: <strong className="text-slate-200">{pair.company_a.domain || 'N/A'}</strong></p>
                      <p>Sector: <strong className="text-slate-200">{pair.company_a.sector}</strong></p>
                      <p>Contacts Linked: <strong className="text-slate-200">{pair.company_a.contacts_count}</strong></p>
                    </div>
                  </div>

                  {/* Company B */}
                  <div className="p-4 rounded-xl bg-slate-850/80 border border-slate-800 space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] uppercase font-bold tracking-wider text-slate-400">
                        Duplicate Candidate (To Merge)
                      </span>
                      <span className="text-xs font-mono text-slate-500">ID: {pair.company_b.id}</span>
                    </div>
                    <p className="text-base font-bold text-white">{pair.company_b.name}</p>
                    <div className="text-xs text-slate-400 space-y-1">
                      <p>Domain: <strong className="text-slate-200">{pair.company_b.domain || 'N/A'}</strong></p>
                      <p>Sector: <strong className="text-slate-200">{pair.company_b.sector}</strong></p>
                      <p>Contacts Linked: <strong className="text-slate-200">{pair.company_b.contacts_count}</strong></p>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )
      ) : (
        /* Confirmed Merges Audit History Table */
        <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 space-y-4">
          <h3 className="text-sm font-semibold text-white">Consolidated Company Merges</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-300">
              <thead className="bg-slate-850/80 uppercase text-[10px] text-slate-400 border-b border-slate-800">
                <tr>
                  <th className="py-3 px-3">Rule</th>
                  <th className="py-3 px-3">Kept Master Entity</th>
                  <th className="py-3 px-3">Merged Child Entity</th>
                  <th className="py-3 px-3">Timestamp</th>
                  <th className="py-3 px-3 text-right">Undo Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800 font-mono">
                {data.confirmed_merges.map((m) => (
                  <tr key={m.log_id} className="hover:bg-slate-850/40">
                    <td className="py-3 px-3 text-purple-400 font-sans">{m.rule}</td>
                    <td className="py-3 px-3 font-sans text-white font-semibold">
                      {m.kept_company?.name} (ID: {m.kept_company?.id})
                    </td>
                    <td className="py-3 px-3 font-sans text-slate-400">
                      {m.merged_company?.name} (ID: {m.merged_company?.id})
                    </td>
                    <td className="py-3 px-3 text-slate-500 font-sans">
                      {m.merged_at ? new Date(m.merged_at).toLocaleString() : 'N/A'}
                    </td>
                    <td className="py-3 px-3 text-right font-sans">
                      <button
                        disabled={actionLoading}
                        onClick={() => handleUndo(m.log_id)}
                        className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white text-xs font-semibold flex items-center gap-1.5 ml-auto transition-colors"
                      >
                        <Undo2 className="w-3.5 h-3.5" />
                        <span>Undo Merge</span>
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
