# Claude PR Review — POC

Automates the first half of the PR review loop: whenever a PR is opened or
updated, Claude reads the diff, checks it against a predefined rules
document, checks it against the linked User Story / Technical Design, and
posts a review comment. **A human still makes the approve/merge decision.**

```
PR Created/Updated
       ↓
GitHub Actions triggers workflow
       ↓
Script fetches PR diff via GitHub API
       ↓
Script loads rules/coding_rules.md
       ↓
Script loads User Story + Technical Design
   (from PR description sections, or fallback docs for the demo)
       ↓
Claude reviews diff vs. rules vs. story/design
       ↓
Script posts Claude's review as a PR comment
       ↓
Human reviewer makes the final decision
```

## What this proves (today's scope)

1. Claude can access/read a GitHub PR — `get_pr_files()` pulls the file list
   and diff via the GitHub REST API.
2. Claude can be given a rules document — `rules/coding_rules.md` is loaded
   fresh on every run and injected into the prompt verbatim.
3. Claude can compare the PR code against those rules — see the "Rule
   Compliance" table in the generated review.
4. Claude can review the implementation against a User Story / Technical
   Design — `get_user_story_and_design()` pulls these from the PR
   description (`## User Story` / `## Technical Design` sections) or from
   the fallback demo docs, and the prompt asks Claude to check alignment
   explicitly.
5. Claude can post findings back to the PR — `post_comment()` writes the
   review as an issue comment on the PR thread.

## Repo layout

```
.github/workflows/claude-pr-review.yml   GitHub Actions workflow (the trigger)
scripts/claude_pr_review.py              Core logic (diff → prompt → Claude → comment)
rules/coding_rules.md                    Predefined coding/documentation rules (sample set)
docs/user_story_example.md               Sample User Story (POC fallback)
docs/technical_design_example.md         Sample Technical Design (POC fallback)
.env.example                             Env vars/secrets reference (no real secrets)
```

## Setup

1. Copy this structure into the target repo (or point the workflow at
   wherever `rules/` and `docs/` live).
2. In **Settings → Secrets and variables → Actions**, add a repo secret:
   - `ANTHROPIC_API_KEY` — your Anthropic API key.
   - `GITHUB_TOKEN` is provided automatically by Actions; no setup needed,
     but confirm workflow permissions include `pull-requests: write`
     (already set in the workflow file).
3. Replace `rules/coding_rules.md` with Truffle's actual coding &
   documentation standards.
4. Decide how User Story / Technical Design get supplied per PR (see
   below) and update the fallback docs or PR template accordingly.

## Supplying the User Story / Technical Design

For the POC, the script looks for `## User Story` and `## Technical Design`
headings inside the PR description. Example PR description:

```
Implements password reset per ticket.

## User Story
As a customer, I want to reset my password via email...

## Technical Design
New endpoint POST /auth/reset-password/request...
```

If those headings aren't found, it falls back to the two example docs in
`docs/` so the demo works out of the box. **Phase 2 candidate:** replace the
fallback with a live pull from Jira/Confluence (Truffle already has
connector infrastructure for this) instead of relying on the PR author to
paste text.

## Running the demo

1. Merge/push this structure to a test repo with the workflow enabled.
2. Open a PR that touches a few files (and, ideally, violates a rule or two
   on purpose — e.g., a hardcoded secret, a missing docstring).
3. Watch the **Actions** tab — the "Claude PR Review (POC)" job should run.
4. Check the PR — a comment from `github-actions[bot]` appears with:
   - Summary
   - Rule compliance table with severities
   - User Story alignment notes
   - Technical Design alignment notes
   - An overall advisory line (never an approval/rejection)

## Explicit POC limitations (by design, for this phase)

- **No auto-approve/reject/merge.** The script only posts a comment.
  Adding a "request changes" review or a merge gate is explicitly
  out of scope until this phase is evaluated.
- **Single summary comment**, not inline/line-level PR comments.
- **Diff size capped** (`MAX_DIFF_CHARS`, default ~60k chars) to control
  token usage — very large PRs get a truncated diff with a note; a real
  rollout should chunk large diffs instead of truncating.
- **User Story/Tech Design sourcing is manual/text-based** — no Jira/
  Confluence integration yet.
- **One rules file, one language-agnostic rule set** — no per-directory or
  per-language rule variants yet.
- Uses `claude-sonnet-5` by default (configurable via `CLAUDE_MODEL`).

## Suggested next phase

- Pull User Story / Technical Design live from Jira/Confluence via
  connector instead of PR-description text.
- Line-level inline comments via the GitHub "review" API
  (`/pulls/{pr}/reviews` with `COMMENT`/`REQUEST_CHANGES` events) instead
  of a single issue comment — still human-approved, but more precise.
- Per-repo or per-directory rule sets.
- Evaluate (separately, with sign-off) whether Claude's verdict should ever
  gate merge — e.g., required status check on "Blocker" findings only.
