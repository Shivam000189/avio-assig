import { createSlice, type PayloadAction } from '@reduxjs/toolkit';
import type { Complaint } from '../../api/types';

interface ComplaintFilters {
  search: string;
  severity: string;
  status: string;
  complaintType: string;
}

interface ComplaintsState {
  items: Complaint[];
  total: number;
  page: number;
  limit: number;
  filters: ComplaintFilters;
  refreshTrigger: number;
}

const initialState: ComplaintsState = {
  items: [],
  total: 0,
  page: 0,
  limit: 10,
  filters: { search: '', severity: '', status: '', complaintType: '' },
  refreshTrigger: 0,
};

const complaintsSlice = createSlice({
  name: 'complaints',
  initialState,
  reducers: {
    setComplaints: (state, action: PayloadAction<{ items: Complaint[]; total: number }>) => {
      state.items = action.payload.items;
      state.total = action.payload.total;
    },
    setPage: (state, action: PayloadAction<number>) => {
      state.page = action.payload;
    },
    setFilter: (
      state,
      action: PayloadAction<{ field: keyof ComplaintFilters; value: string }>,
    ) => {
      state.filters[action.payload.field] = action.payload.value;
      state.page = 0;
    },
    incrementRefreshTrigger: (state) => {
      state.refreshTrigger += 1;
    },
  },
});

export const { setComplaints, setPage, setFilter, incrementRefreshTrigger } = complaintsSlice.actions;
export default complaintsSlice.reducer;
