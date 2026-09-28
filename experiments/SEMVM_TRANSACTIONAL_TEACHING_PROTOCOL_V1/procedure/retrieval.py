"""Controlled natural-language procedure retrieval (spec §26-§28, §56; Amendment 001). NOT open-English understanding.
  request -> (1) deterministic alias rule: request contains a registered alias of >= 2 ACTIVE procedures -> CLARIFY; of exactly 1 -> that one
          -> (2) otherwise the frozen LLM ranks ACTIVE procedures (log P(" name(" | request)); top-2 margin < MARGIN -> CLARIFY
          -> (3) the LLM writes the argument list / nested plan for the chosen procedure
          -> (4) deterministic checks: every parameter present and typed, every literal is a vocabulary value of the parameter type AND occurs
                 in the request, nested calls only to ACTIVE procedures whose return type = parameter type, no extra arguments
          -> invoke (one transaction) | CLARIFY. Nothing is chosen arbitrarily."""
import re, os, sys, copy
sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
import llm as LM, executor as X, lang as L
MARGIN = 1.0   # registered before DEV (nats)


class PlanError(Exception): pass


def parse_call(s):
    s = s.strip(); m = re.match(r"([a-z][a-z0-9_]*)\s*\(", s)
    if not m: raise PlanError(f"not a call: {s!r}")
    name, i, depth, cur, args = m.group(1), m.end(), 1, "", []
    while i < len(s):
        c = s[i]; i += 1
        if c == "(": depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0: break
        if c == "," and depth == 1: args.append(cur); cur = ""; continue
        cur += c
    if depth != 0: raise PlanError("unbalanced parentheses")
    if cur.strip(): args.append(cur)
    out = {}
    for j, a in enumerate(args):
        if "=" not in a or "(" in a.split("=", 1)[0]: k, v = f"_pos{j}", a.strip()          # positional argument (bound only by the single-parameter rule)
        else: k, v = a.split("=", 1); k, v = k.strip(), v.strip()
        out[k] = parse_call(v) if "(" in v else v
    return {"call": name, "args": out}


def check_plan(plan, lib, request, types=None):
    """deterministic compatibility / type check; returns the return type"""
    p = lib.active(plan["call"])
    if p is None: raise PlanError(f"no ACTIVE procedure {plan['call']}")
    toks = {t.lower().strip(",.?!'") for t in request.split()} | {t.lower() for t in re.findall(r"[\w:]+", request)}
    ps = {x["name"]: x["type"] for x in p["parameters"]}
    if len(ps) == 1 and len(plan["args"]) == 1 and set(plan["args"]) != set(ps):   # registered pre-DEV rule (ENGINEERING_LOG #2): single-parameter binding by position
        plan["args"] = {next(iter(ps)): next(iter(plan["args"].values()))}
    if set(plan["args"]) != set(ps): raise PlanError(f"arguments {sorted(plan['args'])} != parameters {sorted(ps)}")
    for k, v in plan["args"].items():
        if isinstance(v, dict):
            rt = check_plan(v, lib, request)
            if rt != ps[k]: raise PlanError(f"nested {v['call']} returns {rt}, {k} needs {ps[k]}")
        else:
            if v not in X.VOCAB[ps[k]]: raise PlanError(f"{v!r} is not a {ps[k]} value")
            if v.lower() not in toks: raise PlanError(f"{v!r} does not occur in the request")
    import validate as VD
    return VD.validate(p, lib)["returns"]


# ---------------- DEV tuning (ENGINEERING_LOG #3): deterministic argument repair + typed candidate fallback / composition search ----------------
VALUE_TYPES = ["PERSON", "TIME", "PLACE", "TOPIC"]


def canon(v, typ):
    for x in sorted(X.VOCAB[typ]):
        if x.lower() == str(v).lower(): return x
    return None


