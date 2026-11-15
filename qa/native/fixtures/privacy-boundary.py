"""Synthetic private sentinel through the actual router and status/socket serializers."""
import asyncio,importlib.util,json,sys,types,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'scripts'))
def verify():
 os.environ.setdefault('PLI_TAILSCALE_IP','100.64.0.42')
 spec=importlib.util.spec_from_file_location('pli_privacy_probe',ROOT/'scripts/demo-server.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 from aiohttp.test_utils import make_mocked_request
 marker='PRIVATE_SENTINEL_8fa2';module.native={'demo':False,'profile':{'name':marker},'speech':marker,'facts':[marker],'sessionId':marker};module.native_updated=0;module.public_display=types.SimpleNamespace(latest=None);module.public_config=lambda:{'enabled':True,'url':'https://public.example'}
 module.runtime_state=lambda:{};module.cached={'process':'fixture'};module.lease_info=lambda request:{'busy':False};module.origin=lambda request:'https://public.example'
 def context(profile):return types.SimpleNamespace(profile=profile,assert_owned=lambda:123)
 def request(host,remote,path='/api/status'):
  value=make_mocked_request('GET',path,headers={'Host':host});value._cache['remote']=remote;return value
 async def main():
  values={}
  module.CONTEXT=context('public')
  response=await module.boundaries(request(module.PUBLIC_MARKER,'127.0.0.1'),module.status);data=json.loads(response.body);values['public']=data.get('profile')=='public'and data.get('app')=={}and marker not in response.text
  module.CONTEXT=context('personal');forwarded=[]
  async def forward(req,origin):
   forwarded.append(req.path);prior=module.CONTEXT;module.CONTEXT=context('public')
   try:return await module.status(req)
   finally:module.CONTEXT=prior
  module.forward_public=forward
  response=await module.boundaries(request(module.IP,module.IP),module.status);values['tailnet']=forwarded==['/api/status']and marker not in response.text and json.loads(response.body).get('app')=={}
  response=await module.boundaries(request('127.0.0.1','127.0.0.1','/api/personal/status'),module.status);values['ownerPositive']=marker in response.text
  values['socket']=module.public_app_snapshot(module.native)=={}
  # Correct outer profile alone cannot satisfy this predicate.
  values['labelOnlyRejected']=not(data.get('profile')=='public'and marker not in json.dumps({**data,'app':{'speech':marker}}))
  return values
 return asyncio.run(main())
if __name__=='__main__':print(json.dumps(verify()))
