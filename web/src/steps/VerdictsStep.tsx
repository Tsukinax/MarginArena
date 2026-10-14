import { useState } from 'react'
import { baht, pct, usd, type SkuResult } from '../api'
import HowWeDecided from '../components/HowWeDecided'

type Props = { results: SkuResult[]; marginProtected: string; onNext: () => void }

const GROUPS = [
  { verdict: 'escalate', title: 'Needs your decision', hint: 'No plan keeps your Margin Floor against every rival move.' },
  { verdict: 'revise', title: 'Better plan found', hint: 'Join, but with a different discount, voucher or gift.' },
  { verdict: 'approve', title: 'Good to join as invited', hint: 'The discount asked works for you, even against rivals.' },
] as const

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
        const rows = results.filter((r) => r.verdict === g.verdict)
        if (rows.length === 0) return null
        return (
          <section key={g.verdict} className={`group group--${g.verdict}`}>
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
                      {r.chosen_worst_total
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
