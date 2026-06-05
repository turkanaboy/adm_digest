# Undergraduate Admissions Daily Digest

This repository generates a weekday admissions digest for Binghamton University admissions staff. It fetches configured higher education sources, scores items for undergraduate admissions relevance, summarizes the strongest matches, archives the digest as Markdown, and emails the team distribution list.

## What the digest includes

- Message of the Day: strategic, admissions-focused, and motivational.
- Affirmation of the Day: brief, plainspoken personal encouragement; uplifting but not admissions-specific, flowery, or spiritual.
- Dad Joke of the Day: intentionally light and not necessarily admissions-related.
- Binghamton Area Brief: a small section for positive SUNY, Binghamton University, and Binghamton-area items that may help admissions staff speak about place and context.
- Top Undergraduate Admissions Articles: up to the configured article count, using broader college/higher-ed articles as supplements when admissions-specific items run short.
- Resources: at most one useful hub, guide, journal, index, or reference page. Resource pages are separated from articles, do not count toward the article count, and do not include quotes.
- Disclaimer: each digest notes that summaries are AI-generated and that readers should consult the linked source for full context.

## Schedule

The GitHub Actions workflow runs Monday-Friday. Because GitHub cron schedules use UTC, it schedules both `0 11 * * 1-5` and `0 12 * * 1-5`, then uses a timezone gate so only the run that occurs at 7:00 AM `America/New_York` actually generates and sends the digest.

The workflow also supports manual runs through `workflow_dispatch`.

The workflow commits generated digest archives and duplicate-tracking updates back to the branch that ran the workflow. To avoid `fetch first` push failures when the remote branch receives new commits during a run, the checkout fetches full history, stale/manual duplicate runs are cancelled with a workflow concurrency group, the branch is reset to the latest remote state before generation, and the commit step saves the generated digest artifacts, resets to the latest remote branch, reapplies the artifacts, and commits immediately before each push attempt. If the remote branch changes again before the push completes, the workflow retries that reset/reapply/commit/push sequence up to five times with longer 15-second-multiplier backoff before failing.

## What I need from you next

Before turning this on for the team, provide or configure:

