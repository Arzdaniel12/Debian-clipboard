# Clipboard History

Aplicación nativa para Debian que conserva localmente los últimos 100 elementos del portapapeles, incluyendo texto e imágenes. Está escrita en Python y GTK 3.

## Funciones

- Ventana de búsqueda rápida para seleccionar y volver a copiar elementos.
- Historial SQLite local, con deduplicación y límite de 100 entradas.
- Icono en la bandeja, borrado individual y borrado completo.
- Pausa del monitoreo, modo privado y exclusión preparada para aplicaciones sensibles.
- Atajo `Super+V`, configurable desde Preferencias.
- Inicio automático mediante el diálogo de Preferencias.

## Instalar en Debian

```bash
sudo apt install python3-gi gir1.2-gtk-3.0 gir1.2-gdkpixbuf-2.0 python3-venv
python3 -m venv --system-site-packages .venv
.venv/bin/pip install -e .
.venv/bin/clipboard-history
```

También se puede instalar el lanzador en el menú de aplicaciones:

```bash
mkdir -p ~/.local/share/applications
cp clipboard-history.desktop ~/.local/share/applications/
```

## Pruebas

Las pruebas no necesitan servidor gráfico:

```bash
python3 -m unittest discover -s tests -v
```

Los datos se guardan en `~/.local/share/clipboard-history/history.db`.

## Licencia

GNU General Public License v3.0. Consulta [LICENSE](LICENSE).
