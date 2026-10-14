import { useMemo, useState } from 'react'
import { baht, usd, verdictWord, type ArenaEvent, type Shop, type Telemetry } from '../api'
import type { Phase } from '../App'

type Props = { events: ArenaEvent[]; phase: Phase; shop: Shop | null; onNext: () => void }

type SkuView = {
  ideas: Extract<ArenaEvent, { type: 'idea' }>[]
  rounds: Map<number, { moves: Extract<ArenaEvent, { type: 'rival_move' }>[]; leader?: Extract<ArenaEvent, { type: 'leader' }> }>
  decided?: Extract<ArenaEvent, { type: 'sku_decided' }>
}

export default function ArenaStep({ events, phase, shop, onNext }: Props) {
  const started = events.find((e) => e.type === 'run_started')
  const skus = started && started.type === 'run_started' ? started.skus : []
  const [picked, setPicked] = useState<string | null>(null)

  const views = useMemo(() => {
    const m = new Map<string, SkuView>()
    const view = (sku: string) => {
      if (!m.has(sku)) m.set(sku, { ideas: [], rounds: new Map() })
      return m.get(sku)!
    }
    const round = (v: SkuView, n: number) => {
      if (!v.rounds.has(n)) v.rounds.set(n, { moves: [] })
      return v.rounds.get(n)!
    }
    for (const e of events) {
      if (e.type === 'idea') view(e.sku).ideas.push(e)
      if (e.type === 'round_started') round(view(e.sku), e.round)
      if (e.type === 'rival_move') round(view(e.sku), e.round).moves.push(e)
      if (e.type === 'leader') round(view(e.sku), e.round).leader = e
      if (e.type === 'sku_decided') view(e.sku).decided = e
    }
    return m
  }, [events])

  const telemetry: Telemetry | null = useMemo(() => {
    for (let i = events.length - 1; i >= 0; i--) {
      const e = events[i]
      if (e.type === 'leader' || e.type === 'run_done') return e.telemetry
    }
    return null
  }, [events])
  const done = events.find((e) => e.type === 'run_done')
  const selected = picked ?? skus.find((s) => !views.get(s)?.decided) ?? skus[0]
  const v = selected ? views.get(selected) : undefined
  const product = shop?.invited.find((s) => s.id === selected)
  const calls = telemetry ? telemetry.calls_ok + telemetry.calls_invalid + telemetry.calls_failed : 0

  return (
    <section className="arena">
      <header className="scoreboard">
        <div className="sb-title">
          <span className="sb-logo">Arena</span>
          <span className="sb-sub">
            {started && started.type === 'run_started'
              ? `${started.model} on ${started.route === 'mi300x' ? 'AMD Instinct MI300X' : 'AMD Token Factory'}`
              : 'Connecting…'}
          </span>
        </div>
        <dl className="sb-stats">
          <div>
            <dt>LLM calls</dt>
            <dd>{calls}</dd>
          </div>
          <div>
            <dt>Tokens per second</dt>
            <dd>{telemetry ? telemetry.tokens_per_second.toLocaleString('en-US') : '–'}</dd>
          </div>
          <div>
            <dt>Rejected answers</dt>
            <dd>{telemetry ? telemetry.calls_invalid : '–'}</dd>
          </div>
          <div>
            <dt>Margin protected</dt>
            <dd className="gold">{done && done.type === 'run_done' ? baht(done.margin_protected) : '…'}</dd>
          </div>
        </dl>
      </header>

      <div className="arena-body">
        <nav className="fixtures" aria-label="Products in the Arena">
          <h2>Products</h2>
          <ol>
            {skus.map((s) => {
              const sv = views.get(s)
              const status = sv?.decided
                ? sv.decided.skip
                  ? 'skip'
                  : sv.decided.verdict
                : sv && sv.rounds.size > 0
                  ? 'live'
                  : 'waiting'
              const name = shop?.invited.find((x) => x.id === s)?.name ?? s
              return (
                <li key={s}>
                  <button
                    type="button"
                    className={`fixture ${s === selected ? 'is-selected' : ''}`}
                    onClick={() => setPicked(s)}
                  >
                    <span className={`dot dot--${status}`} aria-hidden />
                    <span className="fixture-name">{name}</span>
                    <span className={`tag tag--${status}`}>{statusWord(status)}</span>
                  </button>
                </li>
              )
            })}
          </ol>
        </nav>

        <div className="stage">
          {!v || !product ? (
            <p className="stage-wait">Strategists are reading the invitation…</p>
          ) : (
            <>
              <div className="stage-head">
                <h1>{product.name}</h1>
                <p>
                  {baht(product.list_price)} today, invited at {(Number(product.required_discount) * 100).toFixed(0)}%
                  off{shop?.rival_snapshot[product.id] ? `, rival at ${baht(shop.rival_snapshot[product.id].reference_price)}` : ''}
                </p>
              </div>

              <div className="ideas">
                <h3>Plan Ideas from the Strategists</h3>
                {v.ideas.length === 0 && <p className="dim">The engine always tests a plain cut and a voucher.</p>}
                <ul>
                  {v.ideas.map((i, n) => (
                    <li key={n}>
                      <b>{i.strategist}</b>{' '}
                      {[i.use_voucher ? 'use a shop voucher' : 'no voucher', i.gift ? `gift: ${i.gift}` : 'no gift'].join(', ')}
                      <em>{i.why}</em>
                    </li>
                  ))}
                </ul>
              </div>

              <div className="rounds">
                {[...v.rounds.entries()].map(([n, r]) => (
                  <div className="round" key={n}>
                    <h3>Round {n}: red team</h3>
                    {r.moves.length === 0 && <p className="dim">Rivals are looking for a weakness…</p>}
                    {r.moves.map((m, k) => (
                      <article className="move" key={k}>
                        <span className="move-who">{m.rival}</span>
                        <span className="move-what">{moveText(m)}</span>
                        <span className="move-price">rival effectively at {baht(m.effective_rival_price)}</span>
                      </article>
                    ))}
                    {r.leader && (
                      <p className={`leader ${r.leader.changed ? 'is-changed' : ''}`}>
                        {r.leader.skip
                          ? 'Not joining beats every plan so far'
                          : `${r.leader.changed ? 'New leader: ' : 'Leader holds: '}${r.leader.plan ?? 'no plan passes'}`}
                      </p>
                    )}
                  </div>
                ))}
              </div>

              {v.decided && (
                <article className={`champion champion--${v.decided.skip ? 'skip' : v.decided.verdict}`}>
                  <p className="verdict">{verdictWord(v.decided.verdict, v.decided.skip)}</p>
                  <p className="champion-plan">{v.decided.chosen_plan ?? 'No plan survives every rival move'}</p>
                  <dl>
                    <div>
                      <dt>{v.decided.skip ? 'Worst case, not joining' : 'Worst case, this plan'}</dt>
                      <dd>{baht(v.decided.chosen_worst_total ?? v.decided.invited_worst_total)}</dd>
                    </div>
                    <div>
                      <dt>Worst case, as invited</dt>
                      <dd>{baht(v.decided.invited_worst_total)}</dd>
                    </div>
                    <div>
                      <dt>Searched</dt>
                      <dd>
                        {v.decided.plans_searched} plans × {v.decided.scenarios} rival moves
                      </dd>
                    </div>
                  </dl>
                </article>
              )}
            </>
          )}
        </div>

        <aside className="feed" aria-live="polite" aria-label="Commentary">
          <h2>Commentary</h2>
          <ol>
            {events
              .map((e, n) => ({ e, n, text: commentary(e) }))
              .filter((x) => x.text)
              .slice(-40)
              .reverse()
              .map(({ e, n, text }) => (
                <li key={n} className={`ev ev--${e.type}`}>
                  {text}
                </li>
              ))}
          </ol>
        </aside>
      </div>

      <footer className="arena-foot">
        {phase === 'running' && <p>The Arena is running. Every number comes from the pricing engine.</p>}
        {done && done.type === 'run_done' && (
          <>
            <p>
              Done in {done.telemetry.elapsed_seconds}s. Margin protected {baht(done.margin_protected)}{' '}
              {usd(done.margin_protected)} in the worst case.
            </p>
            <button type="button" className="primary" onClick={onNext}>
              See the Verdicts
            </button>
          </>
        )}
      </footer>
    </section>
  )
}

