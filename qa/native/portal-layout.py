"""Actual fonts, first action, two surfaces, narrow screens and 200% browser zoom."""
QA_CONTRACT = {'full': {'profile': 'public',
          'nativeRequired': False,
          'expectedChecks': ['actual200PercentZoom',
                             'app1280FirstActionVisible',
                             'app1280NoOverflow',
                             'app1920FirstActionVisible',
                             'app1920NoOverflow',
                             'app360FirstActionVisible',
                             'app360NoOverflow',
                             'app390FirstActionVisible',
                             'app390NoOverflow',
                             'app768FirstActionVisible',
                             'app768NoOverflow',
                             'controlsAtLeast44',
                             'fontFailureActuallyInjected',
                             'fontFailureStillReadable',
                             'keyboardFocusVisible',
                             'missingReducedMotionRuleRejected',
                             'noJsAlternativesPresent',
                             'noJsErrors',
                             'pleos1280FirstActionVisible',
                             'pleos1280NoOverflow',
                             'pleos1920FirstActionVisible',
                             'pleos1920NoOverflow',
                             'pleos360FirstActionVisible',
                             'pleos360NoOverflow',
                             'pleos390FirstActionVisible',
                             'pleos390NoOverflow',
                             'pleos768FirstActionVisible',
                             'pleos768NoOverflow',
                             'reducedMotionPreference',
                             'validNoJsLinkCount2',
                             'validNoJsLinkCount4',
                             'zoom200NoOverflow'],
          'safetyChecks': {},
          'inputs': ['demo-v2/app.js',
                     'demo-v2/audio-worklet.js',
                     'demo-v2/font.woff2',
                     'demo-v2/index.html',
                     'demo-v2/style.css',
                     'docs/pli-pleos-product-brief.pdf'],
          'fixtures': [],
          'effects': 'none',
          'resources': [['host-load', 'shared']],
          'executionKind': 'HOST_CONTRACT'}}
from pathlib import Path
import json,tempfile,math,hashlib,threading,mimetypes,urllib.request
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
from urllib.parse import urlsplit
from run_record import RunRecord
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[2];checks={};metrics={'viewports':[]};record=RunRecord(__file__,checks,metrics)
SHOT_DIR=record.dir/'screenshots';SHOT_DIR.mkdir(exist_ok=True)
class LayoutFixture(BaseHTTPRequestHandler):
 def log_message(self,*args):pass
 def do_GET(self):
  path=urlsplit(self.path).path
  if path=='/api/status':body=json.dumps({'app':{},'lease':{'busy':False},'runtime':{'phase':'ready'},'controlReady':False,'public':True,'profile':'public'}).encode();mime='application/json'
  elif path=='/api/preview':body=b'{"available":true,"type":"product-story","actualAppFootage":false,"current":false,"durationSeconds":32.5}';mime='application/json'
  elif path.startswith('/api/'):body=b'{}';mime='application/json'
  else:
   target=ROOT/'demo-v2'/('index.html'if path in {'/','/app','/pleos','/resources'}else path.lstrip('/'))
   if path=='/docs/pli-pleos-product-brief.pdf':target=ROOT/path.lstrip('/')
   if not target.is_file()or not target.resolve().is_relative_to(ROOT):self.send_error(404);return
   body=target.read_bytes();mime=mimetypes.guess_type(str(target))[0]or'application/octet-stream'
  self.send_response(200);self.send_header('Content-Type',mime);self.send_header('Content-Length',str(len(body)));self.end_headers()
  try:self.wfile.write(body)
  except (BrokenPipeError,ConnectionResetError):pass
server=ThreadingHTTPServer(('127.0.0.1',0),LayoutFixture);server.daemon_threads=True
threading.Thread(target=server.serve_forever,daemon=True).start();url='http://127.0.0.1:'+str(server.server_port)
def ready(page):page.locator('#page-title').wait_for(state='visible');page.evaluate('document.fonts.ready')
def reduced_applied(page):
 return page.evaluate("""()=>{const spinner=getComputedStyle($('loading-spinner'));const button=getComputedStyle($('connect'));return Math.max(...spinner.animationDuration.split(',').map(parseFloat))<=.001&&Math.max(...button.transitionDuration.split(',').map(parseFloat))<=.001;}""")
def usable_links(page):
 links=page.locator('noscript a').evaluate_all('(as)=>as.map(a=>a.href)')
 return bool(links)and all(urllib.request.urlopen(href,timeout=5).status==200 for href in links)

