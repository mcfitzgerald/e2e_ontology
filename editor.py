import streamlit as st
import sys
import exploder
from pathlib import Path
import contextlib
import json

ONTOLOGY_YAML = "supply_chain_demo.yaml"

st.set_page_config(page_title="Supply Chain Ontology Editor", layout="wide")

@st.cache_resource
def load_current_ontology():
    return exploder.load_ontology(ONTOLOGY_YAML)

def parse_sections(text: str) -> list[dict]:
    import re
    lines = text.splitlines()
    sections = []
    divider_regex = re.compile(r"^(\s*)# (===|---|=+|-+)")
    
    i = 0
    while i < len(lines):
        match = divider_regex.match(lines[i])
        if match:
            start_line = i
            header_text = []
            i += 1
            while i < len(lines) and not divider_regex.match(lines[i]):
                header_text.append(lines[i].strip("# \t"))
                i += 1
            if i < len(lines):
                i += 1 
            header_str = " ".join([h for h in header_text if h]).strip()
            if not header_str:
                header_str = "Unnamed Section"
            if sections:
                sections[-1]['end_line'] = start_line - 1
            sections.append({'header': header_str, 'start_line': start_line})
        else:
            i += 1
    if sections:
        sections[-1]['end_line'] = len(lines) - 1
    return sections

def anchor_and_insert(current_content: str, fragment: str, section_index: int) -> str:
    sections = parse_sections(current_content)
    if not sections or section_index < 0 or section_index >= len(sections):
        return current_content
    sec = sections[section_index]
    end_line = sec['end_line']
    lines = current_content.splitlines()
    
    insert_at = end_line
    while insert_at > sec['start_line'] and not lines[insert_at].strip():
        insert_at -= 1
    insert_at += 1
    
    new_lines = lines[:insert_at]
    if new_lines and new_lines[-1].strip():
        new_lines.append("")
        
    new_lines.append(fragment.rstrip())
    new_lines.append("") 
    
    remainder = lines[insert_at:]
    while remainder and not remainder[0].strip():
        remainder.pop(0)
    new_lines.extend(remainder)
    return "\n".join(new_lines) + "\n"

def render_mermaid(element_name: str):
    path = Path("docs") / f"{element_name}.md"
    if path.exists():
        content = path.read_text()
        import re
        match = re.search(r"```mermaid\n(.*?)\n```", content, re.DOTALL)
        if match:
            st.markdown(f"```mermaid\n{match.group(1)}\n```")
        else:
            st.info("No Mermaid diagram found in docs for this element.")
    else:
        st.warning(f"No documentation file found at `docs/{element_name}.md`. You may need to generate docs.")

def render_global_role_flows(ontology: exploder.Ontology):
    lines = ["flowchart TD"]
    for flow in ontology.flows.values():
        if flow.body.source_role and flow.body.target_role:
            lines.append(f"    {flow.body.source_role} -->|{flow.name}| {flow.body.target_role}")
    if len(lines) > 1:
        st.markdown(f"```mermaid\n{chr(10).join(lines)}\n```")
    else:
        st.info("No role-to-role flows found.")

