import asyncio
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
import agentscope
from core.orchestrator import ProductBuilderOrchestrator
from core.cost_tracker import cost_tracker
from github import Github
from config.settings import AWS_REGION


# ── Load secrets ─────────────────────────────────────────
def get_secret(name: str) -> str:
    client = boto3.client(
        service_name="secretsmanager",
        region_name=AWS_REGION,
    )
    return client.get_secret_value(SecretId=name)["SecretString"]


from config.settings import TELEGRAM_BOT_TOKEN, TELEGRAM_USER_ID
TELEGRAM_TOKEN = TELEGRAM_BOT_TOKEN
ALLOWED_USER_ID = TELEGRAM_USER_ID

# ── Build state tracking ──────────────────────────────────
build_state = {
    "running": False,
    "current": None,
    "phase": None,
    "history": [],
    "cancelled": False,
}


def is_authorized(update: Update) -> bool:
    return update.effective_user.id == ALLOWED_USER_ID


# ── /start command ────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        await update.message.reply_text("Unauthorized. This is a private bot.")
        return

    await update.message.reply_text(
        "*AgentScope Product Builder*\n\n"
        "Multi-agent system that builds complete multi-service "
        "codebases from your PRD.\n\n"
        "*Agents:*\n"
        "PRD Parser (Opus) | Architect (Opus) | Database\n"
        "API Designer | Planner | Coder | Reviewer | QA\n"
        "Frontend | Integration | DevOps | Docs | GitHub\n\n"
        "*Commands:*\n"
        "/build — Start a new product build\n"
        "/status — Check current build status\n"
        "/repos — List your GitHub repos\n"
        "/cost — Get API cost summary\n"
        "/cancel — Cancel running build\n"
        "/help — Show this message",
        parse_mode="Markdown",
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)


# ── /build command ────────────────────────────────────────
async def build_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        await update.message.reply_text("Unauthorized.")
        return

    if build_state["running"]:
        await update.message.reply_text(
            f"A build is already running.\n"
            f"Building: *{build_state['current'][:60]}...*\n\n"
            f"Use /cancel to stop or /status to check.",
            parse_mode="Markdown",
        )
        return

    await update.message.reply_text(
        "Describe your product (PRD).\n\n"
        "You can send a one-liner or a detailed spec.\n"
        "The more detail, the better the output.",
        parse_mode="Markdown",
    )
    context.user_data["waiting_for_requirement"] = True


# ── Handle text (PRD) ────────────────────────────────────
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        await update.message.reply_text("Unauthorized.")
        return

    if not context.user_data.get("waiting_for_requirement"):
        await update.message.reply_text("Use /build to start or /help for commands.")
        return

    context.user_data["waiting_for_requirement"] = False
    prd = update.message.text.strip()

    if len(prd) < 10:
        await update.message.reply_text("Please provide more detail (at least 10 chars).")
        return

    await update.message.reply_text(
        f"*Starting multi-agent build...*\n\n"
        f"PRD: {prd[:200]}{'...' if len(prd) > 200 else ''}\n\n"
        f"13 agents will work through 9 phases.\n"
        f"This takes 5-15 minutes. I'll notify you when done!",
        parse_mode="Markdown",
    )

    # Run build as async task (no threading needed)
    asyncio.create_task(
        run_build(prd, update.effective_chat.id, context.application)
    )


# ── Async build runner ────────────────────────────────────
async def run_build(prd: str, chat_id: int, app):
    build_state["running"] = True
    build_state["current"] = prd
    build_state["cancelled"] = False

    start_time = datetime.now()

    try:
        orchestrator = ProductBuilderOrchestrator()
        url = await orchestrator.build(prd)

        elapsed = (datetime.now() - start_time).seconds
        usage = cost_tracker.summary()
        minutes, seconds = divmod(elapsed, 60)

        if build_state["cancelled"]:
            message = "Build was cancelled."
        elif url:
            message = (
                f"*Build Complete!*\n\n"
                f"Repo: {url}\n"
                f"Time: {minutes}m {seconds}s\n"
                f"API calls: {usage['total_calls']}\n"
                f"Tokens: {usage['total_tokens']:,}\n"
                f"Cost: {usage['total_cost']}\n\n"
                f"Multi-service codebase is ready!"
            )
            build_state["history"].append({
                "prd": prd[:100],
                "url": url,
                "cost": usage["total_cost"],
                "time": elapsed,
                "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            })
        else:
            message = "*Build blocked by security guardrails.*"

    except Exception as e:
        message = f"*Build failed*\n\nError: {str(e)[:300]}"

    finally:
        build_state["running"] = False
        build_state["current"] = None

    await app.bot.send_message(chat_id=chat_id, text=message, parse_mode="Markdown")


# ── /status command ───────────────────────────────────────
async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return

    if build_state["running"]:
        await update.message.reply_text(
            f"*Build in progress...*\n"
            f"PRD: _{build_state['current'][:60]}..._\n"
            f"Use /cancel to stop.",
            parse_mode="Markdown",
        )
    elif build_state["history"]:
        last = build_state["history"][-1]
        await update.message.reply_text(
            f"*Last build:*\n"
            f"PRD: {last['prd']}...\n"
            f"Repo: {last['url']}\n"
            f"Cost: {last['cost']}",
            parse_mode="Markdown",
        )
    else:
        await update.message.reply_text("No builds yet. Use /build to start.")


# ── /repos command ────────────────────────────────────────
async def repos_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    try:
        token = get_secret("agentscope/github-token")
        g = Github(token)
        repos = list(g.get_user().get_repos(sort="updated"))[:10]
        msg = "*Latest repos:*\n\n"
        for i, repo in enumerate(repos, 1):
            msg += f"{i}. [{repo.name}]({repo.html_url})\n"
        await update.message.reply_text(msg, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")


# ── /cost command ─────────────────────────────────────────
async def cost_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    usage = cost_tracker.summary()
    msg = (
        f"*Cost Summary*\n\n"
        f"API calls: {usage['total_calls']}\n"
        f"Tokens: {usage['total_tokens']:,}\n"
        f"Cost: {usage['total_cost']}\n"
        f"Total builds: {len(build_state['history'])}"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")


# ── /cancel command ───────────────────────────────────────
async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    if build_state["running"]:
        build_state["cancelled"] = True
        await update.message.reply_text("Cancelling build...")
    else:
        await update.message.reply_text("No build running.")


# ── Main ──────────────────────────────────────────────────
def main():
    agentscope.init(
        project="agentscope-product-builder",
        logging_path="./logs",
        logging_level="INFO",
    )

    print("Starting AgentScope Telegram Bot...")
    print(f"Authorized user ID: {ALLOWED_USER_ID}")
    print("13 agents | 9-phase pipeline | AgentScope multi-agent system")

    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("build", build_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("repos", repos_command))
    app.add_handler(CommandHandler("cost", cost_command))
    app.add_handler(CommandHandler("cancel", cancel_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot is running. Send /start on Telegram.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
