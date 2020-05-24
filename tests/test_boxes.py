#!/usr/bin/env python3

from rcli.display.box import Box, box
from rcli.display.style import Alignment, Style


def test_simple_box():
    print()
    with box():
        print("Test 0")


def test_simple_box_sep():
    print()
    with box() as b:
        print("Test 1")
        b.sep()
        print("Test 1")


def test_no_flush():
    print()
    with Style(43):
        with box() as b:
            print("Test 2")
            b.sep()
            print("Test", end="")
            print(" 2")


def test_styled_sep_box():
    print()
    with box() as b:
        print("Test 3")
        b.sep()
        with Style(30, 45):
            print("Test 3")
        b.sep()
        print("Test 3")


def test_background_in_row():
    print()
    with Style(42):
        with box() as b:
            print("Test 4")
            b.sep()
            with Style(43):
                print("Test 4")
            b.sep()
            print("Test 4")


def test_info_box():
    print()
    with Box.info() as b:
        print("Test 5")
        b.sep()
        print("Test 5")


def test_ascii_box():
    print()
    with Box.ascii() as b:
        print("Test 6")
        b.sep()
        print("Test 6")


def test_thick_box():
    print()
    with Box.thick() as b:
        print("Test 7")
        b.sep()
        print("Test 7")


def test_star_box():
    print()
    with Box.star() as b:
        print("Test 8")
        b.sep()
        print("Test 8")


def test_double_box():
    print()
    with Box.double() as b:
        print("Test 9")
        b.sep()
        print("Test 9")


def test_fancy_box():
    print()
    with Box.fancy() as b:
        print("Test 10")
        b.sep()
        print("Test 10")


def test_colored_box_white_text():
    print()
    with Style(31), box() as b, Style(39):
        print("Test 11")
        b.sep()
        print("Test 11")


def test_nested_boxes():
    print()
    with box(), box():
        print("Test 12")


def test_deeply_nested_boxes():
    print()
    with box(), Box.fancy(), Box.double(), Box.ascii():
        print("Test 13")


def test_nested_boxes_with_colors_and_rows():
    print()
    with Style(31), Box.fancy():
        with Style(35), box(), Style(32), Box.thick(), Style(30, 45):
            print("Test 14")
        with Style(33), Box.double(), Style(39):
            print("Test 14")


def test_round_box():
    print()
    with Box.round() as b:
        print("Test 15")
        b.sep()
        print("Test 15")


def test_set_width_boxes():
    print()
    with box(size=40), box(size=20):
        print("Test 16")


def test_colored_set_width_boxes():
    print()
    with Style(39, 44), Box.thick(size=40):
        with Style(31, 42), box(size=20), Style(30):
            print("Test 17")
        with Style(30, 41), box(size=30), Style(39), box(), Style(30, 47):
            print("Test 17")
        with Style(33, 49), box(size=35), Style(39):
            print("Test 17")


def test_colored_nested_boxes_with_separator():
    print()
    with Style(31), Box.round(), Style(34), box() as b2, Style(39):
        print("Test 18")
        b2.sep()
        print("Test 18")


def test_colored_deeply_nested_boxes_with_separator():
    print()
    with Style(31), Box.round() as b1, Style(39):
        print("Test 19")
        b1.sep()
        with Style(34), box() as b2, Style(39):
            print("Test 19")
            b2.sep()
            print("Test 19")
            b2.sep()
            with Style(33), box() as b3, Style(39):
                print("Test 19")
                b3.sep()
                print("Test 19")
        b1.sep()
        print("Test 19")


def test_box_with_headers():
    print()
    with Box.thick(
        header="Test 20", footer="Test 20", footer_align=Alignment.RIGHT
    ) as b:
        print("Test 20")
        b.sep("Test 20", align=Alignment.CENTER)
        b.sep(" Test 20", align=Alignment.CENTER)
        b.sep("Test 20 ", align=Alignment.CENTER)
        print("Test 20")


def test_box_with_headers_single_align():
    print()
    with Box.thick(
        header="Test 21", footer="Test 21", align=Alignment.CENTER
    ) as b:
        print("Test 21")
        b.sep("Test 21")
        print("Test 21")
