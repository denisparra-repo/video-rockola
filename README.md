# VideoRockola

**Español** | [English](README.en.md)

Reproductor de videos musicales tipo "rockola" hecho con **Python**, **PyQt6** y **VLC**. Muestra el logo y una vista previa arriba, la lista de canciones abajo, reproduce en pantalla completa y permite **agregar videos a una cola** sin salir de la pantalla completa.

## Distribución de la interfaz

```
┌───────────────────────┬──────────┐
│         LOGO          │  VIDEO   │
├───────────────────────┴──────────┤
│         LISTA CANCIONES          │
└──────────────────────────────────┘
```

- **Logo** (arriba a la izquierda): se lee del archivo `logo.png` ubicado en la carpeta de la aplicación. Si no existe, se genera uno por defecto.
- **Video** (arriba a la derecha): vista previa del video seleccionado.
- **Lista de canciones** (abajo): lista principal con fuente grande y legible.

## Características

- **Configuración con la tecla `P`**: administra varios directorios de videos, los formatos soportados, el logo y la normalización de volumen. Se guarda en `config.json`.
- Carga de videos de **varios directorios** a la vez; todos los videos encontrados se muestran en una sola lista ordenada de forma ascendente por título.
- **Foco automático en la lista**: al iniciar (si hay al menos un video), al terminar un video sin cola pendiente y al salir de pantalla completa con `Esc`.
- **Formatos** seleccionables con casillas, entre los conocidos por VLC.
- **Vista previa automática**: al dejar de navegar por la lista durante ~1,2 segundos, el video seleccionado se reproduce desde la mitad durante 5 segundos y luego se pausa. Mientras se navega (por ejemplo, manteniendo `↑` o `↓`) no se carga ningún video, así que la lista responde con fluidez. El retardo se ajusta con la constante `PREVIEW_DELAY_MS`.
- **Pantalla completa** con `Enter`: oculta logo y lista y reproduce el video desde el inicio.
- **Cola de reproducción** en pantalla completa, con panel inferior y reproducción automática del siguiente video.
- **Normalización de volumen** (filtro `normvol` de VLC) para igualar el volumen entre videos, tanto en la vista previa como en pantalla completa.
- Pausa/reanudación con la barra espaciadora.
- Compatible con Windows, Linux y macOS.

## Requisitos

- Python 3.9 o superior
- [VLC media player](https://www.videolan.org/vlc/) instalado en el sistema (la arquitectura de VLC debe coincidir con la de Python)
- Librerías de Python: `PyQt6` y `python-vlc`

```bash
pip install PyQt6 python-vlc
```

## Uso

```bash
python videorockola.py
```

1. En la primera ejecución se abre el diálogo de configuración. Agrega uno o más directorios con videos y guarda.
2. Navega por la lista: al detenerte ~1,2 s se muestra una vista previa de 5 segundos desde la mitad.
3. Presiona **Enter** para verlo en pantalla completa desde el inicio.
4. En pantalla completa, presiona **↑** o **↓** para abrir el panel de cola y agrega videos (doble clic o `Enter`).
5. Presiona **Esc** para saltar al siguiente video de la cola o, si no hay cola, salir de pantalla completa.

## Controles

| Acción | Control |
|---|---|
| Abrir configuración (fuera de pantalla completa) | `P` |
| Vista previa | Detenerse ~1,2 s sobre un video de la lista |
| Pantalla completa | `Enter` |
| Pausar / Reanudar | `Espacio` |
| Abrir panel de cola (solo en pantalla completa) | `↑` / `↓` |
| Agregar video a la cola | Doble clic o `Enter` en el panel de cola |
| Cerrar panel de cola | `Esc` (o automáticamente tras 5 s sin interacción) |
| Siguiente video de la cola | `Esc` en pantalla completa (si hay cola) |
| Salir de pantalla completa | `Esc` (si la cola está vacía) |

## Diálogo de configuración (`P`)

- **Directorios de videos musicales**: lista con botones para agregar y quitar. Puede haber más de uno.
- **Formatos de video soportados**: lista marcable con `.mp4`, `.m4v`, `.mkv`, `.avi`, `.mov`, `.wmv`, `.flv`, `.f4v`, `.webm`, `.mpg`, `.mpeg`, `.ts`, `.m2ts`, `.mts`, `.3gp`, `.ogv`, `.vob`, `.divx`, `.asf`, `.rm`, `.rmvb`. Por defecto vienen marcados `.mp4`, `.avi`, `.mkv`, `.mov`, `.wmv`, `.flv` y `.webm`.
- **Logo**: vista previa y botón "Cambiar logo…". La imagen elegida se guarda como `logo.png` en la carpeta de la aplicación.
- **Normalizar volumen**: activa o desactiva la normalización. Este cambio se aplica al reiniciar la aplicación.

Al guardar, la lista de canciones se recarga con los nuevos directorios y formatos (y se vacía la cola).

## Normalización de volumen

Se usa el filtro de audio `normvol` de VLC, que ajusta el volumen dinámicamente para que los videos más fuertes no sobresalgan. Como el mismo reproductor se usa para la vista previa y para la pantalla completa, aplica a ambos. Los parámetros (`--norm-buff-size` y `--norm-max-level`) se pueden ajustar en el código si necesitas un efecto más o menos fuerte.

## Cola de reproducción

- Panel sin bordes, siempre visible al frente, del ancho de la pantalla y el 18 % inferior de su alto.
- Solo se abre en pantalla completa y con un video en reproducción.
- Se oculta tras **5 segundos** sin interacción; mientras se navega con las flechas el temporizador se detiene.
- Los videos agregados aparecen en la lista con el prefijo `En cola:`.
- Cuando un video termina (o se presiona `Esc`), se reproduce el primero de la cola.
- Si la cola está vacía cuando termina un video, se sale de pantalla completa y el foco vuelve a la lista.

## Icono de la ventana

La aplicación busca el icono en este orden: `icon.ico`, `icon.png` y, si no hay ninguno, `logo.png`, primero junto al programa y luego dentro del ejecutable. En Windows también se registra un identificador propio para que la barra de tareas muestre este icono y no el de Python. Para usar otro icono basta reemplazar `icon.ico` (idealmente con varios tamaños: 16, 32, 48, 64, 128 y 256 px).


## Archivos del proyecto

```
videorockola.py   # Aplicación completa
icon.ico / icon.png   # Icono de la ventana y del ejecutable
logo.png          # Logo (se crea uno por defecto si no existe)
config.json       # Configuración (se crea al guardar)
requirements.txt  # Dependencias
README.md         # Documentación (español)
README.en.md      # Documentación (inglés)
```

## Notas

- Si VLC no se puede inicializar, la aplicación muestra un error y se cierra.
- Si no hay videos cargados, la lista indica que presiones `P` para configurar los directorios.
- El fin de un video se recibe desde el hilo de VLC y se reenvía al hilo de Qt mediante una señal, para evitar cierres inesperados.
