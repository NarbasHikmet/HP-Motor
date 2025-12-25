import pandas as pd

from hp_motor.data_gateway import read_csv_bytes, read_xml_bytes


def test_csv_delimiter_semicolon():
    df = read_csv_bytes(b"a;b;c\n1;2;3\n4;5;6\n")
    assert list(df.columns) == ["a", "b", "c"]
    assert df.shape == (2, 3)


def test_csv_utf8_sig_bom():
    df = read_csv_bytes(b"\xef\xbb\xbfCol 1,Col-2\nx,y\n")
    assert list(df.columns) == ["col_1", "col_2"]
    assert df.shape == (1, 2)


def test_xml_flatten_nested_records():
    xml = b"""<?xml version="1.0"?>
    <root>
      <rows>
        <row><id>1</id><team><name>A</name></team></row>
        <row><id>2</id><team><name>B</name></team></row>
      </rows>
    </root>
    """
    df = read_xml_bytes(xml)
    assert isinstance(df, pd.DataFrame)
    assert df.shape[0] == 2
    # nested path should become columns after normalization
    # examples: row__team__name => row_team_name (after canonicalization)
    assert any("team" in c and "name" in c for c in df.columns)


def test_xml_single_record():
    xml = b"""<?xml version="1.0"?>
    <match><id>10</id><team>A</team></match>
    """
    df = read_xml_bytes(xml)
    assert df.shape[0] == 1
    assert "match_id" in df.columns or "id" in df.columns
