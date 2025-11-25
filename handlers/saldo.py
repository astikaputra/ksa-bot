import datetime
from database import get_nik_from_telegram, connection
from utils.helpers import log, format_rupiah

def handle_cek_saldo(message, bot):
    """Handle cek saldo request"""
    user_id = str(message.from_user.id)
    
    # Dapatkan data user dari database
    user_data = get_nik_from_telegram(user_id)
    
    if not user_data:
        bot.reply_to(
            message, 
            "Data tidak ditemukan\n\n"
            "ID Telegram Anda tidak terdaftar dalam sistem.\n"
            "Silakan daftar terlebih dahulu dengan klik 'Daftar Sekarang'.",
            parse_mode='Markdown'
        )
        return
    
    nik = user_data['nik']
    nama = user_data['nama']
    
    # Proses cek saldo
    try:
        conn = connection()
        if conn is None:
            bot.reply_to(message, "Koneksi database gagal")
            return
        
        with conn.cursor() as sql:
            # Query saldo
            sql.execute("""
                SELECT COALESCE(SUM(setor) - SUM(tarik), 0) as saldo_anda 
                FROM tb_deposit_detil 
                WHERE nik = %s
            """, (nik,))
            
            hasil_sql = sql.fetchone()
            saldo = hasil_sql['saldo_anda'] if hasil_sql else 0

            saldo_rupiah = format_rupiah(saldo)
            
            pesan_balasan = f"SALDO KOPERASI SINDHU ARTHA WIGUNA\n\n"
            pesan_balasan += f"Nama: {nama}\n"
            pesan_balasan += f"NIK: `{nik}`\n"
            pesan_balasan += f"Saldo: *{saldo_rupiah}*\n\n"
            pesan_balasan += f"Update: {datetime.datetime.now().strftime('%d-%m-%Y %H:%M')}"

            bot.reply_to(message, pesan_balasan, parse_mode='Markdown')
            
            # Log activity
            log(message, f'mysaldo_auto_{nik}')

    except Exception as e:
        bot.reply_to(message, f"Terjadi kesalahan: {str(e)}")

def handle_last_upload(message, bot):
    """Handle last upload command"""
    user_id = str(message.from_user.id)
    
    # Dapatkan data user dari database
    user_data = get_nik_from_telegram(user_id)
    
    if not user_data:
        bot.reply_to(
            message, 
            "Data tidak ditemukan\n\n"
            "ID Telegram Anda tidak terdaftar dalam sistem.",
            parse_mode='Markdown'
        )
        return
    
    nik = user_data['nik']
    nama = user_data['nama']
    
    try:
        conn = connection()
        if conn is None:
            bot.reply_to(message, "Koneksi database gagal")
            return
        
        with conn.cursor() as sql:
            # Query last upload
            sql.execute("""
                SELECT keterangan, setor 
                FROM tb_deposit_detil 
                WHERE jenis = 'setor' AND nik = %s 
                ORDER BY id DESC 
                LIMIT 1
            """, (nik,))
            
            hasil_sql = sql.fetchone()

            if not hasil_sql:
                bot.reply_to(
                    message,
                    f"Tidak Ada Data Upload\n\n"
                    f"Nama: {nama}\n"
                    f"NIK: `{nik}`\n\n"
                    f"Belum ada data upload untuk NIK Anda.",
                    parse_mode='Markdown'
                )
                return

            keterangan = hasil_sql['keterangan'] or "Tidak ada keterangan"
            setor = hasil_sql['setor'] or 0

            setor_rupiah = format_rupiah(setor)

            pesan_balasan = f"SALDO TERAKHIR DIUPLOAD\n\n"
            pesan_balasan += f"Nama: {nama}\n"
            pesan_balasan += f"NIK: `{nik}`\n"
            pesan_balasan += f"Keterangan: {keterangan}\n"
            pesan_balasan += f"Jumlah: *{setor_rupiah}*\n\n"
            pesan_balasan += f"Tanggal Update: {datetime.datetime.now().strftime('%d-%m-%Y %H:%M')}"

            bot.reply_to(message, pesan_balasan, parse_mode='Markdown')
            
            # Log activity
            log(message, f'lastupload_auto_{nik}')

    except Exception as e:
        bot.reply_to(message, f"Terjadi kesalahan: {str(e)}")