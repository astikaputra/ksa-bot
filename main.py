import telebot
from telebot import types

# Import config
from config import config

# Import handlers
from handlers.start import handle_start, show_registration_menu, show_main_menu
from handlers.registration import handle_start_registration, handle_registration_input, handle_registration_callbacks
from handlers.saldo import handle_cek_saldo, handle_last_upload
from handlers.supplier import handle_mysupplier, handle_supplier_callback
from handlers.stok import handle_stok_produk, handle_stock_callback
from handlers.penerimaan import (
    handle_penerimaan_menu, handle_penerimaan_supplier, handle_pilih_supplier,
    handle_penerimaan_input, handle_pilih_produk, handle_produk_paging,
    handle_lihat_item, handle_simpan_penerimaan, handle_batal_penerimaan,
    handle_konfirmasi_simpan_harga_0, handle_gunakan_faktur_otomatis,
    handle_input_faktur_manual, handle_kembali_ke_produk,
    user_states, paging_states
)
from handlers.help import handle_help

# Import database
from database import get_nik_from_telegram

# Initialize bot
bot = telebot.TeleBot(config.BOT_TOKEN)

# ============================ MAIN MESSAGE HANDLERS ============================

@bot.message_handler(commands=['start'])
def handle_start_command(message):
    handle_start(message, bot)

@bot.message_handler(commands=['lastupload'])
def handle_last_upload_command(message):
    handle_last_upload(message, bot)

@bot.message_handler(func=lambda message: True)
def handle_text_messages(message):
    user_id = str(message.from_user.id)
    
    if message.text == "Daftar Sekarang":
        handle_start_registration(message, bot)
    elif message.text == "Cek Saldo":
        handle_cek_saldo(message, bot)
    elif message.text == "Supplier Saya":
        handle_mysupplier(message, bot)
    elif message.text == "Penerimaan Barang":
        handle_penerimaan_menu(message, bot)
    elif message.text == "Stok Produk":
        handle_stok_produk(message, bot)
    elif message.text == "Bantuan":
        handle_help(message, bot)
    elif user_id in user_states:
        # Handle input selama proses penerimaan atau pendaftaran
        if user_states[user_id].get('type') == 'registration':
            handle_registration_input(message, bot)
        else:
            handle_penerimaan_input(message, bot)
    else:
        # Cek status user
        user_data = get_nik_from_telegram(user_id)
        if not user_data:
            show_registration_menu(message, bot)
        else:
            bot.reply_to(message, "Perintah tidak dikenali\n\nGunakan tombol menu atau ketik /start untuk melihat menu utama.", parse_mode='Markdown')

# ============================ CALLBACK QUERY HANDLERS ============================

@bot.callback_query_handler(func=lambda call: call.data == "no_action")
def handle_no_action(call):
    """Handler untuk tombol yang tidak melakukan action"""
    bot.answer_callback_query(call.id, "Halaman saat ini", show_alert=False)

@bot.callback_query_handler(func=lambda call: call.data in ['confirm_registration', 'change_nik'])
def handle_registration_callback(call):
    handle_registration_callbacks(call, bot)

@bot.callback_query_handler(func=lambda call: call.data.startswith('supplier_'))
def handle_supplier_callback_wrapper(call):
    handle_supplier_callback(call, bot)

@bot.callback_query_handler(func=lambda call: call.data.startswith('stock_'))
def handle_stock_callback_wrapper(call):
    handle_stock_callback(call, bot)

@bot.callback_query_handler(func=lambda call: call.data.startswith('penerimaan_'))
def handle_penerimaan_callback(call):
    handle_penerimaan_supplier(call, bot)

@bot.callback_query_handler(func=lambda call: call.data.startswith('pilih_supplier_'))
def handle_pilih_supplier_callback(call):
    handle_pilih_supplier(call, bot)

@bot.callback_query_handler(func=lambda call: call.data.startswith('pilih_produk_'))
def handle_pilih_produk_callback(call):
    handle_pilih_produk(call, bot)

@bot.callback_query_handler(func=lambda call: call.data.startswith('produk_page_'))
def handle_produk_paging_callback(call):
    handle_produk_paging(call, bot)

