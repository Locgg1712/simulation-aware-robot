import sys
from pathlib import Path
import numpy as np
from PIL import Image
from scipy import ndimage as ndi

SRC = sys.argv[1]
OUT = Path(sys.argv[2]); OUT.mkdir(parents=True, exist_ok=True)

# (ytop, ybot, [(name, center_x, fixed(x0,x1) or None), ...])
ROWS = [
 (0, 209, [("house_farm",91),("house_blue",258),("house_town",400),("house_manor",569),
           ("house_barn",761),("house_coop",908),("house_shed",1025),("shop_pierre",1153),
           ("saloon",1295),("greenhouse",1442)]),
 (232, 429, [("silo",66),("windmill",183),("jojamart",341),("fishpond",511),("tree_oak",665),
             ("tree_pine",805),("tree_cherry",943),("bush_green",1078),("bush_berry",1188),
             ("stump",1310),("log",1442)]),
 (452, 566, [("flower_set",83,(10,157)),("crops_set",257,(160,356)),("rock_set",420,(358,482)),
             ("fence_set",590,(485,697)),("crate",743),("barrel",820),("lamp_post",890),
             ("bench",973),("signpost",1061),("mailbox",1141),("well",1229),("well_roof",1312),
             ("scarecrow",1393),("sprinkler",1479)]),
 (590, 707, [("bridge_wood",72),("bridge_stone",197),("red_mat",335),("robot_down",492),
             ("robot_up",592),("robot_left",687),("robot_right",782),("robot_collision",886),
             ("npc_brown",989),("npc_blonde",1079),("npc_purple",1172),("npc_old",1259),
             ("npc_red",1343),("npc_green",1414),("npc_black",1487)]),
 (732, 842, [("agv_front",58),("agv_side",155),("chicken",253),("cow",347),("pig",452),
             ("cat",533),("sheep",619),("door_closed",735),("door_opening",850),
             ("door_open",965),("door_closing",1077),("furn_bookshelf",1205),
             ("furn_fireplace",1337),("furn_bed",1453)]),
 (868, 985, [("furn_table",82),("furn_plant",203),("furn_rug",330),("furn_window",465),
             ("furn_counter",604),("floor_wood",745),("wallpaper",871),
             ("ui_panel",1021,(940,1108)),("ui_button",1210,(1110,1312)),
             ("ui_icons",1423,(1322,1528))]),
]

im = np.array(Image.open(SRC).convert("RGB"))
H, W, _ = im.shape
saved = []
for ytop, ybot, items in ROWS:
    n = len(items)
    for i, it in enumerate(items):
        name, cx = it[0], it[1]
        fixed = it[2] if len(it) > 2 else None
        if fixed:
            x0, x1 = fixed
        else:
            if i == 0: x0 = 0
            else:
                p = items[i-1]
                x0 = p[2][1] if len(p) > 2 else (p[1] + cx)//2
            if i == n-1: x1 = W
            else:
                nx = items[i+1]
                x1 = nx[2][0] if len(nx) > 2 else (nx[1] + cx)//2
        crop = im[ytop:ybot, x0:x1].astype(int)
        sat = crop.max(axis=2) - crop.min(axis=2)
        cand = (crop.min(axis=2) > 225) & (sat < 30)       # nền trắng
        lab, _ = ndi.label(cand)
        border = set(lab[0,:]) | set(lab[-1,:]) | set(lab[:,0]) | set(lab[:,-1]); border.discard(0)
        bg = np.isin(lab, list(border))
        fg = ~bg
        fg = ndi.binary_opening(fg, iterations=1)
        # gọt viền trắng/xám nhạt bám quanh sprite (tàn dư của nền)
        light = (crop.min(axis=2) > 190) & (sat < 45)
        for _ in range(3):
            edge = fg & ~ndi.binary_erosion(fg)
            fg = fg & ~(edge & light)
        # chỉ giữ thành phần lớn (bỏ mảnh vụn của sprite bên cạnh)
        l2, k = ndi.label(ndi.binary_dilation(fg, iterations=3))
        sizes = [(((l2 == j) & fg).sum(), j) for j in range(1, k+1)]
        biggest = max(sizes)[0] if sizes else 0
        thr = 0.12 * biggest if name.endswith("_set") or name.startswith("ui_") else 0.5 * biggest
        keep = np.zeros_like(fg)
        for a, j in sizes:
            if a >= max(40, thr): keep |= (l2 == j) & fg
        if not keep.any(): print("EMPTY", name); continue
        rgba = np.dstack([crop.astype(np.uint8), (keep*255).astype(np.uint8)])
        ys, xs = np.where(keep)
        out = Image.fromarray(rgba[ys.min():ys.max()+1, xs.min():xs.max()+1], "RGBA")
        out.save(OUT / f"{name}.png"); saved.append((name, out.size))
for n, s in saved: print(f"{n:18s} {s}")
print(len(saved), "files")
