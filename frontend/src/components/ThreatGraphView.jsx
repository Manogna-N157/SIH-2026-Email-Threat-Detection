import React from 'react';
import { Mail, User, Globe, Network, MapPin, ArrowDown } from 'lucide-react';

export default function ThreatGraphView({
  threatGraph,
  email,
  ips,
  ipIntelligence
}) {
  const subject = email?.subject || 'Analyzed EML File';

  const senderAddr =
    email?.from_?.[0]?.address ||
    email?.from?.[0]?.address ||
    'Unknown Sender';

  const senderDomain =
    email?.from_?.[0]?.domain ||
    email?.from?.[0]?.domain ||
    'Unknown Domain';

  const primaryIp = ips?.[0] || 'No IP detected';

  const ipIntel =
    ipIntelligence?.find((i) => i.ip === primaryIp) ||
    ipIntelligence?.[0];

  const location =
    ipIntel?.probable_infrastructure_location;

  const locationStr = location
    ? `${location.city || 'Unknown City'}, ${
        location.country || 'Unknown Country'
      }`
    : 'Unknown Location';

  const nodes = [
    {
      title: 'EMAIL',
      value: subject,
      icon: <Mail size={20} />,
      className: 'graph-email'
    },
    {
      title: 'SENDER',
      value: senderAddr,
      icon: <User size={20} />,
      className: 'graph-sender'
    },
    {
      title: 'DOMAIN',
      value: senderDomain,
      icon: <Globe size={20} />,
      className: 'graph-domain'
    },
    {
      title: 'IP ADDRESS',
      value: primaryIp,
      icon: <Network size={20} />,
      className: 'graph-ip'
    },
    {
      title: 'INFRASTRUCTURE LOCATION',
      value: locationStr,
      icon: <MapPin size={20} />,
      className: 'graph-location'
    }
  ];

  return (
    <div className="threat-graph-container">
      <div className="threat-graph-header">
        <div>
          <h4>Relational Threat Graph</h4>
          <p>
            Visual relationship between the email, sender,
            domain, IP address and infrastructure location.
          </p>
        </div>
      </div>

      <div className="threat-graph-flow">
        {nodes.map((node, index) => (
          <React.Fragment key={node.title}>
            <div className={`graph-node ${node.className}`}>
              <div className="graph-node-icon">
                {node.icon}
              </div>

              <div className="graph-node-content">
                <span className="graph-node-title">
                  {node.title}
                </span>

                <span
                  className="graph-node-value"
                  title={node.value}
                >
                  {node.value}
                </span>
              </div>
            </div>

            {index < nodes.length - 1 && (
              <div className="graph-arrow">
                <ArrowDown size={18} />
              </div>
            )}
          </React.Fragment>
        ))}
      </div>

      {threatGraph?.nodes?.length > 0 && (
        <div className="discovered-nodes">
          <h4>
            Discovered Graph Nodes
            <span>{threatGraph.nodes.length}</span>
          </h4>

          <div className="discovered-node-list">
            {threatGraph.nodes.map((node) => (
              <div
                className="discovered-node"
                key={node.id}
              >
                <strong>{node.type}</strong>
                <span>{node.label}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}