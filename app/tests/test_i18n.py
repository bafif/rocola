"""Spanish and English: the catalog, the texts the code asks for, and picking the language."""

from __future__ import annotations

import ast
import shutil
import string
import subprocess
from pathlib import Path

import pytest

from rocola import app as rapp
from rocola import i18n, library, ui
from rocola import input as actions

PACKAGE = Path(rapp.__file__).resolve().parent
REPO = PACKAGE.parent.parent
ROCOLA_LANG_SH = REPO / "os/rootfs-overlay/usr/local/bin/rocola-lang"
SHIPPED_CONF = REPO / "os/rootfs-overlay/etc/rocola/language.conf"


def fields(text: str) -> set[tuple[str, str]]:
    return {(name, spec) for _lit, name, spec, _conv in string.Formatter().parse(text) if name}


@pytest.mark.parametrize("key", sorted(i18n.CATALOG))
def test_every_text_is_in_both_languages(key):
    texts = i18n.CATALOG[key]
    assert set(texts) == set(i18n.LANGUAGES), f"{key}: languages {sorted(texts)}"
    for lang in i18n.LANGUAGES:
        assert texts[lang].strip(), f"{key}: empty in {lang}"
    assert fields(texts["es"]) == fields(texts["en"]), f"{key}: placeholders differ"


def _calls(tree: ast.AST):
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            yield node


def _name(call: ast.Call) -> str:
    f = call.func
    return f.attr if isinstance(f, ast.Attribute) else f.id if isinstance(f, ast.Name) else ""


