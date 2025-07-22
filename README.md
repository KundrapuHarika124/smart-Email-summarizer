# smart-Email-summarizer

A modern web app that connects to your email and turns long, messy messages into short, smart summaries — highlighting what really matters.

---

## 🎯 Problem It Solves

We all get flooded with emails daily. Important deadlines, tasks, or attachments are often buried deep. This tool fixes that by giving you:

-   Quick summaries
-   Clear action points
-   Deadlines spotted automatically
-   Easy access to links and attachments

---

## ✨ Key Features

-   **Smart Summarization**: Uses BART model to give clean, natural summaries.
-   **Crucial Points**: Extracts rules, tasks, and questions from text.
-   **Deadline Detection**: Picks up any date mention — even fuzzy ones like "next week."
-   **Link & File Insight**: Lists all links and attachments with their purpose.
-   **Newsletter Mode**: Detects structured emails (like Devpost) and preserves the original layout.
-   **Sleek UI**: Built with a dark mode theme for a chill, modern feel.

---

## ⚙️ Tech Stack

-   **UI**: Streamlit
-   **Summarization**: HuggingFace Transformers
-   **NLP Magic**: spaCy + dateparser
-   **Email**: IMAP (imaplib)

---

## 🚀 Get Started

1.  Clone the repository:
    ```bash
    git clone [https://github.com/your-username/smart-email-summarizer.git](https://github.com/your-username/smart-email-summarizer.git)
    cd smart-email-summarizer
    ```
2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
3.  Run the app:
    ```bash
    streamlit run app.py
    ```
    *Use a Gmail App Password for login.*

---

## ☁️ Deploy in 1 Click

Host on Streamlit Cloud with these files in your repo:

1.  `requirements.txt`
2.  `packages.txt` (for cmake)
3.  `runtime.txt` (for python version)
4.  `.streamlit/secrets.toml` with your email password (safe!)

> "Don’t just read emails. Understand them instantly."

</markdown>
