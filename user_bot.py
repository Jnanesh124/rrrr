
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram.errors import FloodWait, UserAlreadyParticipant, InviteHashExpired, ChatAdminRequired
from configs import cfg
import asyncio
import re

# User client with string session
user_app = Client(
    "user_session",
    api_id=cfg.API_ID,
    api_hash=cfg.API_HASH,
    session_string=cfg.USER_SESSION
)

# Store user states
user_states = {}
pending_channels = {}
auto_accept_running = {}

class UserState:
    IDLE = 0
    WAITING_FOR_LINK = 1
    WAITING_FOR_ADMIN_CONFIRMATION = 2
    AUTO_ACCEPTING = 3

def extract_invite_link_info(invite_link):
    """Extract channel/group info from invite link"""
    # First check if it's a valid telegram link
    if not any(domain in invite_link.lower() for domain in ['t.me', 'telegram.me']):
        return None
    
    patterns = [
        r't\.me/joinchat/([A-Za-z0-9_-]+)',
        r't\.me/\+([A-Za-z0-9_-]+)',
        r'telegram\.me/joinchat/([A-Za-z0-9_-]+)',
        r'telegram\.me/\+([A-Za-z0-9_-]+)',
        r't\.me/([A-Za-z0-9_]+)',  # For public channels/groups
        r'telegram\.me/([A-Za-z0-9_]+)'  # For public channels/groups
    ]
    
    for pattern in patterns:
        match = re.search(pattern, invite_link)
        if match:
            return match.group(1)
    return None

async def check_admin_permissions(chat_id, user_id):
    """Check if user has admin permissions with invite members permission"""
    try:
        member = await user_app.get_chat_member(chat_id, user_id)
        
        # Check different status types
        status_str = str(member.status).lower()
        
        # If user is creator, they have all permissions
        if "creator" in status_str or member.status == "creator":
            return True
            
        # If user is administrator, check their privileges
        if "administrator" in status_str or member.status == "administrator":
            
            # Try different approaches to check privileges
            try:
                # Method 1: Check if privileges object exists and has can_invite_users
                if hasattr(member, 'privileges') and member.privileges is not None:
                    can_invite = getattr(member.privileges, 'can_invite_users', None)
                    
                    # If can_invite_users is explicitly True
                    if can_invite is True:
                        return True
                    
                    # If can_invite_users is None, it often means all permissions
                    if can_invite is None:
                        # Check if user has other admin permissions
                        other_perms = [
                            getattr(member.privileges, 'can_manage_chat', None),
                            getattr(member.privileges, 'can_delete_messages', None),
                            getattr(member.privileges, 'can_restrict_members', None),
                            getattr(member.privileges, 'can_promote_members', None),
                            getattr(member.privileges, 'can_change_info', None)
                        ]
                        
                        # Count permissions that are True or None (indicating allowed)
                        allowed_perms = sum(1 for perm in other_perms if perm in [True, None])
                        
                        # If user has multiple admin permissions, likely has invite permission too
                        if allowed_perms >= 2:
                            return True
                    
                    # Only return False if can_invite_users is explicitly False
                    if can_invite is False:
                        return False
                    
                    # If we reach here and user is admin, allow it
                    return True
                    
                else:
                    # No privileges object means likely full admin access
                    return True
                    
            except Exception as privilege_error:
                print(f"Error checking privileges: {privilege_error}")
                # If there's an error checking privileges but user is admin, allow it
                return True
                
        return False
        
    except Exception as e:
        print(f"Error checking admin permissions: {e}")
        return False

async def get_pending_requests(chat_id):
    """Get pending join requests for a chat"""
    try:
        pending_requests = []
        async for request in user_app.get_chat_join_requests(chat_id):
            pending_requests.append(request)
        return pending_requests
    except Exception as e:
        error_msg = str(e).lower()
        if "chat_admin_required" in error_msg:
            print(f"Admin permission needed for chat {chat_id}")
        elif "channel_private" in error_msg:
            print(f"Channel/group {chat_id} is not accessible")
        else:
            print(f"Error getting pending requests: {e}")
        return []

