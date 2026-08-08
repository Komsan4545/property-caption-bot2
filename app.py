import os
import requests
import threading
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

app = Flask(__name__)

line_bot_api = LineBotApi(os.environ.get('LINE_CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.environ.get('LINE_CHANNEL_SECRET', ''))

OPENROUTER_API_KEY = os.environ.get('GEMINI_API_KEY') # นำ OpenRouter Key มาวางในช่อง GEMINI_API_KEY บน Render ได้เลย

@app.route("/", methods=['GET'])
def index():
    return "Property Caption Bot is Running!", 200

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers.get('X-Line-Signature', '')
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK', 200

def process_gemini(reply_token, user_message):
    prompt = f"""
    คุณเป็นนักเขียนแคปชั่นขายอสังหาริมทรัพย์มืออาชีพ (Property Copywriter)
    ช่วยเขียนแคปชั่นโพสต์ขาย/เช่าอสังหาริมทรัพย์จากข้อมูลนี้:
    '{user_message}'
    
    กำหนดโครงสร้างแคปชั่น:
    1. หัวข้อที่ดึงดูดใจน่าสนใจ พร้อม Emoji
    2. จุดเด่นหลักของทรัพย์สิน
    3. รายละเอียดสำคัญ (ทำเล, ราคา, ขนาด)
    4. Call to Action ให้ติดต่อสอบถาม
    5. แฮชแท็ก (#) ที่เกี่ยวข้อง
    """
    
    try:
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        }
        data = {
            "model": "google/gemini-2.0-flash-lite-001",
            "messages": [{"role": "user", "content": prompt}]
        }
        
        response = requests.post(url, headers=headers, json=data)
        result = response.json()
        
        if "choices" in result:
            reply_text = result["choices"][0]["message"]["content"]
        else:
            reply_text = f"เกิดข้อผิดพลาด: {result.get('error', {}).get('message', 'Unknown error')}"

    except Exception as e:
        reply_text = f"ขออภัย เกิดข้อผิดพลาดในการประมวลผล: {str(e)}"

    try:
        line_bot_api.reply_message(
            reply_token,
            TextSendMessage(text=reply_text)
        )
    except Exception as e:
        print(f"Error sending LINE message: {e}")

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    thread = threading.Thread(
        target=process_gemini, 
        args=(event.reply_token, event.message.text)
    )
    thread.start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
