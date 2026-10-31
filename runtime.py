import tkinter as tk
import time
import sys
import ctypes
from pathlib import Path


class GameRuntime:
    def __init__(self):
        self.root = None
        self.canvas = None

        self.width = 800
        self.height = 600
        self.background = "black"

        # Standardname der Runtime
        self.program_name = "Nexa"

        self.keys = set()
        self.running = False

    def set_program_name(self, name):
        """Setzt den Namen des laufenden Nexa-Programms."""

        if name is None:
            name = "Nexa"

        name = str(name).strip()

        if not name:
            name = "Nexa"

        self.program_name = name

        # Falls das Fenster bereits existiert, Titel sofort aktualisieren
        if self.root is not None:
            try:
                self.root.title(self.program_name)
            except tk.TclError:
                pass

    def window(self, title, width, height):
        if title is None:
            title = ""

        if not isinstance(title, str):
            raise RuntimeError(
                "window() benötigt einen String als Titel."
            )

        if not isinstance(width, int) or isinstance(width, bool):
            raise RuntimeError(
                "window() benötigt eine Ganzzahl für die Breite."
            )

        if not isinstance(height, int) or isinstance(height, bool):
            raise RuntimeError(
                "window() benötigt eine Ganzzahl für die Höhe."
            )

        if width <= 0 or height <= 0:
            raise RuntimeError(
                "Fenstergröße muss größer als 0 sein."
            )

        self.width = width
        self.height = height

        if self.root is not None:
            try:
                self.root.destroy()
            except tk.TclError:
                pass

            self.root = None
            self.canvas = None

        try:
            # Windows Taskleisten-App-ID für Nexa setzen
            if sys.platform == "win32":
                try:
                    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                        "Nexa.NexaRuntime"
                    )
                except Exception:
                    pass

            self.root = tk.Tk()

        except tk.TclError as error:
            raise RuntimeError(
                f"Grafikfenster konnte nicht erstellt werden: {error}"
            )

        # Ein expliziter Titel überschreibt den automatisch gesetzten
        # Programmnamen.
        if title.strip():
            self.program_name = title.strip()

        self.root.title(self.program_name)
        self.root.geometry(f"{width}x{height}")
        self.root.resizable(False, False)        
        # Nexa-Fenstericon setzen
        icon_path = Path(__file__).resolve().parent / "NexaRuntime.ico"
        if icon_path.exists():
            try:
                self.root.iconbitmap(str(icon_path))
            except tk.TclError:
                pass

        self.canvas = tk.Canvas(
            self.root,
            width=width,
            height=height,
            highlightthickness=0,
            bg=self.background
        )

        self.canvas.pack()

        self.root.bind("<KeyPress>", self._key_down)
        self.root.bind("<KeyRelease>", self._key_up)
        self.root.protocol("WM_DELETE_WINDOW", self.close)

        self.root.focus_force()
        self.running = True

    def _key_down(self, event):
        self.keys.add(event.keysym.lower())

    def _key_up(self, event):
        self.keys.discard(event.keysym.lower())

    def require_window(self):
        if self.root is None or self.canvas is None:
            raise RuntimeError(
                "Kein Spielfenster vorhanden. "
                "Rufe zuerst window() auf."
            )

    def clear(self, color="black"):
        self.require_window()

        if not isinstance(color, str):
            raise RuntimeError(
                "clear() benötigt eine Farbe als String."
            )

        self.background = color
        self.canvas.configure(bg=color)
        self.canvas.delete("all")

    def rect(self, x, y, width, height, color="white"):
        self.require_window()

        values = [x, y, width, height]

        if not all(
            isinstance(value, int) and not isinstance(value, bool)
            for value in values
        ):
            raise RuntimeError(
                "rect() benötigt x, y, width und height als Ganzzahlen."
            )

        if not isinstance(color, str):
            raise RuntimeError(
                "rect() benötigt eine Farbe als String."
            )

        self.canvas.create_rectangle(
            x,
            y,
            x + width,
            y + height,
            fill=color,
            outline=color
        )

    def circle(self, x, y, radius, color="white"):
        self.require_window()

        values = [x, y, radius]

        if not all(
            isinstance(value, int) and not isinstance(value, bool)
            for value in values
        ):
            raise RuntimeError(
                "circle() benötigt x, y und radius als Ganzzahlen."
            )

        if radius < 0:
            raise RuntimeError(
                "circle() benötigt einen Radius >= 0."
            )

        if not isinstance(color, str):
            raise RuntimeError(
                "circle() benötigt eine Farbe als String."
            )

        self.canvas.create_oval(
            x - radius,
            y - radius,
            x + radius,
            y + radius,
            fill=color,
            outline=color
        )

    def text(self, x, y, value, size=24, color="white"):
        self.require_window()

        if not isinstance(x, int) or isinstance(x, bool):
            raise RuntimeError(
                "text() benötigt x als Ganzzahl."
            )

        if not isinstance(y, int) or isinstance(y, bool):
            raise RuntimeError(
                "text() benötigt y als Ganzzahl."
            )

        if not isinstance(value, str):
            value = str(value)

        if not isinstance(size, int) or isinstance(size, bool):
            raise RuntimeError(
                "text() benötigt size als Ganzzahl."
            )

        if not isinstance(color, str):
            raise RuntimeError(
                "text() benötigt eine Farbe als String."
            )

        self.canvas.create_text(
            x,
            y,
            text=value,
            fill=color,
            font=("Arial", size),
            anchor="nw"
        )

    def present(self):
        self.require_window()

        try:
            self.root.update_idletasks()
            self.root.update()
        except tk.TclError:
            self.close()

    def key_down(self, key):
        self.require_window()

        if not isinstance(key, str):
            raise RuntimeError(
                "key_down() benötigt einen String."
            )

        return key.lower() in self.keys

    def wait(self):
        self.require_window()

        try:
            self.root.mainloop()
        except tk.TclError:
            self.close()

    def sleep(self, milliseconds):
        if not isinstance(milliseconds, int) or isinstance(milliseconds, bool):
            raise RuntimeError(
                "sleep() benötigt eine Ganzzahl in Millisekunden."
            )

        if milliseconds < 0:
            raise RuntimeError(
                "sleep() benötigt einen Wert >= 0."
            )

        if self.root is None:
            time.sleep(milliseconds / 1000)
            return

        delay = milliseconds / 1000
        end = time.time() + delay

        while time.time() < end:
            if self.root is None:
                break

            try:
                self.root.update()
                self.root.update_idletasks()
            except tk.TclError:
                break

            time.sleep(0.01)

    def close(self):
        self.running = False
        self.keys.clear()

        if self.root is not None:
            try:
                self.root.destroy()
            except tk.TclError:
                pass

        self.root = None
        self.canvas = None


def start_runtime():
    """
    Startet die Nexa Game Runtime als eigenständiges Programm.
    """

    runtime = GameRuntime()

    runtime.window(
        "Nexa Game Runtime",
        800,
        600
    )

    runtime.clear("black")

    runtime.text(
        20,
        20,
        "Nexa Game Runtime",
        32,
        "white"
    )

    runtime.text(
        20,
        70,
        "Runtime erfolgreich gestartet.",
        20,
        "white"
    )

    runtime.text(
        20,
        110,
        "Bereit fuer Nexa-Spiele.",
        18,
        "gray"
    )

    runtime.present()
    runtime.wait()


def main():
    try:
        start_runtime()

    except KeyboardInterrupt:
        return

    except Exception as error:
        print()
        print("Nexa Game Runtime Fehler:")
        print(error)
        print()

        if getattr(sys, "frozen", False):
            input("Enter zum Beenden...")


if __name__ == "__main__":
    main()



