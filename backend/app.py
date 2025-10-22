from flask import Flask, request
from flask_cors import CORS
import pdfplumber
import spacy
from spacy.matcher import Matcher
from composio import Composio
import base64
import io

# --- Load NLP Model ---
nlp = spacy.load("en_core_web_sm")

# --- SpaCy NLP functions ---
def extract_keywords(text):
    doc = nlp(text.lower())
    keywords = set()
    for chunk in doc.noun_chunks:
        keywords.add(chunk.text)
    for token in doc:
        if token.pos_ in ("NOUN", "PROPN"):
            keywords.add(token.text)
    filtered_keywords = {kw for kw in keywords if len(kw) > 2 and kw not in nlp.Defaults.stop_words}
    return list(filtered_keywords)

# --- Recursive attachment finder ---
def find_attachments(parts):
    attachments = []
    for part in parts:
        if part.get("filename") and part["filename"].lower().endswith((".pdf", ".txt")):
            attachments.append(part)
        if "parts" in part:
            attachments.extend(find_attachments(part["parts"]))
    return attachments

# --- Global app ---
app = Flask(__name__)
CORS(app)
composio = Composio(api_key="ak_DNQlLvKJKdhEaOpBDQ07")

# --- Job Description ---
JD_TEXT = """
We are hiring a Python developer with machine learning experience.
Must know Python, spaCy, and scikit-learn.
Experience with Flask, React, and SQL is a huge plus.
"""
jd_keywords = extract_keywords(JD_TEXT)

# --- Route to list all email subjects and process attachments ---
@app.route("/process-emails")
def process_emails():
    # Dynamic Gmail account selection
    entity_id = request.args.get("entity_id", "pg-test-f2044cb2-7e34-4785-a8d4-19857f389df7")
    print(f"Using Composio Entity ID: {entity_id}")

    # 1. Fetch all inbox emails
    try:
        search_response = composio.tools.execute(
            slug="GMAIL_FETCH_EMAILS",
            arguments={"userId": "me", "query": ""},  # empty query fetches all inbox emails
            dangerously_skip_version_check=True,
            user_id=entity_id
        )
    except Exception as e:
        print(f"Error fetching emails: {e}")
        return {"status": "error", "message": str(e)}, 500

    messages = search_response.get("messages", [])
    if not messages:
        print("No emails found in this account.")
        return {"status": "success", "message": "No emails found."}

    print(f"Total emails fetched: {len(messages)}")
    email_subjects = []
    processed_applicants = []

    # 2. Loop over each email
    for msg in messages:
        msg_id = msg["id"]
        try:
            email_data = composio.tools.execute(
                slug="GMAIL_GET_EMAIL",
                arguments={"userId": "me", "id": msg_id},
                dangerously_skip_version_check=True,
                user_id=entity_id
            )
            # Get subject for logging
            subject = next((h["value"] for h in email_data["payload"]["headers"] if h["name"]=="Subject"), "No Subject")
            email_subjects.append(subject)
            print(f"Found email subject: {subject}")

            # Get sender
            sender = next((h["value"] for h in email_data["payload"]["headers"] if h["name"] == "From"), "Unknown Sender")

            # Process attachments recursively
            if "parts" in email_data["payload"]:
                attachments = find_attachments(email_data["payload"]["parts"])
                for part in attachments:
                    attachment_id = part["body"]["attachmentId"]
                    attachment_data = composio.tools.execute(
                        slug="GMAIL_GET_ATTACHMENT",
                        arguments={"userId": "me", "id": attachment_id, "messageId": msg_id},
                        dangerously_skip_version_check=True,
                        user_id=entity_id
                    )
                    file_data = base64.urlsafe_b64decode(attachment_data["data"])

                    # Extract text
                    extracted_text_resume = ""
                    if part["filename"].endswith(".pdf"):
                        with pdfplumber.open(io.BytesIO(file_data)) as pdf:
                            for page in pdf.pages:
                                extracted_text_resume += page.extract_text() + "\n"
                    else:
                        extracted_text_resume = file_data.decode("utf-8")

                    # Score resume against JD
                    resume_lower = extracted_text_resume.lower()
                    matched_keywords = [k for k in jd_keywords if k in resume_lower]
                    missing_keywords = list(set(jd_keywords) - set(matched_keywords))
                    score = (len(matched_keywords) / len(jd_keywords)) * 100 if jd_keywords else 0

                    processed_applicants.append({
                        "sender": sender,
                        "filename": part["filename"],
                        "score": f"{score:.2f}",
                        "matched": matched_keywords,
                        "missing": missing_keywords
                    })

                    # Mark email as read
                    composio.tools.execute(
                        slug="GMAIL_ADD_LABEL_TO_EMAIL",
                        arguments={
                            "userId": "me",
                            "message_id": msg_id,
                            "remove_label_ids": ["UNREAD"]
                        },
                        dangerously_skip_version_check=True,
                        user_id=entity_id
                    )
                    print(f"Processed {part['filename']} from {sender}, Score: {score:.2f}%")

        except Exception as e:
            print(f"Error processing message {msg_id}: {e}")
            continue

    return {
        "status": "success",
        "total_emails": len(messages),
        "subjects": email_subjects,
        "processed_applicants": processed_applicants
    }

# --- Run app ---
if __name__ == "__main__":
    app.run(debug=True, port=5000)
