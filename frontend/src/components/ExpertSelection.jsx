import './ExpertSelection.css';

function ExpertSelection({
  routingResult,
  availableExperts,
  selectedExperts,
  contextClusters,
  onSelectedExpertsChange,
  onContextClustersChange,
  onConfirm,
  isLoading,
}) {
  const toggleExpert = (id) => {
    if (selectedExperts.includes(id)) {
      onSelectedExpertsChange(selectedExperts.filter((e) => e !== id));
    } else {
      onSelectedExpertsChange([...selectedExperts, id]);
    }
  };

  const handleConfirm = () => {
    onConfirm(selectedExperts, contextClusters);
  };

  const highRiskFlags = routingResult?.high_risk_flags || [];
  const riskLevel = routingResult?.risk_level || 'standard';

  return (
    <div className="expert-selection">
      <h2>Expert Selection / 专家确认</h2>
      <p className="subtitle">
        Review the AI-recommended expert panel. You can add or remove experts before proceeding.
      </p>

      {/* Risk level indicator */}
      <div className={`risk-indicator risk-${riskLevel}`}>
        Risk Level: <strong>{riskLevel.toUpperCase()}</strong>
        {highRiskFlags.length > 0 && (
          <div className="high-risk-flags">
            High-risk flags:
            {highRiskFlags.map((flag, i) => (
              <span key={i} className="risk-flag">{flag}</span>
            ))}
          </div>
        )}
      </div>

      {/* Expert list */}
      <div className="experts-section">
        <h3>Expert Panel / 专家组</h3>
        <div className="experts-grid">
          {availableExperts.map((expert) => {
            const isSelected = selectedExperts.includes(expert.id);
            const routingInfo = routingResult?.experts_selected?.find(
              (e) => e.id === expert.id
            );
            const notNeededInfo = routingResult?.experts_not_needed?.find(
              (e) => e.id === expert.id
            );

            return (
              <div
                key={expert.id}
                className={`expert-card ${isSelected ? 'selected' : ''}`}
                onClick={() => toggleExpert(expert.id)}
              >
                <div className="expert-card-header">
                  <input
                    type="checkbox"
                    checked={isSelected}
                    onChange={() => toggleExpert(expert.id)}
                  />
                  <div>
                    <div className="expert-name">{expert.name.zh}</div>
                    <div className="expert-name-en">{expert.name.en}</div>
                  </div>
                </div>
                <div className="expert-tags">
                  {expert.tags.map((tag) => (
                    <span key={tag} className="tag">{tag}</span>
                  ))}
                </div>
                <ul className="expert-dimensions">
                  {expert.review_dimensions.slice(0, 3).map((dim, i) => (
                    <li key={i}>{dim}</li>
                  ))}
                  {expert.review_dimensions.length > 3 && (
                    <li className="more">+{expert.review_dimensions.length - 3} more</li>
                  )}
                </ul>
                {routingInfo && (
                  <div className="routing-reason recommended">
                    Recommended: {routingInfo.reason}
                  </div>
                )}
                {notNeededInfo && (
                  <div className="routing-reason not-needed">
                    Not recommended: {notNeededInfo.reason}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Context clusters */}
      {contextClusters.length > 0 && (
        <div className="clusters-section">
          <h3>Cross-Domain Discussion Topics / 跨域讨论议题</h3>
          <div className="clusters-list">
            {contextClusters.map((cluster, i) => (
              <div key={i} className="cluster-card">
                <div className="cluster-topic">{cluster.topic}</div>
                <div className="cluster-participants">
                  Participants: {cluster.participants.join(', ')}
                </div>
                {cluster.reason && (
                  <div className="cluster-reason">{cluster.reason}</div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="selection-actions">
        <span className="selection-count">
          {selectedExperts.length} expert(s) selected
        </span>
        <button
          className="btn-primary"
          onClick={handleConfirm}
          disabled={isLoading || selectedExperts.length === 0}
        >
          {isLoading ? 'Starting...' : 'Confirm & Start Review / 确认并开始审查'}
        </button>
      </div>
    </div>
  );
}

export default ExpertSelection;
