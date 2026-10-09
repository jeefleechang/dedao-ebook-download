# -*- coding: utf-8 -*-
"""合成电子书 HTML：文字 + 本地插图，图片按 y 坐标定位到段落间。
用法: python build_html.py [pages.json] [book_title] [book_author]
书名/作者缺省时从首个含“书名：/作者：”的单元推断。
"""
import json, re, html, sys, os, collections

PAGES = sys.argv[1] if len(sys.argv) > 1 else "pages.json"
units = json.load(open(PAGES, encoding="utf-8"))
img_map = json.load(open("img_map.json", encoding="utf-8"))

END_PUNCT = set("。！？：；…）”’!?:;)%")

def unit_text(u):
    lines = {}
    for y,x,ch in u["rows"]: lines.setdefault(y, []).append((x,ch))
    return "".join("".join(c for _,c in sorted(v)) for y,v in sorted(lines.items()))

# 推断书名/作者
book_title = sys.argv[2] if len(sys.argv) > 2 else "电子书"
book_author = sys.argv[3] if len(sys.argv) > 3 else ""
for u in units:
    t = unit_text(u)
    m = re.search(r'书名[：:]\s*([^\n|]{2,30})', t)
    if m and not book_author: book_title = m.group(1).strip()
    m2 = re.search(r'作者[：:]\s*([^\n|]{2,30})', t)
    if m2: book_author = m2.group(1).strip()
    if book_author: break

def is_chapter(s):
    return bool(re.fullmatch(r'(CHA\s*PTER\s*\d+|CHAPTER\s*\d+)', s)) or \
           bool(re.fullmatch(r'第[0-9一二三四五六七八九十]+章.*', s))
def is_section(s):
    return bool(re.match(r'^\d+\.\d+(\.\d+)*[\u4e00-\u9fa5]', s)) and len(s) <= 30
def is_latin_upper(s):
    L=[c for c in s if c.isalpha()]
    return len(L)>0 and all('A'<=c<='Z' for c in L)

# ---- 重建“行+图”有序流 ----
elements=[]
for u in units:
    lines={}
    for y,x,ch in u["rows"]: lines.setdefault(y, []).append((x,ch))
    line_items=[]
    for y in sorted(lines):
        s=""; lx=None
        for x,ch in sorted(lines[y]):
            if lx is not None and x-lx>22: s+=" "
            s+=ch; lx=x
        s=s.strip()
        if s: line_items.append((y,s))
    merged=[]
    for y,s in line_items: merged.append((y,0,s))
    for iy,iw,ih,href in u["imgs"]:
        local=img_map.get(href)
        if not local: continue
        # 注释/脚注入口图标按【渲染尺寸】判定（≤40px），不要写死 URL：
        # 不同书的注释图标 URL 不同。正文插图尺寸大且 URL 唯一。
        merged.append((iy, 2 if (iw<=40 or ih<=40) else 1, local))
    merged.sort(key=lambda z:(z[0],z[1]))
    for _,kind,payload in merged:
        elements.append((("note" if kind==2 else ("img" if kind==1 else "line")), payload))

# ---- 行 -> 段落/标题/列表 ----
blocks=[]; buf=""
def flush():
    global buf
    if buf: blocks.append(("p",buf)); buf=""
def classify(s):
    if is_chapter(s): return "h1"
    if re.fullmatch(r'第[0-9一二三四五六七八九十]+节.*',s): return "h2"
    if is_section(s): return "h3"
    if s in ("序","前言","推荐阅读","版权信息","COPYRIGHT"): return "h1"
    if is_latin_upper(s) and len(s)<18: return "h1"
    if s.startswith(("❑","▪")): return "li"
    if re.match(r'^\d+[.、]', s) and len(s)<42: return "li"
    return "p"

for kind,payload in elements:
    if kind in ("img","note"):
        flush(); blocks.append((kind,payload)); continue
    k=classify(payload)
    if k in ("h1","h2","h3"):
        flush(); blocks.append((k,payload)); continue
    if k=="li":
        flush(); blocks.append(("li",payload.lstrip("❑▪ ").strip())); continue
    if buf:
        if buf[-1] in END_PUNCT: blocks.append(("p",buf)); buf=payload
        else: buf+=payload
    else: buf=payload
