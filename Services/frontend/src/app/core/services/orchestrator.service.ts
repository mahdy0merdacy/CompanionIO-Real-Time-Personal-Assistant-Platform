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

  // ── TTS playback state ────────────────────────────────────────────
  private ttsContext: AudioContext | null = null;
  private ttsQueue: ArrayBuffer[] = [];
  private ttsPlaying = false;
  private ttsReceiving = false;

  // ── TTS enabled toggle ───────────────────────────────────────────
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
  readonly dangerAlert$ = new BehaviorSubject<any | null>(null);

  private streamingMsgId: string | null = null;

  // FLAG: true = le prochain TRANSCRIPT: vient d'un sendText() → ignorer pour éviter la double bulle
  private skipNextTranscript = false;

  // ── Connection ──────────────────────────────────────────────────

  connect(): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) return;

    this.status$.next('connecting');
    this.dangerAlert$.next(null);

    const token = this.auth.token;
    const baseUrl = environment.orchestratorWsUrl;
    const url = token ? `${baseUrl}?token=${encodeURIComponent(token)}` : baseUrl;

    console.log(`[WS] Connecting to ${url}`);
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

    // 1. Affiche la bulle user immédiatement
    this.pushMessage({ role: 'user', content: text });

    // 2. Prépare la bulle IA vide en streaming
    const aiMsgId = this.uid();
    this.streamingMsgId = aiMsgId;
    this.pushMessage({ id: aiMsgId, role: 'ai', content: '', streaming: true });

    // 3. Indique à handleMessage() d'ignorer le prochain TRANSCRIPT: (évite la double bulle)
    this.skipNextTranscript = true;

    this.wasRecordingBeforeProcessing = false;
    this.status$.next('processing');

    // 4. Envoie au serveur
    this.ws.send(JSON.stringify({ type: 'text', data: text }));
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

  // ── TTS audio playback ────────────────────────────────────────────

  private handleAudioChunk(buffer: ArrayBuffer): void {
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
    // JSON structuré (danger_alert, etc.)
    try {
      const parsed = JSON.parse(data);
      if (parsed && parsed.type === 'danger_alert') {
        console.warn('[WS] 🚨 Danger alert received:', parsed.data);
        this.dangerAlert$.next(parsed.data);
        return;
      }
    } catch (e) {
      // pas du JSON — protocole texte normal
    }

    if (data.startsWith('TRANSCRIPT: ')) {
      const transcript = data.slice('TRANSCRIPT: '.length);

      // Si le message vient d'un sendText(), la bulle user est déjà affichée.
      // On ignore ce TRANSCRIPT pour éviter la double bulle,
      // mais on conserve le streamingMsgId déjà créé par sendText().
      if (this.skipNextTranscript) {
        console.log('[WS] Skipping duplicate TRANSCRIPT from text input');
        this.skipNextTranscript = false;
        // Ne pas re-créer de bulle — sendText() les a déjà créées
        return;
      }

      // Cas audio (STT) : push bulle user + bulle IA vide
      const id = this.uid();
      this.streamingMsgId = id;
      this.pushMessage({ role: 'user', content: transcript });
      this.pushMessage({ id, role: 'ai', content: '', streaming: true });
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

    // Token LLM streaming → append à la bulle IA en cours
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