from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from pyrogram import filters, Client, errors, enums
from pyrogram.errors import UserNotParticipant
from pyrogram.errors.exceptions.flood_420 import FloodWait
from database import add_user, add_group, all_users, all_groups, users, remove_user, get_all_fsub_channels, get_fsub_channel
from configs import cfg
from user_bot import (user_app, user_states, pending_channels, auto_accept_running,
                     UserState, extract_invite_link_info, check_admin_permissions,
                     get_pending_requests, auto_accept_pending_requests,
                     start_user_bot, stop_user_bot)
import asyncio

app = Client(
    "approver",
    api_id=cfg.API_ID,
    api_hash=cfg.API_HASH,
    bot_token=cfg.BOT_TOKEN
)

#━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ Pending Accept Commands ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@app.on_message(filters.command("addfsub") & filters.private & filters.user(cfg.SUDO))
async def add_fsub_channel_cmd(_, m: Message):
    """Add force subscription channel - Admin only"""
    try:
        if len(m.command) < 2:
            await m.reply_text(
                "**📝 Add Force Subscription Channel**\n\n"
                "**Usage:**\n"
                "`/addfsub <channel_id_or_username> [invite_link]`\n\n"
                "**Examples:**\n"
                "• `/addfsub -1001234567890 https://t.me/+abcdef`\n"
                "• `/addfsub @publicchannel`\n"
                "• `/addfsub -1001234567890` (without invite link)\n\n"
                "**Note:** For private channels, provide invite link for better user experience."
            )
            return

        channel_input = m.command[1]
        invite_link = m.command[2] if len(m.command) > 2 else None

        # Determine if it's a channel ID or username
        if channel_input.startswith("-") or channel_input.isdigit():
            channel_id = int(channel_input)
            channel_type = "private"
        else:
            channel_id = channel_input.replace("@", "")
            channel_type = "public"

        # Check if bot can access the channel for membership verification
        try:
            me = await app.get_me()
            bot_member = await app.get_chat_member(channel_id, me.id)

            permission_msg = ""

            if bot_member.status == "creator":
                permission_msg = "✅ Creator (full access)"
            elif bot_member.status == "administrator":
                permission_msg = "✅ Admin (can check membership)"
            elif bot_member.status in ["member", "restricted"]:
                permission_msg = "✅ Member (can check membership)"
            else:
                permission_msg = "⚠️ Limited access"

            print(f"✅ Bot access verified for {channel_title}: {permission_msg}")

        except errors.UserNotParticipant:
            await m.reply_text(f"❌ **Error:** Bot is not a member of **{channel_title}**\n\nPlease add the bot to the channel first.")
            return
        except errors.PeerIdInvalid:
            await m.reply_text(f"❌ **Error:** Invalid chat ID or username provided for channel: `{channel_input}`")
            return
        except Exception as e:
            print(f"Warning: Could not verify bot access to {channel_title}: {e}")
            permission_msg = "⚠️ Could not verify access"

        # Try to get channel info to display title
        try:
            chat = await app.get_chat(channel_id)
            channel_title = chat.title or f"Channel {channel_id}"
        except Exception as e:
            channel_title = f"Unknown Channel ({channel_id})"
            print(f"Warning: Could not get title for channel {channel_id}: {e}")

        # Add to database
        from database import add_fsub_channel
        success = add_fsub_channel(str(channel_id), channel_title, invite_link, channel_type)

        if success:
            status_text = f"✅ **Force Subscription Channel Added!**\n\n" \
                         f"**Channel:** {channel_title}\n" \
                         f"**ID/Username:** `{channel_id}`\n" \
                         f"**Type:** {channel_type.title()}\n"

            if invite_link:
                status_text += f"**Invite Link:** [Join Here]({invite_link})\n"

            status_text += f"\n**Bot Status:** {permission_msg}\n\n"
            status_text += "💡 Users must now join this channel to use `/pendingaccept`"

            await m.reply_text(status_text, disable_web_page_preview=True)
        else:
            await m.reply_text("❌ **Failed to add channel.** Please try again.")

    except Exception as e:
        await m.reply_text(f"❌ **Error:** {str(e)}")

@app.on_message(filters.command("removefsub") & filters.private & filters.user(cfg.SUDO))
async def remove_fsub_channel_cmd(_, m: Message):
    """Remove force subscription channel - Admin only"""
    try:
        if len(m.command) < 2:
            # Show current channels
            from database import get_all_fsub_channels
            channels = get_all_fsub_channels()

            if not channels:
                await m.reply_text("📝 **No force subscription channels found.**")
                return

            message = "**📝 Current Force Subscription Channels:**\n\n"
            for i, channel in enumerate(channels, 1):
                message += f"{i}. **{channel['channel_title']}**\n"
                message += f"   ID: `{channel['channel_id']}`\n"
                message += f"   Type: {channel.get('channel_type', 'unknown').title()}\n\n"

            message += "**Usage:** `/removefsub <channel_id_or_username>`\n"
            message += "**Example:** `/removefsub -1001234567890`"

            await m.reply_text(message)
            return

        channel_input = m.command[1]

        # Convert to string for database lookup
        if channel_input.startswith("-") or channel_input.isdigit():
            channel_id = str(int(channel_input))
        else:
            channel_id = channel_input.replace("@", "")

        # Get channel info before removing
        from database import get_fsub_channel, remove_fsub_channel
        channel_info = get_fsub_channel(channel_id)

        if not channel_info:
            await m.reply_text(f"❌ **Channel not found:** `{channel_id}`\n\nUse `/removefsub` to see current channels.")
            return

        # Remove from database
        success = remove_fsub_channel(channel_id)

        if success:
            await m.reply_text(
                f"✅ **Force Subscription Channel Removed!**\n\n"
                f"**Channel:** {channel_info.get('channel_title', 'Unknown')}\n"
                f"**ID:** `{channel_id}`\n\n"
                f"Users no longer need to join this channel."
            )
        else:
            await m.reply_text("❌ **Failed to remove channel.** Please try again.")

    except Exception as e:
        await m.reply_text(f"❌ **Error:** {str(e)}")

