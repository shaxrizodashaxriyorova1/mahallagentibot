#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Mahalla Agenti Telegram Bot
Muallif: Mahalla Agentlik jamoasi
Versiya: 2.0.0
"""

import os
import logging
import sys
from datetime import datetime, timedelta
from io import BytesIO
from typing import Dict, Any, Optional

# Matplotlib backend sozlamasi (xatoliklarni oldini olish uchun)
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, 
    ContextTypes, MessageHandler, filters, ConversationHandler
)
from telegram.constants import ParseMode

from huggingface_hub import InferenceClient
from dotenv import load_dotenv

# ==================== LOAD ENVIRONMENT ====================
load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
HF_API_KEY = os.getenv("HF_API_KEY")

# Token tekshiruvi
if not TOKEN:
    print("❌ XATO: BOT_TOKEN topilmadi! Iltimos, .env fayl yarating va tokeningizni qo'shing.")
    print("📝 .env fayl mazmuni:")
    print("BOT_TOKEN=your_telegram_bot_token_here")
    print("HF_API_KEY=your_huggingface_api_key_here")
    sys.exit(1)

# ==================== KONFIGURATSIYA ====================
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# AI Client ni ishga tushirish
try:
    ai_client = InferenceClient(api_key=HF_API_KEY)
    logger.info("✅ AI Client muvaffaqiyatli ishga tushdi")
except Exception as e:
    logger.error(f"❌ AI Client ishga tushmadi: {e}")
    ai_client = None

# ==================== BANK MA'LUMOTLARI ====================
BANKS: Dict[str, Dict[str, str]] = {
    "hamkorbank": {
        "name": "Hamkorbank",
        "color": "🟢",
        "credit_rate": "22% - 28%",
        "deposit_rate": "18% - 22%",
        "loan_term": "60 oygacha",
        "max_amount": "100 mln so'm",
        "description": "O'zbekistonning yetakchi banklaridan biri. Tez va qulay kreditlash shartlari.",
        "requirements": "✅ Pasport + ID-karta\n✅ Daromad ma'lumotnomasi\n✅ 18 yoshdan katta",
        "phone": "+998 78 120 31 31",
        "website": "https://hamkorbank.uz"
    },
    "xalq_banki": {
        "name": "Xalq Banki",
        "color": "🔵",
        "credit_rate": "22% - 26%",
        "deposit_rate": "17% - 21%",
        "loan_term": "84 oygacha",
        "max_amount": "500 mln so'm",
        "description": "Keng filial tarmog'iga ega, aholiga qulay xizmat ko'rsatadi.",
        "requirements": "✅ Pasport\n✅ Daromad ma'lumotnomasi\n✅ Kafillar (katta summalar uchun)",
        "phone": "+998 71 200 60 00",
        "website": "https://xalqbanki.uz"
    },
    "tbc_bank": {
        "name": "TBC Bank",
        "color": "🟠",
        "credit_rate": "24% - 40.5%",
        "deposit_rate": "19% - 23%",
        "loan_term": "48 oygacha",
        "max_amount": "50 mln so'm",
        "description": "Raqamli bank xizmatlari bilan tanilgan. Mikrokreditlar bo'yicha tezkor.",
        "requirements": "✅ Pasport\n✅ Mobil ilova orqali onlayn ariza",
        "phone": "+998 78 113 33 00",
        "website": "https://tbcbank.uz"
    },
    "turonbank": {
        "name": "Turonbank",
        "color": "🟡",
        "credit_rate": "22% - 27%",
        "deposit_rate": "18% - 22%",
        "loan_term": "60 oygacha",
        "max_amount": "200 mln so'm",
        "description": "Biznes va iste'mol kreditlari bo'yicha qulay shartlar.",
        "requirements": "✅ Pasport\n✅ Daromad ma'lumotnomasi\n✅ Bandlik tasdiqnomasi",
        "phone": "+998 71 202 00 00",
        "website": "https://turonbank.uz"
    },
    "nbu": {
        "name": "NBU (Milliy Bank)",
        "color": "🏛️",
        "credit_rate": "24% - 28%",
        "deposit_rate": "17% - 20%",
        "loan_term": "60 oygacha",
        "max_amount": "100 mln so'm",
        "description": "Davlat banki, ishonchli va barqaror. Mikrokreditlar bo'yicha qulay.",
        "requirements": "✅ Pasport/ID-karta\n✅ Daromad ma'lumotnomasi\n✅ Sug'urta polisi",
        "phone": "+998 71 236 45 45",
        "website": "https://nbu.uz"
    },
    "sqb": {
        "name": "SQB (Savdogar)",
        "color": "🔴",
        "credit_rate": "23% - 28%",
        "deposit_rate": "18% - 22%",
        "loan_term": "60 oygacha",
        "max_amount": "150 mln so'm",
        "description": "Tadbirkorlar va jismoniy shaxslar uchun keng imkoniyatlar.",
        "requirements": "✅ Pasport\n✅ Daromad ma'lumotnomasi\n✅ 2 yillik ish staji",
        "phone": "+998 71 200 66 00",
        "website": "https://sqb.uz"
    }
}

# Valyuta kurslari
EXCHANGE_RATES: Dict[str, float] = {
    "USD": 12900.0,
    "EUR": 14000.0,
    "RUB": 140.0,
    "GBP": 16300.0,
    "CNY": 1780.0
}

# Conversation handler states
(LOAN_AMOUNT, LOAN_RATE, LOAN_TERM, 
 DEPOSIT_AMOUNT, DEPOSIT_RATE, DEPOSIT_TERM,
 CURRENCY_AMOUNT, UZS_AMOUNT) = range(8)

# ==================== YORDAMCHI FUNKSIYALAR ====================
def format_bank_info(bank_key: str) -> str:
    """Bank ma'lumotlarini formatlaydi"""
    bank = BANKS[bank_key]
    return f"""
{bank['color']} *{bank['name']}* {bank['color']}

📋 *Asosiy ma'lumotlar:*
{bank['description']}

💰 *Kredit shartlari:*
• Foiz stavkasi: {bank['credit_rate']}
• Muddati: {bank['loan_term']}
• Maksimal summa: {bank['max_amount']}

📈 *Depozit foizlari:* {bank['deposit_rate']}

📄 *Talab qilinadigan hujjatlar:*
{bank['requirements']}

📞 *Aloqa:* {bank['phone']}
🌐 *Veb-sayt:* {bank['website']}
"""

