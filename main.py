import argparse
import os
import sys
from lib import ai_utils, config, git_utils, utils

def main():
    """Fungsi utama untuk menjalankan alur kerja git acp otomatis."""
    try:
        config.configure_api()
    except ValueError as e:
        print(f"❌ Error Konfigurasi: {e}")
        sys.exit(1)

    # Parser sementara untuk mendapatkan path file konfigurasi
    conf_parser = argparse.ArgumentParser(
        description='Git ACPR Automatic Helper.',
        add_help=False  # Nonaktifkan help untuk parser sementara ini
    )
    conf_parser.add_argument(
        "-c", "--config",
        default="conf/git_acp.conf",
        help="Path ke file konfigurasi. (Default: conf/git_acp.conf)"
    )
    conf_args, remaining_argv = conf_parser.parse_known_args()

    # Muat konfigurasi dari file
    app_config = config.load_app_config(conf_args.config)

    # Tetapkan nilai default dari file konfigurasi, dengan fallback ke nilai hardcoded
    default_max_kb = int(app_config.get('max-kb', 100))
    default_model = app_config.get('model', 'gemini-1.5-flash-latest')
    default_pr_branch = app_config.get('branch-pr', 'develop')
    default_pr_template = app_config.get('pr-template', 'prompt/pull_request_template.md')
    default_auto_save_diff = app_config.get('auto-save-diff', 'false').lower() == 'true'
    default_folder_diff = app_config.get('folder-diff', 'diff')

    # Parser utama yang menggunakan nilai default dari konfigurasi
    parser = argparse.ArgumentParser(
        parents=[conf_parser], # Warisi argumen -c dari parser sementara
        description="Otomatisasi Git Add, Commit, Push, dan Pull Request.",
        epilog="Argumen command-line akan menimpa pengaturan di file konfigurasi."
    )
    parser.add_argument("-k", "--max-kb", type=int, default=default_max_kb, help=f"Ukuran maksimal folder (dalam KB). Default: {default_max_kb}")
    parser.add_argument("-m", "--model", type=str, default=default_model, help=f"Nama model Gemini. Default: {default_model}")
    parser.add_argument("--target-branch", type=str, default=default_pr_branch, help=f"Branch target untuk Pull Request. Default: {default_pr_branch}")
    parser.add_argument("--pr-template", type=str, default=default_pr_template, help=f"Path ke template Pull Request. Default: {default_pr_template}")
    parser.add_argument("--auto-save-diff", action="store_true", default=default_auto_save_diff, help=f"Simpan diff commit ke file. Default: {default_auto_save_diff}")
    parser.add_argument("--folder-diff", type=str, default=default_folder_diff, help=f"Folder untuk menyimpan file diff. Default: {default_folder_diff}")
    parser.add_argument("--steps", type=str, default="acp", help="Langkah yang akan dijalankan: a(add), c(commit), p(push), pr(pull request). Contoh: 'acp'. Default: 'acp'")
    args = parser.parse_args(remaining_argv)

    # --- PENGECEKAN UKURAN FOLDER ---
    total_size_bytes = utils.get_directory_size()
    total_size_kb = total_size_bytes / 1024
    print(f"ℹ️  Ukuran total folder proyek (tanpa .git): {total_size_kb:.2f} KB.")

    if total_size_kb >= args.max_kb:
        print(f"Ukuran folder melebihi {args.max_kb} KB. Script ini dihentikan.")
        print("   (Pengecekan ini untuk mencegah commit tidak sengaja pada repositori besar.)")
        return
    
    steps = args.steps.lower()

    # --- PROSES GIT ---
    current_branch = git_utils.get_current_branch()
    if not current_branch:
        return

    # Cek jika kita berada di branch target, berikan peringatan.
    if current_branch == args.target_branch:
        print(f"⚠️  Peringatan: Anda sedang berada di branch target ('{current_branch}').")
        print("   Skrip tidak akan melakukan push atau membuat PR dari branch ini untuk mencegah kesalahan.")
        # Kita bisa tetap lanjut untuk commit lokal jika ada perubahan.

    print("-" * 30)

    # --- Langkah A: Add ---
    if 'a' in steps:
        if not git_utils.git_add():
            return
    else:
        print("ℹ️ Langkah 'add' dilewati.")

    diff = git_utils.get_git_diff()

    # --- Jalur 1: Ada perubahan baru yang di-stage ---
    if not diff:
        # --- Jalur 2: Tidak ada perubahan baru, cek commit lama ---
        if git_utils.has_unpushed_commits():
            print("ℹ️ Tidak ada perubahan baru yang di-stage, tetapi ada commit yang belum di-push.")
            
            # Ambil info untuk PR SEBELUM push, karena setelah push diff akan kosong
            diff_for_pr = git_utils.get_diff_for_unpushed_commits()
            commit_msg_for_pr = git_utils.get_last_commit_message()

            if 'p' in steps:
                if not git_utils.git_push(current_branch): return
            else:
                print("ℹ️ Langkah 'push' dilewati. Tidak dapat melanjutkan ke PR.")
                return

            if 'pr' in steps:
                create_pr_flow(diff_for_pr, commit_msg_for_pr, current_branch, args)
            else:
                print("ℹ️ Langkah 'pull request' dilewati.")
        elif 'pr' in steps:
            # --- Jalur 3: Hanya ingin membuat PR untuk branch yang sudah ada ---
            print("ℹ️ Tidak ada perubahan baru atau commit yang belum di-push.")
            print("ℹ️ Mencoba membuat PR untuk branch saat ini terhadap target branch...")
            
            # Cek apakah ada perbedaan dengan target branch
            diff_for_pr = git_utils.get_diff_against_branch(args.target_branch)
            commits_info = git_utils.get_commits_against_branch(args.target_branch)
            
            if not diff_for_pr and not commits_info:
                print(f"ℹ️ Tidak ada perbedaan antara branch saat ini dan '{args.target_branch}'.")
                print("   Tidak ada yang perlu di-PR.")
                return
            
            # Gunakan commit terakhir sebagai judul PR
            commit_msg_for_pr = git_utils.get_last_commit_message()
            if not commit_msg_for_pr:
                commit_msg_for_pr = f"PR: {current_branch} to {args.target_branch}"
            
            create_pr_flow(diff_for_pr, commit_msg_for_pr, current_branch, args)
        return # Selesai, karena tidak ada perubahan baru untuk di-commit

    # --- Langkah C: Commit ---
    commit_message = None
    if 'c' in steps:
        commit_message = ai_utils.generate_commit_message(diff, args.model)
        if not commit_message:
            print("Gagal membuat pesan commit otomatis. Proses dihentikan.")
            return

        print(f"\n✨ Pesan commit yang disarankan:\n   '{commit_message}'")
        try:
            confirm_commit = input("\n❓ Apakah Anda ingin commit dengan pesan ini? (y/n): ")
        except KeyboardInterrupt:
            print("\nOperasi dibatalkan oleh pengguna.")
            return

        if confirm_commit.lower() != 'y':
            print("ℹ️ Operasi commit dibatalkan.")
            return

        if not git_utils.git_commit(commit_message):
            return # Gagal commit
        
        # Simpan diff jika auto-save-diff diaktifkan
        if args.auto_save_diff:
            save_commit_diff(diff, args.folder_diff)
    else:
        print("ℹ️ Langkah 'commit' dilewati. Perubahan baru tidak akan di-push atau di-PR-kan.")
        return

    # --- Langkah P: Push ---
    if 'p' in steps:
        if not git_utils.git_push(current_branch): return
    else:
        print("ℹ️ Langkah 'push' dilewati. Tidak dapat melanjutkan ke PR.")
        return

    # --- Langkah PR: Pull Request ---
    if 'pr' in steps:
        create_pr_flow(diff, commit_message, current_branch, args)
    else:
        print("ℹ️ Langkah 'pull request' dilewati.")

