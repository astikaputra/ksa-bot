from telebot import types
from database import get_nik_from_telegram, connection, get_nama_satuan
from utils.helpers import format_rupiah

def handle_stok_produk(message, bot):
    """Handle stok produk request"""
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
                    s.namasuplier AS nama_supplier
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
                keyboard = types.InlineKeyboardMarkup(row_width=1)
                
                for supplier in hasil_sql:
                    id_supplier = supplier['id_supplier']
                    nama_supplier = supplier['nama_supplier']
                    button = types.InlineKeyboardButton(
                        text=nama_supplier,
                        callback_data=f"stock_{id_supplier}_page_1"
                    )
                    keyboard.add(button)
                
                pesan_balasan = f"📦 STOK PRODUK\n\n"
                pesan_balasan += f"Nama: **{user_data['nama']}**\n"
                pesan_balasan += f"Total Supplier: **{len(hasil_sql)}**\n\n"
                pesan_balasan += "Pilih supplier untuk melihat stok:"
                
                bot.send_message(
                    message.chat.id,
                    pesan_balasan,
                    parse_mode='Markdown',
                    reply_markup=keyboard
                )
                
            else:
                pesan_balasan = f"📦 TIDAK ADA SUPPLIER\n\n"
                pesan_balasan += f"Nama: **{user_data['nama']}**\n\n"
                pesan_balasan += "Anda tidak terdaftar sebagai supplier aktif."
                bot.reply_to(message, pesan_balasan, parse_mode='Markdown')
            
    except Exception as e:
        bot.reply_to(message, f"Error: {str(e)}")
    finally:
        if conn and conn.open:
            conn.close()

