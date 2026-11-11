import React from 'react';
import {
  X,
  Building2,
  Mail,
  Phone,
  Globe,
  Tag,
  ShieldCheck,
  CheckCircle,
  AlertTriangle,
  FileText,
  Clock,
  Sparkles,
  Search
} from 'lucide-react';

export default function LeadDetailDrawer({ lead, onClose, onSectorUpdated }) {
  if (!lead) return null;

  const latestCls = lead.latest_classification;
  const confidence = lead.confidence || 0.0;
  const isClassified = lead.status === 'classified';

  // Dual-factor values
  const llmConf = latestCls?.llm_confidence ?? (confidence > 0 ? (confidence / 0.6) : 0.0);
  const simScore = latestCls?.top_retrieval_similarity ?? 0.85;

  return (
    <div className="fixed inset-0 z-50 overflow-hidden bg-black/60 backdrop-blur-sm flex justify-end transition-opacity">
      <div className="w-full max-w-2xl bg-slate-900 border-l border-slate-800 h-full overflow-y-auto shadow-2xl flex flex-col">
        {/* Header */}
        <div className="p-6 border-b border-slate-800 flex items-center justify-between sticky top-0 bg-slate-900/95 backdrop-blur z-10">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-slate-800 border border-slate-700 flex items-center justify-center">
              <Building2 className="w-5 h-5 text-emerald-400" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-white">{lead.name || 'Unidentified Company'}</h2>
              <div className="flex items-center gap-2 mt-0.5">
                <span className="text-xs text-slate-400">{lead.domain || 'No domain'}</span>
                <span className="text-slate-600">•</span>
                <span
                  className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                    isClassified
                      ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                      : 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                  }`}
                >
                  {isClassified ? 'Classified' : 'Needs Review'}
                </span>
              </div>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content Body */}
        <div className="p-6 space-y-6 flex-1">
          {/* Classification & Confidence Gate Card */}
          <div className="p-5 rounded-2xl bg-slate-850/90 border border-slate-800 space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-sm font-semibold text-slate-200">
                <Sparkles className="w-4 h-4 text-emerald-400" />
                <span>Sector Classification & Gate Breakdown</span>
              </div>
              <span className="text-xs text-slate-400 font-mono">
                Model: {latestCls?.model_version || 'bge-small + claude'}
              </span>
            </div>

            <div className="grid grid-cols-3 gap-3 text-center">
              <div className="p-3 rounded-xl bg-slate-900 border border-slate-800">
                <p className="text-[11px] text-slate-400 mb-1">Assigned Sector</p>
                <p className="text-sm font-bold text-emerald-400 truncate">{lead.sector_name || 'Unassigned'}</p>
              </div>
              <div className="p-3 rounded-xl bg-slate-900 border border-slate-800">
                <p className="text-[11px] text-slate-400 mb-1">Final Confidence</p>
                <p className="text-sm font-bold text-white">{(confidence * 100).toFixed(1)}%</p>
              </div>
              <div className="p-3 rounded-xl bg-slate-900 border border-slate-800">
                <p className="text-[11px] text-slate-400 mb-1">Top Vector Sim</p>
                <p className="text-sm font-bold text-blue-400">
                  {latestCls?.top_retrieval_similarity ? (latestCls.top_retrieval_similarity * 100).toFixed(1) + '%' : 'N/A'}
                </p>
              </div>
            </div>

            {/* Formula visualization */}
            <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800/80 text-xs text-slate-300 space-y-1.5 font-mono">
              <div className="flex justify-between text-slate-400 text-[11px]">
                <span>CONFIDENCE FORMULA:</span>
                <span>(0.6 × LLM) + (0.4 × RAG_Sim)</span>
              </div>
              <div className="flex items-center justify-between text-slate-200">
                <span>Calculated Score:</span>
                <span className="font-bold text-emerald-400">
                  {`0.6 × ${(latestCls?.llm_confidence ?? 0.85).toFixed(2)} + 0.4 × ${(latestCls?.top_retrieval_similarity ?? 0.85).toFixed(2)} = ${confidence.toFixed(2)}`}
                </span>
              </div>
            </div>

            {/* Classification Reason */}
            <div>
              <p className="text-xs font-semibold text-slate-400 mb-1">Decision Reason</p>
              <p className="text-xs text-slate-300 leading-relaxed bg-slate-900 p-3 rounded-xl border border-slate-800">
                {lead.classification_reason || 'No reasoning available.'}
              </p>
            </div>

            {/* Evidence Chips */}
            {latestCls?.evidence && latestCls.evidence.length > 0 && (
              <div>
                <p className="text-xs font-semibold text-slate-400 mb-2">Supporting Business Evidence</p>
                <div className="flex flex-wrap gap-1.5">
                  {latestCls.evidence.map((ev, i) => (
                    <span
                      key={i}
                      className="text-xs px-2.5 py-1 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-300"
                    >
                      "{ev}"
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Contact Directory */}
          <div className="space-y-3">
            <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
              <Mail className="w-4 h-4 text-blue-400" />
              <span>Associated Contacts ({lead.contacts?.length || 0})</span>
            </h3>
            <div className="space-y-2">
              {lead.contacts?.map((contact) => (
                <div
                  key={contact.id}
                  className="p-3.5 rounded-xl bg-slate-850/60 border border-slate-800 flex items-center justify-between"
                >
                  <div>
                    <p className="text-sm font-medium text-white">{contact.name || 'Unnamed Contact'}</p>
                    <p className="text-xs text-slate-400">{contact.title || 'No Job Title'}</p>
                    <div className="flex items-center gap-4 mt-2 text-xs text-slate-400">
                      <span className="flex items-center gap-1">
                        <Mail className="w-3.5 h-3.5 text-slate-500" />
                        {contact.email}
                      </span>
                      {contact.phone && (
                        <span className="flex items-center gap-1">
                          <Phone className="w-3.5 h-3.5 text-slate-500" />
                          {contact.phone}
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="text-right">
                    <span className="text-[11px] px-2 py-0.5 rounded-md bg-slate-800 text-slate-300 font-mono">
                      {contact.email_count} email{contact.email_count > 1 ? 's' : ''}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Related Ingested Emails */}
          <div className="space-y-3">
            <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
              <FileText className="w-4 h-4 text-purple-400" />
              <span>Ingested Email Messages ({lead.emails?.length || 0})</span>
            </h3>
            <div className="space-y-3">
              {lead.emails?.map((email) => (
                <div key={email.id} className="p-4 rounded-xl bg-slate-850/60 border border-slate-800 space-y-2">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-semibold text-slate-300">{email.subject || '(No Subject)'}</span>
                    <span className="text-slate-500 flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      {email.received_at ? new Date(email.received_at).toLocaleDateString() : 'Recent'}
                    </span>
                  </div>
                  <p className="text-xs text-slate-400 line-clamp-3 leading-relaxed whitespace-pre-wrap">
                    {email.body || '(No body text)'}
                  </p>
                  {email.signature && (
                    <div className="text-[11px] text-slate-400 border-t border-slate-800/80 pt-2 font-mono whitespace-pre-wrap">
                      <span className="text-slate-500 block mb-0.5">Signature block:</span>
                      {email.signature}
                    </div>
                  )}
                  <div className="flex items-center justify-between pt-1 text-[11px] text-slate-500">
                    <span>Source: {email.source_file || 'API Ingest'}</span>
                    <span>Hash: {email.raw_hash?.substring(0, 10)}...</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-slate-800 bg-slate-900/95 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-xl text-sm font-medium bg-slate-800 hover:bg-slate-700 text-slate-200 transition-colors"
          >
            Close Drawer
          </button>
        </div>
      </div>
    </div>
  );
}
