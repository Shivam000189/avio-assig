export type Severity = 'Critical' | 'Major' | 'Minor';
export type ComplaintStatus = 'Open' | 'InProgress' | 'Closed';
export type ComplaintType =
  | 'AdverseEvent'
  | 'QualityDefect'
  | 'LabelingIssue'
  | 'PackagingIssue'
  | 'DeliveryIssue'
  | 'Other';
export type ComplaintSource = 'Manual' | 'PDF' | 'Email';
export type CapaStatus = 'Recommended' | 'InProgress' | 'Implemented' | 'Verified' | 'Closed';
export type CapaActionType = 'Corrective' | 'Preventive';

export interface ComplaintDocument {
  id: string;
  complaintId: string;
  filename: string;
  fileType: string;
  extractedText?: string | null;
  uploadedAt: string;
}

export interface CAPA {
  id?: string;
  complaintId?: string;
  actionType: CapaActionType | string;
  recommendedAction: string;
  actionOwner?: string | null;
  dueDate?: string | null;
  capaStatus?: CapaStatus | string;
}

export interface ComplaintSummary {
  id?: string;
  complaintId?: string;
  summaryText: string;
  generatedAt?: string;
}

export interface Complaint {
  id: string;
  complaintNumber: string;
  complainantName: string;
  email?: string | null;
  phone?: string | null;
  productName: string;
  batchNumber: string;
  expiryDate?: string | null;
  manufactureDate?: string | null;
  complaintType: ComplaintType | string;
  description: string;
  severity?: Severity | string | null;
  status: ComplaintStatus | string;
  source: ComplaintSource | string;
  country?: string | null;
  aiSummary?: string | null;
  rootCause?: string | null;
  createdAt: string;
  updatedAt: string;
  documents?: ComplaintDocument[];
  capa?: CAPA | null;
  summary?: ComplaintSummary | null;
}

export interface PaginatedComplaintsResponse {
  total: number;
  skip: number;
  limit: number;
  items: Complaint[];
}

export interface ComplaintStatsResponse {
  total: number;
  byStatus: Record<string, number>;
  bySeverity: Record<string, number>;
  openByType: Record<string, number>;
}

export interface PotentialDuplicateInfo {
  complaintId?: string | null;
  complaintNumber?: string | null;
  similarity: 'High' | 'Medium' | 'Low' | string;
  explanation?: string | null;
  isPossibleTrend?: boolean;
}

export interface DocumentMetadata {
  filename: string;
  fileType: string;
  metadata?: Record<string, any>;
}

export interface ExtractedComplaintData {
  complainantName: string;
  email?: string | null;
  phone?: string | null;
  productName: string;
  batchNumber: string;
  expiryDate?: string | null;
  manufactureDate?: string | null;
  complaintType: string;
  description: string;
  country?: string | null;
}

export interface AnalysisResponse {
  rawInput: string;
  source: string;
  extracted?: ExtractedComplaintData | Record<string, any> | null;
  missingFields: string[];
  isComplete: boolean;
  summary?: string | null;
  severity?: Severity | string | null;
  riskReasoning?: string | null;
  recommendedSlaDays?: number | null;
  capaRecommendation?: string | null;
  capaActionType?: CapaActionType | string | null;
  rootCause?: string | null;
  duplicateOf?: string | null;
  potentialDuplicate?: PotentialDuplicateInfo | null;
  duplicateChecked: boolean;
  warnings: string[];
  document?: DocumentMetadata | null;
}

export interface CreateFromAnalysisPayload {
  extracted: ExtractedComplaintData;
  severity?: string | null;
  summary?: string | null;
  capaRecommendation?: string | null;
  capaActionType?: string | null;
  rootCause?: string | null;
  source?: string;
  status?: string;
  documentId?: string | null;
}
