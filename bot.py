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

gif = [    
    'https://graph.org/file/a8a0e8eb4b05399ef9eec.mp4',
    'https://graph.org/file/a8a0e8eb4b05399ef9eec.mp4'
]


#━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ Main process ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.on_chat_join_request(filters.group | filters.channel & ~filters.private)
async def approve(_, m: Message):
    op = m.chat
    kk = m.from_user
    try:
        # Check if the user is already a participant
        chat_member = await app.get_chat_member(op.id, kk.id)
        if chat_member.status in ["member", "administrator", "creator"]:
            print(f"User {kk.first_name} is already a participant of the chat.")
            return

        # Approve the join request
        await app.approve_chat_join_request(op.id, kk.id)
        
        # Send a personalized message to the user
        await app.send_message(
            kk.id,
            f"**Hello Your request to join the channel has been approved.\n\n click /start to see magick**"
        )
        add_user(kk.id)
    except errors.UserAlreadyParticipant:
        print(f"User {kk.first_name} is already a participant of the chat.")
    except errors.PeerIdInvalid:
        print("User hasn't started the bot (likely in a group).")
    except Exception as err:
        print(f"An unexpected error occurred: {err}")   
 
#━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ Start ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.on_message(filters.command("start"))
async def op(_, m: Message):
    try:
        await app.get_chat_member(cfg.CHID, m.from_user.id) 
        
        # If the chat type is private
        if m.chat.type == enums.ChatType.PRIVATE:    
            add_user(m.from_user.id)
            keyboard = InlineKeyboardMarkup(
                [
                    [InlineKeyboardButton("🔔 Main Update Channel 🔔", url="http://t.me/JN2FLIX")],  # First row: 1 button
                    [  # Second row: 2 buttons
                        InlineKeyboardButton("🎥 OTT RELEASEAD MOVIES 🎥", url="https://t.me/+klclyvlnGlEyZWFl"),
                        InlineKeyboardButton("🔞 ADULT SEX VIDEO 🔞", url="https://t.me/+qBu1Y-tOm-1lYWY1")
                    ],
                    [InlineKeyboardButton("🤖 BOT UPDATE CHANNEL 🤖", url="http://t.me/ROCKERSBACKUP")]  # Last row: 1 button
                ]
            )
            await m.reply_text(
                "**<strong>I'm an auto approve  Bot. I can approve users in Groups/Channels. Add me to your chat and promote me to admin with add members permission.</strong>**",
                reply_markup=keyboard
            )
        
        # If the chat type is a group or supergroup
        elif m.chat.type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
            keyboard = InlineKeyboardMarkup(
                [
                    [InlineKeyboardButton("🍿 BOT BACKUP CHANNEL 🍿", url="http://t.me/ROCKERSBACKUP")]
                ]
            )
            add_group(m.chat.id)
            await m.reply_text(
                "**Hello! Start me in private for more details: @ROCKERSBACKUP**",
                reply_markup=keyboard
            )
        
        print(f"{m.from_user.first_name} has started your bot!")

    except UserNotParticipant:
        key = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("🔎 Check Again 🚀", "chk")
                ]
            ]
        )
        await m.reply_text("**<strong>Hello {}  its good to see u again\n\n⚠️Access Denied!⚠️\n\n🍿Subscribe my youtube channel\n\nLink :- https://youtube.com/@jnstudiomovies?si=LNje6Wl7NF-vDDq0\n\nAnd join BOT backupChannel\n\nLINK :- ©️@ROCKERSBACKUP\n\nIf you joined click check again button to confirm.</strong>**".format(cfg.FSUB), reply_markup=key)

#━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ callback ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.on_callback_query(filters.regex("chk"))
async def chk(_, cb : CallbackQuery):
    try:
        await app.get_chat_member(cfg.CHID, cb.from_user.id)
        if cb.message.chat.type == enums.ChatType.PRIVATE:            
            add_user(cb.from_user.id)
            await cb.message.edit("**<strong>I'm an auto approve [Admin Join Requests]({}) Bot.I can approve users in Groups/Channels.Add me to your chat and promote me to admin with add members permission join here for\n\n@Rockers_Bots\n\nBOT BACKUP CHANNEL :- @ROCKERSBACKUP</strong>**")
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
async def fcast(_, m : Message):
    allusers = users
    lel = await m.reply_text("`⚡️ Processing...`")
    success = 0
    failed = 0
    deactivated = 0
    blocked = 0
    for usrs in allusers.find():
        try:
            userid = usrs["user_id"]
            #print(int(userid))
            if m.command[0] == "fcast":
                await m.reply_to_message.forward(int(userid))
            success +=1
        except FloodWait as ex:
            await asyncio.sleep(ex.value)
            if m.command[0] == "fcast":
                await m.reply_to_message.forward(int(userid))
        except errors.InputUserDeactivated:
            deactivated +=1
            remove_user(userid)
        except errors.UserIsBlocked:
            blocked +=1
        except Exception as e:
            print(e)
            failed +=1

    await lel.edit(f"✅Successfull to `{success}` users.\n❌ Faild to `{failed}` users.\n👾 Found `{blocked}` Blocked users \n👻 Found `{deactivated}` Deactivated users.")

if __name__ == "__main__":
    app.run()  # This is for running locally, not needed for Gunicorn
