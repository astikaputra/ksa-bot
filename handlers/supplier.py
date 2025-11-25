from telebot import types
from database import get_nik_from_telegram, connection
from utils.helpers import log

def handle_mysupplier(message, bot):
    """Handle supplier list request"""
    log(message, 'mysupplier')
    
    user_id = str(message.from_user.id)
    
    # Cek apakah user terdaftar
    user_data = get_nik_from_telegram(user_id)
    if not user_data:
        bot.reply_to(
            message, 
            "Data tidak ditemukan\n\nID Telegram Anda tidak terdaftar. Silakan daftar terlebih dahulu.",
            parse_mode='Markdown'
        )
        return
    
    conn = connection()
    if conn is None:
        bot.reply_to(message, "Koneksi database gagal", parse_mode='Markdown')
        return
    
    try:
        with conn.cursor() as sql:
            sql.execute("""
                SELECT 
                    s.id AS id_supplier,
                    s.namasuplier AS nama_supplier,
                    s.alamat,
                    s.notlp,
                    s.person
                FROM 
                    tb_suplier s
                JOIN 
                    tb_karyawan k ON s.id_karyawan = k.id
                WHERE 
                    k.id_tele = %s
                    AND s.aktif = 'Y'
                    AND k.aktif = 'Y'
                ORDER BY s.namasuplier
            """, (user_id,))
            
            hasil_sql = sql.fetchall()
            
            if hasil_sql:
                # Buat tombol inline untuk supplier
                keyboard = types.InlineKeyboardMarkup(row_width=1)
                
                for supplier in hasil_sql:
                    id_supplier = supplier['id_supplier']
                    nama_supplier = supplier['nama_supplier']
                    button = types.InlineKeyboardButton(
                        text=nama_supplier,
                        callback_data=f"supplier_{id_supplier}"
                    )
                    keyboard.add(button)
                
                pesan_balasan = f"SUPPLIER SAYA\n\n"
                pesan_balasan += f"Nama: {user_data['nama']}\n"
                pesan_balasan += f"NIK: `{user_data['nik']}`\n\n"
                pesan_balasan += f"Total {len(hasil_sql)} supplier aktif\nKlik untuk melihat detail:"
                
                bot.send_message(
                    message.chat.id,
                    pesan_balasan,
                    parse_mode='Markdown',
                    reply_markup=keyboard
                )
                
            else:
                pesan_balasan = f"TIDAK ADA SUPPLIER\n\n"
                pesan_balasan += f"Nama: {user_data['nama']}\n"
                pesan_balasan += f"NIK: `{user_data['nik']}`\n\n"
                pesan_balasan += "Anda tidak terdaftar sebagai supplier aktif."
                bot.reply_to(message, pesan_balasan, parse_mode='Markdown')
            
    except Exception as e:
        bot.reply_to(message, f"Error: {str(e)}")
    finally:
        if conn and conn.open:
            conn.close()

def handle_supplier_callback(call, bot):
    """Handle supplier detail callback"""
    supplier_id = call.data.replace('supplier_', '')
    
    conn = connection()
    if conn is None:
        bot.answer_callback_query(call.id, "Koneksi database gagal")
        return
    
    try:
        with conn.cursor() as sql:
            # Query detail supplier berdasarkan ID
            sql.execute("""
                SELECT 
                    s.namasuplier,
                    s.alamat,
                    s.email,
                    s.notlp,
                    s.person,
                    s.aktif
                FROM tb_suplier s
                WHERE s.id = %s
            """, (supplier_id,))
            
            supplier_data = sql.fetchone()
            
            if supplier_data:
                nama_supplier = supplier_data['namasuplier'] or "Tidak ada"
                alamat = supplier_data['alamat'] or "Tidak ada"
                email = supplier_data['email'] or "Tidak ada"
                telepon = supplier_data['notlp'] or "Tidak ada"
                contact_person = supplier_data['person'] or "Tidak ada"
                status = "Aktif" if supplier_data['aktif'] == 'Y' else "Non-aktif"
                
                # Buat pesan detail
                detail_pesan = f"DETAIL SUPPLIER\n\n"
                detail_pesan += f"Nama: {nama_supplier}\n"
                detail_pesan += f"Contact Person: {contact_person}\n"
                detail_pesan += f"Alamat: {alamat}\n"
                detail_pesan += f"Telepon: {telepon}\n"
                detail_pesan += f"Email: {email}\n"
                detail_pesan += f"Status: {status}\n"
                
                # Tombol aksi untuk supplier
                keyboard = types.InlineKeyboardMarkup()
                keyboard.row(
                    types.InlineKeyboardButton("Lihat Stok", callback_data=f"stock_{supplier_id}_page_1")
                )
                keyboard.row(
                    types.InlineKeyboardButton("Kembali ke List", callback_data="back_to_list")
                )
                
                # Edit pesan sebelumnya
                bot.edit_message_text(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    text=detail_pesan,
                    parse_mode='Markdown',
                    reply_markup=keyboard
                )
                
            else:
                bot.answer_callback_query(call.id, "Data supplier tidak ditemukan")
                
    except Exception as e:
        bot.answer_callback_query(call.id, f"Error: {str(e)}")
    finally:
        if conn and conn.open:
            conn.close()