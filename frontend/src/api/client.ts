import type {
  AnalysisResponse,
  Complaint,
  ComplaintStatsResponse,
  CreateFromAnalysisPayload,
  PaginatedComplaintsResponse,
} from './types';

const API_BASE = '/api/v1';

export class ApiError extends Error {
  status: number;
  data: any;
  constructor(message: string, status: number, data?: any) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let errorData: any = null;
    try {
      errorData = await response.json();
    } catch {
      errorData = await response.text();
    }
    const message =
      (errorData && (errorData.detail || errorData.message || errorData.error)) ||
      `Request failed with status ${response.status}`;
    throw new ApiError(typeof message === 'string' ? message : JSON.stringify(message), response.status, errorData);
  }
  if (response.status === 204) {
    return {} as T;
  }
  return response.json();
}

export const api = {
  // Health
  async getHealth(): Promise<{ status: string; app: string; version: string }> {
    const res = await fetch('/health');
    return handleResponse(res);
  },

  // Analytics Stats
  async getStats(): Promise<ComplaintStatsResponse> {
    const res = await fetch(`${API_BASE}/complaints/stats`);
    return handleResponse(res);
  },

  // List Complaints with Filters
  async getComplaints(params?: {
    skip?: number;
    limit?: number;
    search?: string;
    status?: string;
    severity?: string;
    complaintType?: string;
  }): Promise<PaginatedComplaintsResponse> {
    const query = new URLSearchParams();
    if (params?.skip !== undefined) query.set('skip', params.skip.toString());
    if (params?.limit !== undefined) query.set('limit', params.limit.toString());
    if (params?.search) query.set('search', params.search);
    if (params?.status) query.set('status', params.status);
    if (params?.severity) query.set('severity', params.severity);
    if (params?.complaintType) query.set('complaintType', params.complaintType);

    const url = `${API_BASE}/complaints${query.toString() ? `?${query.toString()}` : ''}`;
    const res = await fetch(url);
    return handleResponse(res);
  },

  // Get Single Complaint by ID
  async getComplaint(id: string): Promise<Complaint> {
    const res = await fetch(`${API_BASE}/complaints/${id}`);
    return handleResponse(res);
  },

  // Create Complaint (Direct Manual Entry)
  async createComplaint(payload: Partial<Complaint>): Promise<Complaint> {
    const res = await fetch(`${API_BASE}/complaints`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    return handleResponse(res);
  },

  // Update Complaint
  async updateComplaint(id: string, payload: Partial<Complaint>): Promise<Complaint> {
    const res = await fetch(`${API_BASE}/complaints/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    return handleResponse(res);
  },

  // Delete Complaint
  async deleteComplaint(id: string): Promise<void> {
    const res = await fetch(`${API_BASE}/complaints/${id}`, {
      method: 'DELETE',
    });
    return handleResponse(res);
  },

  // AI Analyze Raw Text
  async analyzeText(text: string, source: string = 'Manual'): Promise<AnalysisResponse> {
    const res = await fetch(`${API_BASE}/complaints/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, source }),
    });
    return handleResponse(res);
  },

  // AI Analyze Uploaded File (PDF, TXT, EML)
  async analyzeFile(file: File, complaintId?: string): Promise<AnalysisResponse> {
    const formData = new FormData();
    formData.append('file', file);
    if (complaintId) {
      formData.append('complaint_id', complaintId);
    }
    const res = await fetch(`${API_BASE}/complaints/analyze-file`, {
      method: 'POST',
      body: formData,
    });
    return handleResponse(res);
  },

  // Save Complaint from AI Analysis (Atomic commit with Summary + CAPA)
  async saveFromAnalysis(payload: CreateFromAnalysisPayload): Promise<Complaint> {
    const res = await fetch(`${API_BASE}/complaints/from-analysis`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    return handleResponse(res);
  },

  // Generate AI Insights on an Already-Saved Complaint
  async generateAiInsights(complaintId: string): Promise<Complaint> {
    const res = await fetch(`${API_BASE}/complaints/${complaintId}/ai-insights`, {
      method: 'POST',
    });
    return handleResponse(res);
  },
};
