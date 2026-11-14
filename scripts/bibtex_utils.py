"""BibTeX transport and exact alpha.bst keys, adapted from stratified.

Metadata words and fields come from the retained DOI response, never inference.
"""
import html
import re
import subprocess
import tempfile
import unicodedata
from pathlib import Path
BIBITEM_RE = re.compile(r"\\bibitem\[([^]]+)]\{([^}]+)}")

ACCENTS = {"\u0300": r"\`", "\u0301": r"\'", "\u0302": r"\^", "\u0303": r"\~",
           "\u0304": r"\=", "\u0306": r"\u", "\u0307": r"\.", "\u0308": r'\"',
           "\u030a": r"\r", "\u030b": r"\H", "\u030c": r"\v", "\u0323": r"\d",
           "\u0327": r"\c", "\u0328": r"\k", "\u0331": r"\b"}
SPECIAL_LETTERS = {"ø": r"\o", "Ø": r"\O", "æ": r"\ae", "Æ": r"\AE",
                   "œ": r"\oe", "Œ": r"\OE", "ß": r"\ss", "ł": r"\l", "Ł": r"\L"}


def bibtex_transport(text: str) -> str:
    """Encode API text for byte-oriented BibTeX; the cached API bytes stay exact."""
    for _ in range(3):
        decoded = html.unescape(text)
        if decoded == text:
            break
        text = decoded
    # Some DOI providers embed inline HTML in titles. Translate presentation
    # markup only; never infer missing words or repair the provider's metadata.
    tags = {"i": r"\emph{", "em": r"\emph{", "b": r"\textbf{",
            "strong": r"\textbf{", "sup": r"\textsuperscript{", "sub": r"\textsubscript{"}
    text = re.sub(r"<(\/?)(i|em|b|strong|sup|sub)\s*>",
                  lambda m: "}" if m[1] else tags[m[2].lower()], text, flags=re.I)
    # Crossref can encode a title's simple subscript as inline MathML.
    text = re.sub(
        r"<mml:math\b[^>]*><mml:msub>"
        r"<mml:mrow><mml:mi>([A-Za-z]+)</mml:mi></mml:mrow>"
        r"<mml:mrow><mml:mi>([A-Za-z0-9]+)</mml:mi></mml:mrow>"
        r"</mml:msub></mml:math>",
        lambda m: "{$" + m[1] + "_{" + m[2] + "}$}",
        text,
    )
    # DOI titles sometimes use display delimiters for an inline symbol.
    # Keep the formula intact and protect its case from alpha.bst.
    text = re.sub(r"\$\$(.*?)\$\$", lambda m: "{$" + m[1].strip() + "$}", text, flags=re.S)
    text = re.sub(r"(?<!\\)&", r"\\&", text)
    punctuation = {"–": "--", "—": "---", "‐": "-", "−": "-", "’": "'", "‘": "`",
                   "“": "``", "”": "''", "\u00a0": "~", "…": r"\ldots{}",
                   "∞": r"{\ensuremath{\infty}}", "ω": r"{\ensuremath{\omega}}",
                   "ℝ": r"{\ensuremath{\mathbb{R}}}",
                   "→": r"{\ensuremath{\to}}"}
    text = unicodedata.normalize("NFD", text)
    result, cursor = [], 0
    while cursor < len(text):
        char = text[cursor]
        cursor += 1
        encoded = char if ord(char) < 128 else punctuation.get(char)
        if char in SPECIAL_LETTERS:
            encoded = "{" + SPECIAL_LETTERS[char] + "}"
        if encoded is None:
            raise RuntimeError(f"unsupported Unicode metadata character U+{ord(char):04X} ({char})")
        while cursor < len(text) and unicodedata.combining(text[cursor]):
            accent = text[cursor]
            cursor += 1
            if accent not in ACCENTS:
                raise RuntimeError(f"unsupported metadata combining accent U+{ord(accent):04X}")
            encoded = "{" + ACCENTS[accent] + "{" + encoded + "}}"
        result.append(encoded)
    return "".join(result)


def safe_alpha_key(key: str) -> bool:
    return key not in {"", ".", ".."} and all(c.isalpha() or c.isdecimal() or c in ":+._-" for c in key)



def normalized_alpha_label(label: str) -> str:
    label = label.replace(r"{\etalchar{+}}", "+").replace(r"\etalchar{+}", "+")
    label = label.replace("{", "").replace("}", "")
    # alpha.bst retains author accents in labels. Decode their rendered letters
    # into NFC keys, rather than stripping accents or putting TeX in pathnames.
    for combining, macro in ACCENTS.items():
        label = re.sub(re.escape(macro) + r"\s*([^\W\d_])",
                       lambda m: unicodedata.normalize("NFC", m[1] + combining), label)
    for letter, macro in sorted(SPECIAL_LETTERS.items(), key=lambda item: -len(item[1])):
        label = label.replace(macro, letter)
    label = unicodedata.normalize("NFC", label)
    if not safe_alpha_key(label):
        raise RuntimeError(f"alpha label is unsafe as a directory name: {label!r}")
    return label


def compute_alpha_labels(entries: list[str]) -> dict[str, str]:
    with tempfile.TemporaryDirectory(prefix="research-alpha-") as raw_tmp:
        tmp = Path(raw_tmp)
        (tmp / "records.bib").write_text("\n\n".join(entries) + "\n", encoding="utf-8")
        (tmp / "labels.tex").write_text(
            "\\documentclass{article}\n"
            "\\begin{document}\n"
            "\\nocite{*}\n"
            "\\bibliographystyle{alpha}\n"
            "\\bibliography{records}\n"
            "\\end{document}\n",
            encoding="utf-8",
        )
        subprocess.run(["pdflatex", "-no-shell-escape", "-halt-on-error", "-interaction=batchmode", "labels.tex"], cwd=tmp, check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=60)
        subprocess.run(["bibtex", "labels"], cwd=tmp, check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=60)
        bbl = (tmp / "labels.bbl").read_text(encoding="utf-8")
    labels = {key: normalized_alpha_label(label) for label, key in BIBITEM_RE.findall(bbl)}
    if len(labels) != len(entries):
        raise RuntimeError(f"BibTeX emitted {len(labels)} labels for {len(entries)} records")
    if len(set(labels.values())) != len(labels):
        raise RuntimeError("BibTeX emitted duplicate alpha labels")
    return labels