def main():
    st.title("Ontology Viewer & Editor")

    try:
        ontology = load_current_ontology()
    except Exception as e:
        st.error(f"Failed to load ontology: {e}")
        return

    tab_viewer, tab_diff, tab_writer = st.tabs(["Viewer", "Diff", "Writable Editor"])

    with tab_viewer:
        st.header("Viewer Mode")
        st.subheader("Global Flow Graph")
        with st.expander("Show Role ↔ Role Flows", expanded=False):
            render_global_role_flows(ontology)

        category = st.sidebar.selectbox("Category", ["Roles", "Events", "State Machines", "Flows", "Entities", "Enums"])
        
        if category == "Roles":
            items = list(ontology.roles.keys())
            item_name = st.selectbox("Select Role", items) if items else None
            if item_name:
                role = ontology.roles[item_name]
                st.write("### Properties")
                st.json({
                    "description": role.body.description,
                    "is_boundary": role.body.is_boundary,
                    "human_involvement": role.body.human_involvement,
                    "domain": role.domain,
                    "subdomain": role.subdomain,
                    "llm_prompt_hint": role.body.llm_prompt_hint,
                })
                render_mermaid(item_name)
                
        elif category == "Events":
            items = list(ontology.events.keys())
            item_name = st.selectbox("Select Event", items) if items else None
            if item_name:
                event = ontology.events[item_name]
                st.write("### Properties")
                st.json({
                    "description": event.body.description,
                    "observed_by": event.body.observed_by,
                    "domain": event.domain,
                    "subdomain": event.subdomain,
                    "llm_prompt_hint": event.body.llm_prompt_hint,
                })
                render_mermaid(item_name)
                
        elif category == "State Machines":
            items = list(ontology.state_machines.keys())
            item_name = st.selectbox("Select State Machine", items) if items else None
            if item_name:
                sm = ontology.state_machines[item_name]
                st.write("### Properties")
                st.json({
                    "states": sm.body.states,
                    "initial": sm.body.initial,
                    "terminal": sm.body.terminal,
                    "transitions": [t.model_dump() for t in sm.body.transitions] if sm.body.transitions else [],
                    "domain": sm.domain,
                    "subdomain": sm.subdomain,
                })
                render_mermaid(item_name)
                
        elif category == "Flows":
            items = list(ontology.flows.keys())
            item_name = st.selectbox("Select Flow", items) if items else None
            if item_name:
                flow = ontology.flows[item_name]
                st.write("### Properties")
                st.json({
                    "kind": flow.kind,
                    "source_role": flow.body.source_role,
                    "target_role": flow.body.target_role,
                    "quantum": flow.body.quantum,
                    "returns": flow.body.returns,
                    "trigger_event": flow.body.trigger_event,
                    "lifecycle_ref": flow.body.lifecycle_ref,
                    "on_failure_route_to": flow.body.on_failure_route_to,
                    "llm_prompt_hint": flow.llm_prompt_hint,
                    "domain": flow.domain,
                    "subdomain": flow.subdomain,
                })
                if flow.axioms:
                    st.write("### Axioms")
                    st.json([a.model_dump() for a in flow.axioms])
                render_mermaid(item_name)
                
        elif category == "Entities":
            items = list(ontology.entities.keys())
            item_name = st.selectbox("Select Entity", items) if items else None
            if item_name:
                entity = ontology.entities[item_name]
                st.write("### Properties")
                st.json({
                    "description": entity.description,
                    "domain": entity.domain,
                    "subdomain": entity.subdomain,
                    "attributes": entity.attributes,
                    "rules": entity.rules,
                    "metrics": [m.model_dump() for m in entity.metrics],
                    "other_annotations": entity.other_annotations,
                })
                render_mermaid(item_name)
                
        elif category == "Enums":
            items = list(ontology.enums.keys())
            item_name = st.selectbox("Select Enum", items) if items else None
            if item_name:
                eenum = ontology.enums[item_name]
                st.write("### Properties")
                st.json(eenum)
                render_mermaid(item_name)

    with tab_diff:
        st.header("Diff Panel")
        col1, col2 = st.columns(2)
        with col1:
            ref_left = st.text_input("Left ref", value="HEAD")
        with col2:
            ref_right = st.text_input("Right ref/file", value=ONTOLOGY_YAML)
        
        if st.button("Compute Diff"):
            try:
                with exploder._resolve_diff_inputs(ref_left, ref_right, ONTOLOGY_YAML) as (path1, path2):
                    old_ont = exploder.load_ontology(path1)
                    new_ont = exploder.load_ontology(path2)
                    deltas = exploder.compute_delta(old_ont, new_ont)
                    if deltas:
                        st.json(json.loads(exploder.render_delta_json(deltas)))
                    else:
                        st.success("(no differences)")
            except Exception as e:
                st.error(f"Diff failed: {e}")

    with tab_writer:
        st.header("Writable Pass")
        st.write("Generate a new ontology element.")
        
        kind = st.selectbox("Element Kind", exploder.SCAFFOLD_KINDS)
        name = st.text_input("Name", placeholder="e.g. new_role_name")
        domain = st.text_input("Domain (Optional)", placeholder="e.g. procurement")
        
        # Read the current file to parse sections for the anchor dropdown
        try:
            current_text = Path(ONTOLOGY_YAML).read_text()
            sections = parse_sections(current_text)
            section_choices = [f"{i}: {s['header']}" for i, s in enumerate(sections)]
        except Exception as e:
            st.error(f"Failed to read sectors: {e}")
            sections = []
            section_choices = []
            
        anchor_selection = st.selectbox("Insert after section", section_choices)
        
        if st.button("Preview"):
            if not name.strip():
                st.error("Name is required.")
            else:
                try:
                    frag = exploder._template_for_kind(kind, name.strip(), {}, domain.strip() if domain.strip() else None)
                    st.session_state["preview_fragment"] = frag
                    st.session_state["preview_name"] = name.strip()
                except Exception as e:
                    st.error(f"Failed to scaffold: {e}")
                    
        if "preview_fragment" in st.session_state:
            st.subheader("Preview")
            frag = st.session_state["preview_fragment"]
            st.code(frag, language="yaml")
            
            import re
            placeholders = re.findall(r"<[A-Z_]+>", frag)
            if placeholders:
                st.warning(f"Please fill out these placeholders before saving: {', '.join(set(placeholders))}")
                
            new_frag = st.text_area("Edit Fragment", value=frag, height=300)
            st.session_state["edited_fragment"] = new_frag
            
            still_has_placeholders = bool(re.search(r"<[A-Z_]+>", new_frag))
            
            if st.button("Insert & Save", disabled=still_has_placeholders):
                # Atomic writes logic
                if not sections:
                    st.error("No sections could be parsed, aborting.")
                else:
                    anchor_idx = int(anchor_selection.split(":")[0])
                    new_content = anchor_and_insert(current_text, new_frag, anchor_idx)
                    
                    tmp_file = Path(f"{ONTOLOGY_YAML}.tmp")
                    tmp_file.write_text(new_content)
                    
                    import subprocess
                    # Run validation against the .tmp file
                    cmd = [sys.executable, "exploder.py", "validate", "--strict", str(tmp_file)]
                    res = subprocess.run(cmd, capture_output=True, text=True)
                    
                    if res.returncode == 0:
                        import os
                        os.replace(tmp_file, ONTOLOGY_YAML)
                        st.success("Successfully inserted and validated!")
                        st.session_state.pop("preview_fragment")
                        # Clear load_current_ontology cache
                        load_current_ontology.clear()
                    else:
                        st.error("Validation failed! Changes were rolled back.")
                        st.code(res.stderr or res.stdout)

if __name__ == "__main__":
    main()
