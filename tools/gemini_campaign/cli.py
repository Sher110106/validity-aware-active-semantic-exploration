from __future__ import annotations
import argparse, json
from .ledger import Ledger
from .config import MODEL_ID, THINKING_LEVEL, PROBE_CAP_MICROUSD

def main(argv=None):
    p=argparse.ArgumentParser(prog='gemini-campaign')
    sub=p.add_subparsers(dest='command',required=True)
    for name in ('summary','export','checksum'):
        q=sub.add_parser(name); q.add_argument('db')
    q=sub.add_parser('probe'); q.add_argument('--paid-enable',action='store_true'); q.add_argument('--db')
    a=p.parse_args(argv)
    if a.command=='probe':
        if not a.paid_enable: print(json.dumps({'dry_run':True,'paid_invocation':False,'model':MODEL_ID,'thinking_level':THINKING_LEVEL,'cap_microusd':PROBE_CAP_MICROUSD,'tests':['model','thinking','function_calling','structured_output','truncation','usage']})); return 0
        raise SystemExit('paid probes are disabled in this branch')
    l=Ledger(a.db)
    try: print(json.dumps(getattr(l,a.command)(),sort_keys=True,default=str))
    finally: l.close()
    return 0
if __name__=='__main__': raise SystemExit(main())
