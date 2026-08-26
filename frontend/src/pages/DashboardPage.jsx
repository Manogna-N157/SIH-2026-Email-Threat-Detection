import React, { useEffect, useState } from 'react';
import {
  Mail,
  AlertTriangle,
  ShieldCheck,
  ArrowRight,
  RefreshCw,
} from 'lucide-react';
import Badge from '../components/Badge';
import { Mail, AlertTriangle, ShieldCheck, ArrowRight, RefreshCw, Shield, ShieldAlert, CheckCircle } from 'lucide-react';

const demoCases = [
  {
    case_id: 'CASE-001',
    filename: 'invoice_payment.eml',
    risk_score: 92,
    risk_level: 'CRITICAL',
    classification: 'PHISHING',
    confidence: 96,
    timestamp: '2026-08-26T10:32:00',
  },
  {
    case_id: 'CASE-002',
    filename: 'account_verification.eml',
    risk_score: 78,
    risk_level: 'HIGH',
    classification: 'MALICIOUS',
    confidence: 91,
    timestamp: '2026-08-26T09:48:00',
  },
  {
    case_id: 'CASE-003',
    filename: 'meeting_invitation.eml',
    risk_score: 34,
    risk_level: 'LOW',
    classification: 'SUSPICIOUS',
    confidence: 82,
    timestamp: '2026-08-26T09:15:00',
  },
  {
    case_id: 'CASE-004',
    filename: 'hr_document.eml',
    risk_score: 12,
    risk_level: 'LOW',
    classification: 'LEGITIMATE',
    confidence: 98,
    timestamp: '2026-08-26T08:42:00',
  },
  {
    case_id: 'CASE-005',
    filename: 'password_reset.eml',
    risk_score: 86,
    risk_level: 'HIGH',
    classification: 'PHISHING',
    confidence: 94,
    timestamp: '2026-08-26T08:10:00',
  },
];

export default function DashboardPage({
  navigateToInvestigate,
  onSelectCase,
}) {
  const [cases, setCases] = useState(demoCases);
  const [loading, setLoading] = useState(false);

  const fetchDashboardData = () => {
    // Frontend-only demo mode.
    // Backend integration can be restored later.
    setLoading(true);

    setTimeout(() => {
      setCases(demoCases);
      setLoading(false);
    }, 400);
  };

  useEffect(() => {
    setCases(demoCases);
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

  const formatConfidence = (value) => {
    if (value === null || value === undefined) return 'N/A';
    return `${value}%`;
  };

  return (
    <div className="page-container">

      {/* Hero Banner */}
      <div className="card overview-banner">
        <div>
          <h2>
            AI-Powered Email Threat Detection, GeoLocation and
            Forensic Intelligence Platform
          </h2>

          <p>
            Comprehensive analysis platform for inspecting .eml headers,
            verifying SPF/DKIM/DMARC authentication, detecting threat
            vectors, mapping probable infrastructure locations, and
            building graph intelligence.
          </p>

          <button
            className="btn btn-primary"
            onClick={navigateToInvestigate}
          >
            <Mail size={16} />
            Investigate New .EML File
          </button>
        </div>
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
        </div>

      </div>

      {/* Recent Cases */}
      <div className="card">

        <div className="card-header">
          <div>
            <h3>Recent Investigative Cases</h3>
            <p className="subtitle">
              Latest email forensic investigations
            </p>
          </div>

          <button
            className="btn btn-secondary btn-sm"
            onClick={fetchDashboardData}
          >
            <RefreshCw size={14} />
            Refresh
          </button>
        </div>

        {loading ? (
          <p className="loading-text">
            Loading recent cases...
          </p>
        ) : (
          <div className="table-container">
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
                {cases.slice(0, 5).map((c) => (
                  <tr key={c.case_id}>

                    <td>
                    <td>
                      <code>{c.case_id}</code>
                    </td>
                    <td>
                      {c.filename}
                    </td>
                    <td>
                      <span className={`risk-score-pill score-${c.risk_score >= 75 ? 'high' : c.risk_score >= 50 ? 'med' : 'low'}`}>
                        {c.risk_score ?? 'N/A'}/100
                      </span>
                      </span>
                    </td>

                    <td>
                      <Badge
                        type="risk_level"
                        value={c.risk_level}
                      />
                    </td>

                    <td>
                      <Badge
                        type="classification"
                        value={c.classification}
                      />
                    </td>

                    <td>
                      {formatConfidence(c.confidence)}
                    </td>

                    <td>
                      {new Date(c.timestamp).toLocaleString()}
                    </td>

                    <td>
                      <button
                        className="btn btn-secondary btn-sm"
                        onClick={() => onSelectCase(c)}
                      >
                        View
                        <ArrowRight size={12} />
                      </button>
                    </td>

                  </tr>
                ))}
              </tbody>

            </table>
          </div>
        )}

      </div>

    </div>
  );
}