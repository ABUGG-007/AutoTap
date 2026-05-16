import os
import sys
import shutil
import zipfile
import tempfile
import subprocess

ROOT = os.path.dirname(os.path.abspath(__file__))
DIST_DIR = os.path.join(ROOT, "dist", "AutoTap")
OUTPUT_ZIP = os.path.join(ROOT, "dist", "AutoTap_2.0.0_Portable.zip")
OUTPUT_INSTALLER = os.path.join(ROOT, "dist", "AutoTap_2.0.0_Setup.exe")

SEVEN_ZIP_DIR = r"C:\Program Files\7-Zip"
SEVEN_ZIP_EXE = os.path.join(SEVEN_ZIP_DIR, "7z.exe")
SFX_MODULE = os.path.join(SEVEN_ZIP_DIR, "7z.sfx")


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


def create_sfx_installer():
    if not os.path.exists(SEVEN_ZIP_EXE):
        print(f"错误: 未找到 7-Zip ({SEVEN_ZIP_EXE})")
        return False
    if not os.path.exists(SFX_MODULE):
        print(f"错误: 未找到 7z.sfx 模块 ({SFX_MODULE})")
        return False
    if not os.path.exists(OUTPUT_ZIP):
        print(f"错误: 便携版 ZIP 不存在 ({OUTPUT_ZIP})")
        return False

    config = """;!@Install@!UTF-8!
Title="AutoTap v2.0.0 安装程序"
BeginPrompt="欢迎使用 AutoTap v2.0.0\n\n点击「确定」开始安装"
ExtractPath="%PROGRAMFILES%\\AutoTap"
RunProgram="AutoTap.exe"
;!@InstallEnd@!"""

    temp_dir = tempfile.mkdtemp()
    try:
        sfx_output = OUTPUT_INSTALLER

        with open(os.path.join(temp_dir, "config.txt"), 'w', encoding='utf-8') as f:
            f.write(config)

        with open(sfx_output, 'wb') as out_f:
            with open(SFX_MODULE, 'rb') as sfx_f:
                shutil.copyfileobj(sfx_f, out_f)
            with open(os.path.join(temp_dir, "config.txt"), 'rb') as cfg_f:
                shutil.copyfileobj(cfg_f, out_f)
            with open(OUTPUT_ZIP, 'rb') as zip_f:
                shutil.copyfileobj(zip_f, out_f)

        size_mb = os.path.getsize(sfx_output) / (1024 * 1024)
        print(f"安装包已创建: {sfx_output} ({size_mb:.1f} MB)")
        return True
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def create_inno_installer():
    iscc_paths = [
        r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        r"C:\Program Files\Inno Setup 6\ISCC.exe",
        r"C:\Program Files (x86)\Inno Setup 5\ISCC.exe",
    ]
    iscc = None
    for p in iscc_paths:
        if os.path.exists(p):
            iscc = p
            break

    if iscc:
        print(f"找到 Inno Setup: {iscc}")
        iss_file = os.path.join(ROOT, "installer.iss")
        result = subprocess.run([iscc, iss_file], capture_output=True, text=True)
        if result.returncode == 0:
            print("安装包已创建!")
            return True
        else:
            print(f"Inno Setup 编译失败: {result.stderr}")
            return False
    else:
        print("未找到 Inno Setup，使用 7z SFX 创建安装包...")
        return create_sfx_installer()


if __name__ == "__main__":
    if not create_portable_zip():
        sys.exit(1)
    if not create_inno_installer():
        sys.exit(1)
    print("\n所有包已生成完毕!")
