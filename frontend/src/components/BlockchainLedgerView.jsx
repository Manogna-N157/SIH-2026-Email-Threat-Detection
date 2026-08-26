import React, { useState, useEffect } from 'react';
import { verifyCaseBlockchain, getBlockchainLedger } from '../api';
import { ShieldCheck, ShieldAlert, CheckCircle2, XCircle, RefreshCw, Link, Cpu } from 'lucide-react';

export default function BlockchainLedgerView({ caseId, initialBlock = null }) {
  const [verifying, setVerifying] = useState(false);
  const [verificationResult, setVerificationResult] = useState(null);
  const [verifyError, setVerifyError] = useState('');
  
  const [ledger, setLedger] = useState([]);
  const [loadingLedger, setLoadingLedger] = useState(false);
  const [ledgerError, setLedgerError] = useState('');

  const activeBlock = verificationResult?.block || initialBlock;

  const handleVerify = async () => {
    if (!caseId) return;
    setVerifying(true);
    setVerifyError('');
    setVerificationResult(null);

    try {
      const data = await verifyCaseBlockchain(caseId);
      setVerificationResult(data);
    } catch (err) {
      setVerifyError(err.message || 'Failed to verify blockchain evidence.');
    } finally {
      setVerifying(false);
    }
  };

  const fetchLedger = async () => {
    setLoadingLedger(true);
    setLedgerError('');
    try {
      const data = await getBlockchainLedger();
      setLedger(data || []);
    } catch (err) {
      setLedgerError(err.message || 'Could not load blockchain ledger.');
    } finally {
      setLoadingLedger(false);
    }
  };

  useEffect(() => {
    fetchLedger();
  }, [caseId]);

  return (
    <div className="blockchain-section" style={{ marginTop: '16px' }}>
      {/* SECTION 4: BLOCKCHAIN EVIDENCE INTEGRITY */}
      <div className="card" style={{ background: '#f8fafc', border: '1px solid #cbd5e1', borderRadius: '8px', padding: '16px', marginBottom: '16px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
          <h4 style={{ display: 'flex', alignItems: 'center', gap: '8px', margin: 0, fontSize: '15px', color: '#0f172a' }}>
            <ShieldCheck size={18} color="#2563eb" /> Blockchain Evidence Integrity
          </h4>
          <button 
            className="btn btn-primary btn-sm" 
            onClick={handleVerify} 
            disabled={verifying || !caseId}
            style={{ fontSize: '12px' }}
          >
            {verifying ? 'Verifying Hashes...' : 'Verify Evidence Integrity'}
          </button>
        </div>

        {activeBlock && (
          <div style={{ fontSize: '13px', background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: '6px', padding: '12px', marginBottom: '12px' }}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '10px' }}>
              <div><strong>Block #:</strong> Block #{activeBlock.index ?? activeBlock.block_index}</div>
              <div><strong>Case ID:</strong> <code>{activeBlock.case_id}</code></div>
              <div><strong>Recorded:</strong> {activeBlock.timestamp ? new Date(activeBlock.timestamp).toLocaleString() : 'N/A'}</div>
            </div>
            <div style={{ marginTop: '8px', wordBreak: 'break-all' }}>
              <strong>Evidence Hash:</strong> <code>{activeBlock.evidence_hash}</code>
            </div>
            <div style={{ marginTop: '4px', wordBreak: 'break-all' }}>
              <strong>Previous Hash:</strong> <code>{activeBlock.previous_hash}</code>
            </div>
            {activeBlock.current_hash && (
              <div style={{ marginTop: '4px', wordBreak: 'break-all' }}>
                <strong>Current Block Hash:</strong> <code>{activeBlock.current_hash}</code>
              </div>
            )}
          </div>
        )}

        {/* Verification Status Feedback */}
        {verificationResult && (
          <div 
            className={`alert alert-${verificationResult.verified ? 'success' : 'error'}`} 
            style={{ margin: '8px 0 0 0', display: 'flex', alignItems: 'center', gap: '10px' }}
          >
            {verificationResult.verified ? (
              <>
                <CheckCircle2 size={20} color="#16a34a" />
                <div>
                  <strong>🟢 Evidence Integrity Verified</strong>
                  <p style={{ margin: '2px 0 0 0', fontSize: '13px' }}>
                    {verificationResult.message || 'No evidence tampering detected. SHA-256 fingerprint matches chained block ledger.'}
                  </p>
                </div>
              </>
            ) : (
              <>
                <XCircle size={20} color="#dc2626" />
                <div>
                  <strong>🔴 Evidence Integrity Check Failed</strong>
                  <p style={{ margin: '2px 0 0 0', fontSize: '13px' }}>
                    {verificationResult.message || 'Possible evidence tampering detected! Case data does not match stored block hash.'}
                  </p>
                </div>
              </>
            )}
          </div>
        )}

        {verifyError && (
          <div className="alert alert-error" style={{ marginTop: '8px' }}>
            <ShieldAlert size={16} /> {verifyError}
          </div>
        )}
      </div>

      {/* SECTION 5: BLOCKCHAIN LEDGER VISUALIZATION */}
      <div className="card" style={{ background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: '8px', padding: '16px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
          <h4 style={{ display: 'flex', alignItems: 'center', gap: '8px', margin: 0, fontSize: '15px', color: '#0f172a' }}>
            <Link size={18} color="#0284c7" /> Evidence Blockchain Ledger
          </h4>
          <button className="btn btn-secondary btn-sm" onClick={fetchLedger} disabled={loadingLedger} style={{ fontSize: '11px' }}>
            <RefreshCw size={12} /> Refresh Ledger
          </button>
        </div>

        {loadingLedger ? (
          <p className="loading-text" style={{ fontSize: '13px' }}>Loading immutable ledger blocks...</p>
        ) : ledgerError ? (
          <p className="text-muted" style={{ fontSize: '13px', color: '#ef4444' }}>{ledgerError}</p>
        ) : ledger.length === 0 ? (
          <p className="text-muted" style={{ fontSize: '13px' }}>No evidence blocks created in ledger yet.</p>
        ) : (
          <div className="ledger-chain-container" style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {ledger.map((blk, idx) => {
              const isCurrentCase = blk.case_id === caseId;
              const shortHash = (hash) => hash ? `${hash.slice(0, 10)}...${hash.slice(-6)}` : 'N/A';
              
              return (
                <React.Fragment key={blk.block_index ?? blk.index ?? idx}>
                  {idx > 0 && (
                    <div style={{ textAlign: 'center', color: '#94a3b8', fontSize: '14px', margin: '-4px 0' }}>
                      ↓
                    </div>
                  )}
                  <div 
                    style={{ 
                      padding: '10px 14px', 
                      background: isCurrentCase ? '#f0f9ff' : '#f8fafc', 
                      border: isCurrentCase ? '2px solid #0284c7' : '1px solid #e2e8f0', 
                      borderRadius: '6px',
                      display: 'flex',
                      justify: 'space-between',
                      alignItems: 'center',
                      flexWrap: 'wrap',
                      gap: '10px'
                    }}
                  >
                    <div>
                      <span style={{ fontWeight: 700, fontSize: '13px', color: '#0f172a', marginRight: '8px' }}>
                        Block #{blk.block_index ?? blk.index}
                      </span>
                      {blk.previous_hash === 'GENESIS' && (
                        <span style={{ background: '#e2e8f0', color: '#475569', fontSize: '11px', padding: '1px 6px', borderRadius: '4px', fontWeight: 600 }}>
                          GENESIS
                        </span>
                      )}
                      {isCurrentCase && (
                        <span style={{ background: '#0284c7', color: '#ffffff', fontSize: '11px', padding: '1px 6px', borderRadius: '4px', fontWeight: 600, marginLeft: '6px' }}>
                          This Case
                        </span>
                      )}
                      <div style={{ fontSize: '12px', color: '#64748b', marginTop: '2px' }}>
                        Case ID: <code>{blk.case_id}</code>
                      </div>
                    </div>

                    <div style={{ fontSize: '11px', fontFamily: 'monospace', color: '#334155' }}>
                      <div>Hash: <strong>{shortHash(blk.current_hash || blk.evidence_hash)}</strong></div>
                      <div style={{ color: '#94a3b8' }}>Prev: {shortHash(blk.previous_hash)}</div>
                    </div>
                  </div>
                </React.Fragment>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
