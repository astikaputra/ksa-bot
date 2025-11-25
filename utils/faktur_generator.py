import datetime
from database import connection

def generate_kode_supplier(nama_supplier):
    """
    Generate 3 digit kode supplier dari nama supplier
    Contoh: WIRASA -> WIR
    """
    if not nama_supplier:
        return "SUP"
    
    # Hilangkan spasi dan ubah ke uppercase
    nama_clean = nama_supplier.replace(" ", "").upper()
    
    # Ambil 3 karakter pertama
    if len(nama_clean) >= 3:
        kode = nama_clean[:3]
    else:
        # Jika nama kurang dari 3 karakter, tambahkan karakter tambahan
        kode = nama_clean.ljust(3, 'X')
    
    return kode

def generate_nomor_faktur_otomatis(supplier_id):
    """
    Generate nomor faktur otomatis berdasarkan format: KODE_SUPPLIER/TAHUN/BULAN/SEQUENCE
    Contoh: WIR/2024/12/001
    """
    conn = connection()
    if conn is None:
        return None
    
    try:
        with conn.cursor() as sql:
            # Ambil nama supplier
            sql.execute("SELECT namasuplier FROM tb_suplier WHERE id = %s", (supplier_id,))
            supplier_data = sql.fetchone()
            
            if not supplier_data:
                return None
                
            nama_supplier = supplier_data['namasuplier']
            kode_supplier = generate_kode_supplier(nama_supplier)
            
            # Dapatkan tahun dan bulan sekarang
            sekarang = datetime.datetime.now()
            tahun = sekarang.strftime('%Y')
            bulan = sekarang.strftime('%m')
            
            # Cari sequence terakhir untuk supplier, tahun, dan bulan ini
            sql.execute("""
                SELECT nofaktur 
                FROM tb_riceve 
                WHERE idsuplier = %s 
                    AND YEAR(tgl) = %s 
                    AND MONTH(tgl) = %s 
                    AND nofaktur LIKE %s
                ORDER BY id DESC 
                LIMIT 1
            """, (supplier_id, tahun, bulan, f"{kode_supplier}/{tahun}/{bulan}/%"))
            
            last_faktur = sql.fetchone()
            
            if last_faktur:
                # Extract sequence number dari nomor faktur terakhir
                last_sequence = last_faktur['nofaktur'].split('/')[-1]
                try:
                    sequence = int(last_sequence) + 1
                except ValueError:
                    sequence = 1
            else:
                sequence = 1
            
            # Format sequence menjadi 3 digit
            sequence_str = f"{sequence:03d}"
            
            # Buat nomor faktur
            nomor_faktur = f"{kode_supplier}/{tahun}/{bulan}/{sequence_str}"
            
            return nomor_faktur
            
    except Exception as e:
        print(f"Error generate_nomor_faktur_otomatis: {e}")
        return None
    finally:
        if conn and conn.open:
            conn.close()