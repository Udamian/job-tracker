"""Lanzador de escritorio de Job Tracker.

Doble clic -> servidor local en 127.0.0.1 (puerto libre) + ventana nativa
(pywebview). Al cerrar la ventana, el servidor se apaga y no queda nada
corriendo en segundo plano.

Si pywebview o el runtime WebView2 no están disponibles, abre el navegador
predeterminado como respaldo.

Opciones útiles:
    python desktop.py            # ventana nativa
    python desktop.py --browser  # forzar navegador
    python desktop.py --serve    # solo servidor (desarrollo/pruebas)
"""

from __future__ import annotations

import argparse
import os
import socket
import sys
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# En un EXE con console=False, stdout/stderr pueden ser None y uvicorn
# intentaría escribir en ellos.
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w", encoding="utf-8")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w", encoding="utf-8")

# Puerto fijo solo para la comunicación entre instancias (no sirve la app).
INSTANCE_PORT = 49731


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_health(port: int, timeout: float = 20.0) -> bool:
    url = f"http://127.0.0.1:{port}/health"
    limite = time.time() + timeout
    while time.time() < limite:
        try:
            with urllib.request.urlopen(url, timeout=0.6) as respuesta:
                if respuesta.status == 200:
                    return True
        except Exception:
            time.sleep(0.12)
    return False


def _start_server(port: int):
    import uvicorn

    from app.main import app

    config = uvicorn.Config(
        app,
        host="127.0.0.1",
        port=port,
        log_level="warning",
        access_log=False,
    )
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, name="jobtracker-uvicorn", daemon=True)
    thread.start()

    if not _wait_health(port):
        raise RuntimeError("El servidor local no respondió a tiempo.")
    return server, thread


def _acquire_instance_lock():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(("127.0.0.1", INSTANCE_PORT))
        sock.listen(1)
        return sock
    except OSError:
        sock.close()
        return None


def _notify_existing_instance() -> bool:
    try:
        with socket.create_connection(("127.0.0.1", INSTANCE_PORT), timeout=1.5) as sock:
            sock.sendall(b"focus\n")
        return True
    except OSError:
        return False


def _listen_for_focus(lock, holder: dict) -> None:
    def loop():
        while True:
            try:
                conexion, _ = lock.accept()
            except OSError:
                break
            try:
                conexion.recv(32)
                callback = holder.get("focus")
                if callback:
                    callback()
            except Exception:
                pass
            finally:
                try:
                    conexion.close()
                except OSError:
                    pass

    threading.Thread(target=loop, name="jobtracker-instance", daemon=True).start()


def _focus_window(holder: dict) -> None:
    ventana = holder.get("window")
    if ventana is None:
        return
    try:
        ventana.restore()
    except Exception:
        pass
    try:
        ventana.show()
    except Exception:
        pass
    try:
        ventana.on_top = True
        ventana.on_top = False
    except Exception:
        pass


def _load_webview():
    try:
        import webview

        return webview
    except Exception as exc:
        print(f"pywebview no disponible ({exc}); se usará el navegador.", file=sys.stderr)
        return None


def _serve_until_closed(thread: threading.Thread) -> None:
    try:
        while thread.is_alive():
            thread.join(0.4)
    except KeyboardInterrupt:
        pass


def main() -> int:
    parser = argparse.ArgumentParser(description="Lanzador de Job Tracker")
    parser.add_argument("--browser", action="store_true", help="Abrir en el navegador predeterminado")
    parser.add_argument("--serve", action="store_true", help="Solo servidor, sin ventana")
    parser.add_argument("--port", type=int, default=0, help="Puerto fijo para la app (por defecto, libre)")
    args = parser.parse_args()

    lock = _acquire_instance_lock()
    if lock is None:
        if _notify_existing_instance():
            print("Job Tracker ya está abierto: se ha enfocado la ventana existente.")
            return 0
        print(
            "Ya hay una instancia de Job Tracker abierta, pero no responde.\n"
            "Ciérrala o espera unos segundos y vuelve a intentarlo.",
            file=sys.stderr,
        )
        return 1

    holder: dict = {}
    _listen_for_focus(lock, holder)

    from app.paths import database_path

    print(f"Job Tracker — datos en {database_path()}")

    port = args.port or _free_port()
    try:
        server, thread = _start_server(port)
    except Exception as exc:
        print(f"No se pudo arrancar el servidor: {exc}", file=sys.stderr)
        try:
            lock.close()
        except OSError:
            pass
        return 1

    url = f"http://127.0.0.1:{port}/dashboard"

    try:
        if args.serve:
            print(f"Servidor listo en {url}")
            _serve_until_closed(thread)
            return 0

        if args.browser:
            webbrowser.open(url)
            _serve_until_closed(thread)
            return 0

        webview = _load_webview()
        if webview is None:
            webbrowser.open(url)
            _serve_until_closed(thread)
            return 0

        from app.main import set_focus_handler

        ventana = webview.create_window(
            "Job Tracker",
            url,
            width=1320,
            height=900,
            min_size=(920, 620),
        )
        holder["window"] = ventana
        holder["focus"] = lambda: _focus_window(holder)
        set_focus_handler(holder["focus"])

        try:
            webview.start()
        except Exception as exc:
            print(
                f"No se pudo abrir la ventana nativa ({exc}); se usará el navegador.",
                file=sys.stderr,
            )
            webbrowser.open(url)
            _serve_until_closed(thread)
        return 0
    finally:
        server.should_exit = True
        thread.join(timeout=5)
        try:
            lock.close()
        except OSError:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
