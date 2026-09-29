from data_joinery.cli import main


def test_main_displays_help(capsys) -> None:
    main([])

    assert "usage: data-joinery" in capsys.readouterr().out
