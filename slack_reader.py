import os
import json
import urllib.request
import urllib.parse

STATE_FILE = "runs/.last_slack_ts"

def fetch_new_user_messages() -> str:
    token = os.environ.get("SLACK_BOT_TOKEN", "").strip()
    channel_id = os.environ.get("SLACK_CHANNEL_ID", "").strip()
    if not token or not channel_id:
        return ""

    last_ts = "0"
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            last_ts = f.read().strip() or "0"

    params = urllib.parse.urlencode({"channel": channel_id, "oldest": last_ts, "limit": 20})
    url = f"https://slack.com/api/conversations.history?{params}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"[SLACK_READ_ERR] {e}", flush=True)
        return ""

    if not data.get("ok"):
        print(f"[SLACK_API_ERR] {data.get('error')}", flush=True)
        return ""

    messages = data.get("messages", [])
    user_msgs = []
    max_ts = float(last_ts)

    for m in reversed(messages):
        ts = float(m.get("ts", 0))
        if ts > max_ts:
            max_ts = ts
        if "bot_id" not in m and m.get("subtype") is None:
            text = m.get("text", "").strip()
            if text:
                user_msgs.append(f"- [User Slack Directive]: {text}")

    with open(STATE_FILE, "w") as f:
        f.write(str(max_ts))

    return "\n".join(user_msgs)

if __name__ == "__main__":
    out = fetch_new_user_messages()
    print(out if out else "(No new user messages)")
