
import os
import logging
import asyncio
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
from io import BytesIO

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from telegram.constants import ParseMode

from huggingface_hub import InferenceClient


TOKEN = os.getenv("BOT_TOKEN")
HF_API_KEY = os.getenv("HF_API_KEY")
ai_client = InferenceClient(api_key=HF_API_KEY)

# Logging sozlamalari
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==================== BANK MA'LUMOTLARI ====================
# Banklar haqida batafsil ma'lumot [citation:1][citation:5][citation:10]
BANKS = {
    "hamkorbank": {
        "name": "🏦 Hamkorbank",
        "color": "🟢",
        "credit_rate": "Yillik 22% - 28%",
        "deposit_rate": "Yillik 18% - 22%",
        "loan_term": "60 oygacha",
        "max_amount": "100 mln so'mgacha",
        "description": "O'zbekistonning yetakchi banklaridan biri. Tez va qulay kreditlash shartlari.",
        "requirements": "✅ Pasport + ID-karta\n✅ Daromad ma'lumotnomasi\n✅ 18 yoshdan katta"
    },
    "xalq_banki": {
        "name": "🏛️ Xalq Banki",
        "color": "🔵",
        "credit_rate": "Yillik 22% - 26%",
        "deposit_rate": "Yillik 17% - 21%",
        "loan_term": "84 oygacha",
        "max_amount": "500 mln so'mgacha",
        "description": "Keng filial tarmog'iga ega, aholiga qulay xizmat ko'rsatadi.",
        "requirements": "✅ Pasport\n✅ Daromad ma'lumotnomasi\n✅ Kafillar (katta summalar uchun)"
    },
    "tbc_bank": {
        "name": "🟠 TBC Bank",
        "color": "🟠",
        "credit_rate": "Yillik 24% - 40.5%",
        "deposit_rate": "Yillik 19% - 23%",
        "loan_term": "48 oygacha",
        "max_amount": "50 mln so'mgacha",
        "description": "Raqamli bank xizmatlari bilan tanilgan. Mikrokreditlar bo'yicha tezkor.",
        "requirements": "✅ Pasport\n✅ Mobil ilova orqali onlayn ariza"
    },
    "turonbank": {
        "name": "🟡 Turonbank",
        "color": "🟡",
        "credit_rate": "Yillik 22% - 27%",
        "deposit_rate": "Yillik 18% - 22%",
        "loan_term": "60 oygacha",
        "max_amount": "200 mln so'mgacha",
        "description": "Biznes va iste'mol kreditlari bo'yicha qulay shartlar.",
        "requirements": "✅ Pasport\n✅ Daromad ma'lumotnomasi\n✅ Bandlik tasdiqnomasi"
    },
    "nbu": {
        "name": "🏦 NBU (Milliy Bank)",
        "color": "🏛️",
        "credit_rate": "Yillik 24% - 28%",
        "deposit_rate": "Yillik 17% - 20%",
        "loan_term": "60 oygacha",
        "max_amount": "100 mln so'mgacha",
        "description": "Davlat banki, ishonchli va barqaror. Mikrokreditlar bo'yicha qulay.",
        "requirements": "✅ Pasport/ID-karta\n✅ Daromad ma'lumotnomasi\n✅ Sug'urta polisi [citation:1]"
    },
    "sqb": {
        "name": "🔴 SQB (Savdogar)",
        "color": "🔴",
        "credit_rate": "Yillik 23% - 28%",
        "deposit_rate": "Yillik 18% - 22%",
        "loan_term": "60 oygacha",
        "max_amount": "150 mln so'mgacha",
        "description": "Tadbirkorlar va jismoniy shaxslar uchun keng imkoniyatlar.",
        "requirements": "✅ Pasport\n✅ Daromad ma'lumotnomasi\n✅ 2 yillik ish staji"
    }
}

# Valyuta kurslari (so'mga nisbatan - taxminiy, real API dan olish tavsiya etiladi)
EXCHANGE_RATES = {
    "USD": 12900,
    "EUR": 14000,
    "RUB": 140,
    "GBP": 16300,
    "CNY": 1780
}

