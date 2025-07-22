import streamlit as st # Used for caching models with @st.cache_resource
from transformers import pipeline, AutoTokenizer, AutoModelForSeq2SeqLM
import re
import spacy
import dateparser # More robust for dates than datefinder
from datetime import datetime # Crucial for datetime.now()
import logging

# Configure logging for better debugging (visible in terminal running Streamlit)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Global NLP Model Loading (Cached for efficiency) ---
@st.cache_resource
def load_nlp_models():
    """Loads and caches NLP models to avoid reloading on every Streamlit rerun."""
    logging.info("Loading NLP models (this happens once)...")
    
    # For summarization: using a distilled BART model for good balance of quality and speed/memory
    # If memory permits (>= 8GB RAM, and you want higher quality, try "facebook/bart-large-cnn")
    summarizer_model_name = "sshleifer/distilbart-cnn-12-6" # Good for i3/8GB
    
    summarizer = pipeline("summarization", model=summarizer_model_name)

    # spaCy for robust NER (Named Entity Recognition) for dates and general text processing
    nlp_spacy = spacy.load("en_core_web_sm")

    logging.info("NLP models loaded.")
    return summarizer, nlp_spacy

# Load models once when the script starts. They will be cached by Streamlit.
# The `summarizer` and `nlp_spacy` objects become globally accessible within this module.
summarizer, nlp_spacy = load_nlp_models() 

# --- Core NLP Functions ---

