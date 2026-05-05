import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { AiFaceService } from '../../core/services/ai-face.service';

@Component({
  selector: 'app-ai-face',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './ai-face.component.html',
  styleUrls: ['./ai-face.component.css']
})
export class AiFaceComponent {
  constructor(public faceService: AiFaceService) {}
}