def _constants(node: ast.AST) -> list[str]:
    """The literal strings an argument can be: "a", "a" if x else "b"."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return [node.value]
    if isinstance(node, ast.IfExp):
        return _constants(node.body) + _constants(node.orelse)
    return []


SOURCES = sorted(PACKAGE.glob("*.py"))


def test_every_key_the_code_asks_for_exists():
    missing = []
    for path in SOURCES:
        for call in _calls(ast.parse(path.read_text(encoding="utf-8"))):
            if _name(call) == "t" and call.args:
                for key in _constants(call.args[0]):
                    if key not in i18n.CATALOG:
                        missing.append(f"{path.name}:{call.lineno} {key}")
    # The keys built at run time: the menu options and MPD's states.
    missing += [f"menu.{o}" for o in ui.MenuScene.OPTIONS if f"menu.{o}" not in i18n.CATALOG]
    missing += [k for k in ui._STATES.values() if k not in i18n.CATALOG]
    assert not missing


# Calls that put text on screen, and which argument holds it.
SCREEN_TEXT_ARG = {
    "render": 0,
    "fit": 0,
    "text": 1,
    "card": 3,
    "marquee": 2,
    "draw_header": 1,
    "_draw_message": 1,
    "_draw_list": 1,
    "_hint": 1,
}


def _has_words(node: ast.AST) -> bool:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return any(c.isalpha() for c in node.value)
    if isinstance(node, ast.JoinedStr):
        return any(_has_words(v) for v in node.values if isinstance(v, ast.Constant))
    return False


def test_no_screen_text_is_written_outside_the_catalog():
    found = []
    for path in SOURCES:
        for call in _calls(ast.parse(path.read_text(encoding="utf-8"))):
            pos = SCREEN_TEXT_ARG.get(_name(call))
            if pos is not None and len(call.args) > pos and _has_words(call.args[pos]):
                found.append(f"{path.name}:{call.lineno}")
    assert not found, "texts on screen must come from i18n.t()"


@pytest.mark.parametrize(
    ("value", "lang"),
    [
        ("es", "es"),
        ("es_AR.UTF-8", "es"),
        ("es-419", "es"),
        ("ES", "es"),
        ("en", "en"),
        ("en_US.UTF-8", "en"),
        ('"en"', "en"),
        ("C.UTF-8", None),
        ("pt_BR.UTF-8", None),
        ("", None),
        (None, None),
    ],
)
def test_normalize(value, lang):
    assert i18n.normalize(value) == lang


@pytest.mark.parametrize(
    ("environ", "lang"),
    [
        ({"LANG": "es_AR.UTF-8"}, "es"),
        ({"LANG": "en_US.UTF-8"}, "en"),
        ({"LANG": "pt_BR.UTF-8"}, "en"),
        ({"LANG": "C.UTF-8"}, "en"),
        ({}, "en"),
        ({"LANG": "en_US.UTF-8", "LC_MESSAGES": "es_ES.UTF-8"}, "es"),
        ({"LANG": "es_AR.UTF-8", "LC_ALL": "en_GB.UTF-8"}, "en"),
        ({"LANG": "en_US.UTF-8", "LANGUAGE": "fr:es"}, "es"),
        ({"LANG": "es_AR.UTF-8", "LANGUAGE": "en"}, "es"),  # Spanish is still preferred
    ],
)
def test_from_locale(environ, lang):
    assert i18n.from_locale(environ) == lang


def write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def test_the_shipped_file_chooses_nothing():
    assert i18n.saved(SHIPPED_CONF) is None


def test_detect_order(tmp_path):
    conf = write(tmp_path / "language.conf", "# comment\nLANGUAGE=en\n")
    cmdline = write(tmp_path / "cmdline", "boot=live quiet rocola.lang=es\n")
    empty = write(tmp_path / "empty.conf", "LANGUAGE=\n")
    none = tmp_path / "missing"
    spanish = {"LANG": "es_AR.UTF-8"}

    assert i18n.detect(spanish, none, none) == "es"
    assert i18n.detect({"LANG": "en_US.UTF-8"}, empty, cmdline) == "es"  # boot entry
    assert i18n.detect(spanish, conf, cmdline) == "en"  # the saved choice wins
    assert i18n.detect({**spanish, "ROCOLA_LANG": "en"}, none, none) == "en"
    assert i18n.detect({**spanish, "ROCOLA_LANG": "xx"}, none, none) == "es"  # ignored


def test_save_keeps_the_comments(tmp_path):
    conf = write(tmp_path / "language.conf", SHIPPED_CONF.read_text(encoding="utf-8"))
    assert i18n.save("en", conf)
    assert i18n.saved(conf) == "en"
    assert i18n.save("es", conf)
    text = conf.read_text(encoding="utf-8")
    assert text.count("LANGUAGE=") == 1 and i18n.saved(conf) == "es"
    assert text.startswith("# Idioma de la rocola")


def test_save_never_raises(tmp_path):
    assert not i18n.save("en", tmp_path / "no" / "such" / "dir" / "language.conf")


@pytest.mark.skipif(shutil.which("bash") is None, reason="needs bash")
@pytest.mark.parametrize(
    ("environ", "conf", "cmdline"),
    [
        ({"LANG": "es_AR.UTF-8"}, "LANGUAGE=\n", ""),
        ({"LANG": "en_US.UTF-8"}, "LANGUAGE=\n", ""),
        ({"LANG": "C"}, "", ""),
        ({}, "", ""),
        ({"LANG": "en_US.UTF-8", "LANGUAGE": "fr:es_MX"}, "", ""),
        ({"LANG": "es_AR.UTF-8", "LC_ALL": "en_US.UTF-8"}, "", ""),
        ({"LANG": "es_AR.UTF-8", "LC_MESSAGES": "de_DE.UTF-8"}, "", ""),
        ({"LANG": "es_AR.UTF-8"}, "LANGUAGE=\n", "boot=live components rocola.lang=en quiet"),
        ({"LANG": "en_US.UTF-8"}, "# x\nLANGUAGE= es \n", "rocola.lang=en"),
        ({"LANG": "en_US.UTF-8"}, 'LANGUAGE="es"\n', ""),
        ({"LANG": "es_AR.UTF-8"}, "LANGUAGE=pt\n", "rocola.lang=xx"),
        ({"LANG": "es_AR.UTF-8", "ROCOLA_LANG": "en"}, "LANGUAGE=es\n", "rocola.lang=es"),
    ],
)
def test_shell_helper_agrees(tmp_path, environ, conf, cmdline):
    """rocola-lang (installer, console scripts) must pick what the app picks."""
    conf_path = write(tmp_path / "language.conf", conf)
    cmdline_path = write(tmp_path / "cmdline", cmdline)
    env = {"PATH": "/usr/bin:/bin", **environ}
    env.update(ROCOLA_LANGUAGE_CONF=str(conf_path), ROCOLA_CMDLINE=str(cmdline_path))
    out = subprocess.run(
        ["bash", str(ROCOLA_LANG_SH)], env=env, capture_output=True, text=True, check=True
    )
    assert out.stdout.strip() == i18n.detect(environ, conf_path, cmdline_path)


SONGS = [
    {"file": "a/1.mp3", "Artist": "Queen", "Album": "Jazz", "Title": "Mustapha"},
    {"file": "b/1.mp3", "Artist": "Soda Stereo", "Album": "Signos", "Title": "Signos"},
    {"file": "c/1.mp3", "Title": "Sin tags"},
]


def menu_app():
    app = rapp.RocolaApp.__new__(rapp.RocolaApp)  # no SDL, no MPD
    app.theme = None
    lib = ui.LibraryScene(app)
    lib.songs = SONGS
    lib.stack = library.reopen(SONGS, lib.stack)
    lib.stack.append(library.open_row(lib.view.rows[0]))  # inside "Todas las canciones"
    app.scenes = {"library": lib}
    return app, lib, ui.MenuScene(app)


def test_the_menu_switches_and_saves_the_language():
    app, lib, menu = menu_app()
    menu.index = menu.options.index("language")
    menu.handle(actions.SELECT)

    assert i18n.language() == "en"
    assert i18n.saved() == "en"
    assert lib.stack[0].rows[0].label == "All songs"
    assert lib.view.title == "All songs"  # still inside the same folder
    assert lib.stack[0].rows[-1].label == "(no artist)"
    assert menu.options[menu.index] == "language"

    menu.handle(actions.SELECT)
    assert i18n.language() == "es" and i18n.saved() == "es"
    assert lib.view.title == "Todas las canciones"


def test_theme_title_per_language(tmp_path):
    from rocola.theme import Theme

    write(tmp_path / "theme.toml", '[branding]\ntitle = { es = "MI ROCOLA", en = "MY JUKEBOX" }\n')
    theme = Theme.load(tmp_path)
    assert theme.title_for("es") == "MI ROCOLA"
    assert theme.title_for("en") == "MY JUKEBOX"
    write(tmp_path / "theme.toml", '[branding]\ntitle = { es = "BAR PEPE" }\n')
    assert Theme.load(tmp_path).title_for("en") == "BAR PEPE"
    write(tmp_path / "theme.toml", '[branding]\ntitle = "BAR PEPE"\n')
    assert Theme.load(tmp_path).title_for("en") == "BAR PEPE"
