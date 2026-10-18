import { useEffect, useState } from 'react'
import { baht, bahtExact, getRecordedSummary, pct, readInvitation, type InvitationReading, type RecordedSummary, type Shop } from '../api'

type Props = { shop: Shop | null; route: string | null; onStart: (recorded: boolean) => void }

export default function InvitationStep({ shop, route, onStart }: Props) {
  const [reading, setReading] = useState<InvitationReading | null>(null)
  const [readState, setReadState] = useState<'idle' | 'reading' | 'error'>('idle')
  const [readError, setReadError] = useState<string | null>(null)
  const [summary, setSummary] = useState<RecordedSummary | null>(null)
  useEffect(() => {
    // The reading the live site made on 15 Oct shows at once; a live reading can take minutes.
    readInvitation(true).then(setReading, () => setReading(null))
    getRecordedSummary().then(setSummary, () => setSummary(null))
  }, [])
  if (!shop) return <p className="muted">Loading the sample invitation…</p>
  const fallback = route !== 'mi300x'
  const count = fallback ? Math.min(4, shop.invited.length) : shop.invited.length
  const checks = new Map(reading?.checks.map((c) => [c.sku, c]))
  const misread = reading?.checks.filter((c) => !c.matches).map((c) => c.sku) ?? []

  const read = async () => {
    setReadState('reading')
    setReadError(null)
    try {
      setReading(await readInvitation(false))
      setReadState('idle')
    } catch (e) {
      setReadError((e as Error).message)
      setReadState('error')
    }
  }

  const [full, twenty, thirty] = shop.fee_example
  const v = summary?.verdicts

  return (
    <section className="panel">
      <section className="hero" aria-label="What MarginArena does">
        <p className="hero-eyebrow">Check a Campaign Invitation before you join it</p>
        {full && twenty && thirty && (
          <p className="hero-problem">
            At Shopee Thailand's fees, a {baht(full.list_price)} product that costs {baht(full.cost)} earns{' '}
            <b>{bahtExact(full.unit_profit)}</b> at full price, <b>{bahtExact(twenty.unit_profit)}</b> at{' '}
            {twenty.discount_pct}% off, and <b className="neg">{bahtExact(thirty.unit_profit)}</b> at{' '}
            {thirty.discount_pct}% off, per unit. MarginArena decides, product by product, whether the invited discount
            pays, even after rivals react.
          </p>
        )}
        {summary && v && (
          <div className="hero-result">
            <p className="hero-number">{bahtExact(summary.margin_protected_by_skips)}</p>
            <p className="hero-what">
              more profit in the worst case for this sample shop by skipping{' '}
              {summary.skipped.map((id) => shop.invited.find((s) => s.id === id)?.name ?? id).join(' and ')} instead
              of joining them as invited. All {summary.products} Verdicts ({v.approve} Approve, {v.revise} Revise, {v.skip} Skip,{' '}
              {v.escalate} Escalate left to a person) keep {bahtExact(summary.margin_protected)}; the rest comes from
              the sunscreen's Revise, which rests on a labelled Seller override.
              <small>
                Recorded{' '}
                {new Date(summary.recorded_at).toLocaleDateString('en-GB', {
                  day: 'numeric',
                  month: 'short',
                  year: 'numeric',
                  timeZone: 'Asia/Bangkok',
                })}{' '}
                with {summary.model} on AMD Token Factory: {summary.calls_ok} model calls, {summary.calls_failed} failed.
                {summary.rival_changed.length > 0 &&
                  ` A Rival's Counter-move changed the plan for ${summary.rival_changed
                    .map((id) => shop.invited.find((s) => s.id === id)?.name ?? id)
                    .join(', ')}.`}
              </small>
            </p>
          </div>
        )}
        <div className="start-actions">
          <button type="button" className="primary" onClick={() => onStart(true)}>
            Watch the recorded Arena (about 20 s)
          </button>
          <button type="button" className="secondary on-dark" onClick={() => onStart(false)}>
            Run {count === shop.invited.length ? `all ${count}` : count} live on AMD Token Factory
          </button>
        </div>
      </section>

      <h1>
        {shop.invitation.marketplace.split(' ')[0]} invited {shop.invited.length} of your products to{' '}
        {shop.invitation.campaign.replace(' Big Sale', '')}
      </h1>
      <p className="lead">
        Before you join, MarginArena checks every product against what rivals could do, using your costs and this
        year's marketplace fees. You confirm before anything happens.
      </p>
      <div className="read-invitation">
        <a href="/api/invitation/sample.pdf" target="_blank" rel="noreferrer">
          Open the invitation (PDF)
        </a>
        <button type="button" className="text-btn" disabled={readState === 'reading'} onClick={read}>
          {readState === 'reading'
            ? 'Evolus is reading it…'
            : reading?.recorded
              ? 'Read it again live with Evolus (2–3 min)'
              : 'Read it with the Evolus extractor (2–3 min)'}
        </button>
        {readState === 'reading' && <span className="small">From 40 seconds to 3 minutes, depending on AMD Token Factory.</span>}
        {reading && (
          <span className="small">
            {reading.recorded
              ? `The Evolus extractor read this PDF on ${new Date(reading.read_at).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'Asia/Bangkok' })} (recorded, run ${reading.execution_id?.slice(0, 8)}): `
              : `Evolus read ${reading.read.items.length} products${reading.cached ? ` (this server's reading from ${new Date(reading.read_at).toLocaleTimeString('en-GB')})` : ''}: `}
            {reading.matches
              ? 'every minimum discount matches the table below.'
              : `${misread.length + reading.extra_skus.length} do not match: ${[...misread, ...reading.extra_skus].join(', ')}.`}
          </span>
        )}
        {readError && (
          <span className="error" role="alert">
            {readError}
          </span>
        )}
      </div>

      <div className="invite-grid">
        <dl className="facts">
          <div>
            <dt>Shop</dt>
            <dd>{shop.name}</dd>
          </div>
          <div>
            <dt>Campaign</dt>
            <dd>
              {shop.invitation.campaign}, {shop.invitation.slot}
            </dd>
          </div>
          <div>
            <dt>Registration closes</dt>
            <dd>{shop.invitation.registration_closes}</dd>
          </div>
          <div>
            <dt>Your Margin Floor</dt>
            <dd>{pct(shop.margin_floor)} profit on every unit, after fees and cost</dd>
          </div>
          <div>
            <dt>Fees</dt>
            <dd>
              Shopee TH Non-Mall PRIME, effective {shop.profile.effective_from}: {pct(shop.profile.commission_rate)}{' '}
              commission, {pct(shop.profile.programme_fee_rate)} PRIME, {pct(shop.profile.payment_fee_rate)} payment and
              ฿{shop.profile.fixed_fee_per_order} per order, plus {pct(shop.profile.vat_rate)} VAT
            </dd>
          </div>
        </dl>

        <div className="assumptions">
          <h2>Assumptions (set in the sample shop file)</h2>
          <ul>
            <li>Campaign traffic ×{shop.assumptions.traffic_lift} before any price effect</li>
            <li>Buyers value a free gift at {pct(shop.assumptions.gift_value_ratio)} of its retail price</li>
            <li>When a rival ends up cheaper, you keep (rival ÷ your price)^{shop.assumptions.cross_price_sensitivity} of buyers</li>
            <li>Price response: {shop.assumptions.elasticity}</li>
            {shop.invited
              .filter((s) => shop.elasticity_overrides[s.id])
              .map((s) => (
                <li key={s.id}>
                  {s.name}: {shop.elasticity_overrides[s.id].text} Source: {shop.elasticity_overrides[s.id].source}.
                </li>
              ))}
          </ul>
          {shop.brand_rules.map((r) => (
            <p key={r.clause} className="clause">
              <b>{r.clause}.</b> {r.text}
            </p>
          ))}
        </div>
      </div>

      <table className="sku-table">
        <thead>
          <tr>
            <th scope="col">Product</th>
            <th scope="col">Brand</th>
            <th scope="col" className="num">Price</th>
            <th scope="col" className="num">Your cost</th>
            <th scope="col" className="num">Stock</th>
            <th scope="col" className="num">Discount asked</th>
            {reading && (
              <th scope="col" className="num">
                Read by Evolus
              </th>
            )}
          </tr>
        </thead>
        <tbody>
          {shop.invited.map((s) => (
            <tr key={s.id}>
              <th scope="row">
                {s.name}
                {shop.elasticity_overrides[s.id] && <span className="override-flag">Seller override</span>}
              </th>
              <td>{s.brand}</td>
              <td className="num">{baht(s.list_price)}</td>
              <td className="num">{baht(s.cost)}</td>
              <td className="num">{s.stock}</td>
              <td className="num">{pct(s.required_discount)}</td>
              {reading && (
                <td className={`num ${checks.get(s.id)?.matches ? '' : 'neg'}`}>
                  {checks.get(s.id)?.read_discount_pct ?? '–'}% {checks.get(s.id)?.matches ? '✓' : '✗'}
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>

      <p className="small">{shop.label}</p>
      <div className="start-actions">
        <button type="button" className="primary" onClick={() => onStart(true)}>
          Watch all {shop.invited.length} products (recorded run)
        </button>
        <button type="button" className="secondary" onClick={() => onStart(false)}>
          Run {count === shop.invited.length ? `all ${count}` : count} live
        </button>
      </div>
      <p className="small">
        The recorded run is a real Arena on AMD Token Factory, replayed in about 20 seconds.
        {fallback &&
          ` A live run checks ${count} of the ${shop.invited.length} products, to stay within Token Factory's shared rate limit, and takes 1–2 minutes.`}
      </p>
    </section>
  )
}
