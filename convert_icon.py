"""
将SVG图标转换为Windows ICO格式
支持多种尺寸以确保在不同场景下显示清晰
"""

import cairosvg
from PIL import Image
import os

def convert_svg_to_ico(svg_path, ico_path, sizes=[256, 128, 64, 48, 32, 16]):
    """
    将SVG文件转换为ICO格式
    
    Args:
        svg_path: SVG文件路径
        ico_path: 输出ICO文件路径
        sizes: 需要生成的图标尺寸列表
    """
    print(f"正在转换图标: {svg_path}")
    
    # 检查SVG文件是否存在
    if not os.path.exists(svg_path):
        print(f"错误: 找不到SVG文件 {svg_path}")
        return False
    
    images = []
    
    # 为每个尺寸生成PNG图像
    for size in sizes:
        print(f"  生成 {size}x{size} 尺寸...")
        
        # 使用cairosvg将SVG转换为PNG数据
        png_data = cairosvg.svg2png(
            url=svg_path,
            output_width=size,
            output_height=size
        )
        
        # 使用PIL打开PNG数据
        from io import BytesIO
        img = Image.open(BytesIO(png_data))
        
        # 添加到图像列表
        images.append(img)
    
    # 保存为ICO格式(包含所有尺寸)
    print(f"正在保存ICO文件: {ico_path}")
    images[0].save(
        ico_path,
        format='ICO',
        sizes=[(img.width, img.height) for img in images],
        append_images=images[1:]
    )
    
    print(f"✓ 图标转换完成: {ico_path}")
    return True

if __name__ == "__main__":
    # 设置文件路径
    svg_file = "icon.svg"
    ico_file = "icon.ico"
    
    # 执行转换
    success = convert_svg_to_ico(svg_file, ico_file)
    
    if success:
        print("\n✓ 成功! 现在可以在PyInstaller中使用icon.ico作为应用图标")
    else:
        print("\n✗ 转换失败")
