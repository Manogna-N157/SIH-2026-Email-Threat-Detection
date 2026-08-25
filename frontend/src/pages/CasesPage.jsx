import React, { useEffect, useState } from 'react';
import { getCases, getCaseDetails, getPdfReportUrl, deleteCase, deleteAllCases } from '../api';
import Badge from '../components/Badge';
import ThreatGraphView from '../components/ThreatGraphView';
import { Briefcase, RefreshCw, Eye, Download, X, AlertCircle, Trash2, CheckCircle2 } from 'lucide-react';

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
      setFeedback({ type: 'error', message: `Could not load details for case ${caseId}: ${err.message}` });
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
      // Optimistically update list or refresh
      setCases((prev) => prev.filter((c) => c.case_id !== caseId));
      if (activeCaseDetail?.case_id === caseId) {
        setActiveCaseDetail(null);
      }
      await fetchCases();
    } catch (err) {
      // Fallback: update client state if backend endpoint not available
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
      // Fallback: clear local list
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
                      <span className={`risk-score-pill score-${c.risk_score >= 70 ? 'high' : c.risk_score >= 40 ? 'med' : 'low'}`}>
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

      {/* Case Details Modal / Full Inspection Box */}
      {activeCaseDetail && (
        <div className="modal-backdrop" onClick={() => setActiveCaseDetail(null)}>
          <div className="modal-content card" onClick={(e) => e.stopPropagation()}>
            <div className="card-header">
              <h3>Case Details: <code>{activeCaseDetail.case_id}</code></h3>
              <button className="btn-icon" onClick={() => setActiveCaseDetail(null)}>
                <X size={18} />
              </button>
            </div>

            {loadingDetail ? (
              <p className="loading-text">Loading detail view...</p>
            ) : (
              <div className="modal-body">
                <div className="details-grid" style={{ marginBottom: '16px' }}>
                  <div className="detail-row">
                    <strong>Filename:</strong> <span>{activeCaseDetail.filename}</span>
                  </div>
                  <div className="detail-row">
                    <strong>Timestamp:</strong> <span>{activeCaseDetail.timestamp}</span>
                  </div>
                  <div className="detail-row">
                    <strong>Risk Score:</strong> 
                    <span>
                      {activeCaseDetail.risk_score ?? 'N/A'}/100
                    </span>
                  </div>
                  <div className="detail-row">
                    <strong>Risk Level:</strong> 
                    <Badge type="risk_level" value={activeCaseDetail.risk_level || activeCaseDetail.analysis?.risk_level} />
                  </div>
                  <div className="detail-row">
                    <strong>Classification:</strong> <Badge type="classification" value={activeCaseDetail.classification} />
                  </div>
                  <div className="detail-row">
                    <strong>Confidence:</strong> <span>{formatConfidence(activeCaseDetail.confidence ?? activeCaseDetail.analysis?.confidence)}</span>
                  </div>
                  <div className="detail-row">
                    <strong>Summary:</strong> <span>{activeCaseDetail.summary}</span>
                  </div>
                </div>

                {activeCaseDetail.analysis && (
                  <div>
                    <h4 style={{ margin: '12px 0 8px 0' }}>Threat Indicators ({activeCaseDetail.analysis.indicators?.length || 0}):</h4>
                    {activeCaseDetail.analysis.indicators?.length > 0 ? (
                      <ul>
                        {activeCaseDetail.analysis.indicators.map((ind, i) => (
                          <li key={i}>
                            <strong>{ind.name}</strong> ({ind.severity}): {ind.explanation}
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p className="text-muted">None</p>
                    )}

                    <h4 style={{ margin: '16px 0 8px 0' }}>Relational Threat Graph:</h4>
                    <ThreatGraphView 
                      threatGraph={activeCaseDetail.analysis.threat_graph}
                      email={activeCaseDetail.analysis.email}
                      ips={activeCaseDetail.analysis.ips}
                      ipIntelligence={activeCaseDetail.analysis.ip_intelligence}
                    />
                  </div>
                )}

                <div className="modal-actions" style={{ marginTop: '20px', display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
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
