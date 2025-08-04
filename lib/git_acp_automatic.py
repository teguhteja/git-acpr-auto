import os
import argparse
import google.generativeai as genai
import subprocess
from dotenv import load_dotenv

# Memuat variabel dari file .env
load_dotenv()

# Konfigurasi API Key
GANAI_API_KEY = os.getenv("GANAI_API_KEY")
if not GANAI_API_KEY:
    raise ValueError("GANAI_API_KEY not found in .env file.")
genai.configure(api_key=GANAI_API_KEY)


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

def get_git_diff():
    """Mendapatkan perbedaan (diff) dari perubahan yang sudah di-staged."""
    try:
        result = subprocess.run(["git", "diff", "--cached"], capture_output=True, text=True, check=True)
        diff_output = result.stdout
        if not diff_output:
            print("Tidak ada perubahan yang di-staged untuk di-commit.")
            return None
        return diff_output
    except subprocess.CalledProcessError as e:
        print(f"❌ Error saat mendapatkan diff Git: {e.stderr}")
        return None
    except FileNotFoundError:
        print("❌ Error: Perintah 'git' tidak ditemukan. Pastikan Git sudah terinstal dan ada di PATH Anda.")
        return None

def generate_commit_message(diff_content, model_name):
    """Mengirimkan diff ke Gemini API untuk membuat pesan commit."""
    # Prompt untuk Gemini
    prompt = f"""
    Anda adalah seorang asisten yang membantu membuat pesan commit Git. Berdasarkan perubahan kode berikut, buatlah satu baris pesan commit yang ringkas namun deskriptif. Fokus pada tujuan utama dari perubahan ini.

    Diff:
    {diff_content}

    Pesan commit (hanya satu baris):
    """

    try:
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(prompt)
        commit_message = response.text.strip()
        
        # Hapus prefix atau konten tidak relevan lainnya dari respons Gemini
        if commit_message.startswith("Pesan commit:"):
            commit_message = commit_message.replace("Pesan commit:", "").strip()
        
        # Pastikan hanya satu baris
        commit_message = commit_message.split('\n')[0]

        return commit_message
        
    except Exception as e:
        print(f"Error saat menghubungi Gemini API: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(
        description="Membuat pesan commit Git otomatis berdasarkan perubahan yang di-staged.",
        epilog="Contoh: python git-commit-automatic.py -k 100 -m gemini-1.5-pro-latest"
    )
    parser.add_argument("-k", "--max-kb", type=int, default=100, help="Ukuran maksimal folder (dalam KB) agar skrip ini berjalan. (Default: 50)")
    parser.add_argument("-m", "--model", type=str, default="gemini-1.5-flash-latest", help="Nama model Gemini yang akan digunakan. (Default: gemini-1.5-flash-latest)")
    args = parser.parse_args()

    # --- PENGECEKAN UKURAN FOLDER ---
    total_size_bytes = get_directory_size()
    total_size_kb = total_size_bytes / 1024

    print(f"ℹ️  Ukuran total folder proyek (tanpa .git): {total_size_kb:.2f} KB.")

    if total_size_kb >= args.max_kb:
        print(f"Ukuran folder melebihi {args.max_kb} KB. Script ini dihentikan.")
        print("   (Pengecekan ini untuk mencegah commit tidak sengaja pada repositori besar.)")
        return
    
    print("-" * 30)
    # --- AKHIR PENGECEKAN ---

    # --- LANGKAH 1: GIT ADD ---
    print("Menambahkan semua perubahan ke staging area (`git add .`)...")
    add_result = subprocess.run(["git", "add", "."], capture_output=True, text=True)
    if add_result.returncode != 0:
        print("❌ Error saat menjalankan 'git add .':")
        print(add_result.stderr)
        return
    print("✅ Perubahan berhasil ditambahkan.")

    diff = get_git_diff()
    if not diff:
        return

    print(f"Menganalisis perubahan dan membuat pesan commit menggunakan model '{args.model}'...")
    commit_message = generate_commit_message(diff, args.model)

    if commit_message:
        print(f"\nPesan commit yang disarankan:\n'{commit_message}'")
        
        # Konfirmasi sebelum commit dan push
        confirm = input("\nApakah Anda ingin commit dan push dengan pesan ini? (y/n): ")
        if confirm.lower() == 'y':
            # Commit
            print("\nMembuat commit...")
            commit_command = ["git", "commit", "-m", commit_message]
            commit_result = subprocess.run(commit_command, capture_output=True, text=True)
            if commit_result.returncode != 0:
                print("❌ Error saat membuat commit:")
                print(commit_result.stderr)
                return
            print("✅ Commit berhasil dibuat!")

            # Push
            print("\nMelakukan push ke remote repository...")
            push_result = subprocess.run(["git", "push"], capture_output=True, text=True)
            if push_result.returncode != 0:
                print("❌ Error saat melakukan push:")
                print(push_result.stderr)
                return
            print("✅ Push berhasil!")
        else:
            print("Operasi dibatalkan.")
    else:
        print("Gagal membuat pesan commit otomatis.")

if __name__ == "__main__":
    main()
