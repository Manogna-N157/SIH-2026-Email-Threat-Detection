import React from 'react';
import { 
  LayoutDashboard, 
  Search, 
  Briefcase, 
  ShieldAlert, 
  FileText,
  Users,
  LogOut
} from 'lucide-react';

export default function Sidebar({ currentPage, setCurrentPage, onLogout, currentUser }) {
  const isAdmin = currentUser?.role === 'ADMIN';

  const menuItems = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'investigate', label: 'Investigate Email', icon: Search },
    { id: 'cases', label: 'Cases', icon: Briefcase },
    { id: 'threat-intel', label: 'Threat Intelligence', icon: ShieldAlert },
    { id: 'reports', label: 'Reports', icon: FileText },
  ];

  if (isAdmin) {
    menuItems.push({ id: 'admin-users', label: 'User Management', icon: Users });
  }

  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <ShieldAlert size={24} className="brand-icon" />
        <div className="brand-text">
          <h2>Email Forensics</h2>
          <span>SIH 2026 Platform</span>
        </div>
      </div>

      <nav className="sidebar-nav">
        {menuItems.map(item => {
          const Icon = item.icon;
          const isActive = currentPage === item.id;
          return (
            <button
              key={item.id}
              className={`nav-item ${isActive ? 'active' : ''}`}
              onClick={() => setCurrentPage(item.id)}
            >
              <Icon size={18} />
              <span>{item.label}</span>
              {item.id === 'admin-users' && <span className="tag-admin-pill">ADMIN</span>}
            </button>
          );
        })}
      </nav>

      <div className="sidebar-footer">
        <p>AI Email Threat Platform</p>
        <span className="status-pill">Backend: localhost:8000</span>
        
        {onLogout && (
          <button 
            className="nav-item logout-nav-item" 
            onClick={onLogout} 
            style={{ marginTop: '12px', width: '100%', color: '#f87171' }}
          >
            <LogOut size={18} />
            <span>Sign Out</span>
          </button>
        )}
      </div>
    </aside>
  );
}
