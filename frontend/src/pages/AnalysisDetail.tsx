import { useCallback, useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAnalyses } from '../contexts/AnalysesContext';
import { recommendationsApi } from '../services/api';
import { downloadReportContent, reportsApi } from '../services/reports-api';
import type { Analysis, Recommendation, RecommendationStatus } from '../types';

function severityColor(severity: string) {
  switch (severity) {
    case 'critical': return 'bg-red-900 text-red-300';
    case 'high': return 'bg-orange-900 text-orange-300';
    case 'medium': return 'bg-yellow-900 text-yellow-300';
    default: return 'bg-gray-700 text-gray-300';
  }
}

function statusColor(status: string) {
  switch (status) {
    case 'completed': return 'bg-green-900 text-green-300';
    case 'failed': return 'bg-red-900 text-red-300';
    case 'running': return 'bg-blue-900 text-blue-300';
    default: return 'bg-gray-700 text-gray-300';
  }
}

export default function AnalysisDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { getAnalysis } = useAnalyses();
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState<'json' | 'markdown' | null>(null);
  const [error, setError] = useState('');

  const loadRecommendations = useCallback(async (analysisId: number) => {
    const recs = await recommendationsApi.list({ analysis_id: analysisId });
    setRecommendations(recs);
  }, []);

  useEffect(() => {
    if (!id) return;
    getAnalysis(Number(id))
      .then(async (data) => {
        setAnalysis(data);
        await loadRecommendations(data.id);
      })
      .catch(() => setError('Failed to load analysis'))
      .finally(() => setLoading(false));
  }, [id, getAnalysis, loadRecommendations]);

  const handleStatusUpdate = async (recId: number, newStatus: RecommendationStatus) => {
    await recommendationsApi.updateStatus(recId, newStatus);
    if (analysis) await loadRecommendations(analysis.id);
  };

  const handleExport = async (format: 'json' | 'markdown') => {
    if (!analysis) return;
    setExporting(format);
    try {
      const report = await reportsApi.generate({
        analysis_id: analysis.id,
        format,
        include_raw_data: format === 'json',
      });
      downloadReportContent(
        report.content,
        `analysis-${analysis.id}.${format === 'json' ? 'json' : 'md'}`,
        format === 'json' ? 'application/json' : 'text/markdown',
      );
    } catch {
      setError('Failed to export report.');
    } finally {
      setExporting(null);
    }
  };

  const copyScript = (script: string) => {
    navigator.clipboard.writeText(script);
  };

  if (loading) {
    return <div className="text-gray-400">Loading...</div>;
  }

  if (error && !analysis) {
    return (
      <div className="space-y-4">
        <p className="text-red-400">{error || 'Analysis not found'}</p>
        <button onClick={() => navigate('/analyses')} className="text-purple-400 hover:text-purple-300 text-sm">
          ← Back to Analyses
        </button>
      </div>
    );
  }

  if (!analysis) return null;

  return (
    <div className="space-y-6">
      <button onClick={() => navigate('/analyses')} className="text-purple-400 hover:text-purple-300 text-sm">
        ← Back to Analyses
      </button>

      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h2 className="text-2xl font-semibold">
            {analysis.analysis_type.charAt(0).toUpperCase() + analysis.analysis_type.slice(1)} Analysis
          </h2>
          <p className="text-gray-400 text-sm">
            Environment ID: {analysis.environment_id} | Created: {new Date(analysis.created_at).toLocaleString()}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {analysis.status === 'completed' && (
            <>
              <button
                onClick={() => handleExport('json')}
                disabled={exporting !== null}
                className="bg-gray-700 hover:bg-gray-600 disabled:opacity-50 px-3 py-1.5 rounded text-sm"
              >
                {exporting === 'json' ? 'Exporting...' : 'Export JSON'}
              </button>
              <button
                onClick={() => handleExport('markdown')}
                disabled={exporting !== null}
                className="bg-gray-700 hover:bg-gray-600 disabled:opacity-50 px-3 py-1.5 rounded text-sm"
              >
                {exporting === 'markdown' ? 'Exporting...' : 'Export Markdown'}
              </button>
            </>
          )}
          <span className={`text-sm px-3 py-1 rounded ${statusColor(analysis.status)}`}>
            {analysis.status}
          </span>
        </div>
      </div>

      {error && (
        <div className="bg-red-900/30 border border-red-800 rounded-lg p-3 text-red-300 text-sm">
          {error}
        </div>
      )}

      {analysis.error_message && (
        <div className="bg-red-900/30 border border-red-800 rounded-lg p-4">
          <h3 className="text-red-400 font-medium mb-2">Error</h3>
          <p className="text-red-300 text-sm">{analysis.error_message}</p>
        </div>
      )}

      {analysis.result && (
        <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
          <h3 className="text-lg font-medium mb-3">Result Summary</h3>
          <div className="prose prose-invert max-w-none">
            <p className="text-gray-300 whitespace-pre-wrap">{analysis.result.summary}</p>
          </div>
          {analysis.result.raw_data && analysis.result.raw_data.length > 0 && (
            <div className="mt-4">
              <h4 className="text-sm font-medium text-gray-400 mb-2">Raw Data</h4>
              <pre className="bg-gray-950 border border-gray-800 rounded p-3 text-xs text-gray-300 overflow-x-auto">
                {JSON.stringify(analysis.result.raw_data, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}

      {recommendations.length > 0 && (
        <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
          <h3 className="text-lg font-medium mb-3">Recommendations ({recommendations.length})</h3>
          <div className="space-y-3">
            {recommendations.map(rec => (
              <div key={rec.id} className="bg-gray-950 border border-gray-800 rounded p-4">
                <div className="flex items-start justify-between gap-4 mb-2">
                  <div>
                    <h4 className="font-medium">{rec.title}</h4>
                    <div className="flex gap-2 mt-1">
                      <span className={`text-xs px-2 py-0.5 rounded uppercase ${severityColor(rec.severity)}`}>
                        {rec.severity}
                      </span>
                      <span className="text-xs px-2 py-0.5 rounded bg-purple-900/50 text-purple-300">
                        {rec.level}
                      </span>
                      <span className="text-xs px-2 py-0.5 rounded bg-gray-800 text-gray-400">
                        {rec.status}
                      </span>
                    </div>
                  </div>
                  {rec.status === 'new' && (
                    <div className="flex gap-2 shrink-0">
                      <button
                        onClick={() => handleStatusUpdate(rec.id, 'acknowledged')}
                        className="text-xs bg-blue-800 hover:bg-blue-700 px-2 py-1 rounded"
                      >
                        Acknowledge
                      </button>
                      <button
                        onClick={() => handleStatusUpdate(rec.id, 'resolved')}
                        className="text-xs bg-green-800 hover:bg-green-700 px-2 py-1 rounded"
                      >
                        Resolve
                      </button>
                    </div>
                  )}
                  {rec.status === 'acknowledged' && (
                    <button
                      onClick={() => handleStatusUpdate(rec.id, 'resolved')}
                      className="text-xs bg-green-800 hover:bg-green-700 px-2 py-1 rounded shrink-0"
                    >
                      Resolve
                    </button>
                  )}
                </div>
                <p className="text-sm text-gray-300 mb-2">{rec.description}</p>
                {rec.impact && (
                  <p className="text-xs text-gray-400 mb-2"><strong>Impact:</strong> {rec.impact}</p>
                )}
                {rec.action && (
                  <p className="text-xs text-gray-300 mb-2"><strong>Action:</strong> {rec.action}</p>
                )}
                {rec.script && (
                  <div className="mt-2">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs text-gray-400">Script ({rec.script_type})</span>
                      <button
                        onClick={() => copyScript(rec.script!)}
                        className="text-xs text-purple-400 hover:text-purple-300"
                      >
                        Copy
                      </button>
                    </div>
                    <pre className="bg-gray-900 border border-gray-800 rounded p-2 text-xs text-gray-300 overflow-x-auto">
                      {rec.script}
                    </pre>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {analysis.reasoning_steps && analysis.reasoning_steps.length > 0 && (
        <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
          <h3 className="text-lg font-medium mb-3">Reasoning Steps</h3>
          <div className="space-y-3">
            {analysis.reasoning_steps.map((step, idx) => (
              <div key={idx} className="bg-gray-950 border border-gray-800 rounded p-3">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-xs font-mono text-purple-400">{step.type || 'step'}</span>
                  {step.tool && (
                    <span className="text-xs text-gray-500">via {step.tool}</span>
                  )}
                </div>
                <p className="text-sm text-gray-300 whitespace-pre-wrap">{step.content}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {!analysis.result && recommendations.length === 0 && !analysis.reasoning_steps?.length && !analysis.error_message && analysis.status !== 'running' && (
        <p className="text-gray-500 text-sm">No results available yet.</p>
      )}
    </div>
  );
}
