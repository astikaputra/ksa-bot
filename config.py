import os

class Config:
    def __init__(self):
        self.load_config()
    
    def load_config(self):
        """Load configuration from config.txt file"""
        try:
            with open('config.txt', 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        key, value = line.split('=', 1)
                        setattr(self, key, value)
        except FileNotFoundError:
            print("File config.txt tidak ditemukan. Menggunakan nilai default.")
            self.set_defaults()
        except Exception as e:
            print(f"Error loading config: {e}")
            self.set_defaults()
    
    def set_defaults(self):
        """Set default values if config file not found"""
        self.DB_HOST = 'localhost'
        self.DB_USER = 'root'
        self.DB_PASSWORD = ''
        self.DB_NAME = 'db_ksa'
        self.BOT_TOKEN = ''
        self.LOG_FILE = 'log_bot.txt'
        self.ITEMS_PER_PAGE = 10

# Global config instance
config = Config()