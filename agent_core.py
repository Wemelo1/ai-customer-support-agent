import os
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.output_parsers import StrOutputParser

ESCALATE_KEYWORDS = [
    "human", "agent", "person", "manager", "supervisor",
    "speak to someone", "real person", "not helpful",
    "lawsuit", "legal", "fraud", "scam"
]

TICKET_KEYWORDS = [
    "refund", "broken", "damaged", "missing", "wrong item",
    "not working", "error", "bug", "complaint"
]

SYSTEM_PROMPT = """You are a helpful AI Customer Support Agent for {business_name}.

You can answer customer questions, create support tickets, and escalate to human agents.

Context from knowledge base:
{context}

Guidelines:
- Be warm, helpful and professional
- Keep responses to 2-4 sentences unless more detail is needed
- If unsure, offer to create a ticket
- Always suggest a next step

At the very end of your reply, on its own line, write one of these exactly:
ACTION:none
ACTION:create_ticket
ACTION:escalate"""


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
            chunk_size=500,
            chunk_overlap=50
        )

    def add_document(self, name: str, content: str):
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

    def search_docs(self, query: str, k: int = 3) -> list:
        if self.vectorstore is None:
            return []
        results = self.vectorstore.similarity_search(query, k=k)
        return [{"source": r.metadata.get("source", "Unknown"), "content": r.page_content} for r in results]

    def list_docs(self) -> list:
        return self.doc_names

    def _get_context(self, query: str) -> str:
        if self.vectorstore is None:
            return "No company documents loaded yet."
        docs = self.search_docs(query)
        if not docs:
            return "No relevant documentation found."
        return "\n\n".join([f"[From {d['source']}]: {d['content'][:300]}" for d in docs])

    def _should_escalate(self, text: str) -> bool:
        return any(kw in text.lower() for kw in ESCALATE_KEYWORDS)

    def _should_create_ticket(self, text: str) -> bool:
        return any(kw in text.lower() for kw in TICKET_KEYWORDS)

    def respond(self, user_message: str, history: list) -> dict:
        context = self._get_context(user_message)
        force_escalate = self._should_escalate(user_message)
        force_ticket = self._should_create_ticket(user_message)

        lc_messages = []
for msg in history[-2:]:  # Only last 1 exchange
    if msg["role"] == "user":
        lc_messages.append(HumanMessage(content=msg["content"]))
    elif msg["role"] == "assistant":
        content = msg["content"][:200]  # Trim long replies
        lc_messages.append(AIMessage(content=content))

        prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            MessagesPlaceholder(variable_name="history"),
            ("human", "{input}")
        ])

        chain = prompt | self.llm | StrOutputParser()

        raw_response = chain.invoke({
            "business_name": self.business_name,
            "context": context,
            "history": lc_messages,
            "input": user_message
        })

        # Parse action
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
