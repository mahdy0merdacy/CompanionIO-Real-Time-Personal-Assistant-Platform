// src/app/core/services/language.service.ts
import { Injectable, inject } from '@angular/core';
import { TranslateService } from '@ngx-translate/core';
import { BehaviorSubject } from 'rxjs';

export type Language = 'fr' | 'en';

@Injectable({
  providedIn: 'root'
})
export class LanguageService {
  private translate = inject(TranslateService);
  private currentLangSubject = new BehaviorSubject<Language>('fr');
  currentLang$ = this.currentLangSubject.asObservable();

  constructor() {
    const savedLang = localStorage.getItem('language') as Language;
    const browserLang = this.translate.getBrowserLang() as Language;
    const defaultLang = savedLang || (browserLang === 'en' ? 'en' : 'fr');

    this.translate.setDefaultLang('fr');
    this.setLanguage(defaultLang);
  }

  setLanguage(lang: Language): void {
    this.translate.use(lang);
    this.currentLangSubject.next(lang);
    localStorage.setItem('language', lang);
    document.documentElement.lang = lang;
  }

  getCurrentLanguage(): Language {
    return this.currentLangSubject.value;
  }

  toggleLanguage(): void {
    const newLang = this.getCurrentLanguage() === 'fr' ? 'en' : 'fr';
    this.setLanguage(newLang);
  }
}
