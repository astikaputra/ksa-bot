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
    from handlers.saldo import handle_last_upload
    handle_last_upload(message, bot)

@bot.message_handler(func=lambda message: True)
def handle_text_messages(message):
    user_id = str(message.from_user.id)
    
    if message.text == "Daftar Sekarang":
        from handlers.registration import handle_start_registration
        handle_start_registration(message, bot)
    elif message.text == "Cek Saldo":
        from handlers.saldo import handle_cek_saldo
        handle_cek_saldo(message, bot)
    elif message.text == "Supplier Saya":
        from handlers.supplier import handle_mysupplier
        handle_mysupplier(message, bot)
    elif message.text == "Penerimaan Barang":
        from handlers.penerimaan import handle_penerimaan_menu
        handle_penerimaan_menu(message, bot)
    elif message.text == "Stok Produk":
        from handlers.stok import handle_stok_produk
        handle_stok_produk(message, bot)
    elif message.text == "Kelola Mapping":
        from handlers.penerimaan import handle_manage_mapping_menu
        handle_manage_mapping_menu(message, bot)
    elif message.text == "Bantuan":
        from handlers.help import handle_help
        handle_help(message, bot)
    elif user_id in user_states:
        # Handle input selama proses penerimaan atau pendaftaran
        if user_states[user_id].get('type') == 'registration':
            from handlers.registration import handle_registration_input
            handle_registration_input(message, bot)
        else:
            from handlers.penerimaan import handle_penerimaan_input
            handle_penerimaan_input(message, bot)
    else:
        # Cek status user
        user_data = get_nik_from_telegram(user_id)
        if not user_data:
            from handlers.start import show_registration_menu
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
    from handlers.registration import handle_registration_callbacks
    handle_registration_callbacks(call, bot)

@bot.callback_query_handler(func=lambda call: call.data.startswith('supplier_'))
def handle_supplier_callback_wrapper(call):
    from handlers.supplier import handle_supplier_callback
    handle_supplier_callback(call, bot)

@bot.callback_query_handler(func=lambda call: call.data.startswith('stock_'))
def handle_stock_callback_wrapper(call):
    from handlers.stok import handle_stock_callback
    handle_stock_callback(call, bot)

@bot.callback_query_handler(func=lambda call: call.data.startswith('penerimaan_'))
def handle_penerimaan_callback(call):
    from handlers.penerimaan import handle_penerimaan_supplier
    handle_penerimaan_supplier(call, bot)

@bot.callback_query_handler(func=lambda call: call.data.startswith('pilih_supplier_'))
def handle_pilih_supplier_callback(call):
    from handlers.penerimaan import handle_pilih_supplier
    handle_pilih_supplier(call, bot)

@bot.callback_query_handler(func=lambda call: call.data.startswith('pilih_produk_'))
def handle_pilih_produk_callback(call):
    from handlers.penerimaan import handle_pilih_produk
    handle_pilih_produk(call, bot)

@bot.callback_query_handler(func=lambda call: call.data.startswith('produk_page_'))
def handle_produk_paging_callback(call):
    from handlers.penerimaan import handle_produk_paging
    handle_produk_paging(call, bot)

@bot.callback_query_handler(func=lambda call: call.data == 'lihat_item')
def handle_lihat_item_callback(call):
    from handlers.penerimaan import handle_lihat_item
    handle_lihat_item(call, bot)

@bot.callback_query_handler(func=lambda call: call.data == 'simpan_penerimaan')
def handle_simpan_penerimaan_callback(call):
    from handlers.penerimaan import handle_simpan_penerimaan
    handle_simpan_penerimaan(call, bot)

@bot.callback_query_handler(func=lambda call: call.data == 'batal_penerimaan')
def handle_batal_penerimaan_callback(call):
    from handlers.penerimaan import handle_batal_penerimaan
    handle_batal_penerimaan(call, bot)

