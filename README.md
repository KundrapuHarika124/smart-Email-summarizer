# smart-Email-summarizer

A modern web app that connects to your email and turns long, messy messages into short, smart summaries — highlighting what really matters.

---

## 🎯 Problem It Solves

We all get flooded with emails daily. Important deadlines, tasks, or attachments are often buried deep. This tool fixes that by giving you:

- Quick summaries
- Clear action points
- Deadlines spotted automatically
- Easy access to links and attachments

---

## ✨ Key Features

- **Smart Summarization**: Uses a DistilBART model to give clean, natural summaries.
- **Crucial Points**: Extracts rules, tasks, and questions from text.
- **Deadline Detection**: Picks up any date mention — even fuzzy ones like "next week." (dateparser + spaCy)
- **Link & File Insight**: Lists all links and attachments (real MIME attachments are parsed and provided as downloads).
- **Newsletter Mode**: Detects structured emails (like Devpost) and preserves the original layout.
- **Sleek UI**: Built with a dark mode theme for a chill, modern feel using Streamlit.

---

## ⚙️ Tech Stack

- **UI**: Streamlit
- **Summarization**: HuggingFace Transformers (sshleifer/distilbart-cnn-12-6)
- **NLP**: spaCy + dateparser
- **Email**: IMAP (imaplib)
- **Runtime**: Python 3.11 (runtime.txt)

---

## Project layout

```
README.md                Project overview, run/deploy instructions
app.py                   Streamlit application (UI, session state, orchestration)
nlp_utils.py             Model loading, text cleaning, summarization, NER, deadline & attachment extraction
email_utils.py           IMAP connection, fetching recent email headers and full email content (now returns structured payload with links & attachments)
requirements.txt         pip deps (streamlit, transformers, torch, spacy, dateparser, etc.)
packages.txt             system package list for deployment (cmake)
runtime.txt              Python runtime version (python-3.11)
```

---

## How to run locally

1. Clone the repository and install dependencies:

```bash
git clone https://github.com/KundrapuHarika124/smart-Email-summarizer.git
cd smart-Email-summarizer
pip install -r requirements.txt
```

2. (Optional) If the spaCy model isn't installed by the wheel in requirements, run:

```bash
python -m spacy download en_core_web_sm
```

3. Start the Streamlit app:

```bash
streamlit run app.py
```

4. Open your browser at http://localhost:8501 (Streamlit prints the exact URL when it starts).

5. Connect your email:
- For Gmail: create an App Password and enter it in the UI (or use Streamlit secrets — see below).
- For other IMAP providers: provide the IMAP server (usually `imap.<provider>.com`) and port (993 for SSL).

6. Select a message to see:
- Cleaned email text (for debugging)
- AI-generated summary
- Extracted action items and deadlines
- Links (🔗 Links section — extracted from the raw email payload before cleaning)
- Attachments (📎 Attachments section — real MIME attachments are parsed and available as download buttons)

---

## How the email payload is returned now (developer note)

`email_utils.fetch_email_content` returns a structured dict instead of a plain string. Example:

```python
{
  "text": "Decoded plain text body for NLP",
  "raw": "Decoded plain + HTML payloads before cleaning",
  "links": ["https://example.com", "http://docs.example.io"],
  "attachments": [
    {"filename": "report.pdf", "content": b"...bytes...", "content_type": "application/pdf"}
  ]
}
```

- `text` is fed to the summarizer and other NLP routines.
- `raw` is used for link extraction and optional debug display.
- `links` are extracted before any URL-stripping cleaning occurs.
- `attachments` are returned as in-memory bytes and surfaced in the UI with `st.download_button`.

---

## Deploying to Streamlit Cloud (get a public link)

1. Push your repo to GitHub (it already is). Make sure the repo has `requirements.txt`, `packages.txt`, and `runtime.txt`.

2. Go to https://share.streamlit.io and connect your GitHub account.

3. Create a new app and point it to this repository and branch.

4. Add secrets in the Streamlit Cloud dashboard (App settings -> Secrets) with keys that the app can read (example keys used in the project):

```
email = "your.email@example.com"
password = "YOUR_APP_PASSWORD"
imap_server = "imap.gmail.com"
imap_port = "993"
```

5. Deploy — Streamlit Cloud will install dependencies and provide a public URL like `https://share.streamlit.io/<user>/<repo>/<branch>/`.

Security note: prefer using App Passwords for Gmail or OAuth for production; do NOT commit secrets to the repository.

---

## Testing attachments & links locally (offline / sample email)

If you prefer not to connect a real mailbox while testing, you can simulate an email:

1. Save a raw .eml file into the repo (e.g., `test_data/sample.eml`).
2. Temporarily modify `email_utils.fetch_email_content` to read that file and return a payload in the same structured format (text/raw/links/attachments). The PR includes instructions to switch to a sample .eml for offline testing.

---

## Troubleshooting

- If Streamlit complains during `spacy.load("en_core_web_sm")`, run `python -m spacy download en_core_web_sm` or ensure the wheel in `requirements.txt` installed correctly.
- If IMAP login fails with Gmail, ensure you created an App Password and aren’t using regular account password for accounts with 2FA.
- For very large attachments, the app keeps attachments in memory — consider adding per-file size limits or streaming to temporary files / cloud storage in production.

---

## Next improvements (ideas)

- Replace IMAP password entry with OAuth2 (Gmail API) for better security and user experience.
- Stream attachments to disk or cloud storage for large files and serve presigned download links.
- Improve key-point extraction using sentence embeddings (SBERT) and extractive ranking instead of heuristics.
- Add unit tests for email parsing, link extraction, and attachment handling.

---

## License & Notes

This repo is an educational/demo project. Review any third-party model licenses (HuggingFace models) before commercial use.

> Don’t just read emails. Understand them instantly.
