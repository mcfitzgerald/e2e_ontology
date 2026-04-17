from pathlib import Path
import pytest
import re

# Simulate the pure functions that will live in editor.py

def parse_sections(text: str) -> list[dict]:
    """
    Parse supply_chain_demo.yaml into a list of section ranges.
    Returns: [{'header': str, 'start_line': int, 'end_line': int}, ...]
    The line range covers the entire section up to just before the next header's block.
    """
    lines = text.splitlines()
    sections = []
    
    # A header block consists of a top divider, some text, and a bottom divider.
    # regex for divider: \s*# (===|---).*
    divider_regex = re.compile(r"^(\s*)# (===|---|=+|-+)")
    
    i = 0
    while i < len(lines):
        match = divider_regex.match(lines[i])
        if match:
            start_line = i
            # gather header lines until the matching bottom divider
            header_text = []
            i += 1
            while i < len(lines) and not divider_regex.match(lines[i]):
                header_text.append(lines[i].strip("# \t"))
                i += 1
            
            # i is now at the bottom divider, if any
            if i < len(lines):
                i += 1 # skip bottom divider
                
            header_str = " ".join([h for h in header_text if h]).strip()
            if not header_str:
                header_str = "Unnamed Section"
                
            if sections:
                # The previous section ends just before this new block
                # However, there might be blank lines before. We don't necessarily truncate them,
                # but if we want to insert we do it BEFORE the blank line preceding this block.
                sections[-1]['end_line'] = start_line - 1
            
            sections.append({
                'header': header_str,
                'start_line': start_line,
                # end_line to be determined by the next section
            })
        else:
            i += 1
            
    if sections:
        sections[-1]['end_line'] = len(lines) - 1
        
    return sections


def anchor_and_insert(current_content: str, fragment: str, section_index: int) -> str:
    """
    Insert `fragment` at the end of the section pointed to by `section_index`.
    Preserve one blank line before the next section's divider.
    """
    sections = parse_sections(current_content)
    if not sections or section_index < 0 or section_index >= len(sections):
        return current_content
    
    sec = sections[section_index]
    end_line = sec['end_line']
    
    lines = current_content.splitlines()
    
    # Find the actual end of content (excluding blank lines at the end of the section)
    insert_at = end_line
    while insert_at > sec['start_line'] and not lines[insert_at].strip():
        insert_at -= 1
        
    insert_at += 1
    
    new_lines = lines[:insert_at]
    if new_lines and new_lines[-1].strip():
        new_lines.append("")
        
    new_lines.append(fragment.rstrip())
    new_lines.append("") # Ensure a blank line after our insertion
    
    # Add back the remaining lines
    # We want to ensure that exactly ONE blank line separates this new block from the next divider.
    # The next divider starts at end_line + 1. So we append lines starting from insert_at, but we 
    # skip any leading blank lines so we don't multiply them.
    remainder = lines[insert_at:]
    while remainder and not remainder[0].strip():
        remainder.pop(0)
        
    new_lines.extend(remainder)
    
    return "\n".join(new_lines) + "\n"

# ----------------- Tests -----------------

def test_parse_sections():
    yaml_text = '''# ===
# First Section
# ===
class1:
  foo: bar

  # ---
  # Sub Section
  # ---
class2:
  baz: 1
'''
    sections = parse_sections(yaml_text)
    assert len(sections) == 2
    assert sections[0]['header'] == "First Section"
    assert sections[0]['start_line'] == 0
    assert sections[0]['end_line'] == 5  # line 5 is blank before Sub Section
    
    assert sections[1]['header'] == "Sub Section"
    assert sections[1]['start_line'] == 6


def test_anchor_and_insert():
    yaml_text = '''# ===
# Sect 1
# ===
Role1:
  val: 1
  
# ===
# Sect 2
# ===
Role2:
  val: 2
'''
    frag = "RoleNew:\n  val: new"
    new_text = anchor_and_insert(yaml_text, frag, 0)
    
    expected = '''# ===
# Sect 1
# ===
Role1:
  val: 1

RoleNew:
  val: new

# ===
# Sect 2
# ===
Role2:
  val: 2
'''
    assert new_text == expected