@bot.callback_query_handler(func=lambda call: call.data == 'lihat_item')
def handle_lihat_item_callback(call):
    handle_lihat_item(call, bot)

@bot.callback_query_handler(func=lambda call: call.data == 'simpan_penerimaan')
def handle_simpan_penerimaan_callback(call):
    handle_simpan_penerimaan(call, bot)

@bot.callback_query_handler(func=lambda call: call.data == 'batal_penerimaan')
def handle_batal_penerimaan_callback(call):
    handle_batal_penerimaan(call, bot)

@bot.callback_query_handler(func=lambda call: call.data == 'konfirmasi_simpan_harga_0')
def handle_konfirmasi_simpan_callback(call):
    handle_konfirmasi_simpan_harga_0(call, bot)

@bot.callback_query_handler(func=lambda call: call.data == 'gunakan_faktur_otomatis')
def handle_gunakan_faktur_callback(call):
    handle_gunakan_faktur_otomatis(call, bot)

@bot.callback_query_handler(func=lambda call: call.data == 'input_faktur_manual')
def handle_input_faktur_callback(call):
    handle_input_faktur_manual(call, bot)

# Additional callback handlers
@bot.callback_query_handler(func=lambda call: call.data == "refresh_penerimaan")
def handle_refresh_penerimaan(call):
    """Handler untuk refresh data penerimaan"""
    bot.delete_message(call.message.chat.id, call.message.message_id)
    message = types.Message(
        message_id=call.message.message_id + 1,
        from_user=call.from_user,
        date=call.message.date,
        chat=call.message.chat,
        content_type='text',
        options=[],
        json_string=''
    )
    message.text = 'Penerimaan Barang'
    handle_penerimaan_menu(message, bot)
    bot.answer_callback_query(call.id, "Data diperbarui")

@bot.callback_query_handler(func=lambda call: call.data == "back_to_stok_menu")
def handle_back_to_stok_menu(call):
    """Handler untuk kembali ke menu stok"""
    bot.delete_message(call.message.chat.id, call.message.message_id)
    message = types.Message(
        message_id=call.message.message_id + 1,
        from_user=call.from_user,
        date=call.message.date,
        chat=call.message.chat,
        content_type='text',
        options=[],
        json_string=''
    )
    message.text = 'Stok Produk'
    handle_stok_produk(message, bot)

@bot.callback_query_handler(func=lambda call: call.data == "back_to_penerimaan_menu")
def handle_back_to_penerimaan_menu(call):
    """Handler untuk kembali ke menu penerimaan"""
    bot.delete_message(call.message.chat.id, call.message.message_id)
    message = types.Message(
        message_id=call.message.message_id + 1,
        from_user=call.from_user,
        date=call.message.date,
        chat=call.message.chat,
        content_type='text',
        options=[],
        json_string=''
    )
    message.text = 'Penerimaan Barang'
    handle_penerimaan_menu(message, bot)

@bot.callback_query_handler(func=lambda call: call.data == "back_to_list")
def handle_back_to_list(call):
    """Handler untuk kembali ke list supplier"""
    bot.delete_message(call.message.chat.id, call.message.message_id)
    message = types.Message(
        message_id=call.message.message_id + 1,
        from_user=call.from_user,
        date=call.message.date,
        chat=call.message.chat,
        content_type='text',
        options=[],
        json_string=''
    )
    message.text = 'Supplier Saya'
    handle_mysupplier(message, bot)

@bot.callback_query_handler(func=lambda call: call.data == "kembali_ke_produk")
def handle_kembali_ke_produk_callback(call):
    """Handler untuk kembali ke pilihan produk"""
    from handlers.penerimaan import handle_kembali_ke_produk as handler
    handler(call, bot)
# ============================ START BOT ============================

if __name__ == "__main__":
    print('Bot KSA berhasil dijalankan!')
    
    # Check if bot token is configured
    if not config.BOT_TOKEN or config.BOT_TOKEN == 'your_bot_token_here':
        print("ERROR: Bot token belum dikonfigurasi. Silakan edit file config.txt")
        exit(1)
    
    try:
        bot.polling(none_stop=True)
    except Exception as e:
        print(f'Bot error: {e}')