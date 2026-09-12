import { createSlice, type PayloadAction } from '@reduxjs/toolkit';
import type { AnalysisResponse } from '../../api/types';

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

const createEmptyForm = (): ComplaintFormData => ({
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
});

interface ComplaintFormState {
  formData: ComplaintFormData;
  analysisData: AnalysisResponse | null;
  uploadedFileName: string | null;
  isAnalyzing: boolean;
  isSaving: boolean;
  progressPercent: number;
  progressStepText: string;
}

const initialState: ComplaintFormState = {
  formData: createEmptyForm(),
  analysisData: null,
  uploadedFileName: null,
  isAnalyzing: false,
  isSaving: false,
  progressPercent: 0,
  progressStepText: '',
};

const complaintFormSlice = createSlice({
  name: 'complaintForm',
  initialState,
  reducers: {
    updateFormField: (
      state,
      action: PayloadAction<{ field: keyof ComplaintFormData; value: string }>,
    ) => {
      state.formData[action.payload.field] = action.payload.value;
    },
    setAnalysisData: (state, action: PayloadAction<AnalysisResponse | null>) => {
      state.analysisData = action.payload;
    },
    populateFromAnalysis: (state, action: PayloadAction<AnalysisResponse>) => {
      const analysis = action.payload;
      const extracted = analysis.extracted as Record<string, string | undefined> | null;
      if (!extracted) return;
      state.formData = {
        ...state.formData,
        complaintSource: analysis.source || state.formData.complaintSource || 'PDF',
        customerName: extracted.complainantName || state.formData.customerName,
        productName: extracted.productName || state.formData.productName,
        productStrength: extracted.country || state.formData.productStrength,
        batchNumber: extracted.batchNumber || state.formData.batchNumber,
        manufactureDate: extracted.manufactureDate?.split('T')[0] || state.formData.manufactureDate,
        expiryDate: extracted.expiryDate?.split('T')[0] || state.formData.expiryDate,
        complaintType: extracted.complaintType || state.formData.complaintType || 'QualityDefect',
        description: extracted.description || state.formData.description,
        severity: analysis.severity || state.formData.severity || 'Major',
        aiSummary: analysis.summary || state.formData.aiSummary || '',
        rootCause: analysis.rootCause || state.formData.rootCause || '',
        capaRecommendation: analysis.capaRecommendation || state.formData.capaRecommendation || '',
        capaActionType: analysis.capaActionType || state.formData.capaActionType || 'Corrective',
      };
    },
    setUploadedFileName: (state, action: PayloadAction<string | null>) => {
      state.uploadedFileName = action.payload;
    },
    setAnalyzing: (state, action: PayloadAction<boolean>) => {
      state.isAnalyzing = action.payload;
    },
    setSaving: (state, action: PayloadAction<boolean>) => {
      state.isSaving = action.payload;
    },
    setProgress: (
      state,
      action: PayloadAction<{ percent: number; text: string }>,
    ) => {
      state.progressPercent = action.payload.percent;
      state.progressStepText = action.payload.text;
    },
    resetComplaintForm: (state) => {
      state.formData = createEmptyForm();
      state.analysisData = null;
      state.uploadedFileName = null;
      state.isAnalyzing = false;
      state.isSaving = false;
      state.progressPercent = 0;
      state.progressStepText = '';
    },
  },
});

export const {
  updateFormField,
  setAnalysisData,
  populateFromAnalysis,
  setUploadedFileName,
  setAnalyzing,
  setSaving,
  setProgress,
  resetComplaintForm,
} = complaintFormSlice.actions;

export default complaintFormSlice.reducer;