def save_commit_diff(diff, folder_diff):
    """Simpan diff commit ke file dengan nama COMMIT_HASH.diff"""
    try:
        # Dapatkan hash commit terakhir
        commit_hash = git_utils.get_last_commit_hash()
        if not commit_hash:
            print("⚠️ Tidak dapat mendapatkan hash commit, diff tidak disimpan.")
            return
        
        # Buat folder jika belum ada
        if not os.path.exists(folder_diff):
            os.makedirs(folder_diff)
            print(f"📁 Folder '{folder_diff}' dibuat.")
        
        # Nama file diff (gunakan 8 karakter pertama dari commit hash)
        diff_filename = f"{commit_hash[:8]}.diff"
        diff_filepath = os.path.join(folder_diff, diff_filename)
        
        # Simpan diff ke file
        with open(diff_filepath, 'w', encoding='utf-8') as f:
            f.write(diff)
        
        print(f"💾 Diff commit disimpan ke: {diff_filepath}")
        
    except Exception as e:
        print(f"⚠️ Gagal menyimpan diff: {e}")

def get_pr_tracking_file(folder_diff):
    """Mendapatkan path file untuk tracking diff yang sudah digunakan untuk PR"""
    return os.path.join(folder_diff, '.pr_used_diffs.txt')

def mark_diff_as_used_for_pr(diff_filename, folder_diff):
    """Menandai diff file sebagai sudah digunakan untuk PR"""
    try:
        tracking_file = get_pr_tracking_file(folder_diff)
        with open(tracking_file, 'a', encoding='utf-8') as f:
            f.write(f"{diff_filename}\n")
        print(f"📝 Diff {diff_filename} ditandai sebagai sudah digunakan untuk PR")
    except Exception as e:
        print(f"⚠️ Gagal menandai diff sebagai used: {e}")

def get_used_diff_files(folder_diff):
    """Mendapatkan daftar diff files yang sudah digunakan untuk PR"""
    tracking_file = get_pr_tracking_file(folder_diff)
    used_files = set()
    
    if os.path.exists(tracking_file):
        try:
            with open(tracking_file, 'r', encoding='utf-8') as f:
                used_files = {line.strip() for line in f.readlines() if line.strip()}
        except Exception as e:
            print(f"⚠️ Gagal membaca tracking file: {e}")
    
    return used_files

