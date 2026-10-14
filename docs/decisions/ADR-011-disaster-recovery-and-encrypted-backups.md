# ADR-011: Estrategia de Copias de Seguridad Cifradas AES-256, Disaster Recovery y Verificación de Integridad

## Estado
Aceptado

## Contexto
La persistencia de datos (base de datos relacional, archivos multimedia subidos y configuraciones de despliegue) requiere un plan de recuperación ante desastres (DRP) robusto con objetivos de recuperación bien definidos (RPO $\le 24$ horas, RTO $\le 30$ minutos), cumplimiento de privacidad RGPD y protección criptográfica contra accesos ilícitos a los archivos de copia.

## Decisión
1. **Cifrado Simétrico AES-256-CBC:**
   - Todos los volcados de base de datos (`pg_dump`), archivos comprimidos de media y configuración se cifran mediante `openssl enc -aes-256-cbc -pbkdf2` usando la clave `BACKUP_ENCRYPTION_KEY`.
2. **Generación Determinista de Manifiestos SHA-256:**
   - Cada artefacto de backup genera un archivo `.manifest.json` que registra el hash criptográfico SHA-256, tamaño en bytes, versión de esquema, conteo de entidades y timestamp exacto.
3. **Orquestación Diaria y Retención Automática:**
   - `backup_all.sh` coordina la ejecución secuencial, emitiendo un resumen consolidado `daily_backup_summary_<timestamp>.json` con retención de 14 días.
4. **Validación Transaccional Post-Restauración:**
   - Comando `python manage.py verify_restore_integrity` para comprobar que la restauración mantenga integridad referencial en usuarios, lecturas, ratings en rango [0.0, 5.0], reseñas [1, 5] y existencia de archivos físicos en `MEDIA_ROOT`.
5. **Monitorización de Frescura (RPO SLA):**
   - Comando `python manage.py check_backup_freshness` que alerta con código de salida si el último backup supera el umbral de 24 horas o presenta discrepancia de checksum SHA-256.

## Consecuencias
### Positivas
- Resguardo total de la privacidad de los lectores incluso si el almacenamiento de backups es vulnerado.
- Capacidad de restauración determinista, transaccional y validada ante desastres catastróficos.
- Cumplimiento estricto de las normativas de protección de datos (RGPD Art. 32).

### Negativas / Retos
- Requiere custodia segura de `BACKUP_ENCRYPTION_KEY` fuera de la máquina de producción.
- Mayor sobrecarga computacional de CPU durante la compresión y cifrado diario de medios.
