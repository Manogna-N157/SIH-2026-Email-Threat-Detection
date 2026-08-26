import React, { useState } from 'react';
import Sidebar from './components/Sidebar';
import Header from './components/Header';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import DashboardPage from './pages/DashboardPage';
import InvestigateEmailPage from './pages/InvestigateEmailPage';
import CasesPage from './pages/CasesPage';
import ThreatIntelPage from './pages/ThreatIntelPage';
import ReportsPage from './pages/ReportsPage';
import AdminUserManagementPage from './pages/AdminUserManagementPage';
import './App.css';

export default function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(() => {
    return sessionStorage.getItem('email_forensics_auth') === 'true';
  });

  const [authView, setAuthView] = useState('login'); // 'login' | 'register'

  const [currentUser, setCurrentUser] = useState(() => {
    const savedUser = sessionStorage.getItem('email_forensics_user');
    return savedUser ? JSON.parse(savedUser) : null;
  });

  const [currentPage, setCurrentPage] = useState('dashboard');
  const [selectedCase, setSelectedCase] = useState(null);

  const handleLoginSuccess = (userSession) => {
    setIsAuthenticated(true);
    setCurrentUser(userSession);
    setCurrentPage('dashboard');
  };

  const handleLogout = () => {
    sessionStorage.removeItem('email_forensics_auth');
    sessionStorage.removeItem('email_forensics_user');
    setIsAuthenticated(false);
    setCurrentUser(null);
    setAuthView('login');
  };

  const handleSelectCase = (caseObj) => {
    setSelectedCase(caseObj);
    setCurrentPage('cases');
  };

  const getPageTitle = () => {
    switch (currentPage) {
      case 'dashboard': return 'Dashboard Overview';
      case 'investigate': return 'Investigate Email (.eml)';
      case 'cases': return 'Investigative Cases';
      case 'threat-intel': return 'Threat Intelligence';
      case 'reports': return 'Forensic PDF Reports';
      case 'admin-users': return 'User Management & Approvals';
      default: return 'Email Forensics Platform';
    }
  };

  // Unauthenticated view: Login or Register
  if (!isAuthenticated) {
    if (authView === 'register') {
      return <RegisterPage onSwitchToLogin={() => setAuthView('login')} />;
    }
    return <LoginPage onLoginSuccess={handleLoginSuccess} onSwitchToRegister={() => setAuthView('register')} />;
  }

  const isAdmin = currentUser?.role === 'ADMIN';

  return (
    <div className="app-layout">
      <Sidebar 
        currentPage={currentPage} 
        setCurrentPage={setCurrentPage} 
        onLogout={handleLogout}
        currentUser={currentUser}
      />
      
      <div className="main-wrapper">
        <Header 
          title={getPageTitle()} 
          onLogout={handleLogout}
          currentUser={currentUser}
        />

        <main className="content-area">
          {currentPage === 'dashboard' && (
            <DashboardPage 
              navigateToInvestigate={() => setCurrentPage('investigate')} 
              onSelectCase={handleSelectCase} 
            />
          )}

          {currentPage === 'investigate' && (
            <InvestigateEmailPage />
          )}

          {currentPage === 'cases' && (
            <CasesPage selectedCaseFromNav={selectedCase} />
          )}

          {currentPage === 'threat-intel' && (
            <ThreatIntelPage />
          )}

          {currentPage === 'reports' && (
            <ReportsPage />
          )}

          {currentPage === 'admin-users' && (
            isAdmin ? (
              <AdminUserManagementPage currentUser={currentUser} />
            ) : (
              <div className="card">
                <div className="alert alert-error">
                  <strong>Unauthorized — Admin access required.</strong>
                </div>
              </div>
            )
          )}
        </main>
      </div>
    </div>
  );
}
