import subprocess
import shutil
import os

def get_current_branch():
    """Mendapatkan nama branch Git saat ini."""
    try:
        result = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"❌ Error saat mendapatkan nama branch: {e.stderr}")
        return None

def has_unpushed_commits():
    """Mengecek apakah ada commit lokal yang belum di-push ke upstream."""
    try:
        # Membandingkan HEAD lokal dengan upstream-nya. Jika ada commit, outputnya > 0.
        # stderr diarahkan ke DEVNULL untuk menekan pesan error jika upstream tidak di-set.
        result = subprocess.run(
            ["git", "rev-list", "--count", "@{u}..HEAD"],
            capture_output=True, text=True, check=True, stderr=subprocess.DEVNULL
        )
        commit_count = int(result.stdout.strip())
        return commit_count > 0
    except (subprocess.CalledProcessError, ValueError):
        # Terjadi jika upstream tidak di-set atau output tidak valid.
        # Kita tidak bisa yakin, jadi lebih aman menganggap tidak ada.
        return False

def get_last_commit_message():
    """Mendapatkan pesan dari commit terakhir."""
    try:
        result = subprocess.run(["git", "log", "-1", "--pretty=%B"], capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"❌ Error saat mendapatkan pesan commit terakhir: {e.stderr}")
        return None

def get_diff_for_unpushed_commits():
    """Mendapatkan diff dari semua commit yang belum di-push."""
    try:
        # Dapatkan diff antara HEAD lokal dan upstream-nya.
        # stderr diarahkan ke DEVNULL untuk menekan pesan error jika upstream tidak di-set.
        result = subprocess.run(
            ["git", "diff", "@{u}..HEAD"],
            capture_output=True, text=True, check=True, stderr=subprocess.DEVNULL
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, ValueError):
        # Terjadi jika upstream tidak di-set atau tidak ada perbedaan.
        return None

def git_add():
    """Menambahkan semua perubahan ke staging area (`git add .`)."""
    print("Menambahkan semua perubahan ke staging area (`git add .`)...")
    result = subprocess.run(["git", "add", "."], capture_output=True, text=True)
    if result.returncode != 0:
        print("❌ Error saat menjalankan 'git add .':")
        print(result.stderr)
        return False
    print("✅ Perubahan berhasil ditambahkan.")
    return True

def get_git_diff():
    """Mendapatkan perbedaan (diff) dari perubahan yang sudah di-staged."""
    try:
        result = subprocess.run(["git", "diff", "--cached"], capture_output=True, text=True, check=True)
        diff_output = result.stdout
        if not diff_output:
            print("ℹ️ Tidak ada perubahan yang di-staged untuk di-commit.")
            return None
        return diff_output
    except subprocess.CalledProcessError as e:
        print(f"❌ Error saat mendapatkan diff Git: {e.stderr}")
        return None
    except FileNotFoundError:
        print("❌ Error: Perintah 'git' tidak ditemukan. Pastikan Git sudah terinstal dan ada di PATH Anda.")
        return None

def git_commit(message):
    """Membuat commit dengan pesan yang diberikan."""
    print("\nMembuat commit...")
    command = ["git", "commit", "-m", message]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        print("❌ Error saat membuat commit:")
        print(result.stderr)
        return False
    print("✅ Commit berhasil dibuat!")
    return True

def git_push(branch_name):
    """Melakukan push ke remote repository, mengatur upstream jika perlu."""
    print(f"\nMelakukan push branch '{branch_name}' ke remote repository...")
    # -u akan mengatur remote branch sebagai upstream untuk branch lokal
    command = ["git", "push", "-u", "origin", branch_name]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        # Cek jika error karena PR sudah ada, ini bukan error fatal
        if "pull request" in result.stderr and "already exists" in result.stderr:
             print(f"ℹ️ Push berhasil, tetapi PR untuk branch '{branch_name}' sepertinya sudah ada.")
             print(result.stderr.strip())
             return True
        print("❌ Error saat melakukan push:")
        print(result.stderr)
        return False
    print("✅ Push berhasil!")
    print(result.stdout)
    return True

def create_pull_request(target_branch, title, body):
    """Membuat Pull Request menggunakan GitHub CLI ('gh')."""
    if not shutil.which("gh"):
        print("❌ Error: GitHub CLI ('gh') tidak ditemukan. Fungsionalitas PR tidak dapat berjalan.")
        print("  Silakan install dari: https://cli.github.com/ dan jalankan 'gh auth login'.")
        return False

    print(f"\nMembuat Pull Request ke branch '{target_branch}'...")
    command = [
        "gh", "pr", "create",
        "--base", target_branch,
        "--title", title,
        "--body", body
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        print("❌ Error saat membuat Pull Request:")
        print(result.stderr)
        return False
    
    print("✅ Pull Request berhasil dibuat!")
    print(result.stdout) # Tampilkan URL PR
    return True
