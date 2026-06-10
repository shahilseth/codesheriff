import { ChevronIcon, SearchIcon, ListIcon, ShieldIcon, PenIcon, ClockIcon } from "./icons";

const STAGE_COLORS = {
  navigator: "#0075de",
  analyst: "#7b3ff2",
  critic: "#dd5b00",
  synthesiser: "#1aae39",
};

function TraceSection({ open, onToggle, icon, iconClass, title, subtitle, timeMs, children }) {
  return (
    <div className="trace-section">
      <button type="button" className="trace-section__header" onClick={onToggle}>
        <span className={`trace-chevron${open ? " trace-chevron--open" : ""}`}>
          <ChevronIcon />
        </span>
        <span className={`trace-icon ${iconClass}`}>{icon}</span>
        <span className="trace-section__titles">
          <span className="trace-section__title">{title}</span>
          <span className="trace-section__subtitle">{subtitle}</span>
        </span>
        <span className="trace-time-badge">{timeMs} ms</span>
      </button>
      {open && <div className="trace-section__body">{children}</div>}
    </div>
  );
}

function NavigatorBody({ data }) {
  return (
    <>
      <div className="trace-subhead">Retrieved chunks</div>
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
          {data.chunks.map((c, i) => (
            <tr key={i}>
              <td className="mono">{c.file_path}</td>
              <td>
                {c.chunk_name} <span className="muted">({c.chunk_type})</span>
              </td>
              <td>
                {c.start_line}-{c.end_line}
              </td>
              <td>{c.similarity_score.toFixed(3)}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <div className="trace-subhead">Relevant commits</div>
      {data.commits.length === 0 ? (
        <p className="muted">No commits retrieved.</p>
      ) : (
        <ul className="trace-list">
          {data.commits.map((c, i) => (
            <li key={i}>
              <span className="mono">{c.hash.slice(0, 8)}</span> {c.message} — {c.author}
            </li>
          ))}
        </ul>
      )}
    </>
  );
}

function AnalystBody({ data }) {
  return (
    <>
      <div className="trace-subhead">Hypothesis</div>
      <p className="trace-text">{data.hypothesis}</p>

      <div className="trace-subhead">Reasoning</div>
      <p className="trace-text">{data.reasoning}</p>

      <div className="trace-subhead">Evidence</div>
      <ul className="trace-list">
        {data.evidence.map((e, i) => (
          <li key={i}>
            <span className="mono">{e.file_path}</span> :: {e.chunk_name} (lines {e.lines}) — {e.relevance}
          </li>
        ))}
      </ul>

      <div className="trace-subhead">Uncertainty</div>
      <p className="trace-text">{data.uncertainty}</p>

      {data.reasoning_gaps.length > 0 && (
        <>
          <div className="trace-subhead">Reasoning gaps</div>
          <ul className="trace-list">
            {data.reasoning_gaps.map((g, i) => (
              <li key={i}>{g}</li>
            ))}
          </ul>
        </>
      )}

      <div className="trace-stat">
        confidence_hint: <strong>{data.confidence_hint.toFixed(2)}</strong>
      </div>
    </>
  );
}

function CriticBody({ data }) {
  return (
    <>
      <div className="trace-subhead">Challenges</div>
      {data.challenges.length === 0 ? (
        <p className="muted">No challenges raised.</p>
      ) : (
        <ul className="trace-list">
          {data.challenges.map((c, i) => (
            <li key={i}>
              <span className={`severity-badge severity-badge--${c.severity}`}>{c.severity}</span>
              <strong> {c.challenge_type}</strong>: {c.description}
              <div className="muted">checkable by: {c.checkable_by}</div>
            </li>
          ))}
        </ul>
      )}

      {data.missing_files.length > 0 && (
        <>
          <div className="trace-subhead">Missing files</div>
          <ul className="trace-list">
            {data.missing_files.map((f, i) => (
              <li key={i}>
                <span className="mono">{f}</span>
              </li>
            ))}
          </ul>
        </>
      )}

      {data.unchecked_assumptions.length > 0 && (
        <>
          <div className="trace-subhead">Unchecked assumptions</div>
          <ul className="trace-list">
            {data.unchecked_assumptions.map((a, i) => (
              <li key={i}>{a}</li>
            ))}
          </ul>
        </>
      )}

      <div className="trace-subhead">Critique summary</div>
      <p className="trace-text">{data.critique_summary}</p>

      <div className="trace-stat">
        confidence_adjustment:{" "}
        <strong className={data.confidence_adjustment < 0 ? "negative" : "positive"}>
          {data.confidence_adjustment >= 0 ? "+" : ""}
          {data.confidence_adjustment.toFixed(2)}
        </strong>
      </div>
    </>
  );
}

function SynthesiserBody({ data }) {
  return (
    <>
      <div className="trace-subhead">Answer</div>
      <p className="trace-text">{data.answer}</p>

      <div className="trace-subhead">Cited files</div>
      {data.cited_files.length === 0 ? (
        <p className="muted">No files cited.</p>
      ) : (
        <ul className="trace-list">
          {data.cited_files.map((f, i) => (
            <li key={i}>
              <span className="mono">{f.file_path}</span> :: {f.chunk_name} (lines {f.lines}) — {f.contribution}
            </li>
          ))}
        </ul>
      )}

      <div className="trace-subhead">Known gaps</div>
      {data.known_gaps.length === 0 ? (
        <p className="muted">None.</p>
      ) : (
        <ul className="trace-list">
          {data.known_gaps.map((g, i) => (
            <li key={i}>{g}</li>
          ))}
        </ul>
      )}
    </>
  );
}

function LatencyBody({ latency }) {
  const stages = ["navigator", "analyst", "critic", "synthesiser"];
  const max = Math.max(...stages.map((s) => latency[s]));
  return (
    <div className="latency-body">
      {stages.map((s) => (
        <div className="latency-row" key={s}>
          <span className="latency-label">{s.charAt(0).toUpperCase() + s.slice(1)}</span>
          <div className="latency-track">
            <div
              className="latency-fill"
              style={{ width: `${max > 0 ? Math.round((latency[s] / max) * 100) : 0}%`, background: STAGE_COLORS[s] }}
            />
          </div>
          <span className="latency-ms">{latency[s]} ms</span>
        </div>
      ))}
      <div className="latency-row latency-row--total">
        <span className="latency-label">Total</span>
        <div className="spacer" />
        <span className="latency-ms">{latency.total} ms</span>
      </div>
    </div>
  );
}

export default function TraceViewer({ trace, traceLoading, traceError, open, onToggle }) {
  return (
    <section className="panel panel--trace panel--result">
      <div className="trace-panel__head">
        <div className="panel__heading-row">
          <span className="eyebrow">Trace</span>
          <h2 className="panel__title">Agent trace</h2>
        </div>
        <p className="panel__desc panel__desc--tight">
          How CodeSheriff reached this answer — four agents in sequence, then the clock.
        </p>
      </div>

      {traceLoading && <div className="trace-loading">Loading trace…</div>}
      {traceError && <div className="trace-error">Failed to load trace: {traceError}</div>}

      {trace && (
        <>
          <TraceSection
            open={open.navigator}
            onToggle={() => onToggle("navigator")}
            icon={<SearchIcon />}
            iconClass="trace-icon--navigator"
            title="Navigator"
            subtitle="Found the relevant files"
            timeMs={trace.latency_ms.navigator}
          >
            <NavigatorBody data={trace.navigator_output} />
          </TraceSection>

          <TraceSection
            open={open.analyst}
            onToggle={() => onToggle("analyst")}
            icon={<ListIcon />}
            iconClass="trace-icon--analyst"
            title="Analyst"
            subtitle="Read and traced the code"
            timeMs={trace.latency_ms.analyst}
          >
            <AnalystBody data={trace.analyst_output} />
          </TraceSection>

          <TraceSection
            open={open.critic}
            onToggle={() => onToggle("critic")}
            icon={<ShieldIcon />}
            iconClass="trace-icon--critic"
            title="Critic"
            subtitle="Verified every claim against source"
            timeMs={trace.latency_ms.critic}
          >
            <CriticBody data={trace.critic_output} />
          </TraceSection>

          <TraceSection
            open={open.synthesiser}
            onToggle={() => onToggle("synthesiser")}
            icon={<PenIcon />}
            iconClass="trace-icon--synthesiser"
            title="Synthesiser"
            subtitle="Wrote the final answer"
            timeMs={trace.latency_ms.synthesiser}
          >
            <SynthesiserBody data={trace.synthesiser_output} />
          </TraceSection>

          <TraceSection
            open={open.latency}
            onToggle={() => onToggle("latency")}
            icon={<ClockIcon />}
            iconClass="trace-icon--latency"
            title="Latency breakdown"
            subtitle="Where the time went"
            timeMs={trace.latency_ms.total}
          >
            <LatencyBody latency={trace.latency_ms} />
          </TraceSection>
        </>
      )}
    </section>
  );
}
