import datetime
from telebot import types
from database import connection, get_nik_from_telegram, get_nama_satuan
from utils.faktur_generator import generate_nomor_faktur_otomatis
from utils.helpers import format_rupiah

# State management untuk proses penerimaan barang
user_states = {}
paging_states = {}

def tampilkan_produk_dengan_tombol(chat_id, user_state, page=1):
    """Tampilkan produk dengan tombol paging"""
    produk_data = user_state['produk_data']
    
    # Settings paging
    items_per_page = 8
    total_pages = max(1, (len(produk_data) + items_per_page - 1) // items_per_page)
    
    # Validasi page
    if page < 1:
        page = 1
    elif page > total_pages:
        page = total_pages
    
    # Calculate start dan end index
    start_index = (page - 1) * items_per_page
    end_index = start_index + items_per_page
    produk_page = produk_data[start_index:end_index]
    
    # Simpan state paging
    paging_states[chat_id] = {
        'supplier_id': user_state['supplier_id'],
        'current_page': page,
        'total_pages': total_pages,
        'produk_data': produk_data
    }
    
    # Buat keyboard untuk produk
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    
    # Tombol produk
    for i, produk in enumerate(produk_page, 1):
        global_index = start_index + i
        id_produk = produk[0]
        nama_produk = produk[1] or "Tidak ada nama"
        
        button_text = f"{global_index}. {nama_produk[:20]}"
        button = types.InlineKeyboardButton(
            text=button_text,
            callback_data=f"pilih_produk_{global_index}"
        )
        keyboard.add(button)
    
    # Tombol paging jika ada lebih dari 1 halaman
    if total_pages > 1:
        paging_buttons = []
        
        # Tombol Previous
        if page > 1:
            paging_buttons.append(
                types.InlineKeyboardButton("⬅️ Prev", callback_data=f"produk_page_{page-1}")
            )
        
        # Info halaman
        paging_buttons.append(
            types.InlineKeyboardButton(f"{page}/{total_pages}", callback_data="no_action")
        )
        
        # Tombol Next
        if page < total_pages:
            paging_buttons.append(
                types.InlineKeyboardButton("Next ➡️", callback_data=f"produk_page_{page+1}")
            )
        
        keyboard.add(*paging_buttons)
    
    # Tombol aksi
    keyboard.row(
        types.InlineKeyboardButton("📦 Lihat Item", callback_data="lihat_item"),
        types.InlineKeyboardButton("💾 Simpan", callback_data="simpan_penerimaan")
    )
    keyboard.row(
        types.InlineKeyboardButton("❌ Batal", callback_data="batal_penerimaan")
    )
    
    pesan_produk = f"🛒 PILIH PRODUK - {user_state['supplier_name']}\n\n"
    pesan_produk += f"**Halaman:** {page}/{total_pages}\n"
    pesan_produk += f"**Total produk:** {len(produk_data)} item\n"
    pesan_produk += f"**Menampilkan:** {len(produk_page)} produk\n\n"
    pesan_produk += "Klik produk untuk menambahkan:"
    
    return pesan_produk, keyboard

def handle_penerimaan_menu(message, bot):
    """Handle menu penerimaan barang"""
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
                # Buat keyboard untuk menu penerimaan
                keyboard = types.InlineKeyboardMarkup(row_width=2)
                
                for supplier in hasil_sql:
                    id_supplier = supplier['id_supplier']
                    nama_supplier = supplier['nama_supplier']
                    
                    btn_riwayat = types.InlineKeyboardButton(
                        text=f"📦 {nama_supplier[:20]}",
                        callback_data=f"penerimaan_{id_supplier}_page_1"
                    )
                    
                    btn_tambah = types.InlineKeyboardButton(
                        text=f"➕ {nama_supplier[:20]}",
                        callback_data=f"pilih_supplier_{id_supplier}"
                    )
                    
                    keyboard.add(btn_riwayat, btn_tambah)
                
                # Tombol refresh
                keyboard.row(
                    types.InlineKeyboardButton("🔄 Refresh Data", callback_data="refresh_penerimaan")
                )
                
                pesan_balasan = f"📦 PENERIMAAN BARANG\n\n"
                pesan_balasan += f"Nama: **{user_data['nama']}**\n"
                pesan_balasan += f"Total Supplier: **{len(hasil_sql)}**\n\n"
                pesan_balasan += "**Pilih supplier:**\n"
                pesan_balasan += "• 📦 Lihat riwayat penerimaan (dengan paging)\n"
                pesan_balasan += "• ➕ Tambah penerimaan baru"
                
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

def handle_penerimaan_supplier(call, bot):
    """Handle riwayat penerimaan supplier dengan paging"""
    supplier_id = call.data.replace('penerimaan_', '')
    
    # Parse page number
    page = 1
    if '_page_' in supplier_id:
        parts = supplier_id.split('_page_')
        supplier_id = parts[0]
        page = int(parts[1])
    
    conn = connection()
    if conn is None:
        bot.answer_callback_query(call.id, "Koneksi database gagal")
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
                FROM tb_riceve r
                WHERE r.idsuplier = %s AND r.aktif = 'Y'
            """, (supplier_id,))
            
            total_data = sql.fetchone()['total']
            items_per_page = 5
            total_pages = max(1, (total_data + items_per_page - 1) // items_per_page)
            
            # Validasi page number
            if page < 1:
                page = 1
            elif page > total_pages:
                page = total_pages
            
            # Calculate offset
            offset = (page - 1) * items_per_page
            
            # Query riwayat penerimaan barang dengan paging
            sql.execute("""
                SELECT 
                    r.id,
                    r.norcv,
                    r.nofaktur,
                    r.tgl,
                    r.totalitem,
                    r.totalharga,
                    r.diskon,
                    r.totalfinal,
                    r.keterangan
                FROM tb_riceve r
                WHERE r.idsuplier = %s 
                    AND r.aktif = 'Y'
                ORDER BY r.tgl DESC, r.id DESC
                LIMIT %s OFFSET %s
            """, (supplier_id, items_per_page, offset))
            
            hasil_penerimaan = sql.fetchall()
            
            if hasil_penerimaan or total_data > 0:
                # Buat pesan riwayat penerimaan
                riwayat_pesan = f"📦 RIWAYAT PENERIMAAN BARANG\n\n"
                riwayat_pesan += f"**Supplier:** {nama_supplier}\n"
                riwayat_pesan += f"**Halaman:** {page}/{total_pages}\n"
                riwayat_pesan += f"**Total Data:** {total_data} penerimaan\n\n"
                
                if hasil_penerimaan:
                    for i, penerimaan in enumerate(hasil_penerimaan, 1):
                        id_rcv = penerimaan['id']
                        no_rcv = penerimaan['norcv'] or "-"
                        no_faktur = penerimaan['nofaktur'] or "-"
                        tgl = penerimaan['tgl'].strftime('%d-%m-%Y') if penerimaan['tgl'] else "-"
                        total_item = penerimaan['totalitem'] or 0
                        total_harga = penerimaan['totalharga'] or 0
                        diskon = penerimaan['diskon'] or 0
                        total_final = penerimaan['totalfinal'] or 0
                        keterangan = penerimaan['keterangan'] or "-"
                        
                        total_final_rupiah = format_rupiah(total_final)
                        
                        nomor_urutan = i + offset
                        riwayat_pesan += f"**{nomor_urutan}. No. RCV:** `{no_rcv}`\n"
                        riwayat_pesan += f"   📅 Tgl: {tgl}\n"
                        riwayat_pesan += f"   📄 Faktur: `{no_faktur}`\n"
                        riwayat_pesan += f"   📦 Item: {total_item} produk\n"
                        riwayat_pesan += f"   💰 Total: {total_final_rupiah}\n"
                        if keterangan and keterangan != "-":
                            riwayat_pesan += f"   📝 Ket: {keterangan[:30]}{'...' if len(keterangan) > 30 else ''}\n"
                        riwayat_pesan += "   ──────────────\n"
                else:
                    riwayat_pesan += "📭 Tidak ada data pada halaman ini\n\n"
                
                # Buat keyboard dengan paging
                keyboard = types.InlineKeyboardMarkup(row_width=5)
                
                # Tombol paging hanya jika ada lebih dari 1 halaman
                if total_pages > 1:
                    paging_buttons = []
                    
                    # Tombol Previous
                    if page > 1:
                        paging_buttons.append(
                            types.InlineKeyboardButton("⬅️", callback_data=f"penerimaan_{supplier_id}_page_{page-1}")
                        )
                    
                    # Tombol nomor halaman
                    start_page = max(1, page - 1)
                    end_page = min(total_pages, page + 1)
                    
                    for p in range(start_page, end_page + 1):
                        if p == page:
                            paging_buttons.append(
                                types.InlineKeyboardButton(f"•{p}•", callback_data=f"penerimaan_{supplier_id}_page_{p}")
                            )
                        else:
                            paging_buttons.append(
                                types.InlineKeyboardButton(str(p), callback_data=f"penerimaan_{supplier_id}_page_{p}")
                            )
                    
                    # Tombol Next
                    if page < total_pages:
                        paging_buttons.append(
                            types.InlineKeyboardButton("➡️", callback_data=f"penerimaan_{supplier_id}_page_{page+1}")
                        )
                    
                    if paging_buttons:
                        keyboard.add(*paging_buttons)
                
                # Tombol aksi
                action_buttons = []
                action_buttons.append(
                    types.InlineKeyboardButton("🔄 Refresh", callback_data=f"penerimaan_{supplier_id}_page_{page}")
                )
                action_buttons.append(
                    types.InlineKeyboardButton("➕ Tambah Baru", callback_data=f"pilih_supplier_{supplier_id}")
                )
                keyboard.add(*action_buttons)
                
                # Tombol kembali
                keyboard.row(
                    types.InlineKeyboardButton("🔙 Kembali ke Menu", callback_data="back_to_penerimaan_menu")
                )
                
                # Edit atau kirim pesan baru
                try:
                    bot.edit_message_text(
                        chat_id=call.message.chat.id,
                        message_id=call.message.message_id,
                        text=riwayat_pesan,
                        parse_mode='Markdown',
                        reply_markup=keyboard
                    )
                except Exception as e:
                    bot.send_message(
                        call.message.chat.id,
                        riwayat_pesan,
                        parse_mode='Markdown',
                        reply_markup=keyboard
                    )
                
            else:
                # Tidak ada data penerimaan sama sekali
                keyboard_empty = types.InlineKeyboardMarkup()
                keyboard_empty.row(
                    types.InlineKeyboardButton("➕ Tambah Penerimaan Pertama", callback_data=f"pilih_supplier_{supplier_id}")
                )
                keyboard_empty.row(
                    types.InlineKeyboardButton("🔙 Kembali ke Menu", callback_data="back_to_penerimaan_menu")
                )
                
                try:
                    bot.edit_message_text(
                        chat_id=call.message.chat.id,
                        message_id=call.message.message_id,
                        text=f"📦 Belum Ada Penerimaan\n\nSupplier **{nama_supplier}** belum memiliki riwayat penerimaan barang.\n\nKlik tombol dibawah untuk menambahkan penerimaan pertama.",
                        parse_mode='Markdown',
                        reply_markup=keyboard_empty
                    )
                except Exception as e:
                    bot.send_message(
                        call.message.chat.id,
                        f"📦 Belum Ada Penerimaan\n\nSupplier **{nama_supplier}** belum memiliki riwayat penerimaan barang.\n\nKlik tombol dibawah untuk menambahkan penerimaan pertama.",
                        parse_mode='Markdown',
                        reply_markup=keyboard_empty
                    )
                
    except Exception as e:
        bot.answer_callback_query(call.id, f"Error: {str(e)}")
        print(f"Error in handle_penerimaan_supplier: {e}")
    finally:
        if conn and conn.open:
            conn.close()

def handle_pilih_supplier(call, bot):
    """Handle pemilihan supplier untuk penerimaan baru"""
    supplier_id = call.data.replace('pilih_supplier_', '')
    
    conn = connection()
    if conn is None:
        bot.answer_callback_query(call.id, "Koneksi database gagal")
        return
    
    try:
        with conn.cursor() as sql:
            # Query untuk mendapatkan nama supplier
            sql.execute("SELECT namasuplier FROM tb_suplier WHERE id = %s", (supplier_id,))
            supplier_data = sql.fetchone()
            nama_supplier = supplier_data['namasuplier'] if supplier_data else "Supplier"
            
            # Query produk yang tersedia
            sql.execute("""
                SELECT 
                    p.id_produk,
                    p.nama_produk,
                    p.deskripsi,
                    p.stok,
                    CASE 
                        WHEN si.harga IS NULL THEN 0
                        WHEN si.harga = 0 THEN 0
                        ELSE si.harga 
                    END AS harga_beli,
                    CASE 
                        WHEN si.satuan IS NOT NULL AND si.satuan != '' THEN si.satuan
                        ELSE p.satuanbesar 
                    END AS satuan_besar_id,
                    CASE 
                        WHEN si.isi IS NOT NULL AND si.isi > 0 THEN si.isi
                        ELSE COALESCE(p.isi, 1)
                    END AS isi_supplier,
                    p.satuanbesar AS satuan_besar_produk_id,
                    p.satuankecil AS satuan_kecil_produk_id,
                    p.isi AS isi_produk,
                    p.harga AS harga_jual
                FROM tbl_produk p
                INNER JOIN tb_suplieritem si ON p.id_produk = si.iditem
                WHERE si.idsuplier = %s 
                    AND si.aktif = 'Y'
                    AND p.aktif = 'Y'
                ORDER BY p.nama_produk
            """, (supplier_id,))
            
            produk_data_raw = sql.fetchall()
            
            # Process produk data untuk mendapatkan nama satuan
            produk_data = []
            for produk in produk_data_raw:
                satuan_besar_id = produk['satuan_besar_id']
                satuan_kecil_id = produk['satuan_kecil_produk_id']
                
                # Dapatkan nama satuan
                satuan_besar = get_nama_satuan(satuan_besar_id)
                satuan_kecil = get_nama_satuan(satuan_kecil_id)
                
                # Reconstruct produk data dengan nama satuan
                processed_produk = (
                    produk['id_produk'],
                    produk['nama_produk'],
                    produk['deskripsi'],
                    produk['stok'],
                    produk['harga_beli'],
                    satuan_besar,
                    produk['isi_supplier'],
                    satuan_besar,
                    satuan_kecil,
                    produk['isi_produk'],
                    produk['harga_jual']
                )
                produk_data.append(processed_produk)
            
            if produk_data:
                # Generate nomor faktur otomatis
                nomor_faktur_otomatis = generate_nomor_faktur_otomatis(supplier_id)
                
                # Simpan state user
                user_states[str(call.from_user.id)] = {
                    'state': 'waiting_for_faktur',
                    'supplier_id': supplier_id,
                    'supplier_name': nama_supplier,
                    'produk_data': produk_data,
                    'items': [],
                    'nofaktur_otomatis': nomor_faktur_otomatis
                }
                
                # Hapus keyboard sebelumnya
                bot.edit_message_text(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    text=f"🛒 TAMBAH PENERIMAAN BARU\n\n**Supplier:** {nama_supplier}\n**Total Produk:** {len(produk_data)} item\n\nSilakan lanjutkan dengan mengisi data berikut:",
                    parse_mode='Markdown'
                )
                
                # Tampilkan nomor faktur otomatis dan minta konfirmasi
                if nomor_faktur_otomatis:
                    keyboard = types.InlineKeyboardMarkup()
                    keyboard.row(
                        types.InlineKeyboardButton(f"✅ Gunakan {nomor_faktur_otomatis}", callback_data="gunakan_faktur_otomatis")
                    )
                    keyboard.row(
                        types.InlineKeyboardButton("✏️ Input Manual", callback_data="input_faktur_manual")
                    )
                    
                    bot.send_message(
                        call.message.chat.id,
                        f"📄 **NOMOR FAKTUR OTOMATIS**\n\n"
                        f"Nomor faktur yang dihasilkan:\n"
                        f"`{nomor_faktur_otomatis}`\n\n"
                        f"Klik tombol untuk menggunakan nomor otomatis atau input manual:",
                        parse_mode='Markdown',
                        reply_markup=keyboard
                    )
                else:
                    # Jika gagal generate otomatis, minta input manual
                    bot.send_message(
                        call.message.chat.id,
                        "📄 **NOMOR FAKTUR**\n\nSilakan ketik nomor faktur:\nContoh: `FAK/2024/001`",
                        parse_mode='Markdown'
                    )
                
            else:
                bot.answer_callback_query(call.id, f"❌ Tidak ada produk untuk {nama_supplier}")
                
    except Exception as e:
        bot.answer_callback_query(call.id, f"Error: {str(e)}")
    finally:
        if conn and conn.open:
            conn.close()

def handle_gunakan_faktur_otomatis(call, bot):
    """Handle penggunaan faktur otomatis"""
    user_id = str(call.from_user.id)
    
    if user_id not in user_states:
        bot.answer_callback_query(call.id, "Tidak ada proses penerimaan aktif")
        return
    
    user_state = user_states[user_id]
    
    # Gunakan nomor faktur otomatis
    user_state['nofaktur'] = user_state['nofaktur_otomatis']
    user_state['state'] = 'waiting_for_keterangan'
    
    # Hapus pesan sebelumnya
    bot.delete_message(call.message.chat.id, call.message.message_id)
    
    # Tampilkan tombol untuk keterangan
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(types.KeyboardButton("-"))
    
    bot.send_message(
        call.message.chat.id,
        f"✅ **NOMOR FAKTUR DITERIMA**\n\nNomor faktur: `{user_state['nofaktur']}`\n\n"
        f"KETERANGAN\n\nSilakan ketik keterangan penerimaan:\nContoh: `Penerimaan barang rutin`\n\nAtau klik `-` untuk kosongkan",
        parse_mode='Markdown',
        reply_markup=keyboard
    )
    
    bot.answer_callback_query(call.id, "Nomor faktur otomatis digunakan")

def handle_input_faktur_manual(call, bot):
    """Handle input faktur manual"""
    user_id = str(call.from_user.id)
    
    if user_id not in user_states:
        bot.answer_callback_query(call.id, "Tidak ada proses penerimaan aktif")
        return
    
    user_state = user_states[user_id]
    user_state['state'] = 'waiting_for_faktur'
    
    # Hapus pesan sebelumnya
    bot.delete_message(call.message.chat.id, call.message.message_id)
    
    # Minta input nomor faktur manual
    bot.send_message(
        call.message.chat.id,
        "📄 **NOMOR FAKTUR MANUAL**\n\nSilakan ketik nomor faktur:\nContoh: `FAK/2024/001`",
        parse_mode='Markdown'
    )
    
    bot.answer_callback_query(call.id, "Input nomor faktur manual")

def handle_penerimaan_input(message, bot):
    """Handle input selama proses penerimaan"""
    user_id = str(message.from_user.id)
    
    if user_id not in user_states:
        return
    
    user_state = user_states[user_id]
    
    if user_state['state'] == 'waiting_for_faktur':
        # Simpan nomor faktur
        user_state['nofaktur'] = message.text
        user_state['state'] = 'waiting_for_keterangan'
        
        # Tampilkan tombol untuk keterangan
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        keyboard.add(types.KeyboardButton("-"))
        
        bot.reply_to(
            message,
            "KETERANGAN\n\nSilakan ketik keterangan penerimaan:\nContoh: `Penerimaan barang rutin`\n\nAtau klik `-` untuk kosongkan",
            parse_mode='Markdown',
            reply_markup=keyboard
        )
        
    elif user_state['state'] == 'waiting_for_keterangan':
        # Simpan keterangan
        user_state['keterangan'] = message.text if message.text != '-' else ''
        user_state['state'] = 'selecting_products'
        
        # Hapus keyboard khusus
        remove_keyboard = types.ReplyKeyboardRemove()
        bot.send_message(message.chat.id, "Membuka menu produk...", reply_markup=remove_keyboard)
        
        # Tampilkan daftar produk dengan tombol dan paging
        pesan_produk, keyboard = tampilkan_produk_dengan_tombol(message.chat.id, user_state, 1)
        bot.send_message(
            message.chat.id,
            pesan_produk,
            parse_mode='Markdown',
            reply_markup=keyboard
        )
        
    elif user_state['state'] == 'waiting_for_qty':
        # Handle input quantity
        try:
            qty = int(message.text)
            if qty <= 0:
                bot.reply_to(message, "Quantity harus lebih dari 0")
                return
                
            # Simpan item dengan data satuan yang lengkap
            selected_product = user_state['selected_product']
            
            user_state['items'].append({
                'id_produk': selected_product['id_produk'],
                'nama_produk': selected_product['nama_produk'],
                'qty': qty,
                'harga': selected_product['harga_beli'],
                'satuan_besar': selected_product['satuan_besar'],
                'satuan_kecil': selected_product['satuan_kecil'],
                'isi': selected_product['isi'],
                'subtotal': qty * selected_product['harga_beli']
            })
            
            # Kembali ke pemilihan produk
            user_state['state'] = 'selecting_products'
            
            # Tampilkan konfirmasi
            harga_rupiah = format_rupiah(selected_product['harga_beli'])
            bot.reply_to(message, f"{selected_product['nama_produk']} ditambahkan: {qty} {selected_product['satuan_besar']}\nHarga: {harga_rupiah}")
            
            # Tampilkan kembali daftar produk dengan paging terakhir
            current_page = 1
            if message.chat.id in paging_states:
                current_page = paging_states[message.chat.id]['current_page']
            
            pesan_produk, keyboard = tampilkan_produk_dengan_tombol(message.chat.id, user_state, current_page)
            bot.send_message(
                message.chat.id,
                pesan_produk,
                parse_mode='Markdown',
                reply_markup=keyboard
            )
            
        except ValueError:
            bot.reply_to(message, "Quantity harus berupa angka")

def handle_pilih_produk(call, bot):
    """Handle pemilihan produk"""
    user_id = str(call.from_user.id)
    
    if user_id not in user_states:
        bot.answer_callback_query(call.id, "Tidak ada proses penerimaan aktif")
        return
    
    user_state = user_states[user_id]
    produk_data = user_state['produk_data']
    
    # Parse nomor produk (global index)
    global_index = int(call.data.replace('pilih_produk_', '')) - 1
    
    if global_index < 0 or global_index >= len(produk_data):
        bot.answer_callback_query(call.id, "Produk tidak valid")
        return
    
    # Ambil data produk berdasarkan index global
    produk = produk_data[global_index]
    
    # Ambil data satuan dan harga
    harga_beli = produk[4]
    satuan_besar = produk[5]
    isi_supplier = produk[6]
    satuan_kecil = produk[8]
    isi_produk = produk[9]
    
    # Pastikan isi tidak kosong
    if not isi_supplier or isi_supplier == 0:
        isi_supplier = isi_produk if isi_produk else 1
    
    # Jika masih 0, beri peringatan tapi tetap lanjutkan
    if harga_beli is None or harga_beli == 0:
        bot.answer_callback_query(call.id, "⚠️ Harga beli 0, pastikan harga sudah diatur")
    
    # Simpan data produk yang dipilih
    user_state['selected_product'] = {
        'id_produk': produk[0],
        'nama_produk': produk[1],
        'harga_beli': float(harga_beli) if harga_beli else 0,
        'satuan_besar': satuan_besar,
        'satuan_kecil': satuan_kecil,
        'isi': int(isi_supplier) if isi_supplier else 1
    }
    
    user_state['state'] = 'waiting_for_qty'
    
    # Minta input quantity
    harga_rupiah = format_rupiah(harga_beli)
    status_harga = " ⚠️ (HARGA BELI 0)" if harga_beli == 0 else ""
    
    bot.send_message(
        call.message.chat.id,
        f"🔢 **QUANTITY**\n\n"
        f"**Produk:** {produk[1]}{status_harga}\n"
        f"**Harga Beli:** {harga_rupiah}\n"
        f"**Satuan Besar:** {satuan_besar}\n"
        f"**Satuan Kecil:** {satuan_kecil}\n"
        f"**Isi:** {isi_supplier} {satuan_kecil} per {satuan_besar}\n\n"
        f"Silakan ketik quantity dalam satuan **{satuan_besar}**:",
        parse_mode='Markdown'
    )
    
    bot.answer_callback_query(call.id, f"Pilih {produk[1]}")

def handle_produk_paging(call, bot):
    """Handle paging produk"""
    user_id = str(call.from_user.id)
    
    if user_id not in user_states:
        bot.answer_callback_query(call.id, "Tidak ada proses penerimaan aktif")
        return
    
    # Parse page number
    page = int(call.data.replace('produk_page_', ''))
    
    user_state = user_states[user_id]
    
    # Tampilkan produk dengan halaman yang diminta
    pesan_produk, keyboard = tampilkan_produk_dengan_tombol(call.message.chat.id, user_state, page)
    
    try:
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=pesan_produk,
            parse_mode='Markdown',
            reply_markup=keyboard
        )
        bot.answer_callback_query(call.id, f"Halaman {page}")
    except Exception as e:
        bot.answer_callback_query(call.id, "Gagal memperbarui halaman")

def handle_lihat_item(call, bot):
    """Handle lihat item yang sudah dipilih"""
    user_id = str(call.from_user.id)
    
    if user_id not in user_states:
        bot.answer_callback_query(call.id, "Tidak ada proses penerimaan aktif")
        return
    
    user_state = user_states[user_id]
    items = user_state['items']
    
    if not items:
        bot.answer_callback_query(call.id, "Belum ada item")
        return
    
    # Buat pesan list item
    pesan_list = "ITEM YANG DITAMBAHKAN\n\n"
    
    total_qty = 0
    total_harga = 0
    items_dengan_harga_0 = []
    
    for i, item in enumerate(items, 1):
        pesan_list += f"*{i}. {item['nama_produk']}*\n"
        pesan_list += f"   Qty: {item['qty']} {item['satuan_besar']}\n"
        pesan_list += f"   Harga Beli: {format_rupiah(item['harga'])}\n"
        pesan_list += f"   Subtotal: {format_rupiah(item['subtotal'])}\n"
        pesan_list += f"   Konversi: {item['qty']} {item['satuan_besar']} = {item['qty'] * item['isi']} {item['satuan_kecil']}\n"
        
        if item['harga'] == 0:
            pesan_list += "   *HARGA BELI 0*\n"
            items_dengan_harga_0.append(item['nama_produk'])
        
        pesan_list += "   --------------\n"
        
        total_qty += item['qty']
        total_harga += item['subtotal']
    
    pesan_list += f"\nTOTAL SEMENTARA:\n"
    pesan_list += f"• Item: {len(items)} produk\n"
    pesan_list += f"• Qty: {total_qty} {items[0]['satuan_besar'] if items else 'unit'}\n"
    pesan_list += f"• Total: {format_rupiah(total_harga)}"
    
    if items_dengan_harga_0:
        pesan_list += f"\n\nPERINGATAN: {len(items_dengan_harga_0)} produk dengan harga beli 0"
    
    # Tombol aksi
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row(
        types.InlineKeyboardButton("Tambah Lagi", callback_data="kembali_ke_produk"),
        types.InlineKeyboardButton("Simpan", callback_data="simpan_penerimaan")
    )
    
    bot.send_message(
        call.message.chat.id,
        pesan_list,
        parse_mode='Markdown',
        reply_markup=keyboard
    )
    
    bot.answer_callback_query(call.id, "Menampilkan item")

def handle_kembali_ke_produk(call, bot):
    """Handle kembali ke menu produk"""
    user_id = str(call.from_user.id)
    
    if user_id not in user_states:
        bot.answer_callback_query(call.id, "Tidak ada proses penerimaan aktif")
        return
    
    user_state = user_states[user_id]
    user_state['state'] = 'selecting_products'
    
    # Dapatkan page terakhir atau mulai dari page 1
    current_page = 1
    if call.message.chat.id in paging_states:
        current_page = paging_states[call.message.chat.id]['current_page']
    
    # Hapus pesan sebelumnya
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except:
        pass
    
    # Tampilkan kembali daftar produk dengan paging
    pesan_produk, keyboard = tampilkan_produk_dengan_tombol(call.message.chat.id, user_state, current_page)
    
    bot.send_message(
        call.message.chat.id,
        pesan_produk,
        parse_mode='Markdown',
        reply_markup=keyboard
    )
    
    bot.answer_callback_query(call.id, "Kembali ke pilihan produk")

def handle_batal_penerimaan(call, bot):
    """Handle batal penerimaan"""
    user_id = str(call.from_user.id)
    
    if user_id in user_states:
        del user_states[user_id]
    
    # Hapus keyboard custom
    remove_keyboard = types.ReplyKeyboardRemove()
    
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="Penerimaan dibatalkan",
        parse_mode='Markdown'
    )
    
    # Kirim pesan dengan keyboard default
    bot.send_message(
        call.message.chat.id,
        "Penerimaan barang telah dibatalkan. Silakan pilih menu lain.",
        reply_markup=remove_keyboard
    )

def handle_simpan_penerimaan(call, bot):
    """Handle simpan penerimaan"""
    user_id = str(call.from_user.id)
    
    if user_id not in user_states:
        bot.answer_callback_query(call.id, "Tidak ada proses penerimaan aktif")
        return
    
    user_state = user_states[user_id]
    items = user_state['items']
    
    if not items:
        bot.answer_callback_query(call.id, "Belum ada item yang ditambahkan")
        return
    
    # Validasi harga beli
    items_dengan_harga_0 = [item for item in items if item['harga'] == 0]
    if items_dengan_harga_0:
        produk_names = [item['nama_produk'] for item in items_dengan_harga_0]
        bot.answer_callback_query(
            call.id, 
            f"{len(items_dengan_harga_0)} produk harga 0"
        )
        # Tanyakan apakah ingin lanjut atau tidak
        keyboard = types.InlineKeyboardMarkup()
        keyboard.row(
            types.InlineKeyboardButton("Lanjut Simpan", callback_data="konfirmasi_simpan_harga_0"),
            types.InlineKeyboardButton("Edit Item", callback_data="kembali_ke_produk")
        )
        
        bot.send_message(
            call.message.chat.id,
            f"PERINGATAN: HARGA BELI 0\n\n"
            f"Ada {len(items_dengan_harga_0)} produk dengan harga beli 0:\n"
            f"{chr(10).join([f'• {name}' for name in produk_names[:5]])}\n\n"
            f"Apakah ingin melanjutkan penyimpanan?",
            parse_mode='Markdown',
            reply_markup=keyboard
        )
        return
    
    # Simpan ke database
    simpan_penerimaan_baru(user_id, user_state, call, bot)

def handle_konfirmasi_simpan_harga_0(call, bot):
    """Handle konfirmasi simpan dengan harga 0"""
    user_id = str(call.from_user.id)
    
    if user_id not in user_states:
        bot.answer_callback_query(call.id, "Tidak ada proses penerimaan aktif")
        return
    
    user_state = user_states[user_id]
    
    # Hapus pesan konfirmasi
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception as e:
        print(f"Gagal menghapus pesan: {e}")
    
    # Simpan ke database
    simpan_penerimaan_baru(user_id, user_state, call, bot)

def simpan_penerimaan_baru(user_id, user_state, source, bot):
    """Simpan penerimaan baru ke database"""
    conn = connection()
    if conn is None:
        if hasattr(source, 'answer_callback_query'):
            bot.answer_callback_query(source.id, "Koneksi database gagal")
        else:
            bot.reply_to(source, "Koneksi database gagal")
        return
    
    try:
        with conn.cursor() as sql:
            # Generate nomor RCV
            tanggal_sekarang = datetime.datetime.now().strftime('%y%m%d')
            
            # Cari sequence number terakhir untuk hari ini
            sql.execute("""
                SELECT MAX(CAST(SUBSTRING(norcv, 7) AS UNSIGNED)) as last_sequence
                FROM tb_riceve 
                WHERE norcv LIKE %s
            """, (f'TLE{tanggal_sekarang}%',))
            
            result = sql.fetchone()
            last_sequence = result['last_sequence'] if result['last_sequence'] is not None else 0
            
            # Generate sequence berikutnya
            sequence = last_sequence + 1
            
            # Jika sequence melebihi 999, reset ke 1
            if sequence > 999:
                sequence = 1
                
                # Cari sequence yang tersedia mulai dari 1
                for i in range(1, 1000):
                    norcv_candidate = f"TLE{tanggal_sekarang}{i:03d}"
                    sql.execute("SELECT COUNT(*) as count FROM tb_riceve WHERE norcv = %s", (norcv_candidate,))
                    if sql.fetchone()['count'] == 0:
                        sequence = i
                        break
            
            norcv = f"TLE{tanggal_sekarang}{sequence:03d}"
            
            # Hitung total
            total_item = len(user_state['items'])
            total_harga = sum(item['subtotal'] for item in user_state['items'])
            diskon = 0
            total_final = total_harga - diskon
            
            # Potong data jika melebihi panjang kolom
            nofaktur = user_state['nofaktur'][:25] if len(user_state['nofaktur']) > 25 else user_state['nofaktur']
            keterangan = user_state['keterangan'][:65535] if len(user_state['keterangan']) > 65535 else user_state['keterangan']
            
            # Dapatkan user data untuk log
            user_data = get_nik_from_telegram(user_id)
            user_name = user_data['nama'] if user_data else f"TG_{user_id}"
            
            # Insert header penerimaan
            sql.execute("""
                INSERT INTO tb_riceve (
                    norcv, nofaktur, keterangan, idsuplier, tgl, jam, 
                    totalitem, totalharga, diskon, totalfinal, user, aktif
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'Y')
            """, (
                norcv,
                nofaktur,
                keterangan,
                user_state['supplier_id'],
                datetime.datetime.now().date(),
                datetime.datetime.now().time(),
                total_item,
                total_harga,
                diskon,
                total_final,
                user_name
            ))
            
            # Dapatkan ID penerimaan yang baru dibuat
            id_rcv = sql.lastrowid
            
            # Insert detail penerimaan - PERBAIKAN: Gunakan ID satuan, bukan nama
            for item in user_state['items']:
                # Hitung qty2 (quantity dalam satuan kecil)
                qty2 = item['qty'] * item['isi']
                
                # Dapatkan ID satuan dari database berdasarkan nama satuan
                # Untuk satuanbesar
                sql.execute("SELECT id FROM tb_satuan WHERE satuan = %s AND aktif = 'Y' LIMIT 1", (item['satuan_besar'],))
                satuan_besar_result = sql.fetchone()
                satuan_besar_id = satuan_besar_result['id'] if satuan_besar_result else 1  # Default ke 1 jika tidak ditemukan
                
                # Untuk satuankecil  
                sql.execute("SELECT id FROM tb_satuan WHERE satuan = %s AND aktif = 'Y' LIMIT 1", (item['satuan_kecil'],))
                satuan_kecil_result = sql.fetchone()
                satuan_kecil_id = satuan_kecil_result['id'] if satuan_kecil_result else 1  # Default ke 1 jika tidak ditemukan
                
                sql.execute("""
                    INSERT INTO tb_ricevedetil (
                        idrcv, iditem, satuanbesar, qty1, satuankecil, isi, qty2,
                        hargabeli, subtotal, hargapokok, posting, user, tgl
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'N', %s, %s)
                """, (
                    id_rcv,
                    item['id_produk'],
                    satuan_besar_id,  # Gunakan ID, bukan nama
                    item['qty'],
                    satuan_kecil_id,  # Gunakan ID, bukan nama
                    item['isi'],
                    qty2,
                    item['harga'],
                    item['subtotal'],
                    item['harga'],
                    user_name,
                    datetime.datetime.now().date()
                ))
            
            conn.commit()
            
            # Hapus state user
            if user_id in user_states:
                del user_states[user_id]
            
            # Buat pesan sukses
            total_final_rupiah = format_rupiah(total_final)
            pesan_sukses = f"PENERIMAAN BARANG BERHASIL DIBUAT\n\n"
            pesan_sukses += f"No. RCV: `{norcv}`\n"
            pesan_sukses += f"No. Faktur: `{nofaktur}`\n"
            pesan_sukses += f"Supplier: {user_state['supplier_name']}\n"
            pesan_sukses += f"Total Item: {total_item} produk\n"
            pesan_sukses += f"Total Harga: {total_final_rupiah}\n"
            pesan_sukses += f"Keterangan: {keterangan[:100]}{'...' if len(keterangan) > 100 else ''}\n\n"
            pesan_sukses += f"Dibuat pada: {datetime.datetime.now().strftime('%d-%m-%Y %H:%M')}"
            
            # Cek jika ada harga 0
            items_dengan_harga_0 = [item for item in user_state['items'] if item['harga'] == 0]
            if items_dengan_harga_0:
                pesan_sukses += f"\n\nCatatan: {len(items_dengan_harga_0)} produk dengan harga beli 0"
            
            # Tombol lihat detail
            keyboard = types.InlineKeyboardMarkup()
            keyboard.row(
                types.InlineKeyboardButton("Lihat Detail", callback_data=f"detail_rcv_{id_rcv}"),
                types.InlineKeyboardButton("Document", callback_data=f"doc_rcv_{id_rcv}")
            )
            
            # PERBAIKAN: Handle CallbackQuery dengan benar
            if hasattr(source, 'message'):  # Ini adalah CallbackQuery
                bot.edit_message_text(
                    chat_id=source.message.chat.id,
                    message_id=source.message.message_id,
                    text=pesan_sukses,
                    parse_mode='Markdown',
                    reply_markup=keyboard
                )
            else:  # Ini adalah Message
                bot.reply_to(
                    source,
                    pesan_sukses,
                    parse_mode='Markdown',
                    reply_markup=keyboard
                )
            
    except Exception as e:
        conn.rollback()
        error_msg = f"Gagal menyimpan penerimaan: {str(e)}"
        print(f"Error detail: {e}")
        if hasattr(source, 'answer_callback_query'):
            bot.answer_callback_query(source.id, error_msg)
        else:
            bot.reply_to(source, error_msg)
    finally:
        if conn and conn.open:
            conn.close()

# ============================ FITUR MANAJEMEN MAPPING PRODUK ============================

def handle_manage_mapping_menu(message, bot):
    """Menu utama manajemen mapping produk per supplier"""
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
                    COUNT(si.id) as total_mapping,
                    SUM(CASE WHEN si.aktif = 'Y' THEN 1 ELSE 0 END) as aktif_mapping
                FROM 
                    tb_suplier s
                JOIN 
                    tb_karyawan k ON s.id_karyawan = k.id
                LEFT JOIN 
                    tb_suplieritem si ON s.id = si.idsuplier
                WHERE 
                    k.id_tele = %s
                    AND s.aktif = 'Y'
                    AND k.aktif = 'Y'
                GROUP BY s.id, s.namasuplier
                ORDER BY s.namasuplier
            """, (user_id,))
            
            hasil_sql = sql.fetchall()
            
            if hasil_sql:
                # Buat keyboard untuk menu manajemen mapping
                keyboard = types.InlineKeyboardMarkup(row_width=1)
                
                for supplier in hasil_sql:
                    id_supplier = supplier['id_supplier']
                    nama_supplier = supplier['nama_supplier']
                    total_mapping = supplier['total_mapping'] or 0
                    aktif_mapping = supplier['aktif_mapping'] or 0
                    
                    button_text = f"📋 {nama_supplier[:20]} ({aktif_mapping}/{total_mapping})"
                    button = types.InlineKeyboardButton(
                        text=button_text,
                        callback_data=f"manage_mapping_{id_supplier}_page_1"
                    )
                    keyboard.add(button)
                
                # Tombol kembali
                keyboard.row(
                    types.InlineKeyboardButton("🔙 Kembali ke Menu", callback_data="back_to_main_menu")
                )
                
                pesan_balasan = f"⚙️ MANAJEMEN MAPPING PRODUK\n\n"
                pesan_balasan += f"Nama: **{user_data['nama']}**\n"
                pesan_balasan += f"Total Supplier: **{len(hasil_sql)}**\n\n"
                pesan_balasan += "**Pilih supplier untuk kelola mapping:**\n"
                pesan_balasan += "Format: Nama Supplier (Aktif/Total)\n\n"
                pesan_balasan += "**Fitur:**\n"
                pesan_balasan += "• Lihat semua mapping produk\n"
                pesan_balasan += "• Aktifkan/nonaktifkan mapping\n"
                pesan_balasan += "• Filter berdasarkan status"
                
                bot.send_message(
                    message.chat.id,
                    pesan_balasan,
                    parse_mode='Markdown',
                    reply_markup=keyboard
                )
                
            else:
                pesan_balasan = f"⚙️ TIDAK ADA SUPPLIER\n\n"
                pesan_balasan += f"Nama: **{user_data['nama']}**\n\n"
                pesan_balasan += "Anda tidak terdaftar sebagai supplier aktif."
                bot.reply_to(message, pesan_balasan, parse_mode='Markdown')
            
    except Exception as e:
        bot.reply_to(message, f"Error: {str(e)}")
    finally:
        if conn and conn.open:
            conn.close()

