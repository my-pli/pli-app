import fs from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';

const source = fs.readFileSync('demo-v2/app.js', 'utf8');
const oneLine = name => source.split('\n').find(line => line.startsWith(`async function ${name}(`) || line.startsWith(`function ${name}(`));
const connect = source.slice(source.indexOf('async function connectVoice(){'), source.indexOf('async function stopVoice('));
const deferred = () => { let resolve; const promise = new Promise(done => { resolve = done; }); return {promise, resolve}; };

function harness(stage) {
  const claim = deferred(), prepare = deferred(), entered = deferred(), requests = [], sockets = [];
  const track = {readyState: 'live', stop() { this.readyState = 'ended'; }};
  const stream = {getTracks: () => [track]};
  const node = () => ({connect() {}, disconnect() {}, port: {postMessage() {}}, frequency: {}, Q: {}});
  class Context {
    sampleRate = 48000;
    audioWorklet = {addModule: async () => {}};
    destination = {};
    async resume() {}
    async close() { this.closed = true; }
    createMediaStreamSource() { return node(); }
    createBiquadFilter() { return node(); }
  }
  class Socket {
    static OPEN = 1;
    readyState = 0;
    bufferedAmount = 0;
    constructor() {
      sockets.push(this);
      queueMicrotask(() => {
        if (this.readyState === 3) return;
        this.readyState = 1;
        this.onopen?.();
        this.onmessage?.({data: JSON.stringify({type: 'ready'})});
      });
    }
    send() {}
    close() { this.readyState = 3; this.onclose?.(); }
  }
  const box = {
    state: {voiceEpoch: 0, voice: false, connecting: false, ending: false, token: null, media: 'LIVE', surface: 'app', status: {app: {bootId: 'same', stateRevision: 10, phase: 'STOPPED'}}},
    window: {isSecureContext: true, AudioWorkletNode: class {}, AudioContext: Context},
    navigator: {mediaDevices: {getUserMedia: async () => stream}}, AudioContext: Context,
    AudioWorkletNode: class { constructor() { return node(); } }, WebSocket: Socket,
    location: {protocol: 'https:', host: 'fixture'}, setTimeout, clearTimeout,
    ctx: null, mic: null, voiceSocket: null, source: null, filter: null, duplex: null, controlSocket: null,
    render() {}, note() {}, connectControl() {}, poll: async () => {}, errorText: error => error.message,
    post: async (path, body = {}, timeout, token = box.state.token) => {
      requests.push({path, body, token});
      if (path.endsWith('/claim')) { if (stage === 'claim') { entered.resolve(); return claim.promise; } return {sessionToken: 'owned-token'}; }
      if (path.endsWith('/prepare')) { entered.resolve(); return prepare.promise; }
      if (path.endsWith('/end')) { box.state.status.app = {bootId: 'same', stateRevision: 11, phase: 'STOPPED'}; return {status: 'STOPPED'}; }
      return {};
    }
  };
  vm.createContext(box);
  vm.runInContext(`'use strict';\n${oneLine('acceptAppSnapshot')}\n${oneLine('cleanupAudio')}\n${oneLine('endSession')}\n${oneLine('stopVoice')}\n${connect}`, box);
  return {box, claim, prepare, entered, requests, sockets, track};
}

const late = harness('claim');
const lateStart = late.box.connectVoice();
await late.entered.promise;
await late.box.endSession();
late.claim.resolve({sessionToken: 'late-old-token'});
await lateStart;
assert.equal(late.requests.some(request => request.path.endsWith('/prepare')), false);
assert.equal(late.requests.find(request => request.path.endsWith('/end')).token, 'late-old-token');
assert.equal(late.box.state.token, null);
assert.equal(late.track.readyState, 'ended');
assert.equal(late.sockets.length, 0);

const preparing = harness('prepare');
const pending = preparing.box.connectVoice();
await preparing.entered.promise;
await new Promise(resolve => setImmediate(resolve));
await preparing.box.endSession();
preparing.prepare.resolve({app: {bootId: 'same', stateRevision: 9, phase: 'PREPARING'}});
await pending;
assert.equal(preparing.requests.some(request => request.path.endsWith('/begin')), false);
assert.equal(preparing.box.state.status.app.phase, 'STOPPED');
assert.equal(preparing.track.readyState, 'ended');
assert.equal(preparing.box.state.voice, false);
assert.ok(preparing.sockets.every(socket => socket.readyState === 3));
console.log(JSON.stringify({cancelledLateClaimCannotPrepareOrRetainLease: true, cancelledPreparationCannotBeginOrOverwriteStoppedState: true}));
