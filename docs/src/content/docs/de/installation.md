---
title: "Installationsanleitung — Gacha Setup für Blender"
description: "So installierst du das Gacha Setup Add-on in Blender (Blender 5.3 empfohlen, Blender/Goo Engine 4.1+ unterstützt) mit Unterstützung für FBX, BetterFBX und VMD."
---

# Installationsanleitung

:::note[Blender-Kompatibilität]
**Blender 5.2 wird empfohlen.** Gacha Setup ist außerdem mit **Blender/Goo Engine 4.1+** kompatibel. Wenn du eine Blender-Version **unter 4.5** verwendest, installiere **BetterFBX**, um Modelle zu importieren.
:::

## Schritt-für-Schritt-Installation

1. Lade das neueste Release-Paket `Gacha_Setup-<version>.zip` von GitHub Releases herunter.
2. Starte Blender 5.2 (empfohlen) oder Blender/Goo Engine 4.1+. Bei Blender-Versionen unter 4.5 installiere zuerst BetterFBX.
3. Öffne **Edit > Preferences > Add-ons**.
4. Klicke auf das Dropdown-Menü in der oberen rechten Ecke und wähle **Install from Disk...**
5. Wähle die heruntergeladene `.zip`-Datei aus und aktiviere das Kontrollkästchen des Add-ons.
6. Drücke <kbd>N</kbd> im 3D Viewport, um das Seitenleisten-Panel **Character Setup Wizard** zu öffnen.

---

## Enthaltene Abhängigkeiten

Das Add-on überprüft und installiert erforderliche Unterabhängigkeiten automatisch beim Aktivieren:

- **ExpyKit**: Automatisiert Rigify-Charakterkonvertierungen.
- **UEFormat**: Ermöglicht den direkten Import von Neverness-to-Everness-Modellen (`.ueformat`).

---

:::tip[Kurztipp]
Hier werden weitere Details zu Konfigurationsoptionen, automatischen Abhängigkeitsprüfungen und der Fehlerbehebung bei fehlenden Abhängigkeiten folgen.
:::
