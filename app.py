import streamlit as st
import imaplib # Needed here for IMAP4.error for specific error handling
import logging
from email_utils import connect_to_imap, fetch_recent_emails, fetch_email_content
# Import ALL your NLP functions and the model loader
from nlp_utils import load_nlp_models, clean_email_text, get_summary, \
                       extract_deadlines, extract_key_points_and_actions, \
                       detect_attachments_with_context

# Configure logging for better debugging (visible in terminal running Streamlit)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Load NLP Models (This will only run once due to @st.cache_resource) ---
# Call the function from nlp_utils.py to load your models.
# The actual models (summarizer, nlp_spacy) are managed internally by nlp_utils.py
# and cached by Streamlit. You just need to call this to trigger their loading.
load_nlp_models()
# You don't directly get the model objects back here, as they are loaded
# globally within nlp_utils.py and managed by st.cache_resource.
# Your nlp_utils functions will automatically use these loaded models.


# --- Streamlit App Configuration ---
st.set_page_config(page_title="Intelligent Email Quick-Digest Viewer", layout="wide")
st.title("📧 Intelligent Email Quick-Digest Viewer")
st.markdown("""
Your personal AI assistant for quick email insights!
Connect your email, select a message, and instantly get summaries,
deadlines, key points, and mentioned attachments.
""")

st.divider()

# --- Initialize session state variables ---
if 'imap_connection' not in st.session_state:
    st.session_state['imap_connection'] = None
if 'email_credentials' not in st.session_state:
    st.session_state['email_credentials'] = {}
if 'recent_emails' not in st.session_state:
    st.session_state['recent_emails'] = []
if 'selected_email_uid' not in st.session_state:
    st.session_state['selected_email_uid'] = None
if 'current_email_content' not in st.session_state:
    st.session_state['current_email_content'] = ""

# --- Step 1: Connect Your Email Account ---
st.header("Step 1: Connect Your Email Account 🔗")

if st.session_state['imap_connection'] is None:
    st.info("Please enter your email credentials to connect.")

    with st.form("email_connect_form"):
        email_provider = st.selectbox(
            "Choose your Email Provider:",
            ("Gmail", "Other (IMAP)"),
            key="email_provider_select"
        )
        user_email = st.text_input("Your Email Address:", placeholder="your.email@example.com", key="user_email_input")
        user_password = st.text_input("Your App Password / Email Password:", type="password", key="user_password_input")

        imap_server_default = "imap.gmail.com" if email_provider == "Gmail" else ""
        imap_server = st.text_input("IMAP Server Address:", value=imap_server_default, key="imap_server_input")
        imap_port = st.number_input("IMAP Port (usually 993 for SSL):", value=993, min_value=1, key="imap_port_input")

        submitted = st.form_submit_button("Connect to Email")

        if submitted:
            if user_email and user_password and imap_server:
                with st.spinner("Connecting to email..."):
                    try:
                        mail_conn = connect_to_imap(user_email, user_password, imap_server, imap_port)
                        if mail_conn:
                            st.session_state['imap_connection'] = mail_conn
                            st.session_state['email_credentials'] = {
                                'email': user_email,
                                'password': user_password,
                                'imap_server': imap_server,
                                'imap_port': imap_port
                            }
                            st.success("Successfully connected to email!")
                            st.session_state['recent_emails'] = fetch_recent_emails(st.session_state['imap_connection'])
                            if not st.session_state['recent_emails']:
                                st.warning("No recent emails found in your inbox or failed to fetch. Please try a different folder or check permissions.")
                        else:
                            st.error("Failed to connect. Please check your credentials and IMAP server settings.")
                    except imaplib.IMAP4.error as e:
                        st.error(f"IMAP login error: {e}. Please ensure you're using an App Password for Gmail/Outlook.")
                    except Exception as e:
                        st.error(f"An unexpected error occurred during connection: {e}")
            else:
                st.warning("Please fill in all email connection details.")
else:
    st.success("You are connected to your email account!")
    if st.button("Reconnect / Refresh Email List"):
        st.session_state['recent_emails'] = fetch_recent_emails(st.session_state['imap_connection'])
        if not st.session_state['recent_emails']:
            st.warning("No recent emails found or failed to refresh. You might need to reconnect if the session expired.")
            st.session_state['imap_connection'] = None
            st.session_state['selected_email_uid'] = None
            st.rerun()


