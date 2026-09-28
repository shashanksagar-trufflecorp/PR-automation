#!/usr/bin/env python3
"""
claude_pr_review.py — POC: Claude-powered PR reviewer.

Flow:
  1. Read PR metadata + diff from the GitHub API.
  2. Load predefined coding/documentation rules from a local file.
  3. Load the User Story / Technical Design (from PR description sections,
     falling back to local doc files for the POC demo).
  4. Ask Claude to review the diff against the rules + story/design.
  5. Post Claude's review as a comment on the PR.

This is a POC: it only posts a comment. It never approves, requests changes,
or merges. A human reviewer makes the final call.
"""

import json
import os
import re
import sys
import textwrap

import requests
from anthropic import Anthropic

GITHUB_API = "https://api.github.com"

# ---- Config (env vars, set by the GitHub Actions workflow) ----------------
GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
GITHUB_REPOSITORY = os.environ["GITHUB_REPOSITORY"]  # "owner/repo"
EVENT_PATH = os.environ["GITHUB_EVENT_PATH"]
CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-5")
RULES_PATH = os.environ.get("RULES_PATH", "rules/coding_rules.md")
FALLBACK_USER_STORY_PATH = os.environ.get(
    "FALLBACK_USER_STORY_PATH", "docs/user_story_example.md"
)
FALLBACK_TECH_DESIGN_PATH = os.environ.get(
    "FALLBACK_TECH_DESIGN_PATH", "docs/technical_design_example.md"
)
MAX_DIFF_CHARS = int(os.environ.get("MAX_DIFF_CHARS", "60000"))

OWNER, REPO = GITHUB_REPOSITORY.split("/")

session = requests.Session()
session.headers.update(
    {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
)


def load_event():
    with open(EVENT_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def get_pr_files(pr_number):
    """Fetch changed files + patches for the PR (paginated)."""
    files = []
    page = 1
    while True:
        resp = session.get(
            f"{GITHUB_API}/repos/{OWNER}/{REPO}/pulls/{pr_number}/files",
            params={"per_page": 100, "page": page},
        )
        resp.raise_for_status()
        batch = resp.json()
        if not batch:
            break
        files.extend(batch)
        page += 1
    return files


def build_diff_text(files):
    """Concatenate filename + patch into one text blob, capped in size."""
    parts = []
    for f in files:
        patch = f.get("patch")
        if not patch:
            # Binary file, or too large a patch for GitHub to return inline.
            parts.append(f"### {f['filename']} ({f['status']})\n[no inline diff available]")
            continue
        parts.append(f"### {f['filename']} ({f['status']})\n```diff\n{patch}\n```")
    text = "\n\n".join(parts)
    if len(text) > MAX_DIFF_CHARS:
        text = text[:MAX_DIFF_CHARS] + "\n\n...[diff truncated for POC token limits]..."
    return text


def extract_section(body, heading):
    """
    Pull a "## User Story" / "## Technical Design" style section out of the
    PR description, if the author included one. Case-insensitive, stops at
    the next '## ' heading.
    """
    if not body:
        return None
    pattern = rf"##\s*{re.escape(heading)}\s*\n(.*?)(?=\n##\s|\Z)"
    match = re.search(pattern, body, re.IGNORECASE | re.DOTALL)
    if match:
        return match.group(1).strip()
    return None


def read_local_file(path):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return None


def get_user_story_and_design(pr_body):
    """
    POC resolution order:
      1. '## User Story' / '## Technical Design' sections in the PR body.
      2. Fallback local demo files (so the POC works without extra setup).
    In a later phase this would instead call a Jira/Confluence connector.
    """
    user_story = extract_section(pr_body, "User Story") or read_local_file(
        FALLBACK_USER_STORY_PATH
    )
    tech_design = extract_section(pr_body, "Technical Design") or read_local_file(
        FALLBACK_TECH_DESIGN_PATH
    )
    return (
        user_story or "[No User Story provided]",
        tech_design or "[No Technical Design provided]",
    )


def build_prompt(diff_text, rules_text, user_story, tech_design, pr_title, pr_body):
    return textwrap.dedent(f"""
    You are a code reviewer for Truffle Consulting. Review the pull request
    diff below strictly against:
      (a) the predefined coding & documentation rules, and
      (b) whether the change actually implements the linked User Story and
          Technical Design.

    Do not approve, reject, or claim any authority to merge — a human
    reviewer makes the final decision. Your job is only to identify issues
    and summarize compliance.

    Output format (markdown):
    ## Automated Review (Claude POC — not a final decision)
    **Summary:** 2-4 sentences on what this PR does and your overall impression.

    ### Rule Compliance
    A table: Rule | Status (Pass/Violation/N-A) | Notes. Use severity labels
    (Blocker/Major/Minor/Info) from the rules doc for violations.

    ### User Story Alignment
    Does the diff satisfy the acceptance criteria? Call out anything missing
    or extra.

    ### Technical Design Alignment
    Does the implementation match the described approach? Call out any
    deviations.

    ### Overall
    One line: "Looks aligned", "Needs changes", or "Needs human judgment —
    see notes", plus why. Explicitly state this is advisory only.

    ---
    PR TITLE: {pr_title}

    PR DESCRIPTION:
    {pr_body or "[none]"}

    RULES DOCUMENT:
    {rules_text}

    USER STORY:
    {user_story}

    TECHNICAL DESIGN:
    {tech_design}

    CODE DIFF:
    {diff_text}
    """).strip()


def call_claude(prompt):
    client = Anthropic(api_key=ANTHROPIC_API_KEY)
    resp = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=3000,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(block.text for block in resp.content if block.type == "text")


def post_comment(pr_number, body):
    resp = session.post(
        f"{GITHUB_API}/repos/{OWNER}/{REPO}/issues/{pr_number}/comments",
        json={"body": body},
    )
    resp.raise_for_status()
    return resp.json()


def main():
    event = load_event()
    pr = event.get("pull_request")
    if not pr:
        print("No pull_request in event payload; exiting.", file=sys.stderr)
        sys.exit(1)

    pr_number = pr["number"]
    pr_title = pr["title"]
    pr_body = pr.get("body") or ""

    print(f"Reviewing PR #{pr_number}: {pr_title}")

    files = get_pr_files(pr_number)
    diff_text = build_diff_text(files)

    rules_text = read_local_file(RULES_PATH) or "[No rules file found at RULES_PATH]"
    user_story, tech_design = get_user_story_and_design(pr_body)

    prompt = build_prompt(diff_text, rules_text, user_story, tech_design, pr_title, pr_body)
    review = call_claude(prompt)

    footer = (
        "\n\n---\n*Posted automatically by the Claude PR Review POC. "
        "This is advisory only — no approval, rejection, or merge action was taken.*"
    )
    post_comment(pr_number, review + footer)
    print("Review posted.")


if __name__ == "__main__":
    main()
