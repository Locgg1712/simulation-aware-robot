# tools/ai_to_sprite.py
import sys
import numpy as np
from PIL import Image
from scipy import ndimage

def convert(src, dst, target_w=128, colors=32):
    img = Image.open(src).convert("RGBA")
    a = np.array(img)
    rgb = a[..., :3].astype(int)

    # 1. Nền = pixel sáng, ít sắc độ (trắng + bóng xám) và nối với mép ảnh
    bright = rgb.min(axis=2) > 165
    low_sat = (rgb.max(axis=2) - rgb.min(axis=2)) < 45
    cand = bright & low_sat
    labels, _ = ndimage.label(cand)
    border = set(labels[0, :]) | set(labels[-1, :]) | set(labels[:, 0]) | set(labels[:, -1])
    border.discard(0)
    bg = np.isin(labels, list(border))
    a[..., 3] = np.where(bg, 0, 255)
    img = Image.fromarray(a)

    # 2. Cắt sát vật thể
    img = img.crop(img.getbbox())

    # 3. Hạ kích thước (BOX làm mịn trước), rồi ép về bảng màu nhỏ
    h = round(img.height * target_w / img.width)
    img = img.resize((target_w, h), Image.BOX)
    alpha = img.getchannel("A").point(lambda v: 255 if v > 128 else 0)
    q = img.convert("RGB").quantize(colors=colors, method=Image.MEDIANCUT, dither=Image.NONE)
    out = q.convert("RGBA")
    out.putalpha(alpha)
    out.save(dst)
    print(f"{dst}: {out.size}")

if __name__ == "__main__":
    convert(sys.argv[1], sys.argv[2],
            int(sys.argv[3]) if len(sys.argv) > 3 else 128)