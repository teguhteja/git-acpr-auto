import os
import google.generativeai as genai
from dotenv import load_dotenv
import configparser

def configure_api():
    """Memuat variabel .env dan mengkonfigurasi API key Gemini."""
    # Coba load .env dari current directory dulu
    load_dotenv()
    api_key = os.getenv("GANAI_API_KEY")
    
    # Jika tidak ada, coba dari script directory
    if not api_key:
        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        env_path = os.path.join(script_dir, '.env')
        load_dotenv(env_path)
        api_key = os.getenv("GANAI_API_KEY")
    
    if not api_key:
        raise ValueError("GANAI_API_KEY tidak ditemukan di file .env. Silakan buat file .env dan tambahkan kunci Anda.")
    genai.configure(api_key=api_key)
    print("✅ API Key berhasil dimuat dan dikonfigurasi.")

def load_app_config(config_path):
    """
    Memuat konfigurasi aplikasi dari file .conf.
    Mengembalikan dictionary dari section [settings] atau dictionary kosong jika tidak ada.
    """
    config = configparser.ConfigParser()

    if not os.path.exists(config_path):
        # Coba cari dari script directory
        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        alternative_config_path = os.path.join(script_dir, config_path)
        
        if os.path.exists(alternative_config_path):
            config_path = alternative_config_path
            print(f"ℹ️  File konfigurasi ditemukan di: {config_path}")
        else:
            # Ini bukan error, karena nilai default akan digunakan. Cukup informasikan.
            print(f"ℹ️  File konfigurasi '{config_path}' tidak ditemukan, menggunakan nilai default.")
            return {}

    try:
        config.read(config_path)
        if 'settings' in config:
            print(f"✅ Konfigurasi berhasil dimuat dari '{config_path}'.")
            return config['settings']
        else:
            # File ada tapi tidak ada section [settings]
            print(f"⚠️  Peringatan: Section [settings] tidak ditemukan di '{config_path}'. Menggunakan nilai default.")
            return {}
    except configparser.Error as e:
        print(f"❌ Error saat mem-parsing file konfigurasi '{config_path}': {e}")
        return {} # Kembalikan dict kosong jika ada error parsing
