# -*- coding: utf-8 -*-
"""下载全部插图到 images/，生成 img_map.json。
用法: python download_imgs.py [pages.json=pages.json]
"""
import json, os, hashlib, subprocess, sys

PAGES = sys.argv[1] if len(sys.argv) > 1 else "pages.json"
units = json.load(open(PAGES, encoding="utf-8"))
urls = sorted({h for u in units for _,_,_,h in u["imgs"]})
os.makedirs("images", exist_ok=True)

mapping = {}
ok = fail = 0
for url in urls:
    # 保留原始扩展名，默认 jpg
    ext = os.path.splitext(url.split("?")[0])[1].lower()
    if ext not in (".jpg", ".jpeg", ".png", ".webp", ".gif"): ext = ".jpg"
    name = hashlib.md5(url.encode()).hexdigest()[:16] + ext
    path = os.path.join("images", name)
    mapping[url] = "images/" + name
    if os.path.exists(path) and os.path.getsize(path) > 0:
        ok += 1; continue
    subprocess.run(["curl","-s","-L","--max-time","40","-o",path,
                    "-H","Referer: https://www.dedao.cn/", url], capture_output=True)
    if os.path.exists(path) and os.path.getsize(path) > 1000:
        ok += 1
    else:
        fail += 1; print("FAIL:", url)

json.dump(mapping, open("img_map.json","w",encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"插图 {len(urls)} 张，成功 {ok}，失败 {fail}")
sys.exit(1 if fail else 0)
