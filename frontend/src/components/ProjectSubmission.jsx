import { useState } from 'react';
import './ProjectSubmission.css';

const BOOLEAN_FLAGS = [
  { key: 'involves_human_subjects', label: 'Involves human subjects / 涉及人类受试者' },
  { key: 'involves_human_genetic_resources', label: 'Involves human genetic resources / 涉及人类遗传资源' },
  { key: 'involves_animals', label: 'Involves animals / 涉及动物实验' },
  { key: 'involves_gene_editing', label: 'Involves gene editing / 涉及基因编辑' },
  { key: 'involves_synthetic_biology', label: 'Involves synthetic biology / 涉及合成生物学' },
  { key: 'involves_environmental_release', label: 'Involves environmental release / 涉及环境释放' },
  { key: 'involves_international_collaboration', label: 'International collaboration / 涉及国际合作' },
  { key: 'involves_vulnerable_populations', label: 'Involves vulnerable populations / 涉及弱势群体' },
  { key: 'involves_ai_systems', label: 'Involves AI systems / 涉及AI系统' },
];

const PROJECT_TYPES = [
  { value: 'basic_research', label: 'Basic Research / 基础研究' },
  { value: 'applied_research', label: 'Applied Research / 应用研究' },
  { value: 'tech_development', label: 'Technology Development / 技术开发' },
  { value: 'clinical_trial', label: 'Clinical Trial / 临床试验' },
];

function ProjectSubmission({ presets, isLoading, onSubmit }) {
  const [preset, setPreset] = useState('life-sciences');
  const [form, setForm] = useState({
    project_title: '',
    principal_investigator: '',
    department: '',
    project_type: 'basic_research',
    research_description: '',
    methodology: '',
    data_management_plan: '',
    funding_source: '',
    conflict_of_interest_declaration: '',
    estimated_sample_size: '',
    study_duration: '',
  });
  const [flags, setFlags] = useState({});

  const handleFieldChange = (field, value) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const handleFlagChange = (key) => {
    setFlags((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    const projectMaterial = { ...form };
    // Add boolean flags
    for (const { key } of BOOLEAN_FLAGS) {
      projectMaterial[key] = !!flags[key];
    }
    // Remove empty optional fields
    for (const k of Object.keys(projectMaterial)) {
      if (projectMaterial[k] === '') delete projectMaterial[k];
    }
    onSubmit(projectMaterial, preset);
  };

  return (
    <div className="project-submission">
      <h2>Submit Project for Ethics Review</h2>
      <p className="subtitle">Fill in the project details below. All reviews are simulated and for reference only.</p>

      <form onSubmit={handleSubmit}>
        {/* Preset selector */}
        <div className="form-group">
          <label>Review Preset</label>
          <select value={preset} onChange={(e) => setPreset(e.target.value)}>
            {presets.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name.zh} / {p.name.en} ({p.expert_count} experts)
              </option>
            ))}
            {presets.length === 0 && <option value="life-sciences">life-sciences</option>}
          </select>
        </div>

        {/* Required fields */}
        <div className="form-group">
          <label>Project Title / 项目名称 *</label>
          <input
            type="text"
            required
            value={form.project_title}
            onChange={(e) => handleFieldChange('project_title', e.target.value)}
            placeholder="e.g. CRISPR-Cas9 Gene Therapy for Sickle Cell Disease"
          />
        </div>

        <div className="form-row">
          <div className="form-group">
            <label>Principal Investigator / 项目负责人 *</label>
            <input
              type="text"
              required
              value={form.principal_investigator}
              onChange={(e) => handleFieldChange('principal_investigator', e.target.value)}
            />
          </div>
          <div className="form-group">
            <label>Department / 所属部门</label>
            <input
              type="text"
              value={form.department}
              onChange={(e) => handleFieldChange('department', e.target.value)}
            />
          </div>
        </div>

        <div className="form-group">
          <label>Project Type / 项目类型</label>
          <select value={form.project_type} onChange={(e) => handleFieldChange('project_type', e.target.value)}>
            {PROJECT_TYPES.map((t) => (
              <option key={t.value} value={t.value}>{t.label}</option>
            ))}
          </select>
        </div>

        <div className="form-group">
          <label>Research Description / 研究内容摘要 *</label>
          <textarea
            required
            rows={5}
            value={form.research_description}
            onChange={(e) => handleFieldChange('research_description', e.target.value)}
            placeholder="Describe the research objectives, background, and significance..."
          />
        </div>

        <div className="form-group">
          <label>Methodology / 研究方法 *</label>
          <textarea
            required
            rows={4}
            value={form.methodology}
            onChange={(e) => handleFieldChange('methodology', e.target.value)}
            placeholder="Describe the technical approach and research methods..."
          />
        </div>

        {/* Boolean flags */}
        <div className="form-group">
          <label>Ethics Flags / 伦理标志位</label>
          <div className="flags-grid">
            {BOOLEAN_FLAGS.map(({ key, label }) => (
              <label key={key} className="flag-checkbox">
                <input
                  type="checkbox"
                  checked={!!flags[key]}
                  onChange={() => handleFlagChange(key)}
                />
                <span>{label}</span>
              </label>
            ))}
          </div>
        </div>

        {/* Optional fields */}
        <details className="optional-fields">
          <summary>Optional Fields / 可选信息</summary>
          <div className="form-group">
            <label>Data Management Plan / 数据管理方案</label>
            <textarea
              rows={3}
              value={form.data_management_plan}
              onChange={(e) => handleFieldChange('data_management_plan', e.target.value)}
            />
          </div>
          <div className="form-row">
            <div className="form-group">
              <label>Funding Source / 资金来源</label>
              <input
                type="text"
                value={form.funding_source}
                onChange={(e) => handleFieldChange('funding_source', e.target.value)}
              />
            </div>
            <div className="form-group">
              <label>Estimated Sample Size / 预期样本量</label>
              <input
                type="text"
                value={form.estimated_sample_size}
                onChange={(e) => handleFieldChange('estimated_sample_size', e.target.value)}
              />
            </div>
          </div>
          <div className="form-row">
            <div className="form-group">
              <label>Study Duration / 研究周期</label>
              <input
                type="text"
                value={form.study_duration}
                onChange={(e) => handleFieldChange('study_duration', e.target.value)}
              />
            </div>
            <div className="form-group">
              <label>Conflict of Interest / 利益冲突声明</label>
              <input
                type="text"
                value={form.conflict_of_interest_declaration}
                onChange={(e) => handleFieldChange('conflict_of_interest_declaration', e.target.value)}
              />
            </div>
          </div>
        </details>

        <button type="submit" className="btn-primary" disabled={isLoading}>
          {isLoading ? 'Submitting...' : 'Submit for Review / 提交审查'}
        </button>
      </form>
    </div>
  );
}

export default ProjectSubmission;
