import os
import sys
import shutil
import zipfile
import subprocess

ROOT = os.path.dirname(os.path.abspath(__file__))
DIST_DIR = os.path.join(ROOT, "dist", "AutoTap")
OUTPUT_ZIP = os.path.join(ROOT, "dist", "AutoTap_2.0.0_Portable.zip")
OUTPUT_INSTALLER = os.path.join(ROOT, "dist", "AutoTap_2.0.0_Setup.exe")

ISCC_PATHS = [
    os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Inno Setup 6", "ISCC.exe"),
    r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
    r"C:\Program Files\Inno Setup 6\ISCC.exe",
]


def create_portable_zip():
    if not os.path.exists(DIST_DIR):
        print(f"错误: {DIST_DIR} 不存在，请先运行 pyinstaller")
        return False

    print("正在创建便携版 ZIP 包...")
    with zipfile.ZipFile(OUTPUT_ZIP, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for root, dirs, files in os.walk(DIST_DIR):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, os.path.dirname(DIST_DIR))
                zf.write(file_path, arcname)
    size_mb = os.path.getsize(OUTPUT_ZIP) / (1024 * 1024)
    print(f"便携版已创建: {OUTPUT_ZIP} ({size_mb:.1f} MB)")
    return True


def create_installer():
    iscc = None
    for p in ISCC_PATHS:
        if os.path.exists(p):
            iscc = p
            break

    if not iscc:
        print("错误: 未找到 Inno Setup 6，请先安装: https://jrsoftware.org/isdl.php")
        return False

    print(f"找到 Inno Setup: {iscc}")
    iss_file = os.path.join(ROOT, "installer.iss")
    result = subprocess.run([iscc, iss_file], capture_output=True, encoding='utf-8', errors='replace')
    if result.returncode == 0:
        size_mb = os.path.getsize(OUTPUT_INSTALLER) / (1024 * 1024)
        print(f"安装包已创建: {OUTPUT_INSTALLER} ({size_mb:.1f} MB)")
        return True
    else:
        print(f"Inno Setup 编译失败:\n{result.stderr}")
        return False


if __name__ == "__main__":
    if not create_portable_zip():
        sys.exit(1)
    if not create_installer():
        sys.exit(1)
    print("\n所有包已生成完毕!")