@app.on_message(filters.command("listfsub") & filters.private & filters.user(cfg.SUDO))
async def list_fsub_channels_cmd(_, m: Message):
    """List all force subscription channels - Admin only"""
    try:
        from database import get_all_fsub_channels
        channels = get_all_fsub_channels()

        if not channels:
            await m.reply_text(
                "📝 **No Force Subscription Channels**\n\n"
                "Use `/addfsub` to add channels.\n\n"
                "**Example:**\n"
                "`/addfsub -1001234567890 https://t.me/+abcdef`"
            )
            return

        message = f"**📝 Force Subscription Channels ({len(channels)})**\n\n"

        # Check bot admin status
        admin_issues = await check_bot_admin_in_fsub()

        for i, channel in enumerate(channels, 1):
            channel_title = channel['channel_title']
            channel_id = channel['channel_id']
            channel_type = channel.get('channel_type', 'unknown')
            invite_link = channel.get('invite_link')

            message += f"**{i}. {channel_title}**\n"
            message += f"   📱 ID: `{channel_id}`\n"
            message += f"   🏷️ Type: {channel_type.title()}\n"

            if invite_link:
                message += f"   🔗 [Invite Link]({invite_link})\n"

            # Check admin status
            admin_status = "✅ Admin" if not any(channel_id in issue for issue in admin_issues) else "❌ Not Admin"
            message += f"   👤 Bot Status: {admin_status}\n\n"

        if admin_issues:
            message += "⚠️ **Admin Issues Found:**\n"
            for issue in admin_issues[:3]:  # Show first 3 issues
                message += f"• {issue}\n"
            if len(admin_issues) > 3:
                message += f"• ...and {len(admin_issues) - 3} more\n"
            message += "\n"

        message += "**Commands:**\n"
        message += "• `/addfsub` - Add channel\n"
        message += "• `/removefsub` - Remove channel"

        await m.reply_text(message, disable_web_page_preview=True)

    except Exception as e:
        await m.reply_text(f"❌ **Error:** {str(e)}")

@app.on_message(filters.private & filters.command('broadcast') & filters.user(cfg.SUDO))
async def send_text(client, message: Message):
    if message.reply_to_message:
        query = await full_userbase()
        broadcast_msg = message.reply_to_message
        total_users = len(query)
        successful = 0
        blocked = 0
        deleted = 0
        unsuccessful = 0
        failure_reasons = {}

        # Initial broadcast status message
        pls_wait = await message.reply(
            f"📡 <b>Live Broadcast Progress</b>\n\n"
            f"👥 <b>Total Users:</b> <code>{total_users}</code>\n"
            f"✅ <b>Sent:</b> <code>0</code>\n"
            f"⏳ <b>Remaining:</b> <code>{total_users}</code>\n"
            f"🚫 <b>Blocked:</b> <code>0</code>\n"
            f"❌ <b>Deleted:</b> <code>0</code>\n"
            f"⚠️ <b>Failed:</b> <code>0</code>\n\n"
            f"📊 <b>Progress:</b> 0.0%\n"
            f"🔄 <b>Status:</b> Starting broadcast..."
        )

        last_update_time = asyncio.get_event_loop().time()

        for index, chat_id in enumerate(query, 1):
            try:
                await broadcast_msg.copy(chat_id)
                successful += 1
            except FloodWait as e:
                await asyncio.sleep(e.value)
                try:
                    await broadcast_msg.copy(chat_id)
                    successful += 1
                except:
                    unsuccessful += 1
            except errors.UserIsBlocked:
                await del_user(chat_id)
                blocked += 1
            except errors.InputUserDeactivated:
                await del_user(chat_id)
                deleted += 1
            except Exception as ex:
                unsuccessful += 1
                # Track failure reasons
                error_type = type(ex).__name__
                error_msg = str(ex)[:50]  # Limit error message length
                failure_key = f"{error_type}: {error_msg}"
                failure_reasons[failure_key] = failure_reasons.get(failure_key, 0) + 1

            # Update progress every 10 messages or every 3 seconds
            current_time = asyncio.get_event_loop().time()
            if index % 10 == 0 or (current_time - last_update_time) >= 3:
                remaining = total_users - index
                progress_percentage = (index / total_users) * 100

                # Determine current status
                if remaining == 0:
                    current_status = "✅ Broadcast completed!"
                elif successful > 0:
                    current_status = f"📤 Broadcasting... (Last: User #{index})"
                else:
                    current_status = "🔄 Processing users..."

                # Build failure reasons text
                failure_text = ""
                if failure_reasons:
                    failure_text = "\n\n📋 <b>Failure Details:</b>\n"
                    for reason, count in list(failure_reasons.items())[:3]:  # Show top 3 failure reasons
                        failure_text += f"• <code>{reason}</code> ({count})\n"
                    if len(failure_reasons) > 3:
                        remaining_failures = sum(list(failure_reasons.values())[3:])
                        failure_text += f"• <i>...and {remaining_failures} other failures</i>\n"

                live_status = (
                    f"📡 <b>Live Broadcast Progress</b>\n\n"
                    f"👥 <b>Total Users:</b> <code>{total_users}</code>\n"
                    f"✅ <b>Sent:</b> <code>{successful}</code>\n"
                    f"⏳ <b>Remaining:</b> <code>{remaining}</code>\n"
                    f"🚫 <b>Blocked:</b> <code>{blocked}</code>\n"
                    f"❌ <b>Deleted:</b> <code>{deleted}</code>\n"
                    f"⚠️ <b>Failed:</b> <code>{unsuccessful}</code>{failure_text}\n\n"
                    f"📊 <b>Progress:</b> {progress_percentage:.1f}%\n"
                    f"🔄 <b>Status:</b> {current_status}"
                )

                try:
                    await pls_wait.edit_text(live_status)
                    last_update_time = current_time
                except:
                    pass  # Continue if edit fails

            # Small delay to prevent flooding
            await asyncio.sleep(0.1)

        # Build detailed failure summary
        failure_summary = ""
        if failure_reasons:
            failure_summary = "\n\n📋 <b>Detailed Failure Analysis:</b>\n"
            for reason, count in failure_reasons.items():
                failure_summary += f"• <code>{reason}</code> - {count} users\n"

        # Final completion status
        final_status = f"""<b><u>📡 Broadcast Completed Successfully!</u></b>

👥 <b>Total Users:</b> <code>{total_users}</code>
✅ <b>Successfully Sent:</b> <code>{successful}</code>
🚫 <b>Blocked Users:</b> <code>{blocked}</code>
❌ <b>Deleted Accounts:</b> <code>{deleted}</code>
⚠️ <b>Unsuccessful:</b> <code>{unsuccessful}</code>{failure_summary}

📈 <b>Success Rate:</b> {(successful/total_users*100):.1f}%
🎯 <b>Status:</b> Broadcast completed!

💡 <b>Note:</b> Blocked and deleted users have been cleaned from database."""

        return await pls_wait.edit_text(final_status)

    else:
        msg = await message.reply("❌ **Reply to a message to broadcast it to all users.**")
        await asyncio.sleep(8)
        await msg.delete()

