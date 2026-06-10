import { useState } from "react";
import AskForm from "./components/AskForm";
import AnswerView from "./components/AnswerView";
import TraceViewer from "./components/TraceViewer";
import { postQuery, getTrace } from "./api";
import "./App.css";

function App() {
  const [result, setResult] = useState(null);
  const [trace, setTrace] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  async function handleSubmit({ repoPath, repoName, question }) {
    setIsLoading(true);
    setError(null);
    setResult(null);
    setTrace(null);

    try {
      const queryResult = await postQuery(repoPath, repoName, question);
      setResult(queryResult);

      const traceData = await getTrace(queryResult.trace_id);
      setTrace(traceData);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="app">
      <h1>CodeSheriff</h1>
      <p className="subtitle">Ask plain-English questions about a codebase.</p>

      <AskForm onSubmit={handleSubmit} isLoading={isLoading} />

      {error && <div className="error-banner">{error}</div>}

      {result && <AnswerView result={result} />}
      {trace && <TraceViewer trace={trace} />}
    </div>
  );
}

export default App;
