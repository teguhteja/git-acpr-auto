import argparse
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
    parser.add_argument("--steps", type=str, default="acpr", help="Langkah yang akan dijalankan: a(add), c(commit), p(push), pr(pull request). Contoh: 'acp'. Default: 'acpr'")
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

    # Gunakan AI untuk mengisi template
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
    git_utils.create_pull_request(args.target_branch, pr_title, final_pr_body)

if __name__ == "__main__":
    main()
