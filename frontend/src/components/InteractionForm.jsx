import { useSelector, useDispatch } from 'react-redux';
import { setFields } from '../store/interactionSlice';

export default function InteractionForm() {
  const form = useSelector((s) => s.interaction);
  const dispatch = useDispatch();
  const set = (patch) => dispatch(setFields(patch));
  const isFresh = !form.hcp_name;
  const emptyCls = isFresh ? ' empty' : '';

  const cls = (base, extra) => 'field-readonly' + ((extra ? ' ' + extra : '') || '') + (isFresh ? ' empty' : '');

  return (
    <div className="form-scroll scrollbar-thin">
      <div className="field-row">
        <div className="field-group">
          <label>HCP Name</label>
          <div className={cls('field-readonly', '')}>{form.hcp_name || 'Awaiting AI extraction…'}</div>
        </div>
        <div className="field-group">
          <label>Interaction Date</label>
          <div className={cls('field-readonly', '')}>{form.interaction_date || 'Awaiting AI extraction…'}</div>
        </div>
      </div>

      <div className="field-group">
        <label>Sentiment</label>
        <div className={'field-readonly sentiment-' + (form.sentiment || 'neutral') + emptyCls}>
          {form.sentiment ? form.sentiment[0].toUpperCase() + form.sentiment.slice(1) : 'Awaiting AI extraction…'}
        </div>
      </div>

      <div className="field-group">
        <label>Products Discussed</label>
        <div className={cls('field-readonly', '')}>{form.products_discussed || 'Awaiting AI extraction…'}</div>
      </div>

      <div className="field-group">
        <label>Materials / Brochures Shared</label>
        <div className={cls('field-readonly', '')}>{form.materials_shared || 'Awaiting AI extraction…'}</div>
      </div>

      <div className="field-group">
        <label>Notes</label>
        <div className={cls('field-readonly', '')}>{form.notes || 'Awaiting AI extraction…'}</div>
      </div>

      <div className="field-group">
        <label>Follow-Up Schedule</label>
        <div className={cls('field-readonly', '')}>
          {form.follow_up_date
            ? form.follow_up_date + (form.follow_up_action ? ' — ' + form.follow_up_action : '')
            : 'Awaiting AI extraction…'}
        </div>
      </div>

      <div className="field-group">
        <label>Compliance Flag</label>
        <div
          className={
            'field-readonly' +
            (form.compliance_flag === 'review_needed' ? ' compliance-warning' : '') +
            (form.compliance_flag === 'compliant' ? ' compliant' : '') +
            emptyCls
          }
        >
          {form.compliance_flag === 'compliant'
            ? '✅ Compliant — no issues found'
            : form.compliance_flag === 'review_needed'
            ? '⚠️ Review Needed — see chat for details'
            : form.compliance_flag || 'Awaiting AI extraction…'}
        </div>
      </div>
    </div>
  );
}
