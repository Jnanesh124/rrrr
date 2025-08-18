from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from pyrogram import filters, Client, errors, enums
from pyrogram.errors import UserNotParticipant
from pyrogram.errors.exceptions.flood_420 import FloodWait
from database import add_user, add_group, all_users, all_groups, users, remove_user
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
@app.on_message(filters.private & filters.command('broadcast') & filters.user(cfg.SUDO))
async def send_text(client, message: Message):
    if message.reply_to_message:
        query = await full_userbase()
        broadcast_msg = message.reply_to_message
        total = 0
        successful = 0
        blocked = 0
        deleted = 0
        unsuccessful = 0

        pls_wait = await message.reply("<i>Broadcasting Message.. This will Take Some Time</i>")
        for chat_id in query:
            try:
                await broadcast_msg.copy(chat_id)
                successful += 1
            except FloodWait as e:
                await asyncio.sleep(e.value)
                await broadcast_msg.copy(chat_id)
                successful += 1
            except errors.UserIsBlocked:
                await del_user(chat_id)
                blocked += 1
            except errors.InputUserDeactivated:
                await del_user(chat_id)
                deleted += 1
            except:
                unsuccessful += 1
                pass
            total += 1

        status = f"""<b><u>Broadcast Completed</u>

Total Users: <code>{total}</code>
Successful: <code>{successful}</code>
Blocked Users: <code>{blocked}</code>
Deleted Accounts: <code>{deleted}</code>
Unsuccessful: <code>{unsuccessful}</code></b>"""

        return await pls_wait.edit(status)

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
    add_user(user_id)

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
            status_text += f"🔹 **Can Invite Users:** {member.privileges.can_invite_users}\n" \
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

        # Auto-approve the join request
        await app.approve_chat_join_request(op.id, kk.id)
        print(f"✅ Auto-approved join request from {kk.first_name or 'Unknown'} (ID: {kk.id}) in {op.title or 'Unknown'}")

        # Add user to database immediately
        add_user(kk.id)

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

#━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ callback ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.on_callback_query(filters.regex("chk"))
async def chk(_, cb : CallbackQuery):
    user_id = cb.from_user.id
    user_name = cb.from_user.first_name or "there"
    
    try:
        await app.get_chat_member(cfg.CHID, user_id)
        if cb.message.chat.type == enums.ChatType.PRIVATE:
            add_user(user_id)
            # Reset user state to IDLE when user joins via callback
            user_states[user_id] = UserState.IDLE

            # Send full welcome message when user joins
            welcome_text = f"""**🎉 Welcome {user_name} to Auto-Approve Bot!**

Thanks for joining our channel! 🎊

🤖 **Your Personal Telegram Assistant:**
✅ **Instant Auto-Approval** - Join requests approved immediately
✅ **Smart Pending Requests** - Auto-accept with user account  
✅ **Auto-Leave Protection** - Leaves channels after 6 hours to protect your account
✅ **Live Statistics** - Real-time processing updates
✅ **Smart Session Management** - Never gets stuck!

**📋 Essential Commands:**
🏠 `/start` - Show this welcome message
🚀 `/pendingaccept` - Start auto-pending request acceptance
✅ `/admindone` - Confirm admin permissions 
🛑 `/stopaccept` - Stop auto-acceptance process
📊 `/stats` - Show pending requests statistics
🧹 `/cleanup` - Force cleanup if stuck

**🔗 Official Channels:**
📢 **Main Channel:** @JNKBACKUP
🤖 **Bot Updates:** @JNK_BOTS

**Ready to get started? Try `/pendingaccept` now!** 🚀"""

            try:
                await cb.message.edit_text(welcome_text)
                print(f"💬 Callback welcome text sent to {user_name} (ID: {user_id})")
            except Exception as text_err:
                print(f"❌ Could not edit message for {user_name}: {text_err}")
                # Try sending new message as fallback
                try:
                    await cb.message.reply_text(welcome_text)
                except:
                    pass

        print(f"✅ {user_name} (ID: {user_id}) joined via callback and started the bot!")
        await cb.answer("✅ Welcome! You're now verified and can use all bot features!", show_alert=False)
        
    except UserNotParticipant:
        await cb.answer("🙅‍♂️ You are not joined to channel, join and try again. 🙅‍♂️", show_alert=True)
    except Exception as e:
        print(f"❌ Error in callback for user {user_id}: {e}")
        await cb.answer("⚠️ Something went wrong. Please try /start command.", show_alert=True)

#━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ Broadcast ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def full_userbase():
    """Get all users from database"""
    user_docs = users.find({})
    user_list = []
    for doc in user_docs:
        user_list.append(int(doc["user_id"]))
    return user_list

async def del_user(user_id):
    """Delete user from database"""
    return remove_user(user_id)

@app.on_message(filters.private & filters.command('broadcast') & filters.user(cfg.SUDO))
async def send_text(client, message: Message):
    if message.reply_to_message:
        query = await full_userbase()
        broadcast_msg = message.reply_to_message
        total = 0
        successful = 0
        blocked = 0
        deleted = 0
        unsuccessful = 0
        
        pls_wait = await message.reply("<i>Broadcasting Message.. This will Take Some Time</i>")
        for chat_id in query:
            try:
                await broadcast_msg.copy(chat_id)
                successful += 1
            except FloodWait as e:
                await asyncio.sleep(e.value)
                await broadcast_msg.copy(chat_id)
                successful += 1
            except errors.UserIsBlocked:
                await del_user(chat_id)
                blocked += 1
            except errors.InputUserDeactivated:
                await del_user(chat_id)
                deleted += 1
            except:
                unsuccessful += 1
                pass
            total += 1
        
        status = f"""<b><u>Broadcast Completed</u>

Total Users: <code>{total}</code>
Successful: <code>{successful}</code>
Blocked Users: <code>{blocked}</code>
Deleted Accounts: <code>{deleted}</code>
Unsuccessful: <code>{unsuccessful}</code></b>"""
        
        return await pls_wait.edit(status)

    else:
        msg = await message.reply("❌ **Reply to a message to broadcast it to all users.**")
        await asyncio.sleep(8)
        await msg.delete()


async def startup_check():
    """Check bot startup and initialize properly"""
    try:
        # Ensure bot is started
        if not app.is_connected:
            print("🔄 Starting main bot connection...")
        
        # Get bot info to ensure connection
        me = await app.get_me()
        print(f"✅ Main bot connected as: {me.first_name} (@{me.username})")
        return True
    except Exception as e:
        print(f"❌ Main bot connection failed: {e}")
        return False

if __name__ == "__main__":
    # Start user bot first
    if start_user_bot():
        print("✅ User bot started successfully!")
        try:
            print("🚀 Starting main bot...")
            # Run startup check first, then run bot
            app.run()
            print("✅ Main bot started successfully!")
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