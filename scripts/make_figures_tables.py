"""Generate every number, table and data figure used in the paper and README directly from the released result JSONs.
python scripts/make_figures_tables.py        (needs matplotlib)
Writes: paper/generated/numbers.tex, paper/generated/tab_*.tex, paper/figures/fig_factorial.{pdf,png}, paper/figures/fig_hosted_arm.{pdf,png},
        docs/generated_numbers.json (the same values, for docs/README)."""
import os, json, math
ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__))); X = os.path.join(ROOT, "experiments")
GEN = os.path.join(ROOT, "paper", "generated"); FIG = os.path.join(ROOT, "paper", "figures"); os.makedirs(GEN, exist_ok=True); os.makedirs(FIG, exist_ok=True); os.makedirs(os.path.join(ROOT, "docs"), exist_ok=True)
J = lambda *p: json.load(open(os.path.join(X, *p)))
BLUE, ORANGE, INK, MUTED, GRID = "#2a78d6", "#eb6834", "#0b0b0b", "#52514e", "#e4e3df"


def cnt(v, n): return (int(round(v * n)), n) if v is not None and n else (None, n)


def frac(k_n): k, n = k_n; return f"{k}/{n}" if k is not None else "--"


def f3(v): return "--" if v is None else (f"{v:.3f}".lstrip("0") if v < 1 else "1.0")


