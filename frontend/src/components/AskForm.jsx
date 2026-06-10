import { useState } from "react";

export default function AskForm({ onSubmit, isLoading }) {
  const [repoPath, setRepoPath] = useState("");
  const [repoName, setRepoName] = useState("codesheriff");
  const [question, setQuestion] = useState("");

  function handleSubmit(e) {
    e.preventDefault();
    if (!repoPath || !repoName || !question) return;
    onSubmit({ repoPath, repoName, question });
  }

  return (
    <form className="ask-form" onSubmit={handleSubmit}>
      <div className="field-row">
        <label>
          Repo path
          <input
            type="text"
            value={repoPath}
            onChange={(e) => setRepoPath(e.target.value)}
            placeholder="/Users/you/code/some-repo"
          />
        </label>
        <label>
          Repo name (must be indexed)
          <input
            type="text"
            value={repoName}
            onChange={(e) => setRepoName(e.target.value)}
            placeholder="codesheriff"
          />
        </label>
      </div>
      <label>
        Question
        <textarea
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Where is the login logic?"
          rows={3}
        />
      </label>
      <button type="submit" disabled={isLoading}>
        {isLoading ? "Asking..." : "Ask"}
      </button>
    </form>
  );
}
