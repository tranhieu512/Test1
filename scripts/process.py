import requests
import re
import os
import json
from datetime import datetime

# ------------------Cấu hình EPG-------------
# Định nghĩa các nguồn EPG
EPG_TVG_URLS = [
    "https://vnepg.site/epg.xml",
    "https://lichphatsong.site/schedule/epg.xml.gz",
]
# Nối các URL và phân tách bằng dấu (;)
EPG_URL_STRING=";".join(EPG_TVG_URLS)

# ----------------- Cấu hình nguồn và -----------------
# Định nghĩa các nguồn cần tải, kèm theo Regex lọc (nếu cần) và Tên Nhóm Chuẩn hóa
SOURCES = [
    # (URL, Regex lọc (giữ lại), Regex loại trừ, Tên nhóm chuẩn hóa mới)
    ("https://raw.githubusercontent.com/tranhieu512/Test1/refs/heads/main/min1", 
     r'"HOẠT HÌNH"',
     None, # <--Không loại trừ
     "HOẠT HÌNH"),
    
     
    ("https://raw.githubusercontent.com/vuminhthanh12/vuminhthanh12/refs/heads/main/vmttv", 
     r'"LIVE EVENTS 🔴"',
     None, # <--Không loại trừ
     "LIVE EVENTS"),
    
]

FINAL_TEXT_FILE = "min"
FINAL_JSON_FILE = "min.json" # xuat file json
ALL_M3U_LINES = [f"#EXTM3U url-tvg=\"{EPG_URL_STRING}\"\n"] # Dòng header đầu tiên
ALL_GROUPS_JSON = [] # danh sach chua du lieu cho JSON

def fetch_and_process(url, filter_regex, exclude_regex, new_group_title):
    """Tải file M3U, lọc kênh, lại trừ kênh và chuẩn hóa cho ca Text va JSON."""
    print(f"--- Đang xử lý nguồn: {url}")
    processed_text_lines = []
    channels_in_group = []
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        raw_lines = response.text.splitlines()
    except Exception as e: #test
        print(f"❌ Lỗi khi tải {url}: {e}")
        return [], []
         
    i = 0
    while i < len(raw_lines):
        current_line = raw_lines[i].strip()

        # 1. Bỏ qua các dòng không phải #EXTINF
        if line.startswith('#EXTINF') and re.search(filter_regex, current_line):
            
            # Loại trừ kênh
            if exclude_regex and re.search(exclude_regex, current_line): # Nếu có Regex loại trừ và kênh khớp với nó, thì bỏ qua kênh này
                i += 1
                continue 
        
            
         # 1. Trich xuat du lieu cho JSON
            tvg_id = re.search(r'tvg-id="([^"]*)"',current_line)
            tvg_logo = re.search(r'tvg-logo="([^"]*)"', current_line)
            name_match = re.search(r',([^,]+)$', current_line)
            channel_name = name_match.group(1).strip() if name_match else "Unknown"
        # 2. Chuẩn hóa dong EXTINF cho file Text
            clean_line = re.sub(r'group-title="[^"]*"', f'group-title="{new_group_title}"', current_line)
            
            temp_channel_lines = [clean_line +'\n'] 
            
            
        # 3. Logic new: Tìm kiếm URL thực 
            j = i + 1
            url_found = False
            while j < len(raw_lines):
                next_l = raw_lines[j].strip()
                if not next_l:
                    # Bỏ qua dòng trống
                    j+=1
                    continue
                
                # a) Nếu gặp EXTINF mới, dừng tìm URL 
                if next_l.startswith('#EXTINF'):
                    break
                    
                # b) Nếu tìm thấy URL hợp lệ (không trống và không bắt đầu bằng '#')
                if not next_l.startswith('#'): 
                    temp_lines.append(next_l + '\n')
                    # Luu vao danh sach JSON
                    channels_for_json.append({
                        "id": tvg_id.group(1) if tvg_id else channel_name.lower().replace("","_"),
                        "name": channel_name,
                        "image": {
                            "url": tvg_logo.group(1) if (tvg_logo and tvg_logo.group(1)) else "https://xem.hoiquan.click/HoiQuan_Mini.png",
                            "display": "contain"
                        },
                        
                        "url": next_l,
                        
                    })
                    url_found = True
                    i = j
                    break
                else: 
                    temp_lines.append(next_l + '\n')
                j += 1
            if url_found:
                    processed_text_lines.extend(temp_lines) # Thêm URL
            
        i += 1

    return processed_text_lines, channels_for_json
# ----------------- Thực thi chính -----------------
if __name__ == "__main__":
    
    # 1. XỬ LÝ CÁC NGUỒN ĐỘNG (Thực hiện trước)
    for url, regex_keep, regex_exclude, group_name in SOURCES:
        text_data, json_data = fetch_and_process(url, regex_keep, regex_exclude, group_name)
        ALL_M3U_LINES.extend(text_data)
    
        if json_data:
            ALL_GROUPS_JSON.append({
                "id": group_name.lower().replace("", "_"),
                "name": group_name,
                "channels": json_data
            })
        
    #  Xóa các dòng trắng thừa
    #final_text_content = [line for line in ALL_M3U_LINES if line.strip()]

     
    # 7. Ghi ra file MIN.txt
    try:
        final_text = [l for l in ALL_M3U_LINES if l.strip()]
        with open(FINAL_TEXT_FILE, 'w', encoding='utf-8') as f:
            f.writelines(final_text)
        print(f"\n✅ Tổng hợp thành công: {FINAL_TEXT_FILE}")
    except Exception as e:
        print(f"❌ Lỗi khi ghi file TXT: {e}")
    # 8. Xuat file JSON
    try:
        mon_data = {
            "id": "MOON LIST",
            "name": "List",
            "color": "#FF6B35",
            "image": {
                "display": "contain",
                "url": "https://xem.hoiquan.click/HoiQuan_Mini.png"
            },
            "groups": ALL_GROUPS_JSON
        }
        with open(FINAL_JSON_FILE, 'w', encoding='utf-8') as f:
            json.dump(mon_data, f, ensure_ascii=False, indent=4)
        print(f"✅ Tổng hợp thành công JSON: {FINAL_JSON_FILE}")
    except Exception as e:
        print(f"❌ Lỗi khi ghi file JSON: {e}")
