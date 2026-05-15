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
        print("未找到 Inno Setup，创建自解压安装包...")
        return create_self_extracting_installer()

def create_self_extracting_installer():
    script = '''@echo off
title AutoTap 2.0.0 安装程序
echo ============================================
echo        AutoTap v2.0.0 安装程序
echo ============================================
echo.
set "INSTALL_DIR=%ProgramFiles%\\AutoTap"
set /p "INSTALL_DIR=请输入安装目录 (默认: %ProgramFiles%\\AutoTap): "
if "%INSTALL_DIR%"=="" set "INSTALL_DIR=%ProgramFiles%\\AutoTap"
echo.
echo 正在安装到: %INSTALL_DIR%
echo.

if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"

echo 正在解压文件...
powershell -Command "Expand-Archive -Path '%~dp0AutoTap.zip' -DestinationPath '%INSTALL_DIR%\\..' -Force"

echo.
echo 正在创建快捷方式...
powershell -Command "$ws = New-Object -ComObject WScript.Shell; $sc = $ws.CreateShortcut([Environment]::GetFolderPath('Desktop') + '\\AutoTap.lnk'); $sc.TargetPath = '%INSTALL_DIR%\\AutoTap.exe'; $sc.WorkingDirectory = '%INSTALL_DIR%'; $sc.Save()"

powershell -Command "$ws = New-Object -ComObject WScript.Shell; $sc = $ws.CreateShortcut([Environment]::GetFolderPath('CommonStartMenu') + '\\Programs\\AutoTap.lnk'); $sc.TargetPath = '%INSTALL_DIR%\\AutoTap.exe'; $sc.WorkingDirectory = '%INSTALL_DIR%'; $sc.Save()"

echo.
echo ============================================
echo        安装完成!
echo ============================================
echo.
echo 桌面快捷方式已创建
echo.
choice /C YN /M "是否立即启动 AutoTap"
if %ERRORLEVEL%==1 start "" "%INSTALL_DIR%\\AutoTap.exe"
exit
'''
    zip_path = OUTPUT_ZIP
    if not os.path.exists(zip_path):
        print("错误: 便携版 ZIP 不存在")
        return False

    temp_dir = tempfile.mkdtemp()
    try:
        bat_path = os.path.join(temp_dir, "install.bat")
        with open(bat_path, 'w', encoding='gbk') as f:
            f.write(script)

        zip_dest = os.path.join(temp_dir, "AutoTap.zip")
        shutil.copy2(zip_path, zip_dest)

        sfx_path = OUTPUT_INSTALLER
        with zipfile.ZipFile(sfx_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
            zf.write(bat_path, "install.bat")
            zf.write(zip_dest, "AutoTap.zip")

        bat_name = os.path.basename(bat_path)
        with open(sfx_path, 'ab') as f:
            pass

        size_mb = os.path.getsize(sfx_path) / (1024 * 1024)
        print(f"自解压安装包已创建: {sfx_path} ({size_mb:.1f} MB)")
        print("注意: 此安装包为ZIP格式，解压后运行 install.bat 即可安装")
        return True
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == "__main__":
    if not create_portable_zip():
        sys.exit(1)
    if not create_installer():
        sys.exit(1)
    print("\n所有包已生成完毕!")
