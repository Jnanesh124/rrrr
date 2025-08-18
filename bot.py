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
import random, asyncio
import os

app = Client(
    "approver",
    api_id=cfg.API_ID,
    api_hash=cfg.API_HASH,
    bot_token=cfg.BOT_TOKEN
)

# List of image URLs
images = [
    'https://storage.teleservices.io/Teleservice_9cecc9a95dba.jpg',
    'https://storage.teleservices.io/Teleservice_bb48095f81f5.jpg',
    'https://storage.teleservices.io/Teleservice_16705d191b64.jpg'
]

#━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ Pending Accept Commands ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

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


@app.on_message(filters.command("stopaccept") & filters.private)
async def stop_accept(_, m: Message):
    user_id = m.from_user.id
    user_name = m.from_user.first_name or "User"

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
            f"👋 **Hi {user_name}!**\n\n"
            f"💡 **Available commands:**\n"
            f"🚀 `/pendingaccept` - Start auto-pending request acceptance\n"
            f"📊 `/stats` - Show statistics\n"
            f"🏠 `/start` - Show welcome message\n"
            f"🧹 `/cleanup` - Force cleanup if stuck"
        )
        return

    # Comprehensive cleanup
    if user_id in auto_accept_running:
        del auto_accept_running[user_id]
    if user_id in pending_channels:
        del pending_channels[user_id]

    # Reset user state to IDLE
    user_states[user_id] = UserState.IDLE

    # Create detailed success message
    success_text = f"✅ **Auto-accept process stopped successfully!**\n\n"
    success_text += f"👋 **Hi {user_name}!**\n\n"
    
    if stopped_channels:
        if len(stopped_channels) == 1:
            success_text += f"🛑 **Stopped processing:** {stopped_channels[0]}\n\n"
        else:
            success_text += f"🛑 **Stopped processing {len(stopped_channels)} channels:**\n"
            for channel in stopped_channels:
                success_text += f"   • {channel}\n"
            success_text += "\n"
    
    success_text += f"📝 **Session cleared** - All data has been reset\n\n"
    success_text += f"💡 **What's next?**\n"
    success_text += f"🚀 Use `/pendingaccept` to start fresh with a new channel\n"
    success_text += f"📊 Use `/stats` to check current status\n"
    success_text += f"🏠 Use `/start` to see the welcome message\n\n"
    success_text += f"🔄 **Ready to start again anytime!**"

    await m.reply_text(success_text)

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
            await send_welcome_message(kk)
        except Exception as welcome_error:
            print(f"⚠️ Welcome message failed, user will get it when they /start: {welcome_error}")

    except errors.ChatAdminRequired:
        print(f"❌ Bot needs admin permissions to approve requests in {op.title}")
    except errors.PeerIdInvalid as e:
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
                await send_welcome_message(new_member)
            except Exception as welcome_error:
                print(f"⚠️ Welcome message failed for new member, they'll get it when they /start: {welcome_error}")

