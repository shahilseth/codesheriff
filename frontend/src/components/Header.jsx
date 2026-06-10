import { BrandStarIcon } from "./icons";

export default function Header({ repoName, indexed }) {
  return (
    <header className="app-header">
      <div className="app-header__inner">
        <div className="brand-mark">
          <BrandStarIcon />
        </div>
        <div className="brand-text">
          <div className="brand-title">CodeSheriff</div>
          <div className="brand-tagline">Answers about your codebase, with the receipts</div>
        </div>
        <div className="spacer" />
        {indexed && (
          <div className="repo-pill">
            <span className="repo-pill__dot" />
            <span className="repo-pill__name">{repoName}</span>
            <span className="repo-pill__suffix">indexed</span>
          </div>
        )}
      </div>
    </header>
  );
}
