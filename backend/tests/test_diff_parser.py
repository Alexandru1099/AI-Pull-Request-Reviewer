from app.diff_parser import ParsedHunk, ParsedLine, parse_unified_diff


def test_parse_unified_diff_single_hunk():
    patch = """@@ -1,3 +1,4 @@
 line1
-line2
+line2 changed
 line3
+line4
"""
    hunks = parse_unified_diff(patch)

    assert len(hunks) == 1
    hunk = hunks[0]
    assert hunk.old_start == 1
    assert hunk.old_count == 3
    assert hunk.new_start == 1
    assert hunk.new_count == 4

    # types of lines in order
    types = [line.type for line in hunk.lines]
    assert types == ["context", "removed", "added", "context", "added"]


def test_parse_unified_diff_multiple_hunks():
    patch = """@@ -1,2 +1,2 @@
-a
+b
 c
@@ -10,1 +10,2 @@
-x
+y
+z
"""
    hunks = parse_unified_diff(patch)
    assert len(hunks) == 2

    first, second = hunks
    assert first.old_start == 1
    assert second.old_start == 10


def test_parse_unified_diff_ignores_no_newline_marker():
    patch = """@@ -1,1 +1,1 @@
-a
+a
\\ No newline at end of file
"""
    hunks = parse_unified_diff(patch)
    assert len(hunks) == 1
    lines = hunks[0].lines
    # No line for the "\ No newline..." marker
    assert [line.type for line in lines] == ["removed", "added"]


def test_parse_unified_diff_empty_or_none():
    assert parse_unified_diff("") == []
    assert parse_unified_diff(None) == []

