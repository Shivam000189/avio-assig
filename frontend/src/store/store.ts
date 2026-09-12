import { configureStore } from '@reduxjs/toolkit';
import complaintFormReducer from './slices/complaintFormSlice';
import complaintsReducer from './slices/complaintsSlice';
import uiReducer from './slices/uiSlice';
import { complaintsApi } from './api/complaintsApi';

export const store = configureStore({
  reducer: {
    complaintForm: complaintFormReducer,
    complaints: complaintsReducer,
    ui: uiReducer,
    [complaintsApi.reducerPath]: complaintsApi.reducer,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware().concat(complaintsApi.middleware),
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
