import pytest
from data_engine.collector import Collector, collector


class TestCollector:
    def test_collector_init(self):
        c = Collector()
        assert c is not None
        assert c.cfg is not None

    def test_get_stock_kline(self):
        c = Collector()
        df = c.get_stock_kline('600000', start_date='2024-01-01', end_date='2024-01-10')
        assert df is not None
        if not df.empty:
            assert 'trade_date' in df.columns
            assert 'open' in df.columns
            assert 'close' in df.columns

    def test_get_all_concept_codes(self):
        c = Collector()
        df = c.get_all_concept_codes()
        assert df is not None
        if not df.empty:
            assert 'concept_code' in df.columns
            assert 'concept_name' in df.columns

    def test_get_concept_kline(self):
        c = Collector()
        df = c.get_all_concept_codes()
        if not df.empty:
            concept_code = df.iloc[0]['concept_code']
            kline = c.get_concept_kline(concept_code, k_type=1)
            assert kline is not None
            if not kline.empty:
                assert 'trade_date' in kline.columns

    def test_get_capital_flow(self):
        c = Collector()
        df = c.get_capital_flow('600000', start_date='2024-01-01', end_date='2024-01-10')
        assert df is not None
        if not df.empty:
            assert 'trade_date' in df.columns

    def test_get_hot_rank(self):
        c = Collector()
        df = c.get_hot_rank()
        assert df is not None
        if not df.empty:
            assert 'stock_code' in df.columns
            assert 'change_pct' in df.columns

    def test_get_billboard(self):
        c = Collector()
        df = c.get_billboard()
        assert df is not None
