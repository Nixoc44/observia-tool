import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { useEnvironments } from '../contexts/EnvironmentsContext';
import { useAIProviders } from '../contexts/AIProvidersContext';
import { useAnalyses } from '../contexts/AnalysesContext';
import { recommendationsApi } from '../services/api';
import type { Recommendation } from '../types';

function severityColor(severity: string) {
  switch (severity) {
    case 'critical': return 'bg-red-900 text-red-300';
    case 'high': return 'bg-orange-900 text-orange-300';
    default: return 'bg-gray-700 text-gray-300';
  }
}

export default function Dashboard() {
  const { environments, fetchEnvironments, loading: envLoading } = useEnvironments();
  const { providers, fetchProviders } = useAIProviders();
  const { analyses, fetchAnalyses, loading: analysesLoading } = useAnalyses();
  const [alerts, setAlerts] = useState<Recommendation[]>([]);
  const [alertsLoading, setAlertsLoading] = useState(false);

  useEffect(() => {
    fetchEnvironments();
    fetchProviders();
    fetchAnalyses({ limit: 5 });
  }, [fetchEnvironments, fetchProviders, fetchAnalyses]);

  useEffect(() => {
    setAlertsLoading(true);
    Promise.all([
      recommendationsApi.list({ severity: 'critical' }),
      recommendationsApi.list({ severity: 'high' }),
    ])
      .then(([critical, high]) => setAlerts([...critical, ...high].slice(0, 5)))
      .catch(() => setAlerts([]))
      .finally(() => setAlertsLoading(false));
  }, []);

  const stats = useMemo(() => {
    const completed = analyses.filter(a => a.status === 'completed').length;
    const failed = analyses.filter(a => a.status === 'failed').length;
    return { completed, failed };
  }, [analyses]);

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-semibold">Dashboard</h2>

      <div className="grid grid-cols-4 gap-4">
        <div className="bg-gray-900 rounded-lg p-4 border border-gray-800">
          <div className="text-gray-400 text-sm mb-1">Environments</div>
          <div className="text-3xl font-bold text-purple-400">{environments.length}</div>
        </div>
        <div className="bg-gray-900 rounded-lg p-4 border border-gray-800">
          <div className="text-gray-400 text-sm mb-1">AI Providers</div>
          <div className="text-3xl font-bold text-blue-400">{providers.length}</div>
        </div>
        <div className="bg-gray-900 rounded-lg p-4 border border-gray-800">
          <div className="text-gray-400 text-sm mb-1">Completed</div>
          <div className="text-3xl font-bold text-green-400">{stats.completed}</div>
        </div>
        <div className="bg-gray-900 rounded-lg p-4 border border-gray-800">
          <div className="text-gray-400 text-sm mb-1">Failed</div>
          <div className="text-3xl font-bold text-red-400">{stats.failed}</div>
        </div>
      </div>

      {(alertsLoading || alerts.length > 0) && (
        <div className="bg-gray-900 rounded-lg p-4 border border-red-900/50">
          <h3 className="text-lg font-semibold mb-4 text-red-300">Priority Recommendations</h3>
          {alertsLoading ? (
            <p className="text-gray-400 text-sm">Loading alerts...</p>
          ) : (
            <div className="space-y-2">
              {alerts.map(alert => (
                <Link
                  key={alert.id}
                  to={`/analyses/${alert.analysis_id}`}
                  className="flex items-center justify-between p-3 bg-gray-800 rounded hover:bg-gray-700 transition-colors"
                >
                  <div>
                    <div className="font-medium">{alert.title}</div>
                    <div className="text-sm text-gray-400 line-clamp-1">{alert.description}</div>
                  </div>
                  <span className={`px-2 py-1 rounded text-xs font-medium uppercase ${severityColor(alert.severity)}`}>
                    {alert.severity}
                  </span>
                </Link>
              ))}
            </div>
          )}
        </div>
      )}

      <div className="flex gap-3">
        <Link to="/environments" className="bg-purple-700 hover:bg-purple-600 px-4 py-2 rounded text-sm transition-colors">
          Manage Environments
        </Link>
        <Link to="/ai-providers" className="bg-blue-700 hover:bg-blue-600 px-4 py-2 rounded text-sm transition-colors">
          Configure AI Providers
        </Link>
        <Link to="/analyses" className="bg-green-700 hover:bg-green-600 px-4 py-2 rounded text-sm transition-colors">
          View Analyses
        </Link>
      </div>

      {envLoading && <p className="text-gray-400 text-sm">Loading...</p>}

      {!envLoading && (environments.length === 0 || providers.length === 0) && (
        <div className="bg-yellow-900/20 border border-yellow-800 rounded-lg p-4 text-yellow-300 text-sm">
          <strong>Get Started:</strong> Configure at least one Dynatrace environment and one AI provider to begin analyzing.
        </div>
      )}

      <div className="bg-gray-900 rounded-lg p-4 border border-gray-800">
        <h3 className="text-lg font-semibold mb-4">Recent Analyses</h3>
        {analysesLoading ? (
          <p className="text-gray-400 text-sm">Loading...</p>
        ) : analyses.length === 0 ? (
          <p className="text-gray-400 text-sm">No analyses yet. Start your first analysis to see results here.</p>
        ) : (
          <div className="space-y-2">
            {analyses.map(analysis => (
              <Link
                key={analysis.id}
                to={`/analyses/${analysis.id}`}
                className="flex items-center justify-between p-3 bg-gray-800 rounded hover:bg-gray-700 transition-colors"
              >
                <div>
                  <div className="font-medium">
                    {analysis.analysis_type.charAt(0).toUpperCase() + analysis.analysis_type.slice(1)} Analysis
                  </div>
                  <div className="text-sm text-gray-400">
                    Env #{analysis.environment_id} • {new Date(analysis.created_at).toLocaleDateString()}
                  </div>
                </div>
                <span className={`px-2 py-1 rounded text-xs font-medium ${
                  analysis.status === 'completed' ? 'bg-green-900 text-green-300' :
                  analysis.status === 'failed' ? 'bg-red-900 text-red-300' :
                  analysis.status === 'running' ? 'bg-blue-900 text-blue-300' :
                  'bg-yellow-900 text-yellow-300'
                }`}>
                  {analysis.status}
                </span>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
