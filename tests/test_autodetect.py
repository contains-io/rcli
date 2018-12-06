from rcli.autodetect import _ensure_entry_points_is_dict


def test_ensure_entry_points_is_dict_works_with_none():
    assert _ensure_entry_points_is_dict(None) == {}


def test_ensure_entry_points_is_dict_works_with_dict():
    expected = {
        'console_scripts': ['foobarbaz=foo.bar:baz'],
    }
    assert _ensure_entry_points_is_dict(expected) == expected


def test_ensure_entry_points_is_dict_works_with_str():
    assert _ensure_entry_points_is_dict('''
    [console_scripts]
    foobarbaz=foo.bar:baz
    ''') == {
        'console_scripts': ['foobarbaz=foo.bar:baz'],
    }
