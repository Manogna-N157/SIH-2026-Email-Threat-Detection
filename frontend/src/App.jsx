import React, { useState, useEffect } from 'react';
import Sidebar from './components/Sidebar';
import Header from './components/Header';
import LoginPage from './pages/LoginPage';
import DashboardPage from './pages/DashboardPage';
import InvestigateEmailPage from './pages/InvestigateEmailPage';
import CasesPage from './pages/CasesPage';
import ThreatIntelPage from './pages/ThreatIntelPage';
import ReportsPage from './pages/ReportsPage';
import './App.css';

export default function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(() => {
    return sessionStorage.getItem('email_forensics_auth') === 'true';
  });

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
      default: return 'Email Forensics Platform';
    }
  };

  // If not authenticated, force Login page
  if (!isAuthenticated) {
    return <LoginPage onLoginSuccess={handleLoginSuccess} />;
  }

  return (
    <div className="app-layout">
      <Sidebar 
        currentPage={currentPage} 
        setCurrentPage={setCurrentPage} 
        onLogout={handleLogout}
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
        </main>
      </div>
    </div>
  );
}
