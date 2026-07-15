import { useState, useCallback } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { setFields } from '../store/interactionSlice';

const EMOTION_OPTIONS = [
  { value: 'positive', emoji: '😊', label: 'Positive' },
  { value: 'neutral', emoji: '🫡', label: 'Neutral' },
  { value: 'negative', emoji: '😟', label: 'Negative' },
  { value: 'mixed', emoji: '🤔', label: 'Mixed' },
];

const SENTIMENT_COLORS = {
  positive: 'var(--success)',
  neutral: 'var(--text-secondary)',
  negative: 'var(--danger)',
  mixed: 'var(--warning)',
};

function Section({ title, emoji, children, className = '' }) {
  return (
    <div className={`info-section ${className}`}>
      <div className="section-header">
        <span className="section-emoji">{emoji}</span>
        <span className="section-title">{title}</span>
      </div>
      <div className="section-content">{children}</div>
    </div>
  );
}

export default function InteractionForm() {
  const form = useSelector((s) => s.interaction);
  const dispatch = useDispatch();

  // Local state for interactive fields
  const [newAttendee, setNewAttendee] = useState('');
  const [newTopic, setNewTopic] = useState('');
  const [newMaterial, setNewMaterial] = useState('');
  const [newSample, setNewSample] = useState('');

  const hasAny = form.hcp_name || form.interaction_date || form.attendees?.length ||
    form.topics_discussed?.length;

  const updateField = useCallback((field, value) => {
    dispatch(setFields({ [field]: value }));
  }, [dispatch]);

  const addAttendee = useCallback(() => {
    const val = newAttendee.trim();
    if (!val) return;
    updateField('attendees', [...(form.attendees || []), val]);
    setNewAttendee('');
  }, [newAttendee, form.attendees, updateField]);

  const removeAttendee = useCallback((index) => {
    updateField('attendees', form.attendees.filter((_, i) => i !== index));
  }, [form.attendees, updateField]);

  const addTopic = useCallback(() => {
    const val = newTopic.trim();
    if (!val) return;
    updateField('topics_discussed', [...(form.topics_discussed || []), val]);
    setNewTopic('');
  }, [newTopic, form.topics_discussed, updateField]);

  const removeTopic = useCallback((index) => {
    updateField('topics_discussed', form.topics_discussed.filter((_, i) => i !== index));
  }, [form.topics_discussed, updateField]);

  const addMaterial = useCallback(() => {
    const val = newMaterial.trim();
    if (!val) return;
    updateField('materials_shared', [...(form.materials_shared || []), val]);
    setNewMaterial('');
  }, [newMaterial, form.materials_shared, updateField]);

  const removeMaterial = useCallback((index) => {
    updateField('materials_shared', form.materials_shared.filter((_, i) => i !== index));
  }, [form.materials_shared, updateField]);

  const addSample = useCallback(() => {
    const val = newSample.trim();
    if (!val) return;
    updateField('samples_distributed', [...(form.samples_distributed || []), val]);
    setNewSample('');
  }, [newSample, form.samples_distributed, updateField]);

  const removeSample = useCallback((index) => {
    updateField('samples_distributed', form.samples_distributed.filter((_, i) => i !== index));
  }, [form.samples_distributed, updateField]);

  const setSentiment = useCallback((val) => {
    updateField('observed_sentiment', val);
  }, [updateField]);

  const fmtDate = (v) => {
    if (!v) return null;
    try {
      return new Date(v).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
    } catch {
      return v;
    }
  };

  // Get badge config
  const getTypeBadge = (type) => {
    if (!type) return null;
    const styles = {
      'In-person call': { bg: 'var(--success-bg)', bd: 'var(--success-border)', txt: '#065f46', emoji: '🤝' },
      'Virtual call': { bg: '#eef2ff', bd: 'rgba(79,70,229,0.25)', txt: '#3730a3', emoji: '💻' },
      'Email correspondence': { bg: '#fff7ed', bd: 'rgba(249,115,22,0.25)', txt: '#9a3412', emoji: '📧' },
      'Text correspondence': { bg: '#fdf4ff', bd: 'rgba(168,85,247,0.25)', txt: '#6b21a8', emoji: '📱' },
    };
    const s = styles[type] || { bg: '#f9fafb', bd: 'var(--border)', txt: 'var(--text)', emoji: '📋' };
    return <span className="type-badge" style={{ background: s.bg, borderColor: s.bd, color: s.txt }}>
      <span className="type-emoji">{s.emoji}</span>{type}
    </span>;
  };

  const getSentimentDisplay = () => {
    const val = form.observed_sentiment;
    if (!val) return <span className="text-muted">Not recorded</span>;
    const opt = EMOTION_OPTIONS.find(o => o.value === val);
    const color = SENTIMENT_COLORS[val] || 'var(--text-secondary)';
    return (
      <span className="sentiment-pill" style={{ background: color + '15', borderColor: color + '40', color }}>
        <span className="sentiment-emoji">{opt?.emoji}</span>
        {val.charAt(0).toUpperCase() + val.slice(1)}
      </span>
    );
  };

  const getComplianceDisplay = () => {
    const val = form.compliance_flag;
    if (val === 'compliant') {
      return <span className="compliance-pill compliance-ok">✅ Compliant — clear</span>;
    }
    if (val === 'review_needed') {
      return <span className="compliance-pill compliance-warn">⚠️ Review needed — see chat</span>;
    }
    if (!val) {
      return <span className="compliance-pill compliance-pending">⏳ Awaiting check...</span>;
    }
    return <span className="text-muted">—</span>;
  };

  const getFileList = () => {
    const files = form.attached_files || [];
    if (!files.length) return <span className="text-muted">No files attached</span>;
    return (
      <div className="file-list">
        {files.map((f, i) => (
          <div key={i} className="file-item">
            <span className="file-icon">📄</span>
            <span className="file-name">{f.name}</span>
            <span className="file-meta">{(f.size / 1024).toFixed(1)} KB</span>
          </div>
        ))}
      </div>
    );
  };

  // Common chip input component
  const ChipInput = ({ value, onChange, onAdd, placeholder, icon, onRemove }) => (
    <div className="chip-input-row">
      <span className="chip-input-icon">{icon}</span>
      <input
        className="chip-input"
        type="text"
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), onAdd())}
      />
      <button className="chip-add-btn" onClick={onAdd} disabled={!value.trim()}>
        <span className="add-icon">+</span>
      </button>
    </div>
  );

  // Render empty state
  if (!hasAny) {
    return (
      <div className="form-panel">
        <div className="form-header">
          <div className="header-brand">
            <div className="header-logo">
              <span className="logo-icon">📋</span>
            </div>
            <div className="header-text">
              <h1>HCP Log</h1>
              <span className="header-tag">AI-Mediated</span>
            </div>
          </div>
        </div>
        <div className="empty-state">
          <div className="empty-visual">
            <span className="empty-emoji">📋</span>
            <div className="empty-rings">
              <span className="ring ring-1" />
              <span className="ring ring-2" />
              <span className="ring ring-3" />
            </div>
          </div>
          <h3>No Interaction Logged Yet</h3>
          <p>Tell the AI assistant about your visit. It will intelligently extract and organize all the details here.</p>
          <div className="empty-icons">
            <span>💬</span><span>📅</span><span>👥</span><span>✅</span>
          </div>
        </div>
      </div>
    );
  }

  // Main form view
  return (
    <div className="form-panel">
      <div className="form-header">
        <div className="header-brand">
          <div className="header-logo">
            <span className="logo-icon">📋</span>
          </div>
          <div className="header-text">
            <h1>HCP Interaction Log</h1>
            <span className="header-tag">AI-Mediated Form</span>
          </div>
        </div>
        <div className="header-meta">
          {form.interaction_date && (
            <span className="meta-badge">
              <span>📅</span>
              <span>{fmtDate(form.interaction_date)}</span>
            </span>
          )}
        </div>
      </div>

      <div className="form-body scrollbar-thin">
        {/* HCP & Interaction Details */}
        <Section emoji="🏥" title="HCP Details">
          <div className="detail-row">
            <div className="detail-card highlight">
              <span className="detail-label">Healthcare Professional</span>
              <span className="detail-value hcp-name">
                {form.hcp_name || '—'}
              </span>
            </div>
            <div className="detail-card">
              <span className="detail-label">Interaction Date</span>
              <span className="detail-value">
                {fmtDate(form.interaction_date) || '—'}
              </span>
            </div>
          </div>
          <div className="detail-row">
            <div className="detail-card">
              <span className="detail-label">Time</span>
              <span className="detail-value">⏰ {fmtDate(form.interaction_time) || '—'}</span>
            </div>
            <div className="detail-card">
              <span className="detail-label">Type</span>
              <div className="detail-value">
                {getTypeBadge(form.interaction_type || '—')}
              </div>
            </div>
          </div>
        </Section>

        {/* Participants */}
        <Section emoji="👥" title="Participants">
          <div className="attendees-section">
            <div className="chip-list">
              {(form.attendees || []).length > 0 ? (
                form.attendees.map((p, i) => (
                  <span key={i} className="attendee-chip">
                    <span className="chip-avatar">👤</span>
                    <span className="chip-text">{p}</span>
                    <button className="chip-remove" onClick={() => removeAttendee(i)}>×</button>
                  </span>
                ))
              ) : (
                <span className="empty-hint">No attendees added yet</span>
              )}
            </div>
            <ChipInput
              value={newAttendee}
              onChange={(e) => setNewAttendee(e.target.value)}
              onAdd={addAttendee}
              placeholder="Add participant name..."
              icon="➕"
            />
          </div>
        </Section>

        {/* Topics Discussed */}
        <Section emoji="💬" title="Topics Discussed">
          <div className="attendees-section">
            <div className="chip-list">
              {(form.topics_discussed || []).length > 0 ? (
                form.topics_discussed.map((t, i) => (
                  <span key={i} className="topic-chip">
                    <span className="chip-emoji">💡</span>
                    <span className="chip-text">{t}</span>
                    <button className="chip-remove" onClick={() => removeTopic(i)}>×</button>
                  </span>
                ))
              ) : (
                <span className="empty-hint">No topics recorded</span>
              )}
            </div>
            <ChipInput
              value={newTopic}
              onChange={(e) => setNewTopic(e.target.value)}
              onAdd={addTopic}
              placeholder="Add topic..."
              icon="➕"
            />
          </div>
        </Section>

        {/* Products Discussed */}
        <Section emoji="💊" title="Products Discussed">
          <div className="text-content">
            {form.products_discussed || '—'}
          </div>
        </Section>

        {/* Materials Shared */}
        <Section emoji="📄" title="Materials Shared">
          <div className="attendees-section">
            <div className="chip-list">
              {(form.materials_shared || []).length > 0 ? (
                form.materials_shared.map((m, i) => (
                  <span key={i} className="material-chip">
                    <span className="chip-emoji">📑</span>
                    <span className="chip-text">{m}</span>
                    <button className="chip-remove" onClick={() => removeMaterial(i)}>×</button>
                  </span>
                ))
              ) : (
                <span className="empty-hint">No materials shared</span>
              )}
            </div>
            <ChipInput
              value={newMaterial}
              onChange={(e) => setNewMaterial(e.target.value)}
              onAdd={addMaterial}
              placeholder="Add material..."
              icon="➕"
            />
          </div>
        </Section>

        {/* Samples Distributed */}
        <Section emoji="🧪" title="Samples Distributed">
          <div className="attendees-section">
            <div className="chip-list">
              {(form.samples_distributed || []).length > 0 ? (
                form.samples_distributed.map((s, i) => (
                  <span key={i} className="sample-chip">
                    <span className="chip-emoji">🔬</span>
                    <span className="chip-text">{s}</span>
                    <button className="chip-remove" onClick={() => removeSample(i)}>×</button>
                  </span>
                ))
              ) : (
                <span className="empty-hint">No samples distributed</span>
              )}
            </div>
            <ChipInput
              value={newSample}
              onChange={(e) => setNewSample(e.target.value)}
              onAdd={addSample}
              placeholder="Add sample..."
              icon="➕"
            />
          </div>
        </Section>

        {/* Attached Files */}
        <Section emoji="📎" title="Attached Files" className="files-section">
          {getFileList()}
        </Section>

        {/* Sentiment */}
        <Section emoji="🧠" title="Observed Sentiment">
          <div className="sentiment-options">
            {EMOTION_OPTIONS.map(opt => (
              <button
                key={opt.value}
                className={`sentiment-btn ${form.observed_sentiment === opt.value ? 'active' : ''}`}
                onClick={() => setSentiment(opt.value)}
                title={opt.label}
              >
                <span className="sentiment-btn-emoji">{opt.emoji}</span>
                <span className="sentiment-btn-label">{opt.label}</span>
              </button>
            ))}
          </div>
        </Section>

        {/* Notes */}
        <Section emoji="📝" title="Notes">
          <div className="notes-content">
            {form.notes || '—'}
          </div>
        </Section>

        {/* Follow-up */}
        <Section emoji="⏰" title="Follow-up">
          <div className="detail-row">
            <div className="detail-card">
              <span className="detail-label">Scheduled Date</span>
              <span className="detail-value">📅 {fmtDate(form.follow_up_date) || '—'}</span>
            </div>
            <div className="detail-card">
              <span className="detail-label">Action Item</span>
              <span className="detail-value">📌 {form.follow_up_action || '—'}</span>
            </div>
          </div>
        </Section>

        {/* Compliance */}
        <Section emoji="✅" title="Compliance Check">
          <div className="compliance-display">
            {getComplianceDisplay()}
          </div>
        </Section>
      </div>
    </div>
  );
}
