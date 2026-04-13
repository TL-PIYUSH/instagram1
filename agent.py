import os
import json
import re
import requests

# Configuration
RULES_FILE = 'rules.json'
PROCESSED_FILE = 'processed_comments.json'
API_VERSION = 'v19.0'
BASE_URL = f'https://graph.facebook.com/{API_VERSION}'

# Credentials
ACCESS_TOKEN = os.environ.get('ACCESS_TOKEN')
IG_USER_ID = os.environ.get('IG_USER_ID')

# Inputs
INPUT_POST_URL = os.environ.get('INPUT_POST_URL', '').strip()
INPUT_KEYWORD = os.environ.get('INPUT_KEYWORD', '').strip()
INPUT_REPLY = os.environ.get('INPUT_REPLY', '').strip()

def load_json(filepath, default):
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return default
    return default

def save_json(filepath, data):
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=4)

def extract_shortcode(url):
    match = re.search(r'/(?:p|reel)/([^/?#&]+)', url)
    if match:
        return match.group(1)
    return None

def main():
    print("🚀 Starting Instagram Auto-Reply Bot...")

    if not ACCESS_TOKEN or not IG_USER_ID:
        print("❌ Error: ACCESS_TOKEN and IG_USER_ID must be set as environment variables.")
        return

    rules = load_json(RULES_FILE, {})
    processed_comments = load_json(PROCESSED_FILE, [])

    # Add new rule if inputs are provided
    if INPUT_POST_URL and INPUT_KEYWORD and INPUT_REPLY:
        shortcode = extract_shortcode(INPUT_POST_URL)
        if shortcode:
            rules[shortcode] = {
                'keyword': INPUT_KEYWORD,
                'reply': INPUT_REPLY
            }
            save_json(RULES_FILE, rules)
            print(f"✅ Added new rule for shortcode '{shortcode}': keyword='{INPUT_KEYWORD}', reply='{INPUT_REPLY}'")
        else:
            print(f"⚠️ Could not extract shortcode from URL: {INPUT_POST_URL}")

    if not rules:
        print("ℹ️ No rules configured. Exiting.")
        return

    print("🔍 Fetching recent media items...")
    media_url = f"{BASE_URL}/{IG_USER_ID}/media"
    params = {
        'fields': 'id,shortcode',
        'access_token': ACCESS_TOKEN,
        'limit': 50
    }
    
    response = requests.get(media_url, params=params)
    if response.status_code != 200:
        print(f"❌ Failed to fetch media: {response.text}")
        return
        
    media_items = response.json().get('data', [])
    print(f"📦 Found {len(media_items)} media items.")

    for item in media_items:
        shortcode = item.get('shortcode')
        media_id = item.get('id')

        if shortcode in rules:
            rule = rules[shortcode]
            keyword = rule['keyword'].lower()
            reply_text = rule['reply']
            
            print(f"💬 Checking comments for media {shortcode} (ID: {media_id})...")
            comments_url = f"{BASE_URL}/{media_id}/comments"
            comments_params = {
                'fields': 'id,text',
                'access_token': ACCESS_TOKEN,
                'limit': 50
            }
            
            comments_response = requests.get(comments_url, params=comments_params)
            if comments_response.status_code != 200:
                print(f"⚠️ Failed to fetch comments for {shortcode}: {comments_response.text}")
                continue
                
            comments = comments_response.json().get('data', [])
            
            for comment in comments:
                comment_id = comment.get('id')
                text = comment.get('text', '')
                
                if comment_id not in processed_comments and keyword in text.lower():
                    print(f"🎯 Found matching comment: '{text}' (ID: {comment_id})")
                    
                    reply_url = f"{BASE_URL}/{comment_id}/replies"
                    reply_payload = {
                        'message': reply_text,
                        'access_token': ACCESS_TOKEN
                    }
                    
                    reply_response = requests.post(reply_url, data=reply_payload)
                    if reply_response.status_code == 200:
                        print(f"✅ Successfully replied to comment {comment_id}")
                        processed_comments.append(comment_id)
                        save_json(PROCESSED_FILE, processed_comments)
                    else:
                        print(f"❌ Failed to reply to comment {comment_id}: {reply_response.text}")

    print("🏁 Finished processing.")

if __name__ == '__main__':
    main()
