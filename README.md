# 🚀 YouTube Auto Pusher V1.0

> **Tự động đăng video lên YouTube đa kênh — by OSN OCIF**

[![Download](https://img.shields.io/badge/Download-Latest-blue)](https://github.com/Cofi295/youtube-auto-pusher/releases/latest)
[![Version](https://img.shields.io/badge/version-1.0.0-green)](https://github.com/Cofi295/youtube-auto-pusher/releases)

---

## 📥 Tải về

👉 **[Tải phiên bản mới nhất](https://github.com/Cofi295/youtube-auto-pusher/releases/latest)**

Chọn file `YouTube Auto Pusher Setup V1.0.exe` → tải về → chạy.

---

## 🎯 Tính năng chính

| Tính năng | Mô tả |
|-----------|-------|
| 🤖 **Tự động đăng video** | Chọn video → chỉnh tiêu đề/mô tả → bấm Lưu & Chạy → tự upload lên YouTube |
| 📺 **Đa kênh YouTube** | Quản lý nhiều kênh cùng lúc, mỗi kênh hoàn toàn độc lập |
| 🔄 **Chuyển đổi kênh** | Một Gmail nhiều kênh? Chuyển đổi trực tiếp trên app không cần đăng nhập lại |
| 📊 **Báo cáo 7 ngày** | Biểu đồ upload, lịch sử đăng video, link YouTube đã đăng |
| ⏰ **Lên lịch đăng** | Đặt ngày giờ đăng cho từng video |
| 🔒 **Chrome riêng biệt** | Mỗi kênh một Chrome profile riêng, cookie không dính nhau |
| 🪟 **Chạy ngầm System Tray** | Bấm X → ẩn xuống khay hệ thống, vẫn đăng video bình thường |
| 🔄 **Auto-update** | Tự động phát hiện và cập nhật phiên bản mới |

---

## 🖥️ Yêu cầu hệ thống

- **Windows 10/11 64-bit**
- **Google Chrome** (để đăng nhập YouTube)
- **Kết nối Internet**

---

## 📖 Hướng dẫn sử dụng

### Bước 1: Cài đặt

1. Tải file `YouTube Auto Pusher Setup V1.0.exe`
2. Chạy file → chọn thư mục cài đặt → Next → Install
3. Tích _"Create a desktop shortcut"_ để có icon ngoài Desktop
4. Bấm **Finish** → App tự mở

---

### Bước 2: Lấy Google API Key (chỉ làm 1 lần)

> ⚠️ **Quan trọng:** Bạn cần tạo API key từ Google Cloud để app có thể đăng video lên kênh của bạn.

**Xem video hướng dẫn:** [Cách tạo Google OAuth Client ID](https://www.youtube.com/results?search_query=create+google+oauth+2.0+desktop+client+id)

**Hoặc làm theo các bước sau:**

1. Vào https://console.cloud.google.com
2. Tạo Project mới (tên gì cũng được)
3. Vào **APIs & Services** → **Library** → tìm `YouTube Data API v3` → **Enable**
4. Vào **APIs & Services** → **OAuth consent screen**
   - Chọn **External** → Create
   - Điền tên app bất kỳ, email của bạn
   - Thêm scope: `youtube.upload` và `youtube.readonly`
   - Thêm test user: email của bạn
5. Vào **APIs & Services** → **Credentials** → **Create Credentials** → **OAuth client ID**
   - ⚠️ Chọn **Application type = Desktop app** (QUAN TRỌNG!)
   - Đặt tên → Create
6. **Download JSON** → được file `client_secret_xxx.json`

---

### Bước 3: Thêm kênh YouTube

1. Mở app → tab **Kênh & Video** → bấm **Thêm kênh**
2. Nhập tên kênh (vd: "Kênh Game Của Tôi")
3. Chọn file `client_secret_xxx.json` vừa tải ở Bước 2
4. Bấm **Tạo & Check API**
5. Chrome tự mở → **Đăng nhập Gmail của kênh YouTube**
6. Google hỏi cấp quyền → bấm **Cho phép / Allow**
7. ✅ Kênh đã kết nối! Bạn sẽ thấy tên kênh hiện trên boxcard

---

### Bước 4: Đăng video

1. Bấm nút **Quản lý video** trên kênh muốn đăng
2. Bấm **Thêm video** → chọn 1 hoặc nhiều video (Ctrl+Click)
3. Bấm vào từng video để mở **Setting**
4. Điền:
   - **Tiêu đề video** (bắt buộc)
   - **Mô tả** (tùy chọn)
   - **Tags, Hashtags** (tùy chọn)
   - **Lịch đăng** (nếu muốn hẹn giờ)
   - **Múi giờ** (mặc định: Asia/Ho_Chi_Minh)
5. Bấm **💾 Lưu và chạy** → Video tự động đăng lên YouTube!
6. Vào tab **Báo cáo** để xem kết quả + link video

---

### Bước 5: Xem kết quả

- **Tab Báo cáo**: Xem biểu đồ 7 ngày, danh sách video đã đăng, link YouTube
- Bấm vào link 🔗 để mở video trên YouTube
- Bấm nút 📋 để copy link video

---

## 🎬 Thao tác nhanh

| Bạn muốn | Làm thế nào |
|----------|------------|
| Thêm kênh mới | Bấm **Thêm kênh** → chọn JSON → **Tạo & Check API** → đăng nhập Google |
| Đăng video | **Quản lý video** → **Thêm video** → chọn file → mở Setting → **Lưu và chạy** |
| Đăng nhiều video | Ctrl+Click chọn nhiều file lúc thêm → mở từng video Setting → Lưu |
| Hẹn giờ đăng | Mở Setting video → chọn ngày giờ ở ô **Lịch đăng** → Lưu |
| Đổi kênh YouTube | Nếu Gmail có nhiều kênh → dropdown chọn kênh ngay trên boxcard |
| Xem link đã đăng | Tab **Báo cáo** → Upload gần đây → bấm link 🔗 |
| Xóa kênh | Hover chuột vào boxcard → bấm nút 🗑️ góc phải trên |
| Chạy ngầm | Bấm **X** → app ẩn xuống khay hệ thống (góc phải màn hình) |

---

## ❓ FAQ

**Q: App có mất phí không?**
A: App miễn phí. Bạn chỉ cần có Google Cloud API key (cũng miễn phí, giới hạn 6 video/ngày với tài khoản thường).

**Q: Tôi có nhiều kênh YouTube trên cùng 1 Gmail, có cần tạo nhiều profile không?**
A: Không. App tự quét tất cả kênh trên Gmail đó và cho phép chuyển đổi trực tiếp.

**Q: App có lấy cắp cookie/mật khẩu không?**
A: Không. App dùng OAuth chính thức của Google. Mỗi kênh có Chrome profile riêng hoàn toàn biệt lập.

**Q: Tôi muốn đăng video lên kênh khác Gmail thì sao?**
A: Tạo thêm profile mới → Check API → đăng nhập Gmail của kênh đó.

**Q: App báo lỗi "API Off" thì làm sao?**
A: Bấm nút **Check API** trên kênh đó → chọn lại file JSON → đăng nhập lại.

**Q: Làm sao để tăng giới hạn upload?**
A: Vào Google Cloud Console → xin verify app → quota tăng lên 100 video/ngày.

---

## 🔧 Dành cho nhà phát triển

```bash
# Clone repo
git clone https://github.com/Cofi295/youtube-auto-pusher.git

# Dev mode
cd electron-ui
npm install
cd ..
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

# Chay app dev
python main.py          # Flet mode
run_electron.bat        # Electron mode

# Build
build_all.ps1           # Full pipeline
```

---

## 📄 License

Copyright © 2026 OSN OCIF. All rights reserved.
