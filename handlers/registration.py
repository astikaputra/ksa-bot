import datetime
from telebot import types
from database import connection, get_nik_from_telegram
from utils.helpers import validate_nik

# State management
user_states = {}

def handle_start_registration(message, bot):
    """Start registration process"""
    user_id = str(message.from_user.id)
    
    # Cek apakah user sudah terdaftar
    existing_user = get_nik_from_telegram(user_id)
    if existing_user:
        bot.reply_to(message, f"Anda sudah terdaftar!\n\nNama: {existing_user['nama']}\nNIK: {existing_user['nik']}\n\nGunakan menu lain untuk mengakses fitur.", parse_mode='Markdown')
        return
    
    # Mulai proses pendaftaran
    user_states[user_id] = {
        'type': 'registration',
        'state': 'waiting_for_nik',
        'data': {}
    }
    
    # Tampilkan instruksi pendaftaran
    bot.send_message(
        message.chat.id,
        "PENDAFTARAN USER BARU\n\n"
        "Silakan ikuti langkah-langkah berikut:\n\n"
        "1. Masukkan NIK Karyawan Anda\n"
        "2. Konfirmasi data\n"
        "3. Selesai\n\n"
        "Langkah 1: Masukkan NIK karyawan Anda (10 digit angka):",
        parse_mode='Markdown'
    )

def handle_registration_input(message, bot):
    """Handle registration input"""
    user_id = str(message.from_user.id)
    
    if user_id not in user_states or user_states[user_id].get('type') != 'registration':
        return
    
    user_state = user_states[user_id]
    
    if user_state['state'] == 'waiting_for_nik':
        # Validasi NIK
        nik = message.text.strip()
        
        if not validate_nik(nik):
            bot.reply_to(message, "NIK harus berupa 10 digit angka. Silakan masukkan kembali NIK Anda:")
            return
        
        # Cek apakah NIK ada di database
        conn = connection()
        if conn is None:
            bot.reply_to(message, "Koneksi database gagal. Silakan coba lagi.")
            return
        
        try:
            with conn.cursor() as sql:
                sql.execute("""
                    SELECT nik, nama
                    FROM tb_karyawan 
                    WHERE nik = %s AND aktif = 'Y'
                """, (nik,))
                
                result = sql.fetchone()
                
                if result:
                    # NIK ditemukan, simpan data dan minta konfirmasi
                    user_state['data'] = {
                        'nik': result['nik'],
                        'nama': result['nama']
                    }
                    user_state['state'] = 'waiting_for_confirmation'
                    
                    # Tampilkan data untuk konfirmasi
                    confirm_text = f"""
DATA DITEMUKAN

Silakan konfirmasi data berikut:

NIK: {result['nik']}
Nama: {result['nama']}

Apakah data di atas benar?
"""
                    keyboard = types.InlineKeyboardMarkup()
                    keyboard.row(
                        types.InlineKeyboardButton("Ya, Data Benar", callback_data="confirm_registration"),
                        types.InlineKeyboardButton("Tidak, Ubah NIK", callback_data="change_nik")
                    )
                    
                    bot.send_message(
                        message.chat.id,
                        confirm_text,
                        parse_mode='Markdown',
                        reply_markup=keyboard
                    )
                    
                else:
                    # NIK tidak ditemukan
                    bot.reply_to(
                        message,
                        f"NIK {nik} tidak ditemukan dalam database karyawan aktif.\n\n"
                        "Pastikan:\n"
                        "• NIK yang dimasukkan benar (10 digit)\n"
                        "• Anda adalah karyawan aktif\n"
                        "• Data sudah terdaftar di sistem\n\n"
                        "Silakan masukkan NIK kembali atau hubungi admin untuk bantuan:"
                    )
                    
        except Exception as e:
            bot.reply_to(message, f"Error: {str(e)}")
        finally:
            if conn and conn.open:
                conn.close()
    
    elif user_state['state'] == 'waiting_for_confirmation':
        # Handle konfirmasi manual (jika user mengetik)
        if message.text.lower() in ['ya', 'yes', 'benar', 'correct']:
            complete_registration(user_id, message.chat.id, bot)
        elif message.text.lower() in ['tidak', 'no', 'salah', 'wrong']:
            user_state['state'] = 'waiting_for_nik'
            bot.reply_to(message, "Silakan masukkan NIK yang benar:")
        else:
            bot.reply_to(message, "Silakan pilih 'Ya' atau 'Tidak' untuk konfirmasi data.")

def complete_registration(user_id, chat_id, bot):
    """Complete registration process"""
    user_state = user_states[user_id]
    user_data = user_state['data']
    
    conn = connection()
    if conn is None:
        bot.send_message(chat_id, "Koneksi database gagal. Silakan coba lagi.")
        return
    
    try:
        with conn.cursor() as sql:
            # Update ID Telegram di database
            sql.execute("""
                UPDATE tb_karyawan 
                SET id_tele = %s 
                WHERE nik = %s AND aktif = 'Y'
            """, (user_id, user_data['nik']))
            
            if sql.rowcount > 0:
                conn.commit()
                
                # Hapus state user
                del user_states[user_id]
                
                # Kirim pesan sukses
                success_text = f"""
PENDAFTARAN BERHASIL! ✅

Selamat {user_data['nama']}, 
Anda telah terdaftar di Bot KSA.

Detail akun:
NIK: {user_data['nik']}
Nama: {user_data['nama']}

Sekarang Anda dapat mengakses semua fitur bot.
"""
                bot.send_message(chat_id, success_text, parse_mode='Markdown')
                
            else:
                bot.send_message(chat_id, "Gagal menyimpan data. Silakan hubungi admin.")
                
    except Exception as e:
        conn.rollback()
        bot.send_message(chat_id, f"Error saat menyimpan data: {str(e)}")
    finally:
        if conn and conn.open:
            conn.close()

def handle_registration_callbacks(call, bot):
    """Handle registration callbacks"""
    user_id = str(call.from_user.id)
    
    if user_id not in user_states or user_states[user_id].get('type') != 'registration':
        bot.answer_callback_query(call.id, "Tidak ada proses pendaftaran aktif")
        return
    
    if call.data == 'confirm_registration':
        # Konfirmasi pendaftaran
        complete_registration(user_id, call.message.chat.id, bot)
        bot.answer_callback_query(call.id, "Menyimpan data...")
        
    elif call.data == 'change_nik':
        # Ubah NIK
        user_states[user_id]['state'] = 'waiting_for_nik'
        user_states[user_id]['data'] = {}
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="Silakan masukkan NIK Anda kembali:",
            parse_mode='Markdown'
        )
        bot.answer_callback_query(call.id, "Masukkan NIK baru")