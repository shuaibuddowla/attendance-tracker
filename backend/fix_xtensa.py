import zipfile
import os
import sys

zip_path = "C:/Users/USER/AppData/Local/Arduino15/staging/packages/xtensa-esp-elf-14.2.0_20260121-x86_64-w64-mingw32.zip"
target_dir = "C:/Users/USER/AppData/Local/Arduino15/packages/esp32/tools/esp-x32/2601"

print(f"Opening {zip_path}...")
with zipfile.ZipFile(zip_path, 'r') as z:
    total = len(z.infolist())
    print(f"Extracting {total} files to {target_dir}...")
    for idx, member in enumerate(z.infolist()):
        # Strip leading 'xtensa-esp-elf/'
        orig_name = member.filename
        if orig_name.startswith("xtensa-esp-elf/"):
            rel_name = orig_name[len("xtensa-esp-elf/"):]
        else:
            rel_name = orig_name
        
        if not rel_name:
            continue
            
        dest_path = os.path.join(target_dir, rel_name.replace('/', os.sep))
        if member.is_dir():
            os.makedirs(dest_path, exist_ok=True)
        else:
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            with z.open(member) as src, open(dest_path, 'wb') as dst:
                dst.write(src.read())
        
        if idx % 1000 == 0 or idx == total - 1:
            print(f"Progress: {idx}/{total} ({int(idx/total*100)}%)")

print("Finished extracting xtensa-esp-elf toolchain!")
