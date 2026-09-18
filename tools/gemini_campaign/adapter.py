"""Injectable native-shaped adapter; no transport or credential is created here."""
from __future__ import annotations
from dataclasses import dataclass
from .config import MODEL_ID, THINKING_LEVEL, OUTPUT_LIMIT, CONTEXT_LIMIT, cost_microdollars
from .errors import AccountingHalt, PolicyError
from .ledger import Ledger

@dataclass(frozen=True)
class FunctionCall:
    name: str
    args: dict

@dataclass(frozen=True)
class ParsedResponse:
    text: str
    function_calls: tuple[FunctionCall, ...]
    thought_signatures: tuple[str, ...]
    finish_reason: str
    truncated: bool
    usage: dict
    model: str
    response_id: str


def parse_response(raw: dict) -> ParsedResponse:
    if not isinstance(raw, dict): raise AccountingHalt("response is not an object")
    usage=raw.get("usage")
    model=raw.get("model")
    response_id=raw.get("response_id") or raw.get("id")
    if not isinstance(usage,dict) or not isinstance(model,str) or not isinstance(response_id,str): raise AccountingHalt("response metadata is incomplete")
    required=('input_tokens','output_tokens','thought_tokens','cached_tokens')
    if any(not isinstance(usage.get(k),int) or usage[k] < 0 for k in required): raise AccountingHalt("response usage is incomplete")
    finish=raw.get('finish_reason')
    if not isinstance(finish,str) or not finish: raise AccountingHalt("response finish reason is missing")
    calls=[]
    for item in raw.get('function_calls',[]) or []:
        if not isinstance(item,dict) or not isinstance(item.get('name'),str) or not isinstance(item.get('args'),dict): raise AccountingHalt("invalid function call")
        calls.append(FunctionCall(item['name'],item['args']))
    text=raw.get('text','')
    if not isinstance(text,str): raise AccountingHalt("invalid response text")
    sigs=raw.get('thought_signatures',[]) or []
    if any(not isinstance(s,str) for s in sigs): raise AccountingHalt("invalid thought signature")
    return ParsedResponse(text,tuple(calls),tuple(sigs),finish,finish in {'MAX_TOKENS','LENGTH'},usage,model,response_id)

class Broker:
    def __init__(self, ledger: Ledger, transport): self.ledger, self.transport = ledger, transport
    def request(self, *, text: str, max_output_tokens: int, max_thought_tokens: int, metadata: dict, model=MODEL_ID, thinking_level=THINKING_LEVEL, retry_of=None):
        if model != MODEL_ID or thinking_level != THINKING_LEVEL: raise PolicyError("model or thinking policy rejected")
        if not isinstance(max_output_tokens,int) or max_output_tokens <= 0 or max_output_tokens > OUTPUT_LIMIT: raise PolicyError("explicit output bound rejected")
        if not isinstance(max_thought_tokens,int) or max_thought_tokens < 0 or max_thought_tokens > OUTPUT_LIMIT: raise PolicyError("thought bound rejected")
        if not isinstance(text,str): raise PolicyError("text rejected")
        from .estimator import estimate_text_tokens
        input_bound=estimate_text_tokens(text)
        if input_bound + max_output_tokens > CONTEXT_LIMIT: raise PolicyError("context bound rejected")
        reservation=cost_microdollars(input_bound,max_output_tokens,max_thought_tokens)
        r=self.ledger.reserve(model=model,thinking_level=thinking_level,reservation_microusd=reservation,retry_of=retry_of,**metadata)
        provider_request_id=r.request_id
        try:
            self.ledger.mark_dispatched(r.request_id,provider_request_id)
            raw=self.transport(text=text, model=model, thinking_level=thinking_level, max_output_tokens=max_output_tokens)
            parsed=parse_response(raw)
            self.ledger.settle(r.request_id, model=parsed.model, provider_response_id=parsed.response_id, finish_reason=parsed.finish_reason, response_bytes=b'', **parsed.usage)
            return parsed
        except (TimeoutError, AccountingHalt):
            raise
