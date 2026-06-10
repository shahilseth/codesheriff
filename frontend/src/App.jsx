import { useEffect, useState } from "react";
import Header from "./components/Header";
import IndexForm from "./components/IndexForm";
import AskForm from "./components/AskForm";
import AnswerView from "./components/AnswerView";
import TraceViewer from "./components/TraceViewer";
import { postIndex, postQuery, getTrace, getHealth } from "./api";
import "./App.css";

const GITHUB_PREFIX = "https://github.com";

const STEP_LABELS = [
  "Cloning repository",
  "Parsing source files",
  "Building symbol graph",
  "Generating embeddings",
  "Finalizing index",
];

function deriveRepoNameFromUrl(url) {
  const trimmed = url.replace(/\/+$/, "");
  const segment = trimmed.split("/").pop() || "";
  return segment.replace(/\.git$/, "");
}

function App() {
  // health
  const [backendDown, setBackendDown] = useState(false);

  // index state
  const [repoInput, setRepoInput] = useState("");
  const [repoName, setRepoName] = useState("");
  const [repoNameTouched, setRepoNameTouched] = useState(false);
  const [indexing, setIndexing] = useState(false);
  const [indexed, setIndexed] = useState(false);
  const [indexError, setIndexError] = useState(null);
  const [fileCount, setFileCount] = useState(0);
  const [stepIdx, setStepIdx] = useState(-1);
  const [indexedRepoPath, setIndexedRepoPath] = useState("");

  // ask state
  const [question, setQuestion] = useState("");
  const [asking, setAsking] = useState(false);
  const [askError, setAskError] = useState(null);
  const [result, setResult] = useState(null);

  // trace state
  const [trace, setTrace] = useState(null);
  const [traceLoading, setTraceLoading] = useState(false);
  const [traceError, setTraceError] = useState(null);
  const [traceOpen, setTraceOpen] = useState({
    navigator: false,
    analyst: false,
    critic: true,
    synthesiser: false,
    latency: false,
  });

  useEffect(() => {
    getHealth().catch(() => setBackendDown(true));
  }, []);

  // animate the indexing progress stepper while a request is in flight
  useEffect(() => {
    if (!indexing) return undefined;
    setStepIdx(0);
    const id = setInterval(() => {
      setStepIdx((i) => (i < STEP_LABELS.length - 1 ? i + 1 : i));
    }, 700);
    return () => clearInterval(id);
  }, [indexing]);

  const isGithub = repoInput.startsWith(GITHUB_PREFIX);
  const isLocal = repoInput.trim().length > 0 && !isGithub;
  const canIndex = repoInput.trim().length > 0 && repoName.trim().length > 0 && !indexing;

  function handleRepoInputChange(value) {
    setRepoInput(value);
    setIndexError(null);
    if (value.startsWith(GITHUB_PREFIX) && !repoNameTouched) {
      setRepoName(deriveRepoNameFromUrl(value));
    }
  }

  function handleRepoNameChange(value) {
    setRepoNameTouched(true);
    setRepoName(value);
  }

  async function handleIndex() {
    if (!canIndex) return;
    setIndexing(true);
    setIndexError(null);

    try {
      const res = await postIndex(repoInput, repoName);
      setFileCount(res.files);
      setIndexed(true);
      setIndexedRepoPath(isGithub ? "" : repoInput);
      setResult(null);
      setTrace(null);
      setQuestion("");
    } catch (err) {
      setIndexError(err.message);
      setStepIdx(-1);
    } finally {
      setIndexing(false);
    }
  }

  function handleReindex() {
    setIndexed(false);
    setIndexError(null);
    setStepIdx(-1);
    setResult(null);
    setTrace(null);
    setTraceError(null);
  }

  async function handleAsk() {
    if (!indexed || !question.trim() || asking) return;
    const q = question.trim();

    setAsking(true);
    setAskError(null);
    setResult(null);
    setTrace(null);
    setTraceError(null);

    try {
      const res = await postQuery(indexedRepoPath, repoName, q);
      setResult(res);
      setTraceLoading(true);
      try {
        const traceData = await getTrace(res.trace_id);
        setTrace(traceData);
      } catch (err) {
        setTraceError(err.message);
      } finally {
        setTraceLoading(false);
      }
    } catch (err) {
      setAskError(err.message);
    } finally {
      setAsking(false);
    }
  }

  function handleToggleTrace(key) {
    setTraceOpen((prev) => ({ ...prev, [key]: !prev[key] }));
  }

  const steps = STEP_LABELS.map((label, i) => {
    const status = stepIdx > i ? "done" : stepIdx === i ? "active" : "pending";
    return { label, status };
  });

  return (
    <div className="app-shell">
      <Header repoName={repoName} indexed={indexed} />

      {backendDown && (
        <div className="health-banner">
          <div className="callout callout--error callout--top">
            <span className="callout__icon">!</span>
            <div className="callout__text">
              <strong>Backend unreachable.</strong> Make sure the CodeSheriff API is running.
            </div>
          </div>
        </div>
      )}

      <main className="app-main">
        <IndexForm
          repoInput={repoInput}
          onRepoInputChange={handleRepoInputChange}
          repoName={repoName}
          onRepoNameChange={handleRepoNameChange}
          isGithub={isGithub}
          isLocal={isLocal}
          indexing={indexing}
          indexed={indexed}
          indexError={indexError}
          fileCount={fileCount}
          steps={steps}
          canIndex={canIndex}
          onSubmit={handleIndex}
          onReindex={handleReindex}
        />

        <AskForm
          question={question}
          onQuestionChange={setQuestion}
          onAsk={handleAsk}
          asking={asking}
          indexed={indexed}
          repoName={repoName}
          askError={askError}
        />

        {result && <AnswerView result={result} repoName={repoName} fileCount={fileCount} trace={trace} />}

        {result && (
          <TraceViewer
            trace={trace}
            traceLoading={traceLoading}
            traceError={traceError}
            open={traceOpen}
            onToggle={handleToggleTrace}
          />
        )}
      </main>
    </div>
  );
}

export default App;
