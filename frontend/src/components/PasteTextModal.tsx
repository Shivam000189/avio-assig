import React, { useState } from 'react';
import { FileText, Loader2, Sparkles, X } from 'lucide-react';

interface PasteTextModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmitText: (text: string) => Promise<void>;
  isAnalyzing: boolean;
}

const SAMPLE_PRESETS = [
  {
    title: '💊 Tablet Chipping (Batch PT-4471-A)',
    text: `From: hospital_pharmacy@metrohealth.org
Subject: Urgent: Defective Paracetamol 500mg Tablets - Batch PT-4471-A

Dear Quality Assurance Team,
We received a batch of Paracetamol 500mg tablets (Lot / Batch number: PT-4471-A, Expiry: 12/2027) manufactured in January 2025. Upon opening the blister packaging for dispensing in our outpatient ward, multiple tablets were found to have chipped edges, severe crumbling, and excessive powder residue in the blister cavities. Approximately 5 blister strips were affected.

Please investigate immediately and advise on replacement protocol.

Sincerely,
Dr. Elizabeth Vance, Chief Pharmacist
Metro Health Hospital Pharmacy`,
  },
  {
    title: '⚠️ Adverse Event (Amoxicillin Rash)',
    text: `URGENT ADVERSE EVENT REPORT
Patient: Female, 42 years old
Product: Amoxicillin 250mg Capsules
Batch Number: AMX-8802-C (Exp: 08/2026, Mfg: 02/2024)
Complainant: Dr. Marcus Brody, Memorial Clinic

Patient developed severe acute urticarial skin rash, facial angioedema, and mild respiratory wheezing approximately 30 minutes following administration of first capsule from prescribed blister pack. Patient required emergency IM epinephrine and oral antihistamines. Patient has no prior penicillin allergy documented. Retaining remaining capsule blister for analytical assay.`,
  },
];

export const PasteTextModal: React.FC<PasteTextModalProps> = ({
  isOpen,
  onClose,
  onSubmitText,
  isAnalyzing,
}) => {
  const [text, setText] = useState('');

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (text.trim().length >= 30) {
      onSubmitText(text.trim());
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-xs animate-fade-in">
      <div className="bg-white rounded-2xl border border-slate-200 shadow-2xl max-w-2xl w-full overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
          <div className="flex items-center space-x-2.5">
            <div className="w-8 h-8 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center">
              <FileText className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-slate-900">
                Paste Complaint Narrative / Email
              </h2>
              <p className="text-xs text-slate-500">
                The 7-node LangGraph pipeline will extract entities, check duplicates, assess risk & recommend CAPA.
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Content */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4 flex-1 flex flex-col overflow-y-auto">
          {/* Preset Buttons */}
          <div>
            <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block mb-2">
              Quick Load Sample Presets:
            </span>
            <div className="flex flex-wrap gap-2">
              {SAMPLE_PRESETS.map((preset, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => setText(preset.text)}
                  className="px-3 py-1.5 rounded-lg bg-slate-50 hover:bg-blue-50 border border-slate-200 hover:border-blue-300 text-slate-700 hover:text-blue-700 text-xs font-medium transition-all"
                >
                  {preset.title}
                </button>
              ))}
            </div>
          </div>

          <div className="flex-1 flex flex-col">
            <label className="block text-xs font-semibold text-slate-700 mb-1.5">
              Complaint Text (Minimum 30 characters)
            </label>
            <textarea
              value={text}
              onChange={(e) => setText(e.target.value)}
              rows={9}
              required
              placeholder="Paste email correspondence, transcribed call notes, or customer incident description..."
              className="w-full flex-1 p-3.5 rounded-xl border border-slate-200 bg-slate-50/50 text-slate-800 text-xs focus:bg-white focus:border-blue-500 focus:ring-2 focus:ring-blue-100 transition-all outline-none font-mono resize-y"
            />
          </div>

          {/* Footer */}
          <div className="pt-3 border-t border-slate-100 flex items-center justify-between">
            <span className="text-[11px] text-slate-400">
              {text.length} characters (min 30 required)
            </span>

            <div className="flex items-center space-x-2.5">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 rounded-xl border border-slate-200 text-slate-600 text-xs font-semibold hover:bg-slate-50"
              >
                Cancel
              </button>

              <button
                type="submit"
                disabled={isAnalyzing || text.trim().length < 30}
                className="flex items-center space-x-2 px-5 py-2 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold shadow-md shadow-blue-600/20 disabled:opacity-50 cursor-pointer"
              >
                {isAnalyzing ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <Sparkles className="w-3.5 h-3.5" />
                )}
                <span>{isAnalyzing ? 'Analyzing Pipeline...' : 'Run AI Analysis'}</span>
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
};
