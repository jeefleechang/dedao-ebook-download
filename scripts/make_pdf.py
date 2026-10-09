# -*- coding: utf-8 -*-
"""把电子书 HTML 用 Edge CDP 打印为 PDF。
用法: python make_pdf.py <html_path> [pdf_path]
前置: Edge 带 --remote-debugging-port=9222 运行中。
"""
import os, base64, sys
from playwright.sync_api import sync_playwright

HTML_PATH = os.path.abspath(sys.argv[1] if len(sys.argv)>1 else sys.exit("需要 html_path"))
PDF_PATH = sys.argv[2] if len(sys.argv)>2 else os.path.splitext(os.path.basename(HTML_PATH))[0]+".pdf"

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
    ctx = browser.contexts[0]
    page = ctx.new_page()
    page.goto("file:///" + HTML_PATH.replace("\\","/"), wait_until="networkidle")

    ready = page.evaluate("""() => {
        const imgs=[...document.querySelectorAll('img')];
        return imgs.every(i=>i.complete&&i.naturalWidth>0) ? imgs.length : 0;
    }""")
    print("已加载图片数:", ready)
    page.evaluate("""async()=>{for(let y=0;y<document.body.scrollHeight;y+=700){window.scrollTo(0,y);await new Promise(r=>setTimeout(r,30));}window.scrollTo(0,0);}""")

    client = ctx.new_cdp_session(page)
    result = client.send("Page.printToPDF", {
        "printBackground": True,
        "paperWidth": 8.27, "paperHeight": 11.69,
        "marginTop": 0.7, "marginBottom": 0.7,
        "marginLeft": 0.65, "marginRight": 0.65,
        "displayHeaderFooter": False,
        "preferCSSPageSize": False,
        "scale": 1.0,
    })
    open(PDF_PATH,"wb").write(base64.b64decode(result["data"]))
    print("PDF生成:", PDF_PATH, round(os.path.getsize(PDF_PATH)/1e6,2),"MB")
    browser.close()
