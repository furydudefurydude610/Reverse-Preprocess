import os
import argparse
import re
from collections import defaultdict

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

def infer_variable_types(content):
    """
    Analyzes the code and returns a dict {var_name: type}
    """
    inferred_types = defaultdict(lambda: "int")  # Default to int
    lines = content.splitlines()
    for line in lines:
        # Infer from indexing like string[i]
        if match := re.search(r'(\w+)\s*\[.*?\]', line):
            inferred_types[match.group(1)] = "char *"
        # Infer from pointer usage like (*temptemp1) = ...
        for match in re.finditer(r'\(\*\s*(\w+)\s*\)', line):
            inferred_types[match.group(1)] = "int *"
        # Direct int-like usage
        for match in re.finditer(r'\b(\w+)\s*[\+\-\*/]?=|[\+\-]{2}', line):
            name = match.group(1)
            if name not in inferred_types:
                inferred_types[name] = "int"

    return inferred_types

def insert_variable_declarations(content, inferred_types, output_folder):
    """
    Inserts variable declarations at top of main function.
    """
    lines = content.splitlines()
    new_lines = []
    inside_main = False
    inserted = False

    for line in lines:
        new_lines.append(line)
        if not inserted and re.search(r'\bmain\s*\(.*\)\s*{', line):
            inside_main = True
        elif inside_main and not inserted:
            # Insert inferred declarations
            for var, vartype in inferred_types.items():
                if "*" in vartype:
                    new_lines.append(f"  {vartype} {var};")
                else:
                    new_lines.append(f"  {vartype} {var} = 0;")
            inserted = True

    restored = "\n".join(new_lines)
    save_step(restored, output_folder, "step3_inferred_declarations.c")
    return restored

def insert_dummy_io(content, output_folder):
    lines = content.splitlines()
    restored_lines = []
    inserted = False

    for line in lines:
        restored_lines.append(line)
        if not inserted and re.search(r'\bint\s+var\s*;', line):
            restored_lines.append('    scanf("%d", &var);')
            restored_lines.append('    printf("value = %d\\n", var);')
            inserted = True

    # fallback: if not inserted above, inject before return
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

    save_step(restored, output_folder, "step4_dummy_io.c")
    return restored

def reverse_preprocess(input_file, output_folder):
    print(f"\n[*] Reversing file: {input_file}")
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
        print(f"[+] Created output folder: {output_folder}")

    with open(input_file, "r") as f:
        content = f.read()
    print(f"[+] Original file read ({len(content)} bytes)")

    content = restore_main_function(content, output_folder)
    content = restore_string_literals(content, output_folder)
    inferred_types = infer_variable_types(content)
    content = insert_variable_declarations(content, inferred_types, output_folder)
    content = insert_dummy_io(content, output_folder)

    final_output_path = os.path.join(output_folder, "restored_main.c")
    with open(final_output_path, "w") as f:
        f.write(content)

    print(f"[✓] Final restored file saved to: {final_output_path}\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Smart Reverse Preprocessor with Type Inference")
    parser.add_argument("-input_file", required=True, help="Path to the preprocessed C file (e.g., main_flat.c)")
    parser.add_argument("-output_folder", required=True, help="Folder to save the restored code")
    args = parser.parse_args()

    reverse_preprocess(args.input_file, args.output_folder)
