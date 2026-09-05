import imaplib
import email
from email.header import decode_header
import logging
import re

# Configure logging for better debugging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def connect_to_imap(email_address, password, imap_server, imap_port=993):
    """
    Establishes and logs into an IMAP connection.
    Returns the IMAP4_SSL object if successful, None otherwise.
    """
    try:
        logging.info(f"Attempting to connect to IMAP server: {imap_server}:{imap_port} for {email_address}")
        mail = imaplib.IMAP4_SSL(imap_server, imap_port)
        mail.login(email_address, password)
        logging.info(f"Successfully connected and logged in to {email_address}")
        return mail
    except imaplib.IMAP4.error as e:
        logging.error(f"IMAP login failed: {e}")
        return None
    except Exception as e:
        logging.error(f"An unexpected error occurred during IMAP connection: {e}")
        return None

def fetch_recent_emails(mail, num_emails=20):
    """
    Fetches a list of recent email subjects and senders.
    'mail' is an active IMAP4_SSL connection object.
    Returns a list of dictionaries with 'uid', 'from', and 'subject'.
    """
    try:
        status, messages = mail.select("INBOX")
        if status != 'OK':
            logging.error(f"Failed to select INBOX: {status}")
            return []

        # Get the UIDs of the most recent emails
        status, email_ids = mail.search(None, "ALL") # ALL can be slow for many emails
        if status != 'OK':
            logging.error(f"Failed to search emails: {status}")
            return []

        email_id_list = email_ids[0].split()
        recent_ids = email_id_list[-num_emails:] # Get last 'num_emails' UIDs

        email_list = []
        for uid_bytes in recent_ids:
            uid = uid_bytes.decode('utf-8')
            status, msg_data = mail.fetch(uid_bytes, "(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT)])")
            if status != 'OK':
                logging.warning(f"Failed to fetch header for UID {uid}: {status}")
                continue

            raw_email = msg_data[0][1]
            msg = email.message_from_bytes(raw_email)

            # Decode header safely
            sender_header = decode_header(msg['From'])
            sender = str(sender_header[0][0]) if isinstance(sender_header[0][0], bytes) else sender_header[0][0]
            if sender_header[0][1]: # Check for encoding
                try:
                    sender = sender.encode('latin-1').decode(sender_header[0][1])
                except (UnicodeDecodeError, LookupError):
                    pass # Fallback to raw string if decoding fails

            subject_header = decode_header(msg['Subject'])
            subject = str(subject_header[0][0]) if isinstance(subject_header[0][0], bytes) else subject_header[0][0]
            if subject_header[0][1]:
                try:
                    subject = subject.encode('latin-1').decode(subject_header[0][1])
                except (UnicodeDecodeError, LookupError):
                    pass

            email_list.append({
                'uid': uid,
                'from': sender,
                'subject': subject
            })
        logging.info(f"Successfully fetched {len(email_list)} recent email headers.")
        return email_list
    except Exception as e:
        logging.error(f"An error occurred while fetching recent emails: {e}")
        return []

def fetch_email_content(mail, uid):
    """
    Fetches the full text content of a specific email by UID.
    'mail' is an active IMAP4_SSL connection object.
    Returns a dict with decoded text, raw body text, extracted links, and attachments, or None.
    """
    def decode_payload(payload_bytes, charset=None):
        if payload_bytes is None:
            return ""
        encodings_to_try = [charset, 'utf-8', 'latin-1']
        for encoding in encodings_to_try:
            if not encoding:
                continue
            try:
                return payload_bytes.decode(encoding, errors='ignore')
            except (LookupError, UnicodeDecodeError):
                continue
        return payload_bytes.decode('utf-8', errors='ignore')

    def extract_links(raw_text):
        pattern = re.compile(r'(?i)\b((?:https?://|www\.)[^\s<>"\'\])]+)')
        seen = set()
        unique_links = []
        for match in pattern.findall(raw_text or ""):
            normalized = match.rstrip('.,;:!?')
            if normalized not in seen:
                seen.add(normalized)
                unique_links.append(normalized)
        return unique_links

    try:
        status, msg_data = mail.fetch(uid, "(RFC822)")
        if status != 'OK':
            logging.error(f"Failed to fetch full content for UID {uid}: {status}")
            return None

        raw_email = msg_data[0][1]
        msg = email.message_from_bytes(raw_email)

        text_content = ""
        raw_text_parts = []
        extracted_links = []
        attachments = []
        seen_links = set()
        if msg.is_multipart():
            for part in msg.walk():
                ctype = part.get_content_type()
                cdispo = str(part.get('Content-Disposition') or "").lower()
                filename = part.get_filename()
                payload_bytes = part.get_payload(decode=True)

                if filename or 'attachment' in cdispo:
                    attachment_filename = filename or "attachment.bin"
                    attachments.append({
                        'filename': attachment_filename,
                        'content': payload_bytes or b"",
                        'content_type': ctype
                    })

                if ctype in ('text/plain', 'text/html') and payload_bytes is not None:
                    decoded_part = decode_payload(payload_bytes, part.get_content_charset())
                    raw_text_parts.append(decoded_part)
                    for link in extract_links(decoded_part):
                        if link not in seen_links:
                            seen_links.add(link)
                            extracted_links.append(link)

                # Look for plain text parts that are not attachments/inline files
                if ctype == 'text/plain' and 'attachment' not in cdispo and not filename and not text_content:
                    try:
                        text_content = decode_payload(payload_bytes, part.get_content_charset())
                    except Exception as e:
                        logging.warning(f"Could not decode plain text part from UID {uid}: {e}")
        else:
            # Not multipart, decode for raw and links and use text/plain for NLP text
            try:
                payload_bytes = msg.get_payload(decode=True)
                charset = msg.get_content_charset()
                decoded_content = decode_payload(payload_bytes, charset)
                raw_text_parts.append(decoded_content)
                extracted_links = extract_links(decoded_content)
                if msg.get_content_type() == 'text/plain':
                    text_content = decoded_content
            except Exception as e:
                logging.warning(f"Could not decode single part text from UID {uid}: {e}")

        raw_content = "\n".join([part for part in raw_text_parts if part]).strip()
        logging.info(
            f"Successfully fetched content for UID {uid}. Content length: {len(text_content)} chars. "
            f"Links: {len(extracted_links)}. Attachments: {len(attachments)}."
        )
        return {
            'text': text_content,
            'raw': raw_content,
            'links': extracted_links,
            'attachments': attachments
        }
    except Exception as e:
        logging.error(f"An error occurred while fetching email content for UID {uid}: {e}")
        return None