def handle_stock_callback(call, bot):
    """Handle stock callback with paging"""
    supplier_id = call.data.replace('stock_', '')
    
    # Parse page number dari callback data jika ada
    page = 1
    if '_page_' in supplier_id:
        parts = supplier_id.split('_page_')
        supplier_id = parts[0]
        page = int(parts[1])
    
    conn = connection()
    if conn is None:
        bot.send_message(call.message.chat.id, "Koneksi database gagal")
        return
    
    try:
        with conn.cursor() as sql:
            # Query untuk mendapatkan nama supplier
            sql.execute("SELECT namasuplier FROM tb_suplier WHERE id = %s", (supplier_id,))
            supplier_data = sql.fetchone()
            nama_supplier = supplier_data['namasuplier'] if supplier_data else "Supplier"
            
            # Hitung total data untuk paging
            sql.execute("""
                SELECT COUNT(*) as total
                FROM tbl_produk p
                INNER JOIN tb_suplieritem si ON p.id_produk = si.iditem
                WHERE si.idsuplier = %s 
                    AND si.aktif = 'Y'
                    AND p.aktif = 'Y'
            """, (supplier_id,))
            
            total_data = sql.fetchone()['total']
            items_per_page = 10
            total_pages = max(1, (total_data + items_per_page - 1) // items_per_page)
            
            # Validasi page number
            if page < 1:
                page = 1
            elif page > total_pages:
                page = total_pages
            
            # Calculate offset
            offset = (page - 1) * items_per_page
            
            # Query stok produk dengan paging dan data satuan
            sql.execute("""
                SELECT 
                    p.id_produk,
                    p.nama_produk,
                    p.deskripsi,
                    p.stok,
                    p.harga,
                    p.satuanbesar,
                    p.satuankecil,
                    p.isi,
                    p.kategori,
                    p.barcode,
                    p.min,
                    p.max,
                    p.aktif,
                    si.harga AS harga_supplier,
                    si.satuan AS satuan_supplier,
                    si.isi AS isi_supplier,
                    si.aktif AS status_mapping
                FROM tbl_produk p
                INNER JOIN tb_suplieritem si ON p.id_produk = si.iditem
                WHERE si.idsuplier = %s 
                    AND si.aktif = 'Y'
                    AND p.aktif = 'Y'
                ORDER BY p.nama_produk
                LIMIT %s OFFSET %s
            """, (supplier_id, items_per_page, offset))
            
            hasil_stok = sql.fetchall()
            
            if hasil_stok or total_data > 0:
                # Buat pesan stok dengan info paging
                stok_pesan = f"📦 DATA STOK PRODUK\n\n"
                stok_pesan += f"**Supplier:** {nama_supplier}\n"
                stok_pesan += f"**Halaman:** {page}/{total_pages}\n"
                stok_pesan += f"**Total Produk:** {total_data} item\n\n"
                
                if hasil_stok:
                    for i, produk in enumerate(hasil_stok, 1):
                        id_produk = produk['id_produk']
                        nama_produk = produk['nama_produk'] or "Tidak ada nama"
                        deskripsi = produk['deskripsi'] or "-"
                        stok = produk['stok'] or 0
                        harga_jual = produk['harga'] or 0
                        satuan_besar_id = produk['satuanbesar']
                        satuan_kecil_id = produk['satuankecil']
                        isi = produk['isi'] or 1
                        min_stok = produk['min'] or 0
                        max_stok = produk['max'] or 0
                        harga_supplier = produk['harga_supplier'] or 0
                        
                        # Dapatkan nama satuan dari tb_satuan
                        satuan_besar = get_nama_satuan(satuan_besar_id)
                        satuan_kecil = get_nama_satuan(satuan_kecil_id)
                        
                        # Format harga ke Rupiah
                        harga_jual_rupiah = format_rupiah(harga_jual)
                        harga_supplier_rupiah = format_rupiah(harga_supplier)
                        
                        # Tentukan status stok
                        if stok <= min_stok:
                            status_stok = "🔴 LOW"
                        elif stok >= max_stok:
                            status_stok = "🟢 FULL"
                        else:
                            status_stok = "🟡 NORMAL"
                        
                        nomor_urutan = i + offset
                        stok_pesan += f"**{nomor_urutan}. {nama_produk}**\n"
                        stok_pesan += f"   📝 {deskripsi}\n"
                        stok_pesan += f"   📊 Stok: {stok} {satuan_kecil} {status_stok}\n"
                        stok_pesan += f"   💰 Harga Jual: {harga_jual_rupiah}\n"
                        stok_pesan += f"   📦 Satuan: {satuan_besar} (isi: {isi} {satuan_kecil})\n"
                        stok_pesan += f"   ⚙️ Min/Max: {min_stok}/{max_stok}\n"
                        stok_pesan += "   ──────────────\n"
                else:
                    stok_pesan += "📭 Tidak ada data pada halaman ini\n\n"
                
                # Buat keyboard dengan paging
                keyboard = types.InlineKeyboardMarkup(row_width=5)
                
                # Tombol paging hanya jika ada lebih dari 1 halaman
                if total_pages > 1:
                    paging_buttons = []
                    
                    # Tombol Previous
                    if page > 1:
                        paging_buttons.append(
                            types.InlineKeyboardButton("⬅️", callback_data=f"stock_{supplier_id}_page_{page-1}")
                        )
                    
                    # Tombol nomor halaman
                    start_page = max(1, page - 1)
                    end_page = min(total_pages, page + 1)
                    
                    for p in range(start_page, end_page + 1):
                        if p == page:
                            paging_buttons.append(
                                types.InlineKeyboardButton(f"•{p}•", callback_data=f"stock_{supplier_id}_page_{p}")
                            )
                        else:
                            paging_buttons.append(
                                types.InlineKeyboardButton(str(p), callback_data=f"stock_{supplier_id}_page_{p}")
                            )
                    
                    # Tombol Next
                    if page < total_pages:
                        paging_buttons.append(
                            types.InlineKeyboardButton("➡️", callback_data=f"stock_{supplier_id}_page_{page+1}")
                        )
                    
                    if paging_buttons:
                        keyboard.add(*paging_buttons)
                
                # Tombol aksi
                action_buttons = []
                action_buttons.append(
                    types.InlineKeyboardButton("🔄 Refresh", callback_data=f"stock_{supplier_id}_page_{page}")
                )
                action_buttons.append(
                    types.InlineKeyboardButton("🔙 Kembali", callback_data="back_to_stok_menu")
                )
                keyboard.add(*action_buttons)
                
                # Edit atau kirim pesan baru
                try:
                    bot.edit_message_text(
                        chat_id=call.message.chat.id,
                        message_id=call.message.message_id,
                        text=stok_pesan,
                        parse_mode='Markdown',
                        reply_markup=keyboard
                    )
                except Exception as e:
                    # Jika edit gagal, kirim pesan baru
                    bot.send_message(
                        call.message.chat.id,
                        stok_pesan,
                        parse_mode='Markdown',
                        reply_markup=keyboard
                    )
                
            else:
                # Tidak ada data stok sama sekali
                keyboard_empty = types.InlineKeyboardMarkup()
                keyboard_empty.row(
                    types.InlineKeyboardButton("🔙 Kembali", callback_data="back_to_stok_menu")
                )
                
                try:
                    bot.edit_message_text(
                        chat_id=call.message.chat.id,
                        message_id=call.message.message_id,
                        text=f"📦 TIDAK ADA STOK PRODUK\n\nSupplier **{nama_supplier}** belum memiliki data stok produk.",
                        parse_mode='Markdown',
                        reply_markup=keyboard_empty
                    )
                except Exception as e:
                    bot.send_message(
                        call.message.chat.id,
                        f"📦 TIDAK ADA STOK PRODUK\n\nSupplier **{nama_supplier}** belum memiliki data stok produk.",
                        parse_mode='Markdown',
                        reply_markup=keyboard_empty
                    )
                
    except Exception as e:
        bot.answer_callback_query(call.id, f"Error: {str(e)}")
        print(f"Error in handle_stock_callback: {e}")
    finally:
        if conn and conn.open:
            conn.close()