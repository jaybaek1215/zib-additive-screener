import os
import sys
import re
import json
import urllib.request

def clean_markdown_for_slack(md_text: str) -> str:
    # Slack mrkdwn 문법에 맞게 ### 헤더를 굵은 제목으로, **를 *로 변환
    lines = []
    for line in md_text.splitlines():
        if line.startswith("|") and "---" in line:
            continue
        if line.startswith("|"):
            # 표 행은 모바일에서 깨지지 않도록 불릿 요약으로 변환
            cells = [c.strip() for c in line.strip("|").split("|")]
            if len(cells) >= 3 and cells[0].isdigit():
                lines.append(f"• *Rank {cells[0]}* `{cells[1]}` — Score: *{cells[2]}*")
            continue
        line = re.sub(r"^#{1,3}\s+(.*)", r"\n*\1*", line)
        line = line.replace("**", "*")
        lines.append(line)
    cleaned = "\n".join(lines).strip()
    return cleaned[:2600] + ("\n\n..._(전체 상세 내용은 WSL `alerts/` 폴더 확인)_" if len(cleaned) > 2600 else "")

def send_milestone_notification(alert_path: str):
    if not os.path.exists(alert_path):
        print(f"[NOTIFY_ERR] File not found: {alert_path}", flush=True)
        return

    with open(alert_path, "r", encoding="utf-8") as f:
        content = f.read()

    title = os.path.basename(alert_path)
    formatted_body = clean_markdown_for_slack(content)

    webhook_url = os.environ.get("RESEARCH_WEBHOOK_URL", "").strip()
    if not webhook_url:
        print("[NOTIFY_WARN] RESEARCH_WEBHOOK_URL is not set.", flush=True)
        return

    if "hooks.slack.com" in webhook_url:
        payload = {
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"🔬 ZIB 자율 연구 PI 브리핑 | {title}",
                        "emoji": True
                    }
                },
                {"type": "divider"},
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": formatted_body
                    }
                }
            ]
        }
    else:
        payload = {"content": f"🔬 **[ZIB 자율 연구 PI 브리핑]** `{title}`\n\n{formatted_body}"}

    req = urllib.request.Request(
        webhook_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": "ZIB-PI-Agent/1.0"}
    )
    try:
        urllib.request.urlopen(req, timeout=10)
        print(f"[NOTIFY] Formatted Slack card sent for {title}", flush=True)
    except Exception as e:
        print(f"[NOTIFY_ERR] Webhook failed: {e}", flush=True)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        send_milestone_notification(sys.argv[1])
