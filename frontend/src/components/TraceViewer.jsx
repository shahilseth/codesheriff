import { useState } from "react";

function Section({ title, defaultOpen, children }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="trace-section">
      <button type="button" className="trace-section-header" onClick={() => setOpen(!open)}>
        {open ? "▼" : "▶"} {title}
      </button>
      {open && <div className="trace-section-body">{children}</div>}
    </div>
  );
}

function NavigatorSection({ navigatorOutput }) {
  return (
    <Section title="Navigator — retrieval" defaultOpen={false}>
      <h4>Retrieved chunks</h4>
      <table className="trace-table">
        <thead>
          <tr>
            <th>File</th>
            <th>Chunk</th>
            <th>Lines</th>
            <th>Similarity</th>
          </tr>
        </thead>
        <tbody>
          {navigatorOutput.chunks.map((chunk, i) => (
            <tr key={i}>
              <td><code>{chunk.file_path}</code></td>
              <td>{chunk.chunk_name} ({chunk.chunk_type})</td>
              <td>{chunk.start_line}-{chunk.end_line}</td>
              <td>{chunk.similarity_score.toFixed(3)}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <h4>Relevant commits</h4>
      {navigatorOutput.commits.length === 0 ? (
        <p className="muted">(none retrieved)</p>
      ) : (
        <ul>
          {navigatorOutput.commits.map((commit, i) => (
            <li key={i}>
              <code>{commit.hash.slice(0, 8)}</code> {commit.message} — {commit.author}
            </li>
          ))}
        </ul>
      )}
    </Section>
  );
}

function AnalystSection({ analystOutput }) {
  return (
    <Section title="Analyst — reasoning" defaultOpen={false}>
      <h4>Hypothesis</h4>
      <p>{analystOutput.hypothesis}</p>

      <h4>Reasoning</h4>
      <p className="reasoning-text">{analystOutput.reasoning}</p>

      <h4>Evidence</h4>
      <ul>
        {analystOutput.evidence.map((ev, i) => (
          <li key={i}>
            <code>{ev.file_path}</code> :: {ev.chunk_name} (lines {ev.lines}) — {ev.relevance}
          </li>
        ))}
      </ul>

      <h4>Uncertainty</h4>
      <p>{analystOutput.uncertainty}</p>

      <h4>Reasoning gaps</h4>
      <ul>
        {analystOutput.reasoning_gaps.map((gap, i) => (
          <li key={i}>{gap}</li>
        ))}
      </ul>

      <p className="trace-stat">
        confidence_hint: <strong>{analystOutput.confidence_hint.toFixed(2)}</strong>
      </p>
    </Section>
  );
}

function CriticSection({ criticOutput }) {
  return (
    <Section title="Critic — adversarial review" defaultOpen={true}>
      <h4>Challenges</h4>
      {criticOutput.challenges.length === 0 ? (
        <p className="muted">(no challenges raised)</p>
      ) : (
        <ul>
          {criticOutput.challenges.map((c, i) => (
            <li key={i}>
              <span className={`severity severity-${c.severity}`}>{c.severity}</span>{" "}
              <strong>{c.challenge_type}</strong>: {c.description}
              <div className="muted">checkable by: {c.checkable_by}</div>
            </li>
          ))}
        </ul>
      )}

      <h4>Missing files</h4>
      {criticOutput.missing_files.length === 0 ? (
        <p className="muted">(none)</p>
      ) : (
        <ul>
          {criticOutput.missing_files.map((f, i) => (
            <li key={i}><code>{f}</code></li>
          ))}
        </ul>
      )}

      <h4>Unchecked assumptions</h4>
      {criticOutput.unchecked_assumptions.length === 0 ? (
        <p className="muted">(none)</p>
      ) : (
        <ul>
          {criticOutput.unchecked_assumptions.map((a, i) => (
            <li key={i}>{a}</li>
          ))}
        </ul>
      )}

      <h4>Critique summary</h4>
      <p>{criticOutput.critique_summary}</p>

      <p className="trace-stat">
        confidence_adjustment:{" "}
        <strong className={criticOutput.confidence_adjustment < 0 ? "negative" : "positive"}>
          {criticOutput.confidence_adjustment >= 0 ? "+" : ""}
          {criticOutput.confidence_adjustment.toFixed(2)}
        </strong>
      </p>
    </Section>
  );
}

function SynthesiserSection({ synthesiserOutput }) {
  return (
    <Section title="Synthesiser — final answer" defaultOpen={false}>
      <h4>Answer</h4>
      <p className="reasoning-text">{synthesiserOutput.answer}</p>

      <h4>Cited files</h4>
      <ul>
        {synthesiserOutput.cited_files.map((cf, i) => (
          <li key={i}>
            <code>{cf.file_path}</code> :: {cf.chunk_name} (lines {cf.lines}) — {cf.contribution}
          </li>
        ))}
      </ul>

      <h4>Known gaps</h4>
      <ul>
        {synthesiserOutput.known_gaps.map((g, i) => (
          <li key={i}>{g}</li>
        ))}
      </ul>
    </Section>
  );
}

function LatencySection({ latencyMs }) {
  const steps = ["navigator", "analyst", "critic", "synthesiser"];
  return (
    <Section title="Latency breakdown" defaultOpen={false}>
      <table className="trace-table">
        <thead>
          <tr>
            <th>Step</th>
            <th>ms</th>
          </tr>
        </thead>
        <tbody>
          {steps.map((step) => (
            <tr key={step}>
              <td>{step}</td>
              <td>{latencyMs[step]}</td>
            </tr>
          ))}
          <tr>
            <td><strong>total</strong></td>
            <td><strong>{latencyMs.total}</strong></td>
          </tr>
        </tbody>
      </table>
    </Section>
  );
}

export default function TraceViewer({ trace }) {
  return (
    <div className="trace-viewer">
      <h2>Trace</h2>
      <p className="trace-meta">
        Confidence: <strong>{trace.confidence.toFixed(2)}</strong> ({trace.confidence_label})
        {" — "}
        analyst {trace.analyst_output.confidence_hint.toFixed(2)}{" "}
        {trace.critic_output.confidence_adjustment >= 0 ? "+" : ""}
        {trace.critic_output.confidence_adjustment.toFixed(2)} (critic)
      </p>

      <NavigatorSection navigatorOutput={trace.navigator_output} />
      <AnalystSection analystOutput={trace.analyst_output} />
      <CriticSection criticOutput={trace.critic_output} />
      <SynthesiserSection synthesiserOutput={trace.synthesiser_output} />
      <LatencySection latencyMs={trace.latency_ms} />
    </div>
  );
}
