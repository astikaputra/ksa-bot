from database import get_nik_from_telegram

def handle_help(message, bot):
    """Handle help command"""
    user_id = str(message.from_user.id)
    user_data = get_nik_from_telegram(user_id)
    
    if user_data:
        user_info = f"Nama: {user_data['nama']}\nNIK: `{user_data['nik']}`\n\n"
        features = """
FITUR YANG TERSEDIA:

1. Cek Saldo
   - Saldo akan ditampilkan otomatis
   - Berdasarkan NIK dari ID Telegram Anda

2. Supplier Saya
   - Lihat daftar supplier yang terkait dengan Anda
   - Klik supplier untuk melihat detail

3. Penerimaan Barang
   - Lihat riwayat penerimaan
   - Tambah penerimaan baru

4. Stok Produk
   - Lihat stok produk per supplier
"""
    else:
        user_info = "Status: ID Telegram belum terdaftar\n\n"
        features = """
SILAKAN DAFTAR TERLEBIH DAHULU:

Klik "Daftar Sekarang" untuk mendaftarkan ID Telegram Anda ke sistem.

Setelah pendaftaran, Anda dapat mengakses semua fitur di atas.
"""
    
    help_text = f"""
BOT KSA - PANDUAN PENGGUNAAN

{user_info}
CARA PENGGUNAAN:
{features}

FITUR OTOMATIS:
- Tidak perlu input NIK manual
- Data diambil otomatis dari sistem
- Hanya user terdaftar yang bisa mengakses

COMMAND TAMBAHAN:
/lastupload - Cek saldo terakhir diupload
/start - Menu utama

CONTACT ADMIN:
Jika mengalami kendala atau butuh bantuan.
"""
    bot.reply_to(message, help_text, parse_mode='Markdown')