import { useState } from 'react'
import { explainVerdict, type Explanation, type Language, type SkuResult } from '../api'

const LANGUAGES: { id: Language; label: string }[] = [
  { id: 'en', label: 'English' },
  { id: 'th', label: 'ไทย' },
]

/** The Verdict in plain words, written by the model on AMD and checked number by number against the engine. */
export default function Explainer({ result }: { result: SkuResult }) {
  const [language, setLanguage] = useState<Language | null>(null)
  const [answers, setAnswers] = useState<Partial<Record<Language, Explanation>>>({})
  const [writing, setWriting] = useState<Language | null>(null)
  const [error, setError] = useState<string | null>(null)

  const ask = async (lang: Language, live = false) => {
    setLanguage(lang)
    setError(null)
    if (answers[lang] && !live) return
    setWriting(lang)
    try {
      const answer = await explainVerdict(result, lang, live)
      setAnswers((prev) => ({ ...prev, [lang]: answer }))
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setWriting(null)
    }
  }

  const shown = language && !writing ? answers[language] : undefined
  const tone = result.skip ? 'skip' : result.verdict

  return (
    <section className={`explain explain--${tone}`} aria-live="polite">
      <div className="explain-head">
        <h3>In plain words</h3>
        <div className="seg" role="group" aria-label="Explanation language">
          {LANGUAGES.map((l) => (
            <button
              key={l.id}
              type="button"
              lang={l.id}
              aria-pressed={language === l.id}
              disabled={writing !== null}
              onClick={() => ask(l.id)}
            >
              {l.label}
            </button>
          ))}
        </div>
      </div>

      {language === null && (
        <p className="explain-hint">
          Gemma writes a short explanation on AMD Token Factory, and the note under it names the model that answered.
          Every number in it is checked against the pricing engine before you see it. For the recorded run, the
          explanation Gemma wrote for this exact Verdict appears at once.
        </p>
      )}
      {writing && <p className="explain-wait">Gemma is writing{writing === 'th' ? ' in Thai' : ''}…</p>}
      {error && <p className="checks">{error}</p>}
      {shown && (
        <>
          <p className="explain-text" lang={shown.language}>
            {shown.text}
          </p>
          <Provenance answer={shown} onLive={() => ask(shown.language, true)} />
        </>
      )}
    </section>
  )
}

function Provenance({ answer: a, onLive }: { answer: Explanation; onLive: () => void }) {
  const where = a.route === 'mi300x' ? 'our AMD Instinct MI300X' : 'AMD Token Factory'
  const drafts = a.rejected.filter((d) => d.text !== null)
  const written = a.written_at
    ? new Date(a.written_at).toLocaleDateString('en-GB', {
        day: 'numeric',
        month: 'short',
        year: 'numeric',
        timeZone: 'Asia/Bangkok',
      })
    : null
  return (
    <div className="explain-meta">
      {a.recorded ? (
        <p>
          <span className="explain-ok" aria-hidden>
            ✓
          </span>{' '}
          Recorded{written && ` ${written}`}: written by {a.model} on {where} for this exact Verdict. Every number
          matches the pricing engine.{' '}
          <button type="button" className="text-btn" onClick={onLive}>
            Ask Gemma again (live)
          </button>
        </p>
      ) : a.source === 'model' ? (
        <p>
          <span className="explain-ok" aria-hidden>
            ✓
          </span>{' '}
          Written by {a.model} on {where}. Every number matches the pricing engine.
        </p>
      ) : (
        <p>
          Numbers-only summary:{' '}
          {drafts.length > 0 ? "the model's drafts cited numbers the engine never produced." : 'the model did not answer.'}
        </p>
      )}
      {drafts.map((d, i) => (
        <p key={i}>
          Rejected draft: it cited{' '}
          {d.unsupported.map((n, j) => (
            <span key={j}>
              {j > 0 && ', '}
              <del>{n}</del>
            </span>
          ))}
          , which the engine never produced.
        </p>
      ))}
    </div>
  )
}