def generate_loan_schedule(amount: float, rate: float, months: int) -> Optional[BytesIO]:
    """Kredit jadvalini yaratib, rasm sifatida qaytaradi"""
    try:
        monthly_rate = rate / 100 / 12
        payment = amount * (monthly_rate * (1 + monthly_rate) ** months) / ((1 + monthly_rate) ** months - 1)
        
        dates = []
        remaining = []
        remaining_amount = amount
        
        for i in range(months):
            interest = remaining_amount * monthly_rate
            principal = payment - interest
            remaining_amount -= principal
            dates.append(i + 1)
            remaining.append(max(remaining_amount, 0))
        
        # Grafik yaratish
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10), facecolor='white')
        
        # Asosiy qarzning kamayishi
        ax1.plot(dates, remaining, linewidth=2, color='#2E86AB')
        ax1.fill_between(dates, 0, remaining, alpha=0.3, color='#2E86AB')
        ax1.set_xlabel('Oy', fontsize=12)
        ax1.set_ylabel('Qolgan qarz (so\'m)', fontsize=12)
        ax1.set_title(f'Kredit qoldig\'i dinamikasi\n{months} oy, {rate}%', fontsize=14, fontweight='bold')
        ax1.grid(True, alpha=0.3)
        
        # Oylik to'lov tarkibi
        interest_part = payment * (rate / 100 / 12)
        principal_part = payment - interest_part
        ax2.bar(['Foiz', 'Asosiy qarz'], [interest_part, principal_part], color=['#E63946', '#2E86AB'])
        ax2.set_ylabel('So\'m', fontsize=12)
        ax2.set_title(f'Oylik to\'lov tarkibi\nJami: {payment:,.0f} so\'m', fontsize=14, fontweight='bold')
        
        plt.tight_layout()
        
        buf = BytesIO()
        plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
        buf.seek(0)
        plt.close()
        
        return buf
    except Exception as e:
        logger.error(f"Grafik yaratishda xatolik: {e}")
        return None

