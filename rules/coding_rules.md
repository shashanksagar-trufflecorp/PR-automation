# Predefined Review Rules (POC Sample Set)

> Replace/extend this file with Truffle Consulting's actual coding & documentation
> standards. Claude reads this file verbatim on every PR review — nothing here is
> hardcoded in the script.

## 1. Coding Standards
- No hardcoded secrets, API keys, tokens, or credentials in source files.
- No commented-out dead code left in the diff.
- Functions/methods should be reasonably small and single-purpose; flag anything
  doing clearly unrelated things in one function.
- Error handling: no empty catch/except blocks that silently swallow errors.
- Naming: variables and functions use clear, descriptive names (no single-letter
  names outside of small loop counters).
- No new print/console.log debug statements left in committed code.

## 2. Documentation Standards
- Every new public function/class/method must have a docstring/comment describing
  purpose, parameters, and return value.
- Any new configuration option, env var, or public API must be reflected in the
  README or relevant docs in the same PR.
- Non-trivial logic (anything not immediately obvious from the code) must have an
  inline comment explaining the "why", not just the "what".

## 3. Testing
- New logic/business rules should be accompanied by at least one automated test.
- Modified functions with existing tests should not reduce test coverage for that
  file without justification in the PR description.

## 4. Security & Data Handling
- No PII, customer data, or confidential business data committed as sample/test
  data.
- Any new external call (API, DB, file system) should include basic input
  validation.

## 5. Severity Levels (for Claude's output)
- **Blocker** – violates rule 4 (security/secrets), or breaks working code.
- **Major** – violates rules 1–3 in a way that affects maintainability/correctness.
- **Minor** – style/naming/nit-level issues.
- **Info** – suggestions, not violations.
