import os

def get_directory_size(start_path='.'):
    """
    Menghitung total ukuran direktori dalam byte, mengabaikan folder .git.
    """
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(start_path):
        # Mencegah os.walk masuk ke dalam direktori .git
        if '.git' in dirnames:
            dirnames.remove('.git')
            
        for f in filenames:
            fp = os.path.join(dirpath, f)
            if not os.path.islink(fp):
                total_size += os.path.getsize(fp)
    return total_size

def read_file_content(file_path):
    """Membaca dan mengembalikan konten dari sebuah file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        print(f"❌ Error: File template '{file_path}' tidak ditemukan.")
        return None
    except Exception as e:
        print(f"❌ Error saat membaca file '{file_path}': {e}")
        return None
