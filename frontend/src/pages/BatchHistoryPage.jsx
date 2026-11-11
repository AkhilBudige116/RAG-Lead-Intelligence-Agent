import React, { useState, useEffect } from 'react';
import { History, RefreshCw, FileText, CheckCircle2, AlertCircle, Clock } from 'lucide-react';
import { getBatches } from '../services/api';

export default function BatchHistoryPage() {
  const [batches, setBatches] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadBatches();
  }, []);

  const loadBatches = async () => {
    try {
      setLoading(true);
      const res = await getBatches({ limit: 50 });
      setBatches(res.items || []);
      setTotal(res.total || 0);
    } catch (err) {
      console.error('Failed to load batch history:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-8 space-y-6 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-3">
            <span>Email Processing Batch History</span>
            <span className="text-xs bg-slate-800 text-slate-300 border border-slate-700 px-2.5 py-0.5 rounded-full font-mono">
              {total} Total Batches
            </span>
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Complete historical audit of email ingestion jobs, batch status, processing durations, and error logs.
          </p>
        </div>

        <button
          onClick={loadBatches}
          className="p-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white transition-colors"
          title="Refresh History"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {/* Batches Table */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900 overflow-hidden shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-300">
            <thead className="bg-slate-850 uppercase text-[10px] font-semibold text-slate-400 border-b border-slate-800">
              <tr>
                <th className="py-3 px-4">Batch ID</th>
                <th className="py-3 px-4">Filename / Source</th>
                <th className="py-3 px-4 text-center">Total</th>
                <th className="py-3 px-4 text-center">Processed</th>
                <th className="py-3 px-4 text-center">Failed</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4 text-right">Upload Date</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800 font-mono">
              {loading ? (
                <tr>
                  <td colSpan="7" className="py-12 text-center text-slate-500 font-sans">
                    Loading batch records...
                  </td>
                </tr>
              ) : batches.length === 0 ? (
                <tr>
                  <td colSpan="7" className="py-12 text-center text-slate-500 font-sans">
                    No upload batches recorded.
                  </td>
                </tr>
              ) : (
                batches.map((b) => {
                  const isCompleted = b.status === 'completed';
                  const isFailed = b.status === 'failed';
                  return (
                    <tr key={b.id} className="hover:bg-slate-850/50 transition-colors">
                      <td className="py-3 px-4 text-emerald-400 font-bold">
                        {b.id.substring(0, 8)}...
                      </td>
                      <td className="py-3 px-4 font-sans text-slate-200">
                        <div className="flex items-center gap-2">
                          <FileText className="w-3.5 h-3.5 text-slate-500 shrink-0" />
                          <span className="truncate max-w-[260px]">{b.filename}</span>
                        </div>
                      </td>
                      <td className="py-3 px-4 text-center text-white">{b.total_emails}</td>
                      <td className="py-3 px-4 text-center text-emerald-400 font-bold">{b.processed_count}</td>
                      <td className="py-3 px-4 text-center text-red-400 font-bold">{b.failed_count}</td>
                      <td className="py-3 px-4 font-sans">
                        <span
                          className={`px-2.5 py-0.5 rounded-full text-[11px] font-semibold border ${
                            isCompleted
                              ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30'
                              : isFailed
                              ? 'bg-red-500/15 text-red-400 border-red-500/30'
                              : 'bg-amber-500/15 text-amber-400 border-amber-500/30'
                          }`}
                        >
                          {b.status}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-right text-slate-400 font-sans">
                        {b.created_at ? new Date(b.created_at).toLocaleString() : 'N/A'}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
