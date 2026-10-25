"""
Tách bộ sprite Nhà & Xưởng Robot (`robot_house .png`) thành các file PNG nền trong suốt (RGBA).
Dựa trên pipeline tách nền + gọt viền sáng của `split_sheet.py` & `split_chars.py`.
"""
import sys
from pathlib import Path
import numpy as np
from PIL import Image
from scipy import ndimage as ndi

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SRC = PROJECT_ROOT / "sprites" / "sprites" / "robot_house" / "robot_house .png"
OUT_SUBDIR = PROJECT_ROOT / "sprites" / "sprites" / "robot_house"
OUT_MAIN = PROJECT_ROOT / "sprites" / "sprites"

# Danh sách (name, x0, y0, x1, y1) khớp chính xác từng thành phần trong robot_house .png (1536x1024)
ITEMS = [
    # Hàng 1-2: Ngôi nhà ngoại thất & Bộ sàn / tường công nghiệp
    ("house_robot",        14,   12,  750,  506),
    ("rh_floor_tile",     784,  110,  972,  276),
    ("rh_hazard_mat",     982,  110, 1103,  281),
    ("rh_exit_mat",      1113,  110, 1257,  279),
    ("rh_charging_dock", 1274,  109, 1458,  284),
    ("rh_wall_vent",      782,  300,  916,  474),
    ("rh_wall_screen",    926,  300, 1045,  475),
    ("rh_wall_arch",     1059,  300, 1199,  475),
    ("rh_wall_doors",    1213,  300, 1460,  476),

    # Hàng 3: Kệ phụ tùng, Trạm cánh tay Robot nâng cấp, bàn kỹ thuật
    ("rh_crate_top",       26,  537,  127,  635),
    ("rh_crate_mid",       26,  640,  127,  745),
    ("rh_shelf_parts",    144,  522,  278,  743),
    ("rh_shelf_wide",     291,  523,  495,  743),
    ("rh_shelf_narrow",   517,  523,  599,  742),
    ("rh_upgrade_station",651,  498,  849,  751),
    ("rh_tool_cabinet",   867,  566,  965,  703),
    ("rh_workbench_green",982,  550, 1130,  704),
    ("rh_computer_desk", 1145,  551, 1324,  715),
    ("rh_diag_table",    1333,  619, 1514,  726),

    # Hàng 4: Bàn tròn bản vẽ, máy chủ, bảng trắng, trạm điều khiển
    ("rh_chair_blue",      33,  762,  102,  870),
    ("rh_stool_1",        133,  767,  194,  828),
    ("rh_stool_2",        133,  829,  194,  895),
    ("rh_round_table",    221,  757,  403,  907),
    ("rh_plant_small",    422,  757,  492,  833),
    ("rh_stool_3",        422,  834,  492,  905),
    ("rh_battery_box",    515,  784,  574,  849),
    ("rh_crate_single",   600,  762,  669,  854),
    ("rh_terminal",       693,  762,  807,  871),
    ("rh_chair_blue2",    835,  758,  908,  869),
    ("rh_solder_station", 936,  770, 1073,  874),
    ("rh_server_1",      1092,  751, 1156,  872),
    ("rh_server_2",      1162,  751, 1227,  872),
    ("rh_whiteboard",    1263,  748, 1492,  874),

    # Hàng 5: Đạo cụ xưởng, bình chữa cháy, cọc tiêu, dàn lạnh
    ("rh_crate_low",       29,  906,  108,  997),
    ("rh_crate_open",     128,  908,  285, 1000),
    ("rh_barrel_blue1",   301,  911,  362, 1000),
    ("rh_barrel_blue2",   403,  908,  466, 1000),
    ("rh_plant_tall",     490,  862,  587, 1000),
    ("rh_crate_tall",     600,  860,  669, 1000),
    ("rh_cone",           688,  904,  759,  996),
    ("rh_bollard",        775,  890,  830, 1000),
    ("rh_sensor_post",    845,  874,  889,  996),
    ("rh_extinguisher",   911,  896,  966,  997),
    ("rh_bin",            993,  896, 1054, 1000),
    ("rh_cooling_unit",  1078,  881, 1200, 1000),
    ("rh_shutter_wide",  1220,  885, 1497, 1000),
]


def extract_all(src_path: Path):
    OUT_SUBDIR.mkdir(parents=True, exist_ok=True)
    OUT_MAIN.mkdir(parents=True, exist_ok=True)
    im = np.array(Image.open(src_path).convert("RGB"))
    saved = []

    for name, x0, y0, x1, y1 in ITEMS:
        crop = im[y0:y1, x0:x1].astype(int)
        sat = crop.max(axis=2) - crop.min(axis=2)
        cand = (crop.min(axis=2) > 225) & (sat < 30)  # nền trắng
        lab, _ = ndi.label(cand)
        border = set(lab[0, :]) | set(lab[-1, :]) | set(lab[:, 0]) | set(lab[:, -1])
        border.discard(0)
        bg = np.isin(lab, list(border))
        fg = ~bg
        fg = ndi.binary_opening(fg, iterations=1)

        # Gọt viền trắng/xám nhạt bám quanh sprite
        light = (crop.min(axis=2) > 195) & (sat < 42)
        for _ in range(3):
            edge = fg & ~ndi.binary_erosion(fg)
            fg = fg & ~(edge & light)

        # Giữ thành phần chính
        l2, k = ndi.label(ndi.binary_dilation(fg, iterations=3))
        sizes = [(((l2 == j) & fg).sum(), j) for j in range(1, k + 1)]
        biggest = max(sizes)[0] if sizes else 0
        thr = 0.08 * biggest
        keep = np.zeros_like(fg)
        for a, j in sizes:
            if a >= max(30, thr):
                keep |= (l2 == j) & fg
        if not keep.any():
            print("EMPTY:", name)
            continue

        rgba = np.dstack([crop.astype(np.uint8), (keep * 255).astype(np.uint8)])
        ys, xs = np.where(keep)
        out = Image.fromarray(rgba[ys.min():ys.max() + 1, xs.min():xs.max() + 1], "RGBA")
        out.save(OUT_SUBDIR / f"{name}.png")
        out.save(OUT_MAIN / f"{name}.png")
        saved.append((name, out.size))

    for n, s in saved:
        print(f"{n:20s} {s}")
    print(f"Extracted {len(saved)} sprites successfully.")


if __name__ == "__main__":
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_SRC
    extract_all(src)

