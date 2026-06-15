import axios from 'axios';

export interface ReportSummary {
  total_analyses: number;
  completed: number;
  failed: number;
  success_rate: number;
  average_duration: number;
  most_common_errors: string[];
  recommendations_generated: number;
}

export interface ChartData {
  date: string;
  count: number;
}

export interface ProviderUsage {
  provider: string;
  count: number;
}

export interface ReportGenerateRequest {
  analysis_id: number;
  format: 'json' | 'markdown';
  include_raw_data?: boolean;
}

export interface GeneratedReport {
  id: number;
  analysis_id: number;
  format: string;
  content: string;
  include_raw_data: boolean;
}

const client = axios.create({ baseURL: '/api/v1' });

export function downloadReportContent(content: string, filename: string, mimeType: string) {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export const reportsApi = {
  getSummary: async (days: number = 30): Promise<ReportSummary> => {
    const { data } = await client.get('/reports/summary', { params: { days } });
    return data;
  },
  getTimeline: async (days: number = 30): Promise<ChartData[]> => {
    const { data } = await client.get('/reports/analytics', { params: { days, type: 'timeline' } });
    return data;
  },
  getProviderUsage: async (days: number = 30): Promise<ProviderUsage[]> => {
    const { data } = await client.get('/reports/analytics', { params: { days, type: 'providers' } });
    return data;
  },
  generate: async (request: ReportGenerateRequest): Promise<GeneratedReport> => {
    const { data } = await client.post('/reports/generate', request);
    return data;
  },
};
