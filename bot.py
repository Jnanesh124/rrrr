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

    user_states[user_id] = UserState.WAITING_FOR_LINK

    await m.reply_text(
        "**🔗 Send Channel/Group Invite Link**\n\n"
        "Please send the invite link of the channel or group where you want to auto-accept pending requests.\n\n"
        "**Supported formats:**\n"
        "• https://t.me/joinchat/xxxxxx\n"
        "• https://t.me/+xxxxxx\n"
        "• https://telegram.me/joinchat/xxxxxx\n\n"
        "**Note:** Make sure the link is valid and not expired!"
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
                chat = await user_app.get_chat(invite_hash)
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
    except Exception as e:
        await m.reply_text(f"❌ **Failed to join:** {str(e)}\n\nPlease check the invite link and try again.")
        user_states[user_id] = UserState.IDLE

@app.on_message(filters.command("admindone") & filters.private)
async def admin_done_command(_, m: Message):
    await handle_admin_done(m.from_user.id, m)

@app.on_callback_query(filters.regex("admin_done"))
async def admin_done_callback(_, cb: CallbackQuery):
    await handle_admin_done(cb.from_user.id, cb.message, cb)

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
                       f"**Solution:** Please ensure you've given me admin rights with the 'Add Members' or 'Invite Users' permission enabled."

            if callback:
                await callback.answer("❌ Admin permission check failed!", show_alert=True)
                await message.edit_text(error_text)
            else:
                await message.reply_text(error_text)
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

    if user_id not in auto_accept_running or not any(auto_accept_running[user_id].values()):
        await m.reply_text("❌ **No active auto-accept process found!**")
        return

    # Stop all auto-accept processes for this user
    for chat_id in auto_accept_running[user_id]:
        auto_accept_running[user_id][chat_id] = False

    user_states[user_id] = UserState.IDLE

    await m.reply_text("✅ **Auto-accept process stopped successfully!**")

@app.on_message(filters.command("stats") & filters.private)
async def show_stats(_, m: Message):
    user_id = m.from_user.id

    if user_id not in pending_channels:
        await m.reply_text("❌ **No channel setup found!**\n\nUse /pendingaccept to setup a channel first.")
        return

    chat_info = pending_channels[user_id]
    chat_id = chat_info['chat_id']
    chat_title = chat_info['chat_title']

    try:
        pending_requests = await get_pending_requests(chat_id)
        pending_count = len(pending_requests)

        is_running = auto_accept_running.get(user_id, {}).get(chat_id, False)
        status = "🟢 Active" if is_running else "🔴 Stopped"

        stats_text = f"📊 **Channel Statistics**\n\n" \
                     f"🏠 **Channel:** {chat_title}\n" \
                     f"👥 **Pending Requests:** {pending_count}\n" \
                     f"⚡ **Status:** {status}\n\n"

        if pending_requests and len(pending_requests) > 0:
            stats_text += "**👥 Recent Pending Users:**\n"
            for i, request in enumerate(pending_requests[:5]):  # Show first 5
                user_name = request.from_user.first_name or "Unknown"
                stats_text += f"{i+1}. {user_name}\n"

            if len(pending_requests) > 5:
                stats_text += f"... and {len(pending_requests) - 5} more"

        await m.reply_text(stats_text)

    except Exception as e:
        await m.reply_text(f"❌ **Error getting statistics:** {str(e)}")

#━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ Main process ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.on_chat_join_request(filters.group | filters.channel & ~filters.private)
async def approve(_, m: Message):
    op = m.chat
    kk = m.from_user
    try:
        add_group(m.chat.id)
        await app.approve_chat_join_request(op.id, kk.id)
        img = random.choice(images)  # Choose a random image
        await app.send_photo(
            kk.id,  # Send to the user who requested to join
            img,  # The chosen image URL
            caption="**Hello {}  your request has been approved ✔️ \n\nClick /start \n\n©️@JNKBACKUP @JNK_BOTS**".format(
                m.from_user.mention
            )
        )
        add_user(kk.id)
    except errors.PeerIdInvalid as e:
        print("User hasn't started the bot (or is from a group)")
    except Exception as err:
        print(str(err))

#━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ Start ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.on_message(filters.command("start"))
async def op(_, m :Message):
    try:
        await app.get_chat_member(cfg.CHID, m.from_user.id)
        if m.chat.type == enums.ChatType.PRIVATE:
            add_user(m.from_user.id)
            user_states[m.from_user.id] = UserState.IDLE

            welcome_text = """**🎉 Welcome to Auto-Approve Bot!**

🤖 **Bot Features:**
✅ Auto-approve join requests
✅ Auto-accept pending requests with user account
✅ Live statistics and logs

**📋 Available Commands:**
/start - Show this welcome message
/pendingaccept - Start auto-pending request acceptance
/admindone - Confirm admin permissions and start auto-accept
/stopaccept - Stop auto-acceptance process
/stats - Show pending requests statistics

**🔗 Channels:**
📢 MAIN CHANNEL: @JNKBACKUP
🤖 BOT UPDATE CHANNEL: @JNK_BOTS

**🚀 To get started with pending request acceptance:**
1. Click /pendingaccept
2. Send your channel/group invite link
3. Click /admindone after giving admin permissions
4. Watch the magic happen! ✨"""

            await m.reply_text(welcome_text, disable_web_page_preview=False)

        elif m.chat.type == enums.ChatType.GROUP or enums.ChatType.SUPERGROUP:
            keyboar = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton("🍿BACKUP CHANNEL🍿", url="http://t.me/JNKBACKUP")
                    ]
                ]
            )
            add_group(m.chat.id)
            await m.reply_text("** Hello start me private for more details @JNKBACKUP**")
        print(m.from_user.first_name +" Is started Your Bot!")

    except UserNotParticipant:
        key = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("🔎 Check Again 🚀", "chk")
                ]
            ]
        )
        await m.reply_text("**<strong>Hello {}  its good to see u again\n join below all channel\n\n@JNK_BOTS\n©@JNKBACKUP</strong>**".format(cfg.FSUB), reply_markup=key)

#━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ callback ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.on_callback_query(filters.regex("chk"))
async def chk(_, cb : CallbackQuery):
    try:
        await app.get_chat_member(cfg.CHID, cb.from_user.id)
        if cb.message.chat.type == enums.ChatType.PRIVATE:
            add_user(cb.from_user.id)
            await cb.message.edit("**<strong>I'm an auto approve [Admin Join Requests]({}) Bot.I can approve users in Groups/Channels.Add me to your chat and promote me to admin with add members permission join here for\n\nMAIN UPDATE CHANNEL :- @JNKBACKUP\nBOT UPDATE CHANNEL :- @JNK_BOTS</strong>**")
        print(cb.from_user.first_name +" Is started Your Bot!")
    except UserNotParticipant:
        await cb.answer("🙅‍♂️ You are not joined to channel join and try again. 🙅‍♂️")

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
            app.run()  # Start main bot
        finally:
            stop_user_bot()  # Clean shutdown of user bot
    else:
        print("❌ Failed to start user bot!")
        app.run()  # Start main bot anyway