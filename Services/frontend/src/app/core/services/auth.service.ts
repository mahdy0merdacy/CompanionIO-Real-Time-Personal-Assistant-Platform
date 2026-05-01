import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { BehaviorSubject, Observable, tap } from 'rxjs';
import { environment } from '../../../environments/environment';

export interface AuthUser {
  username: string;
  token: string;
}

interface AuthResponse {
  access_token: string;
  token_type: string;
  username: string;
}

@Injectable({ providedIn: 'root' })
export class AuthService {
  private http = inject(HttpClient);
  private router = inject(Router);

  private _user = new BehaviorSubject<AuthUser | null>(this.loadUser());
  readonly user$ = this._user.asObservable();

  get currentUser(): AuthUser | null { return this._user.value; }
  get isLoggedIn(): boolean { return !!this._user.value; }
  get token(): string | null { return this._user.value?.token ?? null; }

  register(email: string, username: string, password: string): Observable<AuthResponse> {
    return this.http.post<AuthResponse>(`${environment.authApiUrl}/auth/register`, { email, username, password })
      .pipe(tap(res => this.handleAuth(res)));
  }

  login(email: string, password: string): Observable<AuthResponse> {
    return this.http.post<AuthResponse>(`${environment.authApiUrl}/auth/login`, { email, password })
      .pipe(tap(res => this.handleAuth(res)));
  }

  logout(): void {
    localStorage.removeItem('chat_user');
    this._user.next(null);
    this.router.navigate(['/login']);
  }

  private handleAuth(res: AuthResponse): void {
    const user: AuthUser = { username: res.username, token: res.access_token };
    localStorage.setItem('chat_user', JSON.stringify(user));
    this._user.next(user);
  }

  private loadUser(): AuthUser | null {
    try {
      const raw = localStorage.getItem('chat_user');
      return raw ? JSON.parse(raw) : null;
    } catch { return null; }
  }
}
