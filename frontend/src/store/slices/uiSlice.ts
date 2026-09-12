import { createSlice, type PayloadAction } from '@reduxjs/toolkit';
import type { Complaint } from '../../api/types';

type ActiveTab = 'log' | 'list' | 'analytics';
type SystemStatus = 'connected' | 'checking' | 'error';

interface ToastMessage {
  text: string;
  type: 'success' | 'error';
}

interface UiState {
  activeTab: ActiveTab;
  systemStatus: SystemStatus;
  isPasteModalOpen: boolean;
  toastMessage: ToastMessage | null;
  selectedComplaint: Complaint | null;
}

const initialState: UiState = {
  activeTab: 'log',
  systemStatus: 'checking',
  isPasteModalOpen: false,
  toastMessage: null,
  selectedComplaint: null,
};

const uiSlice = createSlice({
  name: 'ui',
  initialState,
  reducers: {
    setActiveTab: (state, action: PayloadAction<ActiveTab>) => {
      state.activeTab = action.payload;
    },
    setSystemStatus: (state, action: PayloadAction<SystemStatus>) => {
      state.systemStatus = action.payload;
    },
    setPasteModalOpen: (state, action: PayloadAction<boolean>) => {
      state.isPasteModalOpen = action.payload;
    },
    setToastMessage: (state, action: PayloadAction<ToastMessage | null>) => {
      state.toastMessage = action.payload;
    },
    setSelectedComplaint: (state, action: PayloadAction<Complaint | null>) => {
      state.selectedComplaint = action.payload;
    },
  },
});

export const {
  setActiveTab,
  setSystemStatus,
  setPasteModalOpen,
  setToastMessage,
  setSelectedComplaint,
} = uiSlice.actions;

export default uiSlice.reducer;
