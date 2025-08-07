from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from pyrogram import filters, Client, errors, enums
from pyrogram.errors import UserNotParticipant
from pyrogram.errors.exceptions.flood_420 import FloodWait
from database import add_user, add_group, all_users, all_groups, users, remove_user
from configs import cfg
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
            await m.reply_text("**<strong>I'm an auto-approve [Admin Join Requests]({}) Bot. I can approve users in Groups/Channels. Add me to your chat and promote me to admin with add members permission. Join here for\n\nMAIN CHANNEL: @JNKBACKUP\n🎞 BOT UPDATE CHANNEL: @JNK_BOTS</strong>**",disable_web_page_preview=False)
            
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
    app.run()  # This should only be here if you're running locally
