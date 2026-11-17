"""掃描各交易紀錄資料夾中的 PNG 圖片，生成單頁瀏覽網站 index.html。"""

from __future__ import annotations

import json
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "index.html"

# 要放進網站的資料夾（依下拉選單順序）
FOLDERS = ("ES - 實盤", "ES - 復盤", "TXF - 實盤", "TXF - 復盤")

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
DATA_PLACEHOLDER = "__TRADE_DATA__"


def png_size(path: Path) -> tuple[int, int] | None:
    """從 PNG 檔頭 (IHDR) 讀取寬高，讓網頁預留圖片空間、避免版面跳動。"""
    with path.open("rb") as f:
        header = f.read(24)
    if len(header) < 24 or header[:8] != PNG_SIGNATURE or header[12:16] != b"IHDR":
        return None
    return struct.unpack(">II", header[16:24])


def scan_folder(folder: Path) -> list[dict]:
    """回傳資料夾內所有 PNG（依檔名排序，即日期由舊到新）。"""
    entries = []
    for image in sorted(folder.glob("*.png")):
        entry: dict = {"name": image.stem}
        if size := png_size(image):
            entry["width"], entry["height"] = size
        entries.append(entry)
    return entries


def to_json(data: dict[str, list[dict]]) -> str:
    """每張圖一行，新增圖片時 git diff 只會多一行。"""
    blocks = []
    for folder, entries in data.items():
        rows = ",\n".join(f"      {json.dumps(e, ensure_ascii=False)}" for e in entries)
        blocks.append(f"    {json.dumps(folder, ensure_ascii=False)}: [\n{rows}\n    ]")
    # 避免資料中出現 "</script>" 提前結束 script 區塊
    return ("{\n" + ",\n".join(blocks) + "\n  }").replace("</", "<\\/")


def main() -> int:
    data: dict[str, list[dict]] = {}

    for name in FOLDERS:
        folder = ROOT / name
        if not folder.is_dir():
            print(f"略過：找不到資料夾「{name}」")
            continue
        entries = scan_folder(folder)
        if not entries:
            print(f"略過：「{name}」中沒有 .png 檔案")
            continue
        data[name] = entries
        print(f"已載入「{name}」：{len(entries)} 張圖片")

    if not data:
        print("錯誤：沒有任何可用的圖片，未生成網頁。", file=sys.stderr)
        return 1

    html = HTML_TEMPLATE.replace(DATA_PLACEHOLDER, to_json(data))
    OUTPUT.write_text(html, encoding="utf-8")
    print(f"完成：已生成 {OUTPUT.relative_to(ROOT)}")
    return 0


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-Hant">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Trade</title>
  <style>
    :root {
      --bg: #f0f7f4;
      --nav-bg: #e2ede7;
      --border: #b2cfc0;
      --divider: #eee;
      --header-offset: 80px; /* 由 JS 依導覽列實際高度更新 */
    }

    *, *::before, *::after { box-sizing: border-box; }

    html { scroll-padding-top: var(--header-offset); }

    body {
      margin: 0;
      font-family: "Microsoft JhengHei", "Helvetica Neue", Arial, sans-serif;
      background-color: var(--bg);
    }

    .navbar {
      position: sticky;
      top: 0;
      z-index: 10;
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 10px 15px;
      padding: 12px 20px;
      background-color: var(--nav-bg);
      box-shadow: 0 2px 5px rgb(0 0 0 / 10%);
    }

    .nav-group {
      display: flex;
      align-items: center;
      gap: 5px;
    }

    .nav-group label {
      font-size: 14px;
      font-weight: bold;
    }

    .nav-group select {
      min-width: 120px;
      padding: 6px;
      font: inherit;
      font-size: 16px;
      border: 1px solid var(--border);
      border-radius: 4px;
      background-color: #fff;
    }

    main { padding: 0 20px 20px; }

    .entry h2 {
      margin: 10px 0 0.83em;
      font-size: 2em;
    }

    .entry img {
      display: block;
      width: 100%;
      height: auto;
    }

    hr {
      margin: 40px 0;
      border: 1px solid var(--divider);
    }
  </style>
