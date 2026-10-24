import sys, json
from pathlib import Path
import numpy as np
from PIL import Image
from scipy import ndimage as ndi

UP = Path('/mnt/user-data/uploads')
OUT = Path('/mnt/user-data/outputs/sprites')

def remove_labels(rgb):
    r, g, b = rgb[..., 0].astype(int), rgb[..., 1].astype(int), rgb[..., 2].astype(int)
    brown = (r > 55) & (r < 120) & (g > 15) & (g < 70) & (b < 45) & (r > g + 25)
    lab, n = ndi.label(ndi.binary_closing(brown, iterations=2))
    out = rgb.copy(); boxes = []
    for i, sl in enumerate(ndi.find_objects(lab), 1):
        h = sl[0].stop - sl[0].start; w = sl[1].stop - sl[1].start
        fill = (lab[sl] == i).sum() / (h * w)
        if w >= 70 and 26 <= h <= 70 and fill > 0.40:
            out[max(0, sl[0].start-4):sl[0].stop+4, max(0, sl[1].start-4):sl[1].stop+4] = 255
            boxes.append((sl[1].start, sl[0].start, w, h))
    return out, boxes

def foreground(rgb):
    c = rgb.astype(int); sat = c.max(2) - c.min(2)
    cand = (c.min(2) > 225) & (sat < 30)
    lab, _ = ndi.label(cand)
    border = set(lab[0]) | set(lab[-1]) | set(lab[:, 0]) | set(lab[:, -1]); border.discard(0)
    fg = ~np.isin(lab, list(border))
    fg = ndi.binary_opening(fg, iterations=1)
    return fg, c, sat

def clean_edges(fg, c, sat):
    light = (c.min(2) > 190) & (sat < 45)
    shadow = (c.min(2) > 150) & (c.max(2) < 232) & (sat < 38)
    for _ in range(3):
        edge = fg & ~ndi.binary_erosion(fg); fg = fg & ~(edge & light)
    for _ in range(8):
        edge = fg & ~ndi.binary_erosion(fg); fg = fg & ~(edge & shadow)
    return fg

def components(fg, dil):
    lab, n = ndi.label(ndi.binary_dilation(fg, iterations=dil))
    comps = []
    for i, sl in enumerate(ndi.find_objects(lab), 1):
        m = (lab == i) & fg
        if m.sum() < 60: continue
        ys, xs = np.where(m)
        comps.append(dict(mask=m, x0=xs.min(), x1=xs.max()+1, y0=ys.min(), y1=ys.max()+1))
    return comps

def save_comp(rgb, comp, path):
    m = comp['mask'][comp['y0']:comp['y1'], comp['x0']:comp['x1']]
    a = rgb[comp['y0']:comp['y1'], comp['x0']:comp['x1']]
    img = Image.fromarray(np.dstack([a, (m * 255).astype(np.uint8)]), 'RGBA')
    path.parent.mkdir(parents=True, exist_ok=True); img.save(path); return img.size

def rows_by_counts(comps, counts):
    comps = sorted(comps, key=lambda k: (k['y0'] + k['y1']) / 2)
    rows, i = [], 0
    for c in counts:
        rows.append(sorted(comps[i:i+c], key=lambda k: k['x0'])); i += c
    return rows

POSES = [["down", "up", "left", "right"], ["pick_up", "put_down", "sit", "sleep"], ["hurt", "die"]]

def do_character(src, name, x0=0, x1=None, dil=14):
    rgb = np.array(Image.open(src).convert('RGB'))[:, x0:x1]
    rgb, boxes = remove_labels(rgb)
    fg, c, sat = foreground(rgb); fg = clean_edges(fg, c, sat)
    comps = components(fg, dil)
    print(f"{name}: labels={len(boxes)} comps={len(comps)}")
    if len(comps) != 10:
        for k in comps: print('   ', k['x0'], k['y0'], k['x1']-k['x0'], k['y1']-k['y0'])
        return False
    for row, names in zip(rows_by_counts(comps, [4, 4, 2]), POSES):
        for comp, pose in zip(row, names):
            save_comp(rgb, comp, OUT / 'characters' / name / f'{pose}.png')
    return True

if __name__ == '__main__':
    CH = [
     ("38614434-33EC-4E3D-BAC9-FCD82F2F3177", "npc_01_orange_boy"),
     ("474EADD0-0713-433C-9480-669C05E93E35", "npc_02_blonde_girl"),
     ("26E5C62C-5E0F-4DF6-B8C2-C9817B67B5BF", "npc_03_purple_hair"),
     ("B4EBF733-D501-4085-AB94-2EE52B7BD1B0", "npc_04_green_hair"),
     ("067DBAD7-9C3B-4045-9C2B-717B71F06333", "npc_05_blue_boy"),
     ("16DE095C-BFB5-43DF-A34D-A271955E2877", "npc_06_farmer_girl"),
     ("9E40F3CD-4E95-4891-913C-D224623B8BD6", "npc_07_old_man"),
     ("EF999BC6-B96D-4E53-BB69-621BE8220799", "npc_08_maid"),
     ("1D6F896C-752E-46E8-8ABD-0B3EE03DFE6A", "npc_09_young_girl"),
     ("76870F0D-AF27-4AB9-82A3-5852403D41FD", "npc_10_cat_boy"),
    ]
    for f, n in CH: do_character(UP / f'{f}.png', n)
    s12 = UP / "3D5D56DB-B995-499A-85A7-3455076A9F24.png"
    do_character(s12, "npc_12_adventurer", 0, 880)
    do_character(s12, "npc_13_scholar", 892, None)