#modul tambahan maping item

def handle_manage_mapping_supplier(call, bot):
    """Handle daftar mapping produk per supplier"""
    data_parts = call.data.replace('manage_mapping_', '').split('_page_')
    supplier_id = data_parts[0]
    page = int(data_parts[1]) if len(data_parts) > 1 else 1
    
    conn = connection()
    if conn is None:
        bot.answer_callback_query(call.id, "Koneksi database gagal")
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
                FROM tb_suplieritem si
                JOIN tbl_produk p ON si.iditem = p.id_produk
                WHERE si.idsuplier = %s 
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
            
            # Query mapping produk dengan paging
            sql.execute("""
                SELECT 
                    si.id as mapping_id,
                    p.id_produk,
                    p.nama_produk,
                    p.deskripsi,
                    si.harga as harga_beli,
                    s.satuan as nama_satuan,
                    si.isi,
                    si.aktif as status_mapping,
                    p.stok,
                    p.harga as harga_jual
                FROM tb_suplieritem si
                JOIN tbl_produk p ON si.iditem = p.id_produk
                LEFT JOIN tb_satuan s ON si.satuan = s.id
                WHERE si.idsuplier = %s 
                    AND p.aktif = 'Y'
                ORDER BY p.nama_produk
                LIMIT %s OFFSET %s
            """, (supplier_id, items_per_page, offset))
            
            hasil_mapping = sql.fetchall()
            
            if hasil_mapping or total_data > 0:
                # Buat pesan daftar mapping
                mapping_pesan = f"📋 MAPPING PRODUK - {nama_supplier}\n\n"
                mapping_pesan += f"**Halaman:** {page}/{total_pages}\n"
                mapping_pesan += f"**Total Mapping:** {total_data} produk\n\n"
                
                if hasil_mapping:
                    for i, mapping in enumerate(hasil_mapping, 1):
                        mapping_id = mapping['mapping_id']
                        nama_produk = mapping['nama_produk'] or "-"
                        deskripsi = mapping['deskripsi'] or "-"
                        harga_beli = mapping['harga_beli'] or 0
                        nama_satuan = mapping['nama_satuan'] or "PCS"
                        isi = mapping['isi'] or 1
                        status = mapping['status_mapping']
                        stok = mapping['stok'] or 0
                        harga_jual = mapping['harga_jual'] or 0
                        
                        # Format harga
                        harga_beli_rupiah = format_rupiah(harga_beli)
                        harga_jual_rupiah = format_rupiah(harga_jual)
                        
                        # Status icon
                        status_icon = "✅" if status == 'Y' else "❌"
                        status_text = "AKTIF" if status == 'Y' else "NON-AKTIF"
                        
                        nomor_urutan = i + offset
                        mapping_pesan += f"**{nomor_urutan}. {nama_produk} {status_icon}**\n"
                        mapping_pesan += f"   📝 {deskripsi[:30]}{'...' if len(deskripsi) > 30 else ''}\n"
                        mapping_pesan += f"   💰 Beli: {harga_beli_rupiah} | Jual: {harga_jual_rupiah}\n"
                        mapping_pesan += f"   📦 Stok: {stok} | Satuan: {nama_satuan} (isi: {isi})\n"
                        mapping_pesan += f"   🔧 Status: {status_text} | ID Mapping: `{mapping_id}`\n"
                        mapping_pesan += "   ──────────────\n"
                else:
                    mapping_pesan += "📭 Tidak ada data pada halaman ini\n\n"
                
                # Buat keyboard dengan tombol toggle untuk setiap produk
                keyboard = types.InlineKeyboardMarkup(row_width=2)
                
                # Tombol untuk setiap produk
                for i, mapping in enumerate(hasil_mapping, 1):
                    global_index = i + offset - 1
                    mapping_id = mapping['mapping_id']
                    nama_produk = mapping['nama_produk'] or "Produk"
                    status = mapping['status_mapping']
                    
                    status_icon = "✅" if status == 'Y' else "❌"
                    action = "Nonaktifkan" if status == 'Y' else "Aktifkan"
                    
                    button_text = f"{i}. {nama_produk[:15]} {status_icon}"
                    button = types.InlineKeyboardButton(
                        text=button_text,
                        callback_data=f"toggle_mapping_{mapping_id}_{global_index}"
                    )
                    keyboard.add(button)
                
                # Tombol paging jika ada lebih dari 1 halaman
                if total_pages > 1:
                    paging_buttons = []
                    
                    # Tombol Previous
                    if page > 1:
                        paging_buttons.append(
                            types.InlineKeyboardButton("⬅️", callback_data=f"manage_mapping_{supplier_id}_page_{page-1}")
                        )
                    
                    # Info halaman
                    paging_buttons.append(
                        types.InlineKeyboardButton(f"{page}/{total_pages}", callback_data="no_action")
                    )
                    
                    # Tombol Next
                    if page < total_pages:
                        paging_buttons.append(
                            types.InlineKeyboardButton("➡️", callback_data=f"manage_mapping_{supplier_id}_page_{page+1}")
                        )
                    
                    keyboard.add(*paging_buttons)
                
                # Tombol filter dan aksi
                action_buttons = []
                action_buttons.append(
                    types.InlineKeyboardButton("🔄 Refresh", callback_data=f"manage_mapping_{supplier_id}_page_{page}")
                )
                action_buttons.append(
                    types.InlineKeyboardButton("📊 Filter Aktif", callback_data=f"filter_mapping_{supplier_id}_Y_page_1")
                )
                action_buttons.append(
                    types.InlineKeyboardButton("📊 Filter Nonaktif", callback_data=f"filter_mapping_{supplier_id}_N_page_1")
                )
                action_buttons.append(
                    types.InlineKeyboardButton("📋 Semua", callback_data=f"manage_mapping_{supplier_id}_page_1")
                )
                keyboard.add(*action_buttons)
                
                # Tombol kembali
                keyboard.row(
                    types.InlineKeyboardButton("🔙 Kembali ke List", callback_data="back_to_mapping_menu")
                )
                
                # Edit atau kirim pesan baru
                try:
                    bot.edit_message_text(
                        chat_id=call.message.chat.id,
                        message_id=call.message.message_id,
                        text=mapping_pesan,
                        parse_mode='Markdown',
                        reply_markup=keyboard
                    )
                except Exception as e:
                    bot.send_message(
                        call.message.chat.id,
                        mapping_pesan,
                        parse_mode='Markdown',
                        reply_markup=keyboard
                    )
                
            else:
                # Tidak ada mapping sama sekali
                keyboard_empty = types.InlineKeyboardMarkup()
                keyboard_empty.row(
                    types.InlineKeyboardButton("➕ Tambah Mapping Baru", callback_data=f"add_mapping_{supplier_id}")
                )
                keyboard_empty.row(
                    types.InlineKeyboardButton("🔙 Kembali ke List", callback_data="back_to_mapping_menu")
                )
                
                try:
                    bot.edit_message_text(
                        chat_id=call.message.chat.id,
                        message_id=call.message.message_id,
                        text=f"📋 BELUM ADA MAPPING\n\nSupplier **{nama_supplier}** belum memiliki mapping produk.\n\nKlik tombol dibawah untuk menambahkan mapping baru.",
                        parse_mode='Markdown',
                        reply_markup=keyboard_empty
                    )
                except Exception as e:
                    bot.send_message(
                        call.message.chat.id,
                        f"📋 BELUM ADA MAPPING\n\nSupplier **{nama_supplier}** belum memiliki mapping produk.\n\nKlik tombol dibawah untuk menambahkan mapping baru.",
                        parse_mode='Markdown',
                        reply_markup=keyboard_empty
                    )
                
    except Exception as e:
        bot.answer_callback_query(call.id, f"Error: {str(e)}")
        print(f"Error in handle_manage_mapping_supplier: {e}")
    finally:
        if conn and conn.open:
            conn.close()

