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

def generate_enhanced_pr_body(diff_content, model_name, commit_message, pr_template_content, historical_diffs):
    """Membuat PR body yang diperkaya dengan konteks historis dari diff files."""
    
    # Buat konteks historis dari diff files
    historical_context = ""
    if historical_diffs:
        historical_context = "\n\nKonteks Historis dari Commit Sebelumnya:\n"
        for i, diff_info in enumerate(historical_diffs, 1):
            historical_context += f"\n{i}. Commit {diff_info['hash']} ({diff_info['filename']}):\n"
            historical_context += f"```diff\n{diff_info['content'][:1000]}...\n```\n"
    
    prompt = f"""
    Anda adalah seorang asisten ahli yang bertugas mengisi template Pull Request (PR) secara cerdas dan mendetail.
    Berdasarkan pesan commit, perubahan kode (diff) saat ini, konteks historis dari commit sebelumnya, dan template PR yang diberikan, 
    isi setiap bagian dari template dengan informasi yang komprehensif dan berguna.

    Pastikan untuk:
    1. Menjaga format asli template, termasuk header markdown (##)
    2. Menganalisis pola perubahan dari konteks historis untuk memberikan insight yang lebih dalam
    3. Menjelaskan bagaimana perubahan ini berhubungan dengan commit sebelumnya
    4. Memberikan konteks yang lebih kaya tentang evolusi kode
    5. Menyebutkan potensi dampak dan pertimbangan berdasarkan tren perubahan

    Pesan Commit Saat Ini:
    {commit_message}

    Perubahan Kode Saat Ini (Diff):
    ```diff
    {diff_content}
    ```
    {historical_context}

    Template PR untuk diisi:
    ---
    {pr_template_content}
    ---

    Hasil Akhir (template yang sudah diisi dengan analisis yang diperkaya):
    """
    
    try:
        print(f"Menganalisis perubahan dengan konteks historis menggunakan model '{model_name}'...")
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"❌ Error saat menghubungi Gemini API untuk enhanced PR body: {e}")
        return None

def generate_strict_template_pr_body(diff_content, model_name, commit_message, pr_template_content, unused_diffs):
    """Membuat PR body dengan strict adherence ke template, menggunakan unused diff files sebagai konteks."""
    
    # Buat konteks dari unused diff files
    unused_context = ""
    if unused_diffs:
        unused_context = "\n\nKonteks dari Diff Files yang Belum Digunakan untuk PR:\n"
        unused_context += "Gunakan informasi berikut untuk memberikan konteks yang lebih kaya:\n"
        for i, diff_info in enumerate(unused_diffs, 1):
            unused_context += f"\n{i}. Diff File: {diff_info['filename']} (Hash: {diff_info['hash']})\n"
            unused_context += f"```diff\n{diff_info['content']}\n```\n"
    
    prompt = f"""
    Anda adalah seorang technical writer ahli yang HARUS mengisi template Pull Request dengan KETAT mengikuti format yang diberikan.

    ATURAN KETAT:
    1. WAJIB mempertahankan struktur template yang persis sama, termasuk semua header markdown (##)
    2. WAJIB mengisi setiap bagian dengan konten yang relevan dan informatif
    3. JANGAN menambah atau mengurangi section dari template
    4. JANGAN mengubah format atau urutan section
    5. Gunakan konteks dari unused diff files untuk memberikan analisis yang lebih komprehensif
    6. Isi checkbox dengan [x] jika relevan, biarkan [ ] jika tidak
    7. Berikan analisis teknis yang detail berdasarkan semua diff yang tersedia

    Template yang HARUS diikuti (format ini TIDAK BOLEH diubah):
    ---
    {pr_template_content}
    ---

    Pesan Commit:
    {commit_message}

    Diff Perubahan Saat Ini:
    ```diff
    {diff_content}
    ```
    {unused_context}

    HASIL AKHIR (HARUS mengikuti template persis seperti di atas, hanya konten yang diisi):
    """
    
    try:
        print(f"Mengisi template PR dengan strict format menggunakan model '{model_name}'...")
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"❌ Error saat menghubungi Gemini API untuk strict template PR body: {e}")
        return None