def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Asosiy menyu tugmalarini qaytaradi"""
    keyboard = [
        [InlineKeyboardButton("🏦 BANKLAR", callback_data="show_banks")],
        [InlineKeyboardButton("📊 TAQQOSLASH", callback_data="compare_banks")],
        [InlineKeyboardButton("💰 KREDIT HISOBI", callback_data="calc_loan"),
         InlineKeyboardButton("💵 DEPOZIT HISOBI", callback_data="calc_deposit")],
        [InlineKeyboardButton("💱 VALYUTA KONVERTOR", callback_data="currency"),
         InlineKeyboardButton("🤖 AI YORDAMCHI", callback_data="ai_assistant")],
        [InlineKeyboardButton("ℹ️ BOT HAQIDA", callback_data="about")],
    ]
    return InlineKeyboardMarkup(keyboard)

# ==================== HANDLERLAR ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/start komandasi - asosiy menyu"""
    user = update.effective_user
    username = user.first_name or user.username or "Do'stim"
    
    welcome_text = f"""
👋 *Assalomu aleykum, {username}!*

🏦 *Mahalla Agenti Bot* ga xush kelibsiz!

Quyidagi 6 ta bank bo'yicha xizmat ko'rsataman:
🟢 Hamkorbank  •  🔵 Xalq Banki  •  🟠 TBC Bank
🟡 Turonbank   •  🏛️ NBU          •  🔴 SQB

🆕 *Yangiliklar:*
📊 Kredit + Depozit kalkulyator
💱 Valyuta konvertatsiya (USD/EUR/RUB/GBP/CNY)
🤖 AI yordamchi — istalgan savolingizga javob beradi
🔍 Banklar taqqoslash

👇 *Menyudan tanlang:*
"""
    await update.message.reply_text(
        welcome_text, 
        reply_markup=get_main_menu_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Tugmalar bosilganda ishlaydi"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "show_banks":
        keyboard = []
        for key, bank in BANKS.items():
            keyboard.append([InlineKeyboardButton(
                f"{bank['color']} {bank['name']}", 
                callback_data=f"bank_{key}"
            )])
        keyboard.append([InlineKeyboardButton("🔙 Asosiy menyu", callback_data="back_to_main")])
        
        await query.edit_message_text(
            "🏦 *Banklar ro'yxati:*\n\nQuyidagi banklardan birini tanlang:", 
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )
    
    elif data.startswith("bank_"):
        bank_key = data.replace("bank_", "")
        if bank_key in BANKS:
            info = format_bank_info(bank_key)
            keyboard = [[InlineKeyboardButton("🔙 Banklar ro'yxatiga", callback_data="show_banks")]]
            await query.edit_message_text(
                info, 
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.MARKDOWN
            )
    
    elif data == "compare_banks":
        comparison = "📊 *BANKLARNI TAQQOSLASH* 📊\n\n"
        for key, bank in BANKS.items():
            comparison += f"\n{bank['color']} *{bank['name']}*\n"
            comparison += f"   💰 Kredit: {bank['credit_rate']}\n"
            comparison += f"   📈 Depozit: {bank['deposit_rate']}\n"
            comparison += f"   💵 Maksimal: {bank['max_amount']}\n"
            comparison += f"   ⏱️ Muddati: {bank['loan_term']}\n"
            comparison += "─" * 30 + "\n"
        
        keyboard = [[InlineKeyboardButton("🔙 Asosiy menyu", callback_data="back_to_main")]]
        await query.edit_message_text(
            comparison,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )
    
    elif data == "calc_loan":
        await query.edit_message_text(
            "💰 *Kredit kalkulyatori* 💰\n\n"
            "Iltimos, kredit summasini so'mda kiriting:\n"
            "Masalan: `25000000`\n\n"
            "❌ Bekor qilish: /cancel",
            parse_mode=ParseMode.MARKDOWN
        )
        return LOAN_AMOUNT
    
    elif data == "calc_deposit":
        await query.edit_message_text(
            "💵 *Depozit kalkulyatori* 💵\n\n"
            "Iltimos, depozit summasini so'mda kiriting:\n"
            "Masalan: `10000000`\n\n"
            "❌ Bekor qilish: /cancel",
            parse_mode=ParseMode.MARKDOWN
        )
        return DEPOSIT_AMOUNT
    
    elif data == "currency":
        keyboard = []
        for curr in ["USD", "EUR", "RUB", "GBP", "CNY"]:
            keyboard.append([InlineKeyboardButton(f"{curr} → UZS", callback_data=f"curr_{curr}")])
        keyboard.append([InlineKeyboardButton("🔄 UZS → Valyuta", callback_data="curr_reverse")])
        keyboard.append([InlineKeyboardButton("🔙 Asosiy menyu", callback_data="back_to_main")])
        
        rates_text = "💱 *Valyuta kurslari:* 💱\n\n"
        for curr, rate in EXCHANGE_RATES.items():
            rates_text += f"• 1 {curr} = {rate:,.0f} so'm\n"
        
        await query.edit_message_text(
            rates_text + "\n👇 Konvertatsiya turini tanlang:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )
    
    elif data.startswith("curr_") and data != "curr_reverse":
        currency = data.replace("curr_", "")
        context.user_data['currency_from'] = currency
        await query.edit_message_text(
            f"💱 {currency} → UZS konvertatsiyasi\n\n"
            f"1 {currency} = {EXCHANGE_RATES[currency]:,.0f} so'm\n\n"
            f"Qancha {currency} konvertatsiya qilmoqchisiz?\n"
            f"Masalan: `100`\n\n"
            f"❌ Bekor qilish: /cancel",
            parse_mode=ParseMode.MARKDOWN
        )
        context.user_data['step'] = 'currency_amount'
    
    elif data == "curr_reverse":
        await query.edit_message_text(
            "💱 UZS → Valyuta konvertatsiyasi\n\n"
            "Qancha so'm konvertatsiya qilmoqchisiz?\n"
            "Masalan: `1000000`\n\n"
            "❌ Bekor qilish: /cancel",
            parse_mode=ParseMode.MARKDOWN
        )
        context.user_data['step'] = 'uzs_amount'
    
    elif data == "ai_assistant":
        if ai_client:
            await query.edit_message_text(
                "🤖 *AI Yordamchi* 🤖\n\n"
                "Men sizga bank xizmatlari, kreditlar, iqtisodiy masalalar bo'yicha yordam beraman.\n\n"
                "✍️ *Savolingizni yozib yuboring!*\n\n"
                "Masalan:\n"
                "• Qaysi bankda kredit olish qulay?\n"
                "• Depozit qanday hisoblanadi?\n"
                "• Ipoteka krediti shartlari qanday?\n\n"
                "❌ Bekor qilish: /cancel",
                parse_mode=ParseMode.MARKDOWN
            )
            context.user_data['ai_mode'] = True
        else:
            await query.edit_message_text(
                "❌ *AI yordamchi hozircha ishlamayapti!*\n\n"
                "Sabablari:\n"
                "• API kaliti noto'g'ri\n"
                "• Internet aloqasi yo'q\n"
                "• HuggingFace serverida muammo\n\n"
                "🔧 Tez orada ishga tushiriladi.\n\n"
                "Shu vaqtda bank ma'lumotlaridan foydalaning: /start",
                parse_mode=ParseMode.MARKDOWN
            )
    
    elif data == "about":
        about_text = """
ℹ️ *Mahalla Agenti Bot* ℹ️

📌 *Versiya:* 2.0.0
👨‍💻 *Muallif:* Mahalla Agentlik jamoasi
📅 *Oxirgi yangilanish:* 2026 yil

✨ *Funksiyalar:*
• 6 ta bank bo'yicha batafsil ma'lumot
• Kredit va depozit kalkulyatorlari
• Grafik ko'rinishidagi kredit jadvali
• Valyuta konvertori (5 ta valyuta)
• AI yordamchi (DeepSeek modeli)
• Banklar taqqoslash

💡 *Maslahat:* Botdan to'liq foydalanish uchun /start ni bosing.

📞 *Yordam:* @mahalla_agenti_support
"""
        keyboard = [[InlineKeyboardButton("🔙 Asosiy menyu", callback_data="back_to_main")]]
        await query.edit_message_text(
            about_text, 
            reply_markup=InlineKeyboardMarkup(keyboard), 
            parse_mode=ParseMode.MARKDOWN
        )
    
    elif data == "back_to_main":
        await query.edit_message_text(
            "🏦 *Asosiy menyu* 🏦\n\nQuyidagi tugmalardan birini tanlang:",
            reply_markup=get_main_menu_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Foydalanuvchi xabarlarini qayta ishlaydi"""
    message = update.message
    user_text = message.text.strip()
    
    # ==================== AI YORDAMCHI ====================
    # ==================== AI YORDAMCHI ====================
if context.user_data.get('ai_mode'):
    if user_text.lower() == '/cancel':
        context.user_data['ai_mode'] = False
        await message.reply_text("🤖 AI yordamchi rejimi bekor qilindi.\n🏦 Asosiy menyu: /start")
        return
    
    thinking_msg = await message.reply_text("🤔 *O‘ylayapman...*", parse_mode=ParseMode.MARKDOWN)
    
    try:
        # other.py dagi kopya – to‘liq Novita API orqali
        completion = ai_client.chat.completions.create(
            model="deepseek-ai/DeepSeek-R1:novita",  # :novita muhim!
            messages=[
                {
                    "role": "user",
                    "content": user_text
                }
            ],
            max_tokens=500
        )
        response = completion.choices[0].message.content
        
        # Javobni yuborish
        await thinking_msg.edit_text(
            f"🤖 *AI Yordamchi:*\n\n{response}", 
            parse_mode=ParseMode.MARKDOWN
        )
        
    except Exception as e:
        logger.error(f"AI xatolik (Novita): {e}")
        await thinking_msg.edit_text(
            f"❌ *AI xizmatida xatolik:*\n\n"
            f"Xato: {str(e)[:150]}\n\n"
            f"💡 *Maslahat:* Iltimos, keyinroq qayta urinib ko‘ring yoki /start ni bosing.",
            parse_mode=ParseMode.MARKDOWN
        )
    
    context.user_data['ai_mode'] = False
    return
    
    # ==================== KREDIT KALKULYATORI ====================
    if context.user_data.get('calc_type') == 'loan':
        step = context.user_data.get('step')
        
        if step == 'loan_amount':
            try:
                amount = float(user_text.replace(' ', '').replace(',', ''))
                if amount <= 0:
                    raise ValueError
                context.user_data['loan_amount'] = amount
                context.user_data['step'] = 'loan_rate'
                await message.reply_text(
                    f"💰 Kredit summasi: {amount:,.0f} so'm\n\n"
                    f"📈 Endi yillik foiz stavkasini kiriting (%):\n"
                    f"Masalan: `24` (banklar stavkalari 22-40% oralig'ida)\n\n"
                    f"❌ Bekor qilish: /cancel",
                    parse_mode=ParseMode.MARKDOWN
                )
            except ValueError:
                await message.reply_text("❌ Iltimos, to'g'ri summa kiriting (faqat raqamlar). Masalan: `25000000`")
        
        elif step == 'loan_rate':
            try:
                rate = float(user_text.replace('%', '').replace(',', ''))
                if rate <= 0 or rate > 60:
                    raise ValueError
                context.user_data['loan_rate'] = rate
                context.user_data['step'] = 'loan_term'
                await message.reply_text(
                    f"📈 Yillik foiz stavkasi: {rate}%\n\n"
                    f"⏱️ Endi kredit muddatini oylarda kiriting:\n"
                    f"Masalan: `12`, `24`, `36`, `60` (maksimal 84 oy)\n\n"
                    f"❌ Bekor qilish: /cancel",
                    parse_mode=ParseMode.MARKDOWN
                )
            except ValueError:
                await message.reply_text("❌ Iltimos, to'g'ri foiz stavkasi kiriting (1-60 oralig'ida). Masalan: `24`")
        
        elif step == 'loan_term':
            try:
                months = int(user_text)
                if months <= 0 or months > 120:
                    raise ValueError
                
                amount = context.user_data['loan_amount']
                rate = context.user_data['loan_rate']
                
                # Oylik to'lovni hisoblash
                monthly_rate = rate / 100 / 12
                payment = amount * (monthly_rate * (1 + monthly_rate) ** months) / ((1 + monthly_rate) ** months - 1)
                total_payment = payment * months
                total_interest = total_payment - amount
                
                # Kredit jadvali
                schedule_img = generate_loan_schedule(amount, rate, months)
                
                result_text = f"""
💰 *Kredit hisoboti* 💰

📊 *Ma'lumotlar:*
• Kredit summasi: {amount:,.0f} so'm
• Yillik foiz: {rate}%
• Muddati: {months} oy

💵 *Natijalar:*
• Oylik to'lov: {payment:,.0f} so'm
• Jami to'lov: {total_payment:,.0f} so'm
• Jami foiz: {total_interest:,.0f} so'm

📈 *Tavsiya:* Eng past foizli banklar - Hamkorbank (~22%) va Xalq Banki (~22-26%)
"""
                
                if schedule_img:
                    await message.reply_photo(
                        photo=schedule_img,
                        caption=result_text,
                        parse_mode=ParseMode.MARKDOWN
                    )
                else:
                    await message.reply_text(result_text, parse_mode=ParseMode.MARKDOWN)
                
                # Tozalash
                context.user_data.clear()
                
                # Asosiy menyu
                await message.reply_text(
                    "👇 *Asosiy menyu:*",
                    reply_markup=get_main_menu_keyboard(),
                    parse_mode=ParseMode.MARKDOWN
                )
                
            except ValueError:
                await message.reply_text("❌ Iltimos, to'g'ri muddat kiriting (1-120 oy oralig'ida). Masalan: `24`")
    
    # ==================== DEPOZIT KALKULYATORI ====================
    elif context.user_data.get('calc_type') == 'deposit':
        step = context.user_data.get('step')
        
        if step == 'deposit_amount':
            try:
                amount = float(user_text.replace(' ', '').replace(',', ''))
                if amount <= 0:
                    raise ValueError
                context.user_data['deposit_amount'] = amount
                context.user_data['step'] = 'deposit_rate'
                await message.reply_text(
                    f"💵 Depozit summasi: {amount:,.0f} so'm\n\n"
                    f"📈 Endi yillik foiz stavkasini kiriting (%):\n"
                    f"Masalan: `18` (banklar stavkalari 17-23% oralig'ida)\n\n"
                    f"❌ Bekor qilish: /cancel",
                    parse_mode=ParseMode.MARKDOWN
                )
            except ValueError:
                await message.reply_text("❌ Iltimos, to'g'ri summa kiriting. Masalan: `10000000`")
        
        elif step == 'deposit_rate':
            try:
                rate = float(user_text.replace('%', '').replace(',', ''))
                if rate <= 0 or rate > 30:
                    raise ValueError
                context.user_data['deposit_rate'] = rate
                context.user_data['step'] = 'deposit_term'
                await message.reply_text(
                    f"📈 Yillik foiz stavkasi: {rate}%\n\n"
                    f"⏱️ Endi depozit muddatini oylarda kiriting:\n"
                    f"Masalan: `6`, `12`, `24` (maksimal 60 oy)\n\n"
                    f"❌ Bekor qilish: /cancel",
                    parse_mode=ParseMode.MARKDOWN
                )
            except ValueError:
                await message.reply_text("❌ Iltimos, to'g'ri foiz stavkasi kiriting (1-30 oralig'ida).")
        
        elif step == 'deposit_term':
            try:
                months = int(user_text)
                if months <= 0 or months > 60:
                    raise ValueError
                
                amount = context.user_data['deposit_amount']
                rate = context.user_data['deposit_rate']
                
                # Depozit hisobi
                total_interest = amount * (rate / 100) * (months / 12)
                total_amount = amount + total_interest
                
                result_text = f"""
💵 *Depozit hisoboti* 💵

📊 *Ma'lumotlar:*
• Depozit summasi: {amount:,.0f} so'm
• Yillik foiz: {rate}%
• Muddati: {months} oy

💰 *Natijalar:*
• Qo'shimcha foiz: {total_interest:,.0f} so'm
• Jami summa: {total_amount:,.0f} so'm

📈 *Eng yaxshi depozit takliflari:*
• Xalq Banki: 17-21%
• Hamkorbank: 18-22%
• NBU: 17-20%
"""
                
                await message.reply_text(result_text, parse_mode=ParseMode.MARKDOWN)
                
                # Tozalash
                context.user_data.clear()
                
                # Asosiy menyu
                await message.reply_text(
                    "👇 *Asosiy menyu:*",
                    reply_markup=get_main_menu_keyboard(),
                    parse_mode=ParseMode.MARKDOWN
                )
                
            except ValueError:
                await message.reply_text("❌ Iltimos, to'g'ri muddat kiriting (1-60 oy oralig'ida).")
    
    # ==================== VALYUTA KONVERTORI ====================
    elif context.user_data.get('step') == 'currency_amount':
        try:
            amount = float(user_text.replace(' ', '').replace(',', ''))
            if amount <= 0:
                raise ValueError
            
            currency = context.user_data.get('currency_from', 'USD')
            converted = amount * EXCHANGE_RATES[currency]
            
            result_text = f"""
💱 *Konvertatsiya natijasi* 💱

{amount:,.2f} {currency} = {converted:,.0f} so'm

📊 *Kurs:* 1 {currency} = {EXCHANGE_RATES[currency]:,.0f} so'm

💡 *Maslahat:* Boshqa konvertatsiya uchun /start ni bosing.
"""
            await message.reply_text(result_text, parse_mode=ParseMode.MARKDOWN)
            
            context.user_data.clear()
            await message.reply_text(
                "👇 *Asosiy menyu:*",
                reply_markup=get_main_menu_keyboard(),
                parse_mode=ParseMode.MARKDOWN
            )
            
        except ValueError:
            await message.reply_text("❌ Iltimos, to'g'ri miqdor kiriting (faqat raqamlar). Masalan: `100`")
    
    elif context.user_data.get('step') == 'uzs_amount':
        try:
            amount = float(user_text.replace(' ', '').replace(',', ''))
            if amount <= 0:
                raise ValueError
            
            results = []
            for curr, rate in EXCHANGE_RATES.items():
                converted = amount / rate
                results.append(f"• {converted:,.2f} {curr}")
            
            result_text = f"""
💱 *Konvertatsiya natijasi* 💱

{amount:,.0f} so'm = 

{chr(10).join(results)}

📊 *Joriy kurslar bo'yicha*

💡 *Maslahat:* Boshqa konvertatsiya uchun /start ni bosing.
"""
            await message.reply_text(result_text, parse_mode=ParseMode.MARKDOWN)
            
            context.user_data.clear()
            await message.reply_text(
                "👇 *Asosiy menyu:*",
                reply_markup=get_main_menu_keyboard(),
                parse_mode=ParseMode.MARKDOWN
            )
            
        except ValueError:
            await message.reply_text("❌ Iltimos, to'g'ri miqdor kiriting (faqat raqamlar). Masalan: `1000000`")
    
    else:
        await message.reply_text(
            "❓ *Tushunarsiz buyruq* ❓\n\n"
            "Yordam uchun quyidagi buyruqlardan foydalaning:\n"
            "• /start - Asosiy menyu\n"
            "• /cancel - Joriy amalni bekor qilish\n\n"
            "👇 Asosiy menyu:",
            reply_markup=get_main_menu_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )

async def loan_conversation_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Kredit hisoblashni boshlash"""
    query = update.callback_query
    await query.answer()
    context.user_data['calc_type'] = 'loan'
    context.user_data['step'] = 'loan_amount'
    await query.edit_message_text(
        "💰 *Kredit kalkulyatori* 💰\n\n"
        "Iltimos, kredit summasini so'mda kiriting:\n"
        "Masalan: `25000000`\n\n"
        "❌ Bekor qilish: /cancel",
        parse_mode=ParseMode.MARKDOWN
    )

async def deposit_conversation_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Depozit hisoblashni boshlash"""
    query = update.callback_query
    await query.answer()
    context.user_data['calc_type'] = 'deposit'
    context.user_data['step'] = 'deposit_amount'
    await query.edit_message_text(
        "💵 *Depozit kalkulyatori* 💵\n\n"
        "Iltimos, depozit summasini so'mda kiriting:\n"
        "Masalan: `10000000`\n\n"
        "❌ Bekor qilish: /cancel",
        parse_mode=ParseMode.MARKDOWN
    )

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/cancel komandasi - joriy amalni bekor qilish"""
    context.user_data.clear()
    await update.message.reply_text(
        "✅ *Joriy amal bekor qilindi!* ✅\n\n"
        "Yangi buyruq uchun /start ni bosing.\n\n"
        "👇 Asosiy menyu:",
        reply_markup=get_main_menu_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Xatoliklarni qayta ishlash"""
    logger.error(f"Xatolik yuz berdi: {context.error}")
    
    error_message = "❌ *Kechirasiz, texnik xatolik yuz berdi!* ❌\n\n"
    
    if update and update.effective_message:
        await update.effective_message.reply_text(
            error_message + "Iltimos, keyinroq qayta urinib ko'ring yoki /start ni bosing.",
            parse_mode=ParseMode.MARKDOWN
        )

# ==================== ASOSIY FUNKSIYA ====================
def main() -> None:
    """Botni ishga tushirish"""
    print("=" * 50)
    print("🚀 Mahalla Agenti Bot ishga tushmoqda...")
    print(f"🔑 BOT_TOKEN: {'✅ Mavjud' if TOKEN else '❌ Topilmadi'}")
    print(f"🤖 AI Client: {'✅ Ishga tushdi' if ai_client else '❌ Ishlamayapti'}")
    print("=" * 50)
    
    # Application yaratish
    application = Application.builder().token(TOKEN).build()
    
    # Handlerlarni qo'shish
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("cancel", cancel))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_error_handler(error_handler)
    
    # Botni ishga tushirish
    print("✅ Bot muvaffaqiyatli ishga tushdi!")
    print("🏃 Bot ishlayapti...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
