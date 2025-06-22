# Tahap 1: Gunakan base image Python yang ringan
FROM python:3.10-slim

# Tetapkan direktori kerja utama di dalam server
WORKDIR /app

# Perbarui daftar paket server dan instal dependensi yang dibutuhkan oleh Chrome
# wget dan unzip dibutuhkan untuk mengunduh dan mengekstrak file
RUN apt-get update && apt-get install -y \
    wget \
    unzip \
    --no-install-recommends

# Unduh Google Chrome versi stabil untuk Linux
RUN wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb

# Instal Google Chrome dari file yang diunduh, lalu hapus file installer-nya
RUN apt-get install -y ./google-chrome-stable_current_amd64.deb --fix-broken --no-install-recommends
RUN rm google-chrome-stable_current_amd64.deb

# Salin file daftar kebutuhan Python terlebih dahulu
# Docker akan menggunakan cache di langkah ini jika file tidak berubah, mempercepat build
COPY requirements.txt .

# Instal semua modul Python yang dibutuhkan
RUN pip install --no-cache-dir -r requirements.txt

# Salin semua sisa file proyek Anda (main_bot_pro.py, config.json, dll.) ke server
COPY . .

# Perintah yang akan dijalankan secara otomatis saat server dinyalakan
CMD ["python", "bot.py"]