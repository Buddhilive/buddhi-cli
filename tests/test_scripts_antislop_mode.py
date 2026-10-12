from pathlib import Path

import pytest

from buddhi.scripts.antislop_mode import (
    configure_mode,
    read_settings,
    resolve_settings_path,
)


def test_resolve_settings_path_windows() -> None:
    p = resolve_settings_path(
        platform="win32",
        env={"APPDATA": "C:\\Users\\test\\AppData\\Roaming"},
        home="C:\\Users\\test",
    )
    assert p == Path("C:\\Users\\test\\AppData\\Roaming\\antislop\\settings.json")


def test_resolve_settings_path_posix() -> None:
    p = resolve_settings_path(
        platform="linux",
        env={},
        home="/home/test",
    )
    assert p == Path("/home/test/.config/antislop/settings.json")


def test_read_settings_missing_file(tmp_path: Path) -> None:
    file = tmp_path / "settings.json"
    assert read_settings(file) == {}


def test_read_settings_invalid_json(tmp_path: Path) -> None:
    file = tmp_path / "settings.json"
    file.write_text("{not-valid-json", encoding="utf-8")
    with pytest.raises(ValueError, match="Cannot read"):
        read_settings(file)


def test_read_settings_non_dict(tmp_path: Path) -> None:
    file = tmp_path / "settings.json"
    file.write_text('["item"]', encoding="utf-8")
    with pytest.raises(ValueError, match="Expected a JSON object"):
        read_settings(file)


def test_configure_mode_get_default(tmp_path: Path) -> None:
    file = tmp_path / "settings.json"
    msg = configure_mode(None, file=file)
    assert "antislop global mode: ask (default)" in msg
    assert str(file) in msg
    # Should not create the file on read
    assert not file.exists()


def test_configure_mode_set_and_get(tmp_path: Path) -> None:
    file = tmp_path / "settings.json"
    msg = configure_mode("during", file=file)
    assert "antislop global mode: during" in msg
    assert "(default)" not in msg
    assert file.exists()

    # Reading it back
    msg2 = configure_mode(None, file=file)
    assert "antislop global mode: during" in msg2
    assert "(default)" not in msg2


def test_configure_mode_invalid_mode(tmp_path: Path) -> None:
    file = tmp_path / "settings.json"
    with pytest.raises(ValueError, match="Invalid mode"):
        configure_mode("unsupported_mode", file=file)


def test_configure_mode_does_not_overwrite_corrupt_file(tmp_path: Path) -> None:
    file = tmp_path / "settings.json"
    file.write_text("{corrupt", encoding="utf-8")
    with pytest.raises(ValueError, match="Fix or delete it"):
        configure_mode("during", file=file)
    assert file.read_text(encoding="utf-8") == "{corrupt"
