import React, { useState } from 'react';
import { ShieldAlert, Lock, User, LogIn, AlertCircle } from 'lucide-react';

export default function LoginPage({ onLoginSuccess }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = (e) => {
    e.preventDefault();
    setError('');

    // Input validation
    if (!username.trim()) {
      setError('Please enter your email or username.');
      return;
    }
    if (!password) {
      setError('Please enter your password.');
      return;
    }

    setLoading(true);

    // Simple demo authentication check for SIH prototype
    setTimeout(() => {
      // Allow demo credentials or any valid non-empty username/password
      if (
        (username.trim().toLowerCase() === 'admin' && password === 'admin123') ||
        (username.trim().toLowerCase() === 'analyst@sih.gov.in' && password === 'sih2026') ||
        (username.trim().length > 0 && password.length >= 4)
      ) {
        const userSession = {
          username: username.trim(),
          loginTime: new Date().toISOString(),
        };
        sessionStorage.setItem('email_forensics_auth', 'true');
        sessionStorage.setItem('email_forensics_user', JSON.stringify(userSession));
        onLoginSuccess(userSession);
      } else {
        setError('Invalid username or password. (Demo credentials: admin / admin123)');
      }
      setLoading(false);
    }, 400);
  };

  return (
    <div className="login-container">
      <div className="login-card card">
        <div className="login-header">
          <div className="login-logo">
            <ShieldAlert size={36} color="#2563eb" />
          </div>
          <h2>Email Forensics Platform</h2>
          <p className="subtitle">
            AI-Powered Email Threat Detection, GeoLocation and Forensic Intelligence Platform
          </p>
        </div>

        {error && (
          <div className="alert alert-error">
            <AlertCircle size={18} />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="login-form">
          <div className="form-group">
            <label htmlFor="username">Username or Email</label>
            <div className="input-with-icon">
              <User size={18} className="input-icon" />
              <input
                type="text"
                id="username"
                placeholder="Enter username (e.g. admin)"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                autoComplete="username"
              />
            </div>
          </div>

          <div className="form-group">
            <label htmlFor="password">Password</label>
            <div className="input-with-icon">
              <Lock size={18} className="input-icon" />
              <input
                type="password"
                id="password"
                placeholder="Enter password (e.g. admin123)"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
              />
            </div>
          </div>

          <button type="submit" className="btn btn-primary btn-lg login-btn" disabled={loading}>
            {loading ? 'Authenticating...' : (
              <>
                <LogIn size={18} /> Sign In
              </>
            )}
          </button>
        </form>

        <div className="login-demo-tip">
          <p><strong>SIH Prototype Demo Credentials:</strong></p>
          <p>Username: <code>admin</code> | Password: <code>admin123</code></p>
        </div>
      </div>
    </div>
  );
}
