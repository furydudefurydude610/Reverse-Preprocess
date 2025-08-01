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
    # Replace 'entry_point' with 'main'
    content = re.sub(r'\bentry_point\b', 'main', content)

    # Fix malformed main declarations with trailing parameters after main(void)
    content = re.sub(
        r'\bint\s+main\s*\([^)]*\)\s*(,\s*.*?\))\s*{', 
        'int main(void) {', 
        content
    )

    save_step(content, output_folder, "step_restore_main_function.c")
    return content



def restore_string_literals(content, output_folder):
    restored = re.sub(r'"STR"', '"restored_string"', content)
    save_step(restored, output_folder, "step2_restored_strings.c")
    return restored

def extract_function_params(content):
    match = re.search(r'\bmain\s*\(([^)]*)\)', content)
    if not match:
        return set()
    param_block = match.group(1)
    param_names = set()
    for part in param_block.split(','):
        tokens = re.findall(r'\(*\s*\*?\s*(\w+)\s*\)*', part)
        if tokens:
            param_names.add(tokens[-1])
    return param_names

def is_valid_identifier(name):
    return name.isidentifier() and not name[0].isdigit()

def infer_variable_types(content, function_params):
    inferred_types = {}
    declared = set()

    lines = content.splitlines()
    for line in lines:
        # Record declared variables
        decl_match = re.match(r'\s*(int|float|double|char|long|short)\s+(.+?);', line)
        if decl_match:
            varlist = decl_match.group(2)
            for v in varlist.split(','):
                v = v.strip()
                name_match = re.match(r'\*?\s*(\w+)', v)
                if name_match:
                    declared.add(name_match.group(1))

        # Infer pointer
        for match in re.finditer(r'\(\*\s*(\w+)\s*\)', line):
            var = match.group(1)
            if var not in declared and var not in function_params and is_valid_identifier(var):
                inferred_types[var] = "int *"

        # Infer int via usage
        for match in re.finditer(r'\b(\w+)\s*(?:\+\+|--|[+\-*/]?=)', line):
            var = match.group(1)
            if var not in declared and var not in function_params and is_valid_identifier(var):
                inferred_types[var] = "int"

    return inferred_types

def insert_variable_declarations(content, inferred_types, output_folder):
    lines = content.splitlines()
    new_lines = []
    inserted = False
    declared = set()

    for line in lines:
        new_lines.append(line)
        if not inserted and re.search(r'\bmain\s*\(.*\)\s*{', line):
            for var, vartype in inferred_types.items():
                if var not in declared:
                    declared.add(var)
                    if "*" in vartype:
                        new_lines.append(f"    {vartype} {var};")
                    else:
                        new_lines.append(f"    {vartype} {var} = 0;")
            inserted = True

    restored = "\n".join(new_lines)
    save_step(restored, output_folder, "step3_inferred_declarations.c")
    return restored
def extract_function_params(content):
    """Extract parameter names from main() declaration."""
    match = re.search(r'\bmain\s*\(([^)]*)\)', content)
    if not match:
        return set()
    
    param_block = match.group(1)
    if param_block.strip() == 'void' or not param_block.strip():
        return set()

    param_names = set()
    for part in param_block.split(','):
        part = part.strip()
        tokens = re.findall(r'\(*\s*\*?\s*(\w+)\s*\)*', part)
        if tokens:
            param_names.add(tokens[-1])
    return param_names

def insert_pointer_assignments(content, output_folder):
    lines = content.splitlines()
    new_lines = []
    inserted = set()

    for i, line in enumerate(lines):
        new_lines.append(line)
        if match := re.search(r'\(\*\s*(\w+)\s*\)\s*=', line):
            ptr = match.group(1)
            if ptr not in inserted:
                target_var = "sum" if "sum" in line else "product"
                new_lines.insert(i, f"    {ptr} = &{target_var};")
                inserted.add(ptr)

    restored = "\n".join(new_lines)
    save_step(restored, output_folder, "step4_pointer_assignments.c")
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

    save_step(restored, output_folder, "step5_dummy_io.c")
    return restored

def ensure_std_headers(content):
    if "#include" not in content:
        headers = "#include <stdio.h>\n"
        return headers + content
    return content

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
    content = insert_pointer_assignments(content, output_folder)
    content = insert_dummy_io(content, output_folder)
    content = ensure_std_headers(content)

    final_output_path = os.path.join(output_folder, "restored_main.c")
    with open(final_output_path, "w") as f:
        f.write(content)

    print(f"[✓] Final restored file saved to: {final_output_path}\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Smart Reverse Preprocessor (Fixed Version)")
    parser.add_argument("-input_file", required=True, help="Path to the preprocessed C file (e.g., main_flat.c)")
    parser.add_argument("-output_folder", required=True, help="Folder to save the restored code")
    args = parser.parse_args()

    reverse_preprocess(args.input_file, args.output_folder)
