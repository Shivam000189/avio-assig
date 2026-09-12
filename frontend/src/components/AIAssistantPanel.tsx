import React, { useState, useRef } from 'react';
import {
  Bot,
  FileText,
  Info,
  Loader2,
  Send,
  Sparkles,
  UploadCloud,
  X,
} from 'lucide-react';
import { useAppDispatch, useAppSelector } from '../store/hooks';
import { resetComplaintForm, setAnalysisData, setAnalyzing, setProgress, setUploadedFileName } from '../store/slices/complaintFormSlice';
import { setPasteModalOpen, setToastMessage } from '../store/slices/uiSlice';
import { useAnalyzeFileMutation, useChatMutation } from '../store/api/complaintsApi';

export const AIAssistantPanel: React.FC = () => {
  const dispatch = useAppDispatch();
  const { analysisData, isAnalyzing, progressPercent, progressStepText, uploadedFileName } = useAppSelector((state) => state.complaintForm);
  const [analyzeFile] = useAnalyzeFileMutation();
  const [chat] = useChatMutation();
  const [isDragOver, setIsDragOver] = useState(false);
  const [chatInput, setChatInput] = useState('');
  const [chatMessages, setChatMessages] = useState<
    Array<{ sender: 'bot' | 'user'; text: string; time?: string }>
  >([
    {
      sender: 'bot',
      text: 'Upload a complaint document or paste text above. I will automatically extract the details and populate the form for you.',
    },
  ]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const runProgressAnimation = () => {
    dispatch(setProgress({ percent: 10, text: 'Extracting entities & batch coordinates...' }));
    const timers = [
      window.setTimeout(() => dispatch(setProgress({ percent: 35, text: 'Querying database for potential duplicate batch signals...' })), 400),
      window.setTimeout(() => dispatch(setProgress({ percent: 65, text: 'Evaluating completeness & assessing risk classification...' })), 900),
      window.setTimeout(() => dispatch(setProgress({ percent: 85, text: 'Synthesizing executive summary & CAPA recommendations...' })), 1400),
    ];
    return () => timers.forEach(window.clearTimeout);
  };

  const handleFileUpload = async (file: File) => {
    dispatch(setAnalyzing(true));
    dispatch(setUploadedFileName(file.name));
    const cancelAnimation = runProgressAnimation();
    try {
      const analysis = await analyzeFile({ file }).unwrap();
      cancelAnimation();
      dispatch(setProgress({ percent: 100, text: 'Analysis complete. Form populated successfully.' }));
      dispatch(setAnalysisData(analysis));
      dispatch(setToastMessage({ text: `Extracted details from ${file.name}. Review and confirm details.`, type: 'success' }));
    } catch (error) {
      cancelAnimation();
      dispatch(setProgress({ percent: 0, text: '' }));
      dispatch(setToastMessage({ text: getErrorMessage(error, 'File analysis failed. Please verify format and content.'), type: 'error' }));
    } finally {
      dispatch(setAnalyzing(false));
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = () => {
    setIsDragOver(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const file = e.dataTransfer.files[0];
      handleFileUpload(file);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const file = e.target.files[0];
      handleFileUpload(file);
      e.target.value = '';
    }
  };

  const handleSendChat = (e: React.FormEvent) => {
    e.preventDefault();
    if (!chatInput.trim()) return;

    const userText = chatInput.trim();
    setChatMessages((prev) => [...prev, { sender: 'user', text: userText }]);
    setChatInput('');

    void chat({
      message: userText,
      complaintContext: analysisData || {
        rawInput: '',
        source: 'Manual',
        extracted: null,
        missingFields: [],
        isComplete: false,
        duplicateChecked: false,
        warnings: [],
      },
    })
      .unwrap()
      .then(({ response }) => setChatMessages((prev) => [...prev, { sender: 'bot', text: response }]))
      .catch((error) => setChatMessages((prev) => [...prev, { sender: 'bot', text: getErrorMessage(error, 'I could not reach the AI assistant. Please verify the backend and GROQ_API_KEY.') }]));
  };

  return (
    <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden flex flex-col h-full">
      {/* Header */}
      <div className="px-6 pt-6 pb-4 border-b border-slate-100 flex items-center justify-between">
        <div className="flex items-center space-x-2.5">
          <div className="w-7 h-7 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center">
            <Sparkles className="w-4 h-4" />
          </div>
          <h2 className="text-sm font-bold text-slate-900 tracking-tight">
            AI Complaint Intake Assistant
          </h2>
        </div>
        <span className="px-2 py-0.5 rounded-full text-[10px] font-bold tracking-wider uppercase bg-blue-100 text-blue-800 border border-blue-200">
          BETA
        </span>
      </div>

      <div className="p-6 space-y-5 flex-1 flex flex-col overflow-y-auto">
        {/* Upload Zone */}
        <div>
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.txt,.eml"
            onChange={handleFileChange}
            className="hidden"
          />

          <div
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            className={`border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition-all ${
              isDragOver
                ? 'border-blue-500 bg-blue-50/60 scale-[0.99]'
                : uploadedFileName
                ? 'border-emerald-300 bg-emerald-50/30'
                : 'border-slate-200 hover:border-blue-400 hover:bg-slate-50/50'
            }`}
          >
            <UploadCloud className="w-8 h-8 text-blue-600 mx-auto mb-2 opacity-80" />
            <p className="text-xs text-slate-700 font-medium">
              Drag & drop complaint document here
            </p>
            <p className="text-[11px] text-blue-600 font-semibold mt-0.5 hover:underline">
              or click to browse
            </p>

            {uploadedFileName && (
              <div className="mt-3 inline-flex items-center space-x-1.5 px-3 py-1 rounded-md bg-white border border-emerald-200 text-emerald-800 text-xs shadow-2xs">
                <FileText className="w-3.5 h-3.5 text-emerald-600" />
                <span className="font-medium truncate max-w-[200px]">{uploadedFileName}</span>
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    dispatch(resetComplaintForm());
                  }}
                  className="p-0.5 hover:bg-emerald-100 rounded text-slate-400 hover:text-slate-700"
                >
                  <X className="w-3 h-3" />
                </button>
              </div>
            )}
          </div>

          {/* OR Divider */}
          <div className="flex items-center my-3.5">
            <div className="flex-1 border-t border-slate-100" />
            <span className="px-3 text-[10px] font-bold text-slate-400 tracking-wider">
              OR
            </span>
            <div className="flex-1 border-t border-slate-100" />
          </div>

          {/* Paste Button */}
          <button
            type="button"
            onClick={() => dispatch(setPasteModalOpen(true))}
            className="w-full flex items-center justify-center space-x-2 py-2.5 px-4 rounded-xl border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 text-xs font-semibold shadow-2xs transition-colors cursor-pointer"
          >
            <FileText className="w-4 h-4 text-slate-500" />
            <span>Paste Complaint Text / Email</span>
          </button>

          {/* Supported Formats Info Pill */}
          <div className="mt-3.5 p-2.5 rounded-lg bg-emerald-50/70 border border-emerald-200/80 text-emerald-900 text-[11px] flex items-start space-x-2">
            <Info className="w-4 h-4 text-emerald-600 shrink-0 mt-0.2" />
            <div className="leading-tight">
              <span className="font-semibold">Supported formats:</span> PDF, TXT, EML
              <span className="block text-emerald-700 text-[10px] mt-0.5">Max file size: 10MB</span>
            </div>
          </div>
        </div>

        {/* EXTRACTION PROGRESS */}
        {(isAnalyzing || progressPercent > 0) && (
          <div className="pt-2 animate-fade-in">
            <div className="flex items-center justify-between text-xs mb-1.5">
              <span className="text-[11px] font-bold text-slate-600 uppercase tracking-wider">
                EXTRACTION PROGRESS
              </span>
              <span className="font-bold text-blue-600 text-xs">{progressPercent}%</span>
            </div>

            {/* Progress Bar */}
            <div className="w-full h-2 rounded-full bg-slate-100 overflow-hidden relative">
              <div
                className="h-full bg-linear-to-r from-blue-500 via-indigo-600 to-blue-600 rounded-full transition-all duration-300 relative"
                style={{ width: `${progressPercent}%` }}
              >
                {isAnalyzing && (
                  <div className="absolute inset-0 bg-white/20 animate-shimmer" />
                )}
              </div>
            </div>

            <p className="text-[11px] text-slate-500 mt-2 leading-relaxed flex items-center space-x-1.5">
              {isAnalyzing && <Loader2 className="w-3 h-3 text-blue-600 animate-spin shrink-0" />}
              <span>
                {progressStepText ||
                  'Analyzing document content and extracting key details... Please wait, this may take a few moments.'}
              </span>
            </p>
          </div>
        )}

        {/* AI ASSISTANT CONVERSATION BUBBLE */}
        <div className="flex-1 flex flex-col min-h-[160px] pt-1">
          <h3 className="text-[11px] font-bold text-slate-600 uppercase tracking-wider mb-2.5">
            AI ASSISTANT
          </h3>

          <div className="flex-1 bg-slate-50/70 border border-slate-200/80 rounded-xl p-3.5 space-y-3 overflow-y-auto max-h-[220px]">
            {chatMessages.map((msg, idx) => (
              <div
                key={idx}
                className={`flex items-start space-x-2.5 text-xs ${
                  msg.sender === 'user' ? 'justify-end' : 'justify-start'
                }`}
              >
                {msg.sender === 'bot' && (
                  <div className="w-6 h-6 rounded-lg bg-blue-600 text-white flex items-center justify-center shrink-0 shadow-xs">
                    <Bot className="w-3.5 h-3.5" />
                  </div>
                )}
                <div
                  className={`p-3 rounded-xl max-w-[85%] leading-relaxed ${
                    msg.sender === 'bot'
                      ? 'bg-white border border-blue-100/90 text-slate-800 shadow-2xs'
                      : 'bg-blue-600 text-white shadow-xs'
                  }`}
                >
                  {msg.text}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Interactive Chat Input */}
        <form onSubmit={handleSendChat} className="relative pt-1">
          <input
            type="text"
            value={chatInput}
            onChange={(e) => setChatInput(e.target.value)}
            placeholder="Ask me anything about this complaint..."
            className="w-full pl-3.5 pr-11 py-2.5 rounded-xl border border-slate-200 bg-white text-slate-800 text-xs focus:border-blue-500 focus:ring-2 focus:ring-blue-100 transition-all outline-none shadow-2xs"
          />
          <button
            type="submit"
            disabled={!chatInput.trim()}
            className="absolute right-1.5 top-2.5 p-1.5 rounded-lg bg-blue-600 hover:bg-blue-700 disabled:opacity-40 text-white transition-all cursor-pointer"
          >
            <Send className="w-3.5 h-3.5" />
          </button>
        </form>

        <p className="text-[10px] text-center text-slate-400 pt-0.5">
          AI responses may contain errors. Please verify information per GMP SOPs.
        </p>
      </div>
    </div>
  );
};

function getErrorMessage(error: unknown, fallback: string): string {
  if (typeof error === 'object' && error !== null && 'data' in error) {
    const data = (error as { data?: { detail?: string; message?: string } }).data;
    return data?.detail || data?.message || fallback;
  }
  return fallback;
}