async def send_welcome_message(user):
    """Send welcome message to approved user - works for all users regardless of bot start status"""
    try:
        # Check if bot is connected, if not try to start it
        if not app.is_connected:
            try:
                await app.start()
                print("🔄 Bot connection established for welcome message")
            except Exception as conn_error:
                print(f"❌ Failed to establish bot connection: {conn_error}")
                # Try sending anyway in case bot is actually connected
                pass

        img = random.choice(images)  # Choose a random image

        # Ensure user ID is valid integer
        user_id = int(user.id) if hasattr(user, 'id') else user
        user_name = getattr(user, 'first_name', 'Unknown') or 'Unknown'

        # Create user mention properly
        user_mention = f"[{user_name}](tg://user?id={user_id})"

        welcome_caption = f"**🎉 Hello {user_mention}! Your request has been approved ✔️**\n\n" \
                         f"**Welcome to our community!** 🌟\n\n" \
                         f"📱 **Click /start to unlock amazing features:**\n" \
                         f"• Auto-approve join requests\n" \
                         f"• Channel management tools\n" \
                         f"• Live statistics and more!\n\n" \
                         f"🔗 **Join our channels:**\n" \
                         f"📢 @JNKBACKUP\n" \
                         f"🤖 @JNK_BOTS\n\n" \
                         f"**Enjoy your stay!** 😊"

        # Try to send welcome message - this now works for all users
        try:
            await app.send_photo(
                user_id,  # Send to the user who requested to join
                img,  # The chosen image URL
                caption=welcome_caption
            )
            print(f"📸 Welcome photo sent to {user_name} (ID: {user_id})")

        except (errors.PeerIdInvalid, errors.UserIsBlocked):
            # User hasn't started bot or blocked it - but still add to database
            print(f"⚠️ User {user_name} (ID: {user_id}) hasn't started the bot or blocked it")
            try:
                add_user(user_id)
                print(f"✅ User {user_id} added to database for future welcome")
            except:
                pass

        except Exception as photo_err:
            print(f"⚠️ Error sending welcome photo to {user_name}: {photo_err}")
            # Try sending text message instead
            try:
                await app.send_message(user_id, welcome_caption)
                print(f"💬 Welcome text sent to {user_name} (ID: {user_id})")

            except (errors.PeerIdInvalid, errors.UserIsBlocked):
                print(f"⚠️ User {user_name} (ID: {user_id}) hasn't started the bot")
                # Still add to database even if message fails
                try:
                    add_user(user_id)
                    print(f"✅ User {user_id} added to database")
                except:
                    pass

            except Exception as text_err:
                print(f"❌ Could not send any welcome message to user {user_id}: {text_err}")
                # Still add to database 
                try:
                    add_user(user_id)
                    print(f"✅ User {user_id} added to database")
                except:
                    pass

    except Exception as e:
        print(f"❌ Unexpected error in send_welcome_message: {e}")
        # Still try to add user to database
        try:
            user_id = int(user.id) if hasattr(user, 'id') else user
            add_user(user_id)
            print(f"✅ User {user_id} added to database despite error")
        except:
            pass

#━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ Start ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.on_message(filters.command("start"))
async def op(_, m: Message):
    user_id = m.from_user.id
    user_name = m.from_user.first_name or "there"

    try:
        await app.get_chat_member(cfg.CHID, user_id)

        if m.chat.type == enums.ChatType.PRIVATE:
            add_user(user_id)
            
            # Reset user state to IDLE when using /start - this ensures clean state
            user_states[user_id] = UserState.IDLE

            # Always send full welcome message to all users (whether new or returning)
            welcome_text = f"""**🎉 Welcome back {user_name} to Auto-Approve Bot!**

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

**🚀 Quick Start Guide:**
1️⃣ Use `/pendingaccept` command
2️⃣ Send your channel/group invite link  
3️⃣ Give me admin permissions with "Add Members" right
4️⃣ Click `/admindone` to start the magic! ✨
5️⃣ Watch as all pending requests get approved automatically!

**🔄 Pro Tip:** 
User account automatically rejoins when you use `/pendingaccept` again - no manual setup needed!

**🛡️ Account Protection:**
Your user account will auto-leave channels after processing or 6 hours to prevent Telegram limitations.

**Ready to get started? Try `/pendingaccept` now!** 🚀"""

            # Send welcome with a random image
            try:
                img = random.choice(images)
                await m.reply_photo(
                    photo=img,
                    caption=welcome_text,
                    disable_web_page_preview=False
                )
                print(f"📸 Start command photo sent to {user_name} (ID: {user_id})")
            except Exception as photo_err:
                print(f"⚠️ Start command photo failed for {user_name}: {photo_err}")
                # Fallback to text if image fails
                await m.reply_text(welcome_text, disable_web_page_preview=False)
                print(f"💬 Start command text sent to {user_name} (ID: {user_id})")

        elif m.chat.type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🍿 BACKUP CHANNEL 🍿", url="https://t.me/JNKBACKUP")],
                [InlineKeyboardButton("🤖 BOT UPDATES 🤖", url="https://t.me/JNK_BOTS")],
                [InlineKeyboardButton("💬 Start Bot Privately", url=f"https://t.me/{app.me.username}?start=welcome")]
            ])
            add_group(m.chat.id)
            await m.reply_text(
                f"**👋 Hello {user_name}!**\n\n"
                f"🤖 **I'm an Auto-Approve Bot** that can instantly approve join requests!\n\n"
                f"📱 **Start me privately** to unlock powerful features like:\n"
                f"• Auto-accept pending requests\n"
                f"• Channel management tools\n"
                f"• Live statistics and more!\n\n"
                f"👆 **Click the button below to get started!**",
                reply_markup=keyboard
            )

        print(f"✅ {user_name} (ID: {user_id}) started the bot!")

    except UserNotParticipant:
        # Reset user state even if not joined channel
        user_states[user_id] = UserState.IDLE
        
        key = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔎 Check Again 🚀", callback_data="chk")],
            [InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/{cfg.FSUB}")]
        ])
        await m.reply_text(
            f"**🔒 Hello {user_name}!**\n\n"
            f"**To use this bot, please join our channel first:**\n\n"
            f"📢 **Channel:** @{cfg.FSUB}\n"
            f"🤖 **Bot Updates:** @JNK_BOTS\n\n"
            f"**After joining, click 'Check Again' below! 👇**",
            reply_markup=key
        )

    except Exception as e:
        # Reset user state even on error
        user_states[user_id] = UserState.IDLE
        
        print(f"❌ Error in start command for user {user_id}: {e}")
        await m.reply_text(
            f"**⚠️ Hello {user_name}!**\n\n"
            f"There was a temporary issue. Please try again in a moment.\n\n"
            f"📢 **Main Channel:** @JNKBACKUP\n"
            f"🤖 **Bot Updates:** @JNK_BOTS"
        )

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
                img = random.choice(images)
                await cb.message.edit_media(
                    media={"type": "photo", "media": img, "caption": welcome_text},
                    reply_markup=None
                )
                print(f"📸 Callback welcome photo sent to {user_name} (ID: {user_id})")
            except Exception as photo_err:
                print(f"⚠️ Callback photo failed for {user_name}: {photo_err}")
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

