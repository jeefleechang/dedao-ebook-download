# -*- coding: utf-8 -*-
"""得到电子书逐页抓取：文字行(带y) + 插图(带y)，按视口页去重。
用法: python fetch_book.py <reader_url> [out.json=pages.json]
前置: Edge 已用配置副本 + --remote-debugging-port=9222 打开该 reader_url。
"""
import json, time, re, sys
from playwright.sync_api import sync_playwright

READER_URL = sys.argv[1] if len(sys.argv) > 1 else sys.exit("需要 reader_url")
OUT = sys.argv[2] if len(sys.argv) > 2 else "pages.json"

# 双栏视口两页的几何 x（窗口布局不同可能变化；可用 probe 脚本核对）
PAGE_X = [30, 956]

def progress(page):
    t = page.evaluate("() => document.querySelector('.book-info')?.innerText || ''")
    m = re.search(r'(\d+)\s*/\s*(\d+)', t)
    return (int(m.group(1)), int(m.group(2))) if m else (None, None)

EXTRACT = r"""(xs) => {
    function pageData(tx){
        let root=null;
        document.querySelectorAll('.svg-wrapper *').forEach(el=>{
            const r=el.getBoundingClientRect();
            if(Math.abs(r.x-tx)<45 && r.width>800){
                const n=el.querySelectorAll('tspan,text,image').length;
                if(n>0 && (!root||n<root.n))root={el,n};
            }
        });
        if(!root) return {rows:[],imgs:[]};
        const el=root.el, er=el.getBoundingClientRect();
        const rows=[];
        el.querySelectorAll('text').forEach(t=>{
            const ch=t.textContent; if(!ch)return;
            const r=t.getBoundingClientRect();
            rows.push([Math.round((r.top-er.top)/3)*3, Math.round(r.left-er.left), ch]);
        });
        const imgs=[];
        el.querySelectorAll('image').forEach(im=>{
            const href=im.href.baseVal||im.getAttribute('xlink:href')||im.getAttribute('href')||'';
            if(!href || href.startsWith('data:') || href.startsWith('blob:')) return;
            const r=im.getBoundingClientRect();
            imgs.push([Math.round(r.top-er.top), Math.round(r.width), Math.round(r.height), href]);
        });
        return {rows, imgs};
    }
    return xs.map(pageData);
}"""

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
    ctx = browser.contexts[0]
    page = next((pg for pg in ctx.pages if "dedao.cn/ebook" in pg.url), None) or sys.exit("未找到阅读器标签页")
    box = page.evaluate("() => { const r=document.querySelector('.iget-reader').getBoundingClientRect(); return [r.x+r.width/2,r.y+r.height/2];}")
    page.mouse.click(box[0], box[1]); time.sleep(.5)

    print("回到首页...", flush=True)
    tries=0
    while True:
        cur,_=progress(page)
        if cur is not None and cur<=2: break
        page.keyboard.press("ArrowLeft"); time.sleep(.35); tries+=1
        if tries>400: sys.exit("无法回到首页")
    time.sleep(1)

    units=[]; seen=set(); prev=None; stagnant=0; i=0
    while True:
        cur,total=progress(page)
        pair=page.evaluate(EXTRACT,PAGE_X)
        sig=json.dumps(pair,ensure_ascii=False)
        if sig!=prev:
            for d in pair:
                if not d["rows"] and not d["imgs"]: continue
                head="".join(c for _,_,c in d["rows"][:8])
                if d["imgs"]: head += "#" + d["imgs"][0][3][-20:]
                if head not in seen:
                    seen.add(head); units.append(d)
            prev=sig; stagnant=0
        else: stagnant+=1
        nimg=sum(len(u["imgs"]) for u in units)
        print(f"屏{i} {cur}/{total} 页{len(units)} 图{nimg}",flush=True)
        if cur is not None and total and cur>=total-1:
            time.sleep(.8)
            pair=page.evaluate(EXTRACT,PAGE_X)
            for d in pair:
                head="".join(c for _,_,c in d["rows"][:8])
                if d["imgs"]: head += "#" + d["imgs"][0][3][-20:]
                if head and head not in seen: seen.add(head); units.append(d)
            break
        if stagnant>6: break
        page.keyboard.press("ArrowRight"); time.sleep(.55); i+=1

    json.dump(units,open(OUT,"w",encoding="utf-8"),ensure_ascii=False)
    imgs={h for u in units for _,_,_,h in u["imgs"]}
    print(f"完成 页{len(units)} 去重插图{len(imgs)} -> {OUT}",flush=True)
    browser.close()
