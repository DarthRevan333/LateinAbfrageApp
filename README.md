# LateinAbfrageApp
Eine App für verschiedene Plattformen, primär Android, mit welcher man sich über Latein-Vokabel bzw. über deren Formen abfragen lassen kann. (bis jetzt ausschließlich Verben)

# Fortführung
Es bestehen keine Pläne, diese App in Zukunft weiterzuentwickeln.

Falls es dennoch dazu kommen sollte, wird es mit einem Umstieg auf Kotlin einhergehen, bei dem die im Moment auf Python basierte App und ihr momentane Code nicht mehr verwendet werden kann.

# APK Download:
Die .apk Datei kann nebem dem Download durch Github auch unter folgendem Link heruntergeladen werden: https://drive.google.com/file/d/12JAYT5_ML4A7CWbmSfObGpigIaZo4ERZ/view?usp=sharing

# Hinweise zur App
Bei der Auswahl der Schwierigkeit entsprechen folgende Schwierigkeiten folgenden Sekundenangaben pro Frame des Hammers, wobei es insgesamt 20 Frames gibt: Sehr Einfach -> 2.0s; Einfach -> 1.2s; Moderat -> 0.65s; Schwierig -> 0.35s

Das Level-System beeinflusst hierbei ebenfalls die insgesamt vorhandene Zeit , sofern es aktiviert ist. Höhere Level bedeuten kürzere Nachdenkzeiten für eine Vokabel, wobei nur die erste Zahl (vor dem "-") des Levels für dies eine Rolle spielt. Die zweite Zahl (nach dem "-") des Levels speichert den Fortschritt und legt damit fest, wie viele Vokabeln noch richtig eingegeben werden müssen, um im Level aufzusteigen.
Durch richtig eingegebene Vokabeln kann man so aufsteigen oder durch falsch eingegebene auch absteigen (das niedrigste Level ist 0-0).

Wenn das Geschlecht von Partizipien bzw. von Gerundiva "ignoriert" werden soll, ist damit gemeint, dass die Fragestellung nicht zusätzlich speziell nach einem Geschlecht wie "Maskulinum" fragen wird, sondern als Antwort die Form in allen 3 Geschlechtern "Maskulinum", "Femininum" und "Neutrum" akzeptieren wird und daher dann auch die Lösung als eine Liste (durch [] gekennzeichnet) angeben wird.

Der Knopf "Score zurücksetzen" setzt die Zähler auf der Seite "Abfrage", welche die richtigen und falschen Antworten mitzählen wieder auf 0 zurück, wobei eine "falsche Antwort" hierbei als das Ablaufen der Zeit, also als das Aufkommen des Hammers auf dem "Boden", definiert ist.