def repair(plan, lib):
    """case-insensitive vocabulary canonicalization; arguments whose name is not a parameter are bound by value class to the unique unbound
    parameter of that type (value classes are disjoint); leftover arguments that are not vocabulary values of any type are dropped (logged)"""
    p = lib.active(plan["call"])
    if p is None: return plan, ["unknown procedure"]
    ps = {x["name"]: x["type"] for x in p["parameters"]}; bound = {}; notes = []; pending = []
    for k, v in plan["args"].items():
        if isinstance(v, dict): v, _ = repair(v, lib)
        if k in ps and not isinstance(v, dict) and canon(v, ps[k]): bound[k] = canon(v, ps[k])
        elif k in ps and isinstance(v, dict): bound[k] = v
        else: pending.append((k, v))
    for k, v in pending:
        if isinstance(v, dict):
            q = lib.active(v["call"]); rt = next((a["returns"] for a in lib.list_active() if a["name"] == v["call"]), None) if q else None
            tgt = [n for n, t in ps.items() if n not in bound and t == rt]
            if len(tgt) == 1: bound[tgt[0]] = v; notes.append(f"nested {v['call']} bound to {tgt[0]} by type")
            else: bound[k] = v
            continue
        tgt = [n for n, t in ps.items() if n not in bound and canon(v, t)]
        if len(tgt) == 1: bound[tgt[0]] = canon(v, ps[tgt[0]]); notes.append(f"{k}={v} bound to {tgt[0]} by type")
        elif not any(canon(v, t) for t in VALUE_TYPES + ["EVENT_TYPE", "STATUS"]): notes.append(f"dropped non-value argument {k}={v}")
        else: bound[k] = v
    return {"call": plan["call"], "args": bound}, notes


def request_values(request, typ):
    return sorted({canon(t, typ) for t in re.findall(r"[\w:]+", request) if canon(t, typ)})


def candidate_plans(name, lib, request, depth=1):
    p = lib.active(name); acts = {a["name"]: a for a in lib.list_active()}; options = []
    for par in p["parameters"]:
        c = [v for v in request_values(request, par["type"])] if par["type"] in VALUE_TYPES else []
        if depth > 0:
            for q, a in acts.items():
                if q != name and a["returns"] == par["type"]: c += candidate_plans(q, lib, request, depth - 1)
        if not c: return []
        options.append([(par["name"], x) for x in c])
    import itertools
    return [{"call": name, "args": dict(combo)} for combo in itertools.islice(itertools.product(*options), 50)]


def fallback(name, lib, request, procs):
    cands = [c for c in candidate_plans(name, lib, request) if _valid(c, lib, request)]
    if not cands: return None, "no typed candidate arguments in the request"
    if len(cands) == 1: return cands[0], "unique typed candidate"
    prompt = LM.RETRIEVE_FEWSHOT + f"Available: {LM.signature_line(procs)}\nRequest: {request}\nCall:"
    sc = LM._post("/score", {"prompt": prompt, "continuations": [" " + plan_str(c) for c in cands]})["logprobs"]; rk = sorted(zip(sc, range(len(cands))), reverse=True)
    if rk[0][0] - rk[1][0] < MARGIN: return None, f"typed candidates tie (margin {rk[0][0] - rk[1][0]:.2f})"
    return cands[rk[0][1]], "LLM-ranked typed candidate"


def _valid(plan, lib, request):
    try: check_plan(copy.deepcopy(plan), lib, request); return True
    except PlanError: return False


# ---------------- ENGINEERING_LOG #4: stored-procedure reuse canonicalization (semantic identity, spec §57 / §61) ----------------
def composite_template(proc):
    """an ACTIVE procedure whose body is only CALL steps + RETURN of the last call -> nested plan template with {param} leaves; else None"""
    b = proc["body"]
    if len(b) < 2 or b[-1]["op"] != "RETURN" or any(s["op"] != "CALL" for s in b[:-1]): return None
    env = {}
    for s in b[:-1]:
        args = {}
        for k, x in s["args"].items():
            if "var" in x:
                if x["var"] not in env: return None
                args[k] = env[x["var"]]
            elif "param" in x: args[k] = {"param": x["param"]}
            else: args[k] = x["const"]
        env[s["bind"]] = {"call": s["procedure"], "args": args}
    return env.get(b[-1]["value"].get("var"))


def _match(t, pl, bind):
    if isinstance(t, dict) and "param" in t:
        if isinstance(pl, dict): return False
        return bind.setdefault(t["param"], pl) == pl
    if isinstance(t, dict):
        return isinstance(pl, dict) and t["call"] == pl["call"] and set(t["args"]) == set(pl["args"]) and all(_match(t["args"][k], pl["args"][k], bind) for k in t["args"])
    return t == pl


def canonicalize(plan, lib):
    """rewrite a plan that is exactly the expansion of an ACTIVE stored composite into a call of that composite"""
    for a in lib.list_active():
        if a["name"] == plan["call"]: continue
        t = composite_template(lib.active(a["name"]))
        if t is not None:
            bind = {}
            if _match(t, plan, bind) and set(bind) == {x["name"] for x in a["parameters"]}: return {"call": a["name"], "args": bind}, a["name"]
    return plan, None


