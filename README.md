# Scrape-A-RIS

### English summary

Scrape-A-RIS is a scraper for assembly information systems (Ratsinformationssysteme, RIS)
using Somacos SessionNet, written in Python. Scrape-a-RIS is the successor of 
[cologne-ris-scraper](https://github.com/marians/cologne-ris-scraper) and is usable
for SessionNet instances in numerous municipalities (in Germany, mainly).


## Was ist Scape-A-RIS

Scrape-A-RIS ist ein Scraper für Ratsinformationssysteme (RIS), die das System SessionNet 
verwenden. Scrape-A-RIS ist der Nachfolger von [cologne-ris-scraper](https://github.com/marians/cologne-ris-scraper)
und kann für zahlreiche Kommunen eingesetzt werden.

Scrape-A-RIS kann verwendet werden, um die strukturierten Daten und Inhalte aus Sitzungen, Tagesordnungspunkten,
Beschlussvorlagen, Anträgen und Anhängen auszulesen und diese in einer Datenbank abzulegen. Das Wort [Scraper](http://de.wikipedia.org/wiki/Screen_Scraping)
deutet auf die Funktionsweise hin: die Inhalte werden so aus den HTML-Seiten des RIS gelesen, wie sie für ganz
normale Besucher im Web angezeigt werden.

Scrape-A-RIS ist die Grundlage für die Web-Plattform Offenes Köln ([Github](https://github.com/marians/offeneskoeln), 
[WWW](http://offeneskoeln.de/)), die zur benutzerfreundlichen Suche und Anzeige der Daten genutzt werden kann.
Scrape-A-RIS kann jedoch auch unabhängig davon eingesetzt werden, bietet aber kein eigenes User Interface.


## Anforderungen

Scrape-A-RIS ist in Python geschrieben und wurde erfolgreich mit Python-Version 2.7.2 auf Mac OS X 
und 2.6.6 auf Debian und Red Hat Linux getestet.

Daten werden in einer [MongoDB](http://www.mongodb.org/) Datenbank gespeichert. Empfohlen ist die aktuellste
Version 2.4 (speziell für die Verwendung mit [Offenes Köln](https://github.com/marians/offeneskoeln)).

Weitere benötigte Software wird in der
[Installationsanleitung](https://github.com/marians/scrape-a-ris/wiki/Installation) genannt.

## Installation

Synopsis:

1. Mit virtualenv eine Python-Umgebung einrichten und diese starten
2. Python-Module installieren
3. MongoDB starten
4. Konfigurationsdatei config_example.py kopieren zu config.py, config.py anpassen

Eine [ausführliche Installationsanleitung](https://github.com/marians/scrape-a-ris/wiki/Installation) 
findet sich im Wiki.

## Anwendung

Alle Kommandozeilen-Parameter werden erläutert, wenn das Hauptscript wie folgt aufgerufen wird:

    >>> python main.py --help

Mit diesem Aufruf können Inhalte für Februar und März 2013 abgerufen werden:

    >>> python main.py -v --start 2013-02 --end 2013-03 -q

Viel mehr zur Benutzung gibt es in einem [ausführlichen Tutorial](https://github.com/marians/scrape-a-ris/wiki/Benutzung).

## Feedback

Bitte nutze den [Issues](https://github.com/marians/scrape-a-ris/issues) Bereich in diesem Github repository, um
Bugs zu melden.

Wenn Du Hilfe bei der Anpassung der Konfiguration an Dein RIS benötigst, kannst Du Dich auch an die [RIS-Öffner
Mailngliste](https://groups.google.com/group/ris-oeffner/) wenden.

## Unterstützung

Die Entwicklung an Scrape-a-RIS leiste ich unentgeldlich. Während ich das tue, entgeht mir Einkommen, das mit
der Bearbeitung von Aufträgen verbunden wäre. Ein Dilemma! ;-)

Wenn Dir Scrape-a-RIS einen Dienst erweist und Du die Entwicklung unterstützen möchtest,
freue ich mich über eine Spende.

Spenden via [Gittip](https://www.gittip.com/marians/) oder [PayPal](https://www.paypal.com/cgi-bin/webscr?cmd=_s-xclick&hosted_button_id=NJF88AWULCKCQ)
