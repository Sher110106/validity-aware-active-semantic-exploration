import os, stat, tempfile, threading, unittest
from tools.gemini_campaign.adapter import Broker, parse_response
from tools.gemini_campaign.config import MODEL_ID, THINKING_LEVEL, NORMAL_CEILING_MICROUSD
from tools.gemini_campaign.credentials import load_credential
from tools.gemini_campaign.errors import AccountingHalt, CredentialError, PolicyError
from tools.gemini_campaign.ledger import Ledger

META=dict(campaign_id='c',phase_id='p',run_id='r',stage_id='s',member_id='m',tool_turn_id='t',attempt_id='a')
class BrokerTests(unittest.TestCase):
 def ledger(self, ceiling=190_000_000, recovery=False):
  return Ledger(tempfile.mktemp(), ceiling, recovery)
 def test_concurrent_reservations_never_cross_ceiling(self):
  path=tempfile.mktemp(); out=[]
  def work(i):
   try: out.append(Ledger(path,1000,recovery_enabled=True).reserve(**{**META,'attempt_id':str(i)},model=MODEL_ID,thinking_level=THINKING_LEVEL,reservation_microusd=600))
   except AccountingHalt: pass
  ts=[threading.Thread(target=work,args=(i,)) for i in range(8)]
  [t.start() for t in ts]; [t.join() for t in ts]
  self.assertLessEqual(Ledger(path,1000,True).reserved_total(),1000); self.assertEqual(len(out),1)
 def test_timeout_and_missing_usage_keep_reservation(self):
  l=self.ledger(100000,True)
  def timeout(**_): raise TimeoutError()
  with self.assertRaises(TimeoutError): Broker(l,timeout).request(text='hello',max_output_tokens=10,max_thought_tokens=2,metadata=META)
  self.assertEqual(l.summary()['unresolved_requests'],1)
  def incomplete(**_): return {'model':MODEL_ID,'id':'x','finish_reason':'STOP','usage':{}}
  with self.assertRaises(AccountingHalt): Broker(l,incomplete).request(text='hello',max_output_tokens=10,max_thought_tokens=2,metadata={**META,'attempt_id':'b'})
  self.assertEqual(l.summary()['unresolved_requests'],2)
 def test_exact_policy_and_duplicate_settlement(self):
  l=self.ledger(100000,True)
  with self.assertRaises(PolicyError): Broker(l,lambda **_:{}).request(text='x',max_output_tokens=1,max_thought_tokens=0,metadata=META,model='other')
  r=l.reserve(**META,model=MODEL_ID,thinking_level=THINKING_LEVEL,reservation_microusd=100)
  l.settle(r.request_id,model=MODEL_ID,input_tokens=1,output_tokens=1,thought_tokens=0,cached_tokens=0,provider_response_id='resp',finish_reason='STOP')
  l.settle(r.request_id,model=MODEL_ID,input_tokens=1,output_tokens=1,thought_tokens=0,cached_tokens=0,provider_response_id='resp',finish_reason='STOP')
  with self.assertRaises(AccountingHalt): l.settle(r.request_id,model=MODEL_ID,input_tokens=1,output_tokens=1,thought_tokens=0,cached_tokens=0,provider_response_id='different',finish_reason='STOP')
 def test_ceiling_and_price_mismatch(self):
  l=self.ledger(100,True)
  with self.assertRaises(AccountingHalt): l.reserve(**META,model=MODEL_ID,thinking_level=THINKING_LEVEL,reservation_microusd=101)
  r=l.reserve(**META,model=MODEL_ID,thinking_level=THINKING_LEVEL,reservation_microusd=100)
  with self.assertRaises(AccountingHalt): l.settle(r.request_id,model=MODEL_ID,input_tokens=1000000,output_tokens=0,thought_tokens=0,cached_tokens=0,provider_response_id='r',finish_reason='STOP')
 def test_retry_is_a_new_reservation_and_model_mismatch_halts(self):
  l=self.ledger(1000,True)
  first=l.reserve(**META,model=MODEL_ID,thinking_level=THINKING_LEVEL,reservation_microusd=400)
  retry=l.reserve(**{**META,'attempt_id':'retry'},model=MODEL_ID,thinking_level=THINKING_LEVEL,reservation_microusd=400,retry_of=first.request_id)
  self.assertNotEqual(first.request_id,retry.request_id)
  with self.assertRaises(AccountingHalt): l.settle(first.request_id,model='wrong',input_tokens=1,output_tokens=1,thought_tokens=0,cached_tokens=0,provider_response_id='bad',finish_reason='STOP')
 def test_parser_and_no_reasoning_summary(self):
  p=parse_response({'text':'ok','function_calls':[{'name':'tool','args':{}}],'thought_signatures':['sig'],'finish_reason':'MAX_TOKENS','model':MODEL_ID,'id':'id','usage':{'input_tokens':1,'output_tokens':2,'thought_tokens':1,'cached_tokens':0}})
  self.assertEqual(p.function_calls[0].name,'tool'); self.assertTrue(p.truncated); self.assertEqual(p.thought_signatures,('sig',))

class CredentialTests(unittest.TestCase):
 def test_permission_and_generic_errors(self):
  p=tempfile.mktemp()
  with open(p,'w') as handle: handle.write('fake-key')
  os.chmod(p,0o644)
  with self.assertRaises(CredentialError) as error: load_credential(p)
  self.assertNotIn('fake-key', str(error.exception)); self.assertNotIn(p, str(error.exception))
  os.chmod(p,0o600); self.assertEqual(load_credential(p),'fake-key')
  os.chmod(p,0o600); os.unlink(p)
  with self.assertRaisesRegex(CredentialError,'unavailable'): load_credential(p)

if __name__=='__main__': unittest.main()
