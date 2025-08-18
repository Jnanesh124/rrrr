from pymongo import MongoClient
from configs import cfg

client = MongoClient(cfg.MONGO_URI)

users = client['main']['users']
groups = client['main']['groups']

def already_db(user_id):
        user = users.find_one({"user_id" : str(user_id)})
        if not user:
            return False
        return True

def already_dbg(chat_id):
        group = groups.find_one({"chat_id" : str(chat_id)})
        if not group:
            return False
        return True

def add_user(user_id):
    in_db = already_db(user_id)
    if in_db:
        return
    return users.insert_one({"user_id": str(user_id)}) 

def remove_user(user_id):
    in_db = already_db(user_id)
    if not in_db:
        return 
    return users.delete_one({"user_id": str(user_id)})
    
def add_group(chat_id):
    in_db = already_dbg(chat_id)
    if in_db:
        return
    return groups.insert_one({"chat_id": str(chat_id)})

def all_users():
    user = users.find({})
    usrs = len(list(user))
    return usrs

def all_groups():
    group = groups.find({})
    grps = len(list(group))
    return grps

# New collection for tracking all accepted users (even if they left)
accepted_users = client['main']['accepted_users']

def add_accepted_user(user_id, user_name=None, chat_title=None):
    """Add user to accepted users collection (separate from regular users)"""
    try:
        # Check if already exists
        existing = accepted_users.find_one({"user_id": str(user_id)})
        if not existing:
            data = {
                "user_id": str(user_id),
                "user_name": user_name or "Unknown",
                "chat_title": chat_title or "Unknown",
                "accepted_at": str(int(__import__('time').time()))
            }
            accepted_users.insert_one(data)
            print(f"📝 Added {user_name} (ID: {user_id}) to accepted users collection")
    except Exception as e:
        print(f"Error adding accepted user: {e}")

def get_all_accepted_users():
    """Get all accepted users (current + previously accepted)"""
    try:
        # Get current users
        current_users = set()
        for doc in users.find({}):
            current_users.add(int(doc["user_id"]))
        
        # Get all accepted users
        all_accepted = set()
        for doc in accepted_users.find({}):
            all_accepted.add(int(doc["user_id"]))
        
        # Combine both sets (union)
        combined_users = current_users.union(all_accepted)
        return list(combined_users)
    except Exception as e:
        print(f"Error getting all accepted users: {e}")
        # Fallback to current users only
        user_docs = users.find({})
        user_list = []
        for doc in user_docs:
            user_list.append(int(doc["user_id"]))
        return user_list

# Force subscription channels management
fsub_channels = client['main']['fsub_channels']

def add_fsub_channel(channel_id, channel_title=None, invite_link=None, channel_type="private"):
    """Add force subscription channel"""
    try:
        # Normalize channel_id to string
        channel_id_str = str(channel_id).strip()
        
        # Check if already exists
        existing = fsub_channels.find_one({"channel_id": channel_id_str})
        if not existing:
            data = {
                "channel_id": channel_id_str,
                "channel_title": channel_title or "Unknown",
                "invite_link": invite_link,
                "channel_type": channel_type,  # "private" or "public"
                "added_at": str(int(__import__('time').time()))
            }
            fsub_channels.insert_one(data)
            print(f"📝 Added force sub channel: {channel_title} (ID: {channel_id_str})")
            return True
        else:
            # Update existing with provided data
            update_data = {}
            if channel_title and channel_title != "Unknown":
                update_data["channel_title"] = channel_title
            if invite_link:
                update_data["invite_link"] = invite_link
            if channel_type:
                update_data["channel_type"] = channel_type
                
            if update_data:
                fsub_channels.update_one({"channel_id": channel_id_str}, {"$set": update_data})
                print(f"📝 Updated force sub channel: {channel_title or existing.get('channel_title', 'Unknown')} (ID: {channel_id_str})")
            else:
                print(f"📝 Force sub channel already exists: {existing.get('channel_title', 'Unknown')} (ID: {channel_id_str})")
            return True
    except Exception as e:
        print(f"Error adding force sub channel: {e}")
        return False

def remove_fsub_channel(channel_id):
    """Remove force subscription channel"""
    try:
        result = fsub_channels.delete_one({"channel_id": str(channel_id)})
        if result.deleted_count > 0:
            print(f"🗑️ Removed force sub channel: {channel_id}")
            return True
        return False
    except Exception as e:
        print(f"Error removing force sub channel: {e}")
        return False

def get_all_fsub_channels():
    """Get all force subscription channels"""
    try:
        channels = []
        for doc in fsub_channels.find({}):
            channels.append({
                "channel_id": doc["channel_id"],
                "channel_title": doc.get("channel_title", "Unknown"),
                "invite_link": doc.get("invite_link"),
                "channel_type": doc.get("channel_type", "private")
            })
        return channels
    except Exception as e:
        print(f"Error getting force sub channels: {e}")
        return []

def get_fsub_channel(channel_id):
    """Get specific force subscription channel"""
    try:
        return fsub_channels.find_one({"channel_id": str(channel_id)})
    except Exception as e:
        print(f"Error getting force sub channel: {e}")
        return None
