import asyncio
import threading
import boto3
from datetime import datetime
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes
)
from core.orchestrator import ProductBuilderOrchestrator
from core.gateway import gateway
from github import Github
from config.settings import AWS_REGION

# ── Load secrets ─────────────────────────────────────────
def get_secret(name: str) -> str:
    client = boto3.client(
        service_name="secretsmanager",
        region_name=AWS_REGION
    )
    return client.get_secret_value(
        SecretId=name
    )["SecretString"]

from config.settings import TELEGRAM_BOT_TOKEN, TELEGRAM_USER_ID
TELEGRAM_TOKEN  = TELEGRAM_BOT_TOKEN
ALLOWED_USER_ID = TELEGRAM_USER_ID

# ── Build state tracking ──────────────────────────────────
build_state = {
    "running": False,
    "current": None,
    "history": [],
    "cancelled": False
}

# ── Auth check ────────────────────────────────────────────
def is_authorized(update: Update) -> bool:
    return update.effective_user.id == ALLOWED_USER_ID

def unauthorized_msg() -> str:
    return "⛔ Unauthorized. This is a private bot."

# ── /start command ────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        await update.message.reply_text(unauthorized_msg())
        return

    await update.message.reply_text(
        "👋 *AgentScope Product Builder*\n\n"
        "I build complete production codebases from your requirements.\n\n"
        "*Commands:*\n"
        "/build — Start a new product build\n"
        "/status — Check current build status\n"
        "/repos — List your GitHub repos\n"
        "/cost — Get API cost summary\n"
        "/cancel — Cancel running build\n"
        "/help — Show this message",
        parse_mode="Markdown"
    )

# ── /help command ─────────────────────────────────────────
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)

# ── /build command ────────────────────────────────────────
async def build_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        await update.message.reply_text(unauthorized_msg())
        return

    if build_state["running"]:
        await update.message.reply_text(
            "⚠️ A build is already running.\n"
            f"Building: *{build_state['current']}*\n\n"
            "Use /cancel to stop it or /status to check progress.",
            parse_mode="Markdown"
        )
        return

    await update.message.reply_text(
        "💬 What do you want to build?\n\n"
        "Just describe your product in plain English.\n"
        "Example: _A SaaS app for tracking invoices with Stripe payments_",
        parse_mode="Markdown"
    )
    context.user_data["waiting_for_requirement"] = True

# ── Handle free text (product requirement) ────────────────
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        await update.message.reply_text(unauthorized_msg())
        return

    if not context.user_data.get("waiting_for_requirement"):
        await update.message.reply_text(
            "Use /build to start a new build or /help for commands."
        )
        return

    context.user_data["waiting_for_requirement"] = False
    requirement = update.message.text.strip()

    if len(requirement) < 10:
        await update.message.reply_text(
            "⚠️ Please describe your product in more detail."
        )
        return

    # Start build in background thread
    await update.message.reply_text(
        f"🚀 *Starting build...*\n\n"
        f"📋 Requirement:\n_{requirement}_\n\n"
        f"⏳ This takes 3-8 minutes depending on project size.\n"
        f"I'll message you when it's done!",
        parse_mode="Markdown"
    )

    # Run build in background so bot stays responsive
    thread = threading.Thread(
        target=run_build_sync,
        args=(requirement, update.effective_chat.id, context.application)
    )
    thread.daemon = True
    thread.start()

# ── Run build in background thread ───────────────────────
def run_build_sync(requirement: str, chat_id: int, app):
    build_state["running"]   = True
    build_state["current"]   = requirement
    build_state["cancelled"] = False

    start_time = datetime.now()

    try:
        orchestrator = ProductBuilderOrchestrator()
        url = orchestrator.build(requirement)

        elapsed = (datetime.now() - start_time).seconds
        usage   = gateway.summary()

        if build_state["cancelled"]:
            message = "🚫 Build was cancelled."
        elif url:
            message = (
                f"✅ *Build Complete!*\n\n"
                f"📦 Repo: {url}\n"
                f"⏱ Time: {elapsed}s\n"
                f"📊 API calls: {usage['total_calls']}\n"
                f"🔢 Tokens: {usage['total_tokens']:,}\n"
                f"💰 Cost: {usage['total_cost']}\n\n"
                f"Your codebase is ready on GitHub!"
            )

            # Save to history
            build_state["history"].append({
                "requirement": requirement,
                "url": url,
                "cost": usage["total_cost"],
                "time": elapsed,
                "date": datetime.now().strftime("%Y-%m-%d %H:%M")
            })
        else:
            message = (
                "❌ *Build blocked by security guardrails.*\n\n"
                "Your requirement was flagged as potentially unsafe.\n"
                "Please provide a legitimate product requirement."
            )

    except Exception as e:
        message = (
            f"❌ *Build failed*\n\n"
            f"Error: {str(e)[:200]}\n\n"
            f"Please try again or check /status"
        )

    finally:
        build_state["running"] = False
        build_state["current"] = None

    # Send result back to Telegram
    asyncio.run(send_message(app, chat_id, message))