function moveText(m: Extract<ArenaEvent, { type: 'rival_move' }>): string {
  const parts = [`${m.headline_cut_pct}% off`]
  if (m.voucher_baht) parts.push(`฿${m.voucher_baht} voucher`)
  if (m.free_shipping_baht) parts.push(`฿${m.free_shipping_baht} free shipping`)
  if (m.gift_value_baht) parts.push(`฿${m.gift_value_baht} gift`)
  return parts.join(' + ')
}

function commentary(e: ArenaEvent): string | null {
  switch (e.type) {
    case 'run_started':
      return `Arena started on ${e.route === 'mi300x' ? 'AMD Instinct MI300X' : 'AMD Token Factory'} with ${e.skus.length} products.`
    case 'idea':
      return `${e.sku}: ${e.strategist} suggests ${e.gift ? `a ${e.gift} gift` : e.use_voucher ? 'a shop voucher' : 'a plain cut'}.`
    case 'rival_move':
      return `${e.sku}: ${e.rival} answers with ${moveText(e)}. ${e.why}`
    case 'leader':
      return `${e.sku} round ${e.round}: ${e.changed ? 'leader changes to' : 'leader holds:'} ${e.plan ?? 'nothing passes'}.`
    case 'sku_decided':
      return `${e.sku}: ${verdictWord(e.verdict, e.skip)}.`
    case 'error':
      return `Error: ${e.message}`
    default:
      return null
  }
}

function statusWord(s: string) {
  return ({ waiting: 'Waiting', live: 'Live', approve: 'Approve', revise: 'Revise', skip: 'Skip', escalate: 'Escalate' } as Record<string, string>)[s] ?? s
}
