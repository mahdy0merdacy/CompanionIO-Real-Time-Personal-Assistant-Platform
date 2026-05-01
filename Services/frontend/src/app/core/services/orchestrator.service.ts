import { Injectable, inject } from '@angular/core';
import { BehaviorSubject } from 'rxjs';
import { environment } from '../../../environments/environment';
import { AuthService } from './auth.service';

export type WsStatus = 'disconnected' | 'connecting' | 'connected' | 'recording' | 'processing' | 'speaking';

export interface ChatMessage {
  id: string;
  role: 'user' | 'ai';
  content: string;
  transcript?: string;
  streaming?: boolean;
  time: Date;
}

@Injectable({ providedIn: 'root' })
export class OrchestratorService {
  private auth = inject(AuthService);

  private ws: WebSocket | null = null;
  private audioContext: AudioContext | null = null;
  private scriptProcessor: ScriptProcessorNode | null = null;
  private mediaStream: MediaStream | null = null;
  private analyser: AnalyserNode | null = null;
  private volumeInterval: ReturnType<typeof setInterval> | null = null;
  private wasRecordingBeforeProcessing = false;

  // ── TTS playback state (unchanged from working version) ──────────
  private ttsContext: AudioContext | null = null;
  private ttsQueue: ArrayBuffer[] = [];
  private ttsPlaying = false;
  private ttsReceiving = false;

  // ── NEW: TTS enabled toggle ──────────────────────────────────────
  readonly ttsEnabled$ = new BehaviorSubject<boolean>(
    localStorage.getItem('ttsEnabled') !== 'false'
  );

  toggleTts(): void {
    const next = !this.ttsEnabled$.value;
    this.ttsEnabled$.next(next);
    localStorage.setItem('ttsEnabled', String(next));
  }

  readonly status$ = new BehaviorSubject<WsStatus>('disconnected');
  readonly messages$ = new BehaviorSubject<ChatMessage[]>([]);
  readonly volume$ = new BehaviorSubject<number>(0);

  private streamingMsgId: string | null = null;

  // ── Connection ──────────────────────────────────────────────────

