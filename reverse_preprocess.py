import os
import argparse
import re

def save_step(content, folder, filename):
    path = os.path.join(folder, filename)
    with open(path, "w") as f:
        f.write(content)
    print(f"[+] Step saved: {path}")

def restore_main_function(content, output_folder):
    restored = content.replace("entry_point", "main")
    save_step(restored, output_folder, "step1_restored_main.c")
    return restored

def restore_string_literals(content, output_folder):
    restored = re.sub(r'"STR"', '"restored_string"', content)
    save_step(restored, output_folder, "step2_restored_strings.c")
    return restored

def insert_dummy_io(content, output_folder):
    """
    Inserts dummy scanf and printf lines after 'int var;' or before 'return 0;'.
    If 'int var;' not found, it will insert before return statement.
    """
    lines = content.splitlines()
    restored_lines = []
    inserted = False

    for line in lines:
        restored_lines.append(line)
        if not inserted:
            if re.search(r'\bint\s+var\s*;', line):
                restored_lines.append('    scanf("%d", &var);')
                restored_lines.append('    printf("value = %d\\n", var);')
                inserted = True

    # fallback: if not inserted above, inject before return 0;
    if not inserted:
        final_lines = []
        for line in restored_lines:
            if re.match(r'\s*return\s+0\s*;', line):
                final_lines.append('    int var;')
                final_lines.append('    scanf("%d", &var);')
                final_lines.append('    printf("value = %d\\n", var);')
            final_lines.append(line)
        restored = "\n".join(final_lines)
    else:
        restored = "\n".join(restored_lines)

    save_step(restored, output_folder, "step3_dummy_io.c")
    return restored

def reverse_preprocess(input_file, output_folder):
    print(f"\n[*] Reversing file: {input_file}")
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
        print(f"[+] Created output folder: {output_folder}")

    with open(input_file, "r") as f:
        content = f.read()
    print(f"[+] Original file read ({len(content)} bytes)")

    # Step-by-step restoration
    content = restore_main_function(content, output_folder)
    content = restore_string_literals(content, output_folder)
    content = insert_dummy_io(content, output_folder)

    # Final output file
    final_output_path = os.path.join(output_folder, "restored_main.c")
    with open(final_output_path, "w") as f:
        f.write(content)

    print(f"[✓] Final restored file saved to: {final_output_path}\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Verbose Reverse Preprocessor for Xilinx-compatible C code")
    parser.add_argument("-input_file", required=True, help="Path to the preprocessed C file (e.g., main_flat.c)")
    parser.add_argument("-output_folder", required=True, help="Folder to save the restored code")
    args = parser.parse_args()

    reverse_preprocess(args.input_file, args.output_folder)