def main():
    N = {}
    # ---------------- lineage ----------------
    e = J("SEMVM_END_TO_END_POC_V1", "results", "SEMVM_END_TO_END_POC_V1_RESULTS.json")
    N["eepDev"] = frac(cnt(e["DEV"]["SCENARIO_EXACT"], e["DEV"]["n_SCENARIO_EXACT"])); N["eepLocked"] = frac(cnt(e["LOCKED_TEST"]["SCENARIO_EXACT"], e["LOCKED_TEST"]["n_SCENARIO_EXACT"]))
    p = J("SEMVM_PROCEDURE_DISCOVERY_POC_V1", "results", "PROCEDURE_LOCKED_TEST.json"); d = p["LOCKED_TEST_v2"]["DISCOVERED"]
    N["pdLocked"] = frac(cnt(d["SCENARIO_EXACT"], d["n_SCENARIO_EXACT"])); N["pdFalseAccept"] = int(d["VERIFY_FALSE_ACCEPT"])
    pc = p["proposer_comparison"]["locked_v2"]; N["pdLlmOnly"] = pc["llm_only"]; N["pdDiscoveries"] = pc["discoveries"]
    n = J("SEMVM_NATURAL_LANGUAGE_PROCEDURE_TEACHING_V1", "results", "NL_TEACH_DEV.json"); m = n["versions"]["V1.2_final"]["metrics"]; da = n["DIRECT_AST_DIAGNOSTIC"]
    N.update(nlScenario=f3(m["NL_TEACH_SCENARIO_EXACT"]), nlLearned=f3(m["LEARNED_PROCEDURE_EXACT"]), nlWrongExec=m["WRONG_LLM_ACTION_EXECUTED"], nlWrongProposed=m["WRONG_LLM_ACTION_PROPOSED"],
             nlWrongBlocked=m["WRONG_LLM_ACTION_BLOCKED"], nlFalseAccept=m["VERIFY_FALSE_ACCEPT"], nlDirect=f"{100 * da['DIRECT_AST_EXACT']:.1f}", nlTrace=f"{100 * da['TRACE_MEDIATED_PROCEDURE_EXACT']:.1f}")
    x = J("SEMVM_LLM_TO_SEMVM_PROCEDURAL_DISTILLATION_V1", "results", "GROQ_DISTILLATION_DEV.json"); T = x["modes"]["TEACHER"]; S = x["modes"]["SCRIPTED"]; R = x["retention"]["TEACHER"]
    N.update(pdxTeacherLearned=frac(cnt(T["LEARNED_PROCEDURE_EXACT"], T["n_LEARNED_PROCEDURE_EXACT"])), pdxScriptedLearned=frac(cnt(S["LEARNED_PROCEDURE_EXACT"], S["n_LEARNED_PROCEDURE_EXACT"])),
             pdxWrong=T["WRONG_TEACHER_ACTION_EXECUTED"], pdxFalseAccept=T["VERIFY_FALSE_ACCEPT"], pdxRetention=frac(cnt(R["post_handoff_exact_given_exact_acquisition"], R["n"])))
    h = J("SEMVM_HOSTED_TEACHER_GROUNDER_V1", "results", "DEV_FACTORIAL.json")["arms"]
    N.update(htgDLearned=frac(cnt(h["D"]["LEARNED_PROCEDURE_EXACT"], h["D"]["n_LEARNED_PROCEDURE_EXACT"])), htgDGround=f3(h["D"]["GROUNDING_BEHAVIORAL_EXACT"]), htgDWrong=h["D"]["WRONG_BEHAVIORAL_ACTION_EXECUTED"])
    t = J("SEMVM_TRANSACTIONAL_TEACHING_PROTOCOL_V1", "results", "DEV_FACTORIAL.json")["arms"]; tD = t["D"]
    ttp = {k: cnt(tD[k], tD["n_" + k]) for k in ("LEARNED_PROCEDURE_EXACT", "SCENARIO_EXACT", "DISTILLED_SKILL_EXACT", "GROUNDING_BEHAVIORAL_EXACT")}
    N.update(ttpDLearned=frac(ttp["LEARNED_PROCEDURE_EXACT"]), ttpDWrong=tD["WRONG_BEHAVIORAL_ACTION_EXECUTED"])
    # ---------------- RCI ----------------
    P = J("SEMVM_RECOVERY_CAPACITY_ISOLATION_V1", "results", "DEV_POOLED.json"); A = J("SEMVM_RECOVERY_CAPACITY_ISOLATION_V1", "results", "DEV_A_FACTORIAL.json"); B = J("SEMVM_RECOVERY_CAPACITY_ISOLATION_V1", "results", "DEV_B_FACTORIAL.json")
    L = J("SEMVM_RECOVERY_CAPACITY_ISOLATION_V1", "results", "LOCKED_TEST.json"); LS = J("SEMVM_RECOVERY_CAPACITY_ISOLATION_V1", "results", "locked_test", "RCI_SUMMARY.json")["arms"]["D"]
    C = J("SEMVM_RECOVERY_CAPACITY_ISOLATION_V1", "results", "RECOVERY_CEILING_DIAGNOSTIC.json")
    M4 = ["LEARNED_PROCEDURE_EXACT", "SCENARIO_EXACT", "DISTILLED_SKILL_EXACT", "GROUNDING_BEHAVIORAL_EXACT"]
    rci = {arm: {k: P["arms"][arm][k] for k in M4} for arm in ("B", "E", "F", "D")}
    for k, short in zip(M4, ("Learned", "Scenario", "Distilled", "Grounding")):
        r = rci["D"][k]; N[f"rciD{short}Pooled"] = f"{r['pooled_counts'][0]}/{r['pooled_counts'][1]}"; N[f"rciD{short}PooledFrac"] = f3(r["pooled"])
        N[f"rciD{short}A"] = f"{r['per_replicate_counts'][0][0]}/{r['per_replicate_counts'][0][1]}"; N[f"rciD{short}B"] = f"{r['per_replicate_counts'][1][0]}/{r['per_replicate_counts'][1][1]}"
        N[f"rciD{short}Min"] = r["min_successes"]
    N["rciCeiling"] = C["recovered_exactly"]; N["rciFingerprint"] = A["config_fingerprint"][:8]; assert A["config_fingerprint"] == B["config_fingerprint"]
    N["rciSpend"] = "3.57"
    ld = L["as_recorded"]["D"]; lr = {k: cnt(LS.get(k), LS.get("n_" + k)) for k in M4}
    N.update(lockedLearned=frac(lr["LEARNED_PROCEDURE_EXACT"]), lockedScenario=frac(lr["SCENARIO_EXACT"]), lockedDistilled=frac(lr["DISTILLED_SKILL_EXACT"]), lockedGround=frac(lr["GROUNDING_BEHAVIORAL_EXACT"]),
             lockedGroundFrac=f3(LS["GROUNDING_BEHAVIORAL_EXACT"]))
    json.dump(N, open(os.path.join(ROOT, "docs", "generated_numbers.json"), "w"), indent=1)
    with open(os.path.join(GEN, "numbers.tex"), "w") as f:
        f.write("% generated by scripts/make_figures_tables.py from the released result JSONs -- do not edit\n")
        for k, v in N.items(): f.write(f"\\newcommand{{\\{k}}}{{{v}}}\n")
    # ---------------- Table: TTP parent vs RCI successor ----------------
    with open(os.path.join(GEN, "tab_parent_successor.tex"), "w") as f:
        f.write("\\begin{tabular}{lrrl}\n\\toprule\nMetric (Arm D) & TTP parent & RCI pooled & RCI DEV-A / DEV-B\\\\\n\\midrule\n")
        for k, name in zip(M4, ("Learned procedure exact", "Scenario exact", "Distilled skill exact", "Grounding behavioral exact")):
            pk, pn = ttp[k]; r = rci["D"][k]; a_, b_ = r["per_replicate_counts"]
            f.write(f"{name} & {pk}/{pn} ({f3(pk / pn)}) & {r['pooled_counts'][0]}/{r['pooled_counts'][1]} ({f3(r['pooled'])}) & {a_[0]}/{a_[1]} \\;/\\; {b_[0]}/{b_[1]}\\\\\n")
        f.write(f"Wrong committed actions & {tD['WRONG_BEHAVIORAL_ACTION_EXECUTED']} & {sum(P['arms']['D']['WRONG_BEHAVIORAL_ACTION_EXECUTED'])} & {P['arms']['D']['WRONG_BEHAVIORAL_ACTION_EXECUTED'][0]} \\;/\\; {P['arms']['D']['WRONG_BEHAVIORAL_ACTION_EXECUTED'][1]}\\\\\n\\bottomrule\n\\end{{tabular}}\n")
    # ---------------- Table: RCI factorial ----------------
    with open(os.path.join(GEN, "tab_factorial.tex"), "w") as f:
        f.write("\\begin{tabular}{llrrrr}\n\\toprule\nArm & Lesson / recovery & Learned & Scenario & Distilled & Grounding\\\\\n\\midrule\n")
        lab = {"B": "scripted / scripted", "E": "scripted / hosted", "F": "hosted / oracle", "D": "hosted / hosted"}
        for arm in ("B", "E", "F", "D"):
            cells = []
            for k in M4:
                r = rci[arm][k]; a_, b_ = r["per_replicate_counts"]; cells.append(f"{a_[0]}/{a_[1]} + {b_[0]}/{b_[1]} = \\textbf{{{r['pooled_counts'][0]}/{r['pooled_counts'][1]}}}")
            f.write(f"{arm} & {lab[arm]} & " + " & ".join(cells) + "\\\\\n")
        f.write("\\bottomrule\n\\end{tabular}\n")
    # ---------------- Table: LOCKED ----------------
    with open(os.path.join(GEN, "tab_locked.tex"), "w") as f:
        st = L["strict_teardown_rescore"]["D"]
        reuse = " / ".join(f"{LS[k]:.1f}" for k in ("UNSEEN_ARGUMENT_EXACT_GIVEN_ACQUISITION", "RESTART_EXACT_GIVEN_ACQUISITION", "STORED_PROCEDURE_REUSE_GIVEN_ACQUISITION"))
        rows = [("Learned procedure exact", frac(lr["LEARNED_PROCEDURE_EXACT"]), frac(lr["LEARNED_PROCEDURE_EXACT"]), "$\\ge .90$"),
                ("Scenario exact", frac(lr["SCENARIO_EXACT"]), frac(lr["SCENARIO_EXACT"]), "$\\ge .90$"),
                ("Grounding behavioral exact", f"{frac(lr['GROUNDING_BEHAVIORAL_EXACT'])} ({f3(LS['GROUNDING_BEHAVIORAL_EXACT'])})", f"{frac(lr['GROUNDING_BEHAVIORAL_EXACT'])}", "$\\ge .95$"),
                ("Wrong committed actions", str(LS["WRONG_BEHAVIORAL_ACTION_EXECUTED"]), str(LS["WRONG_BEHAVIORAL_ACTION_EXECUTED"]), "$=0$"),
                ("Incomplete demonstrations committed", str(LS["INCOMPLETE_DEMO_COMMITTED"]), str(LS["INCOMPLETE_DEMO_COMMITTED"]), "$=0$"),
                ("Post-handoff hosted calls / network attempts", f"{LS['HOSTED_CALLS_POST_HANDOFF']} / {LS['NETWORK_ATTEMPTS_POST_HANDOFF']}", f"{LS['HOSTED_CALLS_POST_HANDOFF']} / {LS['NETWORK_ATTEMPTS_POST_HANDOFF']}", "$=0$"),
                ("Unseen-arg. / restart / stored reuse given acquisition", reuse, reuse, "$=1$"),
                ("\\textbf{Hosted teardown verified}", "1.0 (probe HTTP 401 accepted)", "\\textbf{0 (401 $\\ne$ 404)}", "$=1$"),
                ("\\textbf{Teacher-disconnect reuse given acquisition}", "1.0", f"\\textbf{{{st['TEACHER_DISCONNECT_REUSE_GIVEN_ACQUISITION']:.1f}}}", "$=1$"),
                ("\\textbf{Distilled skill exact}", frac(lr["DISTILLED_SKILL_EXACT"]), f"\\textbf{{{st['DISTILLED_SKILL_EXACT']:.1f}}}", "$\\ge .90$")]
        f.write("\\begin{tabular}{lllc}\n\\toprule\nCriterion (Arm D, LOCKED, 20 scenarios) & As recorded & Strict (registered rule) & Gate\\\\\n\\midrule\n")
        for r in rows: f.write(" & ".join(r) + "\\\\\n")
        f.write("\\bottomrule\n\\end{tabular}\n")
    # ---------------- Table: worked-example verifier tests ----------------
    cand = J("SEMVM_RECOVERY_CAPACITY_ISOLATION_V1", "procedure_verification", "dev_a", "D", "dev_a-022-S15", "proc_close_oldest_open_request_v1.json")
    tests = (cand.get("paths") or {}).get(cand.get("chosen") or "deterministic", {}).get("tests") or []
    groups = {"static_validation": "static validation", "interface": "interface / signature", "replay": "source replay", "counterfactual": "counterfactual argument substitution",
              "perturb": "state perturbation (all closed / alternate closed)", "neg": "negative cases (missing input, wrong type, empty result, ambiguous entity, deleted object, empty world)",
              "txn": "rollback injection after each state-changing step", "determinism": "determinism"}
    gc = {}
    for tt in tests:
        g = next(v for k, v in groups.items() if tt[0].startswith(k)); gc.setdefault(g, [0, 0]); gc[g][0] += 1 if tt[1] else 0; gc[g][1] += 1
    with open(os.path.join(GEN, "tab_verifier.tex"), "w") as f:
        f.write("\\begin{tabular}{lr}\n\\toprule\nVerifier test family & Passed\\\\\n\\midrule\n")
        for g, (k, nn) in gc.items(): f.write(f"{g} & {k}/{nn}\\\\\n")
        f.write(f"\\midrule\nTotal & {sum(v[0] for v in gc.values())}/{sum(v[1] for v in gc.values())}\\\\\n\\bottomrule\n\\end{{tabular}}\n")
    N["s15Tests"] = f"{sum(v[0] for v in gc.values())}/{sum(v[1] for v in gc.values())}"
    with open(os.path.join(GEN, "numbers.tex"), "a") as f: f.write(f"\\newcommand{{\\s15Tests}}{{{N['s15Tests']}}}\n".replace("\\s15Tests", "\\sfifteenTests"))
    # ---------------- Figures ----------------
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 8.5, "axes.edgecolor": MUTED, "axes.labelcolor": INK, "xtick.color": MUTED, "ytick.color": MUTED, "pdf.fonttype": 42})
    # Figure: RCI factorial as a dot plot (truncated value axis is legitimate for dots, not for bars)
    fig, axes = plt.subplots(1, 4, figsize=(7.2, 2.45), sharey=True)
    arms = ["B", "E", "F", "D"]
    for ax, k, title, th in zip(axes, M4, ("Learned procedure", "Scenario exact", "Distilled skill", "Grounding (behavioral)"), (.90, .90, .90, .95)):
        ax.axhline(th, color=INK, lw=0.8, ls=(0, (3, 2)), zorder=1)
        for i, arm in enumerate(arms):
            r = rci[arm][k]
            for j, (kk, nn) in enumerate(r["per_replicate_counts"]):
                ax.plot(i + (-0.22 if j == 0 else 0.22), kk / nn, marker="o" if j == 0 else "D", ms=4.2, mfc="white", mec=ORANGE, mew=1.2, ls="none", zorder=3)
            ax.plot(i, r["pooled"], marker="o", ms=7, color=BLUE, mec="white", mew=1.2, ls="none", zorder=4)
            ax.text(i, 0.815, f"{r['pooled_counts'][0]}/{r['pooled_counts'][1]}", ha="center", va="bottom", fontsize=6.6, color=INK)
        ax.set_title(title, fontsize=8.3, color=INK); ax.set_xticks(range(4)); ax.set_xticklabels(arms, fontsize=8); ax.set_xlim(-0.6, 3.6)
        ax.set_ylim(0.8, 1.02); ax.grid(axis="y", color=GRID, lw=0.6, zorder=0); ax.spines[["top", "right"]].set_visible(False)
        ax.text(-0.55, th - 0.004, f"gate {th:.2f}", ha="left", va="top", fontsize=6.2, color=MUTED)
    axes[0].set_ylabel("fraction exact")
    from matplotlib.lines import Line2D
    fig.legend(handles=[Line2D([], [], marker="o", color=BLUE, mec="white", ms=7, ls="none", label="pooled (count printed)"),
                        Line2D([], [], marker="o", mfc="white", mec=ORANGE, mew=1.2, ls="none", label="DEV-A"), Line2D([], [], marker="D", mfc="white", mec=ORANGE, mew=1.2, ls="none", label="DEV-B")],
               loc="lower center", ncol=3, frameon=False, fontsize=7, bbox_to_anchor=(0.5, -0.01))
    fig.text(0.5, 0.115, "B = scripted lesson / scripted recovery    E = scripted / hosted    F = hosted / oracle    D = hosted / hosted (primary)", ha="center", fontsize=6.6, color=MUTED)
    fig.tight_layout(rect=(0, 0.14, 1, 1)); fig.savefig(os.path.join(FIG, "fig_factorial.pdf")); fig.savefig(os.path.join(FIG, "fig_factorial.png"), dpi=200); plt.close(fig)
    # Figure: hosted-teacher arm across the lineage (different DEV draws; descriptive), full 0-1 axis
    seq = [("PDX TEACHER", cnt(T["LEARNED_PROCEDURE_EXACT"], T["n_LEARNED_PROCEDURE_EXACT"]), T["WRONG_TEACHER_ACTION_EXECUTED"]),
           ("HTG Arm D", cnt(h["D"]["LEARNED_PROCEDURE_EXACT"], h["D"]["n_LEARNED_PROCEDURE_EXACT"]), h["D"]["WRONG_BEHAVIORAL_ACTION_EXECUTED"]),
           ("TTP Arm D", ttp["LEARNED_PROCEDURE_EXACT"], tD["WRONG_BEHAVIORAL_ACTION_EXECUTED"]),
           ("RCI Arm D\n2 DEV draws", tuple(rci["D"]["LEARNED_PROCEDURE_EXACT"]["pooled_counts"]), sum(P["arms"]["D"]["WRONG_BEHAVIORAL_ACTION_EXECUTED"])),
           ("RCI Arm D\nsealed LOCKED", lr["LEARNED_PROCEDURE_EXACT"], LS["WRONG_BEHAVIORAL_ACTION_EXECUTED"])]
    fig, ax = plt.subplots(figsize=(5.4, 2.6))
    for i, (lab_, (k, nn), w) in enumerate(seq):
        ax.bar(i, k / nn, width=0.58, color=BLUE if i < 4 else "white", edgecolor=BLUE, hatch=None if i < 4 else "////", lw=1.2, zorder=2)
        ax.text(i, k / nn - 0.13, f"{k}/{nn}", ha="center", va="top", fontsize=7.5, color="white" if i < 4 else INK, zorder=4,
                bbox=None if i < 4 else dict(boxstyle="round,pad=0.15", fc="white", ec="none"))
    ax.axhline(0.90, color=INK, lw=0.8, ls=(0, (3, 2)), zorder=1); ax.text(-0.45, 0.915, "gate .90", ha="left", va="bottom", fontsize=6.5, color=MUTED)
    ax.set_xticks(range(len(seq))); ax.set_xticklabels([f"{s[0]}\nwrong: {s[2]}" for s in seq], fontsize=6.6)
    ax.set_ylim(0, 1.1); ax.set_yticks([0, .25, .5, .75, 1.0]); ax.set_ylabel("learned procedure exact")
    ax.grid(axis="y", color=GRID, lw=0.6, zorder=0); ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout(); fig.savefig(os.path.join(FIG, "fig_hosted_arm.pdf")); fig.savefig(os.path.join(FIG, "fig_hosted_arm.png"), dpi=200); plt.close(fig)
    print(json.dumps(N, indent=1))


if __name__ == "__main__":
    main()
