
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

async def get_user_info_from_request(request):
    """Extract user info from different request object types"""
    try:
        # Handle different request object types
        if hasattr(request, 'user'):
            # ChatJoinRequest object
            return request.user.id, request.user.first_name or "Unknown"
        elif hasattr(request, 'from_user'):
            # Some other format
            return request.from_user.id, request.from_user.first_name or "Unknown"
        elif hasattr(request, 'user_id'):
            # Direct user_id format
            try:
                user = await user_app.get_users(request.user_id)
                return user.id, user.first_name or "Unknown"
            except:
                return request.user_id, "Unknown"
        else:
            # Fallback - try to get ID from the request object directly
            user_id = getattr(request, 'id', None) or getattr(request, 'user_id', None)
            if user_id:
                try:
                    user = await user_app.get_users(user_id)
                    return user.id, user.first_name or "Unknown"
                except:
                    return user_id, "Unknown"
            return None, None
    except Exception as e:
        print(f"Error extracting user info from request: {e}")
        return None, None

async def auto_accept_pending_requests(bot_app, user_id, chat_id, chat_title):
    """Automatically accept all pending requests and leave when done"""
    try:
        accepted_count = 0
        failed_count = 0
        ignored_count = 0
        accepted_users = []  # Store accepted users for notification
        processed_users = set()  # Track processed user IDs to avoid duplicates
        
        # First, fetch and display all pending requests
        initial_msg = await bot_app.send_message(user_id, f"🔍 **Fetching pending requests for {chat_title}...**")
        
        initial_requests = await get_pending_requests(chat_id)
        total_initial = len(initial_requests)
        
        if total_initial == 0:
            await initial_msg.edit_text(f"📋 **No pending requests found for {chat_title}**\n\n✅ All users are already approved!")
            # Auto-leave even if no requests found
            try:
                await user_app.send_message(chat_id, "📋 **No pending requests found. Leaving the channel now.**")
                await asyncio.sleep(2)
                await user_app.leave_chat(chat_id)
                await bot_app.send_message(user_id, f"🚪 **User account has left {chat_title} (no pending requests found)**")
            except Exception as leave_error:
                print(f"Error leaving chat after no requests: {leave_error}")
                await bot_app.send_message(user_id, f"⚠️ **Could not leave {chat_title} automatically**")
            return
        
        # Show initial pending requests list
        request_list = "📋 **Pending Requests Found:**\n\n"
        for i, request in enumerate(initial_requests[:10]):  # Show first 10
            req_user_id, req_user_name = await get_user_info_from_request(request)
            if req_user_id:
                request_list += f"{i+1}. {req_user_name} (ID: {req_user_id})\n"
        
        if total_initial > 10:
            request_list += f"... and {total_initial - 10} more\n\n"
        else:
            request_list += "\n"
            
        request_list += f"📊 **Total Pending:** {total_initial}\n\n🚀 **Starting auto-accept process...**"
        
        await initial_msg.edit_text(request_list)
        
        status_msg = None
        consecutive_empty_checks = 0
        last_update_time = asyncio.get_event_loop().time()
        
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
                
                batch_processed = 0
                for request in pending_requests:
                    if not auto_accept_running.get(user_id, {}).get(chat_id, False):
                        break
                        
                    try:
                        req_user_id, req_user_name = await get_user_info_from_request(request)
                        
                        # Skip if we already processed this user
                        if req_user_id and req_user_id in processed_users:
                            continue
                        
                        if req_user_id:
                            # Add to processed users set
                            processed_users.add(req_user_id)
                            batch_processed += 1
                            
                            await user_app.approve_chat_join_request(chat_id, req_user_id)
                            accepted_count += 1
                            accepted_users.append({"id": req_user_id, "name": req_user_name})
                            
                            # Send notification to the user account in the channel
                            try:
                                await user_app.send_message(
                                    chat_id,
                                    f"✅ **Your request has been accepted!**\n\n"
                                    f"👤 **User:** {req_user_name}\n"
                                    f"🏠 **Channel:** {chat_title}\n\n"
                                    f"Welcome to the channel! 🎉"
                                )
                            except Exception as notify_error:
                                print(f"⚠️ Could not send notification for {req_user_name}: {notify_error}")
                            
                            print(f"✅ Accepted: {req_user_name} (ID: {req_user_id})")
                        else:
                            failed_count += 1
                            batch_processed += 1
                            print(f"❌ Failed to get user info from request")
                        
                        await asyncio.sleep(1)  # Small delay to avoid flood
                        
                    except FloodWait as e:
                        print(f"⏳ Flood wait: {e.value} seconds")
                        await asyncio.sleep(e.value)
                    except Exception as e:
                        error_msg = str(e).lower()
                        req_user_id, req_user_name = await get_user_info_from_request(request)
                        
                        # Add to processed users even if failed to avoid re-processing
                        if req_user_id:
                            processed_users.add(req_user_id)
                        
                        batch_processed += 1
                        
                        # Handle specific errors gracefully
                        if "user_channels_too_much" in error_msg:
                            ignored_count += 1
                            print(f"⏭️ Ignored: {req_user_name or 'Unknown'} (ID: {req_user_id or 'Unknown'}) - Too many channels")
                        elif "user_deleted" in error_msg or "user_deactivated" in error_msg:
                            ignored_count += 1
                            print(f"⏭️ Ignored: {req_user_name or 'Unknown'} (ID: {req_user_id or 'Unknown'}) - Account deleted/deactivated")
                        elif "peer_id_invalid" in error_msg:
                            ignored_count += 1
                            print(f"⏭️ Ignored: {req_user_name or 'Unknown'} (ID: {req_user_id or 'Unknown'}) - Invalid user")
                        else:
                            failed_count += 1
                            print(f"❌ Failed to accept request: {e}")
                
                # Send live update after processing batch
                current_time = asyncio.get_event_loop().time()
                if current_time - last_update_time >= 3 and batch_processed > 0:  # Update every 3 seconds if we processed something
                    remaining = total_initial - accepted_count - failed_count - ignored_count
                    progress_text = f"🔄 **Auto-accepting for {chat_title}...**\n\n"
                    progress_text += f"📊 **Live Progress:**\n"
                    progress_text += f"✅ Accepted: {accepted_count}\n"
                    progress_text += f"❌ Failed: {failed_count}\n"
                    progress_text += f"⏭️ Ignored: {ignored_count}\n"
                    progress_text += f"⏳ Remaining: {remaining}\n\n"
                    
                    if accepted_count > 0:
                        progress_text += f"👤 **Last Accepted:** {accepted_users[-1]['name']}\n"
                    elif ignored_count > 0:
                        progress_text += f"⏭️ **Last Action:** Ignored user (too many channels/deleted account)\n"
                    
                    progress_text += f"📈 **Progress:** {((accepted_count + failed_count + ignored_count) / total_initial * 100):.1f}%"
                    
                    if status_msg:
                        try:
                            await status_msg.edit_text(progress_text)
                        except:
                            status_msg = await bot_app.send_message(user_id, progress_text)
                    else:
                        status_msg = await bot_app.send_message(user_id, progress_text)
                    
                    last_update_time = current_time
                
                # Check if we've processed all users
                total_processed = accepted_count + failed_count + ignored_count
                if total_processed >= total_initial:
                    print(f"✅ All {total_initial} users have been processed. Breaking main loop.")
                    break
                
                await asyncio.sleep(3)  # Wait before next batch check
                
            except Exception as e:
                print(f"Error in auto-accept loop: {e}")
                await asyncio.sleep(5)
        
        # Auto-leave the channel/group after completing all requests
        try:
            # Send final summary to the channel
            summary_msg = f"✅ **All pending requests have been processed!**\n\n" \
                         f"📋 **Final Summary:**\n" \
                         f"✅ Accepted: {accepted_count}\n" \
                         f"❌ Failed: {failed_count}\n" \
                         f"⏭️ Ignored: {ignored_count}\n\n"
            
            if accepted_users:
                summary_msg += f"🎉 **Welcome to all {len(accepted_users)} new members!**\n\n"
                if len(accepted_users) <= 10:
                    for user in accepted_users:
                        summary_msg += f"👋 {user['name']}\n"
                else:
                    for user in accepted_users[:10]:
                        summary_msg += f"👋 {user['name']}\n"
                    summary_msg += f"... and {len(accepted_users) - 10} more!\n"
                summary_msg += "\n"
            
            summary_msg += "🚪 **User account is leaving now.** If you need to process requests again, " \
                          "use `/pendingaccept` command and send the invite link to rejoin.\n\n" \
                          "**Thank you for using Auto-Approve Bot!** 🤖"
            
            await user_app.send_message(chat_id, summary_msg)
            await asyncio.sleep(2)  # Wait a moment before leaving
            
            # Leave the chat
            await user_app.leave_chat(chat_id)
            print(f"🚪 User account left chat: {chat_title} (ID: {chat_id})")
            
            # Notify the bot user about successful completion and leaving
            final_text = f"✅ **Auto-accept completed for {chat_title}!**\n\n" \
                        f"📊 **Final Statistics:**\n" \
                        f"✅ Total Accepted: {accepted_count}\n" \
                        f"❌ Total Failed: {failed_count}\n" \
                        f"⏭️ Total Ignored: {ignored_count}\n\n" \
                        f"🚪 **User account has successfully left the channel.**\n\n" \
                        f"💡 **To process requests again:** Use `/pendingaccept` and send the invite link to rejoin."
            
        except Exception as leave_error:
            print(f"❌ Error leaving chat {chat_title}: {leave_error}")
            # If leaving fails, still show completion message
            final_text = f"✅ **Auto-accept completed for {chat_title}!**\n\n" \
                        f"📊 **Final Statistics:**\n" \
                        f"✅ Total Accepted: {accepted_count}\n" \
                        f"❌ Total Failed: {failed_count}\n" \
                        f"⏭️ Total Ignored: {ignored_count}\n\n" \
                        f"⚠️ **Note:** Could not leave the channel automatically. You may leave manually if needed."
                
    except Exception as e:
        print(f"❌ Error in auto-accept process for {chat_title}: {e}")
        await bot_app.send_message(user_id, f"❌ **Error in auto-accept process:** {str(e)}")
        
        # Try to leave the chat even if there was an error
        try:
            await user_app.send_message(chat_id, "❌ **Process ended with error. User account is leaving now.**")
            await asyncio.sleep(2)
            await user_app.leave_chat(chat_id)
            print(f"🚪 User account left chat after error: {chat_title} (ID: {chat_id})")
            leave_status = "🚪 **User account has left the channel.**"
        except Exception as leave_error:
            print(f"❌ Could not leave chat after error: {leave_error}")
            leave_status = "⚠️ **Could not leave the channel automatically.**"
        
        final_text = f"❌ **Process ended with error for {chat_title}**\n\n" \
                    f"📊 **Statistics:**\n" \
                    f"✅ Accepted: {accepted_count}\n" \
                    f"❌ Failed: {failed_count}\n" \
                    f"⏭️ Ignored: {ignored_count}\n\n" \
                    f"{leave_status}"
    
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
