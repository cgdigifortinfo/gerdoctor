# Web / Composition

`server.py` ist nur noch der stabile ASGI-Importpfad. Die FastAPI-Anwendung wird
in `web.application` zusammengesetzt; Zugriffsmiddleware und ASGI-Lifecycle sind
eigene, strikt typisierte Web-Basismodule. Fachliche Router bleiben in ihren
jeweiligen Slice-Unterordnern.

`web.application` ist während der schrittweisen Altcode-Ablösung bewusst nicht
Teil des strikten mypy-Ziels. Alle extrahierten Router, `web.access_middleware`
und `web.lifecycle` werden dagegen strikt geprüft. Diese Ausnahme darf erst
entfernt werden, wenn die verbleibenden Composition-Callbacks typisiert sind.
