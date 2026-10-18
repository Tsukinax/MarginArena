import { useEffect, useMemo, useRef, useState } from 'react'
import { getHealth, getShop, runArena, type ArenaEvent, type Shop, type SkuResult } from './api'
import InvitationStep from './steps/InvitationStep'
import ArenaStep from './steps/ArenaStep'
import VerdictsStep from './steps/VerdictsStep'
import ConfirmStep from './steps/ConfirmStep'

const STEPS = ['Invitation', 'Arena', 'Verdicts', 'Confirm'] as const
export type Phase = 'idle' | 'running' | 'done' | 'error'

export default function App() {
  const [step, setStep] = useState(0)
  const [shop, setShop] = useState<Shop | null>(null)
  const [route, setRoute] = useState<{ route: string; model: string } | null>(null)
  const [healthChecked, setHealthChecked] = useState(false)
  const [events, setEvents] = useState<ArenaEvent[]>([])
  const [phase, setPhase] = useState<Phase>('idle')
  const [error, setError] = useState<string | null>(null)
  const [recorded, setRecorded] = useState(false)
  const abort = useRef<AbortController | null>(null)

  useEffect(() => {
    getShop().then(setShop, (e: Error) => setError(e.message))
    getHealth()
      .then(setRoute, () => setRoute(null))
      .finally(() => setHealthChecked(true))
  }, [])

  const done = useMemo(() => events.find((e) => e.type === 'run_done'), [events])
  const results: SkuResult[] = done && done.type === 'run_done' ? done.results : []

  const start = async (recorded: boolean) => {
    abort.current?.abort()
    abort.current = new AbortController()
    setEvents([])
    setError(null)
    setRecorded(recorded)
    setPhase('running')
    setStep(1)
    let received = 0
    try {
      await runArena(recorded ? { recorded: true } : {}, (e) => {
        received++
        setEvents((prev) => [...prev, e])
        if (e.type === 'error') setError(e.message)
      }, abort.current.signal)
      setPhase('done')
    } catch (e) {
      if ((e as Error).name !== 'AbortError') {
        setError((e as Error).message)
        setPhase(received ? 'error' : 'idle')
        if (!received) setStep(0) // refused before it started: back to the buttons, where the recorded run waits
      }
    }
  }

  const restart = () => {
    abort.current?.abort()
    setEvents([])
    setPhase('idle')
    setError(null)
    setStep(0)
  }

  return (
    <div className="app">
      <aside className="rail">
        <p className="brand">MarginArena</p>
        <ol className="steps">
          {STEPS.map((label, i) => {
            const reachable = i === 0 || (i === 1 && phase !== 'idle') || (i >= 2 && phase === 'done')
            return (
              <li key={label} className={i === step ? 'is-current' : i < step ? 'is-done' : ''}>
                <button type="button" disabled={!reachable} onClick={() => setStep(i)}>
                  <span className="step-n">{i + 1}</span>
                  {label}
                </button>
              </li>
            )
          })}
        </ol>
        <div className="route">
          {route ? (
            <>
              <span className="route-dot is-amd" aria-hidden />
              <span>
                {route.route === 'mi300x' ? 'AMD Instinct MI300X, our vLLM' : 'AMD Token Factory'}
                <small>{route.model}</small>
              </span>
            </>
          ) : (
            <span>{healthChecked ? 'Backend not reachable' : 'Checking AMD Token Factory…'}</span>
          )}
        </div>
        <p className="rail-note">
          AI explores what's open-ended: rival moves and plan ideas. Math solves what's closed: every number a Verdict uses
          comes from the pricing engine.
        </p>
        {step > 0 && (
          <button type="button" className="text-btn" onClick={restart}>
            Start over
          </button>
        )}
      </aside>

      <main className="main">
        {error && (
          <p className="error" role="alert">
            {error}
          </p>
        )}
        {step === 0 && <InvitationStep shop={shop} route={route?.route ?? null} onStart={start} />}
        {step === 1 && (
          <ArenaStep events={events} phase={phase} shop={shop} onNext={() => setStep(2)} />
        )}
        {step === 2 && done && done.type === 'run_done' && (
          <VerdictsStep results={results} marginProtected={done.margin_protected} shop={shop} onNext={() => setStep(3)} />
        )}
        {step === 3 && <ConfirmStep results={results} shop={shop} recorded={recorded} />}
      </main>
    </div>
  )
}
