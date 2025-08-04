#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
apply_binds_gui_i18n_multi.py

Bilingual (FR/EN) minimal GUI to:
1) Choose a JSON SOURCE file (binds to copy).
2) Choose one OR multiple JSON TARGET files (where to apply).
3) Save results next to each TARGET with a suffix, or let the user pick one output file
   (single target) / one output folder (multiple targets).
4) Remove all existing "key" fields in the target(s).
5) Copy "key" fields from the source for common modules.
6) Save and report success (list of outputs if multiple).

Notes:
- The initial folder for the dialogs opens in the Minecraft config folder under %APPDATA%:
  %APPDATA%\.minecraft\config\Myau
  If that exact folder is missing, we fall back to %APPDATA%\.minecraft\config, else the user home.
- Language (FR/EN) is auto-detected from the OS locale.
- You can force behavior with the constants just below.
"""

import json
import sys
import os
import locale
import tkinter as tk
from tkinter import filedialog, messagebox

# -------------------------
# User-tunable constants
# -------------------------
# If True, we ask the user where to save the output file(s).
# - Single target: we ask for a specific output file (Save As).
# - Multiple targets: we ask for ONE output folder; filenames will be auto-generated there.
# If False, we save automatically next to each TARGET, with the suffix/pattern.
ASK_WHERE_TO_SAVE = False

# Pattern used when ASK_WHERE_TO_SAVE == False, OR when multiple targets and user picked an output folder.
# {base} is the TARGET filename without extension.
# >>> Requested suffix: "_mybind"
OUTPUT_NAME_PATTERN = "{base}_mybind.json"

# Default directory where file dialogs will open.
# By default: %APPDATA%\.minecraft\config\Myau (Windows)
def _compute_default_dir():
    appdata = os.environ.get("APPDATA")
    if appdata:
        candidate = os.path.join(appdata, r".minecraft\config\Myau")
        if os.path.isdir(candidate):
            return candidate
        # fallback: config folder
        fallback = os.path.join(appdata, r".minecraft\config")
        if os.path.isdir(fallback):
            return fallback
    # last resort: user home
    return os.path.expanduser("~")

DEFAULT_DIR = _compute_default_dir()


# -------------------------
# i18n (very small helper)
# -------------------------
def detect_lang():
    """Return 'fr' if system locale looks French, else 'en'."""
    try:
        # locale.getdefaultlocale() can raise in some environments; guard defensively
        lang = (locale.getlocale()[0] or locale.getdefaultlocale()[0] or "").lower()
    except Exception:
        lang = ""
    return "fr" if lang.startswith("fr") else "en"


LANG = detect_lang()

TXT = {
    "fr": {
        "title": "Appliquer des binds",
        "step1_title": "Étape 1",
        "step1_msg": "Sélectionnez le fichier SOURCE (avec les binds).",
        "step2_title": "Étape 2",
        "step2_msg_single": "Sélectionnez le fichier CIBLE (où appliquer).",
        "step2_msg_multi": "Sélectionnez un ou plusieurs fichiers CIBLES (où appliquer).",
        "step3_title": "Étape 3",
        "step3_msg_file": "Choisissez un fichier de SORTIE (ou annulez pour enregistrer au même endroit).",
        "step3_msg_dir": "Choisissez un DOSSIER DE SORTIE pour tous les fichiers générés (ou annulez pour enregistrer à côté de chaque fichier CIBLE).",
        "json_src_title": "Fichier JSON SOURCE",
        "json_dst_title": "Fichier JSON CIBLE",
        "json_dsts_title": "Fichiers JSON CIBLES",
        "json_out_title": "Fichier de sortie",
        "dir_out_title": "Dossier de sortie",
        "done_title": "Terminé",
        "done_msg_single": "Les binds ont été appliqués avec succès.\nRésultat :\n{path}",
        "done_msg_multi": "Les binds ont été appliqués avec succès.\nFichiers générés :\n{paths}",
        "err_load": "Impossible de charger '{path}':\n{err}",
        "err_save": "Impossible de sauvegarder '{path}':\n{err}",
        "cancelled": "Opération annulée.",
    },
    "en": {
        "title": "Apply binds",
        "step1_title": "Step 1",
        "step1_msg": "Select the SOURCE file (with the binds).",
        "step2_title": "Step 2",
        "step2_msg_single": "Select the TARGET file (to apply to).",
        "step2_msg_multi": "Select one or more TARGET files (to apply to).",
        "step3_title": "Step 3",
        "step3_msg_file": "Choose an OUTPUT file (or cancel to save in the same place).",
        "step3_msg_dir": "Choose an OUTPUT FOLDER for all generated files (or cancel to save next to each TARGET).",
        "json_src_title": "JSON SOURCE file",
        "json_dst_title": "JSON TARGET file",
        "json_dsts_title": "JSON TARGET files",
        "json_out_title": "Output file",
        "dir_out_title": "Output folder",
        "done_title": "Done",
        "done_msg_single": "Binds applied successfully.\nResult:\n{path}",
        "done_msg_multi": "Binds applied successfully.\nGenerated files:\n{paths}",
        "err_load": "Cannot load '{path}':\n{err}",
        "err_save": "Cannot save '{path}':\n{err}",
        "cancelled": "Operation cancelled.",
    },
}


def t(key, **kwargs):
    text = TXT.get(LANG, TXT["en"]).get(key, key)
    return text.format(**kwargs) if kwargs else text


# -------------------------
# Core JSON helpers
# -------------------------
def load_json(path):
    """Load a JSON file and return the Python object. Show a GUI error on failure."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        messagebox.showerror(t("title"), t("err_load", path=path, err=e))
        sys.exit(1)


