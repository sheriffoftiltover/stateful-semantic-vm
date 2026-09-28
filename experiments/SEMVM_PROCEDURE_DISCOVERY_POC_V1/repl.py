"""Interactive procedure-learning shell. State persists in <dir>/world.sqlite + <dir>/procedures.sqlite (restart = just start again).
Requires the frozen LLM service for LLM proposals / REQUEST retrieval:  CUDA_VISIBLE_DEVICES=1 <llm-python> procedure/llm_service.py &
python repl.py [--dir my_session] [--no-llm]
Try:   NEW PERSON ...  | controlled assertions (binder) | SEMVM_CMD_V1 commands | step lines ($v = FIND CALL WHERE SELF.WHO=Alice ...)
       :teach name(person=Alice)  <steps>  :endteach   :accept name   RUN name person=Bob   REQUEST <request text>   :procedure name"""
import os, sys, json, argparse
ROOT = os.path.dirname(os.path.realpath(__file__)); sys.path[:0] = [os.path.join(ROOT, "procedure"), os.path.join(ROOT, "core")]
import system as SY


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dir", default=os.path.join(ROOT, "repl_session")); ap.add_argument("--no-llm", action="store_true"); ap.add_argument("--binder", action="store_true", help="parse controlled assertions with the frozen binder"); a = ap.parse_args()
    os.makedirs(a.dir, exist_ok=True); binder = None
    if a.binder:
        import binder as BN
        binder = BN.Binder()
    S = SY.System(os.path.join(a.dir, "world.sqlite"), os.path.join(a.dir, "procedures.sqlite"), os.path.join(a.dir, "learn"), use_llm=not a.no_llm, pipeline_mode="FULL" if binder else "GOLD_IR", binder=binder)
    print(__doc__); print("active procedures:", [p["name"] for p in S.lib.list_active()]); n = 0
    while True:
        try: line = input("teach> " if S.teach else "semvm> ").strip()
        except (EOFError, KeyboardInterrupt): break
        if not line: continue
        if line in (":quit", ":q"): break
        n += 1; r = S.process({"text": line}, f"repl:{n}", "repl"); print(f"  [{r['status']}] {r['response']}")
        if r.get("kind") == "discovery":
            for k, v in r["discovery"]["paths"].items(): print(f"    {k}: {v.get('status')}  {(v.get('program') or v.get('proposal') or '').splitlines()[0] if (v.get('program') or v.get('proposal')) else v.get('reason', '')}")
    S.close(); print("bye (state saved)")


if __name__ == "__main__":
    main()
