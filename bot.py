"""
LuxBot — Free 3-Day Collectible Number Trial Bot
Author: Your Name
"""

import logging
import asyncio
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ContextTypes, JobQueue
)
from database import Database
from config import BOT_TOKEN, ADMIN_IDS, TRIAL_DAYS, BOT_USERNAME, REQUIRED_CHANNEL, CHANNEL_INVITE_LINK

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

db = Database()

# ─── HELPERS ─────────────────────────────────────────────────────────────────

async def is_subscribed(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Returns True if the user is a member of REQUIRED_CHANNEL."""
    try:
        member = await context.bot.get_chat_member(
            chat_id=f"@{REQUIRED_CHANNEL}", user_id=user_id
        )
        return member.status in ("member", "administrator", "creator")
    except Exception:
        return False

NOT_SUBSCRIBED_MSG = (
    "🔒 *Channel Subscription Required*\n\n"
    "To claim your free trial on *Free888Robot*, you must first join our channel.\n\n"
    "👇 Join below, then tap ✅ *Check Subscription* to continue."
)

# ─── MESSAGES ────────────────────────────────────────────────────────────────

WELCOME_MSG = """
✨ *Welcome to Free888Robot* ✨

You've just stepped into an exclusive world of *anonymous & collectible Telegram numbers*.

These aren't ordinary numbers — they're rare, prestigious fragments of digital identity.

For a limited time, you can claim a *FREE 3-day trial* and experience:
• 🔒 Complete anonymity
• 💎 Exclusive collectible number
• 👑 Premium feel — zero commitment

Ready to feel what luxury anonymity is like?
"""

ABOUT_MSG = """
💎 *About Free888Robot*

Our collection includes:
• 🔢 *Collectible Numbers* — rare patterns (111, 777, 888 etc.)
• 🕵️ *Anonymous Numbers* — untraceable, clean history
• 📛 *Premium Usernames* — short, memorable handles

*How the trial works:*
1. Join our channel 📢
2. Claim your free number
3. Use it for 3 full days
4. Decide if you want to keep it

One trial per user. Numbers are limited.
"""

# ─── COMMANDS ────────────────────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.ensure_user(user.id, user.username or user.first_name)

    keyboard = [
        [InlineKeyboardButton("💎 Claim Free Trial", callback_data="claim_trial")],
        [InlineKeyboardButton("📋 My Status", callback_data="my_status"),
         InlineKeyboardButton("ℹ️ About", callback_data="about")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        WELCOME_MSG,
        parse_mode="Markdown",
        reply_markup=reply_markup
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 *LuxNumbers Bot Commands*\n\n"
        "/start — Main menu\n"
        "/status — Check your current trial\n"
        "/about — Learn about our numbers\n"
        "/help — This message\n\n"
        "Questions? Contact @" + ADMIN_IDS[0] if ADMIN_IDS else "the admin.",
        parse_mode="Markdown"
    )


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_status(update.effective_user.id, update.message.reply_text)


# ─── CALLBACKS ───────────────────────────────────────────────────────────────

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    data = query.data

    async def reply(text, **kwargs):
        await query.edit_message_text(text, **kwargs)

    if data == "claim_trial":
        await handle_claim(user, reply, context)

    elif data == "my_status":
        await show_status(user.id, reply)

    elif data == "about":
        keyboard = [[InlineKeyboardButton("⬅️ Back", callback_data="back_home")]]
        await reply(ABOUT_MSG, parse_mode="Markdown",
                    reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "back_home":
        keyboard = [
            [InlineKeyboardButton("💎 Claim Free Trial", callback_data="claim_trial")],
            [InlineKeyboardButton("📋 My Status", callback_data="my_status"),
             InlineKeyboardButton("ℹ️ About", callback_data="about")],
        ]
        await reply(WELCOME_MSG, parse_mode="Markdown",
                    reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "extend_trial":
        await reply(
            "💼 *Interested in keeping your number?*\n\n"
            "Send a message to our team and we'll work out a deal just for you.\n\n"
            "Contact: @YourUsername",  # Replace with your actual username
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("⬅️ Back", callback_data="my_status")]]
            )
        )


async def handle_claim(user, reply_fn, context):
    # ── Step 1: Channel subscription gate ──
    if not await is_subscribed(user.id, context):
        await reply_fn(
            NOT_SUBSCRIBED_MSG,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📢 Join Channel", url=CHANNEL_INVITE_LINK)],
                [InlineKeyboardButton("✅ Check Subscription", callback_data="claim_trial")]
            ])
        )
        return
    existing = db.get_active_trial(user.id)
    if existing:
        expires = datetime.fromisoformat(existing["expires_at"])
        remaining = expires - datetime.utcnow()
        hours = int(remaining.total_seconds() // 3600)
        await reply_fn(
            f"⚠️ *You already have an active trial!*\n\n"
            f"📱 Your number: `{existing['number']}`\n"
            f"⏳ Expires in: *{hours} hours*\n\n"
            f"Enjoy your experience! ✨",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("📋 View Status", callback_data="my_status")]]
            )
        )
        return

    if db.has_used_trial(user.id):
        await reply_fn(
            "🔒 *Trial already used*\n\n"
            "You've already experienced a free trial.\n"
            "Loved it? Contact us to get your own number permanently! 💎",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("💬 Contact to Buy", callback_data="extend_trial")]]
            )
        )
        return

    number = db.assign_number(user.id)
    if not number:
        await reply_fn(
            "😔 *No numbers available right now*\n\n"
            "All our collectible numbers are currently on trial.\n"
            "Check back soon — trials expire every 3 days!",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("🏠 Home", callback_data="back_home")]]
            )
        )
        return

    expires_at = datetime.utcnow() + timedelta(days=TRIAL_DAYS)

    # Schedule expiry notification
    context.job_queue.run_once(
        notify_expiry,
        when=timedelta(days=TRIAL_DAYS),
        data={"user_id": user.id, "number": number},
        name=f"expire_{user.id}"
    )

    # Schedule 12h warning
    context.job_queue.run_once(
        notify_warning,
        when=timedelta(days=TRIAL_DAYS) - timedelta(hours=12),
        data={"user_id": user.id, "number": number},
        name=f"warn_{user.id}"
    )

    await reply_fn(
        f"🎉 *Your trial is now LIVE!*\n\n"
        f"📱 *Your Collectible Number:*\n`{number}`\n\n"
        f"⏳ *Trial Duration:* {TRIAL_DAYS} days\n"
        f"📅 *Expires:* {expires_at.strftime('%d %b %Y, %H:%M')} UTC\n\n"
        f"Feel the luxury. Feel the anonymity. 👑\n\n"
        f"_You'll get a reminder 12 hours before expiry._",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📋 My Status", callback_data="my_status")],
            [InlineKeyboardButton("💬 Keep This Number", callback_data="extend_trial")]
        ])
    )


async def show_status(user_id: int, reply_fn):
    trial = db.get_active_trial(user_id)
    if not trial:
        used = db.has_used_trial(user_id)
        if used:
            msg = (
                "📭 *No active trial*\n\n"
                "Your previous trial has expired.\n"
                "Want to own a number permanently? Let's talk! 💎"
            )
            keyboard = [[InlineKeyboardButton("💬 Get My Number", callback_data="extend_trial")]]
        else:
            msg = (
                "📭 *No active trial*\n\n"
                "You haven't claimed your free trial yet!\n"
                "Grab one now — it's completely free. ✨"
            )
            keyboard = [[InlineKeyboardButton("💎 Claim Free Trial", callback_data="claim_trial")]]

        await reply_fn(msg, parse_mode="Markdown",
                       reply_markup=InlineKeyboardMarkup(keyboard))
        return

    expires = datetime.fromisoformat(trial["expires_at"])
    remaining = expires - datetime.utcnow()
    total_secs = remaining.total_seconds()
    days = int(total_secs // 86400)
    hours = int((total_secs % 86400) // 3600)
    mins = int((total_secs % 3600) // 60)

    progress_filled = max(0, TRIAL_DAYS - days - 1)
    progress_bar = "█" * progress_filled + "░" * (TRIAL_DAYS - progress_filled)

    await reply_fn(
        f"📱 *Your Active Trial*\n\n"
        f"Number: `{trial['number']}`\n\n"
        f"⏳ Time Remaining:\n"
        f"`{progress_bar}`\n"
        f"*{days}d {hours}h {mins}m* left\n\n"
        f"📅 Expires: {expires.strftime('%d %b %Y, %H:%M')} UTC",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("💬 Keep This Number", callback_data="extend_trial")],
            [InlineKeyboardButton("⬅️ Main Menu", callback_data="back_home")]
        ])
    )


# ─── SCHEDULED JOBS ──────────────────────────────────────────────────────────

async def notify_warning(context: ContextTypes.DEFAULT_TYPE):
    data = context.job.data
    try:
        await context.bot.send_message(
            chat_id=data["user_id"],
            text=(
                f"⏰ *12 Hours Left on Your Trial!*\n\n"
                f"Your number `{data['number']}` expires in 12 hours.\n\n"
                f"Loved the experience? Contact us to keep it! 💎"
            ),
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("💬 Keep My Number", callback_data="extend_trial")]]
            )
        )
    except Exception as e:
        logger.error(f"Warning notification failed: {e}")


async def notify_expiry(context: ContextTypes.DEFAULT_TYPE):
    data = context.job.data
    db.expire_trial(data["user_id"])
    try:
        await context.bot.send_message(
            chat_id=data["user_id"],
            text=(
                f"⌛ *Your Trial Has Ended*\n\n"
                f"Number `{data['number']}` has been returned to the pool.\n\n"
                f"How was your experience? Want to own a premium number? Let's talk! 👑"
            ),
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("💬 Get My Own Number", callback_data="extend_trial")]]
            )
        )
    except Exception as e:
        logger.error(f"Expiry notification failed: {e}")


# ─── ADMIN COMMANDS ───────────────────────────────────────────────────────────

async def admin_add_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) not in ADMIN_IDS:
        return
    if not context.args:
        await update.message.reply_text("Usage: /addnumber +1234567890 [label]")
        return
    number = context.args[0]
    label = " ".join(context.args[1:]) if len(context.args) > 1 else "Collectible"
    db.add_number(number, label)
    await update.message.reply_text(f"✅ Added number: `{number}` ({label})", parse_mode="Markdown")


async def admin_list_numbers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) not in ADMIN_IDS:
        return
    numbers = db.list_all_numbers()
    if not numbers:
        await update.message.reply_text("No numbers in pool.")
        return
    lines = []
    for n in numbers:
        status = f"🟢 Available" if not n["assigned_to"] else f"🔴 In trial (user {n['assigned_to']})"
        lines.append(f"`{n['number']}` — {n['label']} — {status}")
    await update.message.reply_text(
        "📋 *Number Pool:*\n\n" + "\n".join(lines),
        parse_mode="Markdown"
    )


async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) not in ADMIN_IDS:
        return
    stats = db.get_stats()
    await update.message.reply_text(
        f"📊 *Bot Stats*\n\n"
        f"👥 Total users: {stats['total_users']}\n"
        f"🔢 Total numbers: {stats['total_numbers']}\n"
        f"✅ Active trials: {stats['active_trials']}\n"
        f"📦 Available numbers: {stats['available_numbers']}\n"
        f"📅 Trials completed: {stats['completed_trials']}",
        parse_mode="Markdown"
    )


# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # User commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("status", status_command))

    # Admin commands
    app.add_handler(CommandHandler("addnumber", admin_add_number))
    app.add_handler(CommandHandler("listnumbers", admin_list_numbers))
    app.add_handler(CommandHandler("stats", admin_stats))

    # Buttons
    app.add_handler(CallbackQueryHandler(button_handler))

    logger.info("🚀 LuxNumbers Bot is running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
