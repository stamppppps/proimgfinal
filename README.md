# 🌍 Immersia 360 – Mobile Stitch  
> ระบบต่อภาพพาโนรามาอัตโนมัติจากภาพถ่ายหรือวิดีโอ  
---

## 🧠 Project Overview
**Immersia 360** คือระบบ FastAPI ที่สามารถรวมหลายภาพ (หรือเฟรมจากวิดีโอ)  
ให้กลายเป็นภาพพาโนรามาแบบ 360° ได้อัตโนมัติ พร้อมหน้าเว็บ UI ที่ใช้งานง่าย  
รองรับทั้งโหมด **Panorama** และ **Scans**  

---

## 🚀 Getting Started

### 🧩 1. Clone the Project
```bash
git clone https://github.com/yourname/immersia360.git
cd immersia360
```

---

### ⚙️ 2. Install Dependencies
ใช้ Python 3.9 ขึ้นไป (แนะนำ 3.11+)

```bash
# (ทางเลือก) สร้าง virtual environment
python -m venv .venv
source .venv/bin/activate      # macOS / Linux
# หรือ
.venv\Scripts\activate         # Windows

# ติดตั้ง dependencies หลัก
pip install -U fastapi "uvicorn[standard]" python-multipart numpy opencv-python watchfiles
```

---

### 🖥️ 3. Run the Server (Backend)
```bash
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

เปิดเว็บเบราว์เซอร์ไปที่:  
👉 [http://127.0.0.1:8000](http://127.0.0.1:8000)

---

## 💻 Project Structure
```
immersia360/
├── main.py              # FastAPI backend (API endpoints)
├── index.html           # Web UI (upload images, stitch, view 360°)
├── static/              # Static files (optional)
└── README.md            # Documentation
```

---

## 🧭 API Endpoints

### 🖼️ 1. `/stitch` – สร้างพาโนรามาจากหลายภาพ
| Parameter | Type | Description |
|------------|------|-------------|
| `files` | List[UploadFile] | รูปภาพ 2 รูปขึ้นไป |
| `mode` | str | "panorama" / "scans" |
| `max_width` | int | ความกว้างสูงสุดของภาพ (0 = ไม่ย่อ) |

🔹 **Response:** JPEG Panorama Image

---

### 🎞️ 2. `/stitch_video` – พาโนรามาจากวิดีโอ
| Parameter | Type | Description |
|------------|------|-------------|
| `video` | UploadFile | ไฟล์วิดีโอ `.mp4` / `.mov` |
| `frame_step` | int | ข้ามทุกกี่เฟรม |
| `max_frames` | int | จำนวนเฟรมสูงสุด |
| `max_width` | int | ความกว้างเฟรมสูงสุด |
| `mode` | str | "panorama" / "scans" |

🔹 **Response:** JPEG Panorama Image

---

### 🔍 3. `/stitch_matches` – ดูเส้นเชื่อมระหว่างภาพ
| Parameter | Type | Description |
|------------|------|-------------|
| `files` | List[UploadFile] | รูปภาพ 2 รูปขึ้นไป |
| `max_width` | int | ย่อก่อนแสดงผล |

🔹 **Response:** JPEG Image showing ORB matches

---

### 🎬 4. `/stitch_video_matches` – ดูเส้นเชื่อมระหว่างเฟรมในวิดีโอ
| Parameter | Type | Description |
|------------|------|-------------|
| `video` | UploadFile | วิดีโอ |
| `frame_step` | int | ข้ามเฟรม |
| `max_frames` | int | จำนวนเฟรมสูงสุด |
| `max_width` | int | ย่อก่อนแสดงผล |

---

## 🧪 Example Usage (CLI)

```bash
# Stitch from multiple images
curl -X POST "http://127.0.0.1:8000/stitch"   -F "files=@img1.jpg" -F "files=@img2.jpg"   -F "mode=panorama" -F "max_width=2000"   --output panorama.jpg
```

```bash
# Stitch from video
curl -X POST "http://127.0.0.1:8000/stitch_video"   -F "video=@clip.mp4" -F "frame_step=10" -F "max_frames=20"   --output pano_from_video.jpg
```

---

## 🎨 Web UI Features
- 📤 Upload ภาพ/วิดีโอได้จากเบราว์เซอร์
- 🧮 เลือกโหมด `panorama` หรือ `scans`
- 🧭 กดปุ่ม **ดูแบบ 360°** เพื่อเปิด viewer (Pannellum)
- 📸 ปุ่ม **ดาวน์โหลดภาพผลลัพธ์** ได้โดยตรง
- 💾 จดจำ API URL อัตโนมัติ (LocalStorage)

---

## 🧠 Tips
- ภาพควรมี **overlap 30–60%**
- หลีกเลี่ยงการหมุนเร็วหรือภาพที่เบลอ
- หากพาโนรามาผิดพลาด ลอง:
  - สลับโหมด `scans`
  - ลด `max_width`
  - เพิ่ม `max_frames`
  - ลด `frame_step`

---