@app.on_message(filters.command("cleanup") & filters.private)
async def force_cleanup(_, m: Message):
    """Force cleanup user session if stuck"""
    user_id = m.from_user.id

    # Force cleanup all user data
    cleanup_count = 0

    if user_id in auto_accept_running:
        for chat_id in auto_accept_running[user_id]:
            auto_accept_running[user_id][chat_id] = False
        del auto_accept_running[user_id]
        cleanup_count += 1

    if user_id in pending_channels:
        del pending_channels[user_id]
        cleanup_count += 1

    user_states[user_id] = UserState.IDLE
    cleanup_count += 1

    await m.reply_text(
        f"🧹 **Force Cleanup Complete!**\n\n"
        f"✅ Cleaned {cleanup_count} session items\n"
        f"🔄 You can now start fresh with /pendingaccept\n\n"
        f"💡 Use this command if the bot seems stuck or unresponsive."
    )

@app.on_message(filters.command("stats") & filters.private)
async def show_stats(_, m: Message):
    user_id = m.from_user.id

    # Check if user has any pending channel setup
    if user_id not in pending_channels:
        # Show general bot stats instead
        try:
            total_users = all_users()
            total_groups = all_groups()

            # Check if any auto-accept processes are running
            active_processes = 0
            if user_id in auto_accept_running:
                active_processes = sum(1 for running in auto_accept_running[user_id].values() if running)

            general_stats = f"📊 **Bot Statistics**\n\n" \
                           f"👥 **Total Users:** {total_users}\n" \
                           f"🏠 **Total Groups/Channels:** {total_groups}\n" \
                           f"🔄 **Your Active Processes:** {active_processes}\n\n" \
                           f"💡 **To see channel-specific stats:**\n" \
                           f"Use `/pendingaccept` to setup a channel first, then use `/stats` again."

            await m.reply_text(general_stats)
        except Exception as e:
            await m.reply_text(f"📊 **Bot Statistics**\n\n❌ **Error getting statistics:** {str(e)}\n\n💡 Use `/pendingaccept` to setup a channel for detailed stats.")
        return

    chat_info = pending_channels[user_id]
    chat_id = chat_info['chat_id']
    chat_title = chat_info['chat_title']

    try:
        # Create loading message
        loading_msg = await m.reply_text("🔄 **Loading statistics...**")

        # Import the function from user_bot
        from user_bot import get_pending_requests, get_user_info_from_request

        pending_requests = await get_pending_requests(chat_id)
        pending_count = len(pending_requests)

        is_running = auto_accept_running.get(user_id, {}).get(chat_id, False)
        status = "🟢 Active" if is_running else "🔴 Stopped"

        stats_text = f"📊 **Channel Statistics**\n\n" \
                     f"🏠 **Channel:** {chat_title}\n" \
                     f"🆔 **Chat ID:** `{chat_id}`\n" \
                     f"👥 **Pending Requests:** {pending_count}\n" \
                     f"⚡ **Status:** {status}\n\n"

        if pending_requests and len(pending_requests) > 0:
            stats_text += "**👥 Recent Pending Users:**\n"
            for i, request in enumerate(pending_requests[:5]):  # Show first 5
                try:
                    req_user_id, req_user_name = await get_user_info_from_request(request)
                    stats_text += f"{i+1}. {req_user_name or 'Unknown'} (ID: {req_user_id or 'Unknown'})\n"
                except Exception as req_err:
                    stats_text += f"{i+1}. Unknown user (Error: {str(req_err)[:20]}...)\n"

            if len(pending_requests) > 5:
                stats_text += f"... and {len(pending_requests) - 5} more\n\n"

            stats_text += "**📝 Note:** Users with too many channels/groups or deleted accounts will be automatically ignored during processing.\n\n"

            if not is_running:
                stats_text += "💡 **Tip:** Use `/pendingaccept` with your invite link to start processing these requests!"
        else:
            stats_text += "✅ **No pending requests found!**\n\n"
            if not is_running:
                stats_text += "💡 **To start monitoring:** Use `/pendingaccept` with your invite link."

        # Update the loading message with stats
        await loading_msg.edit_text(stats_text)

    except Exception as e:
        error_text = f"❌ **Error getting statistics:** {str(e)}\n\n" \
                    f"🏠 **Channel:** {chat_title}\n" \
                    f"🆔 **Chat ID:** `{chat_id}`\n\n" \
                    f"💡 **Possible solutions:**\n" \
                    f"• Check if you still have admin permissions\n" \
                    f"• Use `/cleanup` to reset session\n" \
                    f"• Try `/pendingaccept` with a fresh invite link"

        try:
            await loading_msg.edit_text(error_text)
        except:
            await m.reply_text(error_text)

