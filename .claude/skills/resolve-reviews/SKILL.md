---
name: resolve-reviews
description: Fetch PR review comments, apply valid fixes, and reply with what changed.
compatibility: Requires git and gh.
---

# Resolve Reviews

## Steps

1. Resolve current PR with `gh pr view --json number,url`.
2. Fetch inline comments with `gh api repos/{owner}/{repo}/pulls/{number}/comments`.
3. Classify each comment as valid, invalid, or needs clarification.
4. Apply valid fixes only.
5. Run the smallest relevant checks.
6. Commit, push, and reply to the review comment with the commit hash.

Do not resolve threads or dismiss comments unless explicitly asked.
