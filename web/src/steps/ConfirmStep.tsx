import type { Shop, SkuResult } from '../api'

type Props = { results: SkuResult[]; shop: Shop | null }

export default function ConfirmStep({ results, shop }: Props) {
  const joining = results.filter((r) => r.verdict !== 'escalate' && !r.skip)
  const skipped = results.filter((r) => r.skip)
  const escalated = results.filter((r) => r.verdict === 'escalate')

  return (
    <section className="panel">
      <h1>Confirm what happens next</h1>
      <ul className="summary">
        <li>
          <b>{joining.length} products join the Campaign</b> with the plans shown. MarginArena prepares the Seller Centre
          bulk-upload file; you upload it before {shop?.invitation.registration_closes ?? 'registration closes'}.
        </li>
        <li>
          <b>
            {skipped.length} {skipped.length === 1 ? 'product stays' : 'products stay'} out of the Campaign
          </b>{' '}
          at full price, because joining would cost profit even before rivals react.
        </li>
        <li>
          <b>
            {escalated.length} {escalated.length === 1 ? 'product waits' : 'products wait'} for the shop owner.
          </b>{' '}
          An approval request with the numbers goes to the owner.
        </li>
      </ul>
      <p className="small">
        Nothing is registered with the marketplace until you upload the file. Joining a Campaign is always your choice.
      </p>
      <button type="button" className="primary" disabled title="The Evolus workflow is connected in the next build step">
        Send to the Evolus workflow
      </button>
      <p className="small">The Evolus workflow connection is being built next.</p>
    </section>
  )
}
