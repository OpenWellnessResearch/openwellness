# Architecture Decision Records

This directory holds the architecture decisions that the Postgres schema, the sync layer and the API are built on. Each record is short, covers one decision and says why it was made, so a contributor who was not in the room can still follow it.

## Format

Short MADR, about one page per file:

- Line 1 is `# NNNN. Title`.
- A bullet block follows: `- Status: Accepted` (or `Proposed`), `- Date: YYYY-MM-DD`, `- Decisions: D-NN, ...` (decision IDs from the phase 1 context).
- Then the sections `## Context`, `## Decision` and `## Consequences`, in that order.
- The index below lists each ADR exactly once, with a relative link `[NNNN](NNNN-slug.md)`.

## Adding an ADR

1. Take the next free number. Never renumber an existing ADR.
2. To change a decision, write a new ADR that supersedes the old one and set the old one's status to `Superseded by NNNN`. Do not edit an accepted decision in place.
3. Add one row to the index.

## Index

| ADR | Title | Status |
| --- | ----- | ------ |
| [0001](0001-primary-key-format.md) | Primary key format | Accepted |
