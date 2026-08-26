import React, { useState } from 'react';
import { loginUser } from '../api';
import { ShieldAlert, Lock, User, LogIn, AlertCircle } from 'lucide-react';

export default function LoginPage({ onLoginSuccess, onSwitchToRegister }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
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

    try {
      const userResponse = await loginUser(username.trim(), password);
      sessionStorage.setItem('email_forensics_auth', 'true');
      sessionStorage.setItem('email_forensics_user', JSON.stringify(userResponse));
      onLoginSuccess(userResponse);
    } catch (err) {
      setError(err.message || 'Invalid credentials or login failure.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-container">
      <div className="login-card card">
        <div className="login-header">
          <div className="login-logo">
            <ShieldAlert size={36} color="#2563eb" />
          </div>
          <h2>Sign In</h2>
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
            <label htmlFor="login-username">Username / Email</label>
            <div className="input-with-icon">
              <User size={18} className="input-icon" />
              <input
                type="text"
                id="login-username"
                placeholder="Enter username or email"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                autoComplete="username"
                disabled={loading}
              />
            </div>
          </div>

          <div className="form-group">
            <label htmlFor="login-password">Password</label>
            <div className="input-with-icon">
              <Lock size={18} className="input-icon" />
              <input
                type="password"
                id="login-password"
                placeholder="Enter password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
                disabled={loading}
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

        <div className="login-switch-footer" style={{ marginTop: '20px', textAlign: 'center', fontSize: '13px' }}>
          <span>Don't have an account? </span>
          <button
            type="button"
            className="link-btn"
            onClick={onSwitchToRegister}
            style={{ background: 'none', border: 'none', color: '#2563eb', fontWeight: 600, cursor: 'pointer', textDecoration: 'underline' }}
          >
            Register
          </button>
        </div>
      </div>
    </div>
  );
}
