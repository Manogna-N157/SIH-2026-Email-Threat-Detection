import React, { useEffect, useState } from 'react';
import { getCases } from '../api';
import Badge from '../components/Badge';
import { Mail, AlertTriangle, ShieldCheck, ArrowRight, RefreshCw } from 'lucide-react';

export default function DashboardPage({ navigateToInvestigate, onSelectCase }) {
  const [cases, setCases] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const fetchDashboardData = async () => {
    setLoading(true);
    setError('');
    try {
      const data = await getCases();
      setCases(data || []);
    } catch (err) {
      console.warn('Dashboard cases fetch notice:', err.message);
      setError('Could not fetch stored cases from backend. (Is FastAPI backend running?)');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, []);

  // Compute metric numbers strictly following data rules:
  const totalAnalyzed = cases.length;
  
  // High Risk Cases MUST be calculated strictly from the backend's risk_level
  // (risk_level === 'HIGH' or 'CRITICAL', case-insensitive), NOT from classification or risk_score.
  const highRiskCount = cases.filter(c => {
    const rawLevel = c.risk_level || c.analysis?.risk_level;
    if (!rawLevel) return false;
    const upper = String(rawLevel).trim().toUpperCase();
    return upper === 'HIGH' || upper === 'CRITICAL';
  }).length;

  const threatsDetected = cases.filter(c => (c.indicators || []).length > 0 || (c.classification && c.classification !== 'LEGITIMATE')).length;

  const formatConfidence = (val) => {
    if (val === null || val === undefined || val === '') return 'N/A';
    return `${val}%`;
  };

  return (
    <div className="page-container">
      {/* Overview Banner */}
      <div className="card overview-banner">
        <h2>AI-Powered Email Threat Detection, GeoLocation and Forensic Intelligence Platform</h2>
        <p>
          Comprehensive analysis platform for inspecting .eml headers, verifying SPF/DKIM/DMARC authentication, 
          detecting threat vectors, mapping probable infrastructure locations, and building graph intelligence.
        </p>
        <button className="btn btn-primary" onClick={navigateToInvestigate}>
          <Mail size={16} /> Investigate New .EML File
        </button>
      </div>

      {/* Metrics Cards */}
      <div className="metrics-grid">
        <div className="card metric-card">
          <div className="metric-icon blue">
            <Mail size={24} />
          </div>
          <div className="metric-info">
            <span className="metric-label">Emails Analyzed</span>
            <span className="metric-value">{loading ? '...' : totalAnalyzed}</span>
          </div>
        </div>

        <div className="card metric-card">
          <div className="metric-icon red">
            <AlertTriangle size={24} />
          </div>
          <div className="metric-info">
            <span className="metric-label">High Risk Cases</span>
            <span className="metric-value">{loading ? '...' : highRiskCount}</span>
          </div>
        </div>

        <div className="card metric-card">
          <div className="metric-icon orange">
            <ShieldCheck size={24} />
          </div>
          <div className="metric-info">
            <span className="metric-label">Threats Detected</span>
            <span className="metric-value">{loading ? '...' : threatsDetected}</span>
          </div>
        </div>
      </div>

      {/* Recent Cases Section */}
      <div className="card">
        <div className="card-header">
          <h3>Recent Cases</h3>
          <button className="btn btn-secondary btn-sm" onClick={fetchDashboardData}>
            <RefreshCw size={14} /> Refresh
          </button>
        </div>

        {error && <div className="alert alert-warning">{error}</div>}

        {loading ? (
          <p className="loading-text">Loading recent cases...</p>
        ) : cases.length === 0 ? (
          <div className="empty-state">
            <p>No cases analyzed yet. Start by uploading an .eml file on the Investigate page.</p>
            <button className="btn btn-primary" onClick={navigateToInvestigate}>
              Go to Investigate Email
            </button>
          </div>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Case ID</th>
                <th>Filename / Subject</th>
                <th>Risk Score</th>
                <th>Risk Level</th>
                <th>Classification</th>
                <th>Confidence</th>
                <th>Date</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {cases.slice(0, 5).map(c => {
                const riskLevel = c.risk_level || c.analysis?.risk_level;
                const confVal = c.confidence ?? c.analysis?.confidence;
                return (
                  <tr key={c.case_id}>
                    <td><code>{c.case_id}</code></td>
                    <td>{c.filename || c.summary || 'Email Analysis'}</td>
                    <td>
                      <span className={`risk-score-pill score-${c.risk_score >= 70 ? 'high' : c.risk_score >= 40 ? 'med' : 'low'}`}>
                        {c.risk_score ?? 'N/A'}/100
                      </span>
                    </td>
                    <td>
                      {riskLevel ? <Badge type="risk_level" value={riskLevel} /> : <span className="text-muted">N/A</span>}
                    </td>
                    <td><Badge type="classification" value={c.classification} /></td>
                    <td>{formatConfidence(confVal)}</td>
                    <td>{c.timestamp ? new Date(c.timestamp).toLocaleString() : 'N/A'}</td>
                    <td>
                      <button className="btn btn-secondary btn-sm" onClick={() => onSelectCase(c)}>
                        View <ArrowRight size={12} />
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
