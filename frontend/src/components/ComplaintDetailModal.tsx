import React, { useEffect, useState } from 'react';
import {
  CheckCircle2,
  FileText,
  Loader2,
  Sparkles,
  X,
} from 'lucide-react';
import { api } from '../api/client';
import type { Complaint } from '../api/types';
import { formatDate, formatDateTime, getSeverityBadgeColor, getStatusBadgeColor } from '../utils/formatters';

interface ComplaintDetailModalProps {
  complaint: Complaint | null;
  onClose: () => void;
  onUpdate: () => void;
}

export const ComplaintDetailModal: React.FC<ComplaintDetailModalProps> = ({
  complaint,
  onClose,
  onUpdate,
}) => {
  const [current, setCurrent] = useState<Complaint | null>(complaint);
  const [isRunningAi, setIsRunningAi] = useState(false);
  const [isUpdatingStatus, setIsUpdatingStatus] = useState(false);
  const [aiMessage, setAiMessage] = useState<string | null>(null);

  useEffect(() => {
    setCurrent(complaint);
    setAiMessage(null);
  }, [complaint]);

  if (!current) return null;

  const sevStyle = getSeverityBadgeColor(current.severity);
  const statStyle = getStatusBadgeColor(current.status);

  const handleRunAiInsights = async () => {
    try {
      setIsRunningAi(true);
      setAiMessage(null);
      const updated = await api.generateAiInsights(current.id);
      setCurrent(updated);
      setAiMessage('AI Insights successfully generated and synchronized with database.');
      onUpdate();
    } catch (err: any) {
      setAiMessage(err.message || 'Failed to generate AI insights.');
    } finally {
      setIsRunningAi(false);
    }
  };

  const handleStatusChange = async (newStatus: string) => {
    try {
      setIsUpdatingStatus(true);
      const updated = await api.updateComplaint(current.id, { status: newStatus });
      setCurrent(updated);
      onUpdate();
    } catch (err) {
      console.error('Failed to update status', err);
    } finally {
      setIsUpdatingStatus(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-xs animate-fade-in">
      <div className="bg-white rounded-2xl border border-slate-200 shadow-2xl max-w-3xl w-full overflow-hidden flex flex-col max-h-[92vh]">
        {/* Header */}
        <div className="px-6 sm:px-8 py-5 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
          <div className="flex items-center space-x-3">
            <span className="font-mono font-bold text-lg text-blue-700">
              {current.complaintNumber}
            </span>
            <span
              className={`inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-md text-xs font-semibold border ${sevStyle.bg} ${sevStyle.text} ${sevStyle.border}`}
            >
              <span className={`w-1.5 h-1.5 rounded-full ${sevStyle.dot}`} />
              <span>{current.severity || 'Unassessed'}</span>
            </span>
            <span
              className={`inline-flex items-center px-2 py-0.5 rounded-md text-xs font-semibold border ${statStyle.bg} ${statStyle.text} ${statStyle.border}`}
            >
              {current.status}
            </span>
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* AI Action Notification */}
        {aiMessage && (
          <div className="mx-6 sm:mx-8 mt-4 p-3 rounded-xl bg-blue-50 border border-blue-200 text-blue-900 text-xs flex items-center justify-between">
            <span>{aiMessage}</span>
            <button
              onClick={() => setAiMessage(null)}
              className="text-blue-700 font-bold hover:underline"
            >
              Dismiss
            </button>
          </div>
        )}

        {/* Content Body */}
        <div className="p-6 sm:p-8 space-y-6 flex-1 overflow-y-auto text-xs">
          {/* Top Info Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 p-4 rounded-xl bg-slate-50/80 border border-slate-200/70">
            <div>
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
                Product Name
              </span>
              <span className="font-bold text-slate-900 text-sm">{current.productName}</span>
            </div>

            <div>
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
                Batch / Lot Number
              </span>
              <span className="font-mono font-bold text-slate-800 text-sm">
                {current.batchNumber}
              </span>
            </div>

            <div>
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
                Customer Name
              </span>
              <span className="font-semibold text-slate-800">{current.complainantName}</span>
            </div>

            <div>
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
                Complaint Type
              </span>
              <span className="font-medium text-slate-700">{current.complaintType}</span>
            </div>

            <div>
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
                Manufacture Date
              </span>
              <span className="text-slate-600 font-mono">{formatDate(current.manufactureDate)}</span>
            </div>

            <div>
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
                Expiry Date
              </span>
              <span className="text-slate-600 font-mono">{formatDate(current.expiryDate)}</span>
            </div>
          </div>

          {/* Description */}
          <div>
            <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block mb-1.5">
              Incident Narrative
            </span>
            <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 text-slate-800 leading-relaxed">
              {current.description}
            </div>
          </div>

          {/* AI Insights Synthesis */}
          <div className="p-4 rounded-xl bg-linear-to-r from-blue-50/70 via-indigo-50/40 to-slate-50 border border-blue-200 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-blue-900 flex items-center space-x-1.5">
                <Sparkles className="w-4 h-4 text-blue-600" />
                <span>AI Assessment & CAPA Synthesis</span>
              </span>

              <button
                type="button"
                onClick={handleRunAiInsights}
                disabled={isRunningAi}
                className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-lg bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-semibold transition-all shadow-2xs cursor-pointer"
              >
                {isRunningAi ? (
                  <Loader2 className="w-3 h-3 animate-spin" />
                ) : (
                  <Sparkles className="w-3 h-3" />
                )}
                <span>{isRunningAi ? 'Synthesizing...' : 'Run AI Insights'}</span>
              </button>
            </div>

            {current.summary ? (
              <div className="space-y-2 pt-1 text-slate-700">
                <div>
                  <span className="font-semibold text-slate-900 block text-[11px]">
                    Executive Summary:
                  </span>
                  <p className="mt-0.5 leading-relaxed bg-white/80 p-2.5 rounded-lg border border-blue-100">
                    {current.summary.summaryText}
                  </p>
                </div>

                {current.rootCause && (
                  <div>
                    <span className="font-semibold text-slate-900 block text-[11px]">
                      Hypothesized Root Cause:
                    </span>
                    <p className="mt-0.5 leading-relaxed bg-white/80 p-2.5 rounded-lg border border-blue-100">
                      {current.rootCause}
                    </p>
                  </div>
                )}
              </div>
            ) : (
              <p className="text-slate-500 italic text-[11px] pt-1">
                No AI summary generated yet for this manually-logged complaint. Click "Run AI Insights" above to synthesize.
              </p>
            )}
          </div>

          {/* Linked CAPA Plan */}
          {current.capa && (
            <div className="p-4 rounded-xl bg-emerald-50/60 border border-emerald-200 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-emerald-900 flex items-center space-x-1.5">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                  <span>Linked CAPA Action Plan</span>
                </span>
                <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-200">
                  {current.capa.capaStatus || 'Recommended'}
                </span>
              </div>
              <div className="text-slate-800 bg-white/80 p-3 rounded-lg border border-emerald-100 leading-relaxed">
                <div className="font-semibold text-[11px] text-emerald-950 mb-1">
                  Type: {current.capa.actionType} | Owner: {current.capa.actionOwner || 'QA Investigator'}
                </div>
                {current.capa.recommendedAction}
              </div>
            </div>
          )}

          {/* Attached Documents */}
          {current.documents && current.documents.length > 0 && (
            <div>
              <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block mb-2">
                Attached Documents ({current.documents.length})
              </span>
              <div className="space-y-2">
                {current.documents.map((doc) => (
                  <div
                    key={doc.id}
                    className="p-3 rounded-xl bg-slate-50 border border-slate-200 flex items-center justify-between"
                  >
                    <div className="flex items-center space-x-2.5">
                      <FileText className="w-4 h-4 text-blue-600" />
                      <div>
                        <span className="font-semibold text-slate-800 block">{doc.filename}</span>
                        <span className="text-[10px] text-slate-400 font-mono">
                          Format: {doc.fileType.toUpperCase()} | Uploaded: {formatDateTime(doc.uploadedAt)}
                        </span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Footer Actions */}
        <div className="px-6 sm:px-8 py-4 border-t border-slate-100 bg-slate-50/50 flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center space-x-2">
            <span className="text-xs text-slate-500 font-medium">Update Status:</span>
            <select
              value={current.status}
              onChange={(e) => handleStatusChange(e.target.value)}
              disabled={isUpdatingStatus}
              className="px-3 py-1.5 rounded-lg border border-slate-200 bg-white text-xs font-semibold text-slate-800"
            >
              <option value="Open">Open</option>
              <option value="InProgress">In Progress</option>
              <option value="Closed">Closed</option>
            </select>
          </div>

          <button
            type="button"
            onClick={onClose}
            className="px-5 py-2 rounded-xl border border-slate-200 text-slate-700 text-xs font-semibold hover:bg-white transition-colors"
          >
            Close Viewer
          </button>
        </div>
      </div>
    </div>
  );
};
