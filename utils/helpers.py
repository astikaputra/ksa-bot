import datetime
from config import config

def log(message, perintah):
    """Log user activity"""
    try:
        tanggal = datetime.datetime.now().strftime('%d-%B-%Y')
        nama_awal = message.chat.first_name or ''
        nama_akhir = message.chat.last_name or ''
        id_user = message.chat.id
        
        text_log = f'{tanggal}, {id_user}, {nama_awal} {nama_akhir}, {perintah}\n'
        
        with open(config.LOG_FILE, 'a', encoding='utf-8') as log_bot:
            log_bot.write(text_log)
    except Exception as e:
        print(f"Error writing log: {e}")

def format_rupiah(amount):
    """Format number to Rupiah currency"""
    try:
        if amount is None:
            amount = 0
        return f"Rp {float(amount):,.2f}".replace(',', 'temp').replace('.', ',').replace('temp', '.')
    except:
        return "Rp 0"

def validate_nik(nik):
    """Validate NIK format"""
    if not nik or not nik.isdigit() or len(nik) != 10:
        return False
    return True

def get_chat_info_from_source(source):
    """Get chat_id and message_id from either Message or CallbackQuery"""
    if hasattr(source, 'message'):  # CallbackQuery
        return source.message.chat.id, source.message.message_id
    else:  # Message
        return source.chat.id, source.message_id

def send_or_edit_message(bot, source, text, reply_markup=None, parse_mode='Markdown'):
    """Send or edit message based on source type"""
    chat_id, message_id = get_chat_info_from_source(source)
    
    if hasattr(source, 'message'):  # CallbackQuery - edit existing message
        try:
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=text,
                parse_mode=parse_mode,
                reply_markup=reply_markup
            )
        except Exception as e:
            # Jika edit gagal, kirim pesan baru
            bot.send_message(
                chat_id,
                text,
                parse_mode=parse_mode,
                reply_markup=reply_markup
            )
    else:  # Message - send new message
        bot.reply_to(
            source,
            text,
            parse_mode=parse_mode,
            reply_markup=reply_markup
        )