st.divider()

# --- Step 2: Browse & Get Digest ---
st.header("Step 2: Browse & Get Digest ✨")

if st.session_state['imap_connection'] is not None and st.session_state['recent_emails']:
    col1, col2 = st.columns([1, 2])

    with col1:
        st.subheader("Recent Emails")
        if st.session_state['recent_emails']:
            email_options = {
                f"From: {email_info['from']} | Subject: {email_info['subject']}": email_info['uid']
                for email_info in st.session_state['recent_emails']
            }
            selected_display_text = st.radio(
                "Select an email to view its digest:",
                options=list(email_options.keys()),
                key="email_selector"
            )
            selected_uid_from_radio = email_options[selected_display_text] if selected_display_text else None

            if selected_uid_from_radio and st.session_state['selected_email_uid'] != selected_uid_from_radio:
                st.session_state['selected_email_uid'] = selected_uid_from_radio
                with st.spinner(f"Fetching content for UID: {selected_uid_from_radio}..."):
                    st.session_state['current_email_content'] = fetch_email_content(
                        st.session_state['imap_connection'],
                        st.session_state['selected_email_uid']
                    )
                    if st.session_state['current_email_content'] is None:
                        st.warning(f"Could not fetch content for UID: {st.session_state['selected_email_uid']}. It might be malformed or an issue with decoding.")
                    # Clear previous NLP results when a new email is selected
                    st.session_state['summary'] = ""
                    st.session_state['key_points'] = []
                    st.session_state['deadlines'] = []
                    st.session_state['attachments'] = []

        else:
            st.info("No emails loaded. Connect your email or refresh the list.")

    with col2:
        st.subheader("Email Digest")
        if st.session_state['current_email_content']:
            # --- Perform NLP Analysis and Display Digest ---
            with st.spinner("Generating intelligent digest... This might take a moment (loading models if first time)."):
                # Clean the raw email content first
                cleaned_content = clean_email_text(st.session_state['current_email_content'])

                # --- ADD THIS LINE HERE ---
                st.text_area("DEBUG: Cleaned Email Content:", cleaned_content, height=200)
                # --- END OF LINE TO ADD ---

                # Store results in session state to avoid re-running NLP on every minor interaction
                # Check if results are already computed for the current email content
                if 'last_analyzed_content' not in st.session_state or st.session_state['last_analyzed_content'] != cleaned_content:
                    st.session_state['summary'] = get_summary(cleaned_content)
                    st.session_state['key_points'] = extract_key_points_and_actions(cleaned_content)
                    st.session_state['deadlines'] = extract_deadlines(cleaned_content)
                    st.session_state['attachments'] = detect_attachments_with_context(cleaned_content)
                    st.session_state['last_analyzed_content'] = cleaned_content # Store content to check against next time
                
                # Display the results
                st.subheader("📝 Summary")
                st.write(st.session_state['summary'])

                if st.session_state['key_points']:
                    st.subheader("💡 Crucial Points / Action Items")
                    for point in st.session_state['key_points']:
                        st.markdown(f"- {point}") # Use markdown for bullet points
                else:
                    st.info("No distinct crucial points or action items identified.")

                if st.session_state['deadlines']:
                    st.subheader("⏰ Deadlines Detected")
                    for deadline in st.session_state['deadlines']:
                        st.write(f"- {deadline}")
                else:
                    st.info("No specific deadlines found.")

                if st.session_state['attachments']:
                    st.subheader("📎 Mentioned Attachments")
                    for filename, context in st.session_state['attachments']:
                        if context:
                            st.markdown(f"- **{filename}**: {context}")
                        else:
                            st.write(f"- {filename}")
                else:
                    st.info("No file attachments mentioned in the text.")

            # Optional: Display raw content for debugging (can be removed later)
            with st.expander("View Raw Email Content (for debugging)"):
                 st.text_area("Raw Content:", st.session_state['current_email_content'], height=300)

        else:
            st.info("Select an email from the left to generate its digest.")
else:
    st.info("Please connect your email account in Step 1 to browse emails.")


# Ensure the app reruns if session_state changes that need a refresh
# (e.g., after successful connection to show email list immediately)
if 'rerun_flag' in st.session_state and st.session_state['rerun_flag']:
    st.session_state['rerun_flag'] = False # Reset flag
    st.rerun() # Trigger a rerun