flush()

# ---- 输出 HTML ----
out=[f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(book_title)}</title>
<style>
:root{{--ink:#1f2328;--soft:#57606a;--accent:#9a4a2f;--line:#e6e0d8;--bg:#fbf9f5;}}
*{{box-sizing:border-box;}}
body{{margin:0;background:var(--bg);color:var(--ink);
 font-family:"Source Han Serif SC","Noto Serif CJK SC","Songti SC","SimSun",Georgia,serif;
 line-height:1.95;font-size:18px;}}
.cover{{max-width:820px;margin:0 auto;padding:96px 32px 48px;text-align:center;}}
.cover h1{{font-size:40px;line-height:1.3;margin:0 0 14px;letter-spacing:2px;}}
.cover .author{{color:var(--soft);font-size:18px;}}
.cover .rule{{width:64px;height:3px;background:var(--accent);margin:34px auto;}}
article{{max-width:820px;margin:0 auto;padding:8px 32px 120px;}}
h1.chapter{{font-size:28px;margin:64px 0 18px;padding-top:28px;border-top:2px solid var(--line);
 color:var(--accent);letter-spacing:1px;}}
h2{{font-size:22px;margin:40px 0 12px;}}
h3{{font-size:19px;margin:28px 0 10px;color:#33393f;}}
p{{margin:0 0 18px;text-align:justify;text-indent:2em;}}
ul{{margin:0 0 18px;padding-left:1.4em;}}
li{{margin-bottom:10px;text-align:justify;}}
li::marker{{color:var(--accent);}}
figure{{margin:26px 0;text-align:center;}}
figure img{{max-width:100%;height:auto;border:1px solid var(--line);border-radius:6px;
 box-shadow:0 6px 22px rgba(80,60,40,.10);}}
figcaption{{color:var(--soft);font-size:14px;margin-top:8px;}}
.meta{{color:var(--soft);font-size:14px;text-align:center;margin-top:60px;}}
.note-mark{{text-indent:0;margin:14px 0;}}
.note-mark img{{width:26px;height:26px;vertical-align:middle;opacity:.8;}}
@media print{{body{{background:#fff;}}.cover{{padding-top:40px;}}figure img{{box-shadow:none;}}}}
</style></head><body>
<section class="cover">
 <h1>{html.escape(book_title)}</h1>
 <div class="rule"></div>
 <div class="author">{html.escape(book_author)}</div>
</section>
<article>"""]

n=len(blocks); used=set(); seq=[]; idx=0
while idx<n:
    k,t=blocks[idx]
    if k=="img":
        cap=""
        if idx+1<n and blocks[idx+1][0]=="p" and re.match(r'^图\s*\d+[-–]\d+', blocks[idx+1][1]):
            cap=blocks[idx+1][1]; used.add(idx+1); idx+=1
        seq.append(("figure",t,cap))
    else:
        if idx not in used: seq.append((k,t,None))
    idx+=1

for k,t,c in seq:
    if k=="h1": out.append(f'<h1 class="chapter">{html.escape(t)}</h1>')
    elif k=="h2": out.append(f"<h2>{html.escape(t)}</h2>")
    elif k=="h3": out.append(f"<h3>{html.escape(t)}</h3>")
    elif k=="li": out.append(f"<li>{html.escape(t)}</li>")
    elif k=="figure":
        cap=f"<figcaption>{html.escape(c)}</figcaption>" if c else ""
        out.append(f'<figure><img src="{html.escape(t)}" alt="{html.escape(c or "插图")}">{cap}</figure>')
    elif k=="note":
        out.append(f'<p class="note-mark"><img src="{html.escape(t)}" alt="注释"></p>')
    else: out.append(f"<p>{html.escape(t)}</p>")

text="\n".join(out)
text=re.sub(r'(?:<li>.*?</li>\n?)+', lambda m:'<ul>\n'+m.group(0)+'</ul>\n', text)
text+='\n<div class="meta">仅供个人离线阅读 · 由得到阅读器渲染内容整理</div>\n</article></body></html>'
fname=book_title+".html"
open(fname,"w",encoding="utf-8").write(text)
print(collections.Counter(k for k,_,_ in seq))
print("生成:",fname, round(os.path.getsize(fname)/1024,1),"KB")
