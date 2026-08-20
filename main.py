import os
import json

# 整合版 HTML 樣板：去按鈕、選單連動、加入微軟正黑體
HTML_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Trade</title>
    <style>
        body {{
            font-family: "Microsoft JhengHei", "Helvetica Neue", Arial, sans-serif;
            background-color: #f0f7f4;
            margin: 0;
            padding: 20px;
            padding-top: 80px;
        }}
        .navbar {{
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            background-color: #e2ede7;
            padding: 12px 20px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            z-index: 1000;
            box-sizing: border-box;
            display: flex;
            align-items: center;
            gap: 15px;
            flex-wrap: wrap;
        }}
        .nav-group {{
            display: flex;
            align-items: center;
            gap: 5px;
        }}
        .navbar label {{
            font-weight: bold;
            font-size: 14px;
        }}
        .navbar select {{
            padding: 6px;
            font-size: 16px;
            border: 1px solid #b2cfc0;
            border-radius: 4px;
            background-color: #fff;
            min-width: 120px;
        }}
        .content-wrapper {{
            width: 100%;
            max-width: 100%;
            margin: 0 auto;
        }}
        h2 {{
            font-size: 2em;
            font-weight: bold;
            margin-top: 10px;
            scroll-margin-top: 90px;
        }}
        img {{
            width: 100%;
            height: auto;
            display: block;
        }}
        hr {{
            border: 1px solid #eee;
            margin: 40px 0;
        }}
    </style>
</head>
<body>

    <div class="navbar">
        <div class="nav-group">
            <label for="folder-select">商品：</label>
            <select id="folder-select" onchange="onFolderChange()">
{folder_options}
            </select>
        </div>
        <div class="nav-group">
            <label for="date-select">交易日：</label>
            <select id="date-select" onchange="jumpToDate()">
                </select>
        </div>
    </div>

    <div class="content-wrapper" id="content-area">
        </div>

    <script>
        const db = {data_json};

        function onFolderChange() {{
            const folderSelect = document.getElementById('folder-select');
            const dateSelect = document.getElementById('date-select');
            const contentArea = document.getElementById('content-wrapper') || document.getElementById('content-area');
            
            const selectedFolder = folderSelect.value;
            const folderData = db[selectedFolder] || [];
            
            // 1. 更新日期下拉選單 (最新日期排最上面)
            dateSelect.innerHTML = '';
            for (let i = folderData.length - 1; i >= 0; i--) {{
                const dateStr = folderData[i];
                const option = document.createElement('option');
                option.value = dateStr;
                option.textContent = dateStr;
                dateSelect.appendChild(option);
            }}
            
            // 2. 更新下方圖片主體內容
            let bodyHtml = '';
            for (let i = 0; i < folderData.length; i++) {{
                const dateStr = folderData[i];
                bodyHtml += `    <h2 id="${{dateStr}}">${{dateStr}}</h2>\\n`;
                bodyHtml += `    <img src="./${{selectedFolder}}/${{dateStr}}.png" alt="${{dateStr}}">\\n`;
                
                if (i < folderData.length - 1) {{
                    bodyHtml += '    <hr>\\n';
                }}
            }}
            contentArea.innerHTML = bodyHtml;
            
            // 3. 預設選取最新日期，並確認圖片載入完成後精準定位
            if (folderData.length > 0) {{
                const newestDate = folderData[folderData.length - 1];
                dateSelect.value = newestDate;
                
                // 尋找最後一張圖片（最新日期）
                const newestImg = document.querySelector(`img[alt="${{newestDate}}"]`);
                if (newestImg) {{
                    if (newestImg.complete) {{
                        jumpToDate();
                    }} else {{
                        newestImg.onload = function() {{
                            jumpToDate();
                        }};
                    }}
                }} else {{
                    jumpToDate();
                }}
            }} else {{
                window.scrollTo(0, 0);
            }}
        }}

        function jumpToDate() {{
            const selectedDate = document.getElementById('date-select').value;
            if (!selectedDate) return;
            
            const targetEl = document.getElementById(selectedDate);
            if (targetEl) {{
                targetEl.scrollIntoView({{ behavior: 'smooth' }});
            }}
        }}

        window.onload = function() {{
            onFolderChange();
        }};
    </script>
</body>
</html>"""

def main():
    target_folders = ["ES - 實盤", "ES - 復盤", "TXF - 實盤", "TXF - 復盤", "ES", "TXF"]
    all_data = {}
    folder_options_list = []

    print("開始讀取資料夾圖片...")
    
    for folder in target_folders:
        folder_path = f"./{folder}"
        
        if not os.path.exists(folder_path) or not os.path.isdir(folder_path):
            print(f"提示：未找到資料夾 '{folder_path}'，跳過。")
            continue
            
        try:
            files = [f for f in os.listdir(folder_path) if f.lower().endswith('.png')]
            files.sort()
            
            dates = [os.path.splitext(f)[0] for f in files]
            
            if dates:
                all_data[folder] = dates
                folder_options_list.append(f'            <option value="{folder}">{folder}</option>')
                print(f"-> 已載入 {folder} 資料夾 (共 {len(dates)} 張圖片)")
            else:
                print(f"提示：'{folder_path}' 中沒有任何 .png 檔案。")
                
        except Exception as e:
            print(f"讀取資料夾 {folder} 失敗: {e}")

    if not all_data:
        print("錯誤：沒有載入任何有效的商品資料夾與圖片，停止生成。")
        return

    folder_options = "\n".join(folder_options_list)
    data_json = json.dumps(all_data, ensure_ascii=False)

    final_html = HTML_TEMPLATE.format(
        folder_options=folder_options,
        data_json=data_json
    )
    
    output_path = "./index.html"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(final_html)

    print(f"\n全部處理完成！已成功生成直覺跳轉網頁：{output_path}")

if __name__ == "__main__":
    main()