import {
  Component, OnInit, OnDestroy, inject,
  ViewChild, ElementRef, AfterViewChecked,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { Subscription } from 'rxjs';

import { AuthService } from '../core/services/auth.service';
import { OrchestratorService, ChatMessage, WsStatus } from '../core/services/orchestrator.service';
import { AiFaceService } from '../core/services/ai-face.service';
import { AiFaceComponent } from '../components/ai-face/ai-face.component';

@Component({
  selector: 'app-chat',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, AiFaceComponent],
  templateUrl: './chat.component.html',
  styleUrls: ['./chat.component.css'],
})
export class ChatComponent implements OnInit, OnDestroy, AfterViewChecked {
  auth   = inject(AuthService);
  orches = inject(OrchestratorService);
  face   = inject(AiFaceService);

  @ViewChild('messagesEnd') messagesEnd!: ElementRef<HTMLDivElement>;
  @ViewChild('textInput')  textInput!: ElementRef<HTMLTextAreaElement>;

  messages: ChatMessage[] = [];
  status: WsStatus = 'disconnected';
  volume = 0;
  inputText = '';
  inputMode: 'text' | 'voice' = 'text';
  ttsEnabled = true;

  private subs = new Subscription();
  private shouldScroll = false;

  get isRecording()  { return this.status === 'recording'; }
  get isProcessing() { return this.status === 'processing'; }
  get isSpeaking()   { return this.status === 'speaking'; }
  get isConnected()  {
    return ['connected', 'recording', 'processing', 'speaking'].includes(this.status);
  }

  get statusLabel(): string {
    switch (this.status) {
      case 'connecting':  return 'Connexion...';
      case 'connected':   return 'Connecté';
      case 'recording':   return 'Enregistrement...';
      case 'processing':  return 'Traitement...';
      case 'speaking':    return '🔊 Réponse vocale...';
      default:            return 'Déconnecté';
    }
  }

  get volumeBars(): number[] {
    return Array.from({ length: 7 }, (_, i) => {
      const threshold = (i + 1) / 7;
      return this.volume >= threshold ? 1 : Math.max(0.15, this.volume / threshold);
    });
  }

  ngOnInit(): void {
    this.subs.add(this.orches.messages$.subscribe(msgs => {
      this.messages = msgs;
      this.shouldScroll = true;
    }));
    this.subs.add(this.orches.status$.subscribe(s => {
      this.status = s;
      this.updateFaceState(s);
    }));
    this.subs.add(this.orches.volume$.subscribe(v => this.volume = v));
    this.subs.add(this.orches.ttsEnabled$.subscribe(v => this.ttsEnabled = v));
    this.orches.connect();
  }

  ngAfterViewChecked(): void {
    if (this.shouldScroll) {
      this.scrollToBottom();
      this.shouldScroll = false;
    }
  }

  ngOnDestroy(): void {
    this.subs.unsubscribe();
    this.orches.disconnect();
  }

  private updateFaceState(status: WsStatus): void {
    switch (status) {
      case 'recording':
        this.face.set('listening');
        break;
      case 'processing':
        this.face.set('thinking');
        break;
      case 'speaking':
        this.face.set('talking');
        break;
      default:
        this.face.set('idle');
    }
  }

  onKeyDown(e: KeyboardEvent): void {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      this.sendText();
    }
  }

  sendText(): void {
    const text = this.inputText.trim();
    if (!text || this.isProcessing || this.isSpeaking) return;
    this.orches.sendText(text);
    this.inputText = '';
  }

  async toggleRecording(): Promise<void> {
    if (this.isRecording) {
      this.orches.stopRecording();
    } else {
      try {
        await this.orches.startRecording();
      } catch {
        alert('Microphone inaccessible. Vérifiez les permissions.');
      }
    }
  }

  toggleTts(): void {
    this.orches.toggleTts();
  }

  setMode(mode: 'text' | 'voice'): void {
    this.inputMode = mode;
    if (mode === 'text' && this.isRecording) this.orches.stopRecording();
  }

  reconnect(): void { this.orches.connect(); }
  clearChat(): void { this.orches.clearMessages(); }
  logout(): void { this.auth.logout(); }

  formatTime(date: Date): string {
    return date.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
  }

  private scrollToBottom(): void {
    try { this.messagesEnd?.nativeElement.scrollIntoView({ behavior: 'smooth' }); } catch {}
  }

  tips = [
    'Quelle est la météo à Tunis ?',
    'Explique-moi le machine learning',
    'Dis-moi une blague',
    'Traduis "bonjour" en japonais',
  ];

  useTip(tip: string): void {
    this.inputText = tip;
    if (this.inputMode === 'voice') this.setMode('text');
  }
}
