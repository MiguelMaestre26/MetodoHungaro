"""Punto de entrada del sistema de asignacion optima con Metodo Hungaro."""

from src.gui import App


def main() -> None:
    """Inicia la aplicacion de escritorio."""
    aplicacion = App()
    aplicacion.mainloop()


if __name__ == "__main__":
    main()
