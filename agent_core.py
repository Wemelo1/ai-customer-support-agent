import os
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

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
        self.llm = ChatGroq(
            model="llama3-8b-8192",
            api_key=os.getenv("GROQ_API_KEY", ""),
            temperature=0.3
        )
        self.embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )
        self.vectorstore = None
        self.doc_names = []
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=300,
            chunk_overlap=30
        )

    def add_document(self, name, content):
        chunks = self.splitter.split_text(content)
        metadatas = [{"source": name}] * len(chunks)
        if self.vectorstore is None:
            self.vectorstore = Chroma.from_texts(
                texts=chunks,
                embedding=self.embeddings,
                metadatas=metadatas
            )
        else:
            self.vectorstore.add_texts(texts=chunks, metadatas=metadatas)
        if name not in self.doc_names:
            self.doc_names.append(name)

    def search_docs(self, query, k=3):
        if self.vectorstore is None:
            return []
        results = self.vectorstore.similarity_search(query, k=k)
        return [
            {"source": r.metadata.get("source", "Unknown"), "content": r.page_content}
            for r in results
        ]

    def list_docs(self):
        return self.doc_names

    def _get_context(self, query):
        if self.vectorstore is None:
            return "No documents loaded."
        docs = self.search_docs(query)
        if not docs:
            return "No relevant documentation found."
        return "\n".join([f"[{d['source']}]: {d['content'][:200]}" for d in docs])

    def _should_escalate(self, text):
        return any(kw in text.lower() for kw in ESCALATE_KEYWORDS)

    def _should_create_ticket(self, text):
        return any(kw in text.lower() for kw in TICKET_KEYWORDS)

    def respond(self, user_message, history):
        context = self._get_context(user_message)
        force_escalate = self._should_escalate(user_message)
        force_ticket = self._should_create_ticket(user_message)

        system_text = (
            "You are a helpful AI Customer Support Agent for "
            + self.business_name
            + ". Answer questions, create tickets, or escalate to humans when needed. "
            + "Context: " + context
            + " Be warm and concise. At the end of your reply write exactly one of these on its own line: "
            + "ACTION:none or ACTION:create_ticket or ACTION:escalate"
        )

        messages = [SystemMessage(content=system_text)]

        for msg in history[-2:]:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"][:300]))
            elif msg["role"] == "assistant":
                messages.append(AIMessage(content=msg["content"][:200]))

        messages.append(HumanMessage(content=user_message))

        raw_response = self.llm.invoke(messages).content

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
