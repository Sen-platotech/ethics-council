/**
 * API client for the Ethics Council backend.
 */

const API_BASE = 'http://localhost:8001';

export const api = {
  /** List available preset packages. */
  async listPresets() {
    const res = await fetch(`${API_BASE}/api/presets`);
    if (!res.ok) throw new Error('Failed to list presets');
    return res.json();
  },

  /** List all reviews (metadata). */
  async listReviews() {
    const res = await fetch(`${API_BASE}/api/reviews`);
    if (!res.ok) throw new Error('Failed to list reviews');
    return res.json();
  },

  /** Get a specific review. */
  async getReview(reviewId) {
    const res = await fetch(`${API_BASE}/api/reviews/${reviewId}`);
    if (!res.ok) throw new Error('Failed to get review');
    return res.json();
  },

  /** Submit a project for ethics review (runs Stage 0). */
  async submitProject(projectMaterial, preset = 'life-sciences') {
    const res = await fetch(`${API_BASE}/api/reviews`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        project_material: projectMaterial,
        preset,
      }),
    });
    if (!res.ok) throw new Error('Failed to submit project');
    return res.json();
  },

  /** Confirm experts and run full review (non-streaming). */
  async confirmAndRun(reviewId, expertsSelected, contextClusters = null, expertModelOverrides = null) {
    const res = await fetch(`${API_BASE}/api/reviews/${reviewId}/confirm`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        review_id: reviewId,
        experts_selected: expertsSelected,
        context_clusters: contextClusters,
        expert_model_overrides: expertModelOverrides,
      }),
    });
    if (!res.ok) throw new Error('Failed to run review');
    return res.json();
  },

  /**
   * Confirm experts and stream Stages 1-3 progress via SSE.
   * @param {string} reviewId
   * @param {string[]} expertsSelected
   * @param {function} onEvent - (eventType, eventData) => void
   * @param {Array|null} contextClusters
   * @param {Object|null} expertModelOverrides
   */
  async confirmAndRunStream(reviewId, expertsSelected, onEvent, contextClusters = null, expertModelOverrides = null) {
    const res = await fetch(`${API_BASE}/api/reviews/${reviewId}/confirm/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        review_id: reviewId,
        experts_selected: expertsSelected,
        context_clusters: contextClusters,
        expert_model_overrides: expertModelOverrides,
      }),
    });
    if (!res.ok) throw new Error('Failed to start streaming review');

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop(); // keep incomplete line in buffer

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const event = JSON.parse(line.slice(6));
            onEvent(event.type, event);
          } catch (e) {
            console.error('Failed to parse SSE event:', e);
          }
        }
      }
    }
  },

  /** Delete a review. */
  async deleteReview(reviewId) {
    const res = await fetch(`${API_BASE}/api/reviews/${reviewId}`, { method: 'DELETE' });
    if (!res.ok) throw new Error('Failed to delete review');
    return res.json();
  },
};
