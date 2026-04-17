import { useState } from 'react';
import './FinalReport.css';

const CONCLUSION_COLORS = {
  approved: '#e8f5e9',
  conditional: '#fff8e1',
  rejected: '#fce4ec',
};

const CONCLUSION_TEXT_COLORS = {
  approved: '#1b5e20',
  conditional: '#f57f17',
  rejected: '#b71c1c',
};

function FinalReport({ report, domainResults, contextDiscussions, onNewReview }) {
  const [showDeliberation, setShowDeliberation] = useState(false);

  if (!report) {
    return <div className="final-report"><p>No report available.</p></div>;
  }

  const conclusion = report.overall_conclusion || 'unknown';

  const handleExportJSON = () => {
    const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `ethics-review-${report.project_name || 'report'}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="final-report">
      {/* Header */}
      <div
        className="report-header"
        style={{
          background: CONCLUSION_COLORS[conclusion] || '#f5f5f5',
          color: CONCLUSION_TEXT_COLORS[conclusion] || '#333',
        }}
      >
        <div className="report-header-top">
          <div>
            <h2>{report.project_name || 'Ethics Review Report'}</h2>
            <div className="report-meta">
              {report.review_date && <span>Date: {report.review_date}</span>}
              {report.risk_level && <span>Risk: {report.risk_level}</span>}
            </div>
          </div>
          <div className="conclusion-badge">
            {conclusion.toUpperCase()}
          </div>
        </div>
        {report.conclusion_rationale && (
          <p className="conclusion-rationale">{report.conclusion_rationale}</p>
        )}
      </div>

      {/* Domain Assessments */}
      {report.domain_assessments && report.domain_assessments.length > 0 && (
        <section className="report-section">
          <h3>Domain Assessments / 各领域评估</h3>
          <div className="domain-cards">
            {report.domain_assessments.map((da, i) => (
              <div key={i} className="domain-card">
                <div className="domain-card-header">
                  <span className="domain-name">{da.domain}</span>
                  <span className={`assessment-pill assessment-${da.assessment}`}>
                    {da.assessment}
                  </span>
                </div>
                {da.key_risks && da.key_risks.length > 0 && (
                  <div className="domain-risks">
                    {da.key_risks.map((risk, j) => (
                      <div key={j} className="risk-item">
                        <span className={`severity-dot severity-${risk.severity}`} />
                        <span className="risk-id">{risk.risk_id}</span>
                        <span>{risk.description}</span>
                      </div>
                    ))}
                  </div>
                )}
                {da.recommendations && da.recommendations.length > 0 && (
                  <ul className="domain-recommendations">
                    {da.recommendations.map((rec, j) => (
                      <li key={j}>{rec}</li>
                    ))}
                  </ul>
                )}
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Cross-Domain Findings */}
      {report.cross_domain_findings && report.cross_domain_findings.length > 0 && (
        <section className="report-section">
          <h3>Cross-Domain Findings / 跨域发现</h3>
          {report.cross_domain_findings.map((cdf, i) => (
            <div key={i} className="cross-finding-card">
              <div className="cross-finding-topic">{cdf.topic}</div>
              <p>{cdf.finding}</p>
              <div className="cross-finding-meta">
                Domains: {cdf.involved_domains?.join(', ')}
              </div>
              {cdf.recommendation && (
                <div className="cross-finding-rec">Recommendation: {cdf.recommendation}</div>
              )}
            </div>
          ))}
        </section>
      )}

      {/* Unresolved Divergences */}
      {report.unresolved_divergences && report.unresolved_divergences.length > 0 && (
        <section className="report-section">
          <h3>Unresolved Divergences / 未解决分歧</h3>
          {report.unresolved_divergences.map((div, i) => (
            <div key={i} className="divergence-card">
              <p className="divergence-desc">{div.description}</p>
              {div.positions && (
                <div className="divergence-positions">
                  {Object.entries(div.positions).map(([domain, position]) => (
                    <div key={domain} className="position-item">
                      <strong>{domain}:</strong> {position}
                    </div>
                  ))}
                </div>
              )}
              {div.chairman_comment && (
                <div className="chairman-comment">Chairman: {div.chairman_comment}</div>
              )}
            </div>
          ))}
        </section>
      )}

      {/* Priority Actions */}
      {report.priority_actions && report.priority_actions.length > 0 && (
        <section className="report-section">
          <h3>Priority Actions / 修改事项</h3>
          <table className="actions-table">
            <thead>
              <tr>
                <th>Priority</th>
                <th>Action</th>
                <th>Domain</th>
                <th>Deadline</th>
              </tr>
            </thead>
            <tbody>
              {report.priority_actions.map((action, i) => (
                <tr key={i}>
                  <td><span className={`priority-badge priority-${action.priority}`}>{action.priority}</span></td>
                  <td>{action.action}</td>
                  <td>{action.responsible_domain}</td>
                  <td>{action.deadline_suggestion || '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}

      {/* Chairman Notes */}
      {report.chairman_notes && (
        <section className="report-section chairman-notes-section">
          <h3>Chairman Notes / 主席评语</h3>
          <p>{report.chairman_notes}</p>
        </section>
      )}

      {/* Deliberation Log (toggleable) */}
      <section className="report-section">
        <button
          className="btn-secondary"
          onClick={() => setShowDeliberation(!showDeliberation)}
        >
          {showDeliberation ? 'Hide' : 'Show'} Deliberation Log
        </button>
        {showDeliberation && (
          <div className="deliberation-log">
            {domainResults && Object.keys(domainResults).length > 0 && (
              <details open>
                <summary>Stage 1 Domain Results</summary>
                <pre>{JSON.stringify(domainResults, null, 2)}</pre>
              </details>
            )}
            {contextDiscussions && contextDiscussions.length > 0 && (
              <details>
                <summary>Stage 2 Cross-Domain Discussions</summary>
                <pre>{JSON.stringify(contextDiscussions, null, 2)}</pre>
              </details>
            )}
          </div>
        )}
      </section>

      {/* Actions */}
      <div className="report-actions">
        <button className="btn-primary" onClick={handleExportJSON}>
          Export JSON
        </button>
        <button className="btn-secondary" onClick={onNewReview}>
          New Review
        </button>
      </div>
    </div>
  );
}

export default FinalReport;