def handle_toggle_mapping(call, bot):
    """Handle toggle status mapping produk"""
    data_parts = call.data.replace('toggle_mapping_', '').split('_')
    if len(data_parts) >= 2:
        mapping_id = data_parts[0]
        global_index = int(data_parts[1])
    else:
        bot.answer_callback_query(call.id, "Data tidak valid")
        return
    
    # Toggle status di database
    success, new_status = toggle_mapping_status(mapping_id)
    
    if success:
        # Cari supplier_id dari paging state
        supplier_id = None
        current_page = 1
        if call.message.chat.id in paging_states:
            supplier_id = paging_states[call.message.chat.id].get('supplier_id')
            current_page = paging_states[call.message.chat.id].get('current_page', 1)
        
        if supplier_id:
            status_text = "diaktifkan" if new_status == 'Y' else "dinonaktifkan"
            bot.answer_callback_query(call.id, f"✅ Mapping {status_text}")
            
            # Refresh tampilan
            handle_manage_mapping_supplier(
                types.CallbackQuery(
                    id=call.id,
                    from_user=call.from_user,
                    message=call.message,
                    chat_instance=call.chat_instance,
                    data=f"manage_mapping_{supplier_id}_page_{current_page}"
                ),
                bot
            )
        else:
            bot.answer_callback_query(call.id, "Status diubah, refresh manual")
    else:
        bot.answer_callback_query(call.id, "❌ Gagal mengubah status")