def clean_email_text(text):
    """
    Cleans raw email content for better NLP processing.
    Removes HTML tags, URLs, excess whitespace, and common email footers/headers.
    """
    # 1. Remove HTML tags aggressively (Crucial for emails from web sources)
    # This pattern matches anything between < and >, including tags, comments, etc.
    text = re.sub(r'<[^>]+>', ' ', text) # Replace tags with a space to avoid merging words

    # 2. Remove specific email boilerplate and headers/footers commonly found in fetched raw emails
    # Removing common unsubscribe/footer patterns
    text = re.sub(r'To unsubscribe from this group.*|You received this message because.*', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'^\s*[\-_=]{3,}.*?Original Message.*$', '', text, flags=re.MULTILINE | re.DOTALL | re.IGNORECASE)
    text = re.sub(r'On\s+.*?wrote:.*?\n>.*', '', text, flags=re.DOTALL | re.IGNORECASE) # Reply headers
    text = re.sub(r'Start your own s k o o l.*', '', text, flags=re.DOTALL | re.IGNORECASE) # Specific footer from previous example
    text = re.sub(r'Change notification settings.*', '', text, flags=re.DOTALL | re.IGNORECASE) # Notification settings footer
    text = re.sub(r'AI Automation Agency Hub.*?\d+\s*new notification', '', text, flags=re.DOTALL | re.IGNORECASE) # Specific to your example
    text = re.sub(r'Since \d{1,2}:\d{2} (am|pm) \(Jul \d{1,2}, \d{4}\)', '', text, flags=re.IGNORECASE) # Date header like "Since 2:34 am (Jul 21, 2025)"
    text = re.sub(r'Here’s what you missed:', '', text, flags=re.IGNORECASE)
    text = re.sub(r'View Group', '', text, flags=re.IGNORECASE)
    text = re.sub(r'Are we sending you too many emails\?', '', text, flags=re.IGNORECASE)
    text = re.sub(r'We’re bundling up all your email notifications: Hourly', '', text, flags=re.IGNORECASE)
    text = re.sub(r'Change to:.*?(\d+\s*mins|\d+\s*hours|Daily|Weekly)', '', text, flags=re.IGNORECASE | re.DOTALL) # Notification options like "Change to: 5 mins"

    # 3. Remove URLs (aggressive removal, including those in parentheses or just raw)
    # This regex attempts to catch various forms of URLs, including those wrapped in ( )
    # It also targets common link placeholders like [LINK] or simply .com/.org/ etc.
    text = re.sub(r'\s*\(?\s*(https?://[^\s]+|www\.[^\s]+|\b\w+\.(com|org|net|io|co|ai)\/\S*\b)\s*\)?\s*', ' ', text, flags=re.IGNORECASE)
    text = re.sub(r'\[LINK\]', ' ', text, flags=re.IGNORECASE) # Remove specific [LINK] placeholders

    # 4. Remove image alt text, styles, and other artifacts that might remain after HTML removal
    text = re.sub(r'alt="" width="1" height="1" border="0" style="[^!]+!important;[^!]+!', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\b(?:CA|AA)\b\s*', '', text) # Remove "CA", "AA" followed by spaces/parentheses
    text = re.sub(r'\*+', '', text) # Remove any remaining asterisks (like from the old notification lines)
    text = re.sub(r'\s*\( ?\)\s*(\s*\( ?\)\s*)*', ' ', text) # Remove patterns like ( ) ( ) ( )

    # 5. Normalize whitespace: replace multiple spaces with single, reduce multiple newlines
    text = re.sub(r'\s+', ' ', text).strip() # Replace multiple spaces/tabs/newlines with single space
    text = re.sub(r'\n\s*\n', '\n\n', text) # Reduce multiple blank lines to max one

    return text

def get_summary(text):
    """Generates a concise summary of the cleaned text."""
    if not text.strip():
        return "No content to summarize."
    try:
        # Adjust max_length and min_length for desired summary length
        # These values will control the length of your summary output
        summary_output = summarizer(text, max_length=150, min_length=50, do_sample=False)
        return summary_output[0]['summary_text']
    except Exception as e:
        logging.error(f"Error during summarization: {e}")
        return "Could not generate summary."

def extract_deadlines(text):
    """
    Extracts and robustly parses deadlines from the text using dateparser and spaCy.
    Returns a list of formatted deadline strings.
    """
    deadlines = []
    doc = nlp_spacy(text)

    # Use spaCy's NER for date/time entities
    for ent in doc.ents:
        if ent.label_ in ["DATE", "TIME", "EVENT"]: # EVENT can sometimes catch specific deadlines
            # Use dateparser to make sense of the extracted entity text
            # PREFER_DATES_FROM='future' tries to interpret ambiguous dates as future if possible.
            # RELATIVE_BASE=datetime.now() anchors relative dates (e.g., "next Monday") to current time.
            parsed_date = dateparser.parse(ent.text, settings={'PREFER_DATES_FROM': 'future', 'RELATIVE_BASE': datetime.now()})
            if parsed_date:
                # Get surrounding context to determine if it's actually a deadline
                context = text[max(0, ent.start_char - 50):min(len(text), ent.end_char + 50)].lower()
                deadline_keywords = ["deadline", "due", "by", "before", "expires", "register", "submit", "apply", "on or before", "last date"]
                
                # Check for explicit deadline keywords OR if it's a future date within next 30 days
                # Current time for comparison
                current_time = datetime.now()
                # Check if parsed date is in the future
                is_future_date = (parsed_date - current_time).days >= 0
                # Check if it's within the next 30 days for general future dates
                is_within_30_days = (parsed_date - current_time).days <= 30

                if any(keyword in context for keyword in deadline_keywords) and is_future_date:
                    deadlines.append(parsed_date.strftime('%Y-%m-%d %H:%M'))
                elif ent.label_ == "DATE" and is_future_date and is_within_30_days: 
                    deadlines.append(parsed_date.strftime('%Y-%m-%d %H:%M'))
    return list(set(deadlines)) # Return unique deadlines

def extract_key_points_and_actions(text):
    """
    Extracts crucial points and action items using a combination of heuristics and extractive summarization.
    Aims for 'perfect output' by identifying impactful sentences.
    """
    key_points = []
    doc = nlp_spacy(text)

    # Heuristic 1: Sentences containing explicit action verbs/phrases
    action_indicators = [
        "please", "kindly", "ensure", "confirm", "submit", "reply by", "action required",
        "must", "should", "need to", "important:", "note:", "deadline", "review", "attend",
        "find attached", "see attached"
    ]
    # Heuristic 2: Sentences containing high-impact entities (PERSON, ORG, GPE, PRODUCT, EVENT, MONEY)
    # Heuristic 3: Sentences that are questions (often imply action or key info)

    processed_sentences = set() # To avoid duplicate key points if heuristics overlap

    for sent in doc.sents:
        sent_text = sent.text.strip()
        if not sent_text or sent_text in processed_sentences:
            continue

        is_key = False
        # Check Heuristic 1
        if any(indicator in sent_text.lower() for indicator in action_indicators):
            is_key = True
        # Check Heuristic 2 (presence of significant entities)
        if not is_key: # Only if not already marked as key by action indicator
            for ent in sent.ents:
                if ent.label_ in ["PERSON", "ORG", "GPE", "PRODUCT", "EVENT", "MONEY"]: # Significant entities
                    is_key = True
                    break
        # Check Heuristic 3 (simple check for questions)
        if not is_key and sent_text.endswith("?"):
            is_key = True

        if is_key:
            key_points.append(sent_text)
            processed_sentences.add(sent_text)

    # For "perfect output," you might also consider:
    # 1. Using sentence transformers to cluster sentences and pick central ones.
    # 2. Applying a small extractive summarizer (like TextRank) to complement heuristic rules.
    # For now, the refined heuristics are a strong step.

    return key_points

def detect_attachments_with_context(text):
    """
    Detects file mentions with context, providing the 'why' they are attached.
    Returns a list of tuples: (filename, context_snippet).
    """
    mentioned_files = []
    # Regex to find filenames with common extensions
    # Improved regex to capture filename and also a surrounding group (e.g., 50 chars before/after)
    # This regex looks for a word-boundary, then (any word char + dot + common extension), then word-boundary
    # It then captures the surrounding context more broadly.
    file_pattern = r'(\b.{0,80}?)((\w+\.(?:pdf|docx|xlsx|pptx|jpg|png|zip|rar|txt|csv|mp4|mov|mp3))\b)(.{0,80}?\b)'
    # Increased context length to 80 chars for better "why"

    doc = nlp_spacy(text) # Process text with spaCy for sentence segmentation

    for match in re.finditer(file_pattern, text, re.IGNORECASE):
        pre_context = match.group(1).strip()
        filename = match.group(2)
        post_context = match.group(3).strip()

        # Try to get the full sentence containing the mention for better context
        full_sentence = ""
        for sent in doc.sents:
            if filename.lower() in sent.text.lower():
                full_sentence = sent.text.strip()
                break

        # If a full sentence is found, use that. Otherwise, piece together pre/post context.
        context_snippet = full_sentence if full_sentence else (pre_context + filename + post_context).replace(filename, f"**{filename}**").strip()

        # Remove multiple spaces inside the snippet
        context_snippet = re.sub(r'\s+', ' ', context_snippet).strip()

        # Optional: Add a simple check to ensure context is not just the filename or very short irrelevant text
        if len(context_snippet) < 10 and not full_sentence: # If snippet is too short and not a full sentence
             context_snippet = "" # Fallback to no context if it's too minimal

        mentioned_files.append((filename, context_snippet))

    return list(set(mentioned_files)) # Return unique files with their context