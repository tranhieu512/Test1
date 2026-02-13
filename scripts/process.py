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

# ----------------- Cấu hình nguồn và đích -----------------
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
    processed_lines = []
    channels_in_group = []
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        lines = response.text.splitlines()
    except Exception as e: #test
        print(f"❌ Lỗi khi tải {url}: {e}")
        return [], []

   
      
    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # 1. Bỏ qua các dòng không phải #EXTINF
        if line.startswith('#EXTINF') and re.search(filter_regex, line):
            
            # Loại trừ kênh
            if exclude_regex and re.search(exclude_regex, line): # Nếu có Regex loại trừ và kênh khớp với nó, thì bỏ qua kênh này
                i += 1
                continue 
        
            
            # processed_lines.append(line + '\n') # Thêm dòng EXTINF đã xử lý

        # 1. Trich xuat du lieu cho JSON
            tvg_id = re.search(r'tvg-id="([^"]*)"',line)
            tvg_logo = re.search(r'tvg-logo="([^"]*)"', line)
            name_match = re.search(r',([^,]+)$', line)
            channel_name = name_match.group(1).strip() if name_match else "Unknown"
        # 2. Chuẩn hóa dong EXTINF cho file Text
            line = re.sub(r'group-title="[^"]*"', f'group-title="{new_group_title}"', line)
            temp_channel_lines = [line +'\n'] 
            
            
        # 3. Logic new: Tìm kiếm URL thực 
            j = i + 1
            url_found = False
            while j < len(lines):
                next_line = lines[j].strip()
                if not next_line:
                    # Bỏ qua dòng trống
                    j+=1
                    continue
                
                # a) Nếu gặp EXTINF mới, dừng tìm URL 
                if next_line.startswith('#EXTINF'):
                    break
                    
                # b) Nếu tìm thấy URL hợp lệ (không trống và không bắt đầu bằng '#')
                if not next_line.startswith('#'): 
                    temp_channel_lines.append(next_line + '\n')
                    # Luu vao danh sach JSON
                    channels_in_group.append({
                        "id": tvg_id.group(1) if tvg_id else channel_name,
                        "name": channel_name,
                        "title": channel_name,
                        "image": {
                            "url": tvg_logo.group(1) if tvg_logo else "",
                            "display": "contain"
                        },
                        
                        "url": next_line,
                        "link": next_line
                    })
                    url_found = True
                    i = j
                    break
                else: 
                    temp_channel_lines.append(next_line + '\n')
                j += 1
            if url_found:
                    processed_lines.extend(temp_channel_lines) # Thêm URL
            
        i += 1

    return processed_lines, channels_in_group
# ----------------- Thực thi chính -----------------
if __name__ == "__main__":
    # 1. XỬ LÝ CÁC NGUỒN ĐỘNG (Thực hiện trước)
    for url, regex_keep, regex_exclude, group_name in SOURCES:
        channel_list, channels_json = fetch_and_process(url, regex_keep, regex_exclude, group_name)
        ALL_M3U_LINES.extend(channel_list)
    # 2. THÊM KÊNH CỐ ĐỊNH (Thực hiện sau, ở cuối danh sách)
    #print(f"\n✅ Đang thêm {len(STATIC_CHANNELS) // 2} kênh cố định vào cuối danh sách...")
    
    # ❗️ Đảm bảo dòng này thẳng hàng với các dòng xử lý chính khác
    #temp_static_content = [line + '\n' for line in STATIC_CHANNELS] 
    #ALL_M3U_LINES.extend(temp_static_content)
        if channels_json:
            ALL_GROUPS_JSON.append({
                "id": group_name.lower().replace("", "_"),
                "name": group_name,
                "channels": channels_json
            })
        
    # 3. Xóa các dòng trắng thừa
    final_text_content = [line for line in ALL_M3U_LINES if line.strip()]

    # 4. Chuyển list các dòng thành một chuỗi duy nhất để dễ dàng xử lý
    #content_string = "".join(final_content)

    # 5. Ghi ra file MIN.m3u # Đã ẩn
    #try:
    #    with open(FINAL_OUTPUT_FILE, 'w', encoding='utf-8') as f:
    #        f.write(content_string)
    #    print(f"\n✅ Tổng hợp thành công {len(final_content)} dòng vào {FINAL_OUTPUT_FILE}")
    #except Exception as e:
    #    print(f"❌ Lỗi khi ghi file: {e}")
    
    # 6. Tạo nội dung cho file MIN.txt
    #text_content_string = content_string
    
    # 7. Ghi ra file MIN.txt
    try:
        with open(FINAL_TEXT_FILE, 'w', encoding='utf-8') as f:
            f.writelines(final_text_content)
        print(f"\n✅ Tổng hợp thành công: {FINAL_TEXT_FILE}")
    except Exception as e:
        print(f"❌ Lỗi khi ghi file TXT: {e}")
    # 8. Xuat file JSON
    try:
        mon_data = {
            "id": "MOON LIST",
            "name": "List",
            "groups": ALL_GROUPS_JSON
        }
        with open(FINAL_JSON_FILE, 'w', encoding='utf-8') as f:
            json.dump(mon_data, f, ensure_ascii=False, indent=4)
        print(f"✅ Tổng hợp thành công JSON: {FINAL_JSON_FILE}")
    except Exception as e:
        print(f"❌ Lỗi khi ghi file JSON: {e}")
