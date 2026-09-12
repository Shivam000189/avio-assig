import { createApi, fetchBaseQuery } from '@reduxjs/toolkit/query/react';
import type {
  AnalysisResponse,
  Complaint,
  ComplaintStatsResponse,
  CreateFromAnalysisPayload,
  PaginatedComplaintsResponse,
} from '../../api/types';

export interface ComplaintListParams {
  skip?: number;
  limit?: number;
  search?: string;
  status?: string;
  severity?: string;
  complaintType?: string;
  refreshTrigger?: number;
}

export interface ComplaintChatResponse {
  response: string;
}

export const complaintsApi = createApi({
  reducerPath: 'complaintsApi',
  baseQuery: fetchBaseQuery({
    baseUrl: import.meta.env.VITE_API_BASE_URL
      ? `${import.meta.env.VITE_API_BASE_URL.replace(/\/$/, '')}/`
      : '/',
  }),
  tagTypes: ['Complaint', 'Stats'],
  endpoints: (builder) => ({
    getHealth: builder.query<{ status: string; app: string; version: string }, void>({
      query: () => 'health',
    }),
    getStats: builder.query<ComplaintStatsResponse, void>({
      query: () => 'api/v1/complaints/stats',
      providesTags: ['Stats'],
    }),
    getComplaints: builder.query<PaginatedComplaintsResponse, ComplaintListParams | void>({
      query: (params) => {
        const query = new URLSearchParams();
        if (params?.skip !== undefined) query.set('skip', params.skip.toString());
        if (params?.limit !== undefined) query.set('limit', params.limit.toString());
        if (params?.search) query.set('search', params.search);
        if (params?.status) query.set('status', params.status);
        if (params?.severity) query.set('severity', params.severity);
        if (params?.complaintType) query.set('complaintType', params.complaintType);
        const suffix = query.toString() ? `?${query.toString()}` : '';
        return `api/v1/complaints${suffix}`;
      },
      providesTags: (result) =>
        result
          ? [
              ...result.items.map(({ id }) => ({ type: 'Complaint' as const, id })),
              { type: 'Complaint' as const, id: 'LIST' },
            ]
          : [{ type: 'Complaint' as const, id: 'LIST' }],
    }),
    getComplaint: builder.query<Complaint, string>({
      query: (id) => `api/v1/complaints/${id}`,
      providesTags: (_result, _error, id) => [{ type: 'Complaint', id }],
    }),
    createComplaint: builder.mutation<Complaint, Partial<Complaint>>({
      query: (payload) => ({
        url: 'api/v1/complaints',
        method: 'POST',
        body: payload,
      }),
      invalidatesTags: ['Complaint', 'Stats'],
    }),
    updateComplaint: builder.mutation<Complaint, { id: string; payload: Partial<Complaint> }>({
      query: ({ id, payload }) => ({
        url: `api/v1/complaints/${id}`,
        method: 'PUT',
        body: payload,
      }),
      invalidatesTags: (_result, _error, { id }) => [
        { type: 'Complaint', id },
        { type: 'Complaint', id: 'LIST' },
        'Stats',
      ],
    }),
    deleteComplaint: builder.mutation<void, string>({
      query: (id) => ({ url: `api/v1/complaints/${id}`, method: 'DELETE' }),
      invalidatesTags: ['Complaint', 'Stats'],
    }),
    analyzeText: builder.mutation<AnalysisResponse, { text: string; source?: string }>({
      query: ({ text, source = 'Manual' }) => ({
        url: 'api/v1/complaints/analyze',
        method: 'POST',
        body: { text, source },
      }),
    }),
    analyzeFile: builder.mutation<AnalysisResponse, { file: File; complaintId?: string }>({
      query: ({ file, complaintId }) => {
        const body = new FormData();
        body.append('file', file);
        if (complaintId) body.append('complaint_id', complaintId);
        return { url: 'api/v1/complaints/analyze-file', method: 'POST', body };
      },
    }),
    saveFromAnalysis: builder.mutation<Complaint, CreateFromAnalysisPayload>({
      query: (payload) => ({
        url: 'api/v1/complaints/from-analysis',
        method: 'POST',
        body: payload,
      }),
      invalidatesTags: ['Complaint', 'Stats'],
    }),
    generateAiInsights: builder.mutation<Complaint, string>({
      query: (id) => ({ url: `api/v1/complaints/${id}/ai-insights`, method: 'POST' }),
      invalidatesTags: (_result, _error, id) => [
        { type: 'Complaint', id },
        { type: 'Complaint', id: 'LIST' },
        'Stats',
      ],
    }),
    getCapa: builder.query<Complaint['capa'], string>({
      query: (id) => `api/v1/complaints/${id}/capa`,
      providesTags: (_result, _error, id) => [{ type: 'Complaint', id }],
    }),
    updateCapa: builder.mutation<Complaint['capa'], { id: string; payload: Record<string, unknown> }>({
      query: ({ id, payload }) => ({
        url: `api/v1/complaints/${id}/capa`,
        method: 'PUT',
        body: payload,
      }),
      invalidatesTags: (_result, _error, { id }) => [{ type: 'Complaint', id }],
    }),
    chat: builder.mutation<ComplaintChatResponse, { message: string; complaintContext: AnalysisResponse | Complaint }>({
      query: ({ message, complaintContext }) => ({
        url: 'api/v1/complaints/chat',
        method: 'POST',
        body: { message, complaint_context: complaintContext },
      }),
    }),
  }),
});

export const {
  useGetHealthQuery,
  useGetStatsQuery,
  useGetComplaintsQuery,
  useGetComplaintQuery,
  useCreateComplaintMutation,
  useUpdateComplaintMutation,
  useDeleteComplaintMutation,
  useAnalyzeTextMutation,
  useAnalyzeFileMutation,
  useSaveFromAnalysisMutation,
  useGenerateAiInsightsMutation,
  useGetCapaQuery,
  useUpdateCapaMutation,
  useChatMutation,
} = complaintsApi;
