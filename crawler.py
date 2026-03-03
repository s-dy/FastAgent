from typing import Optional, Any
import requests
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class Crawler:
    def __init__(self):
        self.cookies = {
            'bkng_sso_session': 'e30',
            'cnfunco': '1',
            'cnfunco_guest': 'psVersion%3D2',
            'pcm_personalization_disabled': '0',
            'cors_js': '1',
            'BJS': '-',
            'OptanonAlertBoxClosed': '2026-03-02T07:12:14.049Z',
            'bkng_sso_ses': 'eyJib29raW5nX2dsb2JhbCI6W3siYSI6MSwiaCI6Ii9MSk1SZ3luakoxZ3lGR1IvWTZkSFNjUjdHL1NMcytpZDBFdHUxcU50VjQifV19',
            'pcm_consent': 'consentedAt%3D2026-03-02T07%3A12%3A20.062Z%26countryCode%3DCN%26expiresAt%3D2026-08-29T07%3A12%3A20.062Z%26implicit%3Dfalse%26regulation%3Dpipl%26legacyRegulation%3Dgdpr%26consentId%3D5c76ed83-20f0-436f-9ef5-ff5725635ffc%26analytical%3Dfalse%26marketing%3Dfalse',
            'pcm_pac': '%5B%22f08c1512e8b788370b9d9a5205671084f4a35ae845efbdd37418b40f60997abc%22%2C6%5D',
            'bk_nav_search': '%7B%22u%22%3A%22https%3A%2F%2Fwww.booking.com%2Fsearchresults.zh-cn.html%3Fss%3D%25E5%258C%2597%25E4%25BA%25AC%26ssne%3D%25E5%258C%2597%25E4%25BA%25AC%26ssne_untouched%3D%25E5%258C%2597%25E4%25BA%25AC%26label%3Dgog235jc-10CAMoMTjcA0grWANoMYgBAZgBM7gBB8gBDNgBA-gBAfgBAYgCAagCAbgCxYuVzQbAAgHSAiQxZjg4NWFkMy1kZGM5LTRjYzQtYWVkZC1hNWJhYThhZWZhNTXYAgHgAgE%26aid%3D357003%26lang%3Dzh-cn%26sb%3D1%26src_elem%3Dsb%26src%3Dcity%26dest_id%3D-1353149%26dest_type%3Dcity%26group_adults%3D2%26no_rooms%3D1%26group_children%3D0%22%2C%22t%22%3A1772439148644%2C%22p%22%3A%22searchResults%22%7D',
            'OptanonConsent': 'implicitConsentCountry=GDPR&implicitConsentDate=1772435461329&isGpcEnabled=0&datestamp=Mon+Mar+02+2026+16%3A12%3A29+GMT%2B0800+(%E4%B8%AD%E5%9B%BD%E6%A0%87%E5%87%86%E6%97%B6%E9%97%B4)&version=202501.2.0&browserGpcFlag=0&isIABGlobal=false&hosts=&consentId=60811722-b388-4a30-a163-b478eac7041d&interactionCount=1&isAnonUser=1&landingPath=NotLandingPage&groups=C0001%3A1%2CC0002%3A0%2CC0004%3A0&AwaitingReconsent=false&backfilled_at=1772435535886&backfilled_seed=1&geolocation=CN%3BBJ',
            'bkng_sso_auth': 'CAIQi4nT0gIaeJ4Gl7EBF5uKzNEn0jLnph2AsfP9Z59pr1TflijYPiWq+mxaCK61ByT1pSRFlXO7NIOMJURTvEPd8gx3w9k1lhKb2i05zqIorlUfpduUiUWsY96cWntuDBdFzIpvX72T8KkEIhTYAf3BXjW8xXCaWcjwtsbIcOOvMQ==',
            'bkng': '11UmFuZG9tSVYkc2RlIyh9Yaa29%2F3xUOLbiKbS0JOgDBLgl3HZScbDuU%2Fiw45CHTRgdFfLNHYO7GMnhYw51%2BdYPNZAaqee5%2BqwMpH6u7Ty0dma8fVNppeVIGf3ag8t22t9tWrY7HQflnVsOWmXTmHnpWm8VuEziEsPqX%2FhQ30ZJMXQ0kUAuE9NNnnqXrkwp%2B3y8JVYFaUUN0k%3D',
            'aws-waf-token': 'd16f5cc2-3f98-436e-ad5e-bb516dab27bd:AgoAiKU4339RAAAA:I3sN9wMgB6yKYmYwa+ggRBKE1IH2f51fs3OFQYB7gQ7wvM1WlohRDAl+YcFVtJF9d7qVdsJ4Es2NnxTpcs5ryUyKYnzC9LSCM7WiCoU5x64ZLyonPvdLJ+vYY/W2dnDtOgVId19yYcFRLFe4tslgi9D0MZ7AkQshqW/P4+P6qbTWAcH0xs+wyJ2u9f82jpbMd2aI76qpniAMbW8D/yFaOIULfFx8Otm+xOy+eS55iYZ84qPqyjUt32Xh7qkpgqv9gAA=',
        }

        self.headers = {
            'accept': '*/*',
            'accept-language': 'zh-CN,zh;q=0.9',
            'apollographql-client-name': 'b-search-web-searchresults',
            'apollographql-client-version': 'EQQVGUSL',
            'cache-control': 'no-cache',
            'content-type': 'application/json',
            'ect': '4g',
            'origin': 'https://www.booking.com',
            'pragma': 'no-cache',
            'priority': 'u=1, i',
            'referer': 'https://www.booking.com/searchresults.zh-cn.html?ss=%E5%8C%97%E4%BA%AC&ssne=%E5%8C%97%E4%BA%AC&ssne_untouched=%E5%8C%97%E4%BA%AC&efdco=1&label=gog235jc-10CAMoMTjcA0grWANoMYgBAZgBM7gBB8gBDNgBA-gBAfgBAYgCAagCAbgCxYuVzQbAAgHSAiQxZjg4NWFkMy1kZGM5LTRjYzQtYWVkZC1hNWJhYThhZWZhNTXYAgHgAgE&aid=357003&lang=zh-cn&sb=1&src_elem=sb&src=city&dest_id=-1353149&dest_type=city&group_adults=2&no_rooms=1&group_children=0&sb_travel_purpose=leisure&sb_lp=1',
            'sec-ch-ua': '"Not(A:Brand";v="8", "Chromium";v="144", "Google Chrome";v="144"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"macOS"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36',
            'x-booking-context-action-name': 'searchresults_irene',
            'x-booking-context-aid': '357003',
            'x-booking-csrf-token': 'eyJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJjb250ZXh0LWVucmljaG1lbnQtYXBpIiwic3ViIjoiY3NyZi10b2tlbiIsImlhdCI6MTc3MjQzOTE1MCwiZXhwIjoxNzcyNTI1NTUwfQ.dlEzT8MFV_-x-y8wa423Yy9O48fdmqDi88jgPLzQWpswHvMdg657-H-nQO8LWZKvgzXw33MAdPaOvLO4JlqXQg',
            'x-booking-et-serialized-state': 'E4sgkxCRUYvr1dRzVEPOZIMHYRCYLY2lYMP6qxb1k2V3QkPrYcfIl_W3a_DBTo4eD',
            'x-booking-pageview-id': 'fed639b7db930f87',
            'x-booking-site-type-id': '1',
            'x-booking-topic': 'capla_browser_b-search-web-searchresults',
        }

    def _get_dest_id(self, prefix_query: str, nb_suggestions:Optional[int]=20) -> tuple[str, str]:
        """获取搜索id"""
        params = {
            'label': 'gog235jc-10CAMoMTjcA0grWANoMYgBAZgBM7gBB8gBDNgBA-gBAfgBAYgCAagCAbgCxYuVzQbAAgHSAiQxZjg4NWFkMy1kZGM5LTRjYzQtYWVkZC1hNWJhYThhZWZhNTXYAgHgAgE',
            'aid': '357003',
            'lang': 'zh-cn',
        }

        json_data = {
            'operationName': 'AutoComplete',
            'variables': {
                'input': {
                    'prefixQuery': prefix_query, # 搜索关键词
                    'nbSuggestions': nb_suggestions, # 搜索结果数量
                    'fallbackConfig': {
                        'mergeResults': True,
                        'nbMaxMergedResults': 6,
                        'nbMaxThirdPartyResults': 3,
                        'sources': [
                            'GOOGLE',
                            'HERE',
                        ],
                    },
                    'requestConfig': {
                        'enableRequestContextBoost': True,
                    },
                    'requestContext': {
                        'pageviewId': '4650402573b402a8',
                        'location': None,
                    },
                },
            },
            'extensions': {},
            'query': 'query AutoComplete($input: AutoCompleteRequestInput!) {\n  autoCompleteSuggestions(input: $input) {\n    results {\n      destination {\n        countryCode\n        destId\n        destType\n        latitude\n        longitude\n        __typename\n      }\n      displayInfo {\n        imageUrl\n        label\n        labelComponents {\n          name\n          type\n          __typename\n        }\n        showEntireHomesCheckbox\n        title\n        subTitle\n        __typename\n      }\n      metaData {\n        isSkiItem\n        langCode\n        maxLosData {\n          extendedLoS\n          __typename\n        }\n        metaMatches {\n          id\n          text\n          type\n          __typename\n        }\n        roundTrip\n        webFilters\n        autocompleteResultId\n        autocompleteResultSource\n        eligiblePages\n        __typename\n      }\n      __typename\n    }\n    __typename\n  }\n}\n',
        }

        try:
            response = requests.post('https://www.booking.com/dml/graphql', params=params, cookies=self.cookies, headers=self.headers,
                                     json=json_data, timeout=10)
            response.raise_for_status()
            results = response.json()['data']['autoCompleteSuggestions']['results']
            dest_id, dest_type = "", ""
            if results:
                for item in results:
                    destination = item['destination']
                    dest_type = destination['destType']
                    country_code = destination['countryCode']
                    # 排除非中国
                    if country_code != "cn":
                        continue
                    if dest_type not in ['CITY', 'DISTRICT', 'LANDMARK']:
                        continue
                    if dest_type == "LANDMARK":
                        dest_type = "DISTRICT"
                    dest_id = destination['destId']
                    break
            return dest_id, dest_type
        except Exception as e:
            logger.error(f"获取dest_id失败 => {e}")
            return "", ""

    def search_hotels(self, prefix_query: str, checkin: str, checkout: str, nb_adults:int=2, nb_children:int=0, nb_rooms:int=1, offset:int=25) -> list:
        """
        搜索酒店
        :param prefix_query: 搜索关键词
        :param checkin: 入住日期
        :param checkout: 退房时间
        :param nb_adults: 成人数
        :param nb_children: 儿童数
        :param nb_rooms: 客房数
        :param offset: 分页参数，从25开始，步长为25
        :return:
        """
        try:
            dest_id, dest_type = self._get_dest_id(prefix_query)
            logger.info(f"dest_id => {dest_id}")
            if not dest_id:
                return []

            params = {
                'ss': prefix_query,
                'ssne': prefix_query,
                'ssne_untouched': prefix_query,
                'efdco': '1',
                'label': 'gog235jc-10CAMoMTjcA0grWANoMYgBAZgBM7gBB8gBDNgBA-gBAfgBAYgCAagCAbgCxYuVzQbAAgHSAiQxZjg4NWFkMy1kZGM5LTRjYzQtYWVkZC1hNWJhYThhZWZhNTXYAgHgAgE',
                'aid': '357003',
                'lang': 'zh-cn',
                'sb': '1',
                'src_elem': 'sb',
                'src': 'searchresults',
                'dest_id': dest_id,
                'dest_type': dest_type.lower() or 'city',
                'checkin': checkin,
                'checkout': checkout,
                'group_adults': str(nb_adults),
                'no_rooms': str(nb_rooms),
                'group_children': str(nb_children),
            }

            json_data = {
                'operationName': 'FullSearch',
                'variables': {
                    'includeBundle': False,
                    'input': {
                        'acidCarouselContext': None,
                        'childrenAges': [],
                        'dates': {
                            'checkin': checkin,
                            'checkout': checkout,
                        },
                        'doAvailabilityCheck': False,
                        'encodedAutocompleteMeta': None,
                        'enableCampaigns': True,
                        'filters': {},
                        'flexibleDatesConfig': {
                            'broadDatesCalendar': {
                                'checkinMonths': [],
                                'los': [],
                                'startWeekdays': [],
                            },
                            'dateFlexUseCase': 'DATE_RANGE',
                            'dateRangeCalendar': {
                                'checkin': [
                                    checkin,
                                ],
                                'checkout': [
                                    checkout,
                                ],
                            },
                        },
                        'forcedBlocks': None,
                        'location': {
                            'searchString': prefix_query,
                            'destType': dest_type.upper() or "CITY",
                            'destId': int(dest_id),
                        },
                        'metaContext': {
                            'metaCampaignId': 0,
                            'externalTotalPrice': None,
                            'feedPrice': None,
                            'hotelCenterAccountId': None,
                            'rateRuleId': None,
                            'dragongateTraceId': None,
                            'pricingProductsTag': None,
                        },
                        'nbRooms': nb_rooms,
                        'nbAdults': nb_adults,
                        'nbChildren': nb_children,
                        'showAparthotelAsHotel': True,
                        'needsRoomsMatch': False,
                        'optionalFeatures': {
                            'forceArpExperiments': True,
                            'testProperties': False,
                        },
                        'pagination': {
                            'rowsPerPage': 25,
                            'offset': offset or 25,
                        },
                        'rawQueryForSession': '/searchresults.zh-cn.html?label=gog235jc-10CAMoMTjcA0grWANoMYgBAZgBM7gBB8gBDNgBA-gBAfgBAYgCAagCAbgCxYuVzQbAAgHSAiQxZjg4NWFkMy1kZGM5LTRjYzQtYWVkZC1hNWJhYThhZWZhNTXYAgHgAgE&aid=357003&ss=%E6%9C%9D%E9%98%B3%E5%8C%BA&ssne=%E6%9C%9D%E9%98%B3%E5%8C%BA&ssne_untouched=%E6%9C%9D%E9%98%B3%E5%8C%BA&efdco=1&lang=zh-cn&sb=1&src_elem=sb&src=searchresults&dest_id=1718&dest_type=district&checkin=2026-03-04&checkout=2026-03-05&group_adults=2&no_rooms=1&group_children=0',
                        'referrerBlock': {
                            'blockName': 'searchbox',
                        },
                        'sbCalendarOpen': True,
                        'sorters': {
                            'selectedSorter': None,
                            'referenceGeoId': None,
                            'tripTypeIntentId': None,
                        },
                        'travelPurpose': 2,
                        'seoThemeIds': [],
                        'useSearchParamsFromSession': True,
                        'merchInput': {
                            'testCampaignIds': [],
                        },
                        'webSearchContext': {
                            'reason': 'CLIENT_SIDE_UPDATE',
                            'source': 'SEARCH_RESULTS',
                            'outcome': 'SEARCH_RESULTS',
                        },
                        'clientSideRequestId': '15c516d0b14f03c4',
                    },
                    'carouselLowCodeExp': False,
                },
                'extensions': {
                    'persistedQuery': {
                        'version': 1,
                        'sha256Hash': '8cea877c71f083895aa316412e85ffe818b503bb5331babba34a1602977d8b99',
                    },
                },
            }

            response = requests.post('https://www.booking.com/dml/graphql', params=params, cookies=self.cookies, headers=self.headers, json=json_data, timeout=10)
            return self._parse_hotels(response.json())
        except Exception as e:
            logger.error(f"酒店搜索失败 => {e}")
            return []

    def _safe_parse(self,data: dict, path: str, default:Any=''):
        """安全的提取数据"""
        keys = path.split('.')
        result = default
        for key in keys:
            try:
                result = data.get(key)
                if not result:
                    return default
                data = result
            except Exception as e:
                pass
        return result

    def _parse_hotels(self, data: dict) -> list:
        """解析酒店数据"""
        hotels = []
        results = self._safe_parse(data, 'data.searchQueries.search.results', [])

        for h in results:
            try:
                basic = self._safe_parse(h, 'basicPropertyData', {})
                hotel = {
                    'id': self._safe_parse(basic,'id'), # id
                    'ufi': self._safe_parse(basic,'ufi'), #dest_id
                    'name': self._safe_parse(h,'displayName.text'), # 名称
                    'isClosed': self._safe_parse(basic,'isClosed',False), # 是否关闭
                    'isSoldOut': self._safe_parse(h,'soldOutInfo.isSoldOut',False), # 是否售空
                    'location': {k : v for k,v in self._safe_parse(basic,'location', {}).items() if k not in ('__typename','countryCode')}, # 地址信息
                    'score': self._safe_parse(basic,'reviewScore.score', 0), # 评分
                    'starRating': self._safe_parse(basic,'starRating.value', 0),  # 星级
                    'price': self._safe_parse(h,'priceDisplayInfoIrene.displayPrice.amountPerStay.amount'), # 最终价格
                    'room': "、".join([self._safe_parse(_, 'name') for _ in self._safe_parse(h,'matchingUnitConfigurations.unitConfigurations', [])]), # 房间
                }
                hotels.append(hotel)
            except Exception as e:
                logger.error(f'解析失败{e}')

        return hotels


if __name__ == '__main__':
    print(Crawler().search_hotels("天安门广场附近", '2026-03-04', '2026-03-05'))