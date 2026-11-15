"""Old cleanup cannot launch commands or issue HTTP mutations after stop/start."""
from pathlib import Path
import os,sys,tempfile,subprocess,threading,json,urllib.request,signal
ROOT=Path(__file__).resolve().parents[3];sys.path[:0]=[str(ROOT/'qa/native'),str(ROOT/'scripts')]
from run_record import RunRecord
from runtime_context import runtime_intent,set_runtime_intent
with tempfile.TemporaryDirectory(prefix='pli-intent-revoke-')as folder:
 record=object.__new__(RunRecord);record.intent_dir=Path(folder);record.intent=runtime_intent(folder);record.done=True;record.finalized=threading.Event();record.finalized.set();record.install_intent_guard()
 set_runtime_intent(folder,'paused');set_runtime_intent(folder,'running');checks={}
 for key,call in [('supersededCleanupCannotSpawn',lambda:subprocess.run([sys.executable,'-c','raise SystemExit(99)'])),('supersededCleanupCannotSendMutation',lambda:urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:1/old-cleanup',data=b'{}'),timeout=1)),('supersededCleanupCannotKillAnotherProcess',lambda:os.kill(99999999,signal.SIGTERM))]:
  try:call();checks[key]=False
  except RuntimeError as e:checks[key]=str(e)=='RUNTIME_INTENT_CHANGED'
 print(json.dumps(checks));assert all(checks.values())
