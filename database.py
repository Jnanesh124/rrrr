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
