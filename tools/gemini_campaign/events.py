"""Append-only sanitized event JSONL; payloads are allowlisted, not serialized wholesale."""
from __future__ import annotations
import json, os, time
_ALLOWED={'event','request_id','campaign_id','phase_id','run_id','stage_id','member_id','tool_turn_id','attempt_id','model','thinking_level','state','finish_reason','response_id','error_code','timestamp'}

def append_event(path: str, event: dict):
    safe={k:event[k] for k in _ALLOWED if k in event}
    safe['timestamp']=safe.get('timestamp',time.time())
    line=json.dumps(safe,sort_keys=True,separators=(',',':'))+'\n'
    with open(path,'a',encoding='utf-8') as f:
        f.write(line); f.flush(); os.fsync(f.fileno())
