class PcmCaptureProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this.targetRate = 16000;
    this.ratio = sampleRate / this.targetRate;
    this.offset = 0;
  }

  process(inputs) {
    const channel = inputs[0] && inputs[0][0];
    if (!channel || !channel.length) {
      return true;
    }
    const outCount = Math.floor((channel.length - this.offset) / this.ratio);
    if (outCount < 1) {
      this.offset -= channel.length;
      return true;
    }
    const pcm = new Int16Array(outCount);
    let sum = 0;
    let src = this.offset;
    for (let index = 0; index < outCount; index += 1) {
      const sampleIndex = Math.min(channel.length - 1, Math.floor(src));
      const sample = Math.max(-1, Math.min(1, channel[sampleIndex] ?? 0));
      pcm[index] = sample < 0 ? sample * 0x8000 : sample * 0x7fff;
      sum += sample * sample;
      src += this.ratio;
    }
    this.offset = src - channel.length;
    if (this.offset < 0) {
      this.offset = 0;
    }
    const rms = Math.sqrt(sum / outCount);
    this.port.postMessage({ pcm: pcm.buffer, rms }, [pcm.buffer]);
    return true;
  }
}

registerProcessor("pcm-capture", PcmCaptureProcessor);
