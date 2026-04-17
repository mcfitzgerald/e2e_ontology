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
        st.info("Phase 2 placeholder. To be implemented next.")

if __name__ == "__main__":
    main()
