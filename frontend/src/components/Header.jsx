import React, { useEffect, useState } from 'react';
import { checkHealth } from '../api';
import { LogOut, User, Shield } from 'lucide-react';

export default function Header({ title, onLogout, currentUser }) {
  const [backendStatus, setBackendStatus] = useState('checking');

  useEffect(() => {
    const check = async () => {
      try {
        await checkHealth();
        setBackendStatus('online');
      } catch {
        setBackendStatus('offline');
      }
    };
    check();
    const interval = setInterval(check, 15000);
    return () => clearInterval(interval);
  }, []);

  return (
    <header className="top-header">
      <div className="header-title">
        <h1>{title}</h1>
      </div>

      <div className="header-right">
        <div className="header-status">
          <span className={`status-indicator ${backendStatus}`}>
            <span className="dot"></span>
            FastAPI Backend: {backendStatus === 'online' ? 'Connected' : backendStatus === 'offline' ? 'Offline (Check http://localhost:8000)' : 'Checking...'}
          </span>
        </div>

        {currentUser && (
          <div className="user-profile">
            <User size={16} />
            <span>Welcome, <strong>{currentUser.username}</strong></span>
            <span className={`role-badge ${currentUser.role === 'ADMIN' ? 'role-admin' : 'role-user'}`}>
              <Shield size={12} /> Role: {currentUser.role || 'USER'}
            </span>
          </div>
        )}

        {onLogout && (
          <button className="btn btn-secondary btn-sm logout-btn" onClick={onLogout} title="Sign Out">
            <LogOut size={14} />
            <span>Logout</span>
          </button>
        )}
      </div>
    </header>
  );
}
