from zsim.lib_webui import process_apl_editor as apl_editor


def test_apl_archive_bootstraps_missing_custom_dir(tmp_path, monkeypatch):
    default_apl_dir = tmp_path / "APLData"
    custom_apl_dir = default_apl_dir / "custom"
    default_apl_dir.mkdir()
    (default_apl_dir / "sample.toml").write_text(
        """
[general]
title = "Test APL"

[apl_logic]
logic = "1|action+=|wait"
""".strip(),
        encoding="utf-8",
    )

    warnings: list[str] = []
    monkeypatch.setattr(apl_editor, "DEFAULT_APL_DIR", str(default_apl_dir))
    monkeypatch.setattr(apl_editor, "COSTOM_APL_DIR", str(custom_apl_dir))
    monkeypatch.setattr(apl_editor.st, "warning", warnings.append)

    archive = apl_editor.APLArchive()

    assert custom_apl_dir.is_dir()
    assert warnings == []
    assert "Test APL" in archive.options