def toggle_mapping_status(mapping_id):
    """Toggle status aktif/non-aktif mapping di database"""
    conn = connection()
    if conn is None:
        return False, None
    
    try:
        with conn.cursor() as sql:
            # Cek status saat ini
            sql.execute("""
                SELECT aktif FROM tb_suplieritem 
                WHERE id = %s
            """, (mapping_id,))
            
            result = sql.fetchone()
            if not result:
                return False, None
            
            current_status = result['aktif']
            new_status = 'N' if current_status == 'Y' else 'Y'
            
            # Update status
            sql.execute("""
                UPDATE tb_suplieritem 
                SET aktif = %s 
                WHERE id = %s
            """, (new_status, mapping_id))
            
            conn.commit()
            return True, new_status
            
    except Exception as e:
        conn.rollback()
        print(f"Error toggling mapping status: {e}")
        return False, None
    finally:
        if conn and conn.open:
            conn.close()

def handle_filter_mapping(call, bot):
    """Handle filter mapping berdasarkan status"""
    data_parts = call.data.replace('filter_mapping_', '').split('_')
    if len(data_parts) >= 3:
        supplier_id = data_parts[0]
        status_filter = data_parts[1]  # 'Y' atau 'N'
        page = int(data_parts[3]) if len(data_parts) > 3 else 1
    else:
        bot.answer_callback_query(call.id, "Data filter tidak valid")
        return
    
    conn = connection()
    if conn is None:
        bot.answer_callback_query(call.id, "Koneksi database gagal")
        return
    
    try:
        with conn.cursor() as sql:
            # Query untuk mendapatkan nama supplier
            sql.execute("SELECT namasuplier FROM tb_suplier WHERE id = %s", (supplier_id,))
            supplier_data = sql.fetchone()
            nama_supplier = supplier_data['namasuplier'] if supplier_data else "Supplier"
            
            # Hitung total data untuk paging dengan filter
            sql.execute("""
                SELECT COUNT(*) as total
                FROM tb_suplieritem si
                JOIN tbl_produk p ON si.iditem = p.id_produk
                WHERE si.idsuplier = %s 
                    AND p.aktif = 'Y'
                    AND si.aktif = %s
            """, (supplier_id, status_filter))
            
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
            
            # Query mapping produk dengan filter status
            sql.execute("""
                SELECT 
                    si.id as mapping_id,
                    p.id_produk,
                    p.nama_produk,
                    p.deskripsi,
                    si.harga as harga_beli,
                    s.satuan as nama_satuan,
                    si.isi,
                    si.aktif as status_mapping,
                    p.stok,
                    p.harga as harga_jual
                FROM tb_suplieritem si
                JOIN tbl_produk p ON si.iditem = p.id_produk
                LEFT JOIN tb_satuan s ON si.satuan = s.id
                WHERE si.idsuplier = %s 
                    AND p.aktif = 'Y'
                    AND si.aktif = %s
                ORDER BY p.nama_produk
                LIMIT %s OFFSET %s
            """, (supplier_id, status_filter, items_per_page, offset))
            
            hasil_mapping = sql.fetchall()
            
            # Buat pesan dengan filter info
            filter_text = "AKTIF" if status_filter == 'Y' else "NON-AKTIF"
            mapping_pesan = f"📋 MAPPING PRODUK - {nama_supplier}\n\n"
            mapping_pesan += f"**Filter:** {filter_text}\n"
            mapping_pesan += f"**Halaman:** {page}/{total_pages}\n"
            mapping_pesan += f"**Total Mapping:** {total_data} produk\n\n"
            
            if hasil_mapping:
                for i, mapping in enumerate(hasil_mapping, 1):
                    mapping_id = mapping['mapping_id']
                    nama_produk = mapping['nama_produk'] or "-"
                    deskripsi = mapping['deskripsi'] or "-"
                    harga_beli = mapping['harga_beli'] or 0
                    nama_satuan = mapping['nama_satuan'] or "PCS"
                    isi = mapping['isi'] or 1
                    status = mapping['status_mapping']
                    stok = mapping['stok'] or 0
                    harga_jual = mapping['harga_jual'] or 0
                    
                    # Format harga
                    harga_beli_rupiah = format_rupiah(harga_beli)
                    harga_jual_rupiah = format_rupiah(harga_jual)
                    
                    # Status icon
                    status_icon = "✅" if status == 'Y' else "❌"
                    status_text = "AKTIF" if status == 'Y' else "NON-AKTIF"
                    
                    nomor_urutan = i + offset
                    mapping_pesan += f"**{nomor_urutan}. {nama_produk} {status_icon}**\n"
                    mapping_pesan += f"   📝 {deskripsi[:30]}{'...' if len(deskripsi) > 30 else ''}\n"
                    mapping_pesan += f"   💰 Beli: {harga_beli_rupiah} | Jual: {harga_jual_rupiah}\n"
                    mapping_pesan += f"   📦 Stok: {stok} | Satuan: {nama_satuan} (isi: {isi})\n"
                    mapping_pesan += f"   🔧 Status: {status_text} | ID Mapping: `{mapping_id}`\n"
                    mapping_pesan += "   ──────────────\n"
            else:
                mapping_pesan += f"📭 Tidak ada mapping {filter_text.lower()}\n\n"
            
            # Buat keyboard dengan tombol toggle
            keyboard = types.InlineKeyboardMarkup(row_width=2)
            
            # Tombol untuk setiap produk
            for i, mapping in enumerate(hasil_mapping, 1):
                global_index = i + offset - 1
                mapping_id = mapping['mapping_id']
                nama_produk = mapping['nama_produk'] or "Produk"
                status = mapping['status_mapping']
                
                status_icon = "✅" if status == 'Y' else "❌"
                
                button_text = f"{i}. {nama_produk[:15]} {status_icon}"
                button = types.InlineKeyboardButton(
                    text=button_text,
                    callback_data=f"toggle_mapping_{mapping_id}_{global_index}"
                )
                keyboard.add(button)
            
            # Tombol paging jika ada lebih dari 1 halaman
            if total_pages > 1:
                paging_buttons = []
                
                # Tombol Previous
                if page > 1:
                    paging_buttons.append(
                        types.InlineKeyboardButton("⬅️", callback_data=f"filter_mapping_{supplier_id}_{status_filter}_page_{page-1}")
                    )
                
                # Info halaman
                paging_buttons.append(
                    types.InlineKeyboardButton(f"{page}/{total_pages}", callback_data="no_action")
                )
                
                # Tombol Next
                if page < total_pages:
                    paging_buttons.append(
                        types.InlineKeyboardButton("➡️", callback_data=f"filter_mapping_{supplier_id}_{status_filter}_page_{page+1}")
                    )
                
                keyboard.add(*paging_buttons)
            
            # Tombol filter dan aksi
            action_buttons = []
            action_buttons.append(
                types.InlineKeyboardButton("🔄 Refresh", callback_data=f"filter_mapping_{supplier_id}_{status_filter}_page_{page}")
            )
            
            # Tombol filter lain
            if status_filter == 'Y':
                action_buttons.append(
                    types.InlineKeyboardButton("📊 Filter Nonaktif", callback_data=f"filter_mapping_{supplier_id}_N_page_1")
                )
            else:
                action_buttons.append(
                    types.InlineKeyboardButton("📊 Filter Aktif", callback_data=f"filter_mapping_{supplier_id}_Y_page_1")
                )
            
            action_buttons.append(
                types.InlineKeyboardButton("📋 Semua", callback_data=f"manage_mapping_{supplier_id}_page_1")
            )
            keyboard.add(*action_buttons)
            
            # Tombol kembali
            keyboard.row(
                types.InlineKeyboardButton("🔙 Kembali ke List", callback_data="back_to_mapping_menu")
            )
            
            # Edit atau kirim pesan baru
            try:
                bot.edit_message_text(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    text=mapping_pesan,
                    parse_mode='Markdown',
                    reply_markup=keyboard
                )
            except Exception as e:
                bot.send_message(
                    call.message.chat.id,
                    mapping_pesan,
                    parse_mode='Markdown',
                    reply_markup=keyboard
                )
            
    except Exception as e:
        bot.answer_callback_query(call.id, f"Error: {str(e)}")
        print(f"Error in handle_filter_mapping: {e}")
    finally:
        if conn and conn.open:
            conn.close()

# ============================ FUNGSI BANTUAN MAPPING ============================

def get_mapping_stats(supplier_id):
    """Get statistics for mapping produk"""
    conn = connection()
    if conn is None:
        return None
    
    try:
        with conn.cursor() as sql:
            sql.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN aktif = 'Y' THEN 1 ELSE 0 END) as aktif,
                    SUM(CASE WHEN aktif = 'N' THEN 1 ELSE 0 END) as nonaktif
                FROM tb_suplieritem 
                WHERE idsuplier = %s
            """, (supplier_id,))
            
            return sql.fetchone()
    except Exception as e:
        print(f"Error getting mapping stats: {e}")
        return None
    finally:
        if conn and conn.open:
            conn.close()