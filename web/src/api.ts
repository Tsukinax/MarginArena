// Types and calls for the MarginArena backend. Money arrives as decimal strings; the UI never computes it.

export type InvitedSku = {
  id: string
  name: string
  brand: string
  list_price: string
  cost: string
  stock: number
  required_discount: string
}

export type Shop = {
  id: string
  name: string
  label: string
  invitation: { marketplace: string; campaign: string; slot: string; registration_closes: string }
  margin_floor: string
  profile: {
    id: string
    effective_from: string
    commission_rate: string
    payment_fee_rate: string
    programme_fee_rate: string
    fixed_fee_per_order: string
    vat_rate: string
  }
  assumptions: { traffic_lift: string; cross_price_sensitivity: string; gift_value_ratio: string; elasticity: string }
  invited: InvitedSku[]
  brand_rules: { clause: string; brand: string; text: string }[]
  rival_snapshot: Record<string, { rival: string; reference_price: string }>
  /** Per-SKU elasticities the Seller set in place of the pooled fit, each with its own band and label (Q56). */
  elasticity_overrides: Record<string, { elasticity: string; band: [string, string]; text: string; source: string }>
}

export type Telemetry = {
  /** The model answering now: the run's model, or its fallback once the route said that model had no workers. */
  model: string
  calls_ok: number
  calls_invalid: number
  calls_failed: number
  retries: number
  in_flight: number
  completion_tokens: number
  tokens_per_second: number
  elapsed_seconds: number
}

export type Waterfall = {
  plan: string
  list_price: string
  selling_price: string
  voucher: string
  seller_net: string
  fees: { commission: string; payment: string; programme: string; fixed: string; total: string }
  unit_cost: string
  profit: string
  margin: string
}

export type EvidenceLink = { kind: string; text: string; source: string }

export type SkuResult = {
  sku: string
  name: string
  verdict: 'approve' | 'revise' | 'escalate'
  /** A Revise whose better offer is not joining (Q54). */
  skip: boolean
  invited_plan: string
  invited_failed_checks: string[]
  invited_worst_total: string
  invited_expected_total: string
  invited_worst_margin: string
  chosen_plan: string | null
  chosen_worst_total: string | null
  chosen_expected_total: string | null
  chosen_worst_margin: string | null
  dont_join_total: string
  /** This SKU's Margin Floor, as a fraction of the selling price. */
  margin_floor: string
  protected: string
  generic_plan: string
  /** Worst case of the plan chosen against the generic hold, match and undercut moves only. */
  generic_worst_total: string
  generic_worst_total_all_scenarios: string
  /** How much the Counter-moves the AI Rivals found lower that worst case (proof 6). */
  red_team_cut: string
  red_team_gain: string | null
  scenarios: number
  rounds_played: number
  plans_searched: number
  waterfall: Waterfall
  /** Per Counter-move: totals at the point elasticity, and the worst case across the elasticity band. */
  scenario_grid: {
    rival: string
    effective_rival_price: string
    invited_total: string
    shown_total: string
    invited_worst: string
    shown_worst: string
  }[]
  evidence: EvidenceLink[]
  /** The server's HMAC of this result; /api/explain refuses a result without it or with any field changed. */
  signature: string
}

export type ArenaEvent =
  | {
      type: 'run_started'
      route: string
      model: string
      shop: string
      label: string
      skus: string[]
      rounds: number
      rivals: number
      strategists: number
      elasticity: string
      /** Set when the events replay a recorded run: when it was recorded (ISO 8601). */
      recorded_at?: string
    }
  | { type: 'idea'; sku: string; strategist: string; use_voucher: boolean; gift: string | null; why: string }
  | { type: 'round_started'; sku: string; round: number; leader: string }
  | {
      type: 'rival_move'
      sku: string
      round: number
      rival: string
      headline_cut_pct: number
      voucher_baht: number
      free_shipping_baht: number
      gift_value_baht: number
      effective_rival_price: string
      why: string
    }
  | {
      type: 'leader'
      sku: string
      round: number
      verdict: string
      skip: boolean
      plan: string | null
      changed: boolean
      telemetry: Telemetry
    }
  | ({ type: 'sku_decided' } & SkuResult)
  | { type: 'run_done'; results: SkuResult[]; margin_protected: string; telemetry: Telemetry }
  | { type: 'error'; message: string }

export type ArenaRequest = {
  skus?: string[]
  rounds?: number
  rivals?: number
  strategists?: number
  /** Replay the recorded 12-product run instead of calling the model. */
  recorded?: boolean
}

export type Language = 'en' | 'th'

export type Explanation = {
  language: Language
  text: string
  /** 'model': the model's draft passed the number check. 'template': the numbers-only fallback. */
  source: 'model' | 'template'
  /** Drafts the backend threw away; `text` is null when the model didn't answer. */
  rejected: { text: string | null; unsupported: string[] }[]
  route: string
  model: string
}

export async function getHealth(): Promise<{ route: string; model: string }> {
  const r = await fetch('/api/health')
  if (!r.ok) throw new Error(`The backend did not answer (${r.status}).`)
  return r.json()
}