async def send_message(app, chat_id: int, text: str):
    await app.bot.send_message(
        chat_id=chat_id,
        text=text,
        parse_mode="Markdown"
    )

# ── /status command ───────────────────────────────────────
async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        await update.message.reply_text(unauthorized_msg())
        return

    if build_state["running"]:
        await update.message.reply_text(
            f"⚙️ *Build in progress...*\n\n"
            f"📋 Building: _{build_state['current']}_\n\n"
            f"Use /cancel to stop.",
            parse_mode="Markdown"
        )
    elif build_state["history"]:
        last = build_state["history"][-1]
        await update.message.reply_text(
            f"✅ *Last build completed*\n\n"
            f"📋 {last['requirement'][:60]}...\n"
            f"📦 {last['url']}\n"
            f"💰 {last['cost']}\n"
            f"🕐 {last['date']}",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            "💤 No builds running or completed yet.\n"
            "Use /build to start one."
        )

# ── /repos command ────────────────────────────────────────
async def repos_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        await update.message.reply_text(unauthorized_msg())
        return

    await update.message.reply_text("🔍 Fetching your repos...")

    try:
        token = get_secret("agentscope/github-token")
        g = Github(token)
        user = g.get_user()
        repos = list(user.get_repos(sort="updated"))[:10]

        if not repos:
            await update.message.reply_text("No repos found.")
            return

        msg = "📦 *Your latest GitHub repos:*\n\n"
        for i, repo in enumerate(repos, 1):
            visibility = "🔒" if repo.private else "🌐"
            msg += f"{i}. {visibility} [{repo.name}]({repo.html_url})\n"

        await update.message.reply_text(msg, parse_mode="Markdown")

    except Exception as e:
        await update.message.reply_text(f"❌ Error fetching repos: {e}")

# ── /cost command ─────────────────────────────────────────
async def cost_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        await update.message.reply_text(unauthorized_msg())
        return

    usage = gateway.summary()

    history_cost = sum(
        float(b["cost"].replace("$", ""))
        for b in build_state["history"]
    ) if build_state["history"] else 0

    msg = (
        f"💰 *Cost Summary*\n\n"
        f"Current session:\n"
        f"  API calls: {usage['total_calls']}\n"
        f"  Tokens: {usage['total_tokens']:,}\n"
        f"  Cost: {usage['total_cost']}\n\n"
        f"Total builds: {len(build_state['history'])}\n"
        f"All-time cost: ${history_cost:.4f}"
    )

    await update.message.reply_text(msg, parse_mode="Markdown")

# ── /cancel command ───────────────────────────────────────
async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        await update.message.reply_text(unauthorized_msg())
        return

    if build_state["running"]:
        build_state["cancelled"] = True
        await update.message.reply_text(
            "🚫 Cancelling build...\n"
            "The current file will finish then the build will stop."
        )
    else:
        await update.message.reply_text("No build is currently running.")

# ── Main ──────────────────────────────────────────────────
def main():
    print("Starting AgentScope Telegram Bot...")
    print(f"Authorized user ID: {ALLOWED_USER_ID}")

    app = Application.builder().token(TELEGRAM_TOKEN).build()

    # Register handlers
    app.add_handler(CommandHandler("start",  start))
    app.add_handler(CommandHandler("help",   help_command))
    app.add_handler(CommandHandler("build",  build_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("repos",  repos_command))
    app.add_handler(CommandHandler("cost",   cost_command))
    app.add_handler(CommandHandler("cancel", cancel_command))
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_message
    ))

    print("Bot is running. Send /start on Telegram.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
