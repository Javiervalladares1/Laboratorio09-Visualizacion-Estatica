"""Pruebas con copias temporales: los insumos originales nunca se modifican."""
from pathlib import Path
import json
import shutil
import sys
import tempfile
import unittest
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from verificar_entrega import validate_data


class VerificacionDatosTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        shutil.copytree(ROOT / 'datos', self.root / 'datos')

    def modify(self, filename, transform):
        path = self.root / 'datos' / filename
        frame = pd.read_csv(path)
        transform(frame).to_csv(path, index=False)

    def test_insumos_originales_y_seis_modelos(self):
        report = validate_data(self.root)
        self.assertEqual(report['meses_total'], 210)
        self.assertEqual(len(report['modelos_verificados']), 6)
        self.assertAlmostEqual(report['RMSE'], 69294.01007887268)

    def test_predicciones_reordenadas_se_alinean_por_fecha(self):
        self.modify('predicciones_total_lab1.csv', lambda x: x.sample(frac=1, random_state=9))
        self.modify('pronostico_prophet_intervalo95.csv', lambda x: x.iloc[::-1])
        self.assertAlmostEqual(validate_data(self.root)['MAE'], 58032.59940990989)

    def test_mes_duplicado_aunque_se_conserven_conteo_y_extremos(self):
        def duplicate(frame):
            frame.loc[10, 'Fecha'] = frame.loc[9, 'Fecha']
            return frame
        self.modify('serie_total_mensual.csv', duplicate)
        with self.assertRaisesRegex(ValueError, 'duplicadas'):
            validate_data(self.root)

    def test_mes_faltante(self):
        self.modify('pronostico_prophet_intervalo95.csv', lambda x: x.drop(index=10))
        with self.assertRaisesRegex(ValueError, 'faltan o sobran meses'):
            validate_data(self.root)

    def test_fecha_desplazada_con_valores_intactos(self):
        def shift(frame):
            frame.loc[0, 'Fecha'] = '2021-03-01'
            return frame
        self.modify('predicciones_total_lab1.csv', shift)
        with self.assertRaisesRegex(ValueError, 'faltan o sobran meses'):
            validate_data(self.root)

    def test_valor_no_finito(self):
        self.modify('pronostico_prophet_intervalo95.csv', lambda x: x.assign(Superior_95=np.inf))
        with self.assertRaisesRegex(ValueError, 'no finitos'):
            validate_data(self.root)

    def test_intervalo_invertido(self):
        self.modify('pronostico_prophet_intervalo95.csv', lambda x: x.assign(Inferior_95=x.Superior_95 + 1))
        with self.assertRaisesRegex(ValueError, 'Intervalos invertidos'):
            validate_data(self.root)

    def test_error_en_modelo_distinto_del_ganador(self):
        def alter(frame):
            frame.loc[frame.modelo == 'Holt-Winters', 'RMSE'] += 100
            return frame
        self.modify('modelos_total.csv', alter)
        with self.assertRaisesRegex(ValueError, 'Holt-Winters'):
            validate_data(self.root)

    def test_perfil_mensual_desactualizado(self):
        self.modify('perfil_mensual_2009_2019.csv', lambda x: x.assign(Promedio_ingresos=x.Promedio_ingresos + 1))
        with self.assertRaisesRegex(ValueError, 'perfil mensual no coincide'):
            validate_data(self.root)

    def test_participaciones_con_denominador_incorrecto(self):
        self.modify('participaciones.csv', lambda x: x.assign(Porcentaje=x.Porcentaje * .5))
        with self.assertRaisesRegex(ValueError, 'Denominador incorrecto'):
            validate_data(self.root)

    def test_cobertura_de_intervalo_desactualizada(self):
        path = self.root / 'datos' / 'metadatos_intervalo.json'
        meta = json.loads(path.read_text(encoding='utf-8'))
        meta['cobertura_observada_intervalo_prueba'] = .95
        path.write_text(json.dumps(meta), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'Cobertura del intervalo'):
            validate_data(self.root)

    def test_esquema_incompleto(self):
        self.modify('serie_total_mensual.csv', lambda x: x.drop(columns='Ingresos'))
        with self.assertRaisesRegex(ValueError, 'faltan columnas'):
            validate_data(self.root)


if __name__ == '__main__':
    unittest.main()
