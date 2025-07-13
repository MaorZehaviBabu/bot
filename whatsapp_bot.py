import json
import os
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client

app = Flask(__name__)

FILE_NAME = "shopping_list.json"
BASE_URL = os.environ.get("BASE_URL", "")  # הכתובת הציבורית שלך ב-Render

CATEGORIES = {
    "לפני מוצרי החלב": ["יין", "תירוש", "סלומון מעושן"],
    "מוצרי חלב": ["חלב", "גבינה", "יוגורט", "שמנת", "קוטג", "גבינת", "מוצרלה"],
    "לחמים": ["לחם", "פיתות", "לחמניות", "טורטיות"],
    "בשר ודגים": ["בשר", "עוף", "דג", "המבורגר"],
    "קפואים": ["קפוא"],
    "ירקות": ["עגבנייה", "עגבניה", "מלפפון", "גזר", "פלפל", "בצל", "פטריות",
              "חסה", "שום", "כוסברה", "כרוב", "שומר", 'תפו"א', "קולורבי"],
    "שתייה": ["שתייה", "סודה", "קולה", "זירו"],
    "פירות": ["תפוח", "בננה", "תפוז", "ענבים", "אבטיח", "מלון", "אוכמניות"],
    "ניקיון": ["סבון", "אקונומיקה", "מטאטא", "שואב", "כלים", "זבל", "ניקוי", "נייר"],
    "ילדים": ["טיטולים", "מגבונים", "מטרנה", 'תמ"ל', "סבון לתינוקות", "שמפו לתינוקות"],
    "תחזוקה": ["פטיש", "מברג", "נורה", "דבק", "מפתח"],
    "מוצרי מזון יבשים": ["פסטה", "אורז", "שמן", "קמח", "סוכר", "מלח", "קרקר", "פתיתים", "שוקולית", "מיונז", "שקיות קוקי"],
    "תבלינים": ["תבלין", "כמון", "פפריקה", "כורכום", "פלפל שחור", "פלפל לבן", "פלפל יבש", "ראס אל חנות"],
    "חטיפים": ["שוקולד", "במבה", "עוגיות", "חטיף", "חטיפים"]
}


def load_shopping_list():
    if os.path.exists(FILE_NAME):
        with open(FILE_NAME, "r", encoding="utf-8") as f:
            return json.load(f)
    else:
        return {category: [] for category in CATEGORIES.keys()}


def save_shopping_list(shopping_list):
    with open(FILE_NAME, "w", encoding="utf-8") as f:
        json.dump(shopping_list, f, ensure_ascii=False, indent=2)


shopping_list = load_shopping_list()


@app.route("/shopping_list.txt")
def serve_list_file():
    return open("shopping_list.txt", "rb").read(), 200, {
        'Content-Type': 'text/plain; charset=utf-8'
    }


def generate_text_file(shopping_list):
    lines = []
    lines.append("📋 רשימת קניות לפי קטגוריות:\n")

    for category, items in shopping_list.items():
        if items:
            lines.append(f"\n== {category} ==\n")
            for item in items:
                lines.append(f"[ ] {item}")

    content = "\n".join(lines)
    with open("shopping_list.txt", "w", encoding="utf-8") as f:
        f.write(content)
    return "shopping_list.txt"


def categorize_item(item):
    for category, keywords in CATEGORIES.items():
        for word in keywords:
            if word in item:
                return category
    return "אחר"


@app.route("/whatsapp", methods=['POST'])
def whatsapp():
    incoming_msg = request.values.get('Body', '').strip()
    resp = MessagingResponse()
    msg = resp.message()

    print(f"📥 התקבלה הודעה: {incoming_msg}")

    global shopping_list

    if incoming_msg.startswith("הוסף "):
        item = incoming_msg.replace("הוסף ", "").strip()
        category = categorize_item(item)
        if category not in shopping_list:
            shopping_list[category] = []
        shopping_list[category].append(item)
        save_shopping_list(shopping_list)
        msg.body(f"✅ הוספתי לקטגוריה '{category}': {item}")

    elif incoming_msg.startswith("הסר "):
        item = incoming_msg.replace("הסר ", "").strip()
        found = False
        for category, items in shopping_list.items():
            if item in items:
                items.remove(item)
                found = True
                save_shopping_list(shopping_list)
                msg.body(f"🗑️ הסרתי את '{item}' מהרשימה בקטגוריה '{category}'.")
                break
        if not found:
            msg.body(f"❌ לא מצאתי את '{item}' ברשימה.")

    elif incoming_msg == "יצא לרשימה":
        generate_text_file(shopping_list)
        account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
        auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
        client = Client(account_sid, auth_token)

        from_number = request.values.get('To')
        to_number = request.values.get('From')

        public_url = f"{BASE_URL}/shopping_list.txt"

        client.messages.create(
            from_=from_number,
            to=to_number,
            body="📎 הנה רשימת הקניות שלך:",
            media_url=public_url
        )

        msg.body("📤 שלחתי לך את הרשימה כקובץ.")

    elif incoming_msg == "רשימה":
        if not any(shopping_list.values()):
            msg.body("📭 הרשימה ריקה.")
        else:
            response = "📋 רשימת קניות משותפת:\n"
            for category, items in shopping_list.items():
                if items:
                    response += f"\n🗂️ {category}:\n"
                    for i, item in enumerate(items, start=1):
                        response += f"{i}. {item}\n"
            msg.body(response)

    elif incoming_msg == "נקה":
        shopping_list = {category: [] for category in CATEGORIES.keys()}
        save_shopping_list(shopping_list)
        msg.body("🧹 הרשימה נמחקה.")

    else:
        msg.body("לא הבנתי. נסה:\n• הוסף חלב\n• הסר חלב\n• רשימה\n• נקה\n• יצא לרשימה")

    return str(resp)


if __name__ == "__main__":
    app.run(port=5000)
