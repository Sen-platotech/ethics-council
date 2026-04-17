import { useState, useEffect } from 'react';
import ProjectSubmission from './components/ProjectSubmission';
import ExpertSelection from './components/ExpertSelection';
import ReviewProgress from './components/ReviewProgress';
import FinalReport from './components/FinalReport';
import { api } from './api';
import './App.css';

const STEPS = ['submit', 'experts', 'review', 'report'];

function App() {
  const [step, setStep] = useState('submit');
  const [presets, setPresets] = useState([]);
  const [reviews, setReviews] = useState([]);

  // Current review state
  const [reviewId, setReviewId] = useState(null);
  const [routingResult, setRoutingResult] = useState(null);
  const [availableExperts, setAvailableExperts] = useState([]);
  const [selectedExperts, setSelectedExperts] = useState([]);
  const [contextClusters, setContextClusters] = useState([]);
  const [domainResults, setDomainResults] = useState({});
  const [contextDiscussions, setContextDiscussions] = useState([]);
  const [finalReport, setFinalReport] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [progressEvents, setProgressEvents] = useState([]);

  useEffect(() => {
    api.listPresets().then(setPresets).catch(console.error);
    api.listReviews().then(setReviews).catch(console.error);
  }, []);

  // --- Handlers ---

  const handleSubmitProject = async (projectMaterial, preset) => {
    setIsLoading(true);
    setError(null);
    try {
      const result = await api.submitProject(projectMaterial, preset);
      setReviewId(result.review_id);
      setRoutingResult(result.routing_result);
      setAvailableExperts(result.available_experts);
      setSelectedExperts(
        result.routing_result.experts_selected.map((e) => e.id)
      );
      setContextClusters(result.routing_result.context_clusters || []);
      setStep('experts');
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleConfirmExperts = async (experts, clusters) => {
    setIsLoading(true);
    setError(null);
    setProgressEvents([]);
    setDomainResults({});
    setContextDiscussions([]);
    setFinalReport(null);
    setStep('review');

    try {
      await api.confirmAndRunStream(
        reviewId,
        experts,
        (eventType, event) => {
          setProgressEvents((prev) => [...prev, { type: eventType, ...event }]);

          switch (eventType) {
            case 'stage1_expert_complete':
              setDomainResults((prev) => ({
                ...prev,
                [event.expert_id]: event.data,
              }));
              break;
            case 'stage2_cluster_complete':
              setContextDiscussions((prev) => [...prev, event.data]);
              break;
            case 'stage3_complete':
              setFinalReport(event.data);
              break;
            case 'complete':
              setStep('report');
              setIsLoading(false);
              api.listReviews().then(setReviews).catch(console.error);
              break;
            case 'error':
              setError(event.message);
              setIsLoading(false);
              break;
          }
        },
        clusters
      );
    } catch (err) {
      setError(err.message);
      setIsLoading(false);
    }
  };

  const handleLoadReview = async (id) => {
    setIsLoading(true);
    setError(null);
    try {
      const review = await api.getReview(id);
      setReviewId(review.id);
      setRoutingResult(review.routing_result);
      setDomainResults(review.domain_results || {});
      setContextDiscussions(review.context_discussions || []);
      setFinalReport(review.final_report);
      if (review.status === 'completed' && review.final_report) {
        setStep('report');
      } else if (review.status === 'routing_complete') {
        setStep('experts');
      } else {
        setStep('submit');
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleNewReview = () => {
    setStep('submit');
    setReviewId(null);
    setRoutingResult(null);
    setAvailableExperts([]);
    setSelectedExperts([]);
    setContextClusters([]);
    setDomainResults({});
    setContextDiscussions([]);
    setFinalReport(null);
    setProgressEvents([]);
    setError(null);
  };

  // --- Render ---

  const stepIndex = STEPS.indexOf(step);

  return (
    <div className="app">
      {/* Sidebar with review history */}
      <aside className="sidebar">
        <div className="sidebar-header">
          <h2>Ethics Council</h2>
          <button className="btn-new" onClick={handleNewReview}>
            + New Review
          </button>
        </div>
        <div className="sidebar-list">
          {reviews.map((r) => (
            <div
              key={r.id}
              className={`sidebar-item ${r.id === reviewId ? 'active' : ''}`}
              onClick={() => handleLoadReview(r.id)}
            >
              <div className="sidebar-item-title">{r.project_title}</div>
              <div className="sidebar-item-meta">
                <span className={`status-badge status-${r.status}`}>{r.status}</span>
                <span>{r.preset}</span>
              </div>
            </div>
          ))}
          {reviews.length === 0 && (
            <div className="sidebar-empty">No reviews yet</div>
          )}
        </div>
      </aside>

      {/* Main content area */}
      <main className="main-content">
        {/* Progress stepper */}
        <div className="stepper">
          {STEPS.map((s, i) => (
            <div
              key={s}
              className={`stepper-step ${i <= stepIndex ? 'active' : ''} ${i === stepIndex ? 'current' : ''}`}
            >
              <div className="stepper-dot">{i + 1}</div>
              <div className="stepper-label">
                {s === 'submit' && 'Submit'}
                {s === 'experts' && 'Experts'}
                {s === 'review' && 'Review'}
                {s === 'report' && 'Report'}
              </div>
            </div>
          ))}
        </div>

        {error && (
          <div className="error-banner">
            {error}
            <button onClick={() => setError(null)}>Dismiss</button>
          </div>
        )}

        <div className="step-content">
          {step === 'submit' && (
            <ProjectSubmission
              presets={presets}
              isLoading={isLoading}
              onSubmit={handleSubmitProject}
            />
          )}
          {step === 'experts' && (
            <ExpertSelection
              routingResult={routingResult}
              availableExperts={availableExperts}
              selectedExperts={selectedExperts}
              contextClusters={contextClusters}
              onSelectedExpertsChange={setSelectedExperts}
              onContextClustersChange={setContextClusters}
              onConfirm={handleConfirmExperts}
              isLoading={isLoading}
            />
          )}
          {step === 'review' && (
            <ReviewProgress
              progressEvents={progressEvents}
              domainResults={domainResults}
              contextDiscussions={contextDiscussions}
              isLoading={isLoading}
            />
          )}
          {step === 'report' && (
            <FinalReport
              report={finalReport}
              domainResults={domainResults}
              contextDiscussions={contextDiscussions}
              onNewReview={handleNewReview}
            />
          )}
        </div>
      </main>
    </div>
  );
}

export default App;
