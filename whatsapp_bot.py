"""
whatsapp_bot.py — WhatsApp integration using Twilio API.

Setup:
1. pip install twilio flask
2. Sign up at twilio.com → get a WhatsApp sandbox number
3. Set env vars: TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, GROQ_API_KEY
4. Run: python whatsapp_bot.py
5. Expose with ngrok: ngrok http 5000
6. Paste the ngrok URL into Twilio sandbox webhook settings
"""

import os
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
from agent_core import SupportAgent
import uuid
import json

app = Flask(__name__)
agent = SupportAgent()

# In-memory session store (use Redis in production)
sessions = {}

# ── Load knowledge base ──────────────────────────────────────────────────────
# Drop .txt FAQ files into a /knowledge_base folder and they'll be indexed
KB_FOLDER = "knowledge_base"
if os.path.exists(KB_FOLDER):
    for filename in os.listdir(KB_FOLDER):
        if filename.endswith(".txt"):
            with open(os.path.join(KB_FOLDER, filename), "r") as f:
                content = f.read()
            agent.add_document(filename, content)
    print(f"✅ Knowledge base loaded from {KB_FOLDER}/")

# ── Webhook ──────────────────────────────────────────────────────────────────
@app.route("/whatsapp", methods=["POST"])
def whatsapp_webhook():
    incoming_msg = request.values.get("Body", "").strip()
    sender = request.values.get("From", "")  # e.g. whatsapp:+2348012345678

    # Get or create session for this sender
    if sender not in sessions:
        sessions[sender] = {"history": [], "ticket_count": 0}
    session = sessions[sender]

    # Greeting for new sessions
    if not session["history"]:
        greeting = (
            f"👋 Hello! I'm the AI Support Agent for *{agent.business_name}*.\n\n"
            "I can help you with:\n"
            "• ❓ FAQs and general questions\n"
            "• 🎫 Creating support tickets\n"
            "• 📞 Connecting you to a human agent\n\n"
            "How can I help you today?"
        )
        session["history"].append({"role": "assistant", "content": greeting})
        return _send_reply(greeting)

    # Add user message to history
    session["history"].append({"role": "user", "content": incoming_msg})

    # Get AI response
    result = agent.respond(incoming_msg, session["history"])
    reply_text = result["response"]

    # Handle ticket creation
    if result.get("create_ticket"):
        ticket_id = f"TKT-{str(uuid.uuid4())[:6].upper()}"
        session["ticket_count"] += 1
        reply_text += f"\n\n🎫 *Ticket created:* {ticket_id}\nWe'll follow up within 24 hours."
        _save_ticket(ticket_id, sender, incoming_msg, result)

    # Handle escalation
    if result.get("escalate"):
        reply_text += (
            "\n\n👤 *Connecting you to a human agent...*\n"
            "Average wait time: ~3 minutes.\n"
            "Reference: #ESC-" + str(uuid.uuid4())[:4].upper()
        )
        _notify_human_agent(sender, incoming_msg, session["history"])

    session["history"].append({"role": "assistant", "content": reply_text})

    # Keep session history manageable
    if len(session["history"]) > 20:
        session["history"] = session["history"][-20:]

    return _send_reply(reply_text)


def _send_reply(text: str):
    """Return a TwiML response."""
    resp = MessagingResponse()
    resp.message(text)
    return str(resp)


def _save_ticket(ticket_id, sender, issue, result):
    """Save ticket to a JSON file (use a database in production)."""
    import datetime
    ticket = {
        "id": ticket_id,
        "sender": sender,
        "issue": issue,
        "category": result.get("category", "General"),
        "priority": result.get("priority", "Medium"),
        "status": "Open",
        "created": datetime.datetime.now().isoformat(),
        "channel": "WhatsApp"
    }
    os.makedirs("tickets", exist_ok=True)
    with open(f"tickets/{ticket_id}.json", "w") as f:
        json.dump(ticket, f, indent=2)
    print(f"🎫 Ticket saved: {ticket_id}")


def _notify_human_agent(sender, message, history):
    """
    Send an alert to your support team via WhatsApp or SMS.
    Replace AGENT_PHONE with your actual support team number.
    """
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    agent_phone = os.getenv("AGENT_PHONE", "whatsapp:+2348000000000")
    twilio_number = os.getenv("TWILIO_WHATSAPP_NUMBER", "whatsapp:+14155238886")

    if not account_sid or not auth_token:
        print("⚠️ Twilio credentials not set — skipping agent notification")
        return

    client = Client(account_sid, auth_token)
    alert = (
        f"🚨 *Escalation Alert*\n"
        f"Customer: {sender}\n"
        f"Last message: {message[:100]}\n"
        f"Please follow up ASAP."
    )
    client.messages.create(body=alert, from_=twilio_number, to=agent_phone)
    print(f"📲 Human agent notified about escalation from {sender}")


# ── Outbound messaging (optional) ────────────────────────────────────────────
def send_proactive_message(to_number: str, message: str):
    """
    Send a message to a customer proactively (e.g. order update).
    to_number format: +2348012345678
    """
    client = Client(os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN"))
    client.messages.create(
        body=message,
        from_=f"whatsapp:{os.getenv('TWILIO_WHATSAPP_NUMBER', '+14155238886')}",
        to=f"whatsapp:{to_number}"
    )


if __name__ == "__main__":
    print("🚀 WhatsApp bot running on http://0.0.0.0:5000/whatsapp")
    print("📌 Expose with: ngrok http 5000")
    app.run(host="0.0.0.0", port=5000, debug=True)
