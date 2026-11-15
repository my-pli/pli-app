class PliDuplex extends AudioWorkletProcessor {
  constructor(options) {
    super();
    this.rate = options.processorOptions?.wireRate || 24000;
    this.ratio = sampleRate / this.rate;
    this.queue = []; this.offset = 0; this.queued = 0; this.phase = 0;
    this.mic = new Int16Array(this.rate / 25); this.used = 0; this.sum = 0; this.count = 0; this.muted = false;
    this.port.onmessage = ({data}) => {
      if (data.type === 'mute') { this.muted = data.value; return; }
      const pcm = new Int16Array(data);
      if (this.queued > this.rate / 2) { this.queue = []; this.offset = 0; this.queued = 0; this.phase = 0; }
      this.queue.push(pcm); this.queued += pcm.length;
    };
  }
  process(inputs, outputs) {
    const output = outputs[0][0], input = inputs[0]?.[0];
    for (let i = 0; i < output.length; i++) {
      const first = this.queue[0];
      if (first) {
        const a = first[this.offset], b = first[this.offset+1] ?? this.queue[1]?.[0] ?? a;
        output[i] = (a + (b-a)*this.phase) / 32768;
        this.phase += 1 / this.ratio;
        if (this.phase >= 1) {
          this.phase -= 1; this.offset++; this.queued--;
          if (this.offset >= first.length) { this.queue.shift(); this.offset = 0; }
        }
      } else { output[i] = 0; this.phase = 0; }
      this.sum += this.muted ? 0 : (input?.[i] || 0); this.count++;
      if (this.count >= this.ratio) {
        const value = Math.max(-1, Math.min(1, this.sum/this.count)); this.sum = 0; this.count = 0;
        this.mic[this.used++] = value < 0 ? value*32768 : value*32767;
        if (this.used === this.mic.length) {
          const buffer = this.mic.buffer; this.port.postMessage(buffer,[buffer]);
          this.mic = new Int16Array(this.rate/25); this.used = 0;
        }
      }
    }
    return true;
  }
}
registerProcessor('pli-duplex', PliDuplex);