@app.on_message(filters.command("stopaccept") & filters.private)
async def stop_accept(_, m: Message):
    user_id = m.from_user.id
    user_name = m.from_user.first_name or "User"

    print(f"🛑 Stop command received from {user_name} (ID: {user_id})")

    try:
        # Check if there are any active processes
        has_active_process = False
        stopped_channels = []

        if user_id in auto_accept_running:
            for chat_id, is_running in auto_accept_running[user_id].items():
                if is_running:
                    has_active_process = True
                    # Get channel name if available
                    channel_name = "Unknown Channel"
                    if user_id in pending_channels and pending_channels[user_id].get('chat_id') == chat_id:
                        channel_name = pending_channels[user_id].get('chat_title', 'Unknown Channel')
                    stopped_channels.append(channel_name)

                    # Stop the process
                    auto_accept_running[user_id][chat_id] = False

        if not has_active_process:
            await m.reply_text(
                f"❌ **No active auto-accept process found!**\n\n"
                f"👋 Hi {user_name}!\n\n"
                f"💡 **Available commands:**\n"
                f"🚀 `/pendingaccept` - Start auto-pending request acceptance\n"
                f"📊 `/stats` - Show statistics\n"
                f"🏠 `/start` - Show welcome message\n"
                f"🧹 `/cleanup` - Force cleanup if stuck"
            )
            print(f"ℹ️ No active process found for {user_name}")
            return

        # Comprehensive cleanup
        if user_id in auto_accept_running:
            del auto_accept_running[user_id]
        if user_id in pending_channels:
            del pending_channels[user_id]

        # Reset user state to IDLE
        user_states[user_id] = UserState.IDLE

        # Simplified success message
        success_text = "✅ **Auto-accept process stopped!**\n\n"
        success_text += f"👋 Hi {user_name}!\n\n"

        if stopped_channels:
            if len(stopped_channels) == 1:
                success_text += f"🛑 Stopped: {stopped_channels[0]}\n\n"
            else:
                success_text += f"🛑 Stopped {len(stopped_channels)} channels\n\n"

        success_text += "📝 Session cleared - All data reset\n\n"
        success_text += "💡 Use `/pendingaccept` to start fresh!\n"
        success_text += "🔄 Ready to start again anytime!"

        await m.reply_text(success_text)
        print(f"✅ Stop command completed for {user_name} (ID: {user_id})")

    except Exception as e:
        print(f"❌ Error in stop command for user {user_id}: {e}")
        try:
            await m.reply_text("✅ Process stopped (with minor issues). Use `/pendingaccept` to start fresh.")
            # Force cleanup even on error
            user_states[user_id] = UserState.IDLE
            if user_id in auto_accept_running:
                del auto_accept_running[user_id]
            if user_id in pending_channels:
                del pending_channels[user_id]
        except:
            print(f"❌ Could not send stop response to {user_id}")

@app.on_message(filters.command("start") & filters.private)
async def start_command(_, m: Message):
    user_id = m.from_user.id
    user_name = m.from_user.first_name or "there"

    # Add user to DB and set state (optional, for your existing logic)
    try:
        add_user(user_id)
    except Exception as e:
        print(f"[START] Could not add user {user_id}: {e}")

    # (Optional) Reset user state to idle if you use states
    try:
        user_states[user_id] = UserState.IDLE
    except Exception:
        pass

    welcome_text = f"""**🎉 Welcome {user_name} to Auto-Approve Bot!**

🤖 **Your Personal Telegram Assistant:**
✅ **Instant Auto-Approval** — Join requests approved immediately
✅ **Smart Pending Requests** — Auto-accept with user account  
✅ **Auto-Leave Protection** — Leaves channels after 6 hours to protect your account
✅ **Live Statistics** — Real-time processing updates
✅ **Smart Session Management** — Never gets stuck!

**📋 Essential Commands:**
🏠 `/start` — Show this welcome message
🚀 `/pendingaccept` — Start auto-pending request acceptance
✅ `/admindone` — Confirm admin permissions 
🛑 `/stopaccept` — Stop auto-acceptance process
📊 `/stats` — Show pending requests statistics
🧹 `/cleanup` — Force cleanup if stuck

**🔗 Official Channels:**
📢 **Main Channel:** @JNKBACKUP
🤖 **Bot Updates:** @JNK_BOTS

**🚀 Quick Start Guide:**
1️⃣ Use `/pendingaccept` command
2️⃣ Send your channel/group invite link  
3️⃣ Give me admin permissions with "Add Members" right
4️⃣ Click `/admindone` to start the magic! ✨
5️⃣ Watch as all pending requests get approved automatically!

**🔄 Pro Tip:** 
User account automatically rejoins when you use `/pendingaccept` again — no manual setup needed!

**🛡️ Account Protection:**
Your user account will auto-leave channels after processing or 6 hours to prevent Telegram limitations.

**Ready to get started? Try `/pendingaccept` now!** 🚀"""

    await m.reply_text(welcome_text, disable_web_page_preview=False)
    print(f"[START] Sent welcome text to {user_id}")

@app.on_message(filters.command("pendingaccept") & filters.private)
async def pending_accept_start(_, m: Message):
    user_id = m.from_user.id
    user_name = m.from_user.first_name or "User"

    add_user(user_id)

    # Check force subscription first
    is_member, not_joined = await check_user_membership(user_id)

    if not is_member:
        # Generate force subscription message
        fsub_message = await generate_fsub_message(user_name, not_joined)

        # Create check again button
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Check Again", callback_data="check_fsub")]
        ])

        await m.reply_text(fsub_message, reply_markup=keyboard, disable_web_page_preview=True)
        return

    # If user is member of all channels, proceed with normal flow
    # Stop any existing auto-accept processes for this user
    if user_id in auto_accept_running:
        for chat_id in auto_accept_running[user_id]:
            auto_accept_running[user_id][chat_id] = False

    # Clear any existing pending channel data
    if user_id in pending_channels:
        del pending_channels[user_id]

    user_states[user_id] = UserState.WAITING_FOR_LINK

    await m.reply_text(
        "**🔗 Send Channel/Group Invite Link**\n\n"
        "Please send the invite link of the channel or group where you want to auto-accept pending requests.\n\n"
        "**Supported formats:**\n"
        "• https://t.me/joinchat/xxxxxx\n"
        "• https://t.me/+xxxxxx\n"
        "• https://telegram.me/joinchat/xxxxxx\n\n"
        "**Note:** Make sure the link is valid and not expired!\n\n"
        "💡 **Tip:** If you used this command before and the user account left the channel, "
        "it will rejoin automatically when you provide the invite link."
    )

