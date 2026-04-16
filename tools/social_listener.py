# social_listener.py
import os
import json
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

# ==========================================
#  ACTIVE: LIVE CLOUD DATABASE (MONGODB)
# ==========================================
def fetch_posts(batch_size=10):
    """Fetches real-time scraped social data directly from MongoDB Atlas"""
    try:
        mongo_uri = os.getenv("MONGO_URI")
        client = MongoClient(mongo_uri)
        
        db = client["PharmaVigilance"]
        collection = db["social_data"]
        
        raw_posts = list(collection.find({}, {"_id": 0}).limit(batch_size))
        return raw_posts

    except Exception as e:
        print(f"❌ Database Connection Error: {e}")
        return []

# # ==========================================
# #  ACTIVE: LOCAL MOCK DATA (COMMENTED)
# # ==========================================
# # To use this instead, comment out the function above, and uncomment this one!
# def fetch_posts(batch_size=5):
#     """
#     Simulates fetching a batch of social media posts
#     from Twitter, WhatsApp, SMS etc.
#     Returns a list of posts from our mock dataset.
#     """
#     # Build path to the data file
#     base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
#     data_path = os.path.join(base_dir, "data", "mock_posts.json")

#     with open(data_path, "r", encoding="utf-8") as f:
#         all_posts = json.load(f)

#     # Return only the first `batch_size` posts
#     return all_posts[:batch_size]














# import json
# import os

# def fetch_posts(batch_size=5):
#     """
#     Simulates fetching a batch of social media posts
#     from Twitter, WhatsApp, SMS etc.
#     Returns a list of posts from our mock dataset.
#     """
#     # Build path to the data file
#     base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
#     data_path = os.path.join(base_dir, "data", "mock_posts.json")

#     with open(data_path, "r", encoding="utf-8") as f:
#         all_posts = json.load(f)

#     # Return only the first `batch_size` posts
#     return all_posts[:batch_size]