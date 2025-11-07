from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import Response, JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import numpy as np
import cv2
import os, tempfile
from typing import List

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static",StaticFiles(directory="."),name="static")

@app.get("/")
def home():
    return FileResponse("index.html")

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/stitch")
async def stitch(
    files: List[UploadFile] = File(...,description="เลือกรูป >= 2"),
    mode: str = Form("panorama"),
    max_width: int = Form(2000),
):
    if len(files) < 2:
        return JSONResponse({"error": "ต้องมีภาพอย่างน้อย 2 รูป"},status_code=400)

    images = []
    for f in files:
        raw = await f.read()
        arr = np.frombuffer(raw,np.uint8)
        img = cv2.imdecode(arr,cv2.IMREAD_COLOR)
        if img is None:
            return JSONResponse({"error": f"อ่านไฟล์ไม่ได้: {f.filename}"},status_code=400)
        if max_width and img.shape[1] > max_width:
            scale = max_width / float(img.shape[1])
            img = cv2.resize(
                img,
                (int(img.shape[1] * scale),int(img.shape[0] * scale)),
                interpolation=cv2.INTER_AREA,
            )
        images.append(img)

    stitch_mode =(
        cv2.Stitcher_SCANS if mode.lower() == "scans" else cv2.Stitcher_PANORAMA
    )
    stitcher = cv2.Stitcher_create(stitch_mode)
    status, pano = stitcher.stitch(images)

    if status != cv2.Stitcher_OK or pano is None:
        return JSONResponse(
            {
                "error": f"stitch ล้มเหลว (status={status})",
                "hints": [
                    "เพิ่ม overlap 30–60%",
                    "หลีกเลี่ยงภาพเบลอ/แสงต่างกันมาก",
                    "ลองสลับโหมด panorama/scans",
                    "ตั้ง max_width=0 เพื่อไม่ย่อรูป",
                ],
            },
            status_code=422,
        )

    pad = cv2.copyMakeBorder(
        pano, 10, 10, 10, 10,cv2.BORDER_CONSTANT,value=(0, 0, 0)
    )
    gray = cv2.cvtColor(pad,cv2.COLOR_BGR2GRAY)
    _, th = cv2.threshold(gray,0,255,cv2.THRESH_BINARY)
    cnts, _ = cv2.findContours(th,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
    if cnts:
        x, y, w, h = cv2.boundingRect(max(cnts,key=cv2.contourArea))
        pad = pad[y:y + h, x:x + w]

    ok, out = cv2.imencode(".jpg",pad,[int(cv2.IMWRITE_JPEG_QUALITY), 92])
    if not ok:
        return JSONResponse({"error":"บันทึกภาพล้มเหลว"},status_code=500)

    return Response(content=out.tobytes(), media_type="image/jpeg")




def _auto_crop_black_border(bgr_img):
    pad = cv2.copyMakeBorder(
        bgr_img, 10, 10, 10, 10,cv2.BORDER_CONSTANT,value=(0, 0, 0)
    )
    gray = cv2.cvtColor(pad,cv2.COLOR_BGR2GRAY)
    _, th = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY)
    cnts, _ = cv2.findContours(th, cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
    if cnts:
        x, y, w, h = cv2.boundingRect(max(cnts,key=cv2.contourArea))
        pad = pad[y:y + h,x:x + w]
    return pad


def _letterbox_to_2to1(bgr_img):
    H, W = bgr_img.shape[:2]
    target_H = W // 2
    if H == target_H:
        return bgr_img.copy()
    if H > target_H:
        y0 = max(0, (H - target_H) // 2)
        y1 = y0 + target_H
        return bgr_img[y0:y1, :]
    else:
        pad_total = target_H - H
        top = pad_total // 2
        bottom = pad_total - top
        return cv2.copyMakeBorder(
            bgr_img, top, bottom, 0, 0, cv2.BORDER_CONSTANT,value=(0, 0, 0)
        )


def _read_video_frames(tmp_path, frame_step=10,max_frames=20,max_width=1280):
    cap = cv2.VideoCapture(tmp_path)
    if not cap.isOpened():
        return [], "เปิดวิดีโอไม่ได้"
    frames = []
    idx = 0
    grabbed = True
    while grabbed and len(frames) < max_frames:
        grabbed,frame = cap.read()
        if not grabbed:
            break
        if idx % frame_step == 0:
            if frame is None:
                break
            h, w = frame.shape[:2]
            if max_width and w > max_width:
                scale = max_width/float(w)
                frame = cv2.resize(
                    frame,
                    (int(w * scale), int(h * scale)),
                    interpolation=cv2.INTER_AREA,
                )
            frames.append(frame)
        idx += 1
    cap.release()
    if len(frames) < 2:
        return [],"ต้องได้เฟรมอย่างน้อย 2 เฟรม"
    return frames,None


@app.post("/stitch_video")
async def stitch_video(
    video: UploadFile = File(...,description="อัปโหลดไฟล์วิดีโอ"),
    mode: str = Form("panorama"),
    frame_step: int = Form(100),
    max_frames: int = Form(200),
    max_width: int = Form(1280),
    force_equirect_2to1: int = Form(1),
):
    try:
        raw = await video.read()
    except Exception:
        return JSONResponse({"error":"อ่านไฟล์วิดีโอล้มเหลว"},status_code=400)

    try:
        with tempfile.NamedTemporaryFile(
            delete=False, suffix=os.path.splitext(video.filename or "")[-1]
        ) as tmp:
            tmp.write(raw)
            tmp_path = tmp.name
    except Exception:
        return JSONResponse({"error": "ไม่สามารถเซฟไฟล์ชั่วคราวได้"},status_code=500)

    try:
        frames, err = _read_video_frames(
            tmp_path,
            frame_step=frame_step,
            max_frames=max_frames,
            max_width=max_width,
        )
        if err:
            return JSONResponse(
                {
                    "error": f"extract เฟรมล้มเหลว:{err}",
                    "hints": [
                        "ตรวจสอบวิดีโอว่าเปิดได้",
                        "เพิ่ม max_frames หรือ ลด frame_step",
                        "ตั้ง max_width=0 ถ้าต้องการความละเอียดสูง",
                    ],
                },
                status_code=422,
            )

        stitch_mode =(
            cv2.Stitcher_SCANS
            if mode.lower() == "scans"
            else cv2.Stitcher_PANORAMA
        )
        stitcher = cv2.Stitcher_create(stitch_mode)
        status, pano = stitcher.stitch(frames)

        if status != cv2.Stitcher_OK or pano is None:
            return JSONResponse(
                {
                    "error": f"stitch ล้มเหลว (status={status})",
                    "hints": [
                        "หมุนกล้องให้ overlap 30–60%",
                        "เลี่ยงเบลอ/แสงต่างกันมาก",
                        "ลองโหมด panorama/scans",
                        "เพิ่ม max_frames หรือ ลด frame_step",
                    ],
                },
                status_code=422,
            )

        pano = _auto_crop_black_border(pano)
        if force_equirect_2to1:
            pano = _letterbox_to_2to1(pano)

        ok, out = cv2.imencode(".jpg", pano, [int(cv2.IMWRITE_JPEG_QUALITY), 92])
        if not ok:
            return JSONResponse({"error": "บันทึกรูปล้มเหลว"}, status_code=500)

        return Response(content=out.tobytes(), media_type="image/jpeg")
    finally:
        try:
            os.remove(tmp_path)
        except Exception:
            pass




def _draw_matches_sheet(images, max_width_each=600, max_pairs=4):
    orb = cv2.ORB_create(nfeatures=1500)
    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
    panels = []
    n = min(len(images) - 1,max_pairs)

    for i in range(n):
        a, b = images[i],images[i + 1]

        def _resize(img, mw):
            h, w = img.shape[:2]
            if w <= mw:
                return img
            s = mw / float(w)
            return cv2.resize(img, (mw, int(h * s)),interpolation=cv2.INTER_AREA)

        a_small = _resize(a,max_width_each)
        b_small = _resize(b,max_width_each)

        ka, da = orb.detectAndCompute(a_small,None)
        kb, db = orb.detectAndCompute(b_small,None)

        if da is None or db is None:
            panel = np.hstack([a_small, b_small])
        else:
            matches = bf.match(da, db)
            matches = sorted(matches, key=lambda m:m.distance)[:100]
            panel = cv2.drawMatches(a_small, ka, b_small, kb, matches, None, flags=2)

        cv2.putText(panel, f"Pair {i+1}",(10,25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8,(0, 55,255), 2)
        panels.append(panel)

    if not panels:
        return None
    hmax = max(p.shape[0] for p in panels)
    panels_pad = [np.pad(p, ((0, hmax - p.shape[0]), (0, 0), (0, 0))) for p in panels]
    return np.vstack(panels_pad)


@app.post("/stitch_matches")
async def stitch_matches(
    files: List[UploadFile] = File(..., description="เลือกรูป >= 2"),
    max_width: int = Form(1200),
):
    if len(files) < 2:
        return JSONResponse({"error": "ต้องมีภาพอย่างน้อย 2 รูป"}, status_code=400)

    images = []
    for f in files:
        raw = await f.read()
        arr = np.frombuffer(raw, np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is None:
            return JSONResponse({"error": f"อ่านไฟล์ไม่ได้: {f.filename}"}, status_code=400)
        if max_width and img.shape[1] > max_width:
            scale = max_width / float(img.shape[1])
            img = cv2.resize(
                img,
                (int(img.shape[1] * scale), int(img.shape[0] * scale)),
                interpolation=cv2.INTER_AREA,
            )
        images.append(img)

    sheet = _draw_matches_sheet(images)
    if sheet is None:
        return JSONResponse({"error": "ไม่สามารถสร้างภาพ matches ได้"}, status_code=422)

    ok, out = cv2.imencode(".jpg", sheet, [int(cv2.IMWRITE_JPEG_QUALITY), 92])
    if not ok:
        return JSONResponse({"error": "บันทึกภาพ matches ล้มเหลว"}, status_code=500)

    return Response(content=out.tobytes(), media_type="image/jpeg")



      
       