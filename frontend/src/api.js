const BASE_URL = "http://localhost:8000";

export async function postQuery(repoPath, repoName, question) {
  const response = await fetch(`${BASE_URL}/api/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ repo_path: repoPath, repo_name: repoName, question }),
  });

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail?.error || `Request failed (${response.status})`);
  }

  return response.json();
}

export async function getTrace(traceId) {
  const response = await fetch(`${BASE_URL}/api/trace/${traceId}`);

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail?.error || `Request failed (${response.status})`);
  }

  return response.json();
}
