# Issue tracker: Local Markdown

Issues and specs for this repo live as markdown files in `.scratch/`. There is no GitHub remote yet.

## Conventions

- One effort per directory: `.scratch/<effort-slug>/`
- The spec is `.scratch/<effort-slug>/spec.md`
- Tickets are one file each at `.scratch/<effort-slug>/issues/<NN>-<slug>.md`, numbered from `01`
- A `Status:` line near the top of each issue file records its state
- Comments go at the bottom of the file under a `## Comments` heading

## Wayfinding operations

- **Map**: `.scratch/<effort>/map.md`, holding the Destination, Notes, Decisions so far, and fog.
- **Child ticket**: `.scratch/<effort>/issues/NN-<slug>.md`, with the question in the body.
  - A `Type:` line holds `research`, `prototype`, `grilling` or `task`.
  - A `Status:` line holds `open`, `claimed` or `resolved`.
- **Blocking**: a `Blocked by: NN, NN` line near the top. A ticket is unblocked once every ticket it lists is `resolved`.
- **Frontier**: the open, unblocked, unclaimed tickets; take the lowest number first.
- **Claim**: set `Status: claimed` before starting any work.
- **Resolve**: add the answer under `## Answer`, set `Status: resolved`, then add a one-line gist and link under Decisions so far in `map.md`.
