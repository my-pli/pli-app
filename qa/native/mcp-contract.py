QA_CONTRACT = {'full': {'profile': None,
          'nativeRequired': False,
          'expectedChecks': ['mcpAdapterCases'],
          'safetyChecks': {},
          'inputs': ['qa/native/mcp-contract.mjs',
                     'scripts/kidsnote_mcp/site.mjs',
                     'scripts/kidsnote_mcp/sync.mjs',
                     'scripts/kidsnote_mcp/voice.mjs'],
          'fixtures': [],
          'effects': 'none',
          'resources': [['host-load', 'shared']],
          'executionKind': 'MCP_FIXTURE'}}
from pathlib import Path
import json,subprocess
from run_record import RunRecord
ROOT=Path(__file__).resolve().parents[2];checks={};metrics={};record=RunRecord(__file__,checks,metrics,dependencies=["qa/native/mcp-contract.mjs"])
p=subprocess.run(['node',str(ROOT/'qa/native/mcp-contract.mjs')],capture_output=True,text=True)
if p.returncode:raise AssertionError(p.stderr[:700])
cases=json.loads(p.stdout);metrics['adapterCases']=cases;checks['mcpAdapterCases']=bool(cases)and all(x is True for x in cases.values())
print(json.dumps({'checks':checks,'metrics':metrics}));assert all(checks.values())
