import React, { useState } from 'react';
import { analyzeEmail, saveCase } from '../api';
import Badge from '../components/Badge';
import ThreatGraphView from '../components/ThreatGraphView';
import { 
  Upload, 
  FileCheck, 
  AlertCircle, 
  Loader2, 
  ShieldAlert, 
  Mail, 
  Lock, 
  Cpu, 
  Globe, 
  Clock, 
  Network,
  CheckCircle2
} from 'lucide-react';

export default function InvestigateEmailPage() {
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState(null);
  const [savedStatus, setSavedStatus] = useState('');

  const formatConfidence = (val) => {
    if (val === null || val === undefined || val === '') return 'N/A';
    return `${val}%`;
  };

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile) {
      if (!selectedFile.name.toLowerCase().endsWith('.eml')) {
        setError('Please select a valid .eml email file.');
        setFile(null);
        return;
      }
      setFile(selectedFile);
      setError('');
      setResult(null);
      setSavedStatus('');
    }
  };

  const handleAnalyze = async (e) => {
    e.preventDefault();
    if (!file) {
      setError('Please select an .eml file to analyze.');
      return;
    }

    setLoading(true);
    setError('');
    setResult(null);
    setSavedStatus('');

    try {
      const data = await analyzeEmail(file);
      setResult(data);

      // Automatically store as case if backend supports it
      try {
        await saveCase({
          case_id: data.case_id,
          filename: file.name,
          risk_score: data.risk_score,
          risk_level: data.risk_level,
          classification: data.classification,
          confidence: data.confidence,
          summary: `Analysis of ${file.name} - Subject: ${data.email?.subject || 'No Subject'}`,
          indicators: data.indicators || [],
          analysis: data,
        });
        setSavedStatus('Case saved to system.');
      } catch (saveErr) {
        console.warn('Auto-save case notice:', saveErr.message);
      }
    } catch (err) {
      setError(err.message || 'An error occurred during email analysis.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page-container">
      {/* Upload Form Card */}
      <div className="card">
        <h3>Upload .EML File for Threat Analysis</h3>
        <p className="subtitle">
          Select an .eml raw email file to perform forensic parsing, header verification, threat indicator matching, and infrastructure geolocation.
        </p>

        <form onSubmit={handleAnalyze} className="upload-form">
          <div className="file-drop-zone">
            <input 
              type="file" 
              accept=".eml" 
              onChange={handleFileChange} 
              id="eml-upload-input"
              style={{ display: 'none' }}
            />
            <label htmlFor="eml-upload-input" className="file-drop-label">
              <Upload size={32} className="upload-icon" />
              <span>{file ? file.name : 'Click or Drag & Drop .eml file here'}</span>
              {file && <span className="file-size">({(file.size / 1024).toFixed(1)} KB)</span>}
            </label>
          </div>

          <div className="form-actions">
            <button 
              type="submit" 
              className="btn btn-primary btn-lg" 
              disabled={loading || !file}
            >
              {loading ? (
                <>
                  <Loader2 size={18} className="spin" /> Analyzing Email...
                </>
              ) : (
                <>
                  <FileCheck size={18} /> Analyze Email
                </>
              )}
            </button>
          </div>
        </form>

        {loading && (
          <div className="loading-banner">
            <Loader2 size={20} className="spin" />
            <span>Sending .eml file to POST /api/analyze ... Please wait.</span>
          </div>
        )}

        {error && (
          <div className="alert alert-error">
            <AlertCircle size={18} />
            <div>
              <strong>Analysis Error:</strong> {error}
            </div>
          </div>
        )}

        {savedStatus && (
          <div className="alert alert-success" style={{ marginTop: '12px' }}>
            <CheckCircle2 size={16} /> {savedStatus}
          </div>
        )}
      </div>

      {/* ANALYSIS RESULTS SECTION */}
      {result && (
        <div className="analysis-results">
          
          {/* SECTION A: RISK */}
          <div className="card result-card risk-card">
            <div className="card-header">
              <h3><ShieldAlert size={20} /> A. Risk Assessment Summary</h3>
              <span>Case ID: <code>{result.case_id}</code></span>
            </div>
            
            <div className="risk-grid">
              <div className="risk-item">
                <span className="risk-label">Risk Score</span>
                <div className="risk-score-display">
                  <span className={`large-score score-${result.risk_score >= 70 ? 'high' : result.risk_score >= 40 ? 'med' : 'low'}`}>
                    {result.risk_score ?? 'N/A'}
                  </span>
                  <span className="score-max">/ 100</span>
                </div>
              </div>

              <div className="risk-item">
                <span className="risk-label">Risk Level</span>
                <div style={{ marginTop: '4px' }}>
                  <Badge type="risk_level" value={result.risk_level} />
                </div>
              </div>

              <div className="risk-item">
                <span className="risk-label">Classification</span>
                <div style={{ marginTop: '4px' }}>
                  <Badge type="classification" value={result.classification} />
                </div>
              </div>

              <div className="risk-item">
                <span className="risk-label">Confidence</span>
                <span className="risk-value-text">{formatConfidence(result.confidence)}</span>
              </div>

              <div className="risk-item">
                <span className="risk-label">Recommended Action</span>
                <div style={{ marginTop: '4px' }}>
                  <Badge type="action" value={result.ai_analysis?.result?.recommended_action || (result.risk_score >= 70 ? 'QUARANTINE' : 'ALLOW')} />
                </div>
              </div>
            </div>
          </div>

          {/* SECTION B: EMAIL DETAILS */}
          <div className="card result-card">
            <h3><Mail size={20} /> B. Email Details</h3>
            <div className="details-grid">
              <div className="detail-row">
                <strong>Subject:</strong>
                <span>{result.email?.subject || '(No Subject)'}</span>
              </div>
              <div className="detail-row">
                <strong>Date:</strong>
                <span>{result.email?.date || 'N/A'}</span>
              </div>
              <div className="detail-row">
                <strong>Message-ID:</strong>
                <span><code>{result.email?.message_id || 'N/A'}</code></span>
              </div>
              <div className="detail-row">
                <strong>From:</strong>
                <span>{formatEmailAddresses(result.email?.from_ || result.email?.from)}</span>
              </div>
              <div className="detail-row">
                <strong>To:</strong>
                <span>{formatEmailAddresses(result.email?.to)}</span>
              </div>
              <div className="detail-row">
                <strong>Reply-To:</strong>
                <span>{formatEmailAddresses(result.email?.reply_to)}</span>
              </div>
              <div className="detail-row">
                <strong>Return-Path:</strong>
                <span>{formatEmailAddresses(result.email?.return_path)}</span>
              </div>
            </div>

            {/* Attachments list if any */}
            {result.email?.attachments?.length > 0 && (
              <div style={{ marginTop: '16px', paddingTop: '12px', borderTop: '1px solid #e2e8f0' }}>
                <h4>Attachments ({result.email.attachments.length}):</h4>
                <ul className="attachment-list">
                  {result.email.attachments.map((att, idx) => (
                    <li key={idx}>
                      📎 <strong>{att.filename || 'Unnamed attachment'}</strong> ({att.content_type}, {(att.size_bytes / 1024).toFixed(1)} KB)
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Plain text body preview */}
            {result.email?.plain_text_body && (
              <div style={{ marginTop: '16px', paddingTop: '12px', borderTop: '1px solid #e2e8f0' }}>
                <h4>Email Body Preview (Plain Text):</h4>
                <pre className="body-preview">{result.email.plain_text_body.slice(0, 1000)}{result.email.plain_text_body.length > 1000 ? '...' : ''}</pre>
              </div>
            )}
          </div>

          {/* SECTION C: AUTHENTICATION */}
          <div className="card result-card">
            <h3><Lock size={20} /> C. Technical Authentication</h3>
            
            <div className="auth-checks-grid">
              <div className="auth-box">
                <h4>SPF (Sender Policy Framework)</h4>
                {renderAuthCheckList(result.authentication?.spf)}
              </div>

              <div className="auth-box">
                <h4>DKIM (DomainKeys Identified Mail)</h4>
                {renderAuthCheckList(result.authentication?.dkim)}
              </div>

              <div className="auth-box">
                <h4>DMARC</h4>
                {renderAuthCheckList(result.authentication?.dmarc)}
              </div>
            </div>

            {result.authentication?.authentication_results?.length > 0 && (
              <div style={{ marginTop: '14px' }}>
                <h4>Authentication-Results Headers:</h4>
                {result.authentication.authentication_results.map((ar, i) => (
                  <div key={i} className="code-box">{ar}</div>
                ))}
              </div>
            )}
          </div>

          {/* SECTION D: THREAT INDICATORS */}
          <div className="card result-card">
            <h3><AlertCircle size={20} /> D. Threat Indicators ({result.indicators?.length || 0})</h3>
            {!result.indicators || result.indicators.length === 0 ? (
              <p className="text-muted">No explicit threat indicators triggered for this email.</p>
            ) : (
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Indicator Name</th>
                    <th>Severity</th>
                    <th>Explanation</th>
                    <th>Score Contribution</th>
                  </tr>
                </thead>
                <tbody>
                  {result.indicators.map((ind, i) => (
                    <tr key={i}>
                      <td><strong>{ind.name}</strong></td>
                      <td><Badge type="severity" value={ind.severity} /></td>
                      <td>{ind.explanation}</td>
                      <td>+{ind.score_contribution || 0}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>

          {/* SECTION E: AI ANALYSIS */}
          <div className="card result-card">
            <h3><Cpu size={20} /> E. AI Analysis (Backend Semantic Layer)</h3>
            <p className="subtitle">
              Response returned from backend API (No direct frontend Gemini API calls).
            </p>

            {!result.ai_analysis?.available ? (
              <div className="alert alert-info">
                AI semantic analysis layer was not active or turned off in backend. Rule-based analysis provided above.
              </div>
            ) : (
              <div className="ai-analysis-box">
                <div className="ai-grid">
                  <div>
                    <strong>AI Classification:</strong>{' '}
                    <Badge type="classification" value={result.ai_analysis.result?.classification} />
                  </div>
                  <div>
                    <strong>Confidence:</strong> {formatConfidence(result.ai_analysis.result?.confidence)}
                  </div>
                  <div>
                    <strong>Recommended Action:</strong>{' '}
                    <Badge type="action" value={result.ai_analysis.result?.recommended_action} />
                  </div>
                </div>

                {result.ai_analysis.result?.threat_categories?.length > 0 && (
                  <div style={{ marginTop: '12px' }}>
                    <strong>Threat Categories:</strong>
                    <div style={{ display: 'flex', gap: '6px', marginTop: '4px', flexWrap: 'wrap' }}>
                      {result.ai_analysis.result.threat_categories.map((cat, idx) => (
                        <span key={idx} className="tag">{cat}</span>
                      ))}
                    </div>
                  </div>
                )}

                {result.ai_analysis.result?.explanation && (
                  <div style={{ marginTop: '12px' }}>
                    <strong>Explanation:</strong>
                    <p className="ai-explanation">{result.ai_analysis.result.explanation}</p>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* SECTION F: URLS / DOMAINS / IPS */}
          <div className="card result-card">
            <h3><Globe size={20} /> F. Extracted Technical IOCs</h3>
            <div className="ioc-grid">
              <div className="ioc-box">
                <h4>Extracted URLs ({result.urls?.length || 0})</h4>
                {result.urls?.length === 0 ? <p className="text-muted">None</p> : (
                  <ul className="ioc-list">
                    {result.urls.map((u, i) => <li key={i}><code>{u}</code></li>)}
                  </ul>
                )}
              </div>

              <div className="ioc-box">
                <h4>Extracted Domains ({result.domains?.length || 0})</h4>
                {result.domains?.length === 0 ? <p className="text-muted">None</p> : (
                  <ul className="ioc-list">
                    {result.domains.map((d, i) => <li key={i}><code>{d}</code></li>)}
                  </ul>
                )}
              </div>

              <div className="ioc-box">
                <h4>Extracted IP Addresses ({result.ips?.length || 0})</h4>
                {result.ips?.length === 0 ? <p className="text-muted">None</p>
                : (
                  <ul className="ioc-list">
                    {result.ips.map((ip, i) => <li key={i}><code>{ip}</code></li>)}
                  </ul>
                )}
              </div>
            </div>
          </div>

          {/* SECTION G: IP INTELLIGENCE */}
          <div className="card result-card">
            <h3><Network size={20} /> G. IP Intelligence</h3>
            <h4 style={{ color: '#0f172a', margin: '4px 0 8px 0' }}>Probable Infrastructure Location</h4>
            <p className="disclaimer-text">
              * Notice: Network-associated location, not an assertion of a person's physical location.
            </p>

            {!result.ip_intelligence || result.ip_intelligence.length === 0 ? (
              <p className="text-muted">No public IP intelligence lookup available.</p>
            ) : (
              <table className="data-table">
                <thead>
                  <tr>
                    <th>IP Address</th>
                    <th>Class</th>
                    <th>Country</th>
                    <th>City</th>
                    <th>Lat / Long</th>
                    <th>ISP</th>
                    <th>ASN</th>
                    <th>Organization</th>
                  </tr>
                </thead>
                <tbody>
                  {result.ip_intelligence.map((intel, idx) => {
                    const loc = intel.probable_infrastructure_location;
                    return (
                      <tr key={idx}>
                        <td><code>{intel.ip}</code></td>
                        <td><span className="tag">{intel.address_class}</span></td>
                        <td>{loc?.country || 'N/A'}</td>
                        <td>{loc?.city || 'N/A'}</td>
                        <td>{loc?.latitude && loc?.longitude ? `${loc.latitude}, ${loc.longitude}` : 'N/A'}</td>
                        <td>{loc?.isp || 'N/A'}</td>
                        <td>{loc?.asn || 'N/A'}</td>
                        <td>{loc?.organization || 'N/A'}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </div>

          {/* SECTION H: RELAY TIMELINE */}
          <div className="card result-card">
            <h3><Clock size={20} /> H. Email Relay Timeline</h3>
            {!result.timeline || result.timeline.length === 0 ? (
              <p className="text-muted">No relay hop headers recorded.</p>
            ) : (
              <div className="timeline-container">
                {result.timeline.map((event, idx) => (
                  <div key={idx} className="timeline-event">
                    <div className="timeline-badge">Hop {event.sequence}</div>
                    <div className="timeline-content">
                      <div className="timeline-header">
                        <strong>{event.hostname || event.ip || 'Unknown Hop'}</strong>
                        <span className="timeline-time">{event.timestamp || 'No Timestamp'}</span>
                      </div>
                      <div className="timeline-details">
                        <span><strong>Source:</strong> {event.source || 'N/A'}</span> &bull; 
                        <span> <strong>Destination:</strong> {event.destination || 'N/A'}</span> &bull; 
                        <span> <strong>IP:</strong> <code>{event.ip || 'N/A'}</code></span>
                      </div>
                      {event.raw_header && (
                        <div className="timeline-raw">
                          <code>{event.raw_header}</code>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* SECTION I: THREAT GRAPH PLACEHOLDER */}
          <div className="card result-card">
            <h3><Network size={20} /> I. Threat Graph Placeholder</h3>
            <ThreatGraphView 
              threatGraph={result.threat_graph} 
              email={result.email}
              ips={result.ips}
              ipIntelligence={result.ip_intelligence}
            />
          </div>

        </div>
      )}
    </div>
  );
}

// Helpers
function formatEmailAddresses(list) {
  if (!list || list.length === 0) return 'N/A';
  return list
    .map(e => e.display_name ? `${e.display_name} <${e.address}>` : e.address || JSON.stringify(e))
    .join(', ');
}

function renderAuthCheckList(checks) {
  if (!checks || checks.length === 0) return <p className="text-muted">No record</p>;
  return checks.map((c, i) => (
    <div key={i} style={{ marginBottom: '6px', fontSize: '13px' }}>
      <Badge type="result" value={c.result} /> <span style={{ marginLeft: '6px' }}>{c.source}</span>
      <div style={{ fontSize: '11px', color: '#64748b', fontFamily: 'monospace' }}>{c.raw}</div>
    </div>
  ));
}
