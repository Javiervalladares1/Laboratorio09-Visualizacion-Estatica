"""Coherencia interna de los insumos agregados en datos/."""
import json
import numpy as np
import pandas as pd
import pytest
from conftest import ROOT

DATA = ROOT/'datos'


@pytest.fixture(scope='module')
def serie():
    return pd.read_csv(DATA/'serie_total_mensual.csv', parse_dates=['Fecha']).set_index('Fecha').Ingresos


def test_serie_mensual_completa(serie):
    esperado = pd.date_range('2009-01-01', '2026-06-01', freq='MS')
    assert serie.index.equals(esperado)
    assert (serie >= 0).all()


def test_perfil_es_promedio_por_mes_hasta_2019(serie):
    perfil = pd.read_csv(DATA/'perfil_mensual_2009_2019.csv').set_index('Mes').Promedio_ingresos
    pre = serie.loc[:'2019-12-01']
    np.testing.assert_allclose(perfil.to_numpy(), pre.groupby(pre.index.month).mean().to_numpy())
    assert perfil.idxmax() == 12


def test_participaciones_suman_100_por_dimension():
    shares = pd.read_csv(DATA/'participaciones.csv')
    for _, grupo in shares.groupby('Dimension'):
        assert grupo.Porcentaje.sum() == pytest.approx(100)


def test_participacion_terrestre_coincide_con_resumen():
    shares = pd.read_csv(DATA/'participaciones.csv').set_index(['Dimension', 'Categoria'])
    resumen = json.loads((DATA/'resumen_lab1.json').read_text())
    assert shares.loc[('Vía', 'Terrestre'), 'Porcentaje'] == pytest.approx(resumen['participacion_terrestre_pct'])


def test_intervalo_contiene_estimacion():
    pred = pd.read_csv(DATA/'pronostico_prophet_intervalo95.csv')
    assert (pred.Inferior_95 >= 0).all()
    assert (pred.Inferior_95 <= pred.Estimacion_Prophet).all()
    assert (pred.Estimacion_Prophet <= pred.Superior_95).all()


def test_metadatos_coinciden_con_pronostico():
    pred = pd.read_csv(DATA/'pronostico_prophet_intervalo95.csv')
    meta = json.loads((DATA/'metadatos_intervalo.json').read_text())
    cobertura = ((pred.Real >= pred.Inferior_95) & (pred.Real <= pred.Superior_95)).mean()
    assert meta['n_test'] == len(pred)
    assert meta['cobertura_observada_intervalo_prueba'] == pytest.approx(cobertura)
    assert meta['MAE'] == pytest.approx((pred.Real-pred.Estimacion_Prophet).abs().mean())


def test_prophet_es_el_mejor_modelo_del_total():
    models = pd.read_csv(DATA/'modelos_total.csv')
    assert models.sort_values('RMSE').iloc[0].modelo == 'Prophet'
