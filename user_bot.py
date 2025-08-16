
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
        
        # If user is creator, they have all permissions
        if member.status == "creator":
            return True
            
        # If user is administrator, check their privileges
        if member.status == "administrator":
            # If privileges object exists, check can_invite_users
            if hasattr(member, 'privileges') and member.privileges:
                # Check if can_invite_users is explicitly True
                if member.privileges.can_invite_users is True:
                    return True
                    
                # If can_invite_users is None, check if user has general admin permissions
                # None typically means "all permissions" in Telegram
                if member.privileges.can_invite_users is None:
                    # Check if they have other admin permissions that indicate full admin access
                    admin_checks = [
                        getattr(member.privileges, 'can_manage_chat', None),
                        getattr(member.privileges, 'can_delete_messages', None),
                        getattr(member.privileges, 'can_restrict_members', None),
                        getattr(member.privileges, 'can_promote_members', None)
                    ]
                    
                    # If most permissions are None (indicating full access) or True, allow
                    none_count = sum(1 for perm in admin_checks if perm is None)
                    true_count = sum(1 for perm in admin_checks if perm is True)
                    
                    if none_count >= 2 or true_count >= 2:
                        return True
                        
                # For administrators without invite permission explicitly set to False
                if member.privileges.can_invite_users is not False:
                    return True
                    
            else:
                # If no privileges object exists, assume full admin permissions
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
        print(f"Error getting pending requests: {e}")
        return []

async def auto_accept_pending_requests(bot_app, user_id, chat_id, chat_title):
    """Automatically accept all pending requests"""
    try:
        accepted_count = 0
        failed_count = 0
        
        # Send initial status
        await bot_app.send_message(user_id, f"🔄 **Starting auto-accept for {chat_title}...**\n\n📊 **Live Status:**\n✅ Accepted: {accepted_count}\n❌ Failed: {failed_count}")
        
        status_msg = None
        while auto_accept_running.get(user_id, {}).get(chat_id, False):
            try:
                pending_requests = await get_pending_requests(chat_id)
                
                if not pending_requests:
                    await asyncio.sleep(5)  # Wait 5 seconds before checking again
                    continue
                
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
                
    except Exception as e:
        await bot_app.send_message(user_id, f"❌ **Error in auto-accept process:** {str(e)}")
    
    # Final summary
    final_text = f"✅ **Auto-accept completed for {chat_title}!**\n\n📊 **Final Statistics:**\n✅ Total Accepted: {accepted_count}\n❌ Total Failed: {failed_count}"
    
    try:
        if status_msg:
            await status_msg.edit_text(final_text)
        else:
            await bot_app.send_message(user_id, final_text)
    except:
        await bot_app.send_message(user_id, final_text)

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
