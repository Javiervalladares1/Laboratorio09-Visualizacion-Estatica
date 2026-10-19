"""Pruebas de las utilidades de dibujo de scripts/crear_infografia.py."""
import xml.etree.ElementTree as ET
import pytest
import crear_infografia as ci


@pytest.mark.parametrize('valor,dec,esperado', [
    (58032.6, 0, '58 033'),
    (46712345.0, 0, '46 712 345'),
    (0.547, 3, '0,547'),
    (-74.44, 1, '-74,4'),
])
def test_fmt_usa_convenciones_en_espanol(valor, dec, esperado):
    assert ci.fmt(valor, dec) == esperado


@pytest.fixture
def lienzo(tmp_path):
    return ci.Artwork(tmp_path/'prueba.pdf', ci.A3)


def test_texto_fuera_de_margen_falla(lienzo):
    with pytest.raises(ValueError, match='fuera de márgenes'):
        lienzo.text(ci.W-ci.M, 100, 'Texto demasiado largo para el borde', 12)


def test_texto_se_registra_y_escapa_en_svg(lienzo):
    lienzo.text(ci.M, 100, 'A & B < C', 10)
    assert lienzo.text_records[-1]['text'] == 'A & B < C'
    assert '&amp;' in lienzo.svg[-1] and '&lt;' in lienzo.svg[-1]


def test_parrafo_respeta_ancho_maximo(lienzo):
    texto = 'Reforzar atención y transporte antes de diciembre; revisar marzo y julio. '*3
    lienzo.para(ci.M, 200, texto, 200, 9.2)
    lineas = [r for r in lienzo.text_records if r['y'] >= 200]
    assert len(lineas) > 1
    assert all(r['width'] <= 200 for r in lineas)


def test_composicion_completa_dentro_de_margenes(lienzo):
    ci.draw(lienzo)
    raiz = ET.fromstring('\n'.join(lienzo.svg+['</svg>']))
    textos = [t for t in raiz if t.tag.endswith('text')]
    assert len(textos) == len(lienzo.text_records) > 100
    assert all(ci.M-20 <= r['x'] and r['x']+r['width'] <= ci.W-ci.M+3 for r in lienzo.text_records)
