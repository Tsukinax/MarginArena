import { useState } from 'react'
import { baht, pct, usd, type SkuResult } from '../api'
import HowWeDecided from '../components/HowWeDecided'

type Props = { results: SkuResult[]; marginProtected: string; onNext: () => void }

const GROUPS = [
  {
    key: 'escalate',
    title: 'Needs your decision',
    hint: 'Joining earns more than not joining, but breaks your Margin Floor or depends on uncertain demand.',
    match: (r: SkuResult) => r.verdict === 'escalate',
  },
  {
    key: 'skip',
    title: 'Skip these',
    hint: 'Not joining keeps more profit than any plan, even in the worst case.',
    match: (r: SkuResult) => r.skip,
  },
  {
    key: 'revise',
    title: 'Better plan found',
    hint: 'Join, but with a different discount, voucher or gift.',
    match: (r: SkuResult) => r.verdict === 'revise' && !r.skip,
  },
  {
    key: 'approve',
    title: 'Good to join as invited',
    hint: 'The discount asked works for you, even against rivals.',
    match: (r: SkuResult) => r.verdict === 'approve',
  },
]

export default function VerdictsStep({ results, marginProtected, onNext }: Props) {
  const [open, setOpen] = useState<SkuResult | null>(null)
  const needYou = results.filter((r) => r.verdict === 'escalate').length

  return (
    <section className="panel">
      <h1>
        {needYou} {needYou === 1 ? 'product needs' : 'products need'} you. {results.length - needYou} {results.length - needYou === 1 ? 'is' : 'are'}{' '}
        ready.
      </h1>
      <p className="lead">
        Following these Verdicts keeps <b>{baht(marginProtected)}</b> ({usd(marginProtected)}) more profit in the worst
        case than joining as invited, counted over the products MarginArena decided.
      </p>

      {GROUPS.map((g) => {
        const rows = results.filter(g.match)
        if (rows.length === 0) return null
        return (
          <section key={g.key} className={`group group--${g.key}`}>
            <header>
              <h2>
                {g.title} <span>{rows.length}</span>
              </h2>
              <p>{g.hint}</p>
            </header>
            <ul>
              {rows.map((r) => (
                <li key={r.sku}>
                  <button type="button" onClick={() => setOpen(r)}>
                    <span className="row-name">{r.name}</span>
                    <span className="row-plan">{r.chosen_plan ?? `Invited: ${r.invited_plan}`}</span>
                    <span className="row-num">
                      {r.skip
                        ? `keeps ${baht(r.protected)} more by not joining`
                        : r.chosen_worst_total
                          ? `${baht(r.chosen_worst_total)} worst case`
                          : `${pct(r.invited_worst_margin, 1)} margin if joined`}
                    </span>
                    <span className="row-more">How we decided</span>
                  </button>
                </li>
              ))}
            </ul>
          </section>
        )
      })}

      <button type="button" className="primary" onClick={onNext}>
        Review and confirm
      </button>
      {open && <HowWeDecided result={open} onClose={() => setOpen(null)} />}
    </section>
  )
}
