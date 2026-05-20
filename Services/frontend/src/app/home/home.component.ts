import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { AuthService } from '../core/services/auth.service';

@Component({
  selector: 'app-home',
  standalone: true,
  imports: [CommonModule, RouterLink],
  templateUrl: './home.component.html',
  styleUrls: ['./home.component.css']
})
export class HomeComponent {
  auth = inject(AuthService);

  get isLoggedIn(): boolean {
    return this.auth.isLoggedIn;
  }

  get username(): string {
    return this.auth.currentUser?.username ?? '';
  }
}