1. `OPENAI_API_KEY`: add a valid OpenAI API key as a GitHub Actions repository secret. If an API key was ever pasted into chat, email, or a ticket, revoke it and create a fresh key before storing it in GitHub.
2. Email delivery details: `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `EMAIL_FROM`, and `EMAIL_TO`.
3. Pilot recipient list: start with `EMAIL_TO=tlowell@binghamton.edu`; later this can become the full admissions distribution list.
4. Preferred sender address: try `EMAIL_FROM=tlowell@binghamton.edu` only if Binghamton IT allows SMTP/app-password sending from that account. If institutional SMTP blocks that, use a dedicated shared mailbox or a temporary personal sender such as Gmail until a Binghamton-approved mailbox is available.
5. Slack preference: Slack is on hold for now. Leave `slack.enabled: false` and do not set `SLACK_WEBHOOK_URL` until you want a Slack copy.
6. Chronicle approach: keep Chronicle metadata/link-only for now. Do not automate SSO login or scrape paywalled Chronicle text.
7. Source tuning: send any publications, local outlets, or terms you want added or excluded after you see the first few digests.

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

## Step-by-step email setup

### Option A: Binghamton / Microsoft 365 SMTP, preferred if IT allows it

1. Ask Binghamton IT whether authenticated SMTP is allowed for your account or for a shared mailbox. Many Microsoft 365 tenants disable SMTP AUTH by default.
2. If IT approves SMTP AUTH, ask for the exact SMTP settings. Common Microsoft 365 values are:
   - `SMTP_HOST=smtp.office365.com`
   - `SMTP_PORT=587`
   - `SMTP_USERNAME=tlowell@binghamton.edu`
   - `EMAIL_FROM=tlowell@binghamton.edu`
3. Confirm what should be used for `SMTP_PASSWORD`. This may be your account password, but in many environments it must be an app password, service-account password, or shared-mailbox credential. Do not commit this value to the repository.
4. In GitHub, open the repository, then go to **Settings → Secrets and variables → Actions → New repository secret**.
5. Add these repository secrets one at a time:
   - `OPENAI_API_KEY`: fresh OpenAI key, not one that has been pasted publicly.
   - `SMTP_HOST`: value from IT, commonly `smtp.office365.com`.
   - `SMTP_PORT`: commonly `587`.
   - `SMTP_USERNAME`: commonly `tlowell@binghamton.edu`.
   - `SMTP_PASSWORD`: approved SMTP/app/service password.
   - `EMAIL_FROM`: commonly `tlowell@binghamton.edu`.
   - `EMAIL_TO`: start with `tlowell@binghamton.edu`.
6. Run the workflow manually from **Actions → Daily Admissions Digest → Run workflow**.
7. If Microsoft blocks the send, ask IT for the SMTP AUTH/send-as policy error and either enable a shared mailbox/service account or use Option B temporarily.

### Option B: Temporary Gmail sender

Use this only if Binghamton SMTP is blocked while you wait for an approved institutional sending path.

1. Use or create a Gmail account that is acceptable as a temporary sender.
2. Turn on 2-Step Verification for that Google account.
3. Create a Google app password for Mail.
4. Add these GitHub Actions secrets:
   - `SMTP_HOST=smtp.gmail.com`
   - `SMTP_PORT=587`
   - `SMTP_USERNAME=tylermlowell@gmail.com`
   - `SMTP_PASSWORD=<the Google app password>`
   - `EMAIL_FROM=tylermlowell@gmail.com`
   - `EMAIL_TO=tlowell@binghamton.edu`
5. Run the workflow manually and confirm the digest arrives. Later, replace these secrets with a Binghamton-approved sender.

### Notes

- `EMAIL_TO` supports comma-separated recipients, so the pilot can become `person1@binghamton.edu,person2@binghamton.edu` or a single distribution-list address later.
- Do not store API keys, SMTP passwords, or app passwords in files, commits, Slack messages, or screenshots.
- GitHub Actions secrets are referenced by the workflow but are not printed by this app.

## HTML email design

Email delivery sends a multipart message: a plain-text Markdown version for compatibility and a styled HTML version for modern email clients. The HTML version is intentionally designed like a digest letter, with a Binghamton-inspired deep-green header, gold accenting, card-based sections, styled quotes, and prominent article buttons.

Images are supported conservatively:

- If an RSS feed exposes a public article thumbnail, the HTML email can display it above that article card.
- `email.header_image_url` in `config/settings.yaml` can point to an externally hosted header image if you later want a hero photo. Leave it blank to use the branded color header only.
- Images must be publicly reachable by recipients' email clients; the app does not attach or scrape private images.
- Many email clients block remote images by default, so every article remains readable without images.

The color treatment is close to Binghamton branding but intentionally avoids embedding official logos or protected assets until you have an approved image URL or brand-approved asset workflow.

## Chronicle access recommendation

The Chronicle of Higher Education is configured as an institutional-subscription source. Because Binghamton access is through institutional SSO, the first version intentionally does **not** attempt to automate login or scrape paywalled pages. It should use public metadata, links, short available excerpts, or manually supplied links unless the institution confirms that automated authenticated access is permitted.

This protects the subscription, avoids brittle SSO automation, and reduces copyright risk.

## Full text vs. metadata/excerpts

The default mode is `public_full_text`: the digest tries to fetch visible public article text for selected items so summaries and short quotes have enough context, then falls back to RSS metadata/excerpts when the page is paywalled, subscription-only, inaccessible, or too thin to be useful.

Using full public article text can improve summary fidelity when the system has lawful access to the content, but it has tradeoffs:

- Cost: OpenAI API cost is driven largely by tokens. Full article text can be many times more expensive than titles, metadata, and excerpts, especially across multiple articles each weekday.
- Copyright and subscription terms: sending full paywalled article text to a third-party model may require institutional approval.
- Accuracy: metadata-only summaries can miss nuance. The current middle ground is to use visible public text only when available, keep subscription content metadata-only, clearly link to the source, and include a disclaimer.

For this digest, public full text is used only for visible, non-subscription pages and only for the selected items. Institutional-subscription sources remain metadata/link-only unless the institution explicitly approves authenticated automated access.

A practical cost estimate using `gpt-4.1-mini` pricing is still small for this use case, but the difference is real. If the digest sends roughly 8 article records with metadata/excerpts, the request might be around 8,000-15,000 input tokens plus 2,000-4,000 output tokens. If it sends 8 full public articles, it could easily be 40,000-80,000 input tokens plus similar output. At `gpt-4.1-mini` rates, that is often the difference between fractions of a cent and a few cents per digest, but full text also raises access and copyright questions.

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
- Edit `config/settings.yaml` to change tone settings, maximum article count, one-resource cap, archive paths, Slack settings, or model.
- Archived digests are written to `digests/YYYY-MM-DD.md`.
- Duplicate tracking is stored in `data/seen_articles.json`.


## Positive Binghamton-area coverage

The local area brief is intentionally biased toward positive, recruitment-useful coverage. Local sources such as Pressconnects, WBNG, WSKG, Broome County, Visit Binghamton, SUNY, and Binghamton University are collected as candidate inputs, then filtered for upbeat signals such as arts, events, food, downtown development, community, parks, outdoors, awards, and regional momentum. Items with strong negative signals such as crime, crashes, deaths, arrests, scandals, or lawsuits are filtered out of the local brief unless a future configuration explicitly changes that behavior.
