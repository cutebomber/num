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

# ─── CUSTOM EMOJIS ───────────────────────────────────────────────────────────
# Usage: e["bot"], e["tick"], e["cross"], e["tg"], e["diamond"], e["crown"]

def E(emoji_id: str, fallback: str = "·") -> str:
    return f'<tg-emoji emoji-id="{emoji_id}">{fallback}</tg-emoji>'

BOT      = E("5985780596268339498", "🤖")
TICK     = E("5985596818912712352", "✅")
CROSS    = E("5985346521103604145", "❌")
TG       = E("5875465628285931233", "✈")
DIAMOND  = E("6028530359975548369", "💎")
PIRATE   = E("5386372293263892965", "🏴‍☠️")

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

NOT_ALLOWED_MSG = (
    f"{CROSS} <b>Access restricted</b>\n"
    f"──────────────────\n\n"
    f"Free888 is currently invite-only.\n\n"
    f"<i>If you believe you should have access, contact the owner.</i>"
)


NOT_SUBSCRIBED_MSG = (
    f"{TG} <b>One last step</b>\n"
    f"──────────────────\n\n"
    f"Our free trials are exclusive to channel members.\n\n"
    f"Subscribe below to unlock your anonymous number — "
    f"it takes 5 seconds and costs nothing.\n\n"
    f"──────────────────\n"
    f"<i>Already subscribed? Tap</i> <b>Done — Check Me</b>."
)

# ─── MESSAGES ────────────────────────────────────────────────────────────────

WELCOME_MSG = (
    f"{DIAMOND} <b>Free888 — Anonymous Numbers</b>\n"
    f"──────────────────\n\n"
    f"You've been given access to something rare.\n\n"
    f"Our collection of <b>anonymous &amp; collectible</b> Telegram numbers — "
    f"used by people who value privacy, prestige, and identity.\n\n"
    f"{TICK}  Untraceable. Pattern-based. Exclusively yours.\n"
    f"{TICK}  No commitment. No payment. Just 72 hours of luxury.\n"
    f"{TICK}  One free trial, per person, ever.\n\n"
    f"──────────────────\n"
    f"{CROWN}  <i>Claim yours before someone else does.</i>"
)

ABOUT_MSG = (
    f"{CROWN} <b>What makes these numbers special?</b>\n"
    f"──────────────────\n\n"
    f"{PIRATE}  <b>Collectible</b> — exclusively yours for 72 hours.\n"
    f"{TG}  <b>Anonymous</b> — no name, no trace, clean history.\n"
    f"{TICK}  <b>Yours to trial</b> — 72 hours, completely free.\n\n"
    f"──────────────────\n\n"
    f"<b>How it works</b>\n\n"
    f"<b>1.</b> Subscribe to our channel\n"
    f"<b>2.</b> Tap <i>Claim Free Trial</i>\n"
    f"<b>3.</b> Receive your exclusive number instantly\n"
    f"<b>4.</b> Decide if you want to own it permanently\n\n"
    f"──────────────────\n"
    f"<i>Numbers are limited. Trials are first-come, first-served.</i>"
)

