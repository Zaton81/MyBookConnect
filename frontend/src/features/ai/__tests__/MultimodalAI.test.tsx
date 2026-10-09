import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { VisualBookSearchModal } from '../components/VisualBookSearchModal';
import { AIAssistantModal } from '../components/AIAssistantModal';
import { useAuthStore } from '../../../store/auth';

// Mock de useAuthStore
vi.mock('../../../store/auth', () => ({
  useAuthStore: vi.fn(),
}));

// Mock de FileReader para jsdom
class MockFileReader {
  result: string | null = null;
  onload: (() => void) | null = null;
  readAsDataURL(_blob: Blob) {
    this.result = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==';
    if (this.onload) {
      this.onload();
    }
  }
}

describe('Sprint 20: IA Multimodal & Asistente Visual', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.HTMLElement.prototype.scrollIntoView = vi.fn();
    (useAuthStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
      token: 'fake-test-token',
      user: { id: 1, username: 'testuser' },
    });
    vi.stubGlobal('FileReader', MockFileReader);
  });

  describe('VisualBookSearchModal', () => {
    it('no renderiza nada cuando isOpen es false', () => {
      const { container } = render(
        <MemoryRouter>
          <VisualBookSearchModal isOpen={false} onClose={vi.fn()} />
        </MemoryRouter>
      );
      expect(container.firstChild).toBeNull();
    });

    it('renderiza la interfaz de subida de imagen cuando isOpen es true', () => {
      render(
        <MemoryRouter>
          <VisualBookSearchModal isOpen={true} onClose={vi.fn()} />
        </MemoryRouter>
      );

      expect(screen.getByText('Búsqueda Visual & Portadas')).toBeInTheDocument();
      expect(screen.getByText('Identificar libro por foto de portada')).toBeInTheDocument();
      expect(screen.getByText('Haz clic para subir o arrastra una foto')).toBeInTheDocument();
      expect(screen.getByText(/Formatos JPEG, PNG, WebP/i)).toBeInTheDocument();
    });

    it('permite seleccionar una imagen y envía la solicitud al endpoint multimodal', async () => {
      const mockResult = {
        status: 'success',
        is_ai_generated: true,
        badge: 'IA Multimodal Activa',
        art_style: 'Realismo Mágico / Ilustración Cálida',
        mood_atmosphere: 'Nostálgico y legendario',
        color_palette: [
          { name: 'Dorado Antiguo', hex: '#E6C229' },
          { name: 'Rojo Carmesí', hex: '#D11149' },
        ],
        accessible_alt_text: 'Portada de Cien años de soledad con mariposas amarillas.',
        matching_book: {
          id: 42,
          title: 'Cien años de soledad',
          author_name: 'Gabriel García Márquez',
          cover: 'https://example.com/cover.jpg',
          match_confidence: 0.94,
        },
      };

      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => mockResult,
      } as any);

      render(
        <MemoryRouter>
          <VisualBookSearchModal isOpen={true} onClose={vi.fn()} />
        </MemoryRouter>
      );

      const file = new File(['fake-cover-content'], 'cover.png', { type: 'image/png' });
      const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;

      fireEvent.change(fileInput, { target: { files: [file] } });

      const analyzeBtn = await screen.findByText('Identificar y analizar con BookAI');
      expect(analyzeBtn).toBeInTheDocument();
      fireEvent.click(analyzeBtn);

      await waitFor(() => {
        expect(globalThis.fetch).toHaveBeenCalledWith(
          expect.stringContaining('/api/v1/books/ai/multimodal/analyze-cover/'),
          expect.objectContaining({
            method: 'POST',
            body: expect.stringContaining('image_base64'),
          })
        );
      });

      await waitFor(() => {
        expect(screen.getByText('Cien años de soledad')).toBeInTheDocument();
        expect(screen.getByText('Gabriel García Márquez')).toBeInTheDocument();
        expect(screen.getByText(/94%/)).toBeInTheDocument();
        expect(screen.getByText('Realismo Mágico / Ilustración Cálida')).toBeInTheDocument();
        expect(screen.getByText('Nostálgico y legendario')).toBeInTheDocument();
        expect(screen.getByText('Dorado Antiguo')).toBeInTheDocument();
      });
    });

    it('llama a onClose al hacer clic en el botón de cerrar', () => {
      const handleClose = vi.fn();
      render(
        <MemoryRouter>
          <VisualBookSearchModal isOpen={true} onClose={handleClose} />
        </MemoryRouter>
      );

      const closeButton = screen.getByLabelText('Cerrar modal');
      fireEvent.click(closeButton);
      expect(handleClose).toHaveBeenCalledTimes(1);
    });
  });

  describe('AIAssistantModal con capacidades multimodales', () => {
    it('permite adjuntar una imagen para consulta multimodal', async () => {
      render(
        <AIAssistantModal
          isOpen={true}
          onClose={vi.fn()}
          contextBookId={12}
          contextBookTitle="El Señor de los Anillos"
        />
      );

      expect(screen.getByText('BookAI Assistant')).toBeInTheDocument();
      const attachBtn = screen.getByLabelText('Adjuntar foto de portada');
      expect(attachBtn).toBeInTheDocument();

      const file = new File(['image-bytes'], 'tolkien_cover.jpg', { type: 'image/jpeg' });
      const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;

      fireEvent.change(fileInput, { target: { files: [file] } });

      await waitFor(() => {
        expect(screen.getByText(/Imagen adjunta para visión IA/i)).toBeInTheDocument();
      });
    });

    it('envía mensaje multimodal con imagen al endpoint de asistencia', async () => {
      const mockResponse = {
        message: {
          role: 'assistant',
          content: 'Esta portada pertenece a la primera edición de Minotauro ilustrada.',
        },
        ai_online: true,
        badge: 'BookAI Multimodal',
      };

      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => mockResponse,
      } as any);

      render(
        <AIAssistantModal
          isOpen={true}
          onClose={vi.fn()}
          contextBookId={12}
          contextBookTitle="El Señor de los Anillos"
        />
      );

      const file = new File(['image-bytes'], 'tolkien.png', { type: 'image/png' });
      const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
      fireEvent.change(fileInput, { target: { files: [file] } });

      await screen.findByText(/Imagen adjunta para visión IA/i);

      const textInput = screen.getByPlaceholderText(/Pregunta sobre la imagen/i);
      fireEvent.change(textInput, {
        target: { value: '¿Qué edición es esta portada que adjunto?' },
      });

      const sendButton = screen.getByRole('button', { name: /Enviar/i });
      fireEvent.click(sendButton);

      await waitFor(() => {
        expect(globalThis.fetch).toHaveBeenCalledWith(
          expect.stringContaining('/api/v1/books/ai/multimodal/assistant/'),
          expect.objectContaining({
            method: 'POST',
            body: expect.stringContaining('image_base64'),
          })
        );
      });

      await waitFor(() => {
        expect(
          screen.getByText('Esta portada pertenece a la primera edición de Minotauro ilustrada.')
        ).toBeInTheDocument();
      });
    });
  });
});