@bot.callback_query_handler(func=lambda call: call.data == 'konfirmasi_simpan_harga_0')
def handle_konfirmasi_simpan_callback(call):
    from handlers.penerimaan import handle_konfirmasi_simpan_harga_0
    handle_konfirmasi_simpan_harga_0(call, bot)

@bot.callback_query_handler(func=lambda call: call.data == 'gunakan_faktur_otomatis')
def handle_gunakan_faktur_callback(call):
    from handlers.penerimaan import handle_gunakan_faktur_otomatis
    handle_gunakan_faktur_otomatis(call, bot)

@bot.callback_query_handler(func=lambda call: call.data == 'input_faktur_manual')
def handle_input_faktur_callback(call):
    from handlers.penerimaan import handle_input_faktur_manual
    handle_input_faktur_manual(call, bot)

@bot.callback_query_handler(func=lambda call: call.data == "kembali_ke_produk")
def handle_kembali_ke_produk_callback(call):
    from handlers.penerimaan import handle_kembali_ke_produk
    handle_kembali_ke_produk(call, bot)

# ============================ HANDLER UNTUK KELOLA MAPPING ============================

@bot.callback_query_handler(func=lambda call: call.data.startswith('manage_mapping_'))
def handle_manage_mapping_callback(call):
    from handlers.penerimaan import handle_manage_mapping_supplier
    handle_manage_mapping_supplier(call, bot)

@bot.callback_query_handler(func=lambda call: call.data.startswith('toggle_mapping_'))
def handle_toggle_mapping_callback(call):
    from handlers.penerimaan import handle_toggle_mapping
    handle_toggle_mapping(call, bot)

@bot.callback_query_handler(func=lambda call: call.data.startswith('filter_mapping_'))
def handle_filter_mapping_callback(call):
    from handlers.penerimaan import handle_filter_mapping
    handle_filter_mapping(call, bot)

@bot.callback_query_handler(func=lambda call: call.data == 'back_to_mapping_menu')
def handle_back_to_mapping_menu(call):
    """Handler untuk kembali ke menu mapping"""
    # Buat pesan baru untuk trigger mapping menu
    message = types.Message(
        message_id=call.message.message_id + 1,
        from_user=call.from_user,
        date=call.message.date,
        chat=call.message.chat,
        content_type='text',
        options=[],
        json_string=''
    )
    message.text = 'Kelola Mapping'
    
    # Panggil handler mapping menu
    from handlers.penerimaan import handle_manage_mapping_menu
    handle_manage_mapping_menu(message, bot)

@bot.callback_query_handler(func=lambda call: call.data == 'back_to_main_menu')
def handle_back_to_main_menu(call):
    """Handler untuk kembali ke menu utama"""
    # Buat pesan baru untuk trigger start
    message = types.Message(
        message_id=call.message.message_id + 1,
        from_user=call.from_user,
        date=call.message.date,
        chat=call.message.chat,
        content_type='text',
        options=[],
        json_string=''
    )
    message.text = '/start'
    
    # Panggil handler start
    handle_start(message, bot)

@bot.callback_query_handler(func=lambda call: call.data.startswith('add_mapping_'))
def handle_add_mapping(call):
    """Handler untuk tambah mapping baru"""
    supplier_id = call.data.replace('add_mapping_', '')
    bot.answer_callback_query(call.id, "Fitur tambah mapping sedang dikembangan")

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
    from handlers.penerimaan import handle_penerimaan_menu
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
    from handlers.stok import handle_stok_produk
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
    from handlers.penerimaan import handle_penerimaan_menu
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
    from handlers.supplier import handle_mysupplier
    handle_mysupplier(message, bot)

@bot.callback_query_handler(func=lambda call: call.data == "refresh_supplier")
def handle_refresh_supplier(call):
    """Handler untuk refresh data supplier"""
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
    message.text = '/start'
    handle_start(message, bot)

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