export async function getShop(id = 'glow-lab-bkk'): Promise<Shop> {
  const r = await fetch(`/api/shops/${id}`)
  if (!r.ok) throw new Error(`Could not load the sample shop (${r.status}).`)
  return r.json()
}

/** Runs one Arena and calls onEvent for every Server-Sent Event as it arrives. */
export async function runArena(
  body: ArenaRequest,
  onEvent: (e: ArenaEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const r = await fetch('/api/arena', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ shop: 'glow-lab-bkk', ...body }),
    signal,
  })
  if (!r.ok || !r.body)
    throw new Error((await r.json().catch(() => null))?.detail ?? `The Arena could not start (${r.status}).`)
  const reader = r.body.pipeThrough(new TextDecoderStream()).getReader()
  let buffer = ''
  for (;;) {
    const { value, done } = await reader.read()
    if (done) break
    buffer += value
    let cut: number
    while ((cut = buffer.indexOf('\n\n')) >= 0) {
      const chunk = buffer.slice(0, cut)
      buffer = buffer.slice(cut + 2)
      const data = chunk
        .split('\n')
        .filter((l) => l.startsWith('data: '))
        .map((l) => l.slice(6))
        .join('\n')
      if (data) onEvent(JSON.parse(data) as ArenaEvent)
    }
  }
}

/** Explains one decided SKU. The backend rejects any draft that cites a number the engine never produced. */
export async function explainVerdict(result: SkuResult, language: Language): Promise<Explanation> {
  const r = await fetch('/api/explain', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ result, language }),
  })
  if (!r.ok)
    throw new Error((await r.json().catch(() => null))?.detail ?? `The explanation could not be written (${r.status}).`)
  return r.json()
}

/** The Evolus extractor's reading of the sample invitation PDF, each discount checked against the Arena's. */
export type InvitationReading = {
  read: { campaign: string; slot: string; registration_closes: string; items: { sku: string }[] }
  checks: { sku: string; read_discount_pct: string | null; expected_discount_pct: string; matches: boolean }[]
  extra_skus: string[]
  matches: boolean
  execution_id: string | null
  read_at: string
  /** True for the reading the live site made on 15 Oct, replayed without calling Evolus. */
  recorded: boolean
  cached: boolean
}

/** The recorded reading answers at once; a live reading asks the Evolus extractor and can take minutes. */
export async function readInvitation(recorded = false): Promise<InvitationReading> {
  const r = await fetch('/api/invitation/read', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ recorded }),
  })
  if (!r.ok) throw new Error((await r.json().catch(() => null))?.detail ?? `The invitation could not be read (${r.status}).`)
  return r.json()
}

/** What the Evolus Verdict workflow returns (infra/evolus/evolus_kit.py, step "Assemble the result"). */
export type WorkflowResult = {
  shop: string
  campaign: string
  upload: {
    sku: string
    product: string
    promo_plan: string
    campaign_price: string
    voucher: string
    verdict: string
  }[]
  escalations: { sku: string; product: string }[]
  skipped: string[]
  approval_request: string | null
}

export type Confirmation = { status: string | null; result: WorkflowResult | string | null }

/** The Verdict workflow's run on the recorded Arena's Verdicts (15 Oct), shown when a live run cannot start. */
export type RecordedWorkflowRun = {
  execution_id: string
  completed_at: string
  seconds: number
  credits: number
  result: WorkflowResult
  recorded: true
}

/** Starts the Evolus Verdict workflow on the confirmed Verdicts; the server refuses any it did not sign. */
export async function confirmVerdicts(results: SkuResult[]): Promise<string> {
  const r = await fetch('/api/confirm', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ results }),
  })
  if (!r.ok) throw new Error((await r.json().catch(() => null))?.detail ?? `The workflow could not start (${r.status}).`)
  return (await r.json()).execution_id
}

export async function getRecordedConfirmation(): Promise<RecordedWorkflowRun> {
  const r = await fetch('/api/confirm/recorded')
  if (!r.ok) throw new Error(`The recorded Evolus run could not be loaded (${r.status}).`)
  return r.json()
}

export async function getConfirmation(executionId: string): Promise<Confirmation> {
  const r = await fetch(`/api/confirm/${executionId}`)
  if (!r.ok) throw new Error(`Evolus did not report the run (${r.status}).`)
  return r.json()
}

export const baht = (x: string | number | null | undefined): string => {
  if (x === null || x === undefined || x === '') return '–'
  const n = typeof x === 'number' ? x : Number(x)
  const sign = n < 0 ? '−' : ''
  return `${sign}฿${Math.abs(n).toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`
}

/** Bank of Thailand reference rate, 15 Oct 2026 (BOT statistics, report FM_FX_001_S3), for the "≈ $" shown beside baht. */
export const THB_PER_USD = 33.541
export const usd = (x: string | number): string =>
  `≈ $${Math.round(Math.abs(Number(x)) / THB_PER_USD).toLocaleString('en-US')}`

export const pct = (x: string | number, digits = 0): string => `${(Number(x) * 100).toFixed(digits)}%`

export const verdictWord = (v: string, skip = false): string =>
  skip ? 'Skip' : v === 'approve' ? 'Approve' : v === 'revise' ? 'Revise' : 'Escalate'
