"""
tests/test_consolidation.py
============================
Unit tests for fx-consolidation-engine

Run: pytest tests/ -v
"""
import sys, os, csv, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from consolidation import (translate, load_trial_balance, load_eliminations, consolidate, export_csv,
                           translate_trial_balance, summarize, intercompany_residual, net, CTA_CODE)

F = os.path.join(os.path.dirname(__file__), 'fixtures')

class TestTranslate:
    def test_usd_identity(self):          assert translate(1000.0,'USD','USD','average') == 1000.0
    def test_cad_average(self):           assert translate(10000.0,'CAD','USD','average') == pytest.approx(7400.0, rel=1e-4)
    def test_cad_closing(self):           assert translate(10000.0,'CAD','USD','closing') == pytest.approx(7350.0, rel=1e-4)
    def test_gbp_average(self):           assert translate(10000.0,'GBP','USD','average') == pytest.approx(12700.0, rel=1e-4)
    def test_gbp_closing(self):           assert translate(10000.0,'GBP','USD','closing') == pytest.approx(12650.0, rel=1e-4)
    def test_zero_amount(self):           assert translate(0.0,'CAD','USD','average') == 0.0
    def test_cad_historical(self):        assert translate(10000.0,'CAD','USD','historical') == pytest.approx(7800.0, rel=1e-4)
    def test_unknown_currency_raises(self):
        with pytest.raises(ValueError, match="No FX rate"):
            translate(1000.0,'EUR','USD','average')
    def test_unknown_rate_type_raises(self):
        with pytest.raises(ValueError, match="Unknown rate type"):
            translate(1000.0,'CAD','USD','spot')

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

def _row(code, typ, dr, cr, ccy):
    return {'code':code,'name':code,'type':typ,'debit':dr,'credit':cr,'ccy':ccy}

class TestTranslationMethod:
    """IAS 21 current rate method: closing for B/S, average for P&L, historical for equity."""
    def test_rate_types_by_account(self):
        tb = [_row('1000','ASSET',1000,0,'CAD'), _row('3000','EQUITY',0,600,'CAD'),
              _row('4000','REVENUE',0,400,'CAD')]
        rates = {r['code']: r['rate_type'] for r in translate_trial_balance(tb, 'B')}
        assert rates == {'1000':'closing','3000':'historical','4000':'average','3900':'derived'}

    def test_translation_difference_booked_to_cta(self):
        tb = [_row('1000','ASSET',1000,0,'CAD'), _row('3000','EQUITY',0,1000,'CAD')]
        rows = translate_trial_balance(tb, 'B')
        cta = [r for r in rows if r['code'] == CTA_CODE][0]
        # Asset 735 at closing vs equity 780 at historical -> 45 translation loss (debit CTA)
        assert cta['usd_debit'] == pytest.approx(45.0) and cta['usd_credit'] == 0.0
        assert sum(r['usd_debit'] for r in rows) == pytest.approx(sum(r['usd_credit'] for r in rows))

    def test_usd_entity_has_no_cta(self):
        tb = [_row('1000','ASSET',500,0,'USD'), _row('3000','EQUITY',0,500,'USD')]
        assert all(r['code'] != CTA_CODE for r in translate_trial_balance(tb, 'A'))

    def test_unbalanced_trial_balance_rejected(self):
        with pytest.raises(ValueError, match="does not balance"):
            translate_trial_balance([_row('1000','ASSET',100,0,'USD')], 'A')

class TestConsolidationAccuracy:
    @pytest.fixture
    def result(self):
        entities = [('Entity A (USD)', load_trial_balance(f'{F}/entity_a_usd.csv')),
                    ('Entity B (CAD)', load_trial_balance(f'{F}/entity_b_cad.csv')),
                    ('Entity C (GBP)', load_trial_balance(f'{F}/entity_c_gbp.csv'))]
        elims = load_eliminations(f'{F}/intercompany_eliminations.csv')
        return consolidate(entities, elims), elims

    def test_fixture_trial_balances_balance(self):
        for name in ('entity_a_usd','entity_b_cad','entity_c_gbp'):
            rows = load_trial_balance(f'{F}/{name}.csv')
            assert sum(r['debit'] for r in rows) == pytest.approx(sum(r['credit'] for r in rows))

    def test_balance_sheet_balances(self, result):
        ledger, _ = result
        assert summarize(ledger)['balance_difference'] == pytest.approx(0.0, abs=0.01)

    def test_consolidated_ledger_balances(self, result):
        ledger, _ = result
        assert sum(r['total_debit'] for r in ledger.values()) == pytest.approx(
               sum(r['total_credit'] for r in ledger.values()), abs=0.01)

    def test_intercompany_fully_eliminated(self, result):
        ledger, elims = result
        assert intercompany_residual(ledger, elims) == {}
        for code in ('1200','2050','4030','6080'):
            assert net(ledger[code]) == pytest.approx(0.0, abs=0.01)

    def test_eliminations_do_not_change_net_income(self):
        entities = [('A', load_trial_balance(f'{F}/entity_a_usd.csv')),
                    ('B', load_trial_balance(f'{F}/entity_b_cad.csv'))]
        elims = load_eliminations(f'{F}/intercompany_eliminations.csv')
        assert summarize(consolidate(entities, elims))['net_income'] == pytest.approx(
               summarize(consolidate(entities, []))['net_income'])

    def test_cta_is_translation_loss(self, result):
        # CAD and GBP weakened against historical rates, so net assets lost value
        ledger, _ = result
        assert summarize(ledger)['cta'] < 0

    def test_conflicting_account_types_rejected(self):
        a = [_row('1400','ASSET',100,0,'USD'), _row('3000','EQUITY',0,100,'USD')]
        b = [_row('1400','LIABILITY',0,100,'USD'), _row('1000','ASSET',100,0,'USD')]
        with pytest.raises(ValueError, match="common group chart"):
            consolidate([('A',a),('B',b)], [])

    def test_unbalanced_eliminations_rejected(self):
        a = [_row('1000','ASSET',100,0,'USD'), _row('3000','EQUITY',0,100,'USD')]
        elim = [{'description':'x','account_code':'1000','elim_debit':0.0,'elim_credit':50.0}]
        with pytest.raises(ValueError, match="do not balance"):
            consolidate([('A',a)], elim)

    def test_elimination_to_unknown_account_rejected(self):
        a = [_row('1000','ASSET',100,0,'USD'), _row('3000','EQUITY',0,100,'USD')]
        elims = [{'description':'x','account_code':'9999','elim_debit':10.0,'elim_credit':0.0},
                 {'description':'y','account_code':'1000','elim_debit':0.0,'elim_credit':10.0}]
        with pytest.raises(ValueError, match="not in any trial balance"):
            consolidate([('A',a)], elims)

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
        with open(out, newline='', encoding='utf-8-sig') as f:
            rows = list(csv.DictReader(f))
        assert len(rows) > 0 and 'code' in rows[0] and 'net_usd' in rows[0]
