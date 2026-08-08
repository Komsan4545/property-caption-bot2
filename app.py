import os
import threading
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from google import genai

app = Flask(__name__)

line_bot_api = LineBotApi(os.environ.get('LINE_CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.environ.get('LINE_CHANNEL_SECRET', ''))
client = genai.Client(api_key=os.environ.get('GEMINI_API_KEY'))

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
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=prompt,
        )
        reply_text = response.text
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
