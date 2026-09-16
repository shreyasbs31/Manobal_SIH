class PcmCaptureProcessor extends AudioWorkletProcessor {
  process(inputs) {
    const channel = inputs[0] && inputs[0][0];
    if (channel && channel.length) {
      const pcm = new Int16Array(channel.length);
      for (let index = 0; index < channel.length; index += 1) {
        const sample = Math.max(-1, Math.min(1, channel[index] ?? 0));
        pcm[index] = sample < 0 ? sample * 0x8000 : sample * 0x7fff;
      }
      let sum = 0;
      for (let index = 0; index < channel.length; index += 1) {
        const sample = channel[index] ?? 0;
        sum += sample * sample;
      }
      const rms = Math.sqrt(sum / channel.length);
      this.port.postMessage({ pcm: pcm.buffer, rms }, [pcm.buffer]);
    }
    return true;
  }
}

registerProcessor("pcm-capture", PcmCaptureProcessor);
