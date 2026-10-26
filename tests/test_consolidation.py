"""
tests/test_consolidation.py
============================
Unit tests for fx-consolidation-engine

Run: pytest tests/ -v
"""
import sys, os, csv, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from consolidation import translate, load_trial_balance, load_eliminations, consolidate, export_csv

F = os.path.join(os.path.dirname(__file__), 'fixtures')

class TestTranslate:
    def test_usd_identity(self):          assert translate(1000.0,'USD','USD','average') == 1000.0
    def test_cad_average(self):           assert translate(10000.0,'CAD','USD','average') == pytest.approx(7400.0, rel=1e-4)
    def test_cad_closing(self):           assert translate(10000.0,'CAD','USD','closing') == pytest.approx(7350.0, rel=1e-4)
    def test_gbp_average(self):           assert translate(10000.0,'GBP','USD','average') == pytest.approx(12700.0, rel=1e-4)
    def test_gbp_closing(self):           assert translate(10000.0,'GBP','USD','closing') == pytest.approx(12650.0, rel=1e-4)
    def test_zero_amount(self):           assert translate(0.0,'CAD','USD','average') == 0.0
    def test_unknown_currency_raises(self):
        with pytest.raises(ValueError, match="No FX rate"):
            translate(1000.0,'EUR','USD','average')

class TestLoadTrialBalance:
    def test_entity_a_loads(self):        assert len(load_trial_balance(f'{F}/entity_a_usd.csv')) > 0
    def test_entity_b_cad_currency(self): assert all(r['ccy']=='CAD' for r in load_trial_balance(f'{F}/entity_b_cad.csv'))
    def test_entity_c_gbp_currency(self): assert all(r['ccy']=='GBP' for r in load_trial_balance(f'{F}/entity_c_gbp.csv'))
    def test_required_keys(self):
        row = load_trial_balance(f'{F}/entity_a_usd.csv')[0]
        assert {'code','name','type','debit','credit','ccy'}.issubset(row.keys())
    def test_amounts_are_floats(self):
        rows = load_trial_balance(f'{F}/entity_a_usd.csv')
        assert all(isinstance(r['debit'],float) and isinstance(r['credit'],float) for r in rows)
    def test_has_revenue_and_asset_types(self):
        types = {r['type'] for r in load_trial_balance(f'{F}/entity_a_usd.csv')}
        assert 'REVENUE' in types and 'ASSET' in types

class TestLoadEliminations:
    def test_loads(self):                 assert len(load_eliminations(f'{F}/intercompany_eliminations.csv')) > 0
    def test_required_keys(self):
        e = load_eliminations(f'{F}/intercompany_eliminations.csv')[0]
        assert {'account_code','account_name','account_type','entity','elim_debit','elim_credit'}.issubset(e.keys())
    def test_amounts_are_floats(self):
        elims = load_eliminations(f'{F}/intercompany_eliminations.csv')
        assert all(isinstance(e['elim_debit'],float) for e in elims)

class TestConsolidate:
    @pytest.fixture
    def all_data(self):
        a = load_trial_balance(f'{F}/entity_a_usd.csv')
        b = load_trial_balance(f'{F}/entity_b_cad.csv')
        c = load_trial_balance(f'{F}/entity_c_gbp.csv')
        e = load_eliminations(f'{F}/intercompany_eliminations.csv')
        return a, b, c, e

    def test_returns_dict(self, all_data):
        a,b,c,e = all_data
        assert isinstance(consolidate([('A',a),('B',b),('C',c)], e), dict)

    def test_ledger_has_accounts(self, all_data):
        a,b,c,e = all_data
        assert len(consolidate([('A',a),('B',b),('C',c)], e)) > 10

    def test_required_ledger_keys(self, all_data):
        a,b,c,e = all_data
        ledger = consolidate([('A',a),('B',b),('C',c)], e)
        for row in ledger.values():
            assert {'code','name','type','total_debit','total_credit'}.issubset(row.keys())

    def test_empty_eliminations_works(self, all_data):
        a,b,c,e = all_data
        ledger = consolidate([('A',a)], [])
        assert len(ledger) > 0

    def test_amounts_are_numeric(self, all_data):
        a,b,c,e = all_data
        ledger = consolidate([('A',a),('B',b),('C',c)], e)
        for row in ledger.values():
            assert isinstance(row['total_debit'], float)
            assert isinstance(row['total_credit'], float)

    def test_account_types_present(self, all_data):
        a,b,c,e = all_data
        ledger = consolidate([('A',a),('B',b),('C',c)], e)
        types = {v['type'] for v in ledger.values()}
        assert 'REVENUE' in types and 'ASSET' in types

class TestIntegration:
    def test_full_pipeline(self):
        a = load_trial_balance(f'{F}/entity_a_usd.csv')
        b = load_trial_balance(f'{F}/entity_b_cad.csv')
        c = load_trial_balance(f'{F}/entity_c_gbp.csv')
        e = load_eliminations(f'{F}/intercompany_eliminations.csv')
        ledger = consolidate([('A',a),('B',b),('C',c)], e)
        assert len(ledger) > 15

    def test_csv_export(self, tmp_path):
        a = load_trial_balance(f'{F}/entity_a_usd.csv')
        ledger = consolidate([('A',a)], [])
        out = str(tmp_path / 'out.csv')
        export_csv(ledger, out)
        assert os.path.exists(out)
        rows = list(csv.DictReader(open(out)))
        assert len(rows) > 0 and 'code' in rows[0] and 'net_usd' in rows[0]
