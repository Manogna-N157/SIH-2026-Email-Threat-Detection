import React, { useEffect, useState } from 'react';
import { getCases } from '../api';
import Badge from '../components/Badge';
import { Mail, AlertTriangle, ShieldCheck, ArrowRight, RefreshCw, Shield, ShieldAlert, CheckCircle } from 'lucide-react';

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

  // Compute metric numbers strictly following backend risk_level rules:
  const totalAnalyzed = cases.length;
  
  const highRiskCount = cases.filter(c => {
    const rawLevel = c.risk_level || c.analysis?.risk_level;
    if (!rawLevel) return false;
    const upper = String(rawLevel).trim().toUpperCase();
    return upper === 'HIGH' || upper === 'CRITICAL';
  }).length;

  const mediumRiskCount = cases.filter(c => {
    const rawLevel = c.risk_level || c.analysis?.risk_level;
    if (!rawLevel) return false;
    return String(rawLevel).trim().toUpperCase() === 'MEDIUM';
  }).length;

  const lowRiskCount = cases.filter(c => {
    const rawLevel = c.risk_level || c.analysis?.risk_level;
    if (!rawLevel) return false;
    return String(rawLevel).trim().toUpperCase() === 'LOW';
  }).length;

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
      <div className="metrics-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))' }}>
        <div className="card metric-card">
          <div className="metric-icon blue">
            <Mail size={24} />
          </div>
          <div className="metric-info">
            <span className="metric-label">Total Cases</span>
            <span className="metric-value">{loading ? '...' : totalAnalyzed}</span>
          </div>
        </div>

        <div className="card metric-card">
          <div className="metric-icon red">
            <ShieldAlert size={24} />
          </div>
          <div className="metric-info">
            <span className="metric-label">High Risk Cases (75-100)</span>
            <span className="metric-value">{loading ? '...' : highRiskCount}</span>
          </div>
        </div>

        <div className="card metric-card">
          <div className="metric-icon orange">
            <AlertTriangle size={24} />
          </div>
          <div className="metric-info">
            <span className="metric-label">Medium Risk Cases (50-74)</span>
            <span className="metric-value">{loading ? '...' : mediumRiskCount}</span>
          </div>
        </div>

        <div className="card metric-card">
          <div className="metric-icon green" style={{ background: '#dcfce7', color: '#15803d' }}>
            <CheckCircle size={24} />
          </div>
          <div className="metric-info">
            <span className="metric-label">Low Risk Cases (0-49)</span>
            <span className="metric-value">{loading ? '...' : lowRiskCount}</span>
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
                      <span className={`risk-score-pill score-${c.risk_score >= 75 ? 'high' : c.risk_score >= 50 ? 'med' : 'low'}`}>
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
