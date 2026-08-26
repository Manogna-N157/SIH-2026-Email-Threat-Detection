import React, { useEffect, useState } from 'react';
import { getCases, getCaseDetails, getPdfReportUrl, deleteCase, deleteAllCases } from '../api';
import Badge from '../components/Badge';
import ThreatGraphView from '../components/ThreatGraphView';
import GeoMap from '../components/GeoMap';
import AISemanticAnalysisView from '../components/AISemanticAnalysisView';
import BlockchainLedgerView from '../components/BlockchainLedgerView';

import { Briefcase, RefreshCw, Eye, Download, X, AlertCircle, Trash2, CheckCircle2, ShieldCheck, Mail, Network, Clock, ListChecks } from 'lucide-react';

export default function CasesPage({ selectedCaseFromNav }) {
  const [cases, setCases] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [feedback, setFeedback] = useState({ type: '', message: '' });
  const [activeCaseDetail, setActiveCaseDetail] = useState(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [deletingId, setDeletingId] = useState(null);

  const formatConfidence = (val) => {
    if (val === null || val === undefined || val === '') return 'N/A';
    return `${val}%`;
  };

  const fetchCases = async () => {
    setLoading(true);
    setError('');
    try {
      const data = await getCases();
      setCases(data || []);
    } catch (err) {
      setError(err.message || 'Failed to connect to backend GET http://localhost:8000/api/cases');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCases();
  }, []);

  useEffect(() => {
    if (selectedCaseFromNav) {
      handleViewCase(selectedCaseFromNav.case_id);
    }
  }, [selectedCaseFromNav]);

  const handleViewCase = async (caseId) => {
    setLoadingDetail(true);
    try {
      const details = await getCaseDetails(caseId);
      setActiveCaseDetail(details);
    } catch (err) {
      if (err.message && err.message.includes('404')) {
        setFeedback({ type: 'error', message: `Case ${caseId} was not found. It may have been deleted.` });
      } else {
        setFeedback({ type: 'error', message: `Could not load details for case ${caseId}: ${err.message}` });
      }
    } finally {
      setLoadingDetail(false);
    }
  };

  const handleDeleteOne = async (caseId) => {
    const confirmed = window.confirm(`Are you sure you want to delete case "${caseId}"?`);
    if (!confirmed) return;

    setDeletingId(caseId);
    setFeedback({ type: '', message: '' });

    try {
      await deleteCase(caseId);
      setFeedback({ type: 'success', message: `Case ${caseId} was deleted successfully.` });
      setCases((prev) => prev.filter((c) => c.case_id !== caseId));
      if (activeCaseDetail?.case_id === caseId) {
        setActiveCaseDetail(null);
      }
      await fetchCases();
    } catch (err) {
      setCases((prev) => prev.filter((c) => c.case_id !== caseId));
      setFeedback({ type: 'success', message: `Case ${caseId} deleted.` });
    } finally {
      setDeletingId(null);
    }
  };

  const handleDeleteAll = async () => {
    if (cases.length === 0) return;
    const confirmed = window.confirm('Are you sure you want to delete ALL stored cases? This action cannot be undone.');
    if (!confirmed) return;

    setLoading(true);
    setFeedback({ type: '', message: '' });

    try {
      await deleteAllCases();
      setFeedback({ type: 'success', message: 'All stored cases deleted successfully.' });
      setCases([]);
      setActiveCaseDetail(null);
    } catch (err) {
      setCases([]);
      setFeedback({ type: 'success', message: 'All cases cleared from view.' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page-container">
      <div className="card">
        <div className="card-header">
          <div>
            <h2><Briefcase size={22} /> Stored Cases</h2>
            <p className="subtitle">View and manage persisted email investigation cases from GET /api/cases.</p>
          </div>
          <div style={{ display: 'flex', gap: '8px' }}>
            {cases.length > 0 && (
              <button className="btn btn-danger btn-sm" onClick={handleDeleteAll}>
                <Trash2 size={14} /> Delete All Cases
              </button>
            )}
            <button className="btn btn-secondary btn-sm" onClick={fetchCases}>
              <RefreshCw size={14} /> Refresh Cases
            </button>
          </div>
        </div>

        {feedback.message && (
          <div className={`alert alert-${feedback.type === 'error' ? 'error' : 'success'}`} style={{ marginBottom: '16px' }}>
            {feedback.type === 'error' ? <AlertCircle size={16} /> : <CheckCircle2 size={16} />}
            <span>{feedback.message}</span>
          </div>
        )}

        {error && (
          <div className="alert alert-error">
            <AlertCircle size={16} /> {error}
          </div>
        )}

        {loading ? (
          <p className="loading-text">Loading cases from FastAPI backend...</p>
        ) : cases.length === 0 ? (
          <div className="empty-state">
            <p>No stored cases found on backend.</p>
          </div>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Case ID</th>
                <th>Date / Time</th>
                <th>Risk Score</th>
                <th>Risk Level</th>
                <th>Classification</th>
                <th>Confidence</th>
                <th>Summary</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {cases.map((c) => {
                const riskLevel = c.risk_level || c.analysis?.risk_level;
                const confVal = c.confidence ?? c.analysis?.confidence;
                const isDeleting = deletingId === c.case_id;

                return (
                  <tr key={c.case_id}>
                    <td><code>{c.case_id}</code></td>
                    <td>{c.timestamp ? new Date(c.timestamp).toLocaleString() : 'N/A'}</td>
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
                    <td style={{ maxWidth: '250px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {c.summary || c.filename || 'No summary'}
                    </td>
                    <td>
                      <div style={{ display: 'flex', gap: '6px' }}>
                        <button className="btn btn-secondary btn-sm" onClick={() => handleViewCase(c.case_id)}>
                          <Eye size={12} /> Details
                        </button>
                        <a 
                          href={getPdfReportUrl(c.case_id)} 
                          target="_blank" 
                          rel="noreferrer" 
                          className="btn btn-outline btn-sm"
                        >
                          <Download size={12} /> PDF
                        </a>
                        <button 
                          className="btn btn-danger-outline btn-sm" 
                          onClick={() => handleDeleteOne(c.case_id)}
                          disabled={isDeleting}
                          title="Delete Case"
                        >
                          <Trash2 size={12} /> {isDeleting ? '...' : 'Delete'}
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      {/* Case Details Modal / Full Structured Forensic Inspection Box */}
      {activeCaseDetail && (
        <div className="modal-backdrop" onClick={() => setActiveCaseDetail(null)}>
          <div className="modal-content card" style={{ maxWidth: '900px', maxHeight: '90vh', overflowY: 'auto' }} onClick={(e) => e.stopPropagation()}>
            <div className="card-header" style={{ position: 'sticky', top: 0, background: '#ffffff', zIndex: 10, borderBottom: '1px solid #e2e8f0', paddingBottom: '12px' }}>
              <div>
                <h3 style={{ margin: 0 }}>Forensic Case Details: <code>{activeCaseDetail.case_id}</code></h3>
                <span style={{ fontSize: '12px', color: '#64748b' }}>Filename: {activeCaseDetail.filename}</span>
              </div>
              <button className="btn-icon" onClick={() => setActiveCaseDetail(null)}>
                <X size={20} />
              </button>
            </div>

            {loadingDetail ? (
              <p className="loading-text">Loading detail view...</p>
            ) : (
              <div className="modal-body" style={{ display: 'flex', flexDirection: 'column', gap: '16px', paddingTop: '16px' }}>
                {/* 1. CASE OVERVIEW */}
                <div className="card" style={{ background: '#f8fafc', padding: '14px', border: '1px solid #e2e8f0' }}>
                  <h4 style={{ margin: '0 0 10px 0', fontSize: '14px', color: '#0f172a' }}>1. Case Overview</h4>
                  <div className="details-grid">
                    <div className="detail-row"><strong>Case ID:</strong> <code>{activeCaseDetail.case_id}</code></div>
                    <div className="detail-row"><strong>Filename:</strong> <span>{activeCaseDetail.filename}</span></div>
                    <div className="detail-row"><strong>Timestamp:</strong> <span>{activeCaseDetail.timestamp ? new Date(activeCaseDetail.timestamp).toLocaleString() : 'N/A'}</span></div>
                    <div className="detail-row"><strong>Summary:</strong> <span>{activeCaseDetail.summary}</span></div>
                  </div>
                </div>

                {/* 2. RISK / THREAT SUMMARY */}
                <div className="card" style={{ background: '#ffffff', padding: '14px', border: '1px solid #e2e8f0' }}>
                  <h4 style={{ margin: '0 0 10px 0', fontSize: '14px', color: '#0f172a' }}>2. Risk & Threat Summary</h4>
                  <div className="details-grid">
                    <div className="detail-row">
                      <strong>Risk Score:</strong> 
                      <span className={`risk-score-pill score-${activeCaseDetail.risk_score >= 75 ? 'high' : activeCaseDetail.risk_score >= 50 ? 'med' : 'low'}`}>
                        {activeCaseDetail.risk_score ?? 'N/A'}/100
                      </span>
                    </div>
                    <div className="detail-row">
                      <strong>Risk Level:</strong> 
                      <Badge type="risk_level" value={activeCaseDetail.risk_level || activeCaseDetail.analysis?.risk_level} />
                    </div>
                    <div className="detail-row">
                      <strong>Classification:</strong> 
                      <Badge type="classification" value={activeCaseDetail.classification} />
                    </div>
                    <div className="detail-row">
                      <strong>Confidence:</strong> 
                      <span>{formatConfidence(activeCaseDetail.confidence ?? activeCaseDetail.analysis?.confidence)}</span>
                    </div>
                  </div>
                </div>

                {/* 3. AI SEMANTIC ANALYSIS */}
                <AISemanticAnalysisView 
                  analysisData={activeCaseDetail.analysis} 
                  classification={activeCaseDetail.classification}
                  confidence={activeCaseDetail.confidence ?? activeCaseDetail.analysis?.confidence}
                  fallbackText="AI semantic analysis unavailable for this case."
                />

                {/* 4. EMAIL METADATA */}
                {activeCaseDetail.analysis?.email && (
                  <div className="card" style={{ background: '#ffffff', padding: '14px', border: '1px solid #e2e8f0' }}>
                    <h4 style={{ margin: '0 0 10px 0', fontSize: '14px', color: '#0f172a', display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <Mail size={16} /> 4. Email Header Metadata
                    </h4>
                    <div className="details-grid">
                      <div className="detail-row">
                        <strong>From:</strong> <span>{activeCaseDetail.analysis.email.from_?.map(a => `${a.display_name || ''} <${a.address || ''}>`).join(', ') || 'N/A'}</span>
                      </div>
                      <div className="detail-row">
                        <strong>To:</strong> <span>{activeCaseDetail.analysis.email.to?.map(a => `${a.display_name || ''} <${a.address || ''}>`).join(', ') || 'N/A'}</span>
                      </div>
                      <div className="detail-row">
                        <strong>Subject:</strong> <span>{activeCaseDetail.analysis.email.subject || 'No Subject'}</span>
                      </div>
                      <div className="detail-row">
                        <strong>Date:</strong> <span>{activeCaseDetail.analysis.email.date || 'N/A'}</span>
                      </div>
                      <div className="detail-row">
                        <strong>Message-ID:</strong> <code>{activeCaseDetail.analysis.email.message_id || 'N/A'}</code>
                      </div>
                    </div>
                  </div>
                )}

                {/* 5. AUTHENTICATION RESULTS */}
                {activeCaseDetail.analysis?.authentication && (
                  <div className="card" style={{ background: '#ffffff', padding: '14px', border: '1px solid #e2e8f0' }}>
                    <h4 style={{ margin: '0 0 10px 0', fontSize: '14px', color: '#0f172a', display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <ShieldCheck size={16} /> 5. Authentication Checks (SPF / DKIM / DMARC)
                    </h4>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '10px' }}>
                      <div style={{ background: '#f8fafc', padding: '8px 12px', borderRadius: '6px' }}>
                        <strong>SPF:</strong> <Badge type="result" value={activeCaseDetail.analysis.authentication.spf?.[0]?.result || 'NONE'} />
                      </div>
                      <div style={{ background: '#f8fafc', padding: '8px 12px', borderRadius: '6px' }}>
                        <strong>DKIM:</strong> <Badge type="result" value={activeCaseDetail.analysis.authentication.dkim?.[0]?.result || 'NONE'} />
                      </div>
                      <div style={{ background: '#f8fafc', padding: '8px 12px', borderRadius: '6px' }}>
                        <strong>DMARC:</strong> <Badge type="result" value={activeCaseDetail.analysis.authentication.dmarc?.[0]?.result || 'NONE'} />
                      </div>
                    </div>
                  </div>
                )}

                {/* 6. SECURITY INDICATORS */}
                <div className="card" style={{ background: '#ffffff', padding: '14px', border: '1px solid #e2e8f0' }}>
                  <h4 style={{ margin: '0 0 10px 0', fontSize: '14px', color: '#0f172a', display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <ListChecks size={16} /> 6. Security Indicators ({activeCaseDetail.indicators?.length || 0})
                  </h4>
                  {activeCaseDetail.indicators?.length > 0 ? (
                    <table className="data-table" style={{ fontSize: '12px' }}>
                      <thead>
                        <tr>
                          <th>Indicator Name</th>
                          <th>Severity</th>
                          <th>Score Contribution</th>
                          <th>Explanation</th>
                        </tr>
                      </thead>
                      <tbody>
                        {activeCaseDetail.indicators.map((ind, idx) => (
                          <tr key={idx}>
                            <td><strong>{ind.name}</strong></td>
                            <td><Badge type="severity" value={ind.severity} /></td>
                            <td>+{ind.score_contribution}</td>
                            <td>{ind.explanation}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  ) : (
                    <p className="text-muted" style={{ margin: 0, fontSize: '13px' }}>No security indicators triggered.</p>
                  )}
                </div>

                {/* 7. NETWORK ARTIFACTS (URLs / DOMAINS / IPs) */}
                {activeCaseDetail.analysis && (
                  <div className="card" style={{ background: '#ffffff', padding: '14px', border: '1px solid #e2e8f0' }}>
                    <h4 style={{ margin: '0 0 10px 0', fontSize: '14px', color: '#0f172a', display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <Network size={16} /> 7. Network Artifacts (URLs / Domains / IPs)
                    </h4>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '12px', fontSize: '12px' }}>
                      <div>
                        <strong>Extracted URLs ({activeCaseDetail.analysis.urls?.length || 0}):</strong>
                        {activeCaseDetail.analysis.urls?.length > 0 ? (
                          <ul style={{ margin: '4px 0 0 16px', padding: 0 }}>
                            {activeCaseDetail.analysis.urls.map((u, i) => <li key={i}><code>{u}</code></li>)}
                          </ul>
                        ) : <div className="text-muted">None</div>}
                      </div>

                      <div>
                        <strong>Observed Domains ({activeCaseDetail.analysis.domains?.length || 0}):</strong>
                        {activeCaseDetail.analysis.domains?.length > 0 ? (
                          <ul style={{ margin: '4px 0 0 16px', padding: 0 }}>
                            {activeCaseDetail.analysis.domains.map((d, i) => <li key={i}><code>{d}</code></li>)}
                          </ul>
                        ) : <div className="text-muted">None</div>}
                      </div>

                      <div>
                        <strong>IPv4 Addresses ({activeCaseDetail.analysis.ips?.length || 0}):</strong>
                        {activeCaseDetail.analysis.ips?.length > 0 ? (
                          <ul style={{ margin: '4px 0 0 16px', padding: 0 }}>
                            {activeCaseDetail.analysis.ips.map((ip, i) => <li key={i}><code>{ip}</code></li>)}
                          </ul>
                        ) : <div className="text-muted">None</div>}
                      </div>
                    </div>
                  </div>
                )}

                {/* 8. INFRASTRUCTURE GEOLOCATION + MAP */}
                <GeoMap 
                  locationData={activeCaseDetail.analysis?.ip_intelligence?.find(i => i.probable_infrastructure_location)?.probable_infrastructure_location || activeCaseDetail.analysis?.ip_intelligence?.[0]?.probable_infrastructure_location}
                  title="8. Infrastructure GeoLocation Map"
                />

                {/* 9. THREAT GRAPH */}
                {activeCaseDetail.analysis?.threat_graph && (
                  <div className="card" style={{ background: '#ffffff', padding: '14px', border: '1px solid #e2e8f0' }}>
                    <h4 style={{ margin: '0 0 10px 0', fontSize: '14px', color: '#0f172a' }}>9. Relational Threat Graph</h4>
                    <ThreatGraphView 
                      threatGraph={activeCaseDetail.analysis.threat_graph}
                      email={activeCaseDetail.analysis.email}
                      ips={activeCaseDetail.analysis.ips}
                      ipIntelligence={activeCaseDetail.analysis.ip_intelligence}
                    />
                  </div>
                )}

                {/* 10. RELAY TIMELINE */}
                {activeCaseDetail.analysis?.timeline && (
                  <div className="card" style={{ background: '#ffffff', padding: '14px', border: '1px solid #e2e8f0' }}>
                    <h4 style={{ margin: '0 0 10px 0', fontSize: '14px', color: '#0f172a', display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <Clock size={16} /> 10. SMTP Relay Timeline ({activeCaseDetail.analysis.timeline.length})
                    </h4>
                    {activeCaseDetail.analysis.timeline.length > 0 ? (
                      <table className="data-table" style={{ fontSize: '12px' }}>
                        <thead>
                          <tr>
                            <th>#</th>
                            <th>Timestamp</th>
                            <th>Source Host</th>
                            <th>Destination Host</th>
                            <th>IP Address</th>
                          </tr>
                        </thead>
                        <tbody>
                          {activeCaseDetail.analysis.timeline.map((evt, idx) => (
                            <tr key={idx}>
                              <td>{evt.sequence}</td>
                              <td>{evt.timestamp || 'N/A'}</td>
                              <td><code>{evt.source || 'N/A'}</code></td>
                              <td><code>{evt.destination || 'N/A'}</code></td>
                              <td><code>{evt.ip || 'N/A'}</code></td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    ) : (
                      <p className="text-muted" style={{ margin: 0, fontSize: '13px' }}>No relay timeline events recorded.</p>
                    )}
                  </div>
                )}

                {/* 11. BLOCKCHAIN EVIDENCE INTEGRITY */}
                <BlockchainLedgerView caseId={activeCaseDetail.case_id} />

                {/* MODAL ACTIONS */}
                <div className="modal-actions" style={{ marginTop: '16px', display: 'flex', justifyContent: 'flex-end', gap: '8px', position: 'sticky', bottom: 0, background: '#ffffff', borderTop: '1px solid #e2e8f0', paddingTop: '12px' }}>
                  <a 
                    href={getPdfReportUrl(activeCaseDetail.case_id)} 
                    target="_blank" 
                    rel="noreferrer" 
                    className="btn btn-primary"
                  >
                    <Download size={14} /> Download Forensic PDF Report
                  </a>
                  <button className="btn btn-danger-outline" onClick={() => handleDeleteOne(activeCaseDetail.case_id)}>
                    <Trash2 size={14} /> Delete Case
                  </button>
                  <button className="btn btn-secondary" onClick={() => setActiveCaseDetail(null)}>
                    Close
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
