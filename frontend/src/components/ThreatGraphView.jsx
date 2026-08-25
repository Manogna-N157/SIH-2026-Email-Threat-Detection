import React from 'react';

/**
 * Simple placeholder representation of Threat Graph relationships:
 * EMAIL ↓ SENDER ↓ DOMAIN ↓ IP ↓ LOCATION
 */
export default function ThreatGraphView({ threatGraph, email, ips, ipIntelligence }) {
  // Extract info from passed analysis data or nodes
  const subject = email?.subject || 'Analyzed EML File';
  const senderAddr = email?.from_?.[0]?.address || email?.from?.[0]?.address || 'Unknown Sender';
  const senderDomain = email?.from_?.[0]?.domain || email?.from?.[0]?.domain || 'Unknown Domain';
  const primaryIp = ips?.[0] || '127.0.0.1';
  
  const ipIntel = ipIntelligence?.find(i => i.ip === primaryIp) || ipIntelligence?.[0];
  const locationStr = ipIntel?.probable_infrastructure_location
    ? `${ipIntel.probable_infrastructure_location.city || 'City'}, ${ipIntel.probable_infrastructure_location.country || 'Country'}`
    : 'Unknown Location';

  return (
    <div className="threat-graph-container" style={{ padding: '16px', background: '#f8fafc', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
      <p style={{ margin: '0 0 12px 0', fontSize: '13px', color: '#64748b' }}>
        Simplified Relational Graph (EMAIL &rarr; SENDER &rarr; DOMAIN &rarr; IP &rarr; LOCATION)
      </p>
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '8px', maxWidth: '400px', margin: '0 auto' }}>
        
        {/* EMAIL Node */}
        <div style={nodeStyle('#e0f2fe', '#0369a1')}>
          <strong>EMAIL</strong>
          <span style={{ fontSize: '12px', display: 'block', textOverflow: 'ellipsis', overflow: 'hidden', whiteSpace: 'nowrap' }}>
            {subject}
          </span>
        </div>

        <div style={arrowStyle}>&darr;</div>

        {/* SENDER Node */}
        <div style={nodeStyle('#fef3c7', '#92400e')}>
          <strong>SENDER</strong>
          <span style={{ fontSize: '12px', display: 'block' }}>{senderAddr}</span>
        </div>

        <div style={arrowStyle}>&darr;</div>

        {/* DOMAIN Node */}
        <div style={nodeStyle('#fce7f3', '#9d174d')}>
          <strong>DOMAIN</strong>
          <span style={{ fontSize: '12px', display: 'block' }}>{senderDomain}</span>
        </div>

        <div style={arrowStyle}>&darr;</div>

        {/* IP Node */}
        <div style={nodeStyle('#ffedd5', '#c2410c')}>
          <strong>IP ADDRESS</strong>
          <span style={{ fontSize: '12px', display: 'block' }}>{primaryIp}</span>
        </div>

        <div style={arrowStyle}>&darr;</div>

        {/* LOCATION Node */}
        <div style={nodeStyle('#dcfce7', '#166534')}>
          <strong>PROBABLE INFRASTRUCTURE LOCATION</strong>
          <span style={{ fontSize: '12px', display: 'block' }}>{locationStr}</span>
        </div>

      </div>

      {threatGraph?.nodes?.length > 0 && (
        <div style={{ marginTop: '20px', paddingTop: '12px', borderTop: '1px border #cbd5e1' }}>
          <h4 style={{ margin: '0 0 8px 0', fontSize: '13px' }}>Discovered Graph Nodes ({threatGraph.nodes.length}):</h4>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
            {threatGraph.nodes.map(n => (
              <span key={n.id} style={{ background: '#ffffff', border: '1px solid #cbd5e1', padding: '2px 6px', borderRadius: '4px', fontSize: '11px' }}>
                <strong>{n.type}:</strong> {n.label}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

const nodeStyle = (bg, border) => ({
  width: '100%',
  textAlign: 'center',
  padding: '8px 12px',
  backgroundColor: bg,
  border: `1px solid ${border}`,
  borderRadius: '6px',
  fontSize: '13px',
});

const arrowStyle = {
  fontSize: '18px',
  fontWeight: 'bold',
  color: '#64748b',
};
