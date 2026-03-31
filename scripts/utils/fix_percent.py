import os

THESIS_PATH = "/Users/delete/Desktop/rag_system_副本/thesis/thesis.tex"

def fix_percent():
    with open(THESIS_PATH, "rb") as f:
        data = f.read()

    # Fix: "0% 深度" -> "0\\% 深度", "50% 深度" -> "50\\% 深度", "95% 深度" -> "95\\% 深度"
    # Also fix "100% 召回" -> "100\\% 召回"
    # And "Top 2% 头部" -> "Top 2\\% 头部", "2% 尾部" -> "2\\% 尾部"
    
    replacements = [
        ("0% 深度".encode('utf-8'), "0\\% 深度".encode('utf-8')),
        ("50% 深度".encode('utf-8'), "50\\% 深度".encode('utf-8')),
        ("95% 深度".encode('utf-8'), "95\\% 深度".encode('utf-8')),
        ("100% 召回".encode('utf-8'), "100\\% 召回".encode('utf-8')),
        ("Top 2% 头部".encode('utf-8'), "Top 2\\% 头部".encode('utf-8')),
        ("2% 尾部".encode('utf-8'), "2\\% 尾部".encode('utf-8')),
        ("全深度 100% 召回".encode('utf-8'), "全深度 100\\% 召回".encode('utf-8')),
    ]
    
    count = 0
    for old, new in replacements:
        if old in data:
            data = data.replace(old, new)
            count += 1
    
    with open(THESIS_PATH, "wb") as f:
        f.write(data)
    
    print(f"Fixed {count} bare percent signs.")

if __name__ == "__main__":
    fix_percent()
