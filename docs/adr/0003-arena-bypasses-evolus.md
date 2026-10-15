# The Arena calls vLLM directly; Evolus carries out the Verdict

Updated 15 Oct 2026: since [ADR 0005](0005-token-factory-is-the-only-inference-route.md) the Arena calls AMD Token
Factory, not our own MI300X, and a live run makes about 20 calls, not 430. The split stands: each Arena call is a short
JSON proposal the engine scores at once, and an Evolus agent in between would add a hop and use the workspace's 60
requests a minute without changing any result. The figures below are the original reasoning.

We are in the Evolus track, so it would be natural to route every agent call through Evolus agents. An Evolus workspace, however, allows only 60 API requests per minute, and a full Arena run makes about 430 LLM calls in under a minute. That burst is exactly the MI300X batching we want to show. So the Arena's Strategist and Rival calls go straight to our own vLLM endpoint.

Evolus does the part that is a business process:
- The "Campaign Desk" main agent runs on the same vLLM endpoint. It reads the Campaign Invitation through a document extractor, checks rules in a knowledge library, explains the Verdict and answers the Seller.
- After the Seller confirms, a workflow carries out the Verdict.

## Consequences

- Evolus workspace stats show only the Campaign Desk and workflow calls, not the Arena's volume. The README and video must explain this split, so the Evolus judges don't read it as shallow use.
