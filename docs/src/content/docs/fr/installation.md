---
title: "Guide d'installation — Gacha Setup pour Blender"
description: "Comment installer l'add-on Gacha Setup dans Blender (Blender 5.3 recommandé, Blender/Goo Engine 4.1+ pris en charge) avec support FBX, BetterFBX et VMD."
---

# Guide d'installation

:::note[Compatibilité Blender]
**Blender 5.2 est recommandé.** Gacha Setup est également compatible avec **Blender/Goo Engine 4.1+**. Si vous utilisez Blender **antérieur à la version 4.5**, installez **BetterFBX** pour importer les modèles.
:::

## Installation étape par étape

1. Téléchargez le dernier package `Gacha_Setup-<version>.zip` depuis GitHub Releases.
2. Lancez Blender 5.2 (recommandé) ou Blender/Goo Engine 4.1+. Sur les versions de Blender inférieures à 4.5, installez d'abord BetterFBX.
3. Ouvrez **Edit > Preferences > Add-ons**.
4. Cliquez sur le menu déroulant en haut à droite et choisissez **Install from Disk...**
5. Sélectionnez le fichier `.zip` téléchargé et cochez la case de l'add-on.
6. Appuyez sur <kbd>N</kbd> dans la vue 3D pour ouvrir le panneau latéral **Character Setup Wizard**.

---

## Dépendances intégrées

L'add-on vérifie et installe automatiquement les sous-dépendances requises lorsqu'il est activé :

- **ExpyKit** : Automatise la conversion de personnages vers Rigify.
- **UEFormat** : Permet l'importation directe des modèles Neverness to Everness (`.ueformat`).

---

:::tip[Astuce]
Vous trouverez ici des détails supplémentaires sur les options de configuration, les vérifications automatiques d'installation des dépendances et le dépannage des dépendances manquantes.
:::
