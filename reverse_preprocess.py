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

def extract_function_params(content):
    """Extracts parameter names from the main() function signature."""
    match = re.search(r'\bmain\s*\(([^)]*)\)', content)
    if not match:
        return set()
    param_block = match.group(1)
    param_names = set()
    # Extract names like: int (*temp1), char (*string)
    for part in param_block.split(','):
        part = part.strip()
        tokens = re.findall(r'\(*\s*\*?\s*(\w+)\s*\)*', part)
        if tokens:
            param_names.add(tokens[-1])
    return param_names

def is_valid_identifier(name):
    return name.isidentifier() and not name[0].isdigit()

def infer_variable_types(content, function_params):
    """
    Analyzes the code and returns a dict {var_name: type}
    """
    inferred_types = defaultdict(lambda: "int")  # Default to int
    declared = set()

    lines = content.splitlines()
    for line in lines:
        # Infer from array usage like string[i]
        if match := re.search(r'(\w+)\s*\[.*?\]', line):
            var = match.group(1)
            if var not in function_params and is_valid_identifier(var):
                inferred_types[var] = "char *"
        
        # Pointer assignments like (*temp1) = something
        for match in re.finditer(r'\(\*\s*(\w+)\s*\)', line):
            var = match.group(1)
            if var not in function_params and is_valid_identifier(var):
                inferred_types[var] = "int *"

        # Direct increment/decrement or compound assignment
        for match in re.finditer(r'\b(\w+)\s*(?:\+\+|--|[+\-*/]?=)', line):
            var = match.group(1)
            if var not in function_params and is_valid_identifier(var):
                inferred_types[var] = "int"
    
    return inferred_types

def insert_variable_declarations(content, inferred_types, output_folder):
    lines = content.splitlines()
    new_lines = []
    inside_main = False
    inserted = False
    declared = set()

    for line in lines:
        new_lines.append(line)

        if not inserted and re.search(r'\bmain\s*\(.*\)\s*{', line):
            inside_main = True
        elif inside_main and not inserted:
            for var, vartype in inferred_types.items():
                if var not in declared:
                    declared.add(var)
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

    function_params = extract_function_params(content)
    inferred_types = infer_variable_types(content, function_params)
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