@app.on_message(filters.text & filters.private)
async def handle_invite_link(_, m: Message):
    user_id = m.from_user.id

    if user_states.get(user_id) != UserState.WAITING_FOR_LINK:
        return

    invite_link = m.text.strip()
    invite_hash = extract_invite_link_info(invite_link)

    if not invite_hash:
        await m.reply_text(
            "❌ **Invalid invite link!**\n\n"
            "Please send a valid channel/group invite link.\n"
            "Example: https://t.me/joinchat/xxxxxx"
        )
        return

    try:
        # Try to join using user account
        await m.reply_text("🔄 **Attempting to join the channel/group...**")

        try:
            chat = await user_app.join_chat(invite_link)
            chat_id = chat.id
            chat_title = chat.title or "Unknown"

            pending_channels[user_id] = {
                'chat_id': chat_id,
                'chat_title': chat_title,
                'invite_link': invite_link
            }

            user_states[user_id] = UserState.WAITING_FOR_ADMIN_CONFIRMATION

            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ I've given admin permissions", callback_data="admin_done")]
            ])

            await m.reply_text(
                f"✅ **Successfully joined: {chat_title}**\n\n"
                "🛡️ **Next Step:**\n"
                "Please make me an admin in the channel/group with **'Invite Members'** permission.\n\n"
                "After giving admin permissions, click the button below or use /admindone command.",
                reply_markup=keyboard
            )

        except errors.UserAlreadyParticipant:
            # Already in the chat, get chat info
            try:
                chat = await user_app.get_chat(invite_link)
                chat_id = chat.id
                chat_title = chat.title or "Unknown"

                pending_channels[user_id] = {
                    'chat_id': chat_id,
                    'chat_title': chat_title,
                    'invite_link': invite_link
                }

                user_states[user_id] = UserState.WAITING_FOR_ADMIN_CONFIRMATION

                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("✅ I've given admin permissions", callback_data="admin_done")]
                ])

                await m.reply_text(
                    f"✅ **Already joined: {chat_title}**\n\n"
                    "🛡️ **Next Step:**\n"
                    "Please make me an admin in the channel/group with **'Invite Members'** permission.\n\n"
                    "After giving admin permissions, click the button below or use /admindone command.",
                    reply_markup=keyboard
                )

            except Exception as e:
                await m.reply_text(f"❌ **Error getting chat info:** {str(e)}")
                user_states[user_id] = UserState.IDLE

    except errors.InviteHashExpired:
        await m.reply_text("❌ **Invite link has expired!** Please get a new invite link.")
        user_states[user_id] = UserState.IDLE
    except errors.UsernameNotOccupied:
        await m.reply_text("❌ **Invalid username/chat!** The username in the link doesn't exist or the chat is no longer available.")
        user_states[user_id] = UserState.IDLE
    except errors.UsernameInvalid:
        await m.reply_text("❌ **Invalid username format!** Please check the invite link format.")
        user_states[user_id] = UserState.IDLE
    except Exception as e:
        error_msg = str(e).lower()
        if "username_not_occupied" in error_msg:
            await m.reply_text("❌ **Chat not found!** The username/chat in the link doesn't exist or is no longer available.")
        elif "username_invalid" in error_msg:
            await m.reply_text("❌ **Invalid link format!** Please send a valid Telegram invite link.")
        else:
            await m.reply_text(f"❌ **Failed to join:** {str(e)}\n\nPlease check the invite link and try again.")
        user_states[user_id] = UserState.IDLE

@app.on_message(filters.command("admindone") & filters.private)
async def admin_done_command(_, m: Message):
    await handle_admin_done(m.from_user.id, m)

@app.on_callback_query(filters.regex("admin_done"))
async def admin_done_callback(_, cb: CallbackQuery):
    await handle_admin_done(cb.from_user.id, cb.message, cb)

@app.on_callback_query(filters.regex("cancel_setup"))
async def cancel_setup_callback(_, cb: CallbackQuery):
    user_id = cb.from_user.id

    # Clean up user session
    if user_id in auto_accept_running:
        for chat_id in auto_accept_running[user_id]:
            auto_accept_running[user_id][chat_id] = False
        del auto_accept_running[user_id]

    if user_id in pending_channels:
        del pending_channels[user_id]

    user_states[user_id] = UserState.IDLE

    await cb.answer("Setup cancelled!", show_alert=False)
    await cb.message.edit_text("❌ **Setup Cancelled**\n\nYou can start again anytime with /pendingaccept")

@app.on_callback_query(filters.regex("check_fsub"))
async def check_fsub_callback(_, cb: CallbackQuery):
    user_id = cb.from_user.id
    user_name = cb.from_user.first_name or "User"

    # Re-check force subscription
    is_member, not_joined = await check_user_membership(user_id)

    if not is_member:
        # Still not a member, update message with current status
        fsub_message = await generate_fsub_message(user_name, not_joined)

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Check Again", callback_data="check_fsub")]
        ])

        await cb.answer("❌ You're still not a member of all channels!", show_alert=True)
        await cb.message.edit_text(fsub_message, reply_markup=keyboard, disable_web_page_preview=True)
        return

    # User is now a member of all channels
    await cb.answer("✅ Verification successful! You can now use /pendingaccept", show_alert=True)

    success_message = f"**🎉 Verification Successful - {user_name}!**\n\n" \
                     "✅ You are now a member of all required channels!\n\n" \
                     "🚀 **Ready to use bot features:**\n" \
                     "• `/pendingaccept` - Start auto-pending request acceptance\n" \
                     "• `/stats` - Show statistics\n" \
                     "• `/stopaccept` - Stop auto-acceptance process\n\n" \
                     "💡 **Next step:** Use `/pendingaccept` to start!"

    await cb.message.edit_text(success_message)

