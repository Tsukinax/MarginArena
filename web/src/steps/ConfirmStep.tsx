import { useState } from 'react'
import { baht, confirmVerdicts, getConfirmation, type Shop, type SkuResult, type WorkflowResult } from '../api'

type Props = { results: SkuResult[]; shop: Shop | null }
type Run =
  | { state: 'idle' }
  | { state: 'running'; executionId?: string; status?: string | null }
  | { state: 'done'; executionId: string; result: WorkflowResult }
  | { state: 'error'; message: string }

const POLL_MS = 3000
const MAX_POLLS = 60 // about 3 minutes

function csv(rows: WorkflowResult['upload']): string {
  const cell = (s: string) => (/[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s)
  const head = ['SKU', 'Product', 'Campaign price (THB)', 'Shop voucher (THB)', 'Promo Plan', 'Verdict']
  const body = rows.map((r) => [r.sku, r.product, r.campaign_price, r.voucher, r.promo_plan, r.verdict].map(cell))
  return [head, ...body].map((line) => line.join(',')).join('\n') + '\n'
}

export default function ConfirmStep({ results, shop }: Props) {
  const [run, setRun] = useState<Run>({ state: 'idle' })
  const joining = results.filter((r) => r.verdict !== 'escalate' && !r.skip)
  const skipped = results.filter((r) => r.skip)
  const escalated = results.filter((r) => r.verdict === 'escalate')

  const start = async () => {
    setRun({ state: 'running' })
    try {
      const executionId = await confirmVerdicts(results)
      for (let i = 0; i < MAX_POLLS; i++) {
        const c = await getConfirmation(executionId)
        setRun({ state: 'running', executionId, status: c.status })
        if (c.status === 'Completed' && c.result && typeof c.result === 'object') {
          setRun({ state: 'done', executionId, result: c.result })
          return
        }
        if (c.status === 'Failed') throw new Error(`The Evolus workflow failed (run ${executionId}).`)
        await new Promise((resolve) => setTimeout(resolve, POLL_MS))
      }
      throw new Error(`The Evolus workflow is still running (run ${executionId}); try again shortly.`)
    } catch (e) {
      setRun({ state: 'error', message: (e as Error).message })
    }
  }

  const download = (rows: WorkflowResult['upload']) => {
    const url = URL.createObjectURL(new Blob([csv(rows)], { type: 'text/csv' }))
    const a = Object.assign(document.createElement('a'), { href: url, download: 'marginarena-campaign-upload.csv' })
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <section className="panel">
      <h1>Confirm what happens next</h1>
      <ul className="summary">
        <li>
          <b>{joining.length} products join the Campaign</b> with the plans shown. The Evolus workflow prepares the
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
          The Campaign Desk agent drafts the approval request, with the numbers.
        </li>
      </ul>
      <p className="small">
        Nothing is registered with the marketplace until you upload the file, and no email is sent. Joining a Campaign is
        always your choice.
      </p>
      <button type="button" className="primary" disabled={run.state === 'running'} onClick={start}>
        {run.state === 'running' ? 'Evolus workflow running…' : 'Confirm and run the Evolus workflow'}
      </button>
      {run.state === 'running' && run.executionId && (
        <p className="small">
          Evolus run {run.executionId}: {run.status ?? 'starting'}.
        </p>
      )}
      {run.state === 'error' && (
        <p className="error" role="alert">
          {run.message}
        </p>
      )}
      {run.state === 'done' && (
        <div className="workflow-result">
          <h2>Carried out by the Evolus workflow "MarginArena Verdict"</h2>
          <p className="small">Run {run.executionId}. The file's columns are MarginArena's; Seller Centre's template is not public.</p>
          <table className="sku-table">
            <thead>
              <tr>
                <th scope="col">Product</th>
                <th scope="col">Promo Plan</th>
                <th scope="col" className="num">Campaign price</th>
                <th scope="col" className="num">Shop voucher</th>
              </tr>
            </thead>
            <tbody>
              {run.result.upload.map((r) => (
                <tr key={r.sku}>
                  <th scope="row">{r.product}</th>
                  <td>{r.promo_plan}</td>
                  <td className="num">{baht(r.campaign_price)}</td>
                  <td className="num">{baht(r.voucher)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <button type="button" className="secondary" onClick={() => download(run.result.upload)}>
            Download the bulk-upload file (CSV)
          </button>
          {run.result.approval_request && (
            <>
              <h2>Approval request for the shop owner (draft, not sent)</h2>
              <pre className="draft">{run.result.approval_request}</pre>
            </>
          )}
        </div>
      )}
    </section>
  )
}
