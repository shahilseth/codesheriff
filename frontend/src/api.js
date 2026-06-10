const BASE_URL = "http://localhost:8000";

export async function postIndex(repoSource, repoName) {
  const body = { repo_name: repoName };
  if (repoSource.startsWith("https://github.com")) {
    body.repo_url = repoSource;
  } else {
    body.repo_path = repoSource;
  }

  const response = await fetch(`${BASE_URL}/api/index`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    const responseBody = await response.json().catch(() => null);
    throw new Error(responseBody?.detail?.error || `Request failed (${response.status})`);
  }

  return response.json();
}

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

export async function getHealth() {
  const response = await fetch(`${BASE_URL}/health`);

  if (!response.ok) {
    throw new Error(`Request failed (${response.status})`);
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