with sync_playwright()as p:
 b=p.chromium.launch(headless=True,channel='chrome');c=b.new_context(reduced_motion='reduce');v=c.new_page();errors=[];v.on('pageerror',lambda e:errors.append(str(e)))
 for path in ['/app','/pleos']:
  for width,height in [(360,800),(390,844),(768,1024),(1280,900),(1920,1080)]:
   v.set_viewport_size({'width':width,'height':height});v.goto(url+path);ready(v)
   tag=path[1:]+str(width);checks[tag+'NoOverflow']=v.evaluate('document.documentElement.scrollWidth<=innerWidth')
   first=v.locator('#claim-control'if path=='/pleos'else'#connect').bounding_box();metrics['viewports'].append({'surface':path,'width':width,'height':height,'actionBottom':round(first['y']+first['height'])})
   checks[tag+'FirstActionVisible']=first['y']+first['height']<=height
   if width==390 and path=='/app':v.screenshot(path=str(SHOT_DIR/'portal-mobile.png'),full_page=True)
   if width==1280 and path=='/pleos':v.screenshot(path=str(SHOT_DIR/'portal-desktop.png'),full_page=True)
 checks['reducedMotionPreference']=reduced_applied(v)
 negative=c.new_page();css=(ROOT/'demo-v2/style.css').read_text();negative.route('**/style.css*',lambda route:route.fulfill(body=css.split('@media(prefers-reduced-motion:reduce)')[0],content_type='text/css'));negative.goto(url+'/app');ready(negative);checks['missingReducedMotionRuleRejected']=not reduced_applied(negative);negative.close()
 checks['controlsAtLeast44']=v.locator('button:visible').evaluate_all('(bs)=>bs.every(b=>b.getBoundingClientRect().height>=44&&b.getBoundingClientRect().width>=44)')
 with tempfile.TemporaryDirectory(prefix='pli-zoom-')as folder:
  profile=Path(folder)/'Default';profile.mkdir();(profile/'Preferences').write_text(json.dumps({'partition':{'default_zoom_level':{'x':math.log(2)/math.log(1.2)}}}))
  z=p.chromium.launch_persistent_context(folder,channel='chrome',headless=True,viewport={'width':1280,'height':900});page=z.pages[0];page.goto(url+'/pleos');page.wait_for_timeout(1500)
  metrics['zoom200']=page.evaluate('({width:innerWidth,ratio:devicePixelRatio})');checks['actual200PercentZoom']=metrics['zoom200']=={'width':640,'ratio':2};checks['zoom200NoOverflow']=page.evaluate('document.documentElement.scrollWidth<=innerWidth');page.locator('nav a').first.focus();checks['keyboardFocusVisible']=page.locator('nav a').first.evaluate('(e)=>e===document.activeElement&&getComputedStyle(e).outlineStyle!=="none"');z.close()
 fallback=b.new_context();page=fallback.new_page();hits=[];page.route('**/*font.woff2*',lambda r:(hits.append(r.request.url),r.abort()));page.goto(url+'/app');page.evaluate('document.fonts.ready')
 metrics['fontBlockHits']=len(hits);checks['fontFailureActuallyInjected']=len(hits)>0 and page.evaluate("[...document.fonts].some(f=>f.family==='Pretendard'&&f.status==='error')");checks['fontFailureStillReadable']=page.locator('#page-title').is_visible()and page.evaluate('document.documentElement.scrollWidth<=innerWidth')
 nojs=b.new_context(java_script_enabled=False);page=nojs.new_page();page.goto(url+'/app');checks['noJsAlternativesPresent']=usable_links(page)
 for count in [2,4]:
  variant=nojs.new_page();html=(ROOT/'demo-v2/index.html').read_text();start=html.index('<noscript>');end=html.index('</noscript>',start)+len('</noscript>');alternative='<noscript>'+''.join('<a href="/docs/pli-pleos-product-brief.pdf">플리 소개</a>'for _ in range(count))+'</noscript>';variant.route('**/app',lambda route,request,html=html[:start]+alternative+html[end:]:route.fulfill(body=html,content_type='text/html'));variant.goto(url+'/app');checks['validNoJsLinkCount'+str(count)]=usable_links(variant);variant.close()
 checks['noJsErrors']=not errors;metrics['pageErrors']=errors;b.close()
server.shutdown();server.server_close()
metrics['screenshots']={str((SHOT_DIR/name).relative_to(ROOT)):hashlib.sha256((SHOT_DIR/name).read_bytes()).hexdigest()for name in ['portal-desktop.png','portal-mobile.png']}
print(json.dumps({'checks':checks,'metrics':metrics}));assert all(checks.values())
