function ConfidenceBadge({ confidence, label }) {
  return (
    <span className={`confidence-badge confidence-${label}`}>
      {label} ({Math.round(confidence * 100)}%)
    </span>
  );
}

export default function AnswerView({ result }) {
  return (
    <div className="answer-view">
      <div className="answer-header">
        <h2>Answer</h2>
        <ConfidenceBadge confidence={result.confidence} label={result.confidence_label} />
      </div>

      <p className="answer-text">{result.answer}</p>

      {result.cited_files.length > 0 && (
        <div className="answer-section">
          <h3>Cited files</h3>
          <ul>
            {result.cited_files.map((cf, i) => (
              <li key={i}>
                <code>{cf.file_path}</code> :: {cf.chunk_name} (lines {cf.lines})
                <div className="contribution">{cf.contribution}</div>
              </li>
            ))}
          </ul>
        </div>
      )}

      {result.known_gaps.length > 0 && (
        <div className="answer-section">
          <h3>Known gaps</h3>
          <ul>
            {result.known_gaps.map((gap, i) => (
              <li key={i}>{gap}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
