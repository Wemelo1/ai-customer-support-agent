"""
web_widget.py — Flask API backend for the embeddable web chat widget.

Setup:
1. pip install flask flask-cors
2. Run: python web_widget.py
3. Deploy to Render/Railway/Fly.io
4. Embed the widget on ANY website with one <script> tag (see widget.js)
"""

import os
import uuid
import json
import datetime
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from agent_core import SupportAgent

app = Flask(__name__)
CORS(app)  # Allow all origins so the widget works on any website

agent = SupportAgent()
agent.business_name = os.getenv("BUSINESS_NAME", "My Business")

# Load knowledge base
KB_FOLDER = "knowledge_base"
if os.path.exists(KB_FOLDER):
    for filename in os.listdir(KB_FOLDER):
        if filename.endswith(".txt"):
            with open(os.path.join(KB_FOLDER, filename)) as f:
                agent.add_document(filename, f.read())

sessions = {}


@app.route("/chat", methods=["POST"])
def chat():
    """Main chat endpoint called by the web widget."""
    data = request.json
    session_id = data.get("session_id", str(uuid.uuid4()))
    user_message = data.get("message", "").strip()

    if not user_message:
        return jsonify({"error": "Empty message"}), 400

    if session_id not in sessions:
        sessions[session_id] = {"history": []}
    session = sessions[session_id]

    session["history"].append({"role": "user", "content": user_message})

    result = agent.respond(user_message, session["history"])
    reply = result["response"]
    ticket_id = None

    if result.get("create_ticket"):
        ticket_id = _save_ticket(session_id, user_message, result)
        reply += f"\n\n🎫 Ticket created: **{ticket_id}**. We'll follow up within 24 hours."

    session["history"].append({"role": "assistant", "content": reply})
    if len(session["history"]) > 20:
        session["history"] = session["history"][-20:]

    return jsonify({
        "session_id": session_id,
        "response": reply,
        "escalate": result.get("escalate", False),
        "ticket_id": ticket_id,
        "timestamp": datetime.datetime.now().isoformat()
    })


@app.route("/ticket", methods=["POST"])
def create_ticket():
    """Manually create a ticket from the widget form."""
    data = request.json
    ticket_id = _save_ticket(
        data.get("session_id", "web"),
        data.get("issue", "No description"),
        {"category": data.get("category", "General"), "priority": data.get("priority", "Medium")}
    )
    return jsonify({"ticket_id": ticket_id, "status": "created"})


@app.route("/search", methods=["GET"])
def search_docs():
    """Search the knowledge base."""
    query = request.args.get("q", "")
    if not query:
        return jsonify({"results": []})
    results = agent.search_docs(query)
    return jsonify({"results": results})


@app.route("/widget.js")
def serve_widget():
    """Serve the embeddable widget JS."""
    return send_file("widget.js", mimetype="application/javascript")


@app.route("/health")
def health():
    return jsonify({"status": "ok", "business": agent.business_name})


def _save_ticket(session_id, issue, result) -> str:
    ticket_id = f"TKT-{str(uuid.uuid4())[:6].upper()}"
    ticket = {
        "id": ticket_id,
        "session": session_id,
        "issue": issue,
        "category": result.get("category", "General"),
        "priority": result.get("priority", "Medium"),
        "status": "Open",
        "created": datetime.datetime.now().isoformat(),
        "channel": "Web"
    }
    os.makedirs("tickets", exist_ok=True)
    with open(f"tickets/{ticket_id}.json", "w") as f:
        json.dump(ticket, f, indent=2)
    return ticket_id


if __name__ == "__main__":
    print(f"🚀 Web widget API running at http://localhost:8000")
    app.run(host="0.0.0.0", port=8000, debug=True)