  connect(): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) return;

    this.status$.next('connecting');
    const url = environment.orchestratorWsUrl;
    this.ws = new WebSocket(url);
    this.ws.binaryType = 'arraybuffer';

    this.ws.onopen = () => {
      console.log('[WS] Connected to orchestrator');
      this.status$.next('connected');
    };

    this.ws.onmessage = (ev) => {
      if (ev.data instanceof ArrayBuffer) {
        this.handleAudioChunk(ev.data);
      } else {
        this.handleMessage(ev.data as string);
      }
    };

    this.ws.onerror = (err) => {
      console.error('[WS] Error', err);
      this.status$.next('disconnected');
    };

    this.ws.onclose = () => {
      console.log('[WS] Disconnected');
      if (this.status$.value !== 'disconnected') {
        this.status$.next('disconnected');
      }
    };
  }

  disconnect(): void {
    this.stopRecording();
    this.ws?.close();
    this.ws = null;
    this.status$.next('disconnected');
  }

  // ── Text mode ───────────────────────────────────────────────────

  sendText(text: string): void {
    if (!text.trim() || !this.ws || this.ws.readyState !== WebSocket.OPEN) return;
    this.pushMessage({ role: 'user', content: text });
    this.sendTextToLLM(text);
  }

  // ── Audio / mic mode ─────────────────────────────────────────────

  async startRecording(): Promise<void> {
    if (this.status$.value === 'recording') return;
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) this.connect();

    try {
      this.mediaStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          sampleRate: 16000,
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
        }
      });

      this.audioContext = new AudioContext({ sampleRate: 16000 });
      const source = this.audioContext.createMediaStreamSource(this.mediaStream);

      this.analyser = this.audioContext.createAnalyser();
      this.analyser.fftSize = 256;
      source.connect(this.analyser);
      this.startVolumeMonitor();

      this.scriptProcessor = this.audioContext.createScriptProcessor(4096, 1, 1);
      this.scriptProcessor.onaudioprocess = (event) => {
        if (this.ws?.readyState !== WebSocket.OPEN) return;
        const float32 = event.inputBuffer.getChannelData(0);
        const int16 = new Int16Array(float32.length);
        for (let i = 0; i < float32.length; i++) {
          int16[i] = Math.max(-32768, Math.min(32767, float32[i] * 32767));
        }
        this.ws!.send(int16.buffer);
      };

      source.connect(this.scriptProcessor);
      this.scriptProcessor.connect(this.audioContext.destination);

      this.status$.next('recording');
      console.log('[MIC] ✅ Recording started — sending raw PCM16 at 16kHz');
    } catch (err) {
      console.error('[MIC] Error accessing microphone', err);
      throw err;
    }
  }

  stopRecording(): void {
    if (this.scriptProcessor) {
      this.scriptProcessor.disconnect();
      this.scriptProcessor.onaudioprocess = null;
      this.scriptProcessor = null;
    }
    if (this.mediaStream) {
      this.mediaStream.getTracks().forEach(t => t.stop());
      this.mediaStream = null;
    }
    if (this.volumeInterval) {
      clearInterval(this.volumeInterval);
      this.volumeInterval = null;
    }
    this.audioContext?.close();
    this.audioContext = null;
    this.analyser = null;
    this.volume$.next(0);

    if (this.status$.value === 'recording') this.status$.next('connected');
    console.log('[MIC] Recording stopped');
  }

  // ── TTS audio playback (exact same logic as working version) ──────

  private handleAudioChunk(buffer: ArrayBuffer): void {
    // NEW: skip if TTS disabled
    if (!this.ttsEnabled$.value) return;
    if (!this.ttsReceiving) return;
    this.ttsQueue.push(buffer);
    if (!this.ttsPlaying) {
      this.playNextChunk();
    }
  }

  private async playNextChunk(): Promise<void> {
    if (this.ttsQueue.length === 0) {
      this.ttsPlaying = false;
      if (!this.ttsReceiving) {
        this.status$.next(
          this.wasRecordingBeforeProcessing && this.scriptProcessor !== null
            ? 'recording'
            : 'connected'
        );
      }
      return;
    }

    this.ttsPlaying = true;
    const buffer = this.ttsQueue.shift()!;

    try {
      if (!this.ttsContext || this.ttsContext.state === 'closed') {
        this.ttsContext = new AudioContext({ sampleRate: 24000 });
      }

      // ✅ Resume if suspended (browser autoplay policy)
      if (this.ttsContext.state === 'suspended') {
        await this.ttsContext.resume();
      }

      const int16 = new Int16Array(buffer);
      const float32 = new Float32Array(int16.length);
      for (let i = 0; i < int16.length; i++) {
        float32[i] = int16[i] / 32768;
      }

      const audioBuffer = this.ttsContext.createBuffer(1, float32.length, 24000);
      audioBuffer.copyToChannel(float32, 0);

      const source = this.ttsContext.createBufferSource();
      source.buffer = audioBuffer;
      source.connect(this.ttsContext.destination);
      source.onended = () => this.playNextChunk();
      source.start();
    } catch (err) {
      console.error('[TTS PLAY] Error playing chunk:', err);
      this.playNextChunk();
    }
  }

  // ── Message handling ──────────────────────────────────────────────

  private handleMessage(data: string): void {
    if (data.startsWith('TRANSCRIPT: ')) {
      const transcript = data.slice('TRANSCRIPT: '.length);
      const id = this.uid();
      this.streamingMsgId = id;
      this.pushMessage({ id, role: 'ai', content: '', transcript, streaming: true });
      this.wasRecordingBeforeProcessing = this.status$.value === 'recording';
      this.status$.next('processing');
      return;
    }

    if (data === '__TURN_END__') {
      this.finaliseStreaming();
      setTimeout(() => {
        if (this.status$.value === 'processing') {
          this.status$.next(
            this.wasRecordingBeforeProcessing && this.scriptProcessor !== null
              ? 'recording'
              : 'connected'
          );
        }
      }, 300);
      return;
    }

    if (data === '__AUDIO_START__') {
      // NEW: skip if TTS disabled
      if (!this.ttsEnabled$.value) {
        console.log('[TTS] Skipped — TTS disabled');
        return;
      }
      console.log('[TTS] 🔊 Audio stream starting');
      this.ttsReceiving = true;
      this.ttsQueue = [];
      this.ttsPlaying = false;
      this.status$.next('speaking');
      return;
    }

    if (data === '__AUDIO_END__') {
      console.log('[TTS] 🔇 Audio stream ended');
      this.ttsReceiving = false;
      if (!this.ttsPlaying && this.ttsQueue.length === 0) {
        this.status$.next(
          this.wasRecordingBeforeProcessing && this.scriptProcessor !== null
            ? 'recording'
            : 'connected'
        );
      }
      return;
    }

    // LLM streaming token
    if (this.streamingMsgId) {
      this.appendToken(this.streamingMsgId, data);
    }
  }

  // ── Helpers ───────────────────────────────────────────────────────

  private pushMessage(partial: Partial<ChatMessage> & { role: 'user' | 'ai'; content: string }): void {
    const msg: ChatMessage = {
      id: partial.id ?? this.uid(),
      role: partial.role,
      content: partial.content,
      transcript: partial.transcript,
      streaming: partial.streaming ?? false,
      time: new Date(),
    };
    this.messages$.next([...this.messages$.value, msg]);
  }

  private appendToken(id: string, token: string): void {
    const msgs = this.messages$.value.map(m =>
      m.id === id ? { ...m, content: m.content + token } : m
    );
    this.messages$.next(msgs);
  }

  private finaliseStreaming(): void {
    if (!this.streamingMsgId) return;
    const msgs = this.messages$.value.map(m =>
      m.id === this.streamingMsgId ? { ...m, streaming: false } : m
    );
    this.messages$.next(msgs);
    this.streamingMsgId = null;
  }

  // ── Text-to-LLM direct path ──────────────────────────────────────

  private llmWs: WebSocket | null = null;
  private textMsgId: string | null = null;

  private sendTextToLLM(text: string): void {
    const llmUrl = environment.orchestratorWsUrl
      .replace('/ws/session', '')
      .replace(':8000', ':8002')
      + '/llm';

    const id = this.uid();
    this.textMsgId = id;
    this.pushMessage({ id, role: 'ai', content: '', streaming: true });
    this.status$.next('processing');

    if (this.llmWs && this.llmWs.readyState === WebSocket.OPEN) {
      this.llmWs.send(text);
      return;
    }

    this.llmWs = new WebSocket(llmUrl);
    this.llmWs.onopen = () => this.llmWs!.send(text);
    this.llmWs.onmessage = (ev) => {
      const token: string = ev.data;
      if (token === '<END>') {
        if (this.textMsgId) {
          const msgs = this.messages$.value.map(m =>
            m.id === this.textMsgId ? { ...m, streaming: false } : m
          );
          this.messages$.next(msgs);
          this.textMsgId = null;
        }
        this.status$.next('connected');
      } else if (this.textMsgId) {
        this.appendToken(this.textMsgId, token);
      }
    };
    this.llmWs.onerror = () => this.status$.next('connected');
  }

  // ── Volume monitor ────────────────────────────────────────────────

  private startVolumeMonitor(): void {
    const buf = new Uint8Array(this.analyser!.frequencyBinCount);
    this.volumeInterval = setInterval(() => {
      this.analyser?.getByteFrequencyData(buf);
      const avg = buf.reduce((a, b) => a + b, 0) / buf.length;
      this.volume$.next(avg / 128);
    }, 80);
  }

  private uid(): string {
    return Math.random().toString(36).slice(2, 10);
  }

  clearMessages(): void {
    this.messages$.next([]);
  }
}
