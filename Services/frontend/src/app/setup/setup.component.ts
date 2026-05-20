import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { AuthService } from '../core/services/auth.service';

interface DomainOption {
  id: string;
  name: string;
  description: string;
  icon: string;  // Changé de 'string' à 'string' mais maintenant contiendra du SVG
  selected: boolean;
}

@Component({
  selector: 'app-setup',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  templateUrl: './setup.component.html',
  styleUrls: ['./setup.component.css']
})
export class SetupComponent implements OnInit {
  private fb = inject(FormBuilder);
  private auth = inject(AuthService);
  private router = inject(Router);

  currentStep = 1;
  loading = false;
  error = '';

  domainOptions: DomainOption[] = [
    {
      id: 'Healthcare',
      name: 'Health & Wellness',
      description: 'Advice, nutrition, fitness and general health tracking',
      icon: 'health',
      selected: false
    },
    {
      id: 'Technology',
      name: 'Science & Technology',
      description: 'Development, programming, AI news and physics',
      icon: 'tech',
      selected: false
    },
    {
      id: 'Finance',
      name: 'Economy & Finance',
      description: 'Investments, cryptocurrencies, budgeting and stock market',
      icon: 'finance',
      selected: false
    },
    {
      id: 'General',
      name: 'General Knowledge & Leisure',
      description: 'Travel, cooking, history, art and everyday discussions',
      icon: 'general',
      selected: false
    }
  ];

  contactForm!: FormGroup;

  ngOnInit(): void {
    this.contactForm = this.fb.group({
      friend_email: ['', [Validators.required, Validators.email]],
      friend_phone: ['', [Validators.required, Validators.pattern(/^\+?[0-9\s\-]{8,15}$/)]]
    });

    this.auth.getProfile().subscribe({
      next: (profile) => {
        if (profile) {
          if (profile.friend_email) {
            this.contactForm.patchValue({ friend_email: profile.friend_email });
          }
          if (profile.friend_phone) {
            this.contactForm.patchValue({ friend_phone: profile.friend_phone });
          }
          if (profile.domains) {
            const selectedList = profile.domains.split(',');
            this.domainOptions.forEach(opt => {
              if (selectedList.includes(opt.id)) {
                opt.selected = true;
              }
            });
          }
        }
      }
    });
  }

  get friend_email() { return this.contactForm.get('friend_email')!; }
  get friend_phone() { return this.contactForm.get('friend_phone')!; }

  toggleDomain(domain: DomainOption): void {
    domain.selected = !domain.selected;
  }

  get isDomainSelected(): boolean {
    return this.domainOptions.some(d => d.selected);
  }

  nextStep(): void {
    if (this.currentStep === 1) {
      if (!this.isDomainSelected) {
        this.error = 'Veuillez sélectionner au moins un domaine de questions.';
        return;
      }
      this.error = '';
      this.currentStep = 2;
    }
  }

  prevStep(): void {
    this.currentStep = 1;
    this.error = '';
  }

  submit(): void {
    if (this.contactForm.invalid) {
      this.contactForm.markAllAsTouched();
      return;
    }

    this.loading = true;
    this.error = '';

    const selectedDomains = this.domainOptions
      .filter(d => d.selected)
      .map(d => d.id)
      .join(',');

    const payload = {
      friend_email: this.friend_email.value.trim(),
      friend_phone: this.friend_phone.value.trim(),
      domains: selectedDomains
    };

    this.auth.updateProfile(payload).subscribe({
      next: () => {
        this.router.navigate(['/chat']);
      },
      error: (err) => {
        this.error = err?.error?.detail ?? "Impossible d'enregistrer vos paramètres. Veuillez réessayer.";
        this.loading = false;
      }
    });
  }

  // Méthode pour obtenir l'icône SVG correspondante
  getDomainIcon(iconType: string): string {
    const icons = {
      health: `<svg width="28" height="28" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M12 2L3 6V12C3 16.2 6.8 20 12 22C17.2 20 21 16.2 21 12V6L12 2Z" stroke="currentColor" stroke-width="1.5" fill="none"/>
        <path d="M8 12H16" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
        <path d="M12 8V16" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
      </svg>`,
      tech: `<svg width="28" height="28" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <rect x="2" y="3" width="20" height="14" rx="2" stroke="currentColor" stroke-width="1.5" fill="none"/>
        <path d="M8 21H16" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
        <path d="M12 17V21" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
        <circle cx="12" cy="10" r="2" fill="currentColor" fill-opacity="0.5"/>
      </svg>`,
      finance: `<svg width="28" height="28" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M21 12V18C21 19.1 20.1 20 19 20H5C3.9 20 3 19.1 3 18V6C3 4.9 3.9 4 5 4H9" stroke="currentColor" stroke-width="1.5" fill="none"/>
        <path d="M15 4H21V10" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
        <path d="M21 4L15 10" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
        <path d="M12 12L16 8" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
      </svg>`,
      general: `<svg width="28" height="28" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="1.5" fill="none"/>
        <path d="M2 12H22" stroke="currentColor" stroke-width="1.5"/>
        <path d="M12 2C10 4 9 8 9 12C9 16 10 20 12 22" stroke="currentColor" stroke-width="1.5"/>
        <path d="M12 2C14 4 15 8 15 12C15 16 14 20 12 22" stroke="currentColor" stroke-width="1.5"/>
      </svg>`
    };
    return icons[iconType as keyof typeof icons] || icons.health;
  }
}
