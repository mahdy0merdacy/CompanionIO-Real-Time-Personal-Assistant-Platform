import { Injectable, signal } from '@angular/core';

export type FaceState = 'idle' | 'listening' | 'thinking' | 'talking' | 'error' | 'success' | 'loading' | 'excited' | 'sleeping' | 'warning';

@Injectable({ providedIn: 'root' })
export class AiFaceService {
  // We use a Signal for high-performance UI updates
  state = signal<FaceState>('idle');

  set(newState: FaceState) {
    this.state.set(newState);
  }

  // Helper method to check current state
  getState(): FaceState {
    return this.state();
  }
}
