import { GithubIcon, FolderIcon, CheckIcon } from "./icons";

export default function IndexForm({
  repoInput,
  onRepoInputChange,
  repoName,
  onRepoNameChange,
  isGithub,
  isLocal,
  indexing,
  indexed,
  indexError,
  fileCount,
  steps,
  canIndex,
  onSubmit,
  onReindex,
}) {
  return (
    <section className="panel">
      <div className="panel__heading-row">
        <span className="eyebrow">Step 1</span>
        <h2 className="panel__title">Index a repository</h2>
      </div>
      <p className="panel__desc">
        Paste a GitHub URL or a local path — CodeSheriff detects which automatically.
      </p>

      <label className="field">
        <span className="field__label">Repository</span>
        <div className="input-wrap">
          <input
            type="text"
            className="text-input"
            value={repoInput}
            onChange={(e) => onRepoInputChange(e.target.value)}
            placeholder="https://github.com/org/repo · /Users/you/code/repo"
            disabled={indexing}
          />
          {isGithub && (
            <span className="source-badge source-badge--github">
              <GithubIcon /> GitHub
            </span>
          )}
          {isLocal && (
            <span className="source-badge source-badge--local">
              <FolderIcon /> Local path
            </span>
          )}
        </div>
      </label>

      <label className="field field--narrow">
        <span className="field__label">Repo name</span>
        <input
          type="text"
          className="text-input text-input--mono"
          value={repoName}
          onChange={(e) => onRepoNameChange(e.target.value)}
          placeholder="auto-filled from the URL"
          disabled={indexing}
        />
        <span className="field__hint">Scopes every question to this repo — edit if you like.</span>
      </label>

      {indexing && (
        <div className="progress-stepper">
          {steps.map((st) => (
            <div className="step" key={st.label}>
              {st.status === "done" && (
                <span className="step__icon step__icon--done">
                  <CheckIcon />
                </span>
              )}
              {st.status === "active" && <span className="step__icon step__icon--active" />}
              {st.status === "pending" && <span className="step__icon step__icon--pending" />}
              <span className="step__label">{st.label}</span>
            </div>
          ))}
        </div>
      )}

      {indexError && (
        <div className="callout callout--error">
          <span className="callout__icon">!</span>
          <div className="callout__text">
            <strong>Indexing failed.</strong> {indexError}
          </div>
        </div>
      )}

      {indexed && (
        <div className="callout callout--success">
          <span className="callout__icon">
            <CheckIcon />
          </span>
          <div className="callout__text">
            <strong>Indexed {repoName}</strong> — {fileCount.toLocaleString()} source files parsed and embedded. Ask anything below.
          </div>
        </div>
      )}

      <div className="button-row">
        {!indexed && (
          <button className="btn btn--primary" disabled={!canIndex} onClick={onSubmit}>
            {indexing ? (
              <>
                <span className="spinner" />
                <span>Indexing…</span>
              </>
            ) : (
              <span>Index repository</span>
            )}
          </button>
        )}
        {indexed && (
          <>
            <button className="btn btn--secondary" onClick={onReindex}>
              Re-index
            </button>
            <span className="field__hint field__hint--inline">or edit the fields above</span>
          </>
        )}
      </div>
    </section>
  );
}
