import { useEffect } from 'react'
import { baht, pct, verdictWord, type SkuResult } from '../api'
import Explainer from './Explainer'

type Props = { result: SkuResult; onClose: () => void }

export default function HowWeDecided({ result: r, onClose }: Props) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  const w = r.waterfall
  const hasPlan = r.chosen_plan !== null && !r.skip
  const price = Number(w.selling_price)
  const steps = [
    { label: 'Campaign price', value: w.selling_price, kind: 'total' },
    { label: 'Shop voucher', value: `-${w.voucher}`, kind: 'minus' },
    { label: 'Marketplace fees', value: `-${w.fees.total}`, kind: 'minus' },
    { label: 'Product cost (and gift)', value: `-${w.unit_cost}`, kind: 'minus' },
    { label: 'Profit per unit', value: w.profit, kind: Number(w.profit) >= 0 ? 'profit' : 'loss' },
  ]
  let running = 0

  return (
    <div className="scrim" onClick={onClose}>
      <aside className="drawer" role="dialog" aria-modal="true" aria-label="How we decided" onClick={(e) => e.stopPropagation()}>
        <button type="button" className="close" onClick={onClose} aria-label="Close">
          ×
        </button>
        <p className={`pill pill--${r.skip ? 'skip' : r.verdict}`}>{verdictWord(r.verdict, r.skip)}</p>
        <h2>{r.name}</h2>
        <Explainer result={r} />

        <table className="compare">
          <thead>
            <tr>
              <th />
              <th scope="col">As invited</th>
              <th scope="col">{r.skip ? 'Not joining' : r.chosen_plan ? 'MarginArena' : 'Your call'}</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <th scope="row">Promo Plan</th>
              <td>{r.invited_plan}</td>
              <td>{r.chosen_plan ?? 'Decide with the numbers below'}</td>
            </tr>
            <tr>
              <th scope="row">Worst-case Campaign profit</th>
              <td>{baht(r.invited_worst_total)}</td>
              <td>{r.chosen_worst_total ? baht(r.chosen_worst_total) : `${baht(r.dont_join_total)} if you don't join`}</td>
            </tr>
            <tr>
              <th scope="row">Worst-case margin per unit</th>
              <td className={r.invited_failed_checks.includes('below the Margin Floor') ? 'neg' : ''}>
                {pct(r.invited_worst_margin, 1)}
              </td>
              <td>{r.skip ? 'Full price, no Campaign' : r.chosen_worst_margin ? pct(r.chosen_worst_margin, 1) : '–'}</td>
            </tr>
          </tbody>
        </table>
        {r.invited_failed_checks.length > 0 && (
          <p className="checks">Joining as invited: {r.invited_failed_checks.join('; ')}.</p>
        )}

        <h3>Where each baht goes ({w.plan})</h3>
        <div className="wf">
          {steps.map((s) => {
            const value = Number(s.value)
            const start = s.kind === 'minus' ? running + value : 0
            if (s.kind === 'total') running = value
            else if (s.kind === 'minus') running += value
            return (
              <div key={s.label} className={`wf-row wf-row--${s.kind}`}>
                <span>{s.label}</span>
                <span className="wf-track">
                  <span
                    className="wf-bar"
                    style={{ left: `${(Math.max(0, start) / price) * 100}%`, width: `${(Math.abs(value) / price) * 100}%` }}
                  />
                </span>
                <span className="num">{baht(s.value)}</span>
              </div>
            )
          })}
        </div>

        <h3>Every rival move it was tested against</h3>
        <p className="small">Campaign profit in the worst case across the elasticity band, for each move.</p>
        <table className="grid">
          <thead>
            <tr>
              <th scope="col">Rival move</th>
              <th scope="col" className="num">Rival at</th>
              <th scope="col" className="num">As invited</th>
              {hasPlan && (
                <th scope="col" className="num">
                  MarginArena
                </th>
              )}
            </tr>
          </thead>
          <tbody>
            {r.scenario_grid.map((g, i) => (
              <tr key={i}>
                <th scope="row">{g.rival}</th>
                <td className="num">{baht(g.effective_rival_price)}</td>
                <td className="num">{baht(g.invited_worst)}</td>
                {hasPlan && <td className="num">{baht(g.shown_worst)}</td>}
              </tr>
            ))}
          </tbody>
        </table>
        <p className="small">
          {Number(r.red_team_cut) > 0 ? (
            <>
              What the AI Rivals found: against the generic hold, match and undercut moves, the plan chosen first kept{' '}
              {baht(r.generic_worst_total)} in the worst case. The Counter-moves the Rivals found cut that to{' '}
              {baht(r.generic_worst_total_all_scenarios)} ({baht(-Number(r.red_team_cut))}).
              {hasPlan &&
                (Number(r.red_team_gain) > 0
                  ? ` MarginArena's plan keeps ${baht(r.chosen_worst_total)} against all of them.`
                  : ' The plan still holds against them.')}
            </>
          ) : (
            'The AI Rivals found no Counter-move worse than the generic hold, match and undercut moves.'
          )}
        </p>

        <h3>Where the numbers come from</h3>
        <ul className="evidence">
          {r.evidence.map((e, i) => (
            <li key={i}>
              <span className="ev-kind">{e.kind.replace('_', ' ')}</span>
              <span>{e.text}</span>
              <small>{e.source}</small>
            </li>
          ))}
        </ul>
      </aside>
    </div>
  )
}
