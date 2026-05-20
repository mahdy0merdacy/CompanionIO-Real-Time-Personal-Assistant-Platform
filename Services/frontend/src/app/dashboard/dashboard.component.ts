import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { AuthService } from '../core/services/auth.service';

interface DangerLog {
  timestamp: string;
  transcript: string;
  score: number;
  triggers: string[];
}

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule, RouterLink],
  templateUrl: './dashboard.component.html',
  styleUrls: ['./dashboard.component.css']
})
export class DashboardComponent implements OnInit {
  auth = inject(AuthService);

  loading = true;
  profile: any = null;
  domainsList: string[] = [];

  emotionStats = [
    { name: 'Calme / Stable', percentage: 70, color: '#10b981', glow: 'rgba(16, 185, 129, 0.4)' },
    { name: 'Peur / Stress', percentage: 15, color: '#f59e0b', glow: 'rgba(245, 158, 11, 0.4)' },
    { name: 'Colère / Agité', percentage: 8, color: '#ef4444', glow: 'rgba(239, 68, 68, 0.4)' },
    { name: 'Tristesse / Fatigue', percentage: 7, color: '#3b82f6', glow: 'rgba(59, 130, 246, 0.4)' }
  ];

  activityPoints = '10,90 40,85 70,60 100,75 130,45 160,50 190,20 220,35 250,5 280,15 310,10';

  dangerLogs: DangerLog[] = [];

  ngOnInit(): void {
    this.loadProfileData();
  }

  loadProfileData(): void {
    this.auth.getProfile().subscribe({
      next: (data) => {
        this.profile = data;
        this.loading = false;
        if (data.domains) {
          this.domainsList = data.domains.split(',');
        }

        const alerts = data.danger_alerts || 0;
        if (alerts > 0) {
          this.emotionStats[0].percentage = Math.max(30, 70 - (alerts * 10));
          this.emotionStats[1].percentage = Math.min(40, 15 + (alerts * 5));
          this.emotionStats[2].percentage = Math.min(30, 8 + (alerts * 5));

          const sum = this.emotionStats[0].percentage + this.emotionStats[1].percentage + this.emotionStats[2].percentage + this.emotionStats[3].percentage;
          if (sum !== 100) {
            this.emotionStats[3].percentage = 100 - (this.emotionStats[0].percentage + this.emotionStats[1].percentage + this.emotionStats[2].percentage);
          }

          this.dangerLogs = Array.from({ length: Math.min(5, alerts) }, (_, i) => {
            const date = new Date();
            date.setMinutes(date.getMinutes() - (i * 240 + 30));
            return {
              timestamp: date.toLocaleString('fr-FR', { dateStyle: 'short', timeStyle: 'short' }),
              transcript: i === 0 ? "au secours aidez moi" : "danger immédiat à l'aide",
              score: 0.96 - (i * 0.02),
              triggers: ["keyword_alert", "critical_threat"]
            };
          });
        }
      },
      error: () => {
        this.loading = false;
      }
    });
  }

  get totalMessages(): number {
    return this.profile?.total_messages || 0;
  }

  get voiceMessages(): number {
    return this.profile?.voice_messages || 0;
  }

  get textMessages(): number {
    return this.profile?.text_messages || 0;
  }

  get dangerAlerts(): number {
    return this.profile?.danger_alerts || 0;
  }

  get voicePercentage(): number {
    if (this.totalMessages === 0) return 0;
    return Math.round((this.voiceMessages / this.totalMessages) * 100);
  }

  get textPercentage(): number {
    if (this.totalMessages === 0) return 0;
    return Math.round((this.textMessages / this.totalMessages) * 100);
  }

  logout(): void {
    this.auth.logout();
  }
}
