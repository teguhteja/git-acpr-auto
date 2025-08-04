import google.generativeai as genai

def generate_commit_message(diff_content, model_name):
    """Mengirimkan diff ke Gemini API untuk membuat pesan commit."""
    # Prompt untuk Gemini
    prompt = f"""
    Anda adalah seorang asisten yang membantu membuat pesan commit Git. Berdasarkan perubahan kode berikut, buatlah satu baris pesan commit yang ringkas namun deskriptif dalam format conventional commit. Fokus pada tujuan utama dari perubahan ini.

    Contoh: feat: add user authentication feature

    Diff:
    {diff_content}

    Pesan commit (hanya satu baris):
    """

    try:
        print(f"Menganalisis perubahan dan membuat pesan commit menggunakan model '{model_name}'...")
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(prompt)
        commit_message = response.text.strip()
        
        # Hapus prefix atau konten tidak relevan lainnya dari respons Gemini
        if commit_message.startswith("Pesan commit:"):
            commit_message = commit_message.replace("Pesan commit:", "").strip()
        
        # Pastikan hanya satu baris
        return commit_message.split('\n')[0]
        
    except Exception as e:
        print(f"❌ Error saat menghubungi Gemini API: {e}")
        return None

def generate_pr_body(diff_content, model_name, commit_message, pr_template_content):
    """Meminta AI untuk mengisi template Pull Request berdasarkan diff dan pesan commit."""
    prompt = f"""
    Anda adalah seorang asisten ahli yang bertugas mengisi template Pull Request (PR) secara cerdas.
    Berdasarkan pesan commit, perubahan kode (diff), dan template PR yang diberikan, isi setiap bagian dari template.
    Pastikan untuk menjaga format asli template, termasuk header markdown (##), dan hanya mengisi bagian yang relevan.
    Jika sebuah bagian tidak relevan (misalnya, tidak ada 'breaking changes'), Anda bisa menyatakan "Tidak ada." atau biarkan kosong.

    Pesan Commit:
    {commit_message}

    Perubahan Kode (Diff):
    ```diff
    {diff_content}
    ```

    Template PR untuk diisi:
    ---
    {pr_template_content}
    ---

    Hasil Akhir (hanya template yang sudah diisi, tanpa teks tambahan):
    """
    try:
        print(f"Menganalisis perubahan dan membuat deskripsi PR menggunakan model '{model_name}'...")
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"❌ Error saat menghubungi Gemini API untuk deskripsi PR: {e}")
        return None
