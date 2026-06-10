import { LockIcon } from "./icons";

export default function AskForm({ question, onQuestionChange, onAsk, asking, indexed, repoName, askError }) {
  const ready = indexed && question.trim().length > 0 && !asking;

  function handleKeyDown(e) {
    if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
      e.preventDefault();
      if (ready) onAsk();
    }
  }

  return (
    <section className="panel">
      <div className="panel__heading-row">
        <span className="eyebrow">Step 2</span>
        <h2 className="panel__title">Ask a question</h2>
      </div>
      <p className="panel__desc">
        Ask about architecture, data flow, where something lives — CodeSheriff investigates and cites its sources.
      </p>

      {!indexed && (
        <div className="ask-locked-hint">
          <LockIcon />
          Index a repository above to unlock questions.
        </div>
      )}

      <div className={`ask-body${indexed ? "" : " ask-body--disabled"}`}>
        <textarea
          className="textarea"
          value={question}
          onChange={(e) => onQuestionChange(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={!indexed}
          placeholder="How does authentication work?   ·   Where is rate limiting enforced?   ·   What happens on a failed payment?"
          rows={4}
        />
        <div className="ask-footer">
          <span className="kbd-hint">
            <kbd>⌘ ↵</kbd> to send · scoped to <span className="mono">{indexed ? repoName : "no repo yet"}</span>
          </span>
          <div className="spacer" />
          <button className="btn btn--primary" disabled={!ready} onClick={onAsk}>
            {asking ? (
              <>
                <span className="spinner" />
                <span>Investigating…</span>
              </>
            ) : (
              <span>Ask CodeSheriff</span>
            )}
          </button>
        </div>
      </div>

      {askError && (
        <div className="callout callout--error">
          <span className="callout__icon">!</span>
          <div className="callout__text">
            <strong>Query failed.</strong> {askError}
          </div>
        </div>
      )}
    </section>
  );
}
