import React, { useState, useRef, useEffect } from 'react';
import {
  UploadCloud,
  FileText,
  CheckCircle,
  AlertCircle,
  Clock,
  Sparkles,
  ArrowRight,
  Send,
  Code
} from 'lucide-react';
import { uploadFiles, ingestEmailJson, getBatch, getBatches } from '../services/api';

export default function UploadPage() {
  const [activeTab, setActiveTab] = useState('files'); // 'files' or 'json'
  const [dragOver, setDragOver] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [activeBatch, setActiveBatch] = useState(null);
  const [recentBatches, setRecentBatches] = useState([]);
  const fileInputRef = useRef(null);

  // Quick JSON state
  const [jsonSenderName, setJsonSenderName] = useState('Satya Nadella');
  const [jsonSenderEmail, setJsonSenderEmail] = useState('satya@microsoft.com');
  const [jsonSubject, setJsonSubject] = useState('Azure Cloud & Enterprise SaaS Integration');
  const [jsonBody, setJsonBody] = useState(
    'We provide enterprise cloud hosting, machine learning models, and scalable database software.'
  );
  const [jsonSignature, setJsonSignature] = useState(
    'Satya Nadella\nCEO, Microsoft Corporation\nPhone: +1 425-882-8080\nhttps://microsoft.com'
  );
  const [jsonSubmitting, setJsonSubmitting] = useState(false);
  const [jsonResult, setJsonResult] = useState(null);

  useEffect(() => {
    loadBatches();
  }, []);

  // Poll active batch if status is pending or processing
  useEffect(() => {
    if (!activeBatch || ['completed', 'completed_with_errors', 'failed'].includes(activeBatch.status)) {
      return;
    }

    const interval = setInterval(async () => {
      try {
        const updated = await getBatch(activeBatch.id);
        setActiveBatch(updated);
        if (['completed', 'completed_with_errors', 'failed'].includes(updated.status)) {
          loadBatches();
        }
      } catch (err) {
        console.error('Batch polling error:', err);
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [activeBatch]);

  const loadBatches = async () => {
    try {
      const res = await getBatches({ limit: 8 });
      setRecentBatches(res.items || []);
    } catch (err) {
      console.error('Failed to load batch history:', err);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      setSelectedFiles(Array.from(e.dataTransfer.files));
    }
  };

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      setSelectedFiles(Array.from(e.target.files));
    }
  };

  const handleUploadSubmit = async () => {
    if (selectedFiles.length === 0) return;

    try {
      setUploading(true);
      setUploadProgress(0);
      const formData = new FormData();
      selectedFiles.forEach((file) => {
        formData.append('files', file);
      });

      const res = await uploadFiles(formData, (progress) => {
        setUploadProgress(progress);
      });

      setActiveBatch({
        id: res.batch_id,
        filename: selectedFiles.length === 1 ? selectedFiles[0].name : `${selectedFiles.length} files`,
        status: 'pending',
        processed_count: 0,
        failed_count: 0,
        total_emails: selectedFiles.length,
      });

      setSelectedFiles([]);
      loadBatches();
    } catch (err) {
      console.error('Upload failed:', err);
      alert('Upload failed: ' + (err.response?.data?.detail || err.message));
    } finally {
      setUploading(false);
    }
  };

  const handleJsonSubmit = async (e) => {
    e.preventDefault();
    try {
      setJsonSubmitting(true);
      setJsonResult(null);
      const payload = {
        sender_name: jsonSenderName,
        sender_email: jsonSenderEmail,
        subject: jsonSubject,
        body: jsonBody,
        signature: jsonSignature,
      };
      const res = await ingestEmailJson(payload);
      setJsonResult(res);
      loadBatches();
    } catch (err) {
      alert('JSON Ingestion error: ' + (err.response?.data?.detail || err.message));
    } finally {
      setJsonSubmitting(false);
    }
  };

  return (
    <div className="p-8 space-y-8 max-w-6xl mx-auto">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white tracking-tight">Email Ingestion Center</h1>
        <p className="text-sm text-slate-400 mt-1">
          Upload business emails via raw files (.eml, .msg, .mbox, .csv, .json) or authorized JSON API payload.
        </p>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-2 border-b border-slate-800 pb-2">
        <button
          onClick={() => setActiveTab('files')}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-all ${
            activeTab === 'files'
              ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
              : 'text-slate-400 hover:text-white'
          }`}
        >
          <UploadCloud className="w-4 h-4" />
          <span>File Batch Upload</span>
        </button>
        <button
          onClick={() => setActiveTab('json')}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-all ${
            activeTab === 'json'
              ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
              : 'text-slate-400 hover:text-white'
          }`}
        >
          <Code className="w-4 h-4" />
          <span>Direct JSON API Ingest</span>
        </button>
      </div>

      {activeTab === 'files' ? (
        <div className="space-y-6">
          {/* Drag & Drop Zone */}
          <div
            onDragOver={(e) => {
              e.preventDefault();
              setDragOver(true);
            }}
            onDragLeave={() => setDragOver(false)}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            className={`border-2 border-dashed rounded-3xl p-12 text-center cursor-pointer transition-all ${
              dragOver
                ? 'border-emerald-500 bg-emerald-500/10'
                : 'border-slate-800 bg-slate-900/60 hover:border-slate-700 hover:bg-slate-900'
            }`}
          >
            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept=".eml,.msg,.mbox,.csv,.json"
              onChange={handleFileChange}
              className="hidden"
            />
            <div className="w-14 h-14 rounded-2xl bg-emerald-500/10 text-emerald-400 flex items-center justify-center mx-auto mb-4 border border-emerald-500/20">
              <UploadCloud className="w-7 h-7" />
            </div>
            <h3 className="text-base font-semibold text-white">Click or drag & drop email files here</h3>
            <p className="text-xs text-slate-400 mt-1">
              Supports <strong className="text-slate-300">.eml, .msg, .mbox, .csv, and .json</strong> (Max 25 MB per file)
            </p>

            <div className="flex items-center justify-center gap-2 mt-4 text-[11px] text-slate-500 font-mono">
              <span className="px-2 py-0.5 rounded bg-slate-800 border border-slate-700">MIME / RFC822</span>
              <span className="px-2 py-0.5 rounded bg-slate-800 border border-slate-700">Outlook .MSG</span>
              <span className="px-2 py-0.5 rounded bg-slate-800 border border-slate-700">Standard MBOX</span>
              <span className="px-2 py-0.5 rounded bg-slate-800 border border-slate-700">Tabular CSV</span>
            </div>
          </div>

          {/* Selected Files List & Submit */}
          {selectedFiles.length > 0 && (
            <div className="p-5 rounded-2xl bg-slate-900 border border-slate-800 space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-sm font-semibold text-white">
                  Selected Files ({selectedFiles.length})
                </span>
                <button
                  onClick={() => setSelectedFiles([])}
                  className="text-xs text-slate-400 hover:text-red-400 transition-colors"
                >
                  Clear Selection
                </button>
              </div>

              <div className="max-h-48 overflow-y-auto space-y-2">
                {selectedFiles.map((file, idx) => (
                  <div
                    key={idx}
                    className="flex items-center justify-between p-3 rounded-xl bg-slate-850/80 border border-slate-800 text-xs"
                  >
                    <div className="flex items-center gap-2 text-slate-200">
                      <FileText className="w-4 h-4 text-emerald-400" />
                      <span className="font-mono">{file.name}</span>
                    </div>
                    <span className="text-slate-500">{(file.size / 1024).toFixed(1)} KB</span>
                  </div>
                ))}
              </div>

              <div className="flex items-center justify-between pt-2 border-t border-slate-800">
                <span className="text-xs text-slate-400">Ready to dispatch background pipeline</span>
                <button
                  disabled={uploading}
                  onClick={handleUploadSubmit}
                  className="px-6 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-sm transition-all disabled:opacity-50 flex items-center gap-2 shadow-lg shadow-emerald-600/20"
                >
                  {uploading ? 'Uploading...' : 'Process Batch Now'}
                  <ArrowRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}

          {/* Active Batch Live Progress Card */}
          {activeBatch && (
            <div className="p-6 rounded-2xl bg-gradient-to-br from-slate-900 to-slate-850 border border-emerald-500/30 space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <div className="flex items-center gap-2">
                    <Sparkles className="w-4 h-4 text-emerald-400 animate-spin" />
                    <h3 className="text-sm font-bold text-white">Live Batch Processing</h3>
                  </div>
                  <p className="text-xs text-slate-400 font-mono mt-0.5">ID: {activeBatch.id}</p>
                </div>
                <span
                  className={`text-xs px-2.5 py-1 rounded-full font-medium ${
                    activeBatch.status === 'completed'
                      ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                      : 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                  }`}
                >
                  {activeBatch.status.toUpperCase()}
                </span>
              </div>

              <div className="grid grid-cols-3 gap-3 text-center">
                <div className="p-3 rounded-xl bg-slate-900/80 border border-slate-800">
                  <p className="text-[11px] text-slate-400">Total Emails</p>
                  <p className="text-lg font-bold text-white">{activeBatch.total_emails || 'Detecting...'}</p>
                </div>
                <div className="p-3 rounded-xl bg-slate-900/80 border border-slate-800">
                  <p className="text-[11px] text-slate-400">Processed</p>
                  <p className="text-lg font-bold text-emerald-400">{activeBatch.processed_count}</p>
                </div>
                <div className="p-3 rounded-xl bg-slate-900/80 border border-slate-800">
                  <p className="text-[11px] text-slate-400">Failed / Skipped</p>
                  <p className="text-lg font-bold text-red-400">{activeBatch.failed_count}</p>
                </div>
              </div>
            </div>
          )}
        </div>
      ) : (
        /* Direct JSON Ingestion Form */
        <form onSubmit={handleJsonSubmit} className="p-6 rounded-2xl bg-slate-900 border border-slate-800 space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="text-xs font-semibold text-slate-300 block mb-1">Sender Name</label>
              <input
                type="text"
                value={jsonSenderName}
                onChange={(e) => setJsonSenderName(e.target.value)}
                className="w-full px-3.5 py-2 rounded-xl bg-slate-800 border border-slate-700 text-white text-xs focus:outline-none focus:border-emerald-500"
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-slate-300 block mb-1">Sender Email</label>
              <input
                type="email"
                required
                value={jsonSenderEmail}
                onChange={(e) => setJsonSenderEmail(e.target.value)}
                className="w-full px-3.5 py-2 rounded-xl bg-slate-800 border border-slate-700 text-white text-xs focus:outline-none focus:border-emerald-500"
              />
            </div>
          </div>

          <div>
            <label className="text-xs font-semibold text-slate-300 block mb-1">Subject</label>
            <input
              type="text"
              value={jsonSubject}
              onChange={(e) => setJsonSubject(e.target.value)}
              className="w-full px-3.5 py-2 rounded-xl bg-slate-800 border border-slate-700 text-white text-xs focus:outline-none focus:border-emerald-500"
            />
          </div>

          <div>
            <label className="text-xs font-semibold text-slate-300 block mb-1">Email Body</label>
            <textarea
              rows={4}
              required
              value={jsonBody}
              onChange={(e) => setJsonBody(e.target.value)}
              className="w-full px-3.5 py-2 rounded-xl bg-slate-800 border border-slate-700 text-white text-xs focus:outline-none focus:border-emerald-500 leading-relaxed font-mono"
            />
          </div>

          <div>
            <label className="text-xs font-semibold text-slate-300 block mb-1">Signature Block</label>
            <textarea
              rows={3}
              value={jsonSignature}
              onChange={(e) => setJsonSignature(e.target.value)}
              className="w-full px-3.5 py-2 rounded-xl bg-slate-800 border border-slate-700 text-white text-xs focus:outline-none focus:border-emerald-500 leading-relaxed font-mono"
            />
          </div>

          <div className="flex justify-end pt-2">
            <button
              type="submit"
              disabled={jsonSubmitting}
              className="px-6 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-sm transition-all flex items-center gap-2"
            >
              <Send className="w-4 h-4" />
              <span>{jsonSubmitting ? 'Processing...' : 'Send API Ingest Request'}</span>
            </button>
          </div>

          {jsonResult && (
            <div className="mt-4 p-4 rounded-xl bg-slate-850 border border-emerald-500/30 text-xs space-y-1">
              <p className="font-bold text-emerald-400">Ingestion Successful!</p>
              <p className="text-slate-300 font-mono">Batch ID: {jsonResult.batch_id}</p>
              {jsonResult.results?.[0] && (
                <p className="text-slate-400">
                  Assigned Sector: <strong className="text-white">{jsonResult.results[0].sector}</strong> (Confidence: {(jsonResult.results[0].confidence * 100).toFixed(1)}%)
                </p>
              )}
            </div>
          )}
        </form>
      )}

      {/* Recent Batches History Mini Table */}
      <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 space-y-4">
        <h3 className="text-sm font-semibold text-white">Recent Upload Batches</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-300">
            <thead className="bg-slate-850/80 uppercase text-[10px] text-slate-400 border-b border-slate-800">
              <tr>
                <th className="py-2.5 px-3">Batch ID</th>
                <th className="py-2.5 px-3">File / Source</th>
                <th className="py-2.5 px-3">Total</th>
                <th className="py-2.5 px-3">Processed</th>
                <th className="py-2.5 px-3">Status</th>
                <th className="py-2.5 px-3">Date</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-mono">
              {recentBatches.map((b) => (
                <tr key={b.id} className="hover:bg-slate-850/40">
                  <td className="py-2.5 px-3 text-emerald-400">{b.id.substring(0, 8)}...</td>
                  <td className="py-2.5 px-3 font-sans text-slate-200">{b.filename}</td>
                  <td className="py-2.5 px-3">{b.total_emails}</td>
                  <td className="py-2.5 px-3 text-emerald-400">{b.processed_count}</td>
                  <td className="py-2.5 px-3">
                    <span className="px-2 py-0.5 rounded-full text-[10px] bg-slate-800 text-slate-300 border border-slate-700">
                      {b.status}
                    </span>
                  </td>
                  <td className="py-2.5 px-3 text-slate-500 font-sans">
                    {b.created_at ? new Date(b.created_at).toLocaleTimeString() : 'N/A'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
