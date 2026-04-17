import { useState } from 'react';
import './ReviewProgress.css';

function ReviewProgress({ progressEvents, domainResults, contextDiscussions, isLoading }) {
  const [expandedExpert, setExpandedExpert] = useState(null);

  const stage1Started = progressEvents.some((e) => e.type === 'stage1_start');
  const stage1Complete = progressEvents.some((e) => e.type === 'stage1_complete');
  const stage2Started = progressEvents.some((e) => e.type === 'stage2_start');
  const stage2Complete = progressEvents.some((e) => e.type === 'stage2_complete');
  const stage3Started = progressEvents.some((e) => e.type === 'stage3_start');
  const stage3Complete = progressEvents.some((e) => e.type === 'stage3_complete');

  const expertStarts = progressEvents.filter((e) => e.type === 'stage1_expert_start');
  const expertCompletes = progressEvents.filter((e) => e.type === 'stage1_expert_complete');
  const clusterStarts = progressEvents.filter((e) => e.type === 'stage2_cluster_start');
  const clusterCompletes = progressEvents.filter((e) => e.type === 'stage2_cluster_complete');

  return (
    <div className="review-progress">
      <h2>Review in Progress / 审查进行中</h2>

      {/* Stage 1: Domain Reviews */}
      <div className={`stage-block ${stage1Complete ? 'complete' : stage1Started ? 'active' : ''}`}>
        <div className="stage-header">
          <span className="stage-icon">
            {stage1Complete ? '✓' : stage1Started ? (isLoading ? '⟳' : '●') : '○'}
          </span>
          <h3>Stage 1: Domain Expert Reviews / 域内专家审查</h3>
        </div>

        <div className="expert-progress-list">
          {expertStarts.map((evt) => {
            const isComplete = expertCompletes.some((c) => c.expert_id === evt.expert_id);
            const result = domainResults[evt.expert_id];

            return (
              <div key={evt.expert_id} className={`expert-progress-item ${isComplete ? 'done' : 'running'}`}>
                <div
                  className="expert-progress-header"
                  onClick={() => setExpandedExpert(expandedExpert === evt.expert_id ? null : evt.expert_id)}
                >
                  <span className="expert-status-dot">{isComplete ? '✓' : '⟳'}</span>
                  <span className="expert-label">{evt.expert_name || evt.expert_id}</span>
                  {isComplete && result?.summary && (
                    <span className={`assessment-badge assessment-${result.summary?.overall_assessment}`}>
                      {result.summary?.overall_assessment}
                    </span>
                  )}
                </div>

                {expandedExpert === evt.expert_id && result && (
                  <div className="expert-detail-panel">
                    {result.summary && (
                      <div className="detail-section">
                        <h4>Domain Summary</h4>
                        <p><strong>Assessment:</strong> {result.summary.overall_assessment}</p>
                        <p><strong>Confidence:</strong> {result.summary.confidence}</p>
                        {result.summary.key_concerns_summary && (
                          <p><strong>Key Concerns:</strong> {result.summary.key_concerns_summary}</p>
                        )}
                      </div>
                    )}
                    {result.review_a && (
                      <details className="detail-section">
                        <summary>LLM-A First Pass Review</summary>
                        <pre>{JSON.stringify(result.review_a, null, 2)}</pre>
                      </details>
                    )}
                    {result.cross_check_b && (
                      <details className="detail-section">
                        <summary>LLM-B Cross-Check</summary>
                        <pre>{JSON.stringify(result.cross_check_b, null, 2)}</pre>
                      </details>
                    )}
                    {result.cross_check_c && (
                      <details className="detail-section">
                        <summary>LLM-C Cross-Check</summary>
                        <pre>{JSON.stringify(result.cross_check_c, null, 2)}</pre>
                      </details>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Stage 2: Cross-Domain Discussions */}
      {(stage2Started || stage2Complete) && (
        <div className={`stage-block ${stage2Complete ? 'complete' : 'active'}`}>
          <div className="stage-header">
            <span className="stage-icon">
              {stage2Complete ? '✓' : '⟳'}
            </span>
            <h3>Stage 2: Cross-Domain Discussion / 跨域讨论</h3>
          </div>

          <div className="cluster-progress-list">
            {clusterStarts.map((evt, i) => {
              const isComplete = clusterCompletes.some((c) => c.topic === evt.topic);
              return (
                <div key={i} className={`cluster-progress-item ${isComplete ? 'done' : 'running'}`}>
                  <span className="expert-status-dot">{isComplete ? '✓' : '⟳'}</span>
                  <span>{evt.topic}</span>
                  {isComplete && <span className="cluster-done-label">consensus</span>}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Stage 3: Chairman Synthesis */}
      {(stage3Started || stage3Complete) && (
        <div className={`stage-block ${stage3Complete ? 'complete' : 'active'}`}>
          <div className="stage-header">
            <span className="stage-icon">
              {stage3Complete ? '✓' : '⟳'}
            </span>
            <h3>Stage 3: Chairman Synthesis / 主席综合</h3>
          </div>
          {!stage3Complete && <div className="stage-loading">Synthesizing final report...</div>}
        </div>
      )}

      {isLoading && !stage3Complete && (
        <div className="progress-footer">Review is in progress, please wait...</div>
      )}
    </div>
  );
}

export default ReviewProgress;
