# 🤖 AI Customer Support Agent

Built by **Pr0_M1se** · Stack: LangChain + Groq + ChromaDB + Streamlit

A production-ready AI customer support system that works on **WhatsApp, Telegram, and Web** — all powered by the same AI brain.

---

## Features

- ✅ **FAQ answering** — RAG-powered answers from your company docs
- 🎫 **Ticket creation** — Auto-creates tickets when issues need follow-up
- 👤 **Human escalation** — Detects when a customer needs a real person
- 📚 **Doc search** — Semantic search across all your knowledge base documents
- 💬 **WhatsApp** — Via Twilio API
- 📱 **Telegram** — Via python-telegram-bot
- 🌐 **Web widget** — One `<script>` tag embeds it on any website

---

## Project Structure

```
support_agent/
├── app.py              ← Streamlit dashboard (main app)
├── agent_core.py       ← AI brain (LangChain + Groq + ChromaDB)
├── whatsapp_bot.py     ← WhatsApp integration (Twilio)
├── telegram_bot.py     ← Telegram bot
├── web_widget.py       ← Flask API for web widget
├── widget.js           ← Embeddable chat widget script
├── knowledge_base/
│   └── faq.txt         ← Sample FAQ (replace with your own)
├── tickets/            ← Auto-created ticket JSON files
├── requirements.txt
└── .env.example        ← Copy to .env and fill in keys
```

---

## Setup (5 minutes)

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Set up environment variables
```bash
cp .env.example .env
# Edit .env with your API keys
```

You need at minimum:
- **GROQ_API_KEY** — free at [console.groq.com](https://console.groq.com)

### 3. Add your company knowledge base
Drop `.txt` files into the `knowledge_base/` folder. They'll be auto-indexed when the app starts.

### 4. Run the Streamlit dashboard
```bash
streamlit run app.py
```

---

## Channel Setup

### WhatsApp (Twilio)
1. Sign up at [twilio.com](https://twilio.com) — free sandbox available
2. Go to Messaging → Try it out → WhatsApp
3. Add `TWILIO_ACCOUNT_SID` and `TWILIO_AUTH_TOKEN` to `.env`
4. Run the bot: `python whatsapp_bot.py`
5. Expose it: `ngrok http 5000`
6. Paste the ngrok URL into Twilio's WhatsApp sandbox webhook

### Telegram
1. Open Telegram → search `@BotFather` → type `/newbot`
2. Follow the prompts → copy the bot token
3. Add `TELEGRAM_BOT_TOKEN` to `.env`
4. Run: `python telegram_bot.py`
5. Find your bot on Telegram and start chatting!

### Web Widget
1. Run the Flask API: `python web_widget.py`
2. Deploy it (Render, Railway, or Fly.io — all free tier)
3. Add this one line to any website's HTML:

```html
<script 
  src="https://your-api-url.com/widget.js"
  data-business="My Business"
  data-color="#2563eb">
</script>
```

That's it! The chat bubble appears bottom-right on the site.

---

## Deploying the Streamlit app

```bash
# 1. Push to GitHub
git init && git add . && git commit -m "AI Support Agent"
git remote add origin https://github.com/yourusername/support-agent.git
git push -u origin main

# 2. Go to share.streamlit.io
# 3. Connect your GitHub repo
# 4. Add environment variables in the Streamlit secrets panel
# 5. Deploy!
```

---

## Customization

### Add more escalation keywords
In `agent_core.py`, edit the `ESCALATE_KEYWORDS` list.

### Change the LLM model
In `agent_core.py`, change `model="llama3-8b-8192"` to any Groq model:
- `llama3-8b-8192` — fastest, free
- `llama3-70b-8192` — smarter, still free
- `mixtral-8x7b-32768` — great for multilingual

### Add a database for tickets
Replace the JSON file saving in `agent_core.py` with a proper DB:
- **SQLite** for local use
- **Supabase** for production (free tier, Nigerian servers available)
- **MongoDB Atlas** for document storage

---

## What's next?

- [ ] Add voice support (WhatsApp voice notes → speech-to-text → AI response)
- [ ] Build an admin dashboard to manage all tickets in one place
- [ ] Add analytics (most common issues, resolution rate, peak hours)
- [ ] Integrate with payment APIs (Paystack, Flutterwave) for billing queries
- [ ] Multi-language support (Pidgin, Yoruba, Igbo, Hausa)
- [ ] Sell this as a SaaS to Nigerian businesses! 💰

---

*Built with LangChain, Groq, ChromaDB, Streamlit — by Pr0_M1se 🚀*
