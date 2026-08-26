import React from 'react';
import { Bot, AlertCircle, CheckCircle2, ShieldAlert } from 'lucide-react';
import Badge from './Badge';

export default function AISemanticAnalysisView({ analysisData, classification, confidence, fallbackText = 'AI semantic analysis unavailable for this case.' }) {
  const aiAnalysis = analysisData?.ai_analysis;
  const isAvailable = aiAnalysis?.available && aiAnalysis?.result;
  const aiResult = aiAnalysis?.result;

  if (!isAvailable) {
    return (
      <div className="card" style={{ background: '#f8fafc', border: '1px solid #e2e8f0', padding: '16px', borderRadius: '8px' }}>
        <h4 style={{ display: 'flex', alignItems: 'center', gap: '8px', margin: '0 0 10px 0', fontSize: '15px', color: '#1e293b' }}>
          <Bot size={18} color="#64748b" /> AI Semantic Analysis
        </h4>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#64748b', fontSize: '13px' }}>
          <AlertCircle size={16} />
          <span>{fallbackText}</span>
        </div>
      </div>
    );
  }

  return (
    <div className="card" style={{ background: '#f0f9ff', border: '1px solid #bae6fd', borderRadius: '8px', padding: '18px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
        <h4 style={{ display: 'flex', alignItems: 'center', gap: '8px', margin: 0, fontSize: '16px', color: '#0369a1' }}>
          <Bot size={20} color="#0284c7" /> AI Semantic Analysis & Threat Reasoning
        </h4>
        <span style={{ fontSize: '12px', background: '#e0f2fe', color: '#0369a1', padding: '3px 10px', borderRadius: '12px', fontWeight: 700 }}>
          Confidence: {confidence != null ? `${confidence}%` : 'N/A'} (Semantic)
        </span>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '12px', marginBottom: '14px' }}>
        <div style={{ background: '#ffffff', padding: '10px 14px', borderRadius: '6px', border: '1px solid #e0f2fe' }}>
          <span style={{ fontSize: '11px', color: '#64748b', textTransform: 'uppercase', fontWeight: 700 }}>Threat Classification</span>
          <div style={{ marginTop: '4px' }}>
            <Badge type="classification" value={classification || aiResult.classification} />
          </div>
        </div>

        {aiResult.recommended_action && (
          <div style={{ background: '#ffffff', padding: '10px 14px', borderRadius: '6px', border: '1px solid #e0f2fe' }}>
            <span style={{ fontSize: '11px', color: '#64748b', textTransform: 'uppercase', fontWeight: 700 }}>Recommended Action</span>
            <div style={{ marginTop: '4px', fontWeight: 700, color: '#0369a1', fontSize: '13px' }}>
              {aiResult.recommended_action}
            </div>
          </div>
        )}

        {aiResult.threat_categories?.length > 0 && (
          <div style={{ background: '#ffffff', padding: '10px 14px', borderRadius: '6px', border: '1px solid #e0f2fe' }}>
            <span style={{ fontSize: '11px', color: '#64748b', textTransform: 'uppercase', fontWeight: 700 }}>Threat Categories</span>
            <div style={{ marginTop: '4px', display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
              {aiResult.threat_categories.map((cat, i) => (
                <span key={i} className="tag" style={{ background: '#e0f2fe', color: '#0369a1', fontSize: '11px' }}>
                  {cat}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>

      <div style={{ background: '#ffffff', padding: '14px', borderRadius: '6px', border: '1px solid #e0f2fe' }}>
        <h5 style={{ margin: '0 0 6px 0', fontSize: '13px', color: '#1e293b' }}>AI Forensic Explanation:</h5>
        <p style={{ margin: 0, fontSize: '13px', lineHeight: 1.5, color: '#334155', whiteSpace: 'pre-line' }}>
          {aiResult.explanation}
        </p>
      </div>
    </div>
  );
}
