import React from 'react';

/**
 * Reusable simple badge component for risk, classification, action, severity, risk_level, etc.
 */
export default function Badge({ type, value }) {
  if (value === null || value === undefined || value === '') return null;

  let bg = '#e2e8f0';
  let color = '#334155';

  const valUpper = String(value).toUpperCase();

  if (type === 'classification') {
    switch (valUpper) {
      case 'LEGITIMATE':
        bg = '#dcfce7'; color = '#166534'; break;
      case 'SUSPICIOUS':
        bg = '#fef9c3'; color = '#854d0e'; break;
      case 'PHISHING':
        bg = '#ffedd5'; color = '#c2410c'; break;
      case 'IMPERSONATION':
        bg = '#fce7f3'; color = '#9d174d'; break;
      case 'BUSINESS_EMAIL_COMPROMISE':
        bg = '#fee2e2'; color = '#b91c1c'; break;
      case 'MALWARE':
        bg = '#7f1d1d'; color = '#ffffff'; break;
      default:
        bg = '#e2e8f0'; color = '#334155';
    }
  } else if (type === 'action') {
    switch (valUpper) {
      case 'ALLOW':
        bg = '#dcfce7'; color = '#166534'; break;
      case 'MONITOR':
        bg = '#e0f2fe'; color = '#0369a1'; break;
      case 'QUARANTINE':
        bg = '#fef3c7'; color = '#92400e'; break;
      case 'BLOCK':
        bg = '#fee2e2'; color = '#991b1b'; break;
      default:
        bg = '#e2e8f0'; color = '#334155';
    }
  } else if (type === 'severity' || type === 'risk_level') {
    switch (valUpper) {
      case 'CRITICAL':
        bg = '#991b1b'; color = '#ffffff'; break;
      case 'HIGH':
        bg = '#fee2e2'; color = '#991b1b'; break;
      case 'MEDIUM':
        bg = '#fef3c7'; color = '#92400e'; break;
      case 'LOW':
        bg = '#e0f2fe'; color = '#0369a1'; break;
      default:
        bg = '#f1f5f9'; color = '#475569';
    }
  } else if (type === 'result') {
    if (['PASS', 'OK', 'SUCCESS'].includes(valUpper)) {
      bg = '#dcfce7'; color = '#166534';
    } else if (['FAIL', 'FAIL_HARD', 'SOFTFAIL', 'NEUTRAL'].includes(valUpper)) {
      bg = '#fee2e2'; color = '#991b1b';
    } else {
      bg = '#f1f5f9'; color = '#475569';
    }
  }

  return (
    <span
      style={{
        display: 'inline-block',
        padding: '3px 8px',
        borderRadius: '4px',
        fontSize: '12px',
        fontWeight: 600,
        backgroundColor: bg,
        color: color,
        textTransform: 'uppercase',
        letterSpacing: '0.5px',
      }}
    >
      {value}
    </span>
  );
}
