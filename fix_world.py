import xml.etree.ElementTree as ET

# ดึงจากไฟล์ต้นฉบับ
file_path = 'src/my_bot/worlds/211.world'
out_path = 'src/my_bot/worlds/211_fixed.world'

print(f"กำลังประมวลผลไฟล์ {file_path} ...")
tree = ET.parse(file_path)
root = tree.getroot()

for world in root.findall('world'):
    models_to_remove = []
    for model in world.findall('model'):
        # 1. ลบโมเดลที่เป็นบันได
        if 'Stair' in model.get('name', ''):
            models_to_remove.append(model)
            continue
            
        links_to_remove = []
        for link in model.findall('link'):
            name = link.get('name', '')
            # 2. ลบลิงก์บันไดที่ซ่อนอยู่ในตึก
            if 'Stair' in name:
                links_to_remove.append(link)
                
        # สั่งลบออกจาก XML
        for link in links_to_remove:
            model.remove(link)
    for model in models_to_remove:
        world.remove(model)

tree.write(out_path, encoding='utf-8', xml_declaration=True)
print(f"✅ ซ่อมโลกเสร็จแล้ว! บันไดหายไป และกำแพงกลับมาบางเท่าเดิม เซฟไฟล์ไว้ที่: {out_path}")
