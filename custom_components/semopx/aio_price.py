import asyncio
import logging
import aiohttp
import backoff
from datetime import date, datetime, timedelta
from dateutil.parser import parse as parse_dt
from pytz import timezone
from pytz import all_timezones

_LOGGER = logging.getLogger(__name__)


class InvalidValueException(ValueError):
    pass


class CurrencyMismatch(ValueError):
    pass


class AioPrices:
    """Interface"""

    def __init__(self, currency='euro', client=None, timeezone=None, market_area="ROI", tz="Europe/Dublin"):
        self.client = client or aiohttp.ClientSession()
        self.timeezone = timeezone
        self.currency = currency
        self.market_area = market_area
        self.timezone = tz
        self.SEMOPX_API_QUERY_URL = 'https://reports.semopx.com/api/v1/documents/static-reports'
        self.SEMOPX_API_RETRIEVAL_URL = 'https://reports.semopx.com/api/v1/documents'
        self.params = {
            'DPuG_ID': 'EA-001',
            'sort_by': 'Date',
            'order_by': 'DESC',
            'ExcludeDelayedPublication': '0'
        }

    async def _async_fetch(self, url, params=None):
        async with self.client.get(url, params=params) as resp:
            _LOGGER.debug("requested %s with params %s", resp.url, params)
            if resp.status == 204:
                return None
            return await resp.json()

    @backoff.on_exception(
        backoff.expo, (aiohttp.ClientError, KeyError), logger=_LOGGER, max_value=20
    )
    async def fetch(self, data_type=None, end_date=None, areas=None, raw=False):
        """Fetch data from SEMOpx API."""
        report_dict = await self._fetch_semopx_json(days=5)
        return await self._retrieve_market_results(report_dict)

    async def _fetch_semopx_json(self, days=5):
        """Fetch JSON from SEMOpx API."""
        page = 0
        report_dict = {}

        while True:
            await asyncio.sleep(1)
            page += 1
            self.params['page'] = page
            semopx_resp_dict = await self._async_fetch(self.SEMOPX_API_QUERY_URL, params=self.params)

            for item_rec in semopx_resp_dict['items']:
                key_date = item_rec['Date'][:10]
                if key_date not in report_dict:
                    report = {'date': key_date, 'resources': []}
                    report_dict[key_date] = report
                report['resources'].append(item_rec['ResourceName'])

            total_pages = semopx_resp_dict['pagination']['totalPages']
            if page >= total_pages or len(report_dict) > days:
                break

        return report_dict

    async def _retrieve_market_results(self, report_dict):
        """Retrieve market results from SEMOpx API."""
        rec_dict = {}
        for key, report in report_dict.items():
            for resource_name in report['resources']:
                url = f'{self.SEMOPX_API_RETRIEVAL_URL}/{resource_name}'
                semopx_resp_dict = await self._async_fetch(url)

                if not semopx_resp_dict:
                    _LOGGER.error("Failed to fetch data for resource: %s", resource_name)
                    continue

                context_prefix = self._determine_context_prefix(resource_name)
                if not context_prefix:
                    continue

                for data_set_list in semopx_resp_dict.get('rows', []):
                    if self.market_area not in data_set_list[0][1]:
                        continue

                    key_list = [self._parse_semopx_time(date_str) for date_str in data_set_list[2]]
                    self._merge_prices(rec_dict, key_list, data_set_list, context_prefix)

        self._finalize_records(rec_dict)

        # Debug: log the final record dictionary
        _LOGGER.debug("Final record dictionary: %s", rec_dict)

        # Ensure 'areas' key is always present
        return {"areas": rec_dict} if rec_dict else {"areas": {}}

    def _determine_context_prefix(self, resource_name):
        """Determine context prefix based on resource name."""
        if 'SEM-DA' in resource_name:
            return 'da_'
        elif 'SEM-IDA1' in resource_name:
            return 'ida1_'
        elif 'SEM-IDA2' in resource_name:
            return 'ida2_'
        elif 'SEM-IDA3' in resource_name:
            return 'ida3_'
        else:
            return None

    def _parse_semopx_time(self, datetime_str):
        """Parse SEMOpx time."""
        utc_dt = parse_dt(datetime_str)
        if self.timezone not in all_timezones:
            raise ValueError(f"Invalid timezone: {self.timezone}")

        local_tz = timezone(self.timezone)
        local_dt = utc_dt.astimezone(local_tz)
        return int(utc_dt.timestamp()), local_dt

    def _merge_prices(self, rec_dict, key_list, data_set_list, context_prefix):
        """Merge prices into record dictionary."""
        i = -1
        for price in data_set_list[3]:
            i += 1
            ts = key_list[i][0]
            if ts not in rec_dict:
                data_rec = {
                    'ts': ts,
                    'datetime': key_list[i][1].strftime('%Y/%m/%d %H:%M:%S'),
                    'market_area': self.market_area,
                    'currency': self.currency
                }
                rec_dict[ts] = data_rec

            rec_dict[ts][f'{context_prefix}kwh_rate'] = price / 1000

    def _finalize_records(self, rec_dict):
        """Finalize record entries."""
        for rec in rec_dict.values():
            if 'ida3_kwh_rate' in rec:
                rec['final_kwh_rate'] = rec['ida3_kwh_rate']
            elif 'ida2_kwh_rate' in rec:
                rec['final_kwh_rate'] = rec['ida2_kwh_rate']
            elif 'ida1_kwh_rate' in rec:
                rec['final_kwh_rate'] = rec['ida1_kwh_rate']
            elif 'da_kwh_rate' in rec:
                rec['final_kwh_rate'] = rec['da_kwh_rate']

    async def hourly(self, end_date=None, areas=None, raw=False):
        """Helper to fetch hourly data."""
        if areas is None:
            areas = []
        return await self.fetch(data_type="hourly", end_date=end_date, areas=areas, raw=raw)

    async def daily(self, end_date=None, areas=None):
        """Helper to fetch daily data."""
        if areas is None:
            areas = []
        return await self.fetch(data_type="daily", end_date=end_date, areas=areas)

    async def weekly(self, end_date=None, areas=None):
        """Helper to fetch weekly data."""
        if areas is None:
            areas = []
        return await self.fetch(data_type="weekly", end_date=end_date, areas=areas)

    async def monthly(self, end_date=None, areas=None):
        """Helper to fetch monthly data."""
        if areas is None:
            areas = []
        return await self.fetch(data_type="monthly", end_date=end_date, areas=areas)

    async def yearly(self, end_date=None, areas=None):
        """Helper to fetch yearly data."""
        if areas is None:
            areas = []
        return await self.fetch(data_type="yearly", end_date=end_date, areas=areas)