</head>
<body>
  <header class="navbar">
    <div class="nav-group">
      <label for="folder-select">商品：</label>
      <select id="folder-select"></select>
    </div>
    <div class="nav-group">
      <label for="date-select">交易日：</label>
      <select id="date-select"></select>
    </div>
  </header>

  <main id="content"></main>

  <script type="application/json" id="trade-data">
  __TRADE_DATA__
  </script>

  <script>
    "use strict";

    const data = JSON.parse(document.getElementById("trade-data").textContent);
    const header = document.querySelector(".navbar");
    const folderSelect = document.getElementById("folder-select");
    const dateSelect = document.getElementById("date-select");
    const content = document.getElementById("content");
    const reduceMotion = matchMedia("(prefers-reduced-motion: reduce)");

    /** 目前商品中「檔名 -> section 元素」的對照 */
    let sections = new Map();

    // 導覽列高度會因換行而改變，同步給 scroll-padding-top
    const syncHeaderOffset = () =>
      document.documentElement.style.setProperty("--header-offset", `${header.offsetHeight + 20}px`);
    syncHeaderOffset();
    new ResizeObserver(syncHeaderOffset).observe(header);

    // 目前選擇記在網址 hash，重新整理或分享連結時可回到同一張
    const readHash = () => Object.fromEntries(new URLSearchParams(location.hash.slice(1)));
    const writeHash = (folder, date) =>
      history.replaceState(null, "", `#${new URLSearchParams({ folder, date })}`);

    const imageUrl = (folder, name) =>
      `${encodeURIComponent(folder)}/${encodeURIComponent(name)}.png`;

    function renderFolder(folder) {
      const entries = data[folder] ?? [];
      const fragment = document.createDocumentFragment();
      sections = new Map();

      entries.forEach(({ name, width, height }, i) => {
        if (i > 0) fragment.append(document.createElement("hr"));

        const section = document.createElement("section");
        section.className = "entry";

        const title = document.createElement("h2");
        title.textContent = name;

        const img = document.createElement("img");
        img.loading = "lazy"; // 須在設定 src 之前
        img.decoding = "async";
        img.alt = name;
        if (width && height) {
          img.width = width;
          img.height = height;
        }
        img.src = imageUrl(folder, name);

        section.append(title, img);
        fragment.append(section);
        sections.set(name, section);
      });

      content.replaceChildren(fragment);

      // 日期選單：最新的排最上面
      dateSelect.replaceChildren(
        ...[...entries].reverse().map(({ name }) => new Option(name, name))
      );
    }

    function scrollToDate(date, { smooth = false } = {}) {
      sections.get(date)?.scrollIntoView({
        behavior: smooth && !reduceMotion.matches ? "smooth" : "auto",
      });
    }

    function selectFolder(folder, date) {
      folderSelect.value = folder;
      renderFolder(folder);

      const target = sections.has(date) ? date : dateSelect.options[0]?.value;
      if (!target) {
        scrollTo(0, 0);
        return;
      }
      dateSelect.value = target;
      writeHash(folder, target);
      scrollToDate(target);
    }

    folderSelect.replaceChildren(...Object.keys(data).map((name) => new Option(name, name)));

    folderSelect.addEventListener("change", () => selectFolder(folderSelect.value));
    dateSelect.addEventListener("change", () => {
      writeHash(folderSelect.value, dateSelect.value);
      scrollToDate(dateSelect.value, { smooth: true });
    });

    history.scrollRestoration = "manual";
    const initial = readHash();
    selectFolder(
      Object.hasOwn(data, initial.folder ?? "") ? initial.folder : Object.keys(data)[0],
      initial.date
    );
  </script>
</body>
</html>
"""


if __name__ == "__main__":
    sys.exit(main())