async def handle_admin_done(user_id, message, callback=None):
    if user_states.get(user_id) != UserState.WAITING_FOR_ADMIN_CONFIRMATION:
        text = "❌ **No pending channel setup found!**\n\nPlease use /pendingaccept first."
        if callback:
            await callback.answer(text, show_alert=True)
        else:
            await message.reply_text(text)
        return

    if user_id not in pending_channels:
        text = "❌ **Channel information not found!**"
        if callback:
            await callback.answer(text, show_alert=True)
        else:
            await message.reply_text(text)
        return

    chat_info = pending_channels[user_id]
    chat_id = chat_info['chat_id']
    chat_title = chat_info['chat_title']

    # Check admin permissions
    try:
        me = await user_app.get_me()

        # Get detailed member info for debugging
        member = await user_app.get_chat_member(chat_id, me.id)
        status_text = f"📋 **Admin Status Check:**\n" \
                     f"👤 **Status:** {member.status}\n"

        if member.status == "administrator" and hasattr(member, 'privileges') and member.privileges:
            can_invite = getattr(member.privileges, 'can_invite_users', False)
            status_text += f"🔹 **Can Invite Users:** {can_invite}\n" \
                          f"🔹 **Can Manage Chat:** {getattr(member.privileges, 'can_manage_chat', 'Unknown')}\n" \
                          f"🔹 **Can Delete Messages:** {getattr(member.privileges, 'can_delete_messages', 'Unknown')}\n\n"

        has_permission = await check_admin_permissions(chat_id, me.id)

        if not has_permission:
            error_text = f"❌ **Admin Permission Check Failed!**\n\n{status_text}" \
                       f"**Required:** Admin with 'Invite Members' permission\n\n" \
                       f"**Solution:** Please ensure you've given me admin rights with the 'Add Members' or 'Invite Users' permission enabled.\n\n" \
                       f"**⚠️ The button will remain until admin permissions are granted.**"

            # Add Try Again button that persists
            retry_keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Try Again", callback_data="admin_done")],
                [InlineKeyboardButton("❌ Cancel Setup", callback_data="cancel_setup")]
            ])

            if callback:
                await callback.answer("❌ Admin permission check failed! Please grant admin rights and try again.", show_alert=True)
                # Don't close the message, keep the buttons active
                try:
                    await message.edit_text(error_text, reply_markup=retry_keyboard)
                except:
                    # If edit fails, send new message
                    await message.reply_text(error_text, reply_markup=retry_keyboard)
            else:
                await message.reply_text(error_text, reply_markup=retry_keyboard)
            return

        # If we reach here, permissions are good
        status_text += "✅ **Permissions verified successfully!**"

        # Get initial pending requests count
        try:
            pending_requests = await get_pending_requests(chat_id)
            pending_count = len(pending_requests)
        except Exception as e:
            pending_count = "Unknown"
            print(f"Error getting pending requests: {e}")

        user_states[user_id] = UserState.AUTO_ACCEPTING

        if user_id not in auto_accept_running:
            auto_accept_running[user_id] = {}
        auto_accept_running[user_id][chat_id] = True

        success_text = f"✅ **Setup Complete!**\n\n" \
                      f"{status_text}\n" \
                      f"🏠 **Channel:** {chat_title}\n" \
                      f"👥 **Pending Requests:** {pending_count}\n\n" \
                      f"🚀 **Starting auto-accept process...**\n\n" \
                      f"Use /stopaccept to stop the process anytime."

        if callback:
            await callback.answer("✅ Setup complete! Starting auto-accept...", show_alert=False)
            await message.edit_text(success_text)
        else:
            await message.reply_text(success_text)

        # Start auto-accepting in background
        asyncio.create_task(auto_accept_pending_requests(app, user_id, chat_id, chat_title))

    except errors.ChatAdminRequired:
        error_text = "❌ **Admin Rights Required!**\n\n" \
                     "I don't have the necessary admin rights in this chat to perform this action.\n" \
                     "Please promote me to admin and grant the 'Add Members' permission."
        if callback:
            await callback.answer("❌ Admin rights missing!", show_alert=True)
            await message.edit_text(error_text)
        else:
            await message.reply_text(error_text)

    except errors.PeerIdInvalid:
        error_text = "❌ **Invalid Chat ID!**\n\nThe chat ID seems to be invalid. Please check the invite link again."
        if callback:
            await callback.answer("❌ Invalid chat ID!", show_alert=True)
            await message.edit_text(error_text)
        else:
            await message.reply_text(error_text)
        user_states[user_id] = UserState.IDLE

    except Exception as e:
        error_text = f"❌ **An unexpected error occurred:** {str(e)}"
        if callback:
            await callback.answer("❌ Error!", show_alert=True)
            await message.edit_text(error_text)
        else:
            await message.reply_text(error_text)
        print(f"Error in handle_admin_done for user {user_id}: {e}")

#━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ Main process ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.on_chat_join_request(filters.group | filters.channel & ~filters.private)
async def approve(_, m: Message):
    op = m.chat
    kk = m.from_user
    try:
        add_group(m.chat.id)

        # Add user to database BEFORE approving so they can receive broadcasts
        add_user(kk.id)
        print(f"👤 Added user {kk.first_name or 'Unknown'} (ID: {kk.id}) to database")

        # Also add to accepted users collection for permanent tracking
        from database import add_accepted_user
        add_accepted_user(kk.id, kk.first_name or 'Unknown', op.title or 'Unknown')

        # Auto-approve the join request
        await app.approve_chat_join_request(op.id, kk.id)
        print(f"✅ Auto-approved join request from {kk.first_name or 'Unknown'} (ID: {kk.id}) in {op.title or 'Unknown'}")

        # Send welcome message with proper delay and error handling
        try:
            await asyncio.sleep(2)  # Longer delay to ensure bot is ready
            await send_welcome_message(kk, op.title or "Unknown Group")
        except Exception as welcome_error:
            print(f"⚠️ Welcome message failed, user will get it when they /start: {welcome_error}")

    except errors.ChatAdminRequired:
        print(f"❌ Bot needs admin permissions to approve requests in {op.title}")
    except errors.PeerIdInvalid:
        print(f"❌ Peer ID invalid for chat {op.id}")
    except Exception as err:
        print(f"❌ Error auto-approving join request: {str(err)}")
        # Log more details for debugging
        print(f"Chat: {op.title} (ID: {op.id})")
        print(f"User: {kk.first_name} (ID: {kk.id})")

