import { baht, pct, type Shop } from '../api'

type Props = { shop: Shop | null; route: string | null; onStart: (recorded: boolean) => void }

export default function InvitationStep({ shop, route, onStart }: Props) {
  if (!shop) return <p className="muted">Loading the sample invitation…</p>
  const fallback = route !== 'mi300x'
  const count = fallback ? Math.min(4, shop.invited.length) : shop.invited.length

  return (
    <section className="panel">
      <h1>
        {shop.invitation.marketplace.split(' ')[0]} invited {shop.invited.length} of your products to{' '}
        {shop.invitation.campaign.replace(' Big Sale', '')}
      </h1>
      <p className="lead">
        Before you join, MarginArena checks every product against what rivals could do, using your costs and this
        year's marketplace fees. You confirm before anything happens.
      </p>

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
          <h2>Assumptions you can change</h2>
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
