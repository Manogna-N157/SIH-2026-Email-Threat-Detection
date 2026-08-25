// Use relative URL so Vite proxy forwards requests from http://localhost:3000/api to http://localhost:8000/api, bypassing browser CORS restrictions.
const BASE_URL = '';

/**
 * Check backend health status
 */
export async function checkHealth() {
  try {
    const response = await fetch(`${BASE_URL}/api/health`);
    if (!response.ok) {
      throw new Error(`HTTP error ${response.status}`);
    }
    return await response.json();
  } catch (err) {
    console.error('Health check failed:', err);
    throw err;
  }
}

/**
 * Upload EML file and get analysis results from POST /api/analyze
 * @param {File} file - .eml file to analyze
 */
export async function analyzeEmail(file) {
  const formData = new FormData();
  formData.append('file', file);

  try {
    const response = await fetch(`${BASE_URL}/api/analyze`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      let errorMessage = `Analysis failed (Status ${response.status})`;
      try {
        const errorData = await response.json();
        if (errorData.detail) {
          errorMessage = errorData.detail;
        }
      } catch (e) {
        // fallback
      }
      throw new Error(errorMessage);
    }

    return await response.json();
  } catch (err) {
    if (err.message && err.message.includes('Failed to fetch')) {
      throw new Error('Unable to connect to backend server. Please make sure FastAPI is running on http://localhost:8000.');
    }
    throw err;
  }
}

/**
 * Fetch list of stored cases from GET /api/cases
 */
export async function getCases() {
  try {
    const response = await fetch(`${BASE_URL}/api/cases`);
    if (!response.ok) {
      throw new Error(`Failed to fetch cases (Status ${response.status})`);
    }
    return await response.json();
  } catch (err) {
    if (err.message && err.message.includes('Failed to fetch')) {
      throw new Error('Backend unavailable on http://localhost:8000');
    }
    throw err;
  }
}

/**
 * Fetch specific case details from GET /api/cases/{caseId}
 * @param {string} caseId
 */
export async function getCaseDetails(caseId) {
  try {
    const response = await fetch(`${BASE_URL}/api/cases/${encodeURIComponent(caseId)}`);
    if (!response.ok) {
      throw new Error(`Failed to fetch case ${caseId} (Status ${response.status})`);
    }
    return await response.json();
  } catch (err) {
    throw err;
  }
}

/**
 * Save analysis as a case via POST /api/cases
 */
export async function saveCase(caseData) {
  try {
    const response = await fetch(`${BASE_URL}/api/cases`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(caseData),
    });
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `Failed to save case (${response.status})`);
    }
    return await response.json();
  } catch (err) {
    throw err;
  }
}

/**
 * Delete a specific stored case via DELETE /api/cases/{caseId}
 * @param {string} caseId
 */
export async function deleteCase(caseId) {
  try {
    const response = await fetch(`${BASE_URL}/api/cases/${encodeURIComponent(caseId)}`, {
      method: 'DELETE',
    });
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `Failed to delete case (${response.status})`);
    }
    return await response.json();
  } catch (err) {
    throw err;
  }
}

/**
 * Delete all stored cases via DELETE /api/cases
 */
export async function deleteAllCases() {
  try {
    const response = await fetch(`${BASE_URL}/api/cases`, {
      method: 'DELETE',
    });
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `Failed to delete all cases (${response.status})`);
    }
    return await response.json();
  } catch (err) {
    throw err;
  }
}

/**
 * Get PDF report URL for a case
 * @param {string} caseId
 */
export function getPdfReportUrl(caseId) {
  return `${BASE_URL}/api/reports/${encodeURIComponent(caseId)}/pdf`;
}
