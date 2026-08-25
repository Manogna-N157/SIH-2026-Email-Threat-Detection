import React, { useEffect, useState } from 'react';
import { getCases } from '../api';
import { ShieldAlert, Globe, Network, RefreshCw } from 'lucide-react';

export default function ThreatIntelPage() {
  const [cases, setCases] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchCases = async () => {
    setLoading(true);
    try {
      const data = await getCases();
      setCases(data || []);
    } catch {
      // Fallback
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCases();
  }, []);

  // Aggregate IOCs across cases
  const allIps = new Set();
  const allDomains = new Set();
  const allUrls = new Set();
  const infrastructureList = [];

  cases.forEach((c) => {
    const analysis = c.analysis;
    if (analysis) {
      (analysis.ips || []).forEach(ip => allIps.add(ip));
      (analysis.domains || []).forEach(d => allDomains.add(d));
      (analysis.urls || []).forEach(u => allUrls.add(u));
      (analysis.ip_intelligence || []).forEach(intel => {
        if (intel.probable_infrastructure_location) {
          infrastructureList.push({
            ip: intel.ip,
            loc: intel.probable_infrastructure_location,
            caseId: c.case_id
          });
        }
      });
    }
  });

  return (
    <div className="page-container">
      <div className="card">
        <div className="card-header">
          <div>
            <h2><ShieldAlert size={22} /> Threat Intelligence Summary</h2>
            <p className="subtitle">Extracted technical indicators (IPs, Domains, URLs, Infrastructure) aggregated from analyzed email cases.</p>
          </div>
          <button className="btn btn-secondary btn-sm" onClick={fetchCases}>
            <RefreshCw size={14} /> Refresh Intel
          </button>
        </div>

        {loading ? (
          <p className="loading-text">Aggregating threat intelligence data...</p>
        ) : (
          <div>
            {/* Quick Metrics */}
            <div className="metrics-grid" style={{ marginBottom: '24px' }}>
              <div className="card metric-card">
                <div className="metric-icon blue"><Network size={20} /></div>
                <div className="metric-info">
                  <span className="metric-label">Unique IP Addresses</span>
                  <span className="metric-value">{allIps.size}</span>
                </div>
              </div>

              <div className="card metric-card">
                <div className="metric-icon orange"><Globe size={20} /></div>
                <div className="metric-info">
                  <span className="metric-label">Extracted Domains</span>
                  <span className="metric-value">{allDomains.size}</span>
                </div>
              </div>

              <div className="card metric-card">
                <div className="metric-icon red"><ShieldAlert size={20} /></div>
                <div className="metric-info">
                  <span className="metric-label">Extracted URLs</span>
                  <span className="metric-value">{allUrls.size}</span>
                </div>
              </div>
            </div>

            {/* Section 1: Infrastructure Locations */}
            <div style={{ marginBottom: '24px' }}>
              <h3>Probable Infrastructure Locations</h3>
              <p className="disclaimer-text">
                * Network-associated infrastructure locations mapped via IP intelligence lookups.
              </p>

              {infrastructureList.length === 0 ? (
                <p className="text-muted">No infrastructure intelligence mapped yet.</p>
              ) : (
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>IP Address</th>
                      <th>Country</th>
                      <th>City</th>
                      <th>ISP</th>
                      <th>ASN</th>
                      <th>Organization</th>
                    </tr>
                  </thead>
                  <tbody>
                    {infrastructureList.map((item, idx) => (
                      <tr key={idx}>
                        <td><code>{item.ip}</code></td>
                        <td>{item.loc.country || 'N/A'}</td>
                        <td>{item.loc.city || 'N/A'}</td>
                        <td>{item.loc.isp || 'N/A'}</td>
                        <td>{item.loc.asn || 'N/A'}</td>
                        <td>{item.loc.organization || 'N/A'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>

            {/* Section 2: IOC Lists */}
            <div className="ioc-grid">
              <div className="ioc-box">
                <h4>Extracted Domains</h4>
                {allDomains.size === 0 ? <p className="text-muted">No domains recorded</p> : (
                  <ul className="ioc-list">
                    {Array.from(allDomains).map((d, i) => <li key={i}><code>{d}</code></li>)}
                  </ul>
                )}
              </div>

              <div className="ioc-box">
                <h4>Extracted IP Addresses</h4>
                {allIps.size === 0 ? <p className="text-muted">No IP addresses recorded</p> : (
                  <ul className="ioc-list">
                    {Array.from(allIps).map((ip, i) => <li key={i}><code>{ip}</code></li>)}
                  </ul>
                )}
              </div>

              <div className="ioc-box">
                <h4>Extracted URLs</h4>
                {allUrls.size === 0 ? <p className="text-muted">No URLs recorded</p> : (
                  <ul className="ioc-list">
                    {Array.from(allUrls).map((u, i) => <li key={i}><code>{u}</code></li>)}
                  </ul>
                )}
              </div>
            </div>

          </div>
        )}
      </div>
    </div>
  );
}