async def auto_accept_pending_requests(bot_app, user_id, chat_id, chat_title):
    """Automatically accept all pending requests and leave when done"""
    try:
        accepted_count = 0
        failed_count = 0
        
        # Send initial status
        await bot_app.send_message(user_id, f"🔄 **Starting auto-accept for {chat_title}...**\n\n📊 **Live Status:**\n✅ Accepted: {accepted_count}\n❌ Failed: {failed_count}")
        
        status_msg = None
        consecutive_empty_checks = 0
        
        while auto_accept_running.get(user_id, {}).get(chat_id, False):
            try:
                pending_requests = await get_pending_requests(chat_id)
                
                if not pending_requests:
                    consecutive_empty_checks += 1
                    # If no pending requests for 3 consecutive checks (15 seconds), consider done
                    if consecutive_empty_checks >= 3:
                        break
                    await asyncio.sleep(5)  # Wait 5 seconds before checking again
                    continue
                
                # Reset counter if we found pending requests
                consecutive_empty_checks = 0
                
                for request in pending_requests:
                    if not auto_accept_running.get(user_id, {}).get(chat_id, False):
                        break
                        
                    try:
                        await user_app.approve_chat_join_request(chat_id, request.from_user.id)
                        accepted_count += 1
                        
                        # Update live status every 5 accepts or every 10 seconds
                        if accepted_count % 5 == 0:
                            status_text = f"🔄 **Auto-accepting for {chat_title}...**\n\n📊 **Live Status:**\n✅ Accepted: {accepted_count}\n❌ Failed: {failed_count}\n\n👤 **Last Accepted:** {request.from_user.first_name or 'Unknown'}"
                            
                            if status_msg:
                                try:
                                    await status_msg.edit_text(status_text)
                                except:
                                    status_msg = await bot_app.send_message(user_id, status_text)
                            else:
                                status_msg = await bot_app.send_message(user_id, status_text)
                        
                        await asyncio.sleep(1)  # Small delay to avoid flood
                        
                    except FloodWait as e:
                        await asyncio.sleep(e.value)
                    except Exception as e:
                        failed_count += 1
                        print(f"Failed to accept request: {e}")
                
                await asyncio.sleep(3)  # Wait before next batch check
                
            except Exception as e:
                print(f"Error in auto-accept loop: {e}")
                await asyncio.sleep(5)
        
        # Auto-leave the channel/group after completing all requests
        try:
            await user_app.send_message(
                chat_id, 
                "✅ **All pending requests have been processed!**\n\n"
                "📋 **Summary:**\n"
                f"✅ Accepted: {accepted_count}\n"
                f"❌ Failed: {failed_count}\n\n"
                "🚪 **I'm leaving now.** If you need to process requests again, "
                "use `/pendingaccept` command and send the invite link to rejoin.\n\n"
                "**Thank you for using Auto-Approve Bot!** 🤖"
            )
            await asyncio.sleep(2)  # Wait a moment before leaving
            
            # Leave the chat
            await user_app.leave_chat(chat_id)
            
            # Notify the bot user about successful completion and leaving
            final_text = f"✅ **Auto-accept completed for {chat_title}!**\n\n📊 **Final Statistics:**\n✅ Total Accepted: {accepted_count}\n❌ Total Failed: {failed_count}\n\n🚪 **User account has left the channel.**\n\n💡 **To process requests again:** Use `/pendingaccept` and send the invite link to rejoin."
            
        except Exception as leave_error:
            print(f"Error leaving chat: {leave_error}")
            # If leaving fails, still show completion message
            final_text = f"✅ **Auto-accept completed for {chat_title}!**\n\n📊 **Final Statistics:**\n✅ Total Accepted: {accepted_count}\n❌ Total Failed: {failed_count}\n\n⚠️ **Note:** Could not leave the channel automatically. You may leave manually if needed."
                
    except Exception as e:
        await bot_app.send_message(user_id, f"❌ **Error in auto-accept process:** {str(e)}")
        final_text = f"❌ **Process ended with error for {chat_title}**\n\n📊 **Statistics:**\n✅ Accepted: {accepted_count}\n❌ Failed: {failed_count}"
    
    # Send final status
    try:
        if status_msg:
            await status_msg.edit_text(final_text)
        else:
            await bot_app.send_message(user_id, final_text)
    except:
        await bot_app.send_message(user_id, final_text)
    
    # Clean up the running state
    if user_id in auto_accept_running and chat_id in auto_accept_running[user_id]:
        auto_accept_running[user_id][chat_id] = False
    
    # Remove from pending channels so user can start fresh with /pendingaccept
    if user_id in pending_channels:
        del pending_channels[user_id]
    
    # Reset user state to idle
    user_states[user_id] = UserState.IDLE

def start_user_bot():
    """Start the user bot"""
    try:
        user_app.start()
        print("User bot started successfully!")
        return True
    except Exception as e:
        print(f"Failed to start user bot: {e}")
        return False

def stop_user_bot():
    """Stop the user bot"""
    try:
        user_app.stop()
        print("User bot stopped successfully!")
    except Exception as e:
        print(f"Error stopping user bot: {e}")

# Export functions and client for use in main bot
__all__ = ['user_app', 'user_states', 'pending_channels', 'auto_accept_running', 
           'UserState', 'extract_invite_link_info', 'check_admin_permissions', 
           'get_pending_requests', 'auto_accept_pending_requests', 
           'start_user_bot', 'stop_user_bot']
