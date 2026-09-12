import React, { useState, useEffect } from 'react';
import {
  AlertTriangle,
  RotateCcw,
  Save,
  Sparkles,
} from 'lucide-react';
import type { AnalysisResponse } from '../api/types';

export interface ComplaintFormData {
  complaintSource: string;
  customerName: string;
  productName: string;
  productStrength: string;
  batchNumber: string;
  manufactureDate: string;
  expiryDate: string;
  quantityAffected: string;
  complaintType: string;
  complaintDate: string;
  description: string;
  severity: string;
  priority: string;
  aiSummary?: string;
  rootCause?: string;
  capaRecommendation?: string;
  capaActionType?: string;
}

interface ComplaintFormProps {
  formData: ComplaintFormData;
  setFormData: React.Dispatch<React.SetStateAction<ComplaintFormData>>;
  analysisData: AnalysisResponse | null;
  onSave: () => Promise<void>;
  onReset: () => void;
  isSaving: boolean;
}

export const ComplaintForm: React.FC<ComplaintFormProps> = ({
  formData,
  setFormData,
  analysisData,
  onSave,
  onReset,
  isSaving,
}) => {
  const [showAiInsights, setShowAiInsights] = useState(true);

  // Auto-populate when analysis data updates
  useEffect(() => {
    if (analysisData?.extracted) {
      const ext = analysisData.extracted as any;
      setFormData((prev) => ({
        ...prev,
        complaintSource: analysisData.source || prev.complaintSource || 'PDF',
        customerName: ext.complainantName || prev.customerName || '',
        productName: ext.productName || prev.productName || '',
        productStrength: ext.country || prev.productStrength || '',
        batchNumber: ext.batchNumber || prev.batchNumber || '',
        manufactureDate: ext.manufactureDate ? ext.manufactureDate.split('T')[0] : prev.manufactureDate,
        expiryDate: ext.expiryDate ? ext.expiryDate.split('T')[0] : prev.expiryDate,
        complaintType: ext.complaintType || prev.complaintType || 'QualityDefect',
        description: ext.description || prev.description || '',
        severity: analysisData.severity || prev.severity || 'Major',
        aiSummary: analysisData.summary || prev.aiSummary || '',
        rootCause: analysisData.rootCause || prev.rootCause || '',
        capaRecommendation: analysisData.capaRecommendation || prev.capaRecommendation || '',
        capaActionType: analysisData.capaActionType || prev.capaActionType || 'Corrective',
      }));
    }
  }, [analysisData, setFormData]);

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>
  ) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const placeholderText = 'Awaiting AI extraction...';

  return (
    <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden flex flex-col">
      {/* Header Banner */}
      <div className="px-6 sm:px-8 pt-7 pb-5 border-b border-slate-100 flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
            Log Customer Complaint
          </h1>
          <p className="text-xs text-slate-500 font-medium mt-0.5">
            API & FDF Quality Assurance Module
          </p>
        </div>

        {/* Status Pill matching the design */}
        <div className="flex items-center space-x-2">
          <span className="inline-flex items-center px-3 py-1 rounded-md text-xs font-semibold bg-amber-50 text-amber-700 border border-amber-200/80 shadow-2xs">
            Pending Triage
          </span>
        </div>
      </div>

      {/* Duplicate / Trend Warning Banner */}
      {analysisData?.potentialDuplicate && (
        <div className="mx-6 sm:mx-8 mt-5 p-3.5 rounded-xl bg-amber-50/90 border border-amber-300 text-amber-900 text-xs flex items-start space-x-3 animate-fade-in shadow-xs">
          <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
          <div className="flex-1">
            <div className="flex items-center space-x-2">
              <span className="font-bold">
                ⚠️ Potential Duplicate Alert ({analysisData.potentialDuplicate.similarity} Similarity)
              </span>
              {analysisData.potentialDuplicate.complaintNumber && (
                <span className="px-1.5 py-0.5 rounded bg-amber-200/70 font-mono font-bold text-[11px] text-amber-900">
                  {analysisData.potentialDuplicate.complaintNumber}
                </span>
              )}
            </div>
            <p className="mt-1 text-amber-800 leading-relaxed">
              {analysisData.potentialDuplicate.explanation ||
                'This complaint shares product defect characteristics with an existing record in the database.'}
            </p>
          </div>
        </div>
      )}

      {/* Main Form Fields */}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          onSave();
        }}
        className="p-6 sm:p-8 space-y-7 flex-1 overflow-y-auto"
      >
        {/* 1. ORIGIN & CUSTOMER DETAILS */}
        <div>
          <h2 className="text-[11px] font-bold tracking-wider text-slate-500 uppercase mb-3.5 flex items-center space-x-1.5">
            <span>1. ORIGIN & CUSTOMER DETAILS</span>
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                Complaint Source
              </label>
              <input
                type="text"
                name="complaintSource"
                value={formData.complaintSource}
                onChange={handleChange}
                placeholder={placeholderText}
                className="w-full px-3.5 py-2.5 rounded-lg border border-slate-200 bg-slate-50/50 text-slate-800 text-xs focus:bg-white focus:border-blue-500 focus:ring-2 focus:ring-blue-100 transition-all outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                Customer Name <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                name="customerName"
                value={formData.customerName}
                onChange={handleChange}
                required
                placeholder={placeholderText}
                className="w-full px-3.5 py-2.5 rounded-lg border border-slate-200 bg-slate-50/50 text-slate-800 text-xs focus:bg-white focus:border-blue-500 focus:ring-2 focus:ring-blue-100 transition-all outline-none"
              />
            </div>
          </div>
        </div>

        {/* 2. PRODUCT & BATCH IDENTIFICATION */}
        <div>
          <h2 className="text-[11px] font-bold tracking-wider text-slate-500 uppercase mb-3.5 flex items-center space-x-1.5">
            <span>2. PRODUCT & BATCH IDENTIFICATION</span>
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                Product Name <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                name="productName"
                value={formData.productName}
                onChange={handleChange}
                required
                placeholder={placeholderText}
                className="w-full px-3.5 py-2.5 rounded-lg border border-slate-200 bg-slate-50/50 text-slate-800 text-xs focus:bg-white focus:border-blue-500 focus:ring-2 focus:ring-blue-100 transition-all outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                Product Strength/Grade
              </label>
              <input
                type="text"
                name="productStrength"
                value={formData.productStrength}
                onChange={handleChange}
                placeholder={placeholderText}
                className="w-full px-3.5 py-2.5 rounded-lg border border-slate-200 bg-slate-50/50 text-slate-800 text-xs focus:bg-white focus:border-blue-500 focus:ring-2 focus:ring-blue-100 transition-all outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                Batch/Lot Number <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                name="batchNumber"
                value={formData.batchNumber}
                onChange={handleChange}
                required
                placeholder={placeholderText}
                className="w-full px-3.5 py-2.5 rounded-lg border border-slate-200 bg-slate-50/50 font-mono text-slate-800 text-xs focus:bg-white focus:border-blue-500 focus:ring-2 focus:ring-blue-100 transition-all outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                Manufacturing Date
              </label>
              <div className="relative">
                <input
                  type="date"
                  name="manufactureDate"
                  value={formData.manufactureDate}
                  onChange={handleChange}
                  className="w-full px-3.5 py-2.5 rounded-lg border border-slate-200 bg-slate-50/50 text-slate-800 text-xs focus:bg-white focus:border-blue-500 focus:ring-2 focus:ring-blue-100 transition-all outline-none"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                Expiry Date
              </label>
              <div className="relative">
                <input
                  type="date"
                  name="expiryDate"
                  value={formData.expiryDate}
                  onChange={handleChange}
                  className="w-full px-3.5 py-2.5 rounded-lg border border-slate-200 bg-slate-50/50 text-slate-800 text-xs focus:bg-white focus:border-blue-500 focus:ring-2 focus:ring-blue-100 transition-all outline-none"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                Quantity Affected
              </label>
              <div className="relative">
                <input
                  type="text"
                  name="quantityAffected"
                  value={formData.quantityAffected}
                  onChange={handleChange}
                  placeholder={placeholderText}
                  className="w-full pl-3.5 pr-10 py-2.5 rounded-lg border border-slate-200 bg-slate-50/50 text-slate-800 text-xs focus:bg-white focus:border-blue-500 focus:ring-2 focus:ring-blue-100 transition-all outline-none"
                />
                <span className="absolute right-3.5 top-1/2 -translate-y-1/2 text-xs font-medium text-slate-400">
                  kg
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* 3. COMPLAINT DETAILS */}
        <div>
          <h2 className="text-[11px] font-bold tracking-wider text-slate-500 uppercase mb-3.5 flex items-center space-x-1.5">
            <span>3. COMPLAINT DETAILS</span>
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                Complaint Type <span className="text-red-500">*</span>
              </label>
              <select
                name="complaintType"
                value={formData.complaintType}
                onChange={handleChange}
                required
                className="w-full px-3.5 py-2.5 rounded-lg border border-slate-200 bg-slate-50/50 text-slate-800 text-xs focus:bg-white focus:border-blue-500 focus:ring-2 focus:ring-blue-100 transition-all outline-none"
              >
                <option value="">{placeholderText}</option>
                <option value="QualityDefect">Quality Defect (Physical/Chemical)</option>
                <option value="AdverseEvent">Adverse Event (Safety)</option>
                <option value="LabelingIssue">Labeling Issue</option>
                <option value="PackagingIssue">Packaging Issue</option>
                <option value="DeliveryIssue">Delivery Issue</option>
                <option value="Other">Other</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                Complaint Date
              </label>
              <div className="relative">
                <input
                  type="date"
                  name="complaintDate"
                  value={formData.complaintDate}
                  onChange={handleChange}
                  className="w-full px-3.5 py-2.5 rounded-lg border border-slate-200 bg-slate-50/50 text-slate-800 text-xs focus:bg-white focus:border-blue-500 focus:ring-2 focus:ring-blue-100 transition-all outline-none"
                />
              </div>
            </div>

            <div className="sm:col-span-2">
              <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                Detailed Complaint Description <span className="text-red-500">*</span>
              </label>
              <textarea
                name="description"
                value={formData.description}
                onChange={handleChange}
                rows={4}
                required
                placeholder={placeholderText}
                className="w-full px-3.5 py-2.5 rounded-lg border border-slate-200 bg-slate-50/50 text-slate-800 text-xs focus:bg-white focus:border-blue-500 focus:ring-2 focus:ring-blue-100 transition-all outline-none resize-y"
              />
            </div>
          </div>
        </div>

        {/* 4. INITIAL ASSESSMENT & PRIORITY */}
        <div>
          <h2 className="text-[11px] font-bold tracking-wider text-slate-500 uppercase mb-3.5 flex items-center space-x-1.5">
            <span>4. INITIAL ASSESSMENT & PRIORITY</span>
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                Initial Severity
              </label>
              <select
                name="severity"
                value={formData.severity}
                onChange={handleChange}
                className="w-full px-3.5 py-2.5 rounded-lg border border-slate-200 bg-slate-50/50 text-slate-800 text-xs focus:bg-white focus:border-blue-500 focus:ring-2 focus:ring-blue-100 transition-all outline-none"
              >
                <option value="">{placeholderText}</option>
                <option value="Critical">Critical (Class I Hazard / Patient Risk)</option>
                <option value="Major">Major (Class II Regulatory / Defect)</option>
                <option value="Minor">Minor (Cosmetic / Low Impact)</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                Priority
              </label>
              <select
                name="priority"
                value={formData.priority}
                onChange={handleChange}
                className="w-full px-3.5 py-2.5 rounded-lg border border-slate-200 bg-slate-50/50 text-slate-800 text-xs focus:bg-white focus:border-blue-500 focus:ring-2 focus:ring-blue-100 transition-all outline-none"
              >
                <option value="Open">Open (Initial Intake)</option>
                <option value="InProgress">In Progress (Investigation)</option>
                <option value="Closed">Closed</option>
              </select>
            </div>
          </div>
        </div>

        {/* AI INSIGHTS CARD (Summary + CAPA + Root Cause) */}
        {(formData.aiSummary || formData.capaRecommendation || formData.rootCause) && (
          <div className="p-4 rounded-xl bg-linear-to-r from-blue-50/70 via-indigo-50/40 to-slate-50 border border-blue-200/80 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-blue-900 flex items-center space-x-1.5">
                <Sparkles className="w-3.5 h-3.5 text-blue-600" />
                <span>AI Generated Synthesis & CAPA Plan</span>
              </span>
              <button
                type="button"
                onClick={() => setShowAiInsights(!showAiInsights)}
                className="text-[11px] text-blue-700 hover:underline font-medium"
              >
                {showAiInsights ? 'Hide Details' : 'Show Details'}
              </button>
            </div>

            {showAiInsights && (
              <div className="space-y-2.5 pt-1 text-xs text-slate-700">
                {formData.aiSummary && (
                  <div>
                    <span className="font-semibold text-slate-900 block text-[11px]">
                      Executive Summary:
                    </span>
                    <p className="text-slate-600 mt-0.5 leading-relaxed bg-white/70 p-2.5 rounded-lg border border-blue-100/80">
                      {formData.aiSummary}
                    </p>
                  </div>
                )}

                {formData.capaRecommendation && (
                  <div>
                    <span className="font-semibold text-slate-900 block text-[11px]">
                      Recommended CAPA Action ({formData.capaActionType || 'Corrective'}):
                    </span>
                    <p className="text-slate-600 mt-0.5 leading-relaxed bg-white/70 p-2.5 rounded-lg border border-blue-100/80">
                      {formData.capaRecommendation}
                    </p>
                  </div>
                )}

                {formData.rootCause && (
                  <div>
                    <span className="font-semibold text-slate-900 block text-[11px]">
                      Root Cause Hypothesis:
                    </span>
                    <p className="text-slate-600 mt-0.5 leading-relaxed bg-white/70 p-2.5 rounded-lg border border-blue-100/80">
                      {formData.rootCause}
                    </p>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* Footer Actions */}
        <div className="pt-4 border-t border-slate-100 flex items-center justify-between">
          <button
            type="button"
            onClick={onReset}
            className="flex items-center space-x-2 px-4 py-2.5 rounded-xl border border-slate-200 text-slate-700 text-xs font-semibold hover:bg-slate-50 transition-colors shadow-2xs cursor-pointer"
          >
            <RotateCcw className="w-3.5 h-3.5 text-slate-500" />
            <span>Reset Form</span>
          </button>

          <button
            type="submit"
            disabled={isSaving}
            className="flex items-center space-x-2 px-6 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 active:bg-blue-800 text-white text-xs font-semibold shadow-md shadow-blue-600/20 transition-all disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
          >
            {isSaving ? (
              <span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            ) : (
              <Save className="w-3.5 h-3.5" />
            )}
            <span>{isSaving ? 'Saving Complaint...' : 'Save Complaint'}</span>
          </button>
        </div>
      </form>
    </div>
  );
};
