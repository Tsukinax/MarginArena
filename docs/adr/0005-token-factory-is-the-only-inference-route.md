# Token Factory is our only inference route; the MI300X droplet is optional

Supersedes [ADR 0002](0002-two-inference-routes.md).

ADR 0002 made our own vLLM endpoint on an AMD Developer Cloud MI300X the main route, with AMD Token Factory as the fallback. The organisers have since said what counts as AMD for ACT III:

- lablab, in Discord on 13 Oct: ACT III "is hosted on notebooks.amd.com/tokenfactory", with no billing or card needed, and developers don't need the $100 credit, "Just the api from the tokenfactory".
- An AMD mentor, in Discord on 14 Oct: using the Token Factory API counts as a meaningful AMD component, and Gemma through Token Factory counts for the Google prize with no Developer Cloud GPU credits.

The $100 credit needs days of approval, and the user chose not to request it (Q57). So the Arena, the explainer and the Evolus agent all run on Token Factory's Gemma-4-31B-IT.

## Considered options

- **Keep a GPU session, paid by card (about $5 for two hours):** measured MI300X throughput and the Evolus track's strict wording, at the cost of a card on file and 2–3 hours of setup during the build.
- **Token Factory only (chosen):** free, already working, and what the organisers point to.

## Consequences

- The code keeps both routes: `llm.py` uses `mi300x` only when `VLLM_BASE_URL` is set. The submission runs on `token-factory`. `infra/droplet/` stays as an optional path that was never run, so it is never cited as evidence.
- AMD evidence is what Token Factory measurably did: recorded runs and their telemetry in `evidence/`. We make no claim about our own GPU, batching throughput or MI300X benchmarks.
- The live Arena stays small (Token Factory allows 20 requests a minute per account). Larger runs are recorded on Token Factory and labelled, in place of ADR 0004's recorded MI300X run.
- Token Factory still receives sample data only.
- The Evolus track's wording on lablab asks for the main agent on our own vLLM endpoint on AMD Developer Cloud. The AMD mentor answered that exact question in Discord on 14 Oct (07:13 ICT): Token Factory is the AMD-hosted vLLM endpoint given to participants and "perfectly satisfies this requirement". So the Evolus agent runs on Token Factory too.
