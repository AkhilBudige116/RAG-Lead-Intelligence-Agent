import React, { useEffect, useState } from 'react';
import {
  Mail,
  Building2,
  CheckCircle2,
  AlertCircle,
  Copy,
  TrendingUp,
  BarChart3,
  PieChart as PieChartIcon
} from 'lucide-react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  CartesianGrid
} from 'recharts';
import { getStats } from '../services/api';

const COLORS = ['#10b981', '#3b82f6', '#f59e0b', '#ec4899', '#8b5cf6', '#06b6d4', '#64748b'];

export default function OverviewPage() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchStats();
  }, []);

  const fetchStats = async () => {
    try {
      setLoading(true);
      const data = await getStats();
      setStats(data);
    } catch (err) {
      console.error('Failed to load stats:', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="p-8 space-y-6 animate-pulse">
        <div className="h-8 bg-slate-800 rounded w-1/4"></div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="h-28 bg-slate-850 rounded-2xl border border-slate-800"></div>
          ))}
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="h-72 bg-slate-850 rounded-2xl border border-slate-800"></div>
          <div className="h-72 bg-slate-850 rounded-2xl border border-slate-800"></div>
        </div>
      </div>
    );
  }

  const kpis = stats?.kpis || {};
  const sectorDist = stats?.sector_distribution || [];
  const statusDist = stats?.status_distribution || [];
  const confDist = stats?.confidence_distribution || [];

  return (
    <div className="p-8 space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white tracking-tight">Lead Intelligence Overview</h1>
        <p className="text-sm text-slate-400 mt-1">
          Real-time metrics, RAG classification health, and duplicate consolidation telemetry.
        </p>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        {/* KPI 1: Total Emails */}
        <div className="p-5 rounded-2xl bg-slate-900 border border-slate-800 hover:border-slate-700 transition-all shadow-sm">
          <div className="flex items-center justify-between text-slate-400 mb-3">
            <span className="text-xs font-semibold uppercase tracking-wider">Total Emails</span>
            <div className="p-2 rounded-xl bg-blue-500/10 text-blue-400">
              <Mail className="w-4 h-4" />
            </div>
          </div>
          <p className="text-3xl font-bold text-white">{kpis.total_emails || 0}</p>
          <p className="text-[11px] text-slate-500 mt-2">Ingested from all channels</p>
        </div>

        {/* KPI 2: Total Companies */}
        <div className="p-5 rounded-2xl bg-slate-900 border border-slate-800 hover:border-slate-700 transition-all shadow-sm">
          <div className="flex items-center justify-between text-slate-400 mb-3">
            <span className="text-xs font-semibold uppercase tracking-wider">Unique Companies</span>
            <div className="p-2 rounded-xl bg-emerald-500/10 text-emerald-400">
              <Building2 className="w-4 h-4" />
            </div>
          </div>
          <p className="text-3xl font-bold text-white">{kpis.total_companies || 0}</p>
          <p className="text-[11px] text-slate-500 mt-2">Distinct normalized entities</p>
        </div>

        {/* KPI 3: Successfully Classified */}
        <div className="p-5 rounded-2xl bg-slate-900 border border-slate-800 hover:border-slate-700 transition-all shadow-sm">
          <div className="flex items-center justify-between text-slate-400 mb-3">
            <span className="text-xs font-semibold uppercase tracking-wider">Classified Leads</span>
            <div className="p-2 rounded-xl bg-emerald-500/10 text-emerald-400">
              <CheckCircle2 className="w-4 h-4" />
            </div>
          </div>
          <p className="text-3xl font-bold text-emerald-400">{kpis.classified_leads || 0}</p>
          <p className="text-[11px] text-slate-500 mt-2">Confidence ≥ 0.75 Gate</p>
        </div>

        {/* KPI 4: Needs Review */}
        <div className="p-5 rounded-2xl bg-slate-900 border border-slate-800 hover:border-slate-700 transition-all shadow-sm">
          <div className="flex items-center justify-between text-slate-400 mb-3">
            <span className="text-xs font-semibold uppercase tracking-wider">Needs Review</span>
            <div className="p-2 rounded-xl bg-amber-500/10 text-amber-400">
              <AlertCircle className="w-4 h-4" />
            </div>
          </div>
          <p className="text-3xl font-bold text-amber-400">{kpis.needs_review_leads || 0}</p>
          <p className="text-[11px] text-slate-500 mt-2">Routed to Human Review</p>
        </div>

        {/* KPI 5: Duplicates Detected */}
        <div className="p-5 rounded-2xl bg-slate-900 border border-slate-800 hover:border-slate-700 transition-all shadow-sm">
          <div className="flex items-center justify-between text-slate-400 mb-3">
            <span className="text-xs font-semibold uppercase tracking-wider">Duplicates Detected</span>
            <div className="p-2 rounded-xl bg-purple-500/10 text-purple-400">
              <Copy className="w-4 h-4" />
            </div>
          </div>
          <p className="text-3xl font-bold text-purple-400">{kpis.duplicates_detected || 0}</p>
          <p className="text-[11px] text-slate-500 mt-2">Consolidated via Rules 1, 2, 3</p>
        </div>
      </div>

      {/* Charts Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Sector-wise Lead Distribution */}
        <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-semibold text-white flex items-center gap-2">
              <BarChart3 className="w-4 h-4 text-emerald-400" />
              <span>Sector-wise Lead Distribution</span>
            </h2>
            <span className="text-xs text-slate-400">{sectorDist.length} active sectors</span>
          </div>

          <div className="h-72 w-full">
            {sectorDist.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={sectorDist} layout="vertical" margin={{ top: 5, right: 30, left: 80, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                  <XAxis type="number" stroke="#64748b" tick={{ fontSize: 11 }} />
                  <YAxis
                    type="category"
                    dataKey="sector"
                    stroke="#94a3b8"
                    tick={{ fontSize: 11 }}
                    width={100}
                  />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '0.75rem' }}
                    itemStyle={{ color: '#34d399' }}
                  />
                  <Bar dataKey="count" fill="#10b981" radius={[0, 6, 6, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-sm text-slate-500">
                No sector leads processed yet. Upload emails to populate.
              </div>
            )}
          </div>
        </div>

        {/* Classification Status Distribution */}
        <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-semibold text-white flex items-center gap-2">
              <PieChartIcon className="w-4 h-4 text-blue-400" />
              <span>Classification Status Distribution</span>
            </h2>
            <span className="text-xs text-slate-400">Decision Gate Telemetry</span>
          </div>

          <div className="h-72 w-full flex items-center justify-center">
            {statusDist.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={statusDist}
                    dataKey="count"
                    nameKey="status"
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={95}
                    paddingAngle={4}
                    label={({ name, percent }) => `${name} (${(percent * 100).toFixed(0)}%)`}
                  >
                    {statusDist.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '0.75rem' }}
                  />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="text-sm text-slate-500">No classification records.</div>
            )}
          </div>
        </div>

        {/* Confidence Score Distribution */}
        <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 space-y-4">
          <h2 className="text-base font-semibold text-white flex items-center gap-2">
            <TrendingUp className="w-4 h-4 text-purple-400" />
            <span>Confidence Score Distribution</span>
          </h2>
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={confDist} margin={{ top: 10, right: 20, left: 0, bottom: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="range" stroke="#94a3b8" tick={{ fontSize: 11 }} />
                <YAxis stroke="#64748b" tick={{ fontSize: 11 }} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '0.75rem' }}
                />
                <Bar dataKey="count" fill="#8b5cf6" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Duplicate Breakdown & Audit */}
        <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 space-y-4">
          <h2 className="text-base font-semibold text-white flex items-center gap-2">
            <Copy className="w-4 h-4 text-emerald-400" />
            <span>Duplicate Rule Breakdown</span>
          </h2>
          <div className="space-y-3 pt-2">
            {stats?.duplicate_stats && stats.duplicate_stats.length > 0 ? (
              stats.duplicate_stats.map((d, i) => (
                <div
                  key={i}
                  className="p-3.5 rounded-xl bg-slate-850/60 border border-slate-800 flex items-center justify-between"
                >
                  <span className="text-xs font-mono text-slate-300">{d.rule}</span>
                  <span className="text-sm font-bold text-white bg-slate-800 px-3 py-1 rounded-lg">
                    {d.count} matches
                  </span>
                </div>
              ))
            ) : (
              <div className="text-sm text-slate-500 py-8 text-center">
                No duplicate records logged yet.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
