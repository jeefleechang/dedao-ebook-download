# dedao-ebook-download

通过得到（Dedao）会员权益，将**本人有权阅读**的电子书保存为本地 HTML/PDF，用于个人离线阅读与长期留存。

> ⚠️ 使用前请先阅读 [`DISCLAIMER.md`](./DISCLAIMER.md)。
> 本工具仅限**个人已购或会员权益内**内容的离线归档，**禁止传播、分享、转售或商业使用**。

## 原理

得到网页阅读器以 SVG 分页渲染、无官方下载接口，且服务端返回加密 blob。本工具复用本机已登录浏览器会话，通过 CDP 逐页翻页，从渲染后的 SVG DOM 中按坐标重建文字与图片，再合成 HTML / PDF。

## 仓库结构

```
.
├── SKILL.md            # 完整流程说明（Hermes Skill 格式）
├── DISCLAIMER.md       # 免责声明与使用边界
├── LICENSE             # MIT（仅覆盖本仓库代码，不含任何电子书内容）
└── scripts/
    ├── fetch_book.py      # CDP 逐页抓取文字 + 图片
    ├── download_imgs.py  # 下载图片并生成映射
    ├── build_html.py     # 合成 HTML
    └── make_pdf.py       # CDP 打印 PDF
```

## 快速开始

完整步骤、环境准备与坑位见 [`SKILL.md`](./SKILL.md)。简要：

```bash
python -m venv .venv
./.venv/Scripts/python.exe -m pip install playwright pymupdf

# 1) 副本配置启动 Edge 并开 9222（见 SKILL.md）
# 2) 抓取
./.venv/Scripts/python.exe scripts/fetch_book.py "<reader-url>" pages2.json
# 3) 下图
./.venv/Scripts/python.exe scripts/download_imgs.py pages2.json
# 4) 生成 HTML
./.venv/Scripts/python.exe scripts/build_html.py pages2.json
# 5) 生成 PDF
./.venv/Scripts/python.exe scripts/make_pdf.py "<book>.html" "<book>.pdf"
```

## 平台

- Windows 10/11（git-bash）、Edge 浏览器。

## 许可

代码采用 [MIT](./LICENSE)。电子书内容著作权归原权利人所有，本仓库不含任何受版权保护的书籍正文。
