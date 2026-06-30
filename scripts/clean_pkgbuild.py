#!/usr/bin/env python3
import sys
import re

def clean_pkgbuild(filepath, original_name, target_name):
    print(f"Modifying {filepath}: {original_name} -> {target_name}")
    
    with open(filepath, 'r') as f:
        content = f.read()

    # 1. Replace pkgname definition
    # Handles: pkgname=name, pkgname=(name), pkgname=('name'), pkgname=("name")
    pkgname_regex = re.compile(rf'(pkgname\s*=\s*\(?[\'"]?){original_name}([\'"]?\)?)')
    if pkgname_regex.search(content):
        content = pkgname_regex.sub(rf'\1{target_name}\2', content)
    else:
        # Simple replacements if regex misses
        content = content.replace(f"pkgname={original_name}", f"pkgname={target_name}")
        content = content.replace(f"pkgname=('{original_name}')", f"pkgname=('{target_name}')")
        content = content.replace(f"pkgname=(\"{original_name}\")", f"pkgname=(\"{target_name}\")")

    # 2. Add provides and conflicts with original name
    provides_expr = f"provides=('{original_name}')"
    conflicts_expr = f"conflicts=('{original_name}')"
    
    # Check if provides or conflicts are already defined in the file
    if "provides=" in content:
        # Append to existing array, e.g. provides=('foo') -> provides=('foo' 'original_name')
        content = re.sub(r'provides=\((.*?)\)', rf"provides=(\1 '{original_name}')", content)
    else:
        content += f"\n{provides_expr}\n"

    if "conflicts=" in content:
        content = re.sub(r'conflicts=\((.*?)\)', rf"conflicts=(\1 '{original_name}')", content)
    else:
        content += f"\n{conflicts_expr}\n"

    # 3. Replace cross-dependencies for renamed packages
    dependency_renames = {
        "dory-git": "dory",
        "nerd-dictation-git": "nerd-dictation",
        "xdg-desktop-portal-xapp-filepicker-git": "xdg-desktop-portal-xapp-filepicker"
    }
    for old_dep, new_dep in dependency_renames.items():
        content = content.replace(f"'{old_dep}'", f"'{new_dep}'")
        content = content.replace(f'"{old_dep}"', f'"{new_dep}"')
        content = content.replace(f' {old_dep} ', f' {new_dep} ')
        content = content.replace(f'({old_dep} ', f'({new_dep} ')
        content = content.replace(f' {old_dep})', f' {new_dep})')
        content = content.replace(f'({old_dep})', f'({new_dep})')

    # Save modified PKGBUILD
    with open(filepath, 'w') as f:
        f.write(content)
    
    print(f"Successfully cleaned PKGBUILD for {target_name}")

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: clean_pkgbuild.py <filepath> <original_name> <target_name>")
        sys.exit(1)
    clean_pkgbuild(sys.argv[1], sys.argv[2], sys.argv[3])