# ==================== KALIT SO'ZLAR ====================
MAIN_MENU_BUTTONS = {
    "banklar": "🏦 BANKLAR",
    "taqqoslash": "📊 TAQQOSLASH",
    "kredit": "💰 KREDIT HISOBI",
    "depozit": "💵 DEPOZIT HISOBI",
    "valyuta": "💱 VALYUTA KONVERTOR",
    "ai": "🤖 AI YORDAMCHI",
    "about": "ℹ️ BOT HAQIDA"
}

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

🔍 *Qo'shimcha ma'lumot:* /start ni bosing va menyudan tanlang
"""

def generate_loan_schedule(amount: float, rate: float, months: int) -> BytesIO:
    """Kredit jadvalini yaratib, rasm sifatida qaytaradi"""
    monthly_rate = rate / 100 / 12
    payment = amount * (monthly_rate * (1 + monthly_rate) ** months) / ((1 + monthly_rate) ** months - 1)
    
    # Ma'lumotlarni tayyorlash
    dates = []
    remaining = []
    remaining_amount = amount
    schedule_dates = []
    
    for i in range(months):
        interest = remaining_amount * monthly_rate
        principal = payment - interest
        remaining_amount -= principal
        dates.append(i + 1)
        remaining.append(remaining_amount if remaining_amount > 0 else 0)
        schedule_dates.append(datetime.now() + timedelta(days=30 * (i + 1)))
    
    # Grafik yaratish
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10), facecolor='white')
    
    # Asosiy qarzning kamayishi
    ax1.plot(dates, remaining, 'b-', linewidth=2, color='#2E86AB')
    ax1.fill_between(dates, 0, remaining, alpha=0.3, color='#2E86AB')
    ax1.set_xlabel('Oy', fontsize=12)
    ax1.set_ylabel('Qolgan qarz (so\'m)', fontsize=12)
    ax1.set_title(f'Kredit qoldig\'i dinamikasi\n{months} oy, {rate}%', fontsize=14, fontweight='bold')
    ax1.grid(True, alpha=0.3)
    
    # Oylik to'lov diagrammasi
    interest_part = payment * 0.4
    principal_part = payment * 0.6
    ax2.bar(['Foiz', 'Asosiy qarz'], [interest_part, principal_part], color=['#E63946', '#2E86AB'])
    ax2.set_ylabel('So\'m', fontsize=12)
    ax2.set_title(f'Oylik to\'lov tarkibi\nJami: {payment:,.0f} so\'m', fontsize=14, fontweight='bold')
    
    plt.tight_layout()
    
    # Rasmni bytes ga o'tkazish
    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
    buf.seek(0)
    plt.close()
    
    return buf

def generate_comparison_table(banks_to_compare: list) -> str:
    """Banklarni taqqoslash jadvalini yaratadi"""
    comparison = "📊 *BANKLARNI TAQQOSLASH* 📊\n\n"
    comparison += "┌─────────────────┬──────────────┬──────────────┬──────────────┐\n"
    comparison += "│ Bank nomi       │ Kredit foizi │ Depozit foizi│ Maks. summa  │\n"
    comparison += "├─────────────────┼──────────────┼──────────────┼──────────────┤\n"
    
    for bank_key in banks_to_compare:
        if bank_key in BANKS:
            bank = BANKS[bank_key]
            name_short = bank['name'][:15]
            credit = bank['credit_rate'][:12]
            deposit = bank['deposit_rate'][:12]
            max_amt = bank['max_amount'][:12]
            comparison += f"│ {name_short:<15} │ {credit:<12} │ {deposit:<12} │ {max_amt:<12} │\n"
    
    comparison += "└─────────────────┴──────────────┴──────────────┴──────────────┘\n\n"
    comparison += "ℹ️ *Eng past kredit foizi:* Hamkorbank (~22%)\n"
    comparison += "ℹ️ *Eng qulay depozit:* Xalq Banki (~17-21%)\n"
    comparison += "ℹ️ *Eng uzoq muddat:* Xalq Banki (84 oy)\n"
    comparison += "ℹ️ *Eng katta summa:* Xalq Banki (500 mln so'm)\n"
    
    return comparison

# ==================== HANDLERLAR ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/start komandasi - asosiy menyu"""
    user = update.effective_user
    username = user.first_name or user.username or "Do'stim"
    
    # Inline tugmalar
    keyboard = [
        [InlineKeyboardButton(MAIN_MENU_BUTTONS["banklar"], callback_data="show_banks")],
        [InlineKeyboardButton(MAIN_MENU_BUTTONS["taqqoslash"], callback_data="compare_banks")],
        [InlineKeyboardButton(MAIN_MENU_BUTTONS["kredit"], callback_data="calc_loan"),
         InlineKeyboardButton(MAIN_MENU_BUTTONS["depozit"], callback_data="calc_deposit")],
        [InlineKeyboardButton(MAIN_MENU_BUTTONS["valyuta"], callback_data="currency"),
         InlineKeyboardButton(MAIN_MENU_BUTTONS["ai"], callback_data="ai_assistant")],
        [InlineKeyboardButton(MAIN_MENU_BUTTONS["about"], callback_data="about")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
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
    await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Tugmalar bosilganda ishlaydi"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "show_banks":
        # Banklar ro'yxati
        keyboard = []
        for key, bank in BANKS.items():
            keyboard.append([InlineKeyboardButton(f"{bank['color']} {bank['name']}", callback_data=f"bank_{key}")])
        keyboard.append([InlineKeyboardButton("🔙 Orqaga", callback_data="back_to_main")])
        
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
        # Barcha banklarni taqqoslash
        all_banks = list(BANKS.keys())
        comparison = generate_comparison_table(all_banks)
        keyboard = [[InlineKeyboardButton("🔙 Asosiy menyu", callback_data="back_to_main")]]
        await query.edit_message_text(
            comparison,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )
    
    elif data == "calc_loan":
        context.user_data['calc_type'] = 'loan'
        await query.edit_message_text(
            "💰 *Kredit kalkulyatori* 💰\n\n"
            "Iltimos, quyidagi ma'lumotlarni kiriting:\n"
            "`Kredit summasi (so'mda)`\n"
            "Masalan: `25000000`\n\n"
            "Keyin foiz stavkasi va muddatni so'rayman.",
            parse_mode=ParseMode.MARKDOWN
        )
        context.user_data['step'] = 'loan_amount'
    
    elif data == "calc_deposit":
        context.user_data['calc_type'] = 'deposit'
        await query.edit_message_text(
            "💵 *Depozit kalkulyatori* 💵\n\n"
            "Iltimos, depozit summasini kiriting (so'mda):\n"
            "Masalan: `10000000`",
            parse_mode=ParseMode.MARKDOWN
        )
        context.user_data['step'] = 'deposit_amount'
    
    elif data == "currency":
        # Valyuta konvertori
        keyboard = []
        currencies = ["USD", "EUR", "RUB", "GBP", "CNY"]
        for curr in currencies:
            keyboard.append([InlineKeyboardButton(f"{curr} → UZS", callback_data=f"curr_{curr}")])
        keyboard.append([InlineKeyboardButton("🔄 Teskari konvertatsiya", callback_data="curr_reverse")])
        keyboard.append([InlineKeyboardButton("🔙 Asosiy menyu", callback_data="back_to_main")])
        
        rates_text = "💱 *Valyuta kurslari (so'mga nisbatan):* 💱\n\n"
        for curr, rate in EXCHANGE_RATES.items():
            rates_text += f"• 1 {curr} = {rate:,} so'm\n"
        
        await query.edit_message_text(
            rates_text + "\n👇 Quyidagi valyutalardan birini tanlang:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )
    
    elif data.startswith("curr_"):
        currency = data.replace("curr_", "")
        context.user_data['currency_from'] = currency
        context.user_data['conv_type'] = 'to_uzs'
        await query.edit_message_text(
            f"💱 {currency} → UZS konvertatsiyasi\n\n"
            f"1 {currency} = {EXCHANGE_RATES[currency]:,} so'm\n\n"
            f"Qancha {currency} konvertatsiya qilmoqchisiz?\n"
            f"Masalan: `100`",
            parse_mode=ParseMode.MARKDOWN
        )
        context.user_data['step'] = 'currency_amount'
    
    elif data == "curr_reverse":
        context.user_data['conv_type'] = 'from_uzs'
        await query.edit_message_text(
            "💱 UZS → Valyuta konvertatsiyasi\n\n"
            "Qancha so'm konvertatsiya qilmoqchisiz?\n"
            "Masalan: `1000000`",
            parse_mode=ParseMode.MARKDOWN
        )
        context.user_data['step'] = 'uzs_amount'
    
    elif data == "ai_assistant":
        await query.edit_message_text(
            "🤖 *AI Yordamchi* 🤖\n\n"
            "Men sizga bank xizmatlari, kreditlar, iqtisodiy masalalar bo'yicha yordam beraman.\n\n"
            "✍️ Savolingizni yozib yuboring!\n\n"
            "Masalan:\n"
            "- Qaysi bankda kredit olish qulay?\n"
            "- Depozit qanday hisoblanadi?\n"
            "- Ipoteka krediti shartlari qanday?\n\n"
            "❌ Bekor qilish uchun /cancel ni yozing.",
            parse_mode=ParseMode.MARKDOWN
        )
        context.user_data['ai_mode'] = True
    
    elif data == "about":
        about_text = """
ℹ️ *Mahalla Agenti Bot* ℹ️

📌 *Versiya:* 1.0.0
👨‍💻 *Yaratuvchi:* Mahalla Agentlik jamoasi

✨ *Funksiyalar:*
• 6 ta bank bo'yicha batafsil ma'lumot
• Kredit va depozit kalkulyatorlari
• Grafik ko'rinishidagi kredit jadvali
• Valyuta konvertori (5 ta valyuta)
• AI yordamchi (DeepSeek modeli)
• Banklar taqqoslash

📞 *Yordam:* @your_support_bot

🔄 *Bot yangilanishlari:* /start
"""
        keyboard = [[InlineKeyboardButton("🔙 Asosiy menyu", callback_data="back_to_main")]]
        await query.edit_message_text(about_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)
    
    elif data == "back_to_main":
        await start(update, context)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Foydalanuvchi xabarlarini qayta ishlaydi"""
    message = update.message
    user_text = message.text.strip()
    
    # AI yordamchi rejimi
    if context.user_data.get('ai_mode'):
        if user_text.lower() == '/cancel':
            context.user_data['ai_mode'] = False
            await message.reply_text("🤖 AI yordamchi rejimi bekor qilindi. /start bilan asosiy menyuga qayting.")
            return
        
        await message.reply_text("🤔 *O'ylayapman...*", parse_mode=ParseMode.MARKDOWN)
        
        try:
            # HuggingFace AI API orqali javob olish [citation:3][citation:8]
            completion = ai_client.chat.completions.create(
                model="deepseek-ai/DeepSeek-R1:novita",
                messages=[
                    {
                        "role": "system",
                        "content": "Siz O'zbekiston banklari, kreditlar, depozitlar va moliyaviy masalalar bo'yicha mutaxassis yordamchisiz. Faqat bank va moliyaviy savollarga javob bering. Iloji boricha foydali va qisqa javoblar bering."
                    },
                    {
                        "role": "user",
                        "content": user_text
                    }
                ],
                max_tokens=500
            )
            response = completion.choices[0].message.content
            await message.reply_text(f"🤖 *AI Yordamchi:*\n\n{response}", parse_mode=ParseMode.MARKDOWN)
        except Exception as e:
            logger.error(f"AI error: {e}")
            await message.reply_text(
                "❌ Kechirasiz, AI xizmati vaqtinchalik ishlamayapti. Iltimos, keyinroq urinib ko'ring.\n\n"
                "Shu vaqtda bank ma'lumotlarini /start orqali ko'rishingiz mumkin."
            )
        return
    
    # Kredit kalkulyatori
    if context.user_data.get('calc_type') == 'loan':
        step = context.user_data.get('step')
        
        if step == 'loan_amount':
            try:
                amount = float(user_text.replace(' ', ''))
                if amount <= 0:
                    raise ValueError
                context.user_data['loan_amount'] = amount
                context.user_data['step'] = 'loan_rate'
                await message.reply_text(
                    f"💰 Kredit summasi: {amount:,.0f} so'm\n\n"
                    f"Endi yillik foiz stavkasini kiriting (%):\n"
                    f"Masalan: `24`\n\n"
                    f"*Eslatma:* Banklarning stavkalari 22%-40% oralig'ida",
                    parse_mode=ParseMode.MARKDOWN
                )
            except ValueError:
                await message.reply_text("❌ Iltimos, to'g'ri summa kiriting (faqat raqamlar). Masalan: `25000000`")
        
        elif step == 'loan_rate':
            try:
                rate = float(user_text.replace('%', ''))
                if rate <= 0 or rate > 60:
                    raise ValueError
                context.user_data['loan_rate'] = rate
                context.user_data['step'] = 'loan_term'
                await message.reply_text(
                    f"📈 Yillik foiz stavkasi: {rate}%\n\n"
                    f"Endi kredit muddatini oylarda kiriting:\n"
                    f"Masalan: `12`, `24`, `36`, `60`\n\n"
                    f"*Eslatma:* Maksimal muddat 84 oy",
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
                
                # Oylik to'lovni hisoblash (annuitet)
                monthly_rate = rate / 100 / 12
                payment = amount * (monthly_rate * (1 + monthly_rate) ** months) / ((1 + monthly_rate) ** months - 1)
                total_payment = payment * months
                total_interest = total_payment - amount
                
                # Kredit jadvali rasm sifatida
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

📈 *Tavsiya:*
Eng past foizli banklar: Hamkorbank (~22%), Xalq Banki (~22-26%)
Eng uzoq muddatli bank: Xalq Banki (84 oy)
"""
                
                await message.reply_photo(
                    photo=schedule_img,
                    caption=result_text,
                    parse_mode=ParseMode.MARKDOWN
                )
                
                # Kalkulyatorni tozalash
                context.user_data['calc_type'] = None
                context.user_data['step'] = None
                
                # Asosiy menyuga qaytish tugmasi
                keyboard = [[InlineKeyboardButton("🔙 Asosiy menyu", callback_data="back_to_main")]]
                await message.reply_text("👇 Asosiy menyuga qaytish:", reply_markup=InlineKeyboardMarkup(keyboard))
                
            except ValueError:
                await message.reply_text("❌ Iltimos, to'g'ri muddat kiriting (1-120 oy oralig'ida). Masalan: `24`")
    
    # Depozit kalkulyatori
    elif context.user_data.get('calc_type') == 'deposit':
        step = context.user_data.get('step')
        
        if step == 'deposit_amount':
            try:
                amount = float(user_text.replace(' ', ''))
                if amount <= 0:
                    raise ValueError
                context.user_data['deposit_amount'] = amount
                context.user_data['step'] = 'deposit_rate'
                await message.reply_text(
                    f"💵 Depozit summasi: {amount:,.0f} so'm\n\n"
                    f"Endi yillik foiz stavkasini kiriting (%):\n"
                    f"Masalan: `18`\n\n"
                    f"*Eslatma:* Depozit stavkalari 17%-23% oralig'ida",
                    parse_mode=ParseMode.MARKDOWN
                )
            except ValueError:
                await message.reply_text("❌ Iltimos, to'g'ri summa kiriting. Masalan: `10000000`")
        
        elif step == 'deposit_rate':
            try:
                rate = float(user_text.replace('%', ''))
                if rate <= 0 or rate > 30:
                    raise ValueError
                context.user_data['deposit_rate'] = rate
                context.user_data['step'] = 'deposit_term'
                await message.reply_text(
                    f"📈 Yillik foiz stavkasi: {rate}%\n\n"
                    f"Endi depozit muddatini oylarda kiriting:\n"
                    f"Masalan: `6`, `12`, `24`",
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
                
                # Depozit bo'yicha foiz hisoblash
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
                context.user_data['calc_type'] = None
                context.user_data['step'] = None
                
                keyboard = [[InlineKeyboardButton("🔙 Asosiy menyu", callback_data="back_to_main")]]
                await message.reply_text("👇 Asosiy menyuga qaytish:", reply_markup=InlineKeyboardMarkup(keyboard))
                
            except ValueError:
                await message.reply_text("❌ Iltimos, to'g'ri muddat kiriting (1-60 oy oralig'ida).")
    
    # Valyuta konvertori
    elif context.user_data.get('step') == 'currency_amount':
        try:
            amount = float(user_text.replace(' ', ''))
            if amount <= 0:
                raise ValueError
            
            currency = context.user_data.get('currency_from', 'USD')
            converted = amount * EXCHANGE_RATES[currency]
            
            result_text = f"""
💱 *Konvertatsiya natijasi* 💱

{amount:,.2f} {currency} = {converted:,.0f} so'm

📊 *Kurs:* 1 {currency} = {EXCHANGE_RATES[currency]:,} so'm

💡 *Maslahat:* Boshqa konvertatsiya uchun /start ni bosing.
"""
            await message.reply_text(result_text, parse_mode=ParseMode.MARKDOWN)
            
            context.user_data['step'] = None
            keyboard = [[InlineKeyboardButton("🔙 Asosiy menyu", callback_data="back_to_main")]]
            await message.reply_text("👇 Asosiy menyuga qaytish:", reply_markup=InlineKeyboardMarkup(keyboard))
            
        except ValueError:
            await message.reply_text("❌ Iltimos, to'g'ri miqdor kiriting (faqat raqamlar).")
    
    elif context.user_data.get('step') == 'uzs_amount':
        try:
            amount = float(user_text.replace(' ', ''))
            if amount <= 0:
                raise ValueError
            
            # Eng yaqin valyutani taklif qilish
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
            
            context.user_data['step'] = None
            keyboard = [[InlineKeyboardButton("🔙 Asosiy menyu", callback_data="back_to_main")]]
            await message.reply_text("👇 Asosiy menyuga qaytish:", reply_markup=InlineKeyboardMarkup(keyboard))
            
        except ValueError:
            await message.reply_text("❌ Iltimos, to'g'ri miqdor kiriting (faqat raqamlar).")
    
    else:
        # Hech qanday rejimda emas
        await message.reply_text(
            "❓ Tushunarsiz buyruq.\n\n"
            "Yordam uchun /start ni bosing yoki quyidagi buyruqlardan foydalaning:\n"
            "• /start - Asosiy menyu\n"
            "• /cancel - Joriy amalni bekor qilish"
        )

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/cancel komandasi - joriy amalni bekor qilish"""
    context.user_data.clear()
    await update.message.reply_text(
        "✅ Joriy amal bekor qilindi.\n"
        "Yangi buyruq uchun /start ni bosing."
    )

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Xatoliklarni qayta ishlash"""
    logger.error(f"Update {update} caused error {context.error}")
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "❌ Kechirasiz, texnik xatolik yuz berdi. Iltimos, keyinroq qayta urinib ko'ring.\n"
            "Agar muammo takrorlansa, /start ni bosing."
        )

# ==================== ASOSIY FUNKSIYA ====================
def main() -> None:
    """Botni ishga tushirish"""
    # Application yaratish
    application = Application.builder().token(TOKEN).build()
    
    # Handlerlarni qo'shish
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("cancel", cancel))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_error_handler(error_handler)
    
    # Botni ishga tushirish
    print("🤖 Mahalla Agenti Bot ishga tushdi...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
