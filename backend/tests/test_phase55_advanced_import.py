from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APITestCase

from books.models import Author, Book, ReadingStatus, Review, UserBook
from books.services.csv_import_service import CSVFormatDetector, CSVImportService

User = get_user_model()


class Phase55AdvancedImportTests(APITestCase):
    """
    Suite de pruebas automatizadas para la Fase 55 (Importación avanzada)
    y Fase 56 (Importación idempotente).
    """

    def setUp(self):
        self.user = User.objects.create_user(
            username='lector_importador',
            email='importador@example.com',
            password='Password123!',
        )
        self.author = Author.objects.create(name='Gabriel García Márquez')
        self.existing_book = Book.objects.create(
            title='Cien años de soledad',
            author=self.author,
            isbn='9788420471839',
        )

    def test_format_detection(self):
        """Verifica la detección automática de dialectos CSV."""
        gr_headers = ['Book Id', 'Title', 'Author', 'ISBN13', 'Exclusive Shelf', 'My Rating']
        calibre_headers = ['title', 'authors', 'isbn', 'identifiers', 'tags']
        generic_headers = ['titulo', 'autor', 'isbn', 'estado', 'puntuacion']

        self.assertEqual(CSVFormatDetector.detect_format(gr_headers), CSVFormatDetector.GOODREADS)
        self.assertEqual(CSVFormatDetector.detect_format(calibre_headers), CSVFormatDetector.CALIBRE)
        self.assertEqual(CSVFormatDetector.detect_format(generic_headers), CSVFormatDetector.GENERIC)

    def test_goodreads_csv_preview(self):
        """Prueba la previsualización de una exportación típica de Goodreads."""
        goodreads_csv = (
            'Book Id,Title,Author,ISBN13,My Rating,Exclusive Shelf,Date Read,My Review\n'
            '1001,Cien años de soledad,Gabriel García Márquez,="9788420471839",5,read,2026/04/10,"Obra cumbre"\n'
            '1002,El amor en los tiempos del cólera,Gabriel García Márquez,="9780307389732",4,read,2026/05/12,"Gran romance"\n'
            '1003,Dune,Frank Herbert,="9780441172719",0,to-read,,\n'
        )

        preview = CSVImportService.parse_and_preview_csv(goodreads_csv, self.user)
        self.assertEqual(preview['format_detected'], CSVFormatDetector.GOODREADS)
        self.assertEqual(preview['total_rows'], 3)
        self.assertEqual(preview['valid_count'], 3)
        self.assertEqual(preview['existing_in_catalog_count'], 1)  # Cien años de soledad

        items = preview['preview_items']
        # Fila 1: ya en catálogo
        self.assertEqual(items[0]['title'], 'Cien años de soledad')
        self.assertEqual(items[0]['isbn'], '9788420471839')
        self.assertEqual(items[0]['status'], ReadingStatus.READ)
        self.assertEqual(items[0]['rating'], 5)
        self.assertEqual(items[0]['match_status'], 'in_catalog')

        # Fila 2: nueva
        self.assertEqual(items[1]['title'], 'El amor en los tiempos del cólera')
        self.assertEqual(items[1]['status'], ReadingStatus.READ)
        self.assertEqual(items[1]['match_status'], 'new')

        # Fila 3: to-read
        self.assertEqual(items[2]['title'], 'Dune')
        self.assertEqual(items[2]['status'], ReadingStatus.WANT_TO_READ)
        self.assertEqual(items[2]['rating'], None)
        self.assertEqual(items[2]['match_status'], 'new')

    def test_calibre_csv_preview(self):
        """Prueba previsualización de exportación de Calibre."""
        calibre_csv = (
            'title,authors,isbn,identifiers,tags,rating\n'
            'Fahrenheit 451,Ray Bradbury,9788445077528,isbn:9788445077528,"Ciencia Ficción, Distopía",5\n'
            '1984,George Orwell,,isbn:9780451524935,"Clásicos, Distopía",4\n'
        )

        preview = CSVImportService.parse_and_preview_csv(calibre_csv, self.user)
        self.assertEqual(preview['format_detected'], CSVFormatDetector.CALIBRE)
        self.assertEqual(preview['total_rows'], 2)
        self.assertEqual(preview['valid_count'], 2)

        items = preview['preview_items']
        self.assertEqual(items[0]['title'], 'Fahrenheit 451')
        self.assertEqual(items[0]['author'], 'Ray Bradbury')
        self.assertIn('Ciencia Ficción', items[0]['categories'])
        self.assertEqual(items[1]['isbn'], '9780451524935')

    def test_execute_csv_import_creates_records(self):
        """Prueba ejecución de importación con creación de Book, UserBook y Review."""
        items = [
            {
                'title': 'Crónica de una muerte anunciada',
                'author': 'Gabriel García Márquez',
                'isbn': '9788497592437',
                'status': ReadingStatus.READ,
                'rating': 5,
                'review_text': 'Novela corta magistral',
                'date_read': '2026-03-01',
                'categories': ['Novela', 'Realismo Mágico'],
                'is_valid': True,
            },
            {
                'title': 'El coronel no tiene quien le escriba',
                'author': 'Gabriel García Márquez',
                'isbn': '9788497592352',
                'status': ReadingStatus.WANT_TO_READ,
                'rating': None,
                'review_text': '',
                'date_read': None,
                'categories': ['Novela'],
                'is_valid': True,
            },
        ]

        result = CSVImportService.execute_csv_import(items, self.user)
        self.assertTrue(result['success'])
        self.assertEqual(result['imported_books_count'], 2)
        self.assertEqual(result['added_to_library_count'], 2)
        self.assertEqual(result['reviews_created_count'], 1)

        # Verificar BD
        book1 = Book.objects.get(isbn='9788497592437')
        self.assertEqual(book1.title, 'Crónica de una muerte anunciada')
        self.assertEqual(book1.author.name, 'Gabriel García Márquez')

        ub1 = UserBook.objects.get(user=self.user, book=book1)
        self.assertEqual(ub1.status, ReadingStatus.READ)
        self.assertEqual(ub1.rating, 5)

        review = Review.objects.get(user=self.user, book=book1)
        self.assertEqual(review.text, 'Novela corta magistral')
        self.assertEqual(review.rating, 5)

    def test_deduplication_and_idempotence(self):
        """Fase 56: Garantiza que reintentar la misma importación no duplica libros ni entradas."""
        items = [
            {
                'title': 'Cien años de soledad',  # Ya existe en setUp
                'author': 'Gabriel García Márquez',
                'isbn': '9788420471839',
                'status': ReadingStatus.READ,
                'rating': 5,
                'is_valid': True,
            }
        ]

        initial_books_count = Book.objects.count()

        # Primera importación
        res1 = CSVImportService.execute_csv_import(items, self.user)
        self.assertEqual(res1['imported_books_count'], 0)  # Reutiliza el existente
        self.assertEqual(res1['added_to_library_count'], 1)
        self.assertEqual(Book.objects.count(), initial_books_count)
        self.assertEqual(UserBook.objects.filter(user=self.user, book=self.existing_book).count(), 1)

        # Segunda importación idéntica (Idempotencia)
        res2 = CSVImportService.execute_csv_import(items, self.user)
        self.assertEqual(res2['imported_books_count'], 0)
        self.assertEqual(res2['added_to_library_count'], 0)
        self.assertEqual(res2['updated_in_library_count'], 1)
        self.assertEqual(Book.objects.count(), initial_books_count)
        self.assertEqual(UserBook.objects.filter(user=self.user, book=self.existing_book).count(), 1)

    def test_atomic_rollback_on_failure(self):
        """Verifica que un error crítico durante la transacción revierte todo el lote."""
        items = [
            {
                'title': 'Libro A Bueno',
                'author': 'Autor A',
                'isbn': '9780000000011',
                'status': ReadingStatus.READ,
                'is_valid': True,
            },
            {
                'title': 'Libro B Falla',
                'author': 'Autor B',
                'isbn': '9780000000022',
                'status': ReadingStatus.READ,
                'is_valid': True,
            },
        ]

        initial_books = Book.objects.count()

        # Simulamos que al crear el segundo libro ocurre una excepción de base de datos
        original_get_or_create = UserBook.objects.get_or_create

        def fail_on_second(*args, **kwargs):
            if kwargs.get('defaults', {}).get('status') == ReadingStatus.READ and Book.objects.filter(isbn='9780000000022').exists():
                raise RuntimeError("Fallo forzado para probar rollback atómico")
            return original_get_or_create(*args, **kwargs)

        with patch.object(UserBook.objects, 'get_or_create', side_effect=fail_on_second):
            with self.assertRaises(RuntimeError):
                CSVImportService.execute_csv_import(items, self.user)

        # Tras el rollback, el Libro A no debe haber quedado persistido
        self.assertEqual(Book.objects.count(), initial_books)
        self.assertFalse(Book.objects.filter(isbn='9780000000011').exists())

    def test_api_csv_preview_and_confirm(self):
        """Prueba la API REST de previsualización y confirmación de CSV."""
        self.client.force_authenticate(user=self.user)

        csv_content = (
            b'Title,Author,ISBN13,Exclusive Shelf,My Rating\n'
            b'El Aleph,Jorge Luis Borges,9788420658421,read,5\n'
            b'Ficciones,Jorge Luis Borges,9788420666679,to-read,0\n'
        )
        file = SimpleUploadedFile('mis_lecturas.csv', csv_content, content_type='text/csv')

        # 1. Preview
        res_preview = self.client.post(
            '/api/v1/books/import/csv/preview/',
            {'file': file},
            format='multipart',
        )
        self.assertEqual(res_preview.status_code, status.HTTP_200_OK)
        self.assertEqual(res_preview.data['total_rows'], 2)
        self.assertEqual(res_preview.data['valid_count'], 2)

        # 2. Confirm
        items_to_import = res_preview.data['preview_items']
        res_confirm = self.client.post(
            '/api/v1/books/import/csv/confirm/',
            {'items': items_to_import, 'update_existing': True},
            format='json',
        )
        self.assertEqual(res_confirm.status_code, status.HTTP_200_OK)
        self.assertEqual(res_confirm.data['imported_books_count'], 2)
        self.assertEqual(res_confirm.data['added_to_library_count'], 2)

        # Comprobar que los libros existen y están en la estantería
        self.assertTrue(Book.objects.filter(title='El Aleph').exists())
        self.assertTrue(UserBook.objects.filter(user=self.user, book__title='El Aleph').exists())
