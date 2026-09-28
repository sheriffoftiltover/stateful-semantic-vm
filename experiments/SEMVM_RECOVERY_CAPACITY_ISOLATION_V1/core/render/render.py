"""Deterministic template renderer (spec §16). No generative model."""


def render_value(store, v):
    if v.startswith("person:"): return store.alias_of(v) or v
    r = store.value(v); return r[2] if r else v


def render(status, store=None, ret=None, reason=""):
    if status == "OK":
        if ret is None: return "OK."
        return ", ".join(sorted(render_value(store, v) for v in ret)) if ret else "No matching item."
    return {"RESOLUTION_AMBIGUOUS": f"Ambiguous: {reason}.", "UNSUPPORTED_INPUT": "Unsupported input.", "IR_VALIDATION_ERROR": "I could not form a valid structure.",
            "RESOLVE_REFERENCE": f"Nothing to refer to: {reason}.", "VM_EXEC_ERROR": "The update failed and nothing was changed.",
            "COMMAND_SYNTAX_ERROR": "Unsupported command.", "RESOLVE_TIME": "Unsupported time."}.get(status, f"Error: {status}.")
