import { useState, useEffect } from 'react';
import { api } from './api/client';
import type { AnalysisResponse, Complaint, CreateFromAnalysisPayload } from './api/types';
import { Header } from './components/Header';
import { ComplaintForm } from './components/ComplaintForm';
import type { ComplaintFormData } from './components/ComplaintForm';
import { AIAssistantPanel } from './components/AIAssistantPanel';
import { PasteTextModal } from './components/PasteTextModal';
import { ComplaintsList } from './components/ComplaintsList';
import { ComplaintDetailModal } from './components/ComplaintDetailModal';
import { StatsDashboard } from './components/StatsDashboard';
import { CheckCircle2, X } from 'lucide-react';

const EMPTY_FORM: ComplaintFormData = {
  complaintSource: '',
  customerName: '',
  productName: '',
  productStrength: '',
  batchNumber: '',
  manufactureDate: '',
  expiryDate: '',
  quantityAffected: '',
  complaintType: '',
  complaintDate: new Date().toISOString().split('T')[0],
  description: '',
  severity: '',
  priority: 'Open',
  aiSummary: '',
  rootCause: '',
  capaRecommendation: '',
  capaActionType: 'Corrective',
};

export function App() {
  const [activeTab, setActiveTab] = useState<'log' | 'list' | 'analytics'>('log');
  const [systemStatus, setSystemStatus] = useState<'connected' | 'checking' | 'error'>('checking');
  const [formData, setFormData] = useState<ComplaintFormData>(EMPTY_FORM);
  const [analysisData, setAnalysisData] = useState<AnalysisResponse | null>(null);

  // Analysis & extraction state
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [progressPercent, setProgressPercent] = useState(0);
  const [progressStepText, setProgressStepText] = useState('');
  const [uploadedFileName, setUploadedFileName] = useState<string | null>(null);
  const [isPasteModalOpen, setIsPasteModalOpen] = useState(false);

  // Saving state & toasts
  const [isSaving, setIsSaving] = useState(false);
  const [toastMessage, setToastMessage] = useState<{ text: string; type: 'success' | 'error' } | null>(null);

  // Modal viewer state
  const [selectedComplaint, setSelectedComplaint] = useState<Complaint | null>(null);
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  // Health check on mount
  useEffect(() => {
    const checkBackend = async () => {
      try {
        await api.getHealth();
        setSystemStatus('connected');
      } catch (err) {
        setSystemStatus('error');
      }
    };
    checkBackend();
  }, []);

  // Step simulation for extraction progress
  const runProgressAnimation = () => {
    setProgressPercent(10);
    setProgressStepText('Extracting entities & batch coordinates...');
    const t1 = setTimeout(() => {
      setProgressPercent(35);
      setProgressStepText('Querying database for potential duplicate batch signals...');
    }, 400);
    const t2 = setTimeout(() => {
      setProgressPercent(65);
      setProgressStepText('Evaluating completeness & assessing risk classification...');
    }, 900);
    const t3 = setTimeout(() => {
      setProgressPercent(85);
      setProgressStepText('Synthesizing executive summary & CAPA recommendations...');
    }, 1400);

    return () => {
      clearTimeout(t1);
      clearTimeout(t2);
      clearTimeout(t3);
    };
  };

  // Handle File Upload
  const handleFileUpload = async (file: File) => {
    try {
      setIsAnalyzing(true);
      setUploadedFileName(file.name);
      const cancelAnim = runProgressAnimation();

      const analysis = await api.analyzeFile(file);
      cancelAnim();
      setProgressPercent(100);
      setProgressStepText('Analysis complete. Form populated successfully.');
      setAnalysisData(analysis);
      setToastMessage({
        text: `Extracted details from ${file.name}. Review and confirm details.`,
        type: 'success',
      });
    } catch (err: any) {
      setProgressPercent(0);
      setProgressStepText('');
      setToastMessage({
        text: err.message || 'File analysis failed. Please verify format and content.',
        type: 'error',
      });
    } finally {
      setIsAnalyzing(false);
    }
  };

  // Handle Text Paste Analysis
  const handleTextAnalysis = async (text: string) => {
    try {
      setIsAnalyzing(true);
      setUploadedFileName('Pasted Narrative');
      setIsPasteModalOpen(false);
      const cancelAnim = runProgressAnimation();

      const analysis = await api.analyzeText(text, 'Manual');
      cancelAnim();
      setProgressPercent(100);
      setProgressStepText('Analysis complete. Form populated successfully.');
      setAnalysisData(analysis);
      setToastMessage({
        text: 'Complaint text analyzed successfully.',
        type: 'success',
      });
    } catch (err: any) {
      setProgressPercent(0);
      setProgressStepText('');
      setToastMessage({
        text: err.message || 'Text analysis failed. Please ensure at least 30 characters.',
        type: 'error',
      });
    } finally {
      setIsAnalyzing(false);
    }
  };

  // Save Complaint Handler
  const handleSaveComplaint = async () => {
    if (!formData.customerName || !formData.productName || !formData.batchNumber || !formData.description) {
      setToastMessage({
        text: 'Please fill in required fields: Customer Name, Product, Batch, and Description.',
        type: 'error',
      });
      return;
    }

    try {
      setIsSaving(true);

      // If we have AI analysis, use atomic from-analysis endpoint
      if (analysisData?.extracted) {
        const payload: CreateFromAnalysisPayload = {
          extracted: {
            complainantName: formData.customerName,
            productName: formData.productName,
            batchNumber: formData.batchNumber,
            description: formData.description,
            complaintType: formData.complaintType || 'QualityDefect',
            country: formData.productStrength || undefined,
            manufactureDate: formData.manufactureDate ? `${formData.manufactureDate}T00:00:00Z` : undefined,
            expiryDate: formData.expiryDate ? `${formData.expiryDate}T00:00:00Z` : undefined,
          },
          severity: formData.severity || undefined,
          summary: formData.aiSummary || analysisData.summary || undefined,
          capaRecommendation: formData.capaRecommendation || analysisData.capaRecommendation || undefined,
          capaActionType: formData.capaActionType || analysisData.capaActionType || 'Corrective',
          rootCause: formData.rootCause || analysisData.rootCause || undefined,
          source: formData.complaintSource || analysisData.source || 'Manual',
          status: formData.priority || 'Open',
        };

        const saved = await api.saveFromAnalysis(payload);
        setToastMessage({
          text: `Complaint [${saved.complaintNumber}] saved successfully with linked CAPA and Summary!`,
          type: 'success',
        });
      } else {
        // Direct manual save
        const saved = await api.createComplaint({
          complainantName: formData.customerName,
          productName: formData.productName,
          batchNumber: formData.batchNumber,
          description: formData.description,
          complaintType: (formData.complaintType as any) || 'QualityDefect',
          severity: (formData.severity as any) || undefined,
          source: (formData.complaintSource as any) || 'Manual',
          status: (formData.priority as any) || 'Open',
          country: formData.productStrength || undefined,
          manufactureDate: formData.manufactureDate ? `${formData.manufactureDate}T00:00:00Z` : undefined,
          expiryDate: formData.expiryDate ? `${formData.expiryDate}T00:00:00Z` : undefined,
        });

        setToastMessage({
          text: `Complaint [${saved.complaintNumber}] created successfully!`,
          type: 'success',
        });
      }

      // Reset form and refresh
      handleResetForm();
      setRefreshTrigger((prev) => prev + 1);
    } catch (err: any) {
      setToastMessage({
        text: err.message || 'Failed to save complaint.',
        type: 'error',
      });
    } finally {
      setIsSaving(false);
    }
  };

  const handleResetForm = () => {
    setFormData(EMPTY_FORM);
    setAnalysisData(null);
    setUploadedFileName(null);
    setProgressPercent(0);
    setProgressStepText('');
  };

  return (
    <div className="min-h-screen bg-slate-100/70 text-slate-800 flex flex-col antialiased">
      {/* Global Navbar Header */}
      <Header
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        systemStatus={systemStatus}
      />

      {/* Toast Notification */}
      {toastMessage && (
        <div className="fixed bottom-6 right-6 z-50 animate-bounce-in max-w-md">
          <div
            className={`p-4 rounded-xl shadow-xl flex items-start space-x-3 text-xs border ${
              toastMessage.type === 'success'
                ? 'bg-slate-900 text-white border-slate-700'
                : 'bg-red-900 text-white border-red-700'
            }`}
          >
            {toastMessage.type === 'success' ? (
              <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
            ) : (
              <X className="w-5 h-5 text-red-400 shrink-0 mt-0.5" />
            )}
            <div className="flex-1 leading-relaxed">{toastMessage.text}</div>
            <button
              onClick={() => setToastMessage(null)}
              className="text-slate-400 hover:text-white p-0.5"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* Main Workspace Layout */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 lg:p-8">
        {activeTab === 'log' && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
            {/* Left Column: Complaint Form (60-65% width) */}
            <div className="lg:col-span-7 xl:col-span-8">
              <ComplaintForm
                formData={formData}
                setFormData={setFormData}
                analysisData={analysisData}
                onSave={handleSaveComplaint}
                onReset={handleResetForm}
                isSaving={isSaving}
              />
            </div>

            {/* Right Column: AI Assistant Panel (35-40% width) */}
            <div className="lg:col-span-5 xl:col-span-4 sticky top-24">
              <AIAssistantPanel
                onFileUpload={handleFileUpload}
                onOpenPasteModal={() => setIsPasteModalOpen(true)}
                isAnalyzing={isAnalyzing}
                progressPercent={progressPercent}
                progressStepText={progressStepText}
                analysisData={analysisData}
                uploadedFileName={uploadedFileName}
                onClearUploadedFile={handleResetForm}
              />
            </div>
          </div>
        )}

        {activeTab === 'list' && (
          <ComplaintsList
            onSelectComplaint={(c) => setSelectedComplaint(c)}
            onRefreshTrigger={refreshTrigger}
          />
        )}

        {activeTab === 'analytics' && <StatsDashboard />}
      </main>

      {/* Paste Complaint Narrative Modal */}
      <PasteTextModal
        isOpen={isPasteModalOpen}
        onClose={() => setIsPasteModalOpen(false)}
        onSubmitText={handleTextAnalysis}
        isAnalyzing={isAnalyzing}
      />

      {/* Complaint Detail Modal */}
      <ComplaintDetailModal
        complaint={selectedComplaint}
        onClose={() => setSelectedComplaint(null)}
        onUpdate={() => setRefreshTrigger((prev) => prev + 1)}
      />
    </div>
  );
}

export default App;
