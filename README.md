# EscalAI — Consumer Escalation Agent

A LangGraph-based case manager for consumer complaints. It walks a complaint up India's real escalation ladder, drafts each letter, tracks the reply deadline, reacts to what the company says back, and notifies you on your phone when a case moves up. It is exposed as a self-hosted MCP server (Streamable HTTP) with a web-based voice-style simulator standing in for an Alexa+ skill.

**It only drafts and tracks. It never sends anything on your behalf, and it is not legal advice.**

## Quick start

```bash
git clone https://github.com/shrutijagadale0725-rgb/EscalationAI.git
cd EscalationAI
python -m venv .venv
.venv\Scripts\activate        # Windows; use `source .venv/bin/activate` on Mac/Linux
pip install -r requirements.txt
python -m escalation_agent.mcp_server
```

Open **http://127.0.0.1:8000**. No API key is needed. Groq and notifications are optional extras, and the app is fully functional on its deterministic fallback without them.

Run `python -m escalation_agent.mcp_server` from the folder that contains the `escalation_agent` package.

**A 3-minute tour**

1. Click *New complaint* and describe a problem, e.g. "My earbuds from Amazon arrived broken, order OD-12345, Rs 2499". The form pre-fills from your text.
2. Review the drafted letter and tell the agent "I sent it". The reply window starts.
3. Type "it's been 6 days" or a date like "it's 26th nov" and watch it track the deadline, then escalate to the next stage with a new letter.
4. Try a company reply: "they rejected it, out of warranty" (escalates at once), "they offered a 50% refund" (asks you to accept or escalate), or "they approved my refund" (resolves).
5. Turn on *Read aloud* and use the mic button for voice in and out.

## What it does

Walks a complaint through a four-stage escalation ladder:

1. **Seller support** (7-day reply window): a direct complaint letter
2. **The platform's grievance officer** (30 days): required acknowledgment and redress under the Consumer Protection (E-Commerce) Rules, 2020
3. **The National Consumer Helpline** (45 days): 1800-11-4000 / consumerhelpline.gov.in
4. **The Consumer Commission**: a formal filing at e-Jagriti (e-jagriti.gov.in), tiered by claim value (District / State / National Commission). The agent pauses here and asks whether filing is worth it for the amount.

At each stage it drafts a letter, tracks the real reply-window deadline, and pauses for you to confirm you've sent it. If the window passes with no reply, or the company rejects the complaint, it escalates. You can stop a case at any point, or reopen a stopped case to pick up from where you left it, including one stopped at the filing decision.

Every letter is labelled as AI-drafted (and whether you edited it) so you review it before sending.

## When the company replies

Tell the agent what the company said and it reacts to what they meant:

| Their reply | What the case does |
|---|---|
| **Accepted** (agrees to refund or replace) | Marked resolved |
| **Rejected** | Escalates immediately, without waiting out the window |
| **Partial offer** (part refund, voucher, discount) | Keeps waiting and asks you to say "resolved" to accept or "escalate" to move on |
| **Stalling** ("looking into it") | Noted in the history. The clock keeps running. |
| **Unclear** | Saved in the history, no action |

Classification uses Groq when a key is set, and accepts the model's answer only if it is one of those five labels. Otherwise (no key, an error, or an invented label) it falls back to a deterministic regex classifier.

## Notifications