# Handle new members joining (after approval)
@app.on_message(filters.new_chat_members)
async def welcome_new_members(_, m: Message):
    """Welcome new members who joined the chat"""
    for new_member in m.new_chat_members:
        if not new_member.is_bot:  # Don't welcome other bots
            print(f"👋 New member joined: {new_member.first_name or 'Unknown'} (ID: {new_member.id})")
            add_user(new_member.id)

            # Send welcome with error handling
            try:
                await asyncio.sleep(2)  # Longer delay for bot readiness
                await send_welcome_message(new_member, m.chat.title or "Unknown Group")
            except Exception as welcome_error:
                print(f"⚠️ Welcome message failed for new member, they'll get it when they /start: {welcome_error}")

async def send_welcome_message(user, group_name="Unknown Group"):
    """Send simple welcome message to approved user and add to database"""
    try:
        # Ensure user ID is valid integer
        user_id = int(user.id) if hasattr(user, 'id') else user
        user_name = getattr(user, 'first_name', 'Unknown') or 'Unknown'

        # Add user to database first
        add_user(user_id)

        # Simple welcome message
        welcome_text = f"**Hi {user_name}! Your request accepted {group_name}**"

        # Try to send welcome message
        try:
            await app.send_message(user_id, welcome_text)
            print(f"💬 Welcome text sent to {user_name} (ID: {user_id})")

        except (errors.PeerIdInvalid, errors.UserIsBlocked):
            print(f"⚠️ User {user_name} (ID: {user_id}) hasn't started the bot or blocked it")
            print(f"✅ User {user_id} added to database for future messages")

        except Exception as text_err:
            print(f"❌ Could not send welcome message to user {user_id}: {text_err}")
            print(f"✅ User {user_id} added to database")

    except Exception as e:
        print(f"❌ Unexpected error in send_welcome_message: {e}")
        # Still try to add user to database
        try:
            user_id = int(user.id) if hasattr(user, 'id') else user
            add_user(user_id)
            print(f"✅ User {user_id} added to database despite error")
        except:
            pass

#━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ callback ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Old CHID callback removed - now using FSUB_CHANNELS only

#━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ Broadcast ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def full_userbase():
    """Get all users from database including previously accepted users"""
    from database import get_all_accepted_users
    return get_all_accepted_users()

async def del_user(user_id):
    """Delete user from database"""
    return remove_user(user_id)

async def check_user_membership(user_id):
    """Check if user is member of all force subscription channels"""
    try:
        fsub_channels = get_all_fsub_channels()
        if not fsub_channels:
            return True, []  # No force sub channels, allow access

        not_joined = []

        for channel in fsub_channels:
            channel_id = channel["channel_id"]
            channel_title = channel["channel_title"]
            invite_link = channel.get("invite_link")

            try:
                # Convert channel_id to int if it's numeric (private channels)
                if channel_id.startswith("-") or channel_id.isdigit():
                    chat_id = int(channel_id)
                else:
                    chat_id = channel_id  # Public channel username

                # Check membership
                member = await app.get_chat_member(chat_id, user_id)

                if member.status in ["left", "kicked"]:
                    not_joined.append({
                        "channel_id": channel_id,
                        "channel_title": channel_title,
                        "invite_link": invite_link
                    })

            except errors.UserNotParticipant:
                not_joined.append({
                    "channel_id": channel_id,
                    "channel_title": channel_title,
                    "invite_link": invite_link
                })
            except Exception as e:
                print(f"Error checking membership for {channel_id}: {e}")
                # If we can't check, assume not joined for safety
                not_joined.append({
                    "channel_id": channel_id,
                    "channel_title": channel_title,
                    "invite_link": invite_link
                })

        is_member_of_all = len(not_joined) == 0
        return is_member_of_all, not_joined

    except Exception as e:
        print(f"Error in check_user_membership: {e}")
        return False, []

async def generate_fsub_message(user_name, not_joined_channels):
    """Generate force subscription message with direct invite links only"""
    try:
        if not not_joined_channels:
            return None

        message = f"**🔒 Access Restricted - {user_name}!**\n\n"
        message += "To use `/pendingaccept` command, you must join all our channels first:\n\n"

        for i, channel in enumerate(not_joined_channels, 1):
            channel_id = channel["channel_id"]
            invite_link = channel.get("invite_link")

            if invite_link:
                # Use provided invite link - direct link only
                message += f"{i}. {invite_link}\n"
            elif not channel_id.startswith("-") and not channel_id.isdigit():
                # Public channel - create t.me link
                username = channel_id.replace("@", "")
                message += f"{i}. https://t.me/{username}\n"
            else:
                # Private channel without invite link - try to generate one
                try:
                    # Convert to int for private channels
                    chat_id_int = int(channel_id)

                    # Try to create invite link if bot is admin
                    try:
                        invite = await app.create_chat_invite_link(chat_id_int)
                        generated_link = invite.invite_link
                        message += f"{i}. {generated_link}\n"

                        # Update database with new invite link
                        from database import add_fsub_channel
                        add_fsub_channel(channel_id, channel.get("channel_title"), generated_link, "private")
                        print(f"✅ Generated invite link for channel {channel_id}: {generated_link}")

                    except Exception as link_err:
                        print(f"❌ Failed to generate invite link for channel {channel_id}: {link_err}")
                        message += f"{i}. Contact admin for invite link\n"

                except Exception as conv_err:
                    print(f"❌ Invalid channel ID format {channel_id}: {conv_err}")
                    message += f"{i}. Contact admin for invite link\n"

        message += "\n**📋 Instructions:**\n"
        message += "1️⃣ Join ALL channels above by clicking the links\n"
        message += "2️⃣ Click **✅ Check Again** button below\n"
        message += "3️⃣ Once verified, you can use `/pendingaccept`\n\n"
        message += "💡 **Note:** You must be a member of all channels to access bot features."

        return message

    except Exception as e:
        print(f"Error generating fsub message: {e}")
        return "**🔒 Access Restricted!**\n\nPlease join our channels to use this bot."