# ─── COMMANDS ────────────────────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.ensure_user(user.id, user.username or user.first_name)

    if not db.is_whitelisted(user.id):
        await update.message.reply_text(NOT_ALLOWED_MSG, parse_mode="HTML")
        return

    keyboard = [
        [InlineKeyboardButton("✦  Claim Free Trial", callback_data="claim_trial")],
        [InlineKeyboardButton("◈  My Status", callback_data="my_status"),
         InlineKeyboardButton("◉  About", callback_data="about")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        WELCOME_MSG,
        parse_mode="HTML",
        reply_markup=reply_markup
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"{BOT} <b>Free888Robot</b>\n\n"
        f"/start — Main menu\n"
        f"/status — Check your current trial\n"
        f"/about — How it works\n"
        f"/help — This message",
        parse_mode="HTML"
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
        keyboard = [[InlineKeyboardButton("‹  Back", callback_data="back_home")]]
        await reply(ABOUT_MSG, parse_mode="HTML",
                    reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "back_home":
        keyboard = [
            [InlineKeyboardButton("✦  Claim Free Trial", callback_data="claim_trial")],
            [InlineKeyboardButton("◈  My Status", callback_data="my_status"),
             InlineKeyboardButton("◉  About", callback_data="about")],
        ]
        await reply(WELCOME_MSG, parse_mode="HTML",
                    reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "extend_trial":
        await reply(
            f"{CROWN} <b>Make it permanently yours</b>\n"
            f"──────────────────\n\n"
            f"You've had a taste of what anonymity and prestige feels like.\n\n"
            f"If you'd like to own this number — or choose another from our collection — "
            f"reach out directly and we'll make it happen.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("‹  Back", callback_data="my_status")]]
            )
        )


async def handle_claim(user, reply_fn, context):
    # ── Step 0: Whitelist gate ──
    if not db.is_whitelisted(user.id):
        await reply_fn(NOT_ALLOWED_MSG, parse_mode="HTML")
        return

    # ── Step 1: Channel subscription gate ──
    if not await is_subscribed(user.id, context):
        await reply_fn(
            NOT_SUBSCRIBED_MSG,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✦  Subscribe to Channel", url=CHANNEL_INVITE_LINK)],
                [InlineKeyboardButton("◈  Done — Check Me", callback_data="claim_trial")]
            ])
        )
        return
    existing = db.get_active_trial(user.id)
    if existing:
        expires = datetime.fromisoformat(existing["expires_at"])
        remaining = expires - datetime.utcnow()
        hours = int(remaining.total_seconds() // 3600)
        await reply_fn(
            f"{TICK} <b>Active trial</b>\n\n"
            f"<code>{existing['number']}</code>\n\n"
            f"<i>Expires in {hours}h</i>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("◈  View Status", callback_data="my_status")]]
            )
        )
        return

    if db.has_used_trial(user.id):
        await reply_fn(
            f"{CROSS} <b>Trial already used</b>\n\n"
            f"You've experienced the free trial.\n"
            f"<i>Reach out if you'd like to own a number permanently.</i>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("✦  Get in Touch", callback_data="extend_trial")]]
            )
        )
        return

    number = db.assign_number(user.id)
    if not number:
        await reply_fn(
            f"{CROSS} <b>No numbers available</b>\n\n"
            f"All trials are currently active.\n"
            f"<i>Check back in a few days — slots open as trials expire.</i>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("‹  Home", callback_data="back_home")]]
            )
        )
        return

    expires_at = datetime.utcnow() + timedelta(days=TRIAL_DAYS)

    context.job_queue.run_once(
        notify_expiry,
        when=timedelta(days=TRIAL_DAYS),
        data={"user_id": user.id, "number": number},
        name=f"expire_{user.id}"
    )
    context.job_queue.run_once(
        notify_warning,
        when=timedelta(days=TRIAL_DAYS) - timedelta(hours=12),
        data={"user_id": user.id, "number": number},
        name=f"warn_{user.id}"
    )

    await reply_fn(
        f"{CROWN} <b>Your number is ready</b>\n"
        f"──────────────────\n\n"
        f"Here is your exclusive anonymous number:\n\n"
        f"<code>{number}</code>\n\n"
        f"──────────────────\n\n"
        f"{TICK}  Trial active — 72 hours from now\n"
        f"{DIAMOND}  Expires <b>{expires_at.strftime('%d %b %Y, %H:%M')} UTC</b>\n\n"
        f"<i>You will receive a reminder 12 hours before it expires.\n"
        f"If you love it — it can be yours permanently.</i>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("◈  My Status", callback_data="my_status"),
             InlineKeyboardButton("‹  Home", callback_data="back_home")]
        ])
    )


