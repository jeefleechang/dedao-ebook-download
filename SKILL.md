---
name: dedao-ebook-download
description: "Use when saving a Dedao (得到) ebook locally via CDP to HTML/PDF for personal long-term offline retention."
version: 1.1.0
author: jeefleechang
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [dedao, ebook, cdp, playwright, pdf, scrape, personal-archive]
---

# 通过得到会员权益将电子书保存到本地长期留存

> 适用范围：仅限你**本人已购买**或在**得到会员有效权益内**有权阅读的电子书。
> 本工具用于个人离线归档与长期留存，不用于传播、分享、转售或任何商业用途。
> 使用即表示你已知悉并同意根目录 `DISCLAIMER.md` 中的免责声明。

## 一、原理

得到电子书网页阅读器（`dedao.cn/ebook/reader?id=...`）采用 **SVG 分页渲染，无官方下载入口**：

- 服务端接口 `get_pages` 返回的是**加密 SVG blob**，无法直接还原文字；
- 阅读器在本地解密后，**DOM 中是明文**。

因此可行路线是：**复用本机已登录的浏览器会话 → 通过 CDP 自动逐页翻页 →
从渲染后的 SVG DOM 按坐标重建文字与插图 → 合成 HTML → 用 CDP `printToPDF` 生成 PDF**，
实现本地长期留存。

已验证：
- 《本体驱动的AI数据管理》：302 页 / 109 张图 / 293 页 PDF；
- 《智能：AI时代的商业、组织与战略的本质》：纯文字书（仅注释图标）/ 138 页 PDF。

## 二、使用边界（务必遵守）

- 只抓你本人**已购买**或**会员权益内**的内容；
- 仅供**个人离线阅读与归档**；
- **不要**上传抓取到的书籍正文到任何公开位置；
- **不要**分享、转售、二次传播，或用于绕过付费墙、批量爬取。

## 三、关键事实（先读，省踩坑）

1. **登录态**：本机 Edge 已登录。新版 Edge/Chrome（≥136）在**默认配置文件**上
   禁止开启 `--remote-debugging-port`（端口静默不监听），必须用**配置副本**目录启动
   （Cookie 为 Windows DPAPI 加密，同一用户可解密）。
2. **Cookie 文件锁**：Edge 运行时 `User Data/Default/Network/Cookies` 被独占，
   必须先关闭 Edge，再复制 `Local State` + `Default/Preferences`
   + `Default/Network/Cookies*` 到副本目录。
3. **正文文字 = SVG `<text>` 逐字定位**：需按 y 分行、行内按 x 排序重建；
   `innerText` 会逐字换行，`textContent` 含 `@font-face` 垃圾，均不能直接使用。
4. **正文插图 = SVG `<image>`**：可直接用 curl 下载（加
   `Referer: https://www.dedao.cn/`）。**不要限定 umiwi 域名**，以免漏掉
   `igetget.com` 等域名的真插图；只排除 `data:`/`blob:` 内联 URL。
5. **「注」字注释入口图标**：按**渲染尺寸**判定（≤40px 为内联小图标），
   **不要写死 URL**——不同书的图标 URL 不同，写死会被误判为正文插图。
6. **双栏模式**：一次方向键翻 2 页；视口内有两页（几何 x≈30 / x≈897，随窗口布局变化），
   DOM 还有前后缓冲页与镜像副本，须按几何位置 + 内容指纹去重。
7. **`loading="lazy"` 在 `file://` 下不加载图片**，HTML 中不要使用懒加载。

## 四、环境准备（一次性）

```bash
# 在工作目录建立独立 venv（装进 Hermes 主 venv 会被 PYTHONPATH 干扰）
mkdir -p /e/ailearn/dedao_dl && cd /e/ailearn/dedao_dl
python -m venv .venv
./.venv/Scripts/python.exe -m pip install playwright pymupdf
```

Windows 下 terminal 为 git-bash，使用 POSIX 语法；`taskkill` 需
`MSYS_NO_PATHCONV=1 taskkill /IM msedge.exe /F`（否则 `/IM` 被当成路径）。

## 五、执行流程

### 1. 关闭 Edge → 复制配置 → 副本启动并开调试端口

```bash
MSYS_NO_PATHCONV=1 taskkill /IM msedge.exe /F ; sleep 2
SRC="$HOME/AppData/Local/Microsoft/Edge/User Data"
DST="./edge_profile"
rm -rf "$DST"; mkdir -p "$DST/Default/Network"
cp "$SRC/Local State" "$DST/"
cp "$SRC/Default/Preferences" "$DST/Default/"
cp "$SRC/Default/Network/Cookies" "$SRC/Default/Network/Cookies-journal" "$DST/Default/Network/" 2>/dev/null
```