When a case escalates, EscalAI tells you three ways: an in-app banner, a push notification to your phone via [ntfy](https://ntfy.sh), and optionally an email. All of it is optional, and a failed notification never breaks a case.

Create a `.env` file next to the `escalation_agent` folder (it is git-ignored; never commit it):

```
NTFY_TOPIC=pick-a-long-random-topic-name
SMTP_USER=you@gmail.com
SMTP_PASSWORD=your-16-character-gmail-app-password
NOTIFY_EMAIL_TO=where-to-send@example.com
```

- **Phone:** install the ntfy app and subscribe to the same topic name. Anyone who knows the topic can read it, so make it long and unguessable.
- **Email:** uses Gmail SMTP with an [app password](https://myaccount.google.com/apppasswords), not your normal password. Skip the `SMTP_*` lines to turn email off.
- Only `NTFY_*`, `SMTP_*` and `NOTIFY_*` keys are read from `.env`. Restart the server after editing it.

## Why this architecture

Alexa+'s gated developer tools are not available to hackathon participants this cycle, so a self-hosted MCP server plus a web-based simulator is the stand-in. The "voice assistant" here is a browser page with mic input and speech output, talking to the same MCP tools an Alexa+ skill would call.

## How it understands you

Free text goes through `/api/understand`, which tries Groq (an LLM) first for natural-language routing and field extraction. It silently falls back to deterministic regex matching if there's no `GROQ_API_KEY` or the Groq call fails for any reason.

While a case is in the **waiting** stage, a second pass handles free-form check-ins: relative durations ("it's been 8 days"), calendar dates ("it's 23 nov", counted from the date the case was opened), and fact-grounded questions ("when will I hear back?"). The model gets a real callable action (`advance_days`) instead of generating free text, and any free-text answer is only accepted if every number in it matches a known fact about the case. Anything it can't safely answer falls back to "not sure, check back" rather than guessing.

Once a case is finished (resolved, stopped or ready to file), closing remarks like "thanks" or "ok" get a friendly reply and do not start a new complaint.

## Running with Groq (optional)

Groq is read from your real environment, not from `.env`:

```powershell
$env:GROQ_API_KEY="your-key-here"       # PowerShell
$env:GROQ_MODEL="openai/gpt-oss-120b"   # optional override
```

```bash
export GROQ_API_KEY="your-key-here"     # macOS / Linux
```

## MCP tools exposed

| Tool | Purpose |
|---|---|
| `start_case` | Open a new complaint case |
| `log_response` | Record events: answer, sent, seller_replied (classified automatically), resolved, escalate, file, stop |
| `get_next_step` | Current status and days left in the reply window |
| `draft_escalation` | Re-fetch the current letter/case file |
| `simulate_days` | **Demo only**: fast-forward the case clock |
| `reopen_case` | Resume a case you previously stopped |
| `delete_case` | Permanently delete a case, its letters and its history |
| `list_cases` | List past cases, most recent first |

## The simulator

- **Voice in and out**: a mic button for speech input, optional *Read aloud* with a selectable voice.
- **Pre-filled intake**: order number, amount and platform are pulled from what you type.
- **Case management**: every case is saved and resumable from the sidebar, with a delete button (with confirmation) that removes the case and its full LangGraph history.
- **Deadlines you can read**: each step shows its due date and days left, anchored to the date the case was opened.
- **Inline message editing** and a **copy** icon on every message.
- Resizable panes, official-channel links at each escalation stage, and a landing page explaining what the agent does and doesn't do with your data.

## Built with

Python, LangGraph (with SqliteSaver persistence), Starlette, the `mcp` Python SDK, Groq, ntfy, SQLite, and plain HTML/CSS/JavaScript.

## Testing and accuracy

Run from the folder that contains the `escalation_agent` package and `tests/`:

```bash
python -m pytest -v
```

All 64 tests pass. Use `python -m pytest` rather than bare `pytest` so the project folder is on the import path. They cover the full escalation ladder, real versus simulated clock behaviour, the MCP endpoint end to end, the HTTP API's security checks (origin and content-type), notifications (including that a failing notifier never breaks a case), company-reply handling, and regression tests for bugs found along the way. See [`FRICTION_LOG.md`](FRICTION_LOG.md) for what went wrong and how it was fixed.

Two small accuracy scripts, both hand-labelled:

```bash
python eval_accuracy.py    # field extraction: 22/22 complaints, 5/5 routing cases
python eval_replies.py     # company-reply classification: 24/24 on the regex classifier
```

These sets are small and were written by the author, so treat them as regression checks rather than real-world accuracy. Real replies will sometimes be misread. Add your own samples to the lists in the scripts to test further.

## Limitations

- Drafts letters only. It does not negotiate: on a partial offer it lets you accept or escalate, but does not write a counter-offer.
- You type or paste what the company said. It does not read email or screenshots.
- A case marked resolved cannot be reopened (only stopped cases can).
- Notifications fire when a case escalates, not as a deadline approaches.

## Roadmap

- **Deadline reminders** shortly before each reply window ends.
- **Counter-offer drafts** for partial offers, and reopening resolved cases.
- **More regions and rules** through `rules.yaml`.
- **Real Alexa+ device**: connect the same MCP tools to an Alexa+ Agent Skill once developer access is available.

## AI assistance

Built with help from Claude (Anthropic) for architecture design, debugging, code generation and documentation. Groq powers the optional runtime language understanding.

## Disclaimer

This tool drafts messages and tracks deadlines. It is not legal advice. Stage windows in `rules.yaml` are verified against public sources as of the dates noted there. Always confirm current rules and fees on the official sites (e-jagriti.gov.in, consumerhelpline.gov.in) before relying on a deadline or filing.

## License

MIT, see `LICENSE`.