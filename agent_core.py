"""
agent_core.py — The brain of the AI Customer Support Agent.
Uses LangChain + Groq + ChromaDB for RAG-powered support.
"""
import os
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.output_parsers import StrOutputParser
import json

# Keywords that trigger escalation to a human agent
ESCALATE_KEYWORDS = [
    "human", "agent", "person", "manager", "supervisor",
    "speak to someone", "real person", "not helpful", "useless",
    "lawsuit", "legal", "fraud", "scam", "stolen"
]

# Keywords that trigger ticket creation
TICKET_KEYWORDS = [
    "refund", "broken", "damaged", "missing", "wrong item",
    "not working", "error", "bug", "complaint", "issue"
]

SYSTEM_PROMPT = """You are a helpful, professional AI Customer Support Agent for {business_name}.

Your capabilities:
- Answer customer questions using the knowledge base context provided
- Create support tickets for issues that need follow-up
- Escalate to human agents when customers request it or when issues are complex
- Search company documentation to find accurate answers

Context from knowledge base:
{context}

Guidelines:
- Be warm, helpful, and professional
- Keep responses concise (2-4 sentences unless detail is needed)
- If you don't know something, say so honestly and offer to create a ticket
- Always offer a next step (create ticket, escalate, or provide info)
- Use Nigerian-friendly language when appropriate (you serve Nigerian customers)
- Never make up information about orders, accounts, or policies

At the END of your response, output a JSON block on a new line like this:
```json
{{"action": "none", "priority": "Medium", "category": "General"}}
```
Action can be: "none", "create_ticket", "escalate", or "both"
"""

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
        """Add a document to the knowledge base."""
        chunks = self.splitter.split_text(content)
        texts = chunks
        metadatas = [{"source": name}] * len(chunks)

        if self.vectorstore is None:
            self.vectorstore = Chroma.from_texts(
                texts=texts,
                embedding=self.embeddings,
                metadatas=metadatas
            )
        else:
            self.vectorstore.add_texts(texts=texts, metadatas=metadatas)

        if name not in self.doc_names:
            self.doc_names.append(name)

    def search_docs(self, query: str, k: int = 3) -> list:
        """Search the knowledge base for relevant content."""
        if self.vectorstore is None:
            return []
        results = self.vectorstore.similarity_search(query, k=k)
        return [{"source": r.metadata.get("source", "Unknown"), "content": r.page_content} for r in results]

    def list_docs(self) -> list:
        return self.doc_names

    def _get_context(self, query: str) -> str:
        """Retrieve relevant context from knowledge base."""
        if self.vectorstore is None:
            return "No company documents loaded yet."
        docs = self.search_docs(query)
        if not docs:
            return "No relevant documentation found for this query."
        return "\n\n".join([f"[From {d['source']}]: {d['content']}" for d in docs])

    def _should_escalate(self, text: str) -> bool:
        text_lower = text.lower()
        return any(kw in text_lower for kw in ESCALATE_KEYWORDS)

    def _should_create_ticket(self, text: str) -> bool:
        text_lower = text.lower()
        return any(kw in text_lower for kw in TICKET_KEYWORDS)

    def respond(self, user_message: str, history: list) -> dict:
        """Generate a response and determine actions."""
        context = self._get_context(user_message)

        # Pre-check keywords before calling LLM
        force_escalate = self._should_escalate(user_message)
        force_ticket = self._should_create_ticket(user_message)

        # Build history for LLM
        lc_messages = []
        for msg in history[-6:]:  # Last 3 exchanges
            if msg["role"] == "user":
                lc_messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                lc_messages.append(AIMessage(content=msg["content"]))

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

        # Parse action JSON from response
        action = "none"
        priority = "Medium"
        category = "General"
        clean_response = raw_response

        if "```json" in raw_response:
            try:
                json_start = raw_response.index("```json") + 7
                json_end = raw_response.index("```", json_start)
                json_str = raw_response[json_start:json_end].strip()
                action_data = json.loads(json_str)
                action = action_data.get("action", "none")
                priority = action_data.get("priority", "Medium")
                category = action_data.get("category", "General")
                clean_response = raw_response[:raw_response.index("```json")].strip()
            except Exception:
                clean_response = raw_response

        # Override with keyword detection
        if force_escalate:
            action = "escalate"
        if force_ticket and action == "none":
            action = "create_ticket"

        return {
            "response": clean_response,
            "escalate": action in ("escalate", "both"),
            "create_ticket": action in ("create_ticket", "both"),
            "priority": priority,
            "category": category,
        }