#━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ info ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.on_message(filters.command("users") & filters.user(cfg.SUDO))
async def dbtool(_, m : Message):
    xx = all_users()
    x = all_groups()
    tot = int(xx + x)
    await m.reply_text(text=f"""
🍀 Chats Stats 🍀
🙋‍♂️ Users : `{xx}`
👥 Groups : `{x}`
🚧 Total users & groups : `{tot}` """)

#━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ Broadcast ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.on_message(filters.command("bcast") & filters.user(cfg.SUDO))
async def bcast(_, m: Message):
    allusers = users  # Assuming this is the database containing all users, not just subscribed ones
    lel = await m.reply_text("`⚡️ Processing...`")
    success = 0
    failed = 0
    deactivated = 0
    blocked = 0

    # Loop through all users and attempt to broadcast the message
    for usrs in allusers.find():  # This should fetch all users from the database
        try:
            userid = usrs["user_id"]
            if m.command[0] == "bcast":
                await m.reply_to_message.copy(int(userid))
            success += 1
        except FloodWait as ex:
            await asyncio.sleep(ex.value)
            if m.command[0] == "bcast":
                await m.reply_to_message.copy(int(userid))
        except errors.InputUserDeactivated:
            deactivated += 1
            remove_user(userid)  # Remove the deactivated user from the database
        except errors.UserIsBlocked:
            blocked += 1
        except Exception as e:
            print(e)  # Log the error for further debugging
            failed += 1

    # Send the result summary to the admin
    await lel.edit(f"✅ Successfully broadcasted to `{success}` users.\n"
                   f"❌ Failed to broadcast to `{failed}` users.\n"
                   f"👾 `{blocked}` users have blocked the bot.\n"
                   f"👻 `{deactivated}` users are deactivated.")

#━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ Broadcast Forward ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.on_message(filters.command("fcast") & filters.user(cfg.SUDO))
async def fcast(_, m: Message):
    allusers = users
    lel = await m.reply_text("`⚡️ Processing...`")
    success = 0
    failed = 0
    deactivated = 0
    blocked = 0

    for usrs in allusers.find():
        try:
            userid = usrs["user_id"]
            if m.command[0] == "fcast":
                await m.reply_to_message.forward(int(userid))
            success += 1
        except FloodWait as ex:
            await asyncio.sleep(ex.value)
            if m.command[0] == "fcast":
                await m.reply_to_message.forward(int(userid))
        except errors.InputUserDeactivated:
            deactivated += 1
            remove_user(userid)
        except errors.UserIsBlocked:
            blocked += 1
        except Exception as e:
            print(e)
            failed += 1

    await lel.edit(
        f"✅ Successful to `{success}` users.\n"
        f"❌ Failed to `{failed}` users.\n"
        f"👾 Found `{blocked}` Blocked users.\n"
        f"👻 Found `{deactivated}` Deactivated users."
    )


if __name__ == "__main__":
    # Start user bot first
    if start_user_bot():
        print("✅ User bot started successfully!")
        try:
            print("🚀 Starting main bot...")
            # Start bot and run it indefinitely
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
        except Exception as e:
            print(f"❌ Error running main bot: {e}")