async def show_status(user_id: int, reply_fn):
    trial = db.get_active_trial(user_id)
    if not trial:
        used = db.has_used_trial(user_id)
        if used:
            msg = (
                f"{CROSS} <b>Trial expired</b>\n\n"
                f"Your 72-hour window has closed.\n"
                f"<i>Contact us to own a number permanently.</i>"
            )
            keyboard = [[InlineKeyboardButton("✦  Get in Touch", callback_data="extend_trial")]]
        else:
            msg = (
                f"{DIAMOND} <b>No active trial</b>\n\n"
                f"<i>You haven't claimed yours yet.</i>"
            )
            keyboard = [[InlineKeyboardButton("✦  Claim Free Trial", callback_data="claim_trial")]]

        await reply_fn(msg, parse_mode="HTML",
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
        f"{TICK} <b>Your active trial</b>\n"
        f"──────────────────\n\n"
        f"<b>Number</b>\n"
        f"<code>{trial['number']}</code>\n\n"
        f"<b>Time remaining</b>\n"
        f"<code>{progress_bar}</code>\n"
        f"{days}d {hours}h {mins}m left\n\n"
        f"──────────────────\n"
        f"{DIAMOND}  <i>Expires {expires.strftime('%d %b %Y, %H:%M')} UTC</i>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("‹  Home", callback_data="back_home")]
        ])
    )


# ─── SCHEDULED JOBS ──────────────────────────────────────────────────────────

async def notify_warning(context: ContextTypes.DEFAULT_TYPE):
    data = context.job.data
    try:
        await context.bot.send_message(
            chat_id=data["user_id"],
            text=(
                f"{DIAMOND} <b>12 hours left on your trial</b>\n"
                f"──────────────────\n\n"
                f"Your anonymous number\n"
                f"<code>{data['number']}</code>\n"
                f"expires in 12 hours.\n\n"
                f"──────────────────\n"
                f"{CROWN}  <i>Loved the experience? Reach out and keep it forever.</i>"
            ),
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("✦  Keep This Number", callback_data="extend_trial")]]
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
                f"{CROSS} <b>Your trial has ended</b>\n"
                f"──────────────────\n\n"
                f"<code>{data['number']}</code> has been returned to the pool.\n\n"
                f"We hope you felt what true anonymity is like.\n\n"
                f"──────────────────\n"
                f"{CROWN}  <i>This number — or another from our collection — "
                f"can still be yours permanently.</i>"
            ),
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("✦  Own a Number", callback_data="extend_trial")]]
            )
        )
    except Exception as e:
        logger.error(f"Expiry notification failed: {e}")


# ─── ADMIN COMMANDS ───────────────────────────────────────────────────────────

async def admin_allow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) not in ADMIN_IDS:
        return
    if not context.args:
        await update.message.reply_text("Usage: /allow &lt;user_id&gt; [note]", parse_mode="HTML")
        return
    user_id = int(context.args[0])
    note = " ".join(context.args[1:]) if len(context.args) > 1 else ""
    db.add_to_whitelist(user_id, note=note)
    await update.message.reply_text(f"✅ User <code>{user_id}</code> whitelisted.", parse_mode="HTML")


async def admin_revoke(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) not in ADMIN_IDS:
        return
    if not context.args:
        await update.message.reply_text("Usage: /revoke &lt;user_id&gt;", parse_mode="HTML")
        return
    user_id = int(context.args[0])
    db.remove_from_whitelist(user_id)
    await update.message.reply_text(f"🚫 User <code>{user_id}</code> revoked.", parse_mode="HTML")


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
    app.add_handler(CommandHandler("allow", admin_allow))
    app.add_handler(CommandHandler("revoke", admin_revoke))
    app.add_handler(CommandHandler("addnumber", admin_add_number))
    app.add_handler(CommandHandler("listnumbers", admin_list_numbers))
    app.add_handler(CommandHandler("stats", admin_stats))

    # Buttons
    app.add_handler(CallbackQueryHandler(button_handler))

    logger.info("🚀 LuxNumbers Bot is running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