async def check_bot_admin_in_fsub():
    """Check if bot has admin permissions in force sub channels"""
    try:
        fsub_channels = get_all_fsub_channels()
        me = await app.get_me()

        issues = []

        for channel in fsub_channels:
            channel_id = channel["channel_id"]
            channel_title = channel["channel_title"]

            try:
                # Convert channel_id to int if it's numeric
                if channel_id.startswith("-") or channel_id.isdigit():
                    chat_id = int(channel_id)
                else:
                    chat_id = channel_id

                # Check bot's membership
                bot_member = await app.get_chat_member(chat_id, me.id)

                if bot_member.status == "creator":
                    print(f"✅ Bot is creator in {channel_title}")
                elif bot_member.status == "administrator":
                    # For force subscription, we only need to check membership
                    # Bot doesn't need admin rights to check if users are members
                    print(f"✅ Bot is admin in {channel_title}")
                else:
                    # Bot is not admin - but that's OK for membership checking
                    # We can still check if users are members even as a regular member
                    print(f"ℹ️ Bot is regular member in {channel_title} (sufficient for membership checking)")

            except errors.ChatAdminRequired:
                # This means bot can't get member info - might need basic member access
                issues.append(f"❌ {channel_title}: Bot cannot access member list")
            except errors.PeerIdInvalid:
                issues.append(f"❌ {channel_title}: Invalid channel ID")
            except errors.UserNotParticipant:
                issues.append(f"❌ {channel_title}: Bot is not a member")
            except Exception as e:
                error_msg = str(e).lower()
                if "chat_admin_required" in error_msg:
                    issues.append(f"❌ {channel_title}: Bot needs basic access")
                elif "peer_id_invalid" in error_msg:
                    issues.append(f"❌ {channel_title}: Invalid channel ID")
                elif "user_not_participant" in error_msg:
                    issues.append(f"❌ {channel_title}: Bot is not a member")
                else:
                    print(f"⚠️ Could not check {channel_title}: {e}")

        return issues

    except Exception as e:
        print(f"Error checking bot admin status: {e}")
        return [f"Error checking admin status: {e}"]

async def startup_check():
    """Check bot startup and initialize properly"""
    try:
        # Ensure bot is started
        if not app.is_connected:
            print("🔄 Starting main bot connection...")

        # Get bot info to ensure connection
        me = await app.get_me()
        print(f"✅ Main bot connected as: {me.first_name} (@{me.username})")

        # Check bot admin status in force sub channels
        admin_issues = await check_bot_admin_in_fsub()
        if admin_issues:
            print("⚠️ Force subscription admin issues:")
            for issue in admin_issues:
                print(f"  {issue}")

        return True
    except Exception as e:
        print(f"❌ Main bot connection failed: {e}")
        return False

async def initialize_fsub_channels():
    """Initialize force subscription channels from config"""
    try:
        if not cfg.FSUB_CHANNELS:
            print("ℹ️ No force subscription channels configured")
            return

        channels = [ch.strip() for ch in cfg.FSUB_CHANNELS.split(',') if ch.strip()]
        from database import add_fsub_channel

        print(f"🔄 Initializing {len(channels)} force subscription channels...")

        for channel in channels:
            try:
                if channel.startswith('@'):
                    # Public channel
                    channel_username = channel.replace('@', '')
                    try:
                        chat = await app.get_chat(channel_username)
                        add_fsub_channel(channel_username, chat.title, None, "public")
                        print(f"✅ Initialized public channel: {chat.title}")
                    except Exception as e:
                        print(f"⚠️ Could not get info for @{channel_username}: {e}")
                        add_fsub_channel(channel_username, f"@{channel_username}", None, "public")
                        print(f"✅ Added public channel: @{channel_username} (info unavailable)")

                elif channel.startswith('-') or channel.isdigit():
                    # Private channel by ID
                    channel_id = int(channel)
                    try:
                        chat = await app.get_chat(channel_id)
                        # Try to generate invite link if bot is admin
                        invite_link = None
                        try:
                            invite = await app.create_chat_invite_link(channel_id)
                            invite_link = invite.invite_link
                        except:
                            pass  # Bot might not be admin or have permission

                        add_fsub_channel(str(channel_id), chat.title, invite_link, "private")
                        print(f"✅ Initialized private channel: {chat.title}")
                    except Exception as e:
                        print(f"⚠️ Could not get info for channel {channel_id}: {e}")
                        add_fsub_channel(str(channel_id), f"Private Channel {channel_id}", None, "private")
                        print(f"✅ Added private channel: {channel_id} (info unavailable)")
                else:
                    # Invalid format
                    print(f"⚠️ Invalid channel format: {channel}")

            except Exception as e:
                print(f"❌ Error initializing channel {channel}: {e}")

        print(f"✅ Force subscription initialization completed")

    except Exception as e:
        print(f"❌ Error initializing force sub channels: {e}")

if __name__ == "__main__":
    # Start user bot first
    if start_user_bot():
        print("✅ User bot started successfully!")
        try:
            print("🚀 Starting main bot...")
            app.start()

            # Initialize force subscription channels
            import asyncio
            asyncio.get_event_loop().run_until_complete(initialize_fsub_channels())

            # Run startup check
            asyncio.get_event_loop().run_until_complete(startup_check())

            print("✅ Main bot started successfully!")

            # Keep running using the correct method
            try:
                from pyrogram import idle
                idle()
            except ImportError:
                # Fallback for older versions
                try:
                    app.idle()
                except AttributeError:
                    # Manual idle implementation
                    import signal
                    import threading

                    def signal_handler(sig, frame):
                        print("🛑 Stopping bot...")
                        app.stop()
                        stop_user_bot()
                        exit(0)

                    signal.signal(signal.SIGINT, signal_handler)
                    signal.signal(signal.SIGTERM, signal_handler)

                    # Keep the main thread alive
                    event = threading.Event()
                    event.wait()

        except Exception as e:
            print(f"❌ Error running main bot: {e}")
        finally:
            stop_user_bot()  # Clean shutdown of user bot
    else:
        print("❌ Failed to start user bot!")
        print("🚀 Starting main bot anyway...")
        try:
            app.run()  # Start main bot anyway
            print("✅ Main bot started successfully!")
        except Exception as e:
            print(f"❌ Error running main bot: {e}")