后台启动（注意 Edge 路径是 `Program Files (x86)`）：

```bash
MSYS_NO_PATHCONV=1 "/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe" \
  --remote-debugging-port=9222 \
  --user-data-dir="<工作目录绝对路径>\edge_profile" \
  --profile-directory=Default --no-first-run \
  "<reader URL>"
```

健康检查：`curl -s http://127.0.0.1:9222/json/version` 返回 Browser 信息。

### 2. 逐页抓取（文字 + 插图）

```bash
./.venv/Scripts/python.exe scripts/fetch_book.py "<reader URL>" pages2.json
```

脚本：连 CDP → 点阅读器中央聚焦 → 连续 `ArrowLeft` 回首页 → 逐屏 `ArrowRight`，
每屏抓取视口两页的 `<text>`（y,x,ch）与 `<image>`（y,w,h,href），
按「前几行文字 + 首图 URL」指纹去重，存 `pages2.json`。

**完成判据**：进度到 `N/N`，单元数 ≈ 页数（纯图扉页会让单元数略多）。
页根只按几何 x 匹配 + width>800 认定，**不要**设「text 节点 >30」门槛，
否则章节扉页会整页丢失。

### 3. 下载插图

```bash
./.venv/Scripts/python.exe scripts/download_imgs.py pages2.json
```

从 `pages2.json` 收集去重 URL，curl（带 Referer）存到 `images/`，
生成 `img_map.json`。**完成判据**：成功数 == URL 数，失败 0，每张 >1KB。

### 4. 合成 HTML

```bash
./.venv/Scripts/python.exe scripts/build_html.py pages2.json
```

按页内 y 坐标把图插到正确位置；行跨行拼接（行尾无终止标点则与下行合并）；识别：

- 章标题 `CHAPTER N` / `第N章` → h1；
- 小节 `N.N.N中文…`（≤30 字）→ h3；
- `❑` / `N.` 开头短行 → li；
- 渲染尺寸 ≤40px 的小图 → 内联注释图标（非 figure）；
- 插图后紧跟 `图N-N…` 行 → figcaption。

**坑**：中文含标点字符串 `.isupper()` 恒为 True，判断大写标题必须只对拉丁字母判断。

### 5. 转 PDF

```bash
./.venv/Scripts/python.exe scripts/make_pdf.py "<生成的.html>" "<输出.pdf>"
```

等待所有 `<img>` `complete && naturalWidth>0`，滚动触发渲染，用 CDP
`Page.printToPDF`（A4，printBackground，margin≈0.7in）输出。
**完成判据**：文件为有效 PDF，pymupdf 可打开、页数合理，首页与含图页目视无乱码/裁切。

## 六、常见坑（Common Pitfalls）

1. 直接对默认 Edge 配置开 9222 → 端口不监听，必须副本目录。
2. 没关 Edge 就复制 Cookies → `Device or resource busy`，先 taskkill。
3. Edge 路径写成 `x88` → 进程秒退，核对 `Program Files (x86)`。
4. 直接用 innerText/textContent → 逐字换行或含 @font-face 垃圾，按坐标重建。
5. 页根加文字数门槛 → 章节扉页/封面丢失，只按几何位置认定。
6. 中文行用 `.isupper()` → 大量误判标题，仅对拉丁字母判定大写。
7. HTML 用 `loading="lazy"` → file:// 下图全裂，删除懒加载。
8. 注释图标靠写死 URL → 换书即误判，按渲染尺寸判定。
9. 插图 URL 限定 umiwi 域名 → 漏掉其它域名真插图，只排除 data:/blob:。
10. 抓太快 → 拿到占位状态，翻页间隔 ≥0.5s 并按指纹去重。
11. 移动 HTML 不带 images/ → 图全裂，连带文件夹或改单文件 base64 HTML。

## 七、验收清单（Verification Checklist）

- [ ] `curl http://127.0.0.1:9222/json/version` 正常（副本配置）
- [ ] `pages2.json` 单元数 ≈ 全书页数，去重插图数与全书规模吻合
- [ ] images/ 全部下载成功（失败 0、每张 >1KB）
- [ ] HTML 章节骨架完整、无重复 figure、无文字断裂/乱码，所有图片 `naturalWidth>0`
- [ ] 若转 PDF：pymupdf 可打开、页数合理，首页与含图页目视通过
- [ ] 已确认：仅限个人离线归档，未上传/传播任何书籍正文