def collect_unused_diffs_for_pr(folder_diff, current_diff_hash=None, limit=3):
    """Kumpulkan diff files yang belum digunakan untuk PR sebagai konteks tambahan"""
    try:
        if not os.path.exists(folder_diff):
            return []
        
        used_files = get_used_diff_files(folder_diff)
        
        # Ambil semua file .diff dan filter yang belum digunakan
        unused_diffs = []
        for filename in os.listdir(folder_diff):
            if filename.endswith('.diff') and filename not in used_files:
                # Skip current diff jika ada
                if current_diff_hash and filename.startswith(current_diff_hash[:8]):
                    continue
                    
                filepath = os.path.join(folder_diff, filename)
                mtime = os.path.getmtime(filepath)
                unused_diffs.append((filepath, filename, mtime))
        
        # Urutkan berdasarkan waktu modifikasi (terbaru dulu) dan batasi
        unused_diffs.sort(key=lambda x: x[2], reverse=True)
        selected_diffs = unused_diffs[:limit]
        
        diff_contexts = []
        for filepath, filename, _ in selected_diffs:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    diff_content = f.read()
                    hash_part = filename.replace('.diff', '')
                    diff_contexts.append({
                        'filename': filename,
                        'hash': hash_part,
                        'content': diff_content[:1500]  # Batasi panjang untuk efisiensi prompt
                    })
            except Exception as e:
                print(f"⚠️ Gagal membaca unused diff file {filepath}: {e}")
                continue
        
        print(f"📋 Ditemukan {len(diff_contexts)} diff file yang belum digunakan untuk PR")
        return diff_contexts
        
    except Exception as e:
        print(f"⚠️ Error saat mengumpulkan unused diffs: {e}")
        return []

def create_pr_flow(diff, commit_message, current_branch, args):
    """Mengatur alur pembuatan Pull Request."""
    # Pengecekan branch target (ini adalah implementasi dari permintaan Anda)
    if current_branch == args.target_branch:
        print(f"ℹ️ Branch saat ini ('{current_branch}') sama dengan branch target ('{args.target_branch}').")
        print("   Pull Request tidak dibuat untuk menghindari PR ke branch yang sama.")
        return

    print("\n--- Membuat Pull Request ---")
    template_content = utils.read_file_content(args.pr_template)
    if not template_content:
        print("Membatalkan pembuatan PR karena template tidak ditemukan.")
        return

    # Dapatkan hash commit saat ini untuk tracking
    current_commit_hash = git_utils.get_last_commit_hash()
    
    # Kumpulkan diff files yang belum digunakan untuk PR
    print("📋 Mengumpulkan diff files yang belum digunakan untuk PR...")
    unused_diffs = collect_unused_diffs_for_pr(args.folder_diff, current_commit_hash, limit=3)
    
    # Gunakan AI untuk mengisi template dengan strict adherence dan unused diffs
    final_pr_body = ai_utils.generate_strict_template_pr_body(
        diff, args.model, commit_message, template_content, unused_diffs
    )
    
    # Fallback ke metode lama jika fungsi baru tidak tersedia
    if not final_pr_body:
        print("⚠️ Menggunakan metode standar untuk membuat PR body...")
        final_pr_body = ai_utils.generate_pr_body(diff, args.model, commit_message, template_content)
    
    if not final_pr_body:
        print("Gagal membuat deskripsi PR. Membatalkan pembuatan PR.")
        return

    # Gunakan pesan commit sebagai judul PR
    pr_title = commit_message

    # Tampilkan hasil dan minta konfirmasi akhir
    print("\n" + "="*10 + " PR Preview " + "="*10)
    print(f"Title: {pr_title}")
    print("-" * 30)
    print("Body:")
    print(final_pr_body)
    print("=" * 32)

    try:
        confirm_pr = input("\n❓ Buat Pull Request dengan konten di atas? (y/n): ")
        if confirm_pr.lower() != 'y':
            print("ℹ️ Pembuatan Pull Request dibatalkan.")
            return
    except KeyboardInterrupt:
        print("\nOperasi dibatalkan oleh pengguna.")
        return

    # Buat Pull Request
    pr_success = git_utils.create_pull_request(args.target_branch, pr_title, final_pr_body)
    
    # Tandai diff files sebagai sudah digunakan untuk PR jika berhasil
    if pr_success:
        # Mark current commit's diff as used
        if current_commit_hash:
            current_diff_filename = f"{current_commit_hash[:8]}.diff"
            mark_diff_as_used_for_pr(current_diff_filename, args.folder_diff)
        
        # Mark unused diffs that were used in PR context as used
        for unused_diff in unused_diffs:
            mark_diff_as_used_for_pr(unused_diff['filename'], args.folder_diff)

if __name__ == "__main__":
    main()
