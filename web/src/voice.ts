// Record the microphone as 16-bit mono WAV at 16 kHz, the format Muse Voice Transcribe takes.

const RATE = 16000

export type Recording = { stop: () => Promise<Blob> }

export async function record(): Promise<Recording> {
  const stream = await navigator.mediaDevices.getUserMedia({ audio: { channelCount: 1 } })
  const ctx = new AudioContext({ sampleRate: RATE })
  const source = ctx.createMediaStreamSource(stream)
  // ScriptProcessor is deprecated but needs no separate worklet file; a few seconds of speech is fine
  const node = ctx.createScriptProcessor(4096, 1, 1)
  const chunks: Float32Array[] = []
  node.onaudioprocess = e => chunks.push(new Float32Array(e.inputBuffer.getChannelData(0)))
  source.connect(node)
  node.connect(ctx.destination)
  return {
    stop: async () => {
      node.disconnect()
      source.disconnect()
      stream.getTracks().forEach(t => t.stop())
      await ctx.close()
      return wav(chunks)
    },
  }
}

function wav(chunks: Float32Array[]): Blob {
  const n = chunks.reduce((k, c) => k + c.length, 0)
  const buf = new DataView(new ArrayBuffer(44 + n * 2))
  const text = (at: number, s: string) => [...s].forEach((ch, i) => buf.setUint8(at + i, ch.charCodeAt(0)))
  text(0, 'RIFF'); buf.setUint32(4, 36 + n * 2, true); text(8, 'WAVE')
  text(12, 'fmt '); buf.setUint32(16, 16, true); buf.setUint16(20, 1, true); buf.setUint16(22, 1, true)
  buf.setUint32(24, RATE, true); buf.setUint32(28, RATE * 2, true); buf.setUint16(32, 2, true); buf.setUint16(34, 16, true)
  text(36, 'data'); buf.setUint32(40, n * 2, true)
  let at = 44
  for (const c of chunks) for (const v of c) {
    buf.setInt16(at, Math.max(-1, Math.min(1, v)) * 0x7fff, true)
    at += 2
  }
  return new Blob([buf], { type: 'audio/wav' })
}