def resolve_args(name, request, lib, procs, out):
    text, _ = LM.generate_call(request, procs, name); out.setdefault("llm_call_texts", {})[name] = text
    try:
        plan = parse_call(text); plan, notes = repair(plan, lib); check_plan(plan, lib, request); return plan, "llm"
    except PlanError as e:
        plan, why = fallback(name, lib, request, procs); out.setdefault("fallbacks", {})[name] = why
        return (plan, "typed_fallback") if plan else (None, f"{e}; fallback: {why}")


def plan_to_proc(plan):
    """nested plan -> a one-off composite procedure (CALL steps only), executed as ONE transaction"""
    body = []; n = [0]
    def emit(pl):
        args = {}
        for k, v in pl["args"].items(): args[k] = {"var": emit(v)} if isinstance(v, dict) else {"const": v}
        var = f"c{n[0]}"; n[0] += 1; body.append({"op": "CALL", "bind": var, "procedure": pl["call"], "args": args}); return var
    body.append({"op": "RETURN", "value": {"var": emit(plan)}}); return {"name": "__composite", "parameters": [], "body": body}


def retrieve(request, lib):
    procs = lib.list_active(); out = {"request": request, "candidates": [p["name"] for p in procs]}
    if not procs: out.update(status="CLARIFY", reason="no active procedures"); return out
    low = " " + " ".join(re.findall(r"[\w:]+", request.lower())) + " "
    hit = sorted({p["name"] for p in procs for a in p["aliases"] if f" {a} " in low})
    out["alias_hits"] = hit
    if len(hit) >= 2: out.update(status="CLARIFY", reason=f"request matches the alias of {len(hit)} procedures: {hit}"); return out
    if len(hit) == 1: name = hit[0]; out["ranking"] = [[name, None]]
    else:
        scores, _ = LM.score_names(request, procs); rank = sorted(zip([p["name"] for p in procs], scores), key=lambda x: -x[1]); out["ranking"] = [[a, round(b, 4)] for a, b in rank]
        if len(rank) > 1 and rank[0][1] - rank[1][1] < MARGIN:
            # #4 (final form): the score margin only SELECTS the candidates to examine; equivalence is STRUCTURAL. Every candidate within MARGIN
            # of the best is resolved to a plan and canonicalized (stored-procedure expansion); equivalent plans collapse into ONE semantic
            # candidate BEFORE ambiguity is decided. CLARIFY iff more than one DISTINCT canonical plan remains (or none resolves).
            within = [nm for nm, sc in rank if rank[0][1] - sc < MARGIN]; plans = {}
            for nm in within:
                pl, src = resolve_args(nm, request, lib, procs, out)
                if pl: cp, _ = canonicalize(pl, lib); plans.setdefault(plan_str(cp), (cp, []))[1].append(nm)
            out["tie_candidates"] = within; out["distinct_canonical_plans"] = sorted(plans)
            if len(plans) == 1:
                cp, members = next(iter(plans.values())); out.update(status="OK", plan=cp, argument_source="tie_collapsed_equivalent", collapsed=members); return out
            out.update(status="CLARIFY", reason=f"{len(plans)} distinct canonical plans within margin {MARGIN} ({within})"); return out
        name = rank[0][0]
    text, _ = LM.generate_call(request, procs, name); out["llm_call_text"] = text
    try:
        plan = parse_call(text); plan, notes = repair(plan, lib); out["repair_notes"] = notes; check_plan(plan, lib, request); out.update(status="OK", plan=plan, argument_source="llm")
    except PlanError as e:
        out["llm_argument_error"] = str(e); plan, why = fallback(name, lib, request, procs); out["fallback"] = why
        if plan is None: out.update(status="CLARIFY", reason=f"argument check failed: {e}; fallback: {why}")
        else: out.update(status="OK", plan=plan, argument_source="typed_fallback")
    if out.get("status") == "OK":
        cp, via = canonicalize(out["plan"], lib)
        if via: out.update(plan=cp, canonicalized_to=via)
    return out


def plan_str(pl): return f"{pl['call']}(" + ", ".join(f"{k}={plan_str(v) if isinstance(v, dict) else v}" for k, v in sorted(pl["args"].items())) + ")"
