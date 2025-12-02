from telebot import types
from database import get_nik_from_telegram

def show_registration_menu(message, bot):
    """Show registration menu for new users"""
    keyboard = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    buttons = [
        types.KeyboardButton("Daftar Sekarang"),
        types.KeyboardButton("Bantuan")
    ]
    keyboard.add(*buttons)
    
    welcome_text = """
Selamat Datang di Bot KSA

Anda belum terdaftar dalam sistem. 
Silakan daftar untuk mengakses semua fitur bot.

Fitur yang tersedia setelah pendaftaran:
• Cek Saldo Koperasi
• Kelola Supplier  
• Penerimaan Barang
• Cek Stok Produk
• Kelola Mapping Produk

Klik "Daftar Sekarang" untuk memulai pendaftaran.
"""
    bot.reply_to(message, welcome_text, parse_mode='Markdown', reply_markup=keyboard)

def show_main_menu(message, bot):
    """Show main menu for registered users"""
    keyboard = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    
    buttons = [
        types.KeyboardButton("Cek Saldo"),
        types.KeyboardButton("Supplier Saya"),
        types.KeyboardButton("Penerimaan Barang"),
        types.KeyboardButton("Stok Produk"),
        types.KeyboardButton("Kelola Mapping"),  # MENU BARU
        types.KeyboardButton("Bantuan")
    ]
    
    keyboard.add(*buttons)
    
    welcome_text = """
Selamat Datang di Bot KSA

Silakan pilih menu yang tersedia:

• Cek Saldo - Cek saldo koperasi otomatis
• Supplier Saya - Lihat daftar supplier  
• Penerimaan Barang - Kelola penerimaan barang
• Stok Produk - Lihat stok produk
• Kelola Mapping - Aktif/nonaktif mapping produk per supplier
• Bantuan - Panduan penggunaan

Fitur otomatis:
Saldo dan data akan ditampilkan secara otomatis berdasarkan ID Telegram Anda.
"""
    bot.reply_to(message, welcome_text, parse_mode='Markdown', reply_markup=keyboard)

def handle_start(message, bot):
    """Handle /start command"""
    user_id = str(message.from_user.id)
    
    # Cek apakah user sudah terdaftar
    user_data = get_nik_from_telegram(user_id)
    
    if not user_data:
        # User belum terdaftar, tampilkan menu pendaftaran
        show_registration_menu(message, bot)
    else:
        # User sudah terdaftar, tampilkan menu utama
        show_main_menu(message, bot)