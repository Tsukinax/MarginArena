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
}

export type Telemetry = {
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
  generic_worst_total_all_scenarios: string
  red_team_gain: string | null
  scenarios: number
  rounds_played: number
  plans_searched: number
  waterfall: Waterfall
  scenario_grid: { rival: string; effective_rival_price: string; invited_total: string; shown_total: string }[]
  evidence: EvidenceLink[]
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

export type ArenaRequest = { skus?: string[]; rounds?: number; rivals?: number; strategists?: number }

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
  if (!r.ok || !r.body) throw new Error(`The Arena could not start (${r.status}).`)
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
  if (!r.ok) throw new Error(`The explanation could not be written (${r.status}).`)
  return r.json()
}

export const baht = (x: string | number | null | undefined): string => {
  if (x === null || x === undefined || x === '') return '–'
  const n = typeof x === 'number' ? x : Number(x)
  const sign = n < 0 ? '−' : ''
  return `${sign}฿${Math.abs(n).toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`
}

export const USD_PER_THB = 0.029
export const usd = (x: string | number): string =>
  `≈ $${Math.round(Math.abs(Number(x)) * USD_PER_THB).toLocaleString('en-US')}`

export const pct = (x: string | number, digits = 0): string => `${(Number(x) * 100).toFixed(digits)}%`

export const verdictWord = (v: string, skip = false): string =>
  skip ? 'Skip' : v === 'approve' ? 'Approve' : v === 'revise' ? 'Revise' : 'Escalate'
