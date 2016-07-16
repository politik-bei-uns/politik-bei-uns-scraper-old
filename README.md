# Scraper für Politik bei Uns

Die Scraper können aus den Ratsinformationssysteme (RIS) Somacos, SessionNet und CC e-gov AllRis strukturierte Daten wie Personen, Gruppierungen, Sitzungen, Tagesordnungspunkten, Beschlussvorlagen, Anträgen und Anhängen auslesen und diese in einer Datenbank ablegen.

Diese Scraper sind die Grundlage für die Website Politik bei uns ([Github](https://github.com/okfde/politik-bei-uns-scraper-web), 
[WWW](https://politik-bei-uns.de/)), die zur benutzerfreundlichen Suche und Anzeige der Daten genutzt werden kann.
Sie können jedoch auch unabhängig davon eingesetzt werden.

## Anforderungen

Die Scraper sind in Python 2 geschrieben und speichern die Daten in einer [MongoDB](http://www.mongodb.org/) Datenbank.

Weitere benötigte Software wird in der [Installationsanleitung](https://github.com/okfde/politik-bei-uns-scraper/wiki/Installation) genannt.

## Installation

Eine [ausführliche Installationsanleitung](https://github.com/okfde/politik-bei-uns-scraper/wiki/Installation) findet sich im Wiki.

Synopsis:

1. Mit virtualenv eine Python-Umgebung einrichten und diese starten
2. Python-Module installieren
3. MongoDB starten
4. Konfigurationsdatei config_example.py kopieren zu config.py, config.py anpassen


## Anwendung

Alle Kommandozeilen-Parameter werden erläutert, wenn das Hauptscript wie folgt aufgerufen wird:

    >>> python main.py --help

Mit diesem Aufruf können Inhalte für Februar und März 2013 abgerufen werden:

    >>> python main.py --start 2013-02 --end 2013-03

Viel mehr zur Benutzung gibt es in einem [ausführlichen Tutorial](https://github.com/okfde/politik-bei-uns-scraper/wiki/Benutzung).

### Lizenz

Der Code steht unter der BSD 3-Clause License [Lizenz](https://github.com/okfde/politik-bei-uns-scraper/blob/master/LIZENZ.txt).

## Geschichte

Der Scraper basiert auf dem Projekt [Scrape-A-RIS](https://github.com/marians/scrape-a-ris) bzw [cologne-ris-scraper](https://github.com/marians/cologne-ris-scraper)
von [Marian Steinbach](http://www.sendung.de/).
