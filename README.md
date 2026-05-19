# 🚀 YouTube Auto Pusher V1.0

> **Tự động đăng video lên YouTube đa kênh

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

1. Tải file `YouTube Auto Pusher Setup V1.0.exe` từ link trên
2. Chạy file → chọn thư mục cài đặt → Next → Install
3. Tích _"Create a desktop shortcut"_ để có icon ngoài Desktop
4. Bấm **Finish** → App tự mở

---

### Bước 2: Lấy Google API Key (chỉ làm 1 lần)

> ⚠️ Phải làm đúng bước này thì app mới đăng được video lên kênh của bạn.

#### 2.1 Tạo Google Cloud Project

1. Mở Chrome, vào: **https://console.cloud.google.com**
2. Đăng nhập bằng Gmail của bạn
3. Ở góc trái trên cùng, bấm vào **dropdown chọn project** (cạnh logo Google Cloud)
4. Bấm **NEW PROJECT**
5. **Project name:** gõ `YouTube Auto Pusher` (hoặc tên gì tùy bạn)
6. **Location:** để mặc định `No organization`
7. Bấm **CREATE** → đợi vài giây

#### 2.2 Bật YouTube Data API v3

1. Menu trái (biểu tượng ☰) → **APIs & Services** → **Library**
2. Gõ vào ô tìm kiếm: `YouTube Data API v3`
3. Click vào kết quả tìm được
4. Bấm nút **ENABLE** (màu xanh)

#### 2.3 Tạo OAuth Consent Screen

1. Menu trái → **APIs & Services** → **OAuth consent screen**
2. Chọn **User Type:** `External` → bấm **CREATE**
3. Điền thông tin:
   - **App name:** `YouTube Auto Pusher`
   - **User support email:** chọn email của bạn trong dropdown
   - **Developer contact:** chọn email của bạn
   - (Các ô còn lại bỏ trống)
4. Kéo xuống dưới → bấm **SAVE AND CONTINUE**
5. Màn hình **Scopes** → bấm **ADD OR REMOVE SCOPES**
   - Tìm và tích chọn 2 scope:
     - `https://www.googleapis.com/auth/youtube.upload`
     - `https://www.googleapis.com/auth/youtube.readonly`
   - Bấm **UPDATE** → **SAVE AND CONTINUE**
6. Màn hình **Test users** → bấm **ADD USERS**
   - Nhập Gmail của bạn → **ADD**
   - Bấm **SAVE AND CONTINUE**
7. Màn hình Summary → bấm **BACK TO DASHBOARD**

#### 2.4 Tạo OAuth Client ID (Desktop app)

1. Menu trái → **APIs & Services** → **Credentials**
2. Bấm nút **+ CREATE CREDENTIALS** (trên cùng) → chọn **OAuth client ID**
3. ⚠️ **Application type:** Chọn `Desktop app` (QUAN TRỌNG - không chọn Web application!)
4. **Name:** `YouTube Auto Pusher Desktop`
5. Bấm **CREATE**
6. Cửa sổ popup hiện ra → bấm **DOWNLOAD JSON**
7. File tải về có tên: `client_secret_XXXXX...json`
8. **Giữ file này** — dùng ở Bước 3

---

### Bước 3: Thêm kênh YouTube vào app

1. Mở app → tab **Kênh & Video** → bấm **Thêm kênh**
2. Nhập tên kênh (vd: "Kênh Game Của Tôi")
3. Bấm **Chọn file** → chọn file `client_secret_XXX.json` vừa tải ở Bước 2
4. Bấm **Tạo & Check API**
5. Chrome tự mở → **Đăng nhập Gmail của kênh YouTube**
6. Google hỏi: _"YouTube Auto Pusher wants to access your Google Account"_
   - Nếu thấy cảnh báo _"Google hasn't verified this app"_ → bấm **Continue**
   - Chọn kênh YouTube bạn muốn dùng → bấm **Allow**
7. ✅ Kênh đã kết nối! Trên app sẽ hiện tên kênh YouTube của bạn

---

### Bước 4: Đăng video

