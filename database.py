import pymysql
from config import config

def connection():
    """Create database connection"""
    try:
        conn = pymysql.connect(
            host=config.DB_HOST,
            user=config.DB_USER,
            password=config.DB_PASSWORD,
            db=config.DB_NAME,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        return conn
    except Exception as e:
        print(f"Database connection error: {e}")
        return None

def get_nik_from_telegram(user_id):
    """Get user data from telegram ID"""
    conn = connection()
    if conn is None:
        return None
    
    try:
        with conn.cursor() as sql:
            sql.execute("""
                SELECT nik, nama 
                FROM tb_karyawan 
                WHERE id_tele = %s AND aktif = 'Y'
            """, (user_id,))
            result = sql.fetchone()
            return result
    except Exception as e:
        print(f"Error get_nik_from_telegram: {e}")
        return None
    finally:
        if conn and conn.open:
            conn.close()

def get_nama_satuan(id_satuan):
    """Get unit name from tb_satuan"""
    if not id_satuan:
        return "PCS"
    
    conn = connection()
    if conn is None:
        return "PCS"
    
    try:
        with conn.cursor() as sql:
            sql.execute("SELECT satuan FROM tb_satuan WHERE id = %s AND aktif = 'Y'", (id_satuan,))
            result = sql.fetchone()
            return result['satuan'] if result else "PCS"
    except Exception as e:
        print(f"Error get_nama_satuan: {e}")
        return "PCS"
    finally:
        if conn and conn.open:
            conn.close()