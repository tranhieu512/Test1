import requests
import re
import os
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
    ("https://raw.githubusercontent.com/vuminhthanh12/vuminhthanh12/refs/heads/main/vmttv", 
     r'"VTV"',
     None, # <--Không loại trừ
     "Nhóm Kênh VTV"),
     
    ("https://raw.githubusercontent.com/tranhieu512/test/refs/heads/main/min1", 
     r'"HTV"',
     None, # <--Không loại trừ
     "Nhóm Kênh HTV/HTVC"),
     
    ("https://raw.githubusercontent.com/vuminhthanh12/vuminhthanh12/refs/heads/main/vmttv", 
     r'"VTVcab"',
     None, # <--Không loại trừ
     "Nhóm Kênh VTVcab"),

    ("https://raw.githubusercontent.com/vuminhthanh12/vuminhthanh12/refs/heads/main/vmttv", 
     r'"SCTV"', # Chỉ giữ SCTV
     None, # <--Không loại trừ 
     "Nhóm Kênh SCTV"),

    ("https://raw.githubusercontent.com/tranhieu512/Test1/refs/heads/main/min1", 
     r'"HOẠT HÌNH"',
     None, # <--Không loại trừ
     "HOẠT HÌNH"),
    
    ("https://raw.githubusercontent.com/tranhieu512/test/refs/heads/main/min1", 
     r'"Kênh thiết yếu"',
     None, # <--Không loại trừ
     "Nhóm Kênh Thiết yếu"),

    ("https://raw.githubusercontent.com/vuminhthanh12/vuminhthanh12/refs/heads/main/vmttv", 
     r'"Quốc Tế"',
     None, # <--Không loại trừ
     "Quốc Tế"),
    
    ("https://raw.githubusercontent.com/vuminhthanh12/vuminhthanh12/refs/heads/main/vmttv", 
     r'"LIVE EVENTS 🔴"',
     None, # <--Không loại trừ
     "LIVE EVENTS"),
    
]

# FINAL_OUTPUT_FILE = "MIN.m3u" # Đã ẩn xuất file m3u
FINAL_TEXT_FILE = "min"
ALL_M3U_LINES = [f"#EXTM3U url-tvg=\"{EPG_URL_STRING}\"\n"] # Dòng header đầu tiên

def fetch_and_process_m3u(url, filter_regex, exclude_regex, new_group_title):
    """Tải file M3U, lọc kênh, lại trừ kênh và chuẩn hóa Group Title."""
    print(f"--- Đang xử lý nguồn: {url}")
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"❌ Lỗi khi tải {url}: {e}")
        return []

    lines = response.text.splitlines()
    processed_lines = []
    
    # Duyệt qua từng dòng để tìm #EXTINF
    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # 1. Bỏ qua các dòng không phải #EXTINF
        if not line.startswith('#EXTINF'):
            i += 1
            continue
            
        # 2. Lọc kênh: Kiểm tra xem dòng EXTINF có khớp với Regex lọc không
        if re.search(filter_regex, line):
            # Loại trừ kênh
            if exclude_regex and re.search(exclude_regex, line): # Nếu có Regex loại trừ và kênh khớp với nó, thì bỏ qua kênh này
                i += 1
                continue # Bỏ qua vòng lặp hiện tại, chuyển sang dòng #EXTINF tiếp theo
        # 3. Chuẩn hóa Group Title
            line = re.sub(r'group-title="[^"]*"', f'group-title="{new_group_title}"', line)
            
            processed_lines.append(line + '\n') # Thêm dòng EXTINF đã xử lý
            
        # 4. Logic new: Tìm kiếm tất cả các dòng va URL thực 
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
                if next_line and not next_line.startswith('#'):
                    processed_lines.append(next_line + '\n') # Thêm URL
                    url_found=True
                    i = j # Bắt đầu tìm kiếm EXTINF tiếp theo từ dòng này 
                    break # Thoát khỏi vòng lặp tìm URL
                
                # c) Nếu là dòng trống hoặc thẻ mở rộng (như #EXTGRP)
                if next_line.startswith('#'):
                    # Thêm dòng thẻ mở rộng vào trước URL
                    processed_lines.append(next_line + '\n')
                j += 1
            
            # Nếu tìm thấy URL, i đã được cập nhật, ta tiếp tục vòng lặp chính 
            # Nếu không tìm thấy URL (vi du: gap EXTINF tiep theo), ta phải cập nhật i
            if not url_found:
                 i = j
        else:
            # Nếu không khớp với bộ lọc, chuyển sang dòng tiếp theo
            i += 1


    return processed_lines
# ----------------- Thực thi chính -----------------
if __name__ == "__main__":
    # 1. XỬ LÝ CÁC NGUỒN ĐỘNG (Thực hiện trước)
    for url, regex_keep, regex_exclude, group in SOURCES:
        channel_list = fetch_and_process_m3u(url, regex_keep, regex_exclude, group)
        ALL_M3U_LINES.extend(channel_list)
    # 2. THÊM KÊNH CỐ ĐỊNH (Thực hiện sau, ở cuối danh sách)
    #print(f"\n✅ Đang thêm {len(STATIC_CHANNELS) // 2} kênh cố định vào cuối danh sách...")
    
    # ❗️ Đảm bảo dòng này thẳng hàng với các dòng xử lý chính khác
    #temp_static_content = [line + '\n' for line in STATIC_CHANNELS] 
    #ALL_M3U_LINES.extend(temp_static_content)
        
    # 3. Xóa các dòng trắng thừa
    final_content = [line for line in ALL_M3U_LINES if line.strip()]

    # 4. Chuyển list các dòng thành một chuỗi duy nhất để dễ dàng xử lý
    content_string = "".join(final_content)

    # 5. Ghi ra file MIN.m3u # Đã ẩn
    #try:
    #    with open(FINAL_OUTPUT_FILE, 'w', encoding='utf-8') as f:
    #        f.write(content_string)
    #    print(f"\n✅ Tổng hợp thành công {len(final_content)} dòng vào {FINAL_OUTPUT_FILE}")
    #except Exception as e:
    #    print(f"❌ Lỗi khi ghi file: {e}")
    
    # 6. Tạo nội dung cho file MIN.txt
    text_content_string = content_string
    
    # 7. Ghi ra file MIN.txt
    try:
        with open(FINAL_TEXT_FILE, 'w', encoding='utf-8') as f:
            f.write(text_content_string)
        print(f"\n✅ Tổng hợp thành công {len(final_content)} dòng vào {FINAL_TEXT_FILE}")
    except Exception as e:
        print(f"❌ Lỗi khi ghi file TXT: {e}")
