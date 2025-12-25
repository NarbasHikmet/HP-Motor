from hp_motor.data_gateway import read_csv_bytes, read_xml_bytes


def test_csv_semicolon_smoke():
    df = read_csv_bytes(b"a;b\n1;2\n")
    assert df.shape == (1, 2)


def test_xml_smoke():
    df = read_xml_bytes(b'<?xml version="1.0"?><root><row><id>1</id></row></root>')
    assert len(df) >= 1
    assert df.shape[1] >= 1