1. Bấm nút **Quản lý video** trên kênh muốn đăng
2. Bấm **Thêm video** → chọn 1 hoặc nhiều video (Ctrl+Click để chọn nhiều)
3. Bấm vào từng video để mở **Setting**
4. Điền:
   - **Tiêu đề video** (bắt buộc)
   - **Mô tả** (tùy chọn)
   - **Tags, Hashtags** (tùy chọn)
   - **Lịch đăng** (nếu muốn hẹn giờ — ô này có viền xanh nổi bật)
   - **Múi giờ** (mặc định: Asia/Ho_Chi_Minh)
5. Bấm **💾 Lưu và chạy** → Video tự động đăng lên YouTube!
6. Vào tab **Báo cáo** để xem kết quả + link video

---

### Bước 5: Xem kết quả đăng

- Vào tab **Báo cáo**
- Mục **Upload gần đây** hiện danh sách video đã đăng
- Bấm vào **🔗 Mở video** để xem trên YouTube
- Bấm nút **📋** để copy link video
- Mục **7 ngày qua** hiện biểu đồ số lượng video đã đăng mỗi ngày

---

## 🎬 Thao tác nhanh

| Bạn muốn | Làm thế nào |
|----------|------------|
| Thêm kênh mới | **Thêm kênh** → nhập tên → chọn JSON → **Tạo & Check API** |
| Đăng video ngay | **Quản lý video** → **Thêm video** → mở Setting → **Lưu và chạy** |
| Đăng nhiều video 1 lúc | Ctrl+Click chọn nhiều file khi thêm → mở từng video Setting → Lưu |
| Hẹn giờ đăng | Mở Setting video → chọn ngày giờ ở ô **Lịch đăng** → Lưu |
| Đổi kênh YouTube | Nếu Gmail có nhiều kênh → dropdown chọn kênh trên boxcard |
| Xem link video đã đăng | Tab **Báo cáo** → bấm link 🔗 |
| Copy link video | Tab **Báo cáo** → bấm nút 📋 cạnh link |
| Copy tên kênh | Tab **Báo cáo** → bấm nút 📋 cạnh tên kênh |
| Xóa kênh | Hover chuột vào boxcard → bấm nút 🗑️ góc phải trên |
| Sửa kênh | Hover chuột vào boxcard → bấm nút ✏️ góc phải trên |
| Chạy ngầm | Bấm **X** → app ẩn xuống khay hệ thống (góc phải thanh taskbar) |
| Mở lại app từ khay | Double-click icon YouTube trên khay hệ thống |

---

## ❓ FAQ

**Q: App có mất phí không?**
A: App miễn phí. Google API cũng miễn phí (giới hạn ~6 video/ngày).

**Q: Tôi có nhiều kênh YouTube trên cùng 1 Gmail, có cần tạo nhiều profile không?**
A: Không. Sau khi Check API, app tự quét tất cả kênh. Dropdown chọn kênh hiện ngay trên boxcard.

**Q: App có lấy cookie/mật khẩu của tôi không?**
A: Không. App dùng OAuth chính thức của Google. Mỗi kênh có Chrome profile riêng biệt hoàn toàn.

**Q: Tôi muốn đăng lên kênh của Gmail khác?**
A: Tạo profile mới → Check API → đăng nhập Gmail của kênh đó.

**Q: Bị lỗi "redirect_uri_mismatch" khi đăng nhập Google?**
A: Bạn đã chọn sai Application type. Phải chọn **Desktop app** (không phải Web application). Xóa client ID cũ, tạo lại với đúng loại.

**Q: App báo "API Off" thì làm sao?**
A: Bấm nút **Check API** trên kênh đó → chọn lại file JSON → đăng nhập lại.

**Q: Làm sao để tăng giới hạn upload?**
A: Vào Google Cloud Console → xin verify app → quota tăng lên ~100 video/ngày. Cần có channel YouTube đã bật kiếm tiền.

**Q: Tôi đổi kênh YouTube trên app nhưng link đăng lên vẫn kênh cũ?**
A: Sau khi chọn kênh mới từ dropdown, các video thêm SAU ĐÓ mới đăng lên kênh mới. Video đã có trong danh sách vẫn giữ kênh cũ.

---

## 📄 License

Copyright © 2026 All rights reserved.
