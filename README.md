# scrape-a-ris

### English summary

ris-scraper is a scraper for assembly information systems (Ratsinformationssysteme, RIS)
using Somacos SessionNet or CC e-gov AllRis, written in Python.


## Was ist ris-scraper?

ris-scraper ist ein Scraper für Ratsinformationssysteme (RIS). Bislang werden die Systeme Somacos SessionNet und CC e-gov AllRis unterstützt.

ris-scraper kann verwendet werden, um die strukturierten Daten und Inhalte aus Personen, Gruppierungen, Sitzungen, Tagesordnungspunkten,
Beschlussvorlagen, Anträgen und Anhängen auszulesen und diese in einer Datenbank abzulegen. Das Wort [Scraper](http://de.wikipedia.org/wiki/Screen_Scraping)
deutet auf die Funktionsweise hin: die Inhalte werden so aus den HTML-Seiten des RIS gelesen, wie sie für ganz
normale Besucher im Web angezeigt werden.

ris-scraper ist die Grundlage für die Web-Plattform "Politik bei uns" ([Github](https://github.com/okfde/ris-web)), 
[WWW](https://politik-bei-uns.de/), die zur benutzerfreundlichen Suche und Anzeige der Daten genutzt werden kann.
ris-scraper kann jedoch auch unabhängig davon eingesetzt werden, bietet aber kein eigenes User Interface.
Zudem muss beachtet werden, dass die bearbeitenden Scripte sowie das OParl Interface ebenfalls in ([ris-web](https://github.com/okfde/ris-web) enthalten sind.


## Anforderungen

ris-scraper ist in Python geschrieben und wurde erfolgreich mit Python-Version 2.7 auf Debian und Ubuntu getestet.

Daten werden in einer [MongoDB](http://www.mongodb.org/) Datenbank gespeichert. Empfohlen ist die aktuellste Version 2.6.

Weitere benötigte Software wird in der [Installationsanleitung](https://github.com/okfde/ris-scraper/wiki/Installation) genannt.

## Installation

Synopsis:

1. Mit virtualenv eine Python-Umgebung einrichten und diese starten
2. Python-Module installieren
3. MongoDB starten
4. Konfigurationsdatei config_example.py kopieren zu config.py, config.py anpassen

Eine [ausführliche Installationsanleitung](https://github.com/okfde/ris-scraper/wiki/Installation) findet sich im Wiki.

## Anwendung

Alle Kommandozeilen-Parameter werden erläutert, wenn das Hauptscript wie folgt aufgerufen wird:

    >>> python main.py --help

Mit diesem Aufruf können Inhalte für Februar und März 2013 abgerufen werden:

    >>> python main.py --start 2013-02 --end 2013-03

Viel mehr zur Benutzung gibt es in einem [ausführlichen Tutorial](https://github.com/okfde/ris-scraper/wiki/Benutzung).

###Lizenz

Der Code steht unter einer MIT-artigen [Lizenz](https://github.com/okfde/ris-web/blob/master/LIZENZ.txt).

## Feedback

Bitte nutze den [Issues](https://github.com/okfde/ris-scraper/issues) Bereich in diesem Github repository, um
Bugs zu melden.

Wenn Du Hilfe bei der Anpassung der Konfiguration an Dein RIS benötigst, kannst Du Dich auch an die [RIS-Öffner
Mailngliste](https://groups.google.com/group/ris-oeffner/) wenden.

## Geschichte

Der Scraper basiert auf dem Projekt [Scrape-A-RIS](https://github.com/marians/scrape-a-ris) bzw [cologne-ris-scraper](https://github.com/marians/cologne-ris-scraper)
von [Marian Steinbach](http://www.sendung.de/).
