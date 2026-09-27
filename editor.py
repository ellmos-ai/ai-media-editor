"""Thin compatibility shim -- the real implementation lives in
ai_media_editor/editor.py. Kept so `python editor.py ...` (as documented
in README/CLAUDE.md/docs/USECASES.md) keeps working without a package
install.
"""

from ai_media_editor.editor import main


if __name__ == "__main__":
    main()
