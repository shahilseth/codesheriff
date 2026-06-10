import { FileIcon } from "./icons";

const CONFIDENCE_CLASS = {
  high: "confidence-pill--high",
  medium: "confidence-pill--medium",
  low: "confidence-pill--low",
};

const CONFIDENCE_BAR_CLASS = {
  high: "confidence-bar__fill--high",
  medium: "confidence-bar__fill--medium",
  low: "confidence-bar__fill--low",
};

export default function AnswerView({ result, repoName, fileCount, trace }) {
  const pct = Math.round(result.confidence * 100);
  const pillClass = CONFIDENCE_CLASS[result.confidence_label] || CONFIDENCE_CLASS.medium;
  const barClass = CONFIDENCE_BAR_CLASS[result.confidence_label] || CONFIDENCE_BAR_CLASS.medium;
  const paragraphs = result.answer.split(/\n\s*\n/).filter((p) => p.trim().length > 0);

  return (
    <section className="panel panel--result">
      <div className="answer-header">
        <h2 className="panel__title">Answer</h2>
        <div className="spacer" />
        <span className={`confidence-pill ${pillClass}`}>
          <span className="confidence-pill__dot" />
          {result.confidence_label} confidence
        </span>
        <div className="confidence-bar-wrap">
          <div className="confidence-bar">
            <div className={`confidence-bar__fill ${barClass}`} style={{ width: `${pct}%` }} />
          </div>
          <span className={`confidence-pct ${pillClass}`}>{pct}%</span>
        </div>
      </div>

      <div className="question-quote">
        <div className="question-quote__bar" />
        <div className="question-quote__text">{result.question}</div>
      </div>

      <div className="answer-paragraphs">
        {paragraphs.map((p, i) => (
          <p key={i}>{p}</p>
        ))}
      </div>

      <div className="answer-grid">
        <div>
          <div className="section-label">Cited files</div>
          {result.cited_files.length === 0 && <p className="muted">No files cited.</p>}
          {result.cited_files.map((f, i) => (
            <div className="cited-file-row" key={i}>
              <div className="cited-file-row__main">
                <FileIcon />
                <span className="cited-file__path">{f.file_path}</span>
                <span className="cited-file__lines">{f.lines}</span>
              </div>
              <div className="cited-file__contribution">{f.contribution}</div>
            </div>
          ))}
        </div>
        <div>
          <div className="section-label">Known gaps</div>
          {result.known_gaps.length === 0 && <p className="muted">No known gaps.</p>}
          {result.known_gaps.map((g, i) => (
            <div className="gap-row" key={i}>
              <span className="gap-dot" />
              <span className="gap-text">{g}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="answer-footer">
        Answered from <span className="mono">{repoName}</span>
        {trace && (
          <>
            {" · searched "}
            {trace.navigator_output.retrieved_file_paths.length} of {fileCount.toLocaleString()} files
            {" · "}
            {trace.latency_ms.total.toLocaleString()} ms
          </>
        )}
      </div>
    </section>
  );
}
