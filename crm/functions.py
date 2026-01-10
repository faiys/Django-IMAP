import imaplib
import email
from email.header import decode_header
from email.utils import parseaddr
from bs4 import BeautifulSoup

IMAP_SERVER = "mail.privateemail.com"
IMAP_PORT = 993

def decode_header_value(value):
    if not value:
        return None
    decoded, charset = decode_header(value)[0]
    if isinstance(decoded, bytes):
        return decoded.decode(charset or "utf-8", errors="ignore")
    return decoded

def extract_body(msg):
    body = ""

    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            disposition = str(part.get("Content-Disposition"))

            if content_type == "text/plain" and "attachment" not in disposition:
                body = part.get_payload(decode=True).decode(errors="ignore")
                break
    else:
        body = msg.get_payload(decode=True).decode(errors="ignore")

    return body

def extract_attachments(msg):
    attachments = []

    for part in msg.walk():
        if part.get("Content-Disposition"):
            filename = part.get_filename()
            if filename:
                payload = part.get_payload(decode=True)
                attachments.append({
                    "filename": filename,
                    "content_type": part.get_content_type(),
                    "size": len(payload) if payload else 0
                })

    return attachments

def extract_full_body(msg):
    text_body = None
    html_body = None
    attachments = []

    for part in msg.walk():
        content_type = part.get_content_type()
        disposition = str(part.get("Content-Disposition"))

        # Plain text
        if content_type == "text/plain" and "attachment" not in disposition:
            text_body = part.get_payload(decode=True).decode(errors="ignore")

        # HTML body
        elif content_type == "text/html" and "attachment" not in disposition:
            html_body = part.get_payload(decode=True).decode(errors="ignore")

        # Attachments
        elif "attachment" in disposition:
            payload = part.get_payload(decode=True)
            attachments.append({
                "filename": part.get_filename(),
                "content_type": content_type,
                "size": len(payload) if payload else 0,
            })

    return text_body, html_body, attachments

# def fetch_emails(username, password, page , page_size ):
#     mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
#     mail.login(username, password)
#     mail.select("INBOX")

#     status, messages = mail.search(None, "ALL")
#     all_ids  = messages[0].split()

#     start = -page  * page_size 
#     end = None if page == 1 else -(page - 1) * page_size

#     mail_ids = all_ids[start:end]

#     emails = []

#     for mail_id in mail_ids:
#         # 1️⃣ Fetch headers
#         status, header_data = mail.fetch(mail_id, "(BODY.PEEK[HEADER])")
#         header_msg = email.message_from_bytes(header_data[0][1])
#         # 2️⃣ Fetch body text ONLY
#         status, body_data = mail.fetch(mail_id, "(BODY.PEEK[TEXT])")
#         body_msg = email.message_from_bytes(body_data[0][1])

#         emails.append({
#             "mail_id": mail_id.decode(),
#             "subject": decode_header_value(header_msg.get("Subject")),
#             "from": decode_header_value(header_msg.get("From")),
#             "to": decode_header_value(header_msg.get("To")),
#             "cc": decode_header_value(header_msg.get("Cc")),
#             "date": header_msg.get("Date"),
#             "message_id": header_msg.get("Message-ID"),
#             "body": extract_body(body_msg)[:50],   # ✅ fast
#         })

#     mail.logout()
#     return emails

def extract_uid(response_part):
    try:
        return response_part.split(b'UID ')[1].split()[0].decode()
    except Exception:
        return None
    
def extract_preview_from_msg(msg, limit=50):
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            disp = str(part.get("Content-Disposition"))

            if ctype == "text/plain" and "attachment" not in disp:
                return part.get_payload(decode=True)\
                           .decode(errors="ignore")[:limit]

            if ctype == "text/html" and "attachment" not in disp:
                html = part.get_payload(decode=True).decode(errors="ignore")
                text = BeautifulSoup(html, "html.parser").get_text(" ")
                return text.strip()[:limit]
    else:
        return msg.get_payload(decode=True)\
                  .decode(errors="ignore")[:limit]

    return ""

def fetch_emails(username, password, page, page_size):
    mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
    mail.login(username, password)
    mail.select("INBOX")

    # 1️⃣ Get all UIDs
    status, data = mail.uid("search", None, "ALL")
    uids = data[0].split()

    total_count = len(uids)

    if not uids:
        mail.logout()
        return []

    last_uid = int(uids[-1])

    # 2️⃣ Calculate UID range
    end_uid = last_uid - (page - 1) * page_size
    start_uid = max(1, end_uid - page_size + 1)

    uid_range = f"{start_uid}:{end_uid}"

    # 3️⃣ Fetch FULL emails (required for HTML-only mails)
    status, fetch_data = mail.uid("fetch", uid_range, "(RFC822)")

    emails = []

    for item in fetch_data:
        if not isinstance(item, tuple) or not item[1]:
            continue

        meta, raw_email = item
        uid = extract_uid(meta)

        if not uid:
            continue

        msg = email.message_from_bytes(raw_email)
        preview = extract_preview_from_msg(msg) 

        emails.append({
            "mail_id": uid,
            "subject": decode_header_value(msg.get("Subject")),
            "from": decode_header_value(msg.get("From")),
            "to": decode_header_value(msg.get("To")),
            "cc": decode_header_value(msg.get("Cc")),
            "date": msg.get("Date"),
            "message_id": msg.get("Message-ID"),
            "body": preview,
        })
    final_email = {"total_count" : total_count, "emails" : emails}
    mail.logout()
    return final_email



def fetch_one_email_full(username, password, mail_id):
    mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
    mail.login(username, password)
    mail.select("INBOX")

    # ✅ FETCH BY UID (NOT sequence number)
    status, data = mail.uid("fetch", mail_id, "(RFC822)")

    if status != "OK" or not data or not isinstance(data[0], tuple):
        mail.logout()
        return None

    raw_email = data[0][1]
    msg = email.message_from_bytes(raw_email)

    text_body, html_body, attachments = extract_full_body(msg)

    mail.logout()

    from_name, from_address = parseaddr(msg.get("From"))
    to_name, to_address = parseaddr(msg.get("To"))
    cc_name, cc_address = parseaddr(msg.get("Cc"))

    return {
        "mail_id": mail_id,
        "subject": decode_header_value(msg.get("Subject")),
        "from_name": decode_header_value(from_name),
        "from_address": decode_header_value(from_address),
        "to_name": decode_header_value(to_name),
        "to_address": decode_header_value(to_address),
        "cc_name": decode_header_value(cc_name),
        "cc_address": decode_header_value(cc_address),
        "date": msg.get("Date"),
        "message_id": msg.get("Message-ID"),
        "text_body": text_body,
        "html_body": html_body,
        "attachments": attachments,
    }

