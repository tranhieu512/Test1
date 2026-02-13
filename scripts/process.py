import requests
import re
import json
import os

# ------------------Cấu hình EPG-------------
EPG_TVG_URLS = [
    "https://vnepg.site/epg.xml",
    "https://lichphatsong.site/schedule/epg.xml.gz",
]
EPG_URL_STRING=";".join(EPG_TVG_URLS)

# ----------------- Cấu hình nguồn -----------------
SOURCES = [
    ("https://raw.githubusercontent.com/tranhieu512/Test1/refs/heads/main/min1", r'"HOẠT HÌNH"', None, "HOẠT HÌNH"),
    ("https://raw.githubusercontent.com/vuminhthanh12/vuminhthanh12/refs/heads/main/vmttv", r'"LIVE EVENTS 🔴"', None, "LIVE EVENTS"),
]

FINAL_TEXT_FILE = "min"
FINAL_JSON_FILE = "min.json"

def fetch_and_process(url, filter_regex, exclude_regex, new_group_title):
    print(f"--- Đang xử lý nguồn: {url}")
    processed_text_lines = []
    channels_for_json = []
    
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        raw_lines = response.text.splitlines()
    except Exception as e:
        print(f"❌ Lỗi khi tải {url}: {e}")
        return [], [] 

    i = 0
    while i < len(raw_lines):
        current_line = raw_lines[i].strip()

        # Kiểm tra dòng #EXTINF
        if current_line.startswith('#EXTINF') and re.search(filter_regex, current_line):
            if exclude_regex and re.search(exclude_regex, current_line):
                i += 1
                continue
            
            # --- KHỞI TẠO BIẾN NGAY TẠI ĐÂY ---
            clean_line = re.sub(r'group-title="[^"]*"', f'group-title="{new_group_title}"', current_line)
            temp_lines = [clean_line + '\n'] 
            
            # Trích xuất thông tin
            name_match = re.search(r',([^,]+)$', current_line)
            channel_name = name_match.group(1).strip() if name_match else "Unknown"
            tvg_id_match = re.search(r'tvg-id="([^"]*)"', current_line)
            tvg_logo_match = re.search(r'tvg-logo="([^"]*)"', current_line)
            
            j = i + 1
            url_found = False
            
            # Tìm URL phía sau dòng #EXTINF
            while j < len(raw_lines):
                next_l = raw_lines[j].strip()
                if not next_l:
                    j += 1
                    continue
                if next_l.startswith('#EXTINF'):
                    break
                
                # Bất kể là dòng gì (URL hay tag phụ), đều thêm vào temp_lines
                temp_lines.append(next_l + '\n')
                
                # Nếu không bắt đầu bằng #, đây chính là URL stream
                if not next_l.startswith('#'):
                    channels_for_json.append({
                        "id": tvg_id_match.group(1) if (tvg_id_match and tvg_id_match.group(1)) else channel_name.lower().replace(" ", "_"),
                        "name": channel_name,
                        "image": {
                            "url": tvg_logo_match.group(1) if (tvg_logo_match and tvg_logo_match.group(1)) else "https://xem.hoiquan.click/HoiQuan_Mini.png",
                            "display": "contain"
                        },
                        "url": next_l
                    })
                    url_found = True
                    i = j # Nhảy chỉ số i đến dòng URL
                    break
                j += 1
            
            if url_found:
                processed_text_lines.extend(temp_lines)
        
        i += 1
    
    return processed_text_lines, channels_for_json

if __name__ == "__main__":
    ALL_M3U_LINES = [f"#EXTM3U url-tvg=\"{EPG_URL_STRING}\"\n"]
    ALL_GROUPS_JSON = [] 

    for url, filter_reg, exclude_reg, g_name in SOURCES:
        t_data, j_data = fetch_and_process(url, filter_reg, exclude_reg, g_name)
        ALL_M3U_LINES.extend(t_data)
        
        if j_data:
            ALL_GROUPS_JSON.append({
                "id": g_name.lower().replace(" ", "_"),
                "name": g_name,
                "channels": j_data
            })
        
    # Ghi file TEXT (M3U)
    try:
        with open(FINAL_TEXT_FILE, 'w', encoding='utf-8') as f:
            f.writelines([l for l in ALL_M3U_LINES if l.strip()])
        print(f"✅ Đã lưu file TEXT: {FINAL_TEXT_FILE}")
    except Exception as e:
        print(f"❌ Lỗi ghi file TEXT: {e}")
    
    # Ghi file JSON (Đúng định dạng Monplayer yêu cầu)
    try:
        mon_data = {
            "id": "MyPlaylist",
            "name": "DANH SÁCH TỔNG HỢP",
            "color": "#FF6B35",
            "image": {
                "display": "contain",
                "url": "https://xem.hoiquan.click/HoiQuan_Mini.png"
            },
            "groups": ALL_GROUPS_JSON
        }
        with open(FINAL_JSON_FILE, 'w', encoding='utf-8') as f:
            json.dump(mon_data, f, ensure_ascii=False, indent=4)
        print(f"✅ Đã lưu file JSON chuẩn Monplayer!")
    except Exception as e:
        print(f"❌ Lỗi ghi file JSON: {e}")
