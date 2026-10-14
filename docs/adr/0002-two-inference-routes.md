# Two inference routes: our own MI300X for the Arena, Token Factory as the always-on fallback

Superseded by [ADR 0005](0005-token-factory-is-the-only-inference-route.md) on 15 Oct 2026: the submission runs on Token Factory only.

The Arena and the Evolus main agent run on our own vLLM endpoint on an AMD Developer Cloud MI300X, serving Gemma-4-31B-IT, behind Caddy HTTPS on an sslip.io name made from the droplet's IP. That is where we get high-concurrency batching, and the Evolus track requires its main agent to run there. The droplet costs $2.59/hr, and the $100 credit buys about 38 hours, so it is switched on only for development sessions, recording and announced judging windows.

The public app therefore falls back to AMD Token Factory's shared Gemma-4-31B-IT whenever the droplet is off. That route is free and always on, but it is limited to 30 requests per minute and 8 concurrent. With it, the app keeps working and still runs on AMD; the Arena simply runs smaller.

## Considered options

- **Only Token Factory:** cannot show batching throughput, and does not meet the Evolus track's "own vLLM endpoint" rule.
- **Only the MI300X:** the demo dies when the credit runs out, and judges may test until 15 Nov.

## Consequences

- The app always shows which route served a run, so the AMD evidence stays honest.
- Arena size depends on the route.