def save_json(obj, path):
    """Save the Python object as JSON to the given file. Show a GUI error on failure."""
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(obj, f, indent=2, ensure_ascii=False)
    except Exception as e:
        messagebox.showerror(t("title"), t("err_save", path=path, err=e))
        sys.exit(1)


def apply_binds(src_cfg, dst_cfg):
    """
    Remove all 'key' fields from dst_cfg, then copy 'key' fields from src_cfg
    for modules present in both.
    """
    # 1) remove
    for module, params in list(dst_cfg.items()):
        if isinstance(params, dict):
            params.pop("key", None)

    # 2) copy
    for module, src_params in src_cfg.items():
        if module in dst_cfg and isinstance(src_params, dict) and "key" in src_params:
            if not isinstance(dst_cfg[module], dict):
                dst_cfg[module] = {}
            dst_cfg[module]["key"] = src_params["key"]

    return dst_cfg


# -------------------------
# Main GUI flow
# -------------------------
def main():
    # Tk init
    root = tk.Tk()
    root.withdraw()  # hide main window

    # Step 1: choose source
    messagebox.showinfo(t("step1_title"), t("step1_msg"))
    src_path = filedialog.askopenfilename(
        title=t("json_src_title"),
        initialdir=DEFAULT_DIR,
        filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
    )
    if not src_path:
        messagebox.showinfo(t("title"), t("cancelled"))
        sys.exit(0)

    # Step 2: choose target(s)
    # We use askopenfilenames to allow selecting one or multiple files.
    messagebox.showinfo(t("step2_title"), t("step2_msg_multi"))
    dst_paths = filedialog.askopenfilenames(
        title=t("json_dsts_title"),
        initialdir=DEFAULT_DIR,
        filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
    )
    if not dst_paths:
        messagebox.showinfo(t("title"), t("cancelled"))
        sys.exit(0)

    # Normalize to list
    if isinstance(dst_paths, (tuple, list)):
        dst_paths = list(dst_paths)
    else:
        dst_paths = [dst_paths]

    # Step 3: where to save
    # Strategy:
    # - If ASK_WHERE_TO_SAVE is False: always save next to each target, using OUTPUT_NAME_PATTERN.
    # - If True and len(dst_paths) == 1: ask for a single output file (like the original behavior).
    # - If True and len(dst_paths) > 1: ask for an output FOLDER to put all generated files (or cancel to fallback).
    chosen_out_file = None
    chosen_out_dir = None

    if ASK_WHERE_TO_SAVE:
        if len(dst_paths) == 1:
            messagebox.showinfo(t("step3_title"), t("step3_msg_file"))
            default_name = os.path.basename(dst_paths[0])
            chosen_out_file = filedialog.asksaveasfilename(
                title=t("json_out_title"),
                defaultextension=".json",
                initialdir=os.path.dirname(dst_paths[0]),
                initialfile=default_name,
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            )
            # If user cancels, we will fallback to pattern next to the target.
        else:
            messagebox.showinfo(t("step3_title"), t("step3_msg_dir"))
            chosen_out_dir = filedialog.askdirectory(
                title=t("dir_out_title"),
                initialdir=os.path.dirname(dst_paths[0]),
                mustexist=True,
            )
            # If user cancels, we will fallback to "next to each target".

    # Processing (load source once)
    src_cfg = load_json(src_path)
    generated_paths = []

    for dst_path in dst_paths:
        dst_cfg = load_json(dst_path)
        updated = apply_binds(src_cfg, dst_cfg)

        # Determine out_path
        if not ASK_WHERE_TO_SAVE:
            # Always save next to the target, with pattern
            base, _ext = os.path.splitext(os.path.basename(dst_path))
            out_dir = os.path.dirname(dst_path)
            out_path = os.path.join(out_dir, OUTPUT_NAME_PATTERN.format(base=base))
        else:
            if len(dst_paths) == 1:
                if chosen_out_file:
                    out_path = chosen_out_file
                else:
                    # Fallback: same folder as the single target, with pattern
                    base, _ext = os.path.splitext(os.path.basename(dst_path))
                    out_dir = os.path.dirname(dst_path)
                    out_path = os.path.join(out_dir, OUTPUT_NAME_PATTERN.format(base=base))
            else:
                # Multiple targets
                base, _ext = os.path.splitext(os.path.basename(dst_path))
                if chosen_out_dir:
                    out_dir = chosen_out_dir
                else:
                    out_dir = os.path.dirname(dst_path)
                out_path = os.path.join(out_dir, OUTPUT_NAME_PATTERN.format(base=base))

        save_json(updated, out_path)
        generated_paths.append(out_path)

    # Report
    if len(generated_paths) == 1:
        messagebox.showinfo(t("done_title"), t("done_msg_single", path=generated_paths[0]))
    else:
        # Join paths on new lines; message box is simple but readable.
        listing = "\n".join(generated_paths)
        messagebox.showinfo(t("done_title"), t("done_msg_multi", paths=listing))


if __name__ == "__main__":
    main()
