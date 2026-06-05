"""
telegram_bot.py — Telegram bot integration using python-telegram-bot.

Setup:
1. pip install python-telegram-bot groq
2. Open Telegram → search @BotFather → /newbot → copy your token
3. Set env vars: TELEGRAM_BOT_TOKEN, GROQ_API_KEY
4. Run: python telegram_bot.py
"""

import os
import logging
import uuid
import json
import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
from agent_core import SupportAgent

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ── Init agent ────────────────────────────────────────────────────────────────
agent = SupportAgent()
agent.business_name = os.getenv("BUSINESS_NAME", "My Business")

# Load knowledge base docs
KB_FOLDER = "knowledge_base"
if os.path.exists(KB_FOLDER):
    for filename in os.listdir(KB_FOLDER):
        if filename.endswith(".txt"):
            with open(os.path.join(KB_FOLDER, filename)) as f:
                agent.add_document(filename, f.read())
    print(f"✅ Knowledge base loaded from {KB_FOLDER}/")

# In-memory session store (per chat_id)
sessions = {}


# ── /start command ────────────────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.effective_user.first_name or "there"
    keyboard = [
        [InlineKeyboardButton("❓ FAQs", callback_data="faq"),
         InlineKeyboardButton("🎫 Create Ticket", callback_data="ticket")],
        [InlineKeyboardButton("👤 Human Agent", callback_data="human"),
         InlineKeyboardButton("📚 Search Docs", callback_data="docs")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    welcome_text = (
        f"👋 Hi {user_name}! Welcome to *{agent.business_name} Support*.\n\n"
        "I'm your AI assistant. I can:\n"
        "• Answer your questions instantly\n"
        "• Create support tickets\n"
        "• Connect you to a human agent\n"
        "• Search our documentation\n\n"
        "Choose an option below or just type your question!"
    )
    await update.message.reply_text(
        welcome_text,
        parse_mode="Markdown",
        reply_markup=reply_markup
    )
    sessions[update.effective_chat.id] = {"history": []}


# ── /help command ─────────────────────────────────────────────────────────────
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "*Available commands:*\n"
        "/start — Restart the bot\n"
        "/ticket — Create a support ticket\n"
        "/status — Check your ticket status\n"
        "/help — Show this message\n\n"
        "Or just *type any question* and I'll answer it! 🤖"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")


# ── /ticket command ───────────────────────────────────────────────────────────
async def create_ticket_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📝 *Create a Support Ticket*\n\nPlease describe your issue in detail and I'll create a ticket for you.",
        parse_mode="Markdown"
    )
    # Set user in ticket-creation mode
    chat_id = update.effective_chat.id
    if chat_id not in sessions:
        sessions[chat_id] = {"history": []}
    sessions[chat_id]["creating_ticket"] = True


# ── Button callbacks ──────────────────────────────────────────────────────────
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id

    if query.data == "faq":
        await query.message.reply_text(
            "❓ *Frequently Asked Questions*\n\nJust type your question and I'll find the answer!",
            parse_mode="Markdown"
        )
    elif query.data == "ticket":
        await create_ticket_command(update, context)
    elif query.data == "human":
        ref = f"ESC-{str(uuid.uuid4())[:4].upper()}"
        await query.message.reply_text(
            f"👤 *Connecting to Human Agent...*\n\n"
            f"Reference: `{ref}`\n"
            f"Average wait: ~3 minutes.\n\n"
            f"A support agent will message you shortly.",
            parse_mode="Markdown"
        )
        await _notify_team(context, chat_id, "User requested human agent")
    elif query.data == "docs":
        await query.message.reply_text(
            "📚 *Search Documentation*\n\nType your search query and I'll find relevant docs.",
            parse_mode="Markdown"
        )


# ── Handle messages ───────────────────────────────────────────────────────────
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_message = update.message.text

    if chat_id not in sessions:
        sessions[chat_id] = {"history": []}
    session = sessions[chat_id]
    session["history"].append({"role": "user", "content": user_message})

    # Show typing indicator
    await context.bot.send_chat_action(chat_id=chat_id, action="typing")

    # Get AI response
    result = agent.respond(user_message, session["history"])
    reply_text = result["response"]

    # Handle ticket creation
    if result.get("create_ticket") or session.get("creating_ticket"):
        ticket_id = _save_ticket(chat_id, user_message, result)
        reply_text += f"\n\n🎫 *Ticket created:* `{ticket_id}`\nWe'll respond within 24 hours."
        session["creating_ticket"] = False

    # Handle escalation
    if result.get("escalate"):
        ref = f"ESC-{str(uuid.uuid4())[:4].upper()}"
        reply_text += f"\n\n👤 *Escalating to human agent...*\nRef: `{ref}`"
        await _notify_team(context, chat_id, user_message)

    session["history"].append({"role": "assistant", "content": reply_text})

    # Trim history
    if len(session["history"]) > 20:
        session["history"] = session["history"][-20:]

    # Add quick action buttons
    keyboard = [[
        InlineKeyboardButton("🎫 Create Ticket", callback_data="ticket"),
        InlineKeyboardButton("👤 Human Agent", callback_data="human"),
    ]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        reply_text,
        parse_mode="Markdown",
        reply_markup=reply_markup
    )


def _save_ticket(chat_id, issue, result) -> str:
    ticket_id = f"TKT-{str(uuid.uuid4())[:6].upper()}"
    ticket = {
        "id": ticket_id,
        "chat_id": str(chat_id),
        "issue": issue,
        "category": result.get("category", "General"),
        "priority": result.get("priority", "Medium"),
        "status": "Open",
        "created": datetime.datetime.now().isoformat(),
        "channel": "Telegram"
    }
    os.makedirs("tickets", exist_ok=True)
    with open(f"tickets/{ticket_id}.json", "w") as f:
        json.dump(ticket, f, indent=2)
    logger.info(f"Ticket saved: {ticket_id}")
    return ticket_id


async def _notify_team(context, chat_id, message):
    """Notify your support team chat when escalation happens."""
    team_chat_id = os.getenv("TEAM_TELEGRAM_CHAT_ID")
    if team_chat_id:
        await context.bot.send_message(
            chat_id=team_chat_id,
            text=f"🚨 *Escalation Alert*\nChat ID: `{chat_id}`\nMessage: {message[:100]}",
            parse_mode="Markdown"
        )


# ── Error handler ─────────────────────────────────────────────────────────────
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Exception: {context.error}")


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("❌ Set TELEGRAM_BOT_TOKEN environment variable")

    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("ticket", create_ticket_command))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(error_handler)

    print(f"🚀 Telegram bot started for {agent.business_name}")
    print("📌 Press Ctrl+C to stop")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
