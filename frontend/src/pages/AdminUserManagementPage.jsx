import React, { useEffect, useState } from 'react';
import { getAdminUsers, approveUser, rejectUser, deleteUser } from '../api';
import Badge from '../components/Badge';
import { Users, ShieldCheck, CheckCircle2, XCircle, Trash2, RefreshCw, AlertCircle } from 'lucide-react';

export default function AdminUserManagementPage({ currentUser }) {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [actionFeedback, setActionFeedback] = useState({ type: '', message: '' });

  const isAdmin = currentUser?.role === 'ADMIN';

  const fetchUsers = async () => {
    if (!isAdmin) return;
    setLoading(true);
    setError('');
    try {
      const data = await getAdminUsers();
      setUsers(data || []);
    } catch (err) {
      setError(err.message || 'Failed to fetch registered users list from backend.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, [currentUser]);

  if (!isAdmin) {
    return (
      <div className="page-container">
        <div className="card">
          <div className="alert alert-error" style={{ fontSize: '16px', padding: '20px' }}>
            <AlertCircle size={24} />
            <div>
              <strong>Access Denied — Unauthorized</strong>
              <p style={{ margin: '4px 0 0 0', fontSize: '14px' }}>
                Admin access required to view user approval controls. You are currently logged in as a normal USER.
              </p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  const handleApprove = async (userObj) => {
    setActionFeedback({ type: '', message: '' });
    try {
      await approveUser(userObj.id);
      setActionFeedback({ type: 'success', message: `User "${userObj.username}" has been APPROVED.` });
      await fetchUsers();
    } catch (err) {
      setActionFeedback({ type: 'error', message: `Approval failed: ${err.message}` });
    }
  };

  const handleReject = async (userObj) => {
    setActionFeedback({ type: '', message: '' });
    try {
      await rejectUser(userObj.id);
      setActionFeedback({ type: 'success', message: `User "${userObj.username}" registration has been REJECTED.` });
      await fetchUsers();
    } catch (err) {
      setActionFeedback({ type: 'error', message: `Rejection failed: ${err.message}` });
    }
  };

  const handleDelete = async (userObj) => {
    if (userObj.username === currentUser?.username) {
      alert('You cannot delete your own admin account while logged in.');
      return;
    }
    const confirmed = window.confirm(`Are you sure you want to delete user "${userObj.username}"?`);
    if (!confirmed) return;

    setActionFeedback({ type: '', message: '' });
    try {
      await deleteUser(userObj.id);
      setActionFeedback({ type: 'success', message: `User "${userObj.username}" deleted successfully.` });
      await fetchUsers();
    } catch (err) {
      setActionFeedback({ type: 'error', message: `Deletion failed: ${err.message}` });
    }
  };

  const pendingCount = users.filter((u) => u.status === 'PENDING').length;

  return (
    <div className="page-container">
      <div className="card">
        <div className="card-header">
          <div>
            <h2><Users size={22} /> User Registration & Approval Management</h2>
            <p className="subtitle">
              Admin Authority Panel: Review, approve, or reject user registrations (GET /api/admin/users).
            </p>
          </div>
          <button className="btn btn-secondary btn-sm" onClick={fetchUsers}>
            <RefreshCw size={14} /> Refresh Users
          </button>
        </div>

        {actionFeedback.message && (
          <div className={`alert alert-${actionFeedback.type === 'error' ? 'error' : 'success'}`} style={{ marginBottom: '16px' }}>
            {actionFeedback.type === 'error' ? <AlertCircle size={16} /> : <CheckCircle2 size={16} />}
            <span>{actionFeedback.message}</span>
          </div>
        )}

        {error && (
          <div className="alert alert-error">
            <AlertCircle size={16} /> {error}
          </div>
        )}

        {pendingCount > 0 && (
          <div className="alert alert-warning" style={{ marginBottom: '16px' }}>
            <ShieldCheck size={18} />
            <span>
              <strong>{pendingCount} Pending User Registration(s)</strong> awaiting administrative review and approval.
            </span>
          </div>
        )}

        {loading ? (
          <p className="loading-text">Loading registered users...</p>
        ) : users.length === 0 ? (
          <div className="empty-state">
            <p>No registered users found.</p>
          </div>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Username</th>
                <th>Email</th>
                <th>Role</th>
                <th>Registration Status</th>
                <th>Created At</th>
                <th>Admin Actions</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => {
                const isPending = u.status === 'PENDING';
                const isApproved = u.status === 'APPROVED';
                const isRejected = u.status === 'REJECTED';

                return (
                  <tr key={u.id} style={{ background: isPending ? '#fffbeb' : undefined }}>
                    <td>
                      <strong>{u.username}</strong>
                      {u.username === currentUser?.username && <span className="tag" style={{ marginLeft: '6px' }}>You</span>}
                    </td>
                    <td>{u.email}</td>
                    <td>
                      <span className={`tag ${u.role === 'ADMIN' ? 'tag-admin' : ''}`}>
                        {u.role}
                      </span>
                    </td>
                    <td>
                      <span className={`risk-score-pill ${isApproved ? 'score-low' : isPending ? 'score-med' : 'score-high'}`}>
                        {u.status}
                      </span>
                    </td>
                    <td>{u.created_at ? new Date(u.created_at).toLocaleString() : 'N/A'}</td>
                    <td>
                      <div style={{ display: 'flex', gap: '6px' }}>
                        {!isApproved && (
                          <button
                            className="btn btn-primary btn-sm"
                            onClick={() => handleApprove(u)}
                            title="Approve User"
                          >
                            <CheckCircle2 size={12} /> Approve
                          </button>
                        )}

                        {!isRejected && (
                          <button
                            className="btn btn-secondary btn-sm"
                            onClick={() => handleReject(u)}
                            title="Reject User"
                          >
                            <XCircle size={12} /> Reject
                          </button>
                        )}

                        <button
                          className="btn btn-danger-outline btn-sm"
                          onClick={() => handleDelete(u)}
                          disabled={u.username === currentUser?.username}
                          title="Delete User"
                        >
                          <Trash2 size={12} />
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
