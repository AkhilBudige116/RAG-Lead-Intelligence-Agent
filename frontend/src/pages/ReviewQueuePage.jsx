import React, { useState, useEffect } from 'react';
import {
  CheckSquare,
  Check,
  Edit2,
  AlertTriangle,
  Building2,
  Mail,
  Globe,
  Sparkles,
  Layers,
  Save,
  X
} from 'lucide-react';
import { getReviewQueue, processReviewAction, getSectors } from '../services/api';

export default function ReviewQueuePage({ onReviewProcessed }) {
  const [queue, setQueue] = useState([]);
  const [sectors, setSectors] = useState([]);
  const [loading, setLoading] = useState(true);

  // Modal state for changing sector
  const [modalLead, setModalLead] = useState(null);
  const [targetSectorId, setTargetSectorId] = useState('');
  const [reviewerName, setReviewerName] = useState('Senior Analyst');
  const [reviewerNotes, setReviewerNotes] = useState('');
  const [learnAsExample, setLearnAsExample] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const [queueRes, sectorsRes] = await Promise.all([
        getReviewQueue(),
        getSectors()
      ]);
      setQueue(queueRes.items || []);
      setSectors(sectorsRes || []);
    } catch (err) {
      console.error('Failed to load review queue:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleAccept = async (lead) => {
    try {
      await processReviewAction(lead.id, {
        action: 'accept',
        reviewer_name: reviewerName,
        learn_as_example: false
      });
      loadData();
      if (onReviewProcessed) onReviewProcessed();
    } catch (err) {
      alert('Failed to accept suggestion: ' + (err.response?.data?.detail || err.message));
    }
  };

  const openChangeModal = (lead) => {
    setModalLead(lead);
    setTargetSectorId(lead.suggested_sector_id || (sectors[0]?.id || ''));
    setReviewerNotes('');
    setLearnAsExample(false);
  };

  const handleModalSave = async (e) => {
    e.preventDefault();
    if (!modalLead || !targetSectorId) return;

    try {
      setSubmitting(true);
      await processReviewAction(modalLead.id, {
        action: 'change',
        target_sector_id: targetSectorId,
        reviewer_name: reviewerName,
        notes: reviewerNotes,
        learn_as_example: learnAsExample
      });
      setModalLead(null);
      loadData();
      if (onReviewProcessed) onReviewProcessed();
    } catch (err) {
      alert('Failed to save correction: ' + (err.response?.data?.detail || err.message));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="p-8 space-y-6 max-w-6xl mx-auto">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-3">
          <span>Human-in-the-Loop Review Queue</span>
          <span className="text-xs bg-amber-500/20 text-amber-400 border border-amber-500/30 px-2.5 py-0.5 rounded-full font-mono">
            {queue.length} Pending
          </span>
        </h1>
        <p className="text-sm text-slate-400 mt-1">
          Review leads with uncertain classifications or low dual-factor confidence scores. Confirm suggestions or correct sector mappings.
        </p>
      </div>

      {loading ? (
        <div className="space-y-4">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="h-44 bg-slate-900 rounded-2xl border border-slate-800 animate-pulse"></div>
          ))}
        </div>
      ) : queue.length === 0 ? (
        <div className="p-12 text-center rounded-3xl bg-slate-900 border border-slate-800">
          <CheckSquare className="w-12 h-12 text-emerald-400 mx-auto mb-3" />
          <h3 className="text-base font-semibold text-white">Review Queue is Clear!</h3>
          <p className="text-xs text-slate-400 mt-1">
            All ingested leads satisfy the confidence threshold or have already been reviewed.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {queue.map((lead) => {
            const conf = lead.confidence || 0.0;
            return (
              <div
                key={lead.id}
                className="p-6 rounded-2xl bg-slate-900 border border-slate-800 hover:border-slate-700 transition-all space-y-4"
              >
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-slate-800 border border-slate-700 flex items-center justify-center shrink-0">
                      <Building2 className="w-5 h-5 text-amber-400" />
                    </div>
                    <div>
                      <h3 className="text-base font-bold text-white">{lead.company_name}</h3>
                      <div className="flex items-center gap-3 text-xs text-slate-400 mt-0.5">
                        <span className="flex items-center gap-1">
                          <Mail className="w-3.5 h-3.5 text-slate-500" />
                          {lead.email}
                        </span>
                        {lead.domain && (
                          <span className="flex items-center gap-1 font-mono text-slate-400">
                            <Globe className="w-3.5 h-3.5 text-slate-500" />
                            {lead.domain}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => handleAccept(lead)}
                      disabled={!lead.suggested_sector_id}
                      className="px-4 py-2 rounded-xl bg-emerald-600/20 hover:bg-emerald-600 text-emerald-300 hover:text-white border border-emerald-500/30 text-xs font-semibold flex items-center gap-1.5 transition-all disabled:opacity-40"
                    >
                      <Check className="w-4 h-4" />
                      <span>Accept Suggestion</span>
                    </button>
                    <button
                      onClick={() => openChangeModal(lead)}
                      className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-xs font-semibold flex items-center gap-1.5 transition-all"
                    >
                      <Edit2 className="w-4 h-4" />
                      <span>Change Sector</span>
                    </button>
                  </div>
                </div>

                {/* Classification Evaluation Box */}
                <div className="p-4 rounded-xl bg-slate-850/80 border border-slate-800/80 grid grid-cols-1 md:grid-cols-4 gap-4 text-xs">
                  <div>
                    <span className="text-[11px] text-slate-400 block mb-1">AI Suggested Sector</span>
                    <span className="font-bold text-amber-400 text-sm">
                      {lead.suggested_sector_name || 'Needs Review'}
                    </span>
                  </div>
                  <div>
                    <span className="text-[11px] text-slate-400 block mb-1">Dual-Factor Confidence</span>
                    <span className="font-bold text-white text-sm">{(conf * 100).toFixed(1)}%</span>
                  </div>
                  <div className="md:col-span-2">
                    <span className="text-[11px] text-slate-400 block mb-1">Model Reasoning & Flag Rationale</span>
                    <p className="text-slate-300 text-xs leading-relaxed">{lead.reason || 'Flagged for review.'}</p>
                  </div>
                </div>

                {/* Evidence Chips */}
                {lead.evidence && lead.evidence.length > 0 && (
                  <div className="flex items-center gap-2 flex-wrap text-xs">
                    <span className="text-slate-500 font-semibold text-[11px]">Evidence:</span>
                    {lead.evidence.map((ev, i) => (
                      <span
                        key={i}
                        className="px-2.5 py-0.5 rounded-md bg-slate-800 border border-slate-700 text-slate-300 font-mono text-[11px]"
                      >
                        "{ev}"
                      </span>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Change Sector Modal */}
      {modalLead && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-3xl p-6 w-full max-w-lg shadow-2xl space-y-5">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-base font-bold text-white">Reclassify Lead Sector</h3>
              <button
                onClick={() => setModalLead(null)}
                className="text-slate-400 hover:text-white"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleModalSave} className="space-y-4 text-xs">
              <div>
                <label className="text-slate-300 font-semibold block mb-1">Target Company</label>
                <p className="text-white font-bold text-sm bg-slate-850 p-3 rounded-xl border border-slate-800">
                  {modalLead.company_name}
                </p>
              </div>

              <div>
                <label className="text-slate-300 font-semibold block mb-1">Select Industry Sector</label>
                <select
                  required
                  value={targetSectorId}
                  onChange={(e) => setTargetSectorId(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-xl bg-slate-800 border border-slate-700 text-white text-xs focus:outline-none focus:border-emerald-500"
                >
                  {sectors.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="text-slate-300 font-semibold block mb-1">Reviewer Name / ID</label>
                <input
                  type="text"
                  required
                  value={reviewerName}
                  onChange={(e) => setReviewerName(e.target.value)}
                  className="w-full px-3.5 py-2 rounded-xl bg-slate-800 border border-slate-700 text-white text-xs focus:outline-none focus:border-emerald-500"
                />
              </div>

              <div>
                <label className="text-slate-300 font-semibold block mb-1">Reviewer Justification / Notes</label>
                <textarea
                  rows={2}
                  placeholder="Reason for manual sector assignment..."
                  value={reviewerNotes}
                  onChange={(e) => setReviewerNotes(e.target.value)}
                  className="w-full px-3.5 py-2 rounded-xl bg-slate-800 border border-slate-700 text-white text-xs focus:outline-none focus:border-emerald-500 leading-relaxed"
                />
              </div>

              <div className="flex items-center gap-2 p-3 rounded-xl bg-slate-850/80 border border-slate-800">
                <input
                  type="checkbox"
                  id="learnExample"
                  checked={learnAsExample}
                  onChange={(e) => setLearnAsExample(e.target.checked)}
                  className="rounded border-slate-700 text-emerald-500 focus:ring-0 bg-slate-800"
                />
                <label htmlFor="learnExample" className="text-slate-300 cursor-pointer text-xs">
                  Add <strong>{modalLead.company_name}</strong> as confirmed example in Sector Knowledge Base
                </label>
              </div>

              <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setModalLead(null)}
                  className="px-4 py-2 rounded-xl text-slate-400 hover:text-white hover:bg-slate-800 font-medium"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-5 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-semibold flex items-center gap-1.5 transition-all"
                >
                  <Save className="w-4 h-4" />
                  <span>{submitting ? 'Saving...' : 'Confirm & Save'}</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
