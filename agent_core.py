import os
from groq import Groq

ESCALATE_KEYWORDS = [
    "human", "agent", "person", "manager", "supervisor",
    "speak to someone", "real person", "not helpful",
    "lawsuit", "legal", "fraud", "scam"
]

TICKET_KEYWORDS = [
    "refund", "broken", "damaged", "missing", "wrong item",
    "not working", "error", "bug", "complaint"
]


class SupportAgent:
    def __init__(self):
        self.business_name = "My Business"
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY", ""))
        self.doc_names = []
        self.docs = []

    def add_document(self, name, content):
        self.docs.append({"source": name, "content": content})
        if name not in self.doc_names:
            self.doc_names.append(name)

    def search_docs(self, query, k=3):
        if not self.docs:
            return []
        query_lower = query.lower()
        scored = []
        for doc in self.docs:
            score = sum(1 for word in query_lower.split() if word in doc["content"].lower())
            scored.append((score, doc))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [d for _, d in scored[:k]]

    def list_docs(self):
        return self.doc_names

    def _get_context(self, query):
        if not self.docs:
            return "No documents loaded."
        docs = self.search_docs(query)
        if not docs:
            return "No relevant documentation found."
        return "\n".join([f"[{d['source']}]: {d['content'][:300]}" for d in docs])

    def _should_escalate(self, text):
        return any(kw in text.lower() for kw in ESCALATE_KEYWORDS)

    def _should_create_ticket(self, text):
        return any(kw in text.lower() for kw in TICKET_KEYWORDS)

    def respond(self, user_message, history):
        context = self._get_context(user_message)
        force_escalate = self._should_escalate(user_message)
        force_ticket = self._should_create_ticket(user_message)

        system_text = (
            "You are a helpful AI Customer Support Agent for " + self.business_name + ". "
            "Answer questions clearly and concisely in 2-3 sentences. "
            "Use this context if relevant: " + context[:500] + " "
            "End your reply with exactly one of these on its own line: "
            "ACTION:none or ACTION:create_ticket or ACTION:escalate"
        )

        messages = [{"role": "system", "content": system_text}]

        for msg in history[-2:]:
            if msg["role"] in ("user", "assistant"):
                messages.append({
                    "role": msg["role"],
                    "content": msg["content"][:200]
                })

        messages.append({"role": "user", "content": user_message})

        response = self.client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=messages,
            max_tokens=300,
            temperature=0.3
        )

        raw_response = response.choices[0].message.content

        action = "none"
        clean_response = raw_response

        if "ACTION:" in raw_response:
            parts = raw_response.split("ACTION:")
            clean_response = parts[0].strip()
            action_str = parts[1].strip().lower()
            if "escalate" in action_str:
                action = "escalate"
            elif "create_ticket" in action_str:
                action = "create_ticket"

        if force_escalate:
            action = "escalate"
        if force_ticket and action == "none":
            action = "create_ticket"

        return {
            "response": clean_response,
            "escalate": action == "escalate",
            "create_ticket": action in ("create_ticket", "both"),
            "priority": "Medium",
            "category": "General",
        }
