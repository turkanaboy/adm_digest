# Undergraduate Admissions Daily Digest

This repository generates a weekday admissions digest for Binghamton University admissions staff. It fetches configured higher education sources, scores items for undergraduate admissions relevance, summarizes the strongest matches, archives the digest as Markdown, and emails the team distribution list.

## What the digest includes

- Message of the Day: strategic, admissions-focused, and motivational.
- Affirmation of the Day: powerful, uplifting, and written for admissions counselors, readers, and operations staff doing daily student-facing work.
- Dad Joke of the Day: intentionally light and not necessarily admissions-related.
- Binghamton Area Brief: a small section for SUNY, Binghamton University, and Binghamton-area items that may help admissions staff speak about place and context.
- Top Undergraduate Admissions Articles: up to 8 relevant articles with standard-length summaries, a short important quote when available, and source links.
- Disclaimer: each digest notes that summaries are AI-generated and that readers should consult the linked source for full context.

## Schedule

The GitHub Actions workflow runs Monday-Friday. Because GitHub cron schedules use UTC, it schedules both `0 11 * * 1-5` and `0 12 * * 1-5`, then uses a timezone gate so only the run that occurs at 7:00 AM `America/New_York` actually generates and sends the digest.

The workflow also supports manual runs through `workflow_dispatch`.

## Required GitHub Actions secrets

Set these repository secrets before enabling production delivery:

- `OPENAI_API_KEY`: OpenAI API key for summarization and daily generated sections.
- `SMTP_HOST`: SMTP server hostname.
- `SMTP_PORT`: SMTP port, usually `587`.
- `SMTP_USERNAME`: SMTP username.
- `SMTP_PASSWORD`: SMTP password or app password.
- `EMAIL_FROM`: Sender address.
- `EMAIL_TO`: Comma-separated team distribution list recipients.

Optional Slack posting:

- `SLACK_WEBHOOK_URL`: Incoming webhook URL for a Slack channel.

Slack incoming webhooks can work on free Slack workspaces if the workspace allows the app/webhook installation. The digest currently keeps Slack disabled in `config/settings.yaml`; set `slack.enabled` to `true` or run with `--post-slack` once a webhook is available.

## Chronicle access recommendation

The Chronicle of Higher Education is configured as an institutional-subscription source. Because Binghamton access is through institutional SSO, the first version intentionally does **not** attempt to automate login or scrape paywalled pages. It should use public metadata, links, short available excerpts, or manually supplied links unless the institution confirms that automated authenticated access is permitted.

This protects the subscription, avoids brittle SSO automation, and reduces copyright risk.

## Full text vs. metadata/excerpts

The default recommendation is `metadata_and_excerpts`.

Using full article text can improve summary fidelity when the system has lawful access to the content, but it has tradeoffs:

- Cost: OpenAI API cost is driven largely by tokens. Full article text can be many times more expensive than titles, metadata, and excerpts, especially across multiple articles each weekday.
- Copyright and subscription terms: sending full paywalled article text to a third-party model may require institutional approval.
- Accuracy: metadata-only summaries can miss nuance. The safer middle ground is to summarize from titles, public summaries, RSS descriptions, and short excerpts, while clearly linking to the source and including a disclaimer.

For this digest, metadata and excerpts are usually enough to identify relevance, provide an executive awareness summary, and direct staff to read the full source where needed. If later approved, selected public full-text sources can be enabled source-by-source.

## Local usage

Install dependencies:

```bash
python -m pip install -e .
```

Generate a local fallback digest without OpenAI or email:

```bash
python -m adm_digest.main --dry-run --no-openai
```

Generate and email with OpenAI:

```bash
OPENAI_API_KEY=... SMTP_HOST=... SMTP_USERNAME=... SMTP_PASSWORD=... EMAIL_FROM=... EMAIL_TO=... python -m adm_digest.main --send-email
```

## Configuration

- Edit `config/sources.yaml` to add or remove publications.
- Edit `config/settings.yaml` to change tone settings, maximum article count, archive paths, Slack settings, or model.
- Archived digests are written to `digests/YYYY-MM-DD.md`.
- Duplicate tracking is stored in `data/seen_articles.json`.
