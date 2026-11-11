import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  UploadCloud,
  Users,
  CheckSquare,
  CopyCheck,
  Layers,
  History,
  FileSpreadsheet
} from 'lucide-react';

const NAV_ITEMS = [
  { to: '/', label: 'Overview', icon: LayoutDashboard },
  { to: '/upload', label: 'Email Upload', icon: UploadCloud },
  { to: '/leads', label: 'Lead Management', icon: Users },
  { to: '/review', label: 'Review Queue', icon: CheckSquare, badgeKey: 'review' },
  { to: '/duplicates', label: 'Duplicate Review', icon: CopyCheck },
  { to: '/sectors', label: 'Sector Knowledge', icon: Layers },
  { to: '/batches', label: 'Batch History', icon: History },
];

export default function Sidebar({ pendingReviewCount = 0 }) {
  return (
    <aside className="w-64 border-r border-slate-800 bg-slate-900/60 flex flex-col justify-between py-6 select-none shrink-0">
      <div>
        <div className="px-6 mb-6">
          <p className="text-[11px] font-semibold tracking-wider uppercase text-slate-400">Navigation</p>
        </div>
        <nav className="space-y-1.5 px-3">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  `flex items-center justify-between px-3.5 py-2.5 rounded-xl text-sm font-medium transition-all ${
                    isActive
                      ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 shadow-sm'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
                  }`
                }
              >
                <div className="flex items-center gap-3">
                  <Icon className="w-4 h-4" />
                  <span>{item.label}</span>
                </div>
                {item.badgeKey === 'review' && pendingReviewCount > 0 && (
                  <span className="bg-amber-500/20 text-amber-400 border border-amber-500/30 text-[11px] font-bold px-2 py-0.5 rounded-full">
                    {pendingReviewCount}
                  </span>
                )}
              </NavLink>
            );
          })}
        </nav>
      </div>

      <div className="px-6">
        <div className="p-3.5 rounded-xl bg-slate-850/80 border border-slate-800 text-xs text-slate-400">
          <p className="font-semibold text-slate-300 mb-1">Company Assessment Mode</p>
          <p className="text-[11px] leading-relaxed">
            All 13 standard industry sectors loaded with dual-factor RAG classification.
          </p>
        </div>
      </div>
    </aside>
  );
}
