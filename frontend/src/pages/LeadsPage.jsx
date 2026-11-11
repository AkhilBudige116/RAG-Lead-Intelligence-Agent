import React, { useState, useEffect } from 'react';
import {
  Search,
  Filter,
  Download,
  Building2,
  Mail,
  ChevronLeft,
  ChevronRight,
  ExternalLink,
  FileSpreadsheet,
  FileText
} from 'lucide-react';
import { getLeads, getLead, getSectors, getExportUrl } from '../services/api';
import LeadDetailDrawer from '../components/LeadDetailDrawer';

export default function LeadsPage() {
  const [leads, setLeads] = useState([]);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(15);
  const [loading, setLoading] = useState(true);

  // Filters
  const [search, setSearch] = useState('');
  const [sectorFilter, setSectorFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');
  const [confidenceMin, setConfidenceMin] = useState('');
  const [sectors, setSectors] = useState([]);

  // Detail Drawer state
  const [selectedLeadId, setSelectedLeadId] = useState(null);
  const [selectedLeadDetail, setSelectedLeadDetail] = useState(null);

  useEffect(() => {
    loadSectors();
  }, []);

  useEffect(() => {
    fetchLeads();
  }, [page, pageSize, sectorFilter, statusFilter, confidenceMin]);

  const loadSectors = async () => {
    try {
      const data = await getSectors();
      setSectors(data);
    } catch (err) {
      console.error('Failed to load sectors:', err);
    }
  };

  const fetchLeads = async () => {
    try {
      setLoading(true);
      const params = {
        page,
        page_size: pageSize,
        search: search || undefined,
        sector: sectorFilter !== 'all' ? sectorFilter : undefined,
        status: statusFilter !== 'all' ? statusFilter : undefined,
        min_confidence: confidenceMin ? parseFloat(confidenceMin) : undefined,
      };
      const res = await getLeads(params);
      setLeads(res.items || []);
      setTotal(res.total || 0);
      setTotalPages(res.total_pages || 1);
    } catch (err) {
      console.error('Failed to load leads:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    setPage(1);
    fetchLeads();
  };

  const openLeadDetail = async (id) => {
    try {
      setSelectedLeadId(id);
      const detail = await getLead(id);
      setSelectedLeadDetail(detail);
    } catch (err) {
      console.error('Failed to load lead details:', err);
    }
  };

  const closeDrawer = () => {
    setSelectedLeadId(null);
    setSelectedLeadDetail(null);
  };

  const currentFilters = {
    search: search || undefined,
    sector: sectorFilter !== 'all' ? sectorFilter : undefined,
    status: statusFilter !== 'all' ? statusFilter : undefined,
    min_confidence: confidenceMin || undefined,
  };

  return (
    <div className="p-8 space-y-6">
      {/* Header & Export Actions */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Lead Intelligence Directory</h1>
          <p className="text-sm text-slate-400 mt-1">
            Browse, filter, and inspect AI-classified business leads and company contacts.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <a
            href={getExportUrl('csv', currentFilters)}
            download="leads_export.csv"
            className="px-3.5 py-2 rounded-xl bg-slate-850 hover:bg-slate-800 border border-slate-700 text-xs font-semibold text-slate-200 flex items-center gap-2 transition-colors"
          >
            <Download className="w-3.5 h-3.5 text-emerald-400" />
            <span>Export CSV</span>
          </a>
          <a
            href={getExportUrl('xlsx', currentFilters)}
            download="leads_export.xlsx"
            className="px-3.5 py-2 rounded-xl bg-slate-850 hover:bg-slate-800 border border-slate-700 text-xs font-semibold text-slate-200 flex items-center gap-2 transition-colors"
          >
            <FileSpreadsheet className="w-3.5 h-3.5 text-blue-400" />
            <span>Export Excel</span>
          </a>
        </div>
      </div>

      {/* Filter Toolbar */}
      <div className="p-4 rounded-2xl bg-slate-900 border border-slate-800 flex flex-wrap items-center justify-between gap-3">
        <form onSubmit={handleSearchSubmit} className="flex items-center gap-2 flex-1 min-w-[240px]">
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-slate-500 absolute left-3.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search companies, domains, contacts, or emails..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-9 pr-3.5 py-2 rounded-xl bg-slate-800 border border-slate-700 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500"
            />
          </div>
          <button
            type="submit"
            className="px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold transition-colors"
          >
            Search
          </button>
        </form>

        <div className="flex items-center gap-2 flex-wrap text-xs">
          {/* Sector Filter */}
          <select
            value={sectorFilter}
            onChange={(e) => {
              setSectorFilter(e.target.value);
              setPage(1);
            }}
            className="px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-slate-200 focus:outline-none"
          >
            <option value="all">All Sectors</option>
            {sectors.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>

          {/* Status Filter */}
          <select
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value);
              setPage(1);
            }}
            className="px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-slate-200 focus:outline-none"
          >
            <option value="all">All Statuses</option>
            <option value="classified">Classified</option>
            <option value="needs_review">Needs Review</option>
          </select>

          {/* Min Confidence */}
          <select
            value={confidenceMin}
            onChange={(e) => {
              setConfidenceMin(e.target.value);
              setPage(1);
            }}
            className="px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-slate-200 focus:outline-none"
          >
            <option value="">Any Confidence</option>
            <option value="0.75">≥ 75% Confidence</option>
            <option value="0.85">≥ 85% Confidence</option>
            <option value="0.90">≥ 90% Confidence</option>
          </select>
        </div>
      </div>

      {/* Leads Table */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900 overflow-hidden shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-300">
            <thead className="bg-slate-850 uppercase text-[10px] font-semibold text-slate-400 border-b border-slate-800">
              <tr>
                <th className="py-3 px-4">Company</th>
                <th className="py-3 px-4">Primary Contact</th>
                <th className="py-3 px-4">Email</th>
                <th className="py-3 px-4">Industry Sector</th>
                <th className="py-3 px-4 text-center">Confidence</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/80">
              {loading ? (
                <tr>
                  <td colSpan="7" className="py-12 text-center text-slate-500">
                    Loading lead records...
                  </td>
                </tr>
              ) : leads.length === 0 ? (
                <tr>
                  <td colSpan="7" className="py-12 text-center text-slate-500">
                    No matching leads found.
                  </td>
                </tr>
              ) : (
                leads.map((lead) => {
                  const conf = lead.confidence || 0.0;
                  const isClassified = lead.status === 'classified';
                  return (
                    <tr
                      key={lead.id}
                      onClick={() => openLeadDetail(lead.id)}
                      className="hover:bg-slate-850/60 cursor-pointer transition-colors"
                    >
                      <td className="py-3 px-4 font-semibold text-white flex items-center gap-2">
                        <Building2 className="w-3.5 h-3.5 text-slate-500 shrink-0" />
                        <span className="truncate max-w-[180px]">{lead.company_name}</span>
                      </td>
                      <td className="py-3 px-4 text-slate-300 truncate max-w-[140px]">{lead.contact_name}</td>
                      <td className="py-3 px-4 text-slate-400 font-mono truncate max-w-[180px]">{lead.email}</td>
                      <td className="py-3 px-4">
                        <span className="px-2.5 py-1 rounded-lg bg-slate-800 text-slate-200 border border-slate-700/60">
                          {lead.sector_name}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-center font-bold">
                        <span
                          className={
                            conf >= 0.75
                              ? 'text-emerald-400'
                              : conf >= 0.5
                              ? 'text-amber-400'
                              : 'text-red-400'
                          }
                        >
                          {(conf * 100).toFixed(1)}%
                        </span>
                      </td>
                      <td className="py-3 px-4">
                        <span
                          className={`px-2.5 py-0.5 rounded-full text-[11px] font-medium ${
                            isClassified
                              ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30'
                              : 'bg-amber-500/15 text-amber-400 border border-amber-500/30'
                          }`}
                        >
                          {isClassified ? 'Classified' : 'Needs Review'}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-right">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            openLeadDetail(lead.id);
                          }}
                          className="p-1.5 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-emerald-400 transition-colors"
                          title="View Details"
                        >
                          <ExternalLink className="w-4 h-4" />
                        </button>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination Bar */}
        <div className="p-4 border-t border-slate-800 flex items-center justify-between text-xs text-slate-400">
          <span>
            Showing page <strong className="text-white">{page}</strong> of <strong className="text-white">{totalPages}</strong> ({total} total leads)
          </span>
          <div className="flex items-center gap-2">
            <button
              disabled={page <= 1}
              onClick={() => setPage(page - 1)}
              className="p-2 rounded-xl bg-slate-800 hover:bg-slate-700 disabled:opacity-40 transition-colors"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <button
              disabled={page >= totalPages}
              onClick={() => setPage(page + 1)}
              className="p-2 rounded-xl bg-slate-800 hover:bg-slate-700 disabled:opacity-40 transition-colors"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Slide-over Detail Drawer */}
      {selectedLeadDetail && (
        <LeadDetailDrawer
          lead={selectedLeadDetail}
          onClose={closeDrawer}
          onSectorUpdated={() => {
            fetchLeads();
            closeDrawer();
          }}
        />
      )}
    </div>
  );
}
