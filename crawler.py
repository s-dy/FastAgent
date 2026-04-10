from datetime import datetime, timedelta
from typing import Optional, Any
import requests
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

is_cn = True
if is_cn:
    base_url = 'https://www.booking.cn/dml/graphql'
else:
    base_url = 'https://www.booking.com/dml/graphql'

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
            #####################################################################
            'aws-waf-token': '05f92800-8ada-4010-a70f-c544a1563518:AgoAqzJv6c8bAAAA:Yj+lwtAbSZ8z0EK8besgpGbAN1bGzx+BN4qU91UJYPJXfNZYIRrOYTTS/hgBY7l0Lk4d7B5/KZNh6d2yz9rX/YV7XDjn0XvfrcGqVA8Xmmvn4wxQ08cPh6Yccq50PjFrTsBawAcb/71H1Wyz0fFohmlrfst1J+lPpjluScK3BcMf+u5idt1a1PDoGqTHC2jEXP461gEJv/eY0e1bp2BLLSjeTKE1pWrQQS+lXLsVJjjI0kDUcbOmdC0kt/ccsGNezX45A0A=',
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
            response = requests.post(base_url, params=params, cookies=self.cookies, headers=self.headers,
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
            logger.info(f"prefix_query => {prefix_query}，checkin => {checkin}，checkout => {checkout}，nb_adults => {nb_adults}，nb_children => {nb_children}，nb_rooms => {nb_rooms}，offset => {offset}")
            if checkin == checkout:
                checkout = (datetime.strptime(checkin, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
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
                'query': 'query FullSearch($input: SearchQueryInput!, $carouselLowCodeExp: Boolean!, $includeBundle: Boolean = false) {\n  searchQueries {\n    search(input: $input) {\n      ...FullSearchFragment\n      __typename\n    }\n    __typename\n  }\n}\n\nfragment FullSearchFragment on SearchQueryOutput {\n  banners {\n    ...Banner\n    __typename\n  }\n  breadcrumbs {\n    ... on SearchResultsBreadcrumb {\n      ...SearchResultsBreadcrumb\n      __typename\n    }\n    ... on LandingPageBreadcrumb {\n      ...LandingPageBreadcrumb\n      __typename\n    }\n    __typename\n  }\n  carousels {\n    ...Carousel\n    __typename\n  }\n  destinationLocation {\n    ...DestinationLocation\n    __typename\n  }\n  entireHomesSearchEnabled\n  dateFlexibilityOptions {\n    enabled\n    __typename\n  }\n  flexibleDatesConfig {\n    broadDatesCalendar {\n      checkinMonths\n      los\n      startWeekdays\n      losType\n      __typename\n    }\n    dateFlexUseCase\n    dateRangeCalendar {\n      flexWindow\n      checkin\n      checkout\n      __typename\n    }\n    __typename\n  }\n  filters {\n    ...FilterData\n    __typename\n  }\n  filtersTrackOnView {\n    type\n    experimentHash\n    value\n    __typename\n  }\n  appliedFilterOptions {\n    ...FilterOption\n    __typename\n  }\n  recommendedFilterOptions {\n    ...FilterOption\n    __typename\n  }\n  pagination {\n    nbResultsPerPage\n    nbResultsTotal\n    __typename\n  }\n  tripTypes {\n    ...TripTypesData\n    __typename\n  }\n  results {\n    ...ReviewSummary\n    ...BasicPropertyData\n    ...PropertyUspBadges\n    ...MatchingUnitConfigurations\n    ...NeedsProfileNeeds\n    ...PropertyBlocks\n    ...BookerExperienceData\n    ...TopPhotos\n    ...CardLabels\n    ...PersonalizedPhotos\n    generatedPropertyTitle\n    descriptionSummary\n    priceDisplayInfoIrene {\n      ...PriceDisplayInfoIrene\n      __typename\n    }\n    licenseDetails {\n      nextToHotelName\n      __typename\n    }\n    isTpiExclusiveProperty\n    propertyCribsAvailabilityLabel\n    mlBookingHomeTags\n    trackOnView {\n      type\n      experimentHash\n      value\n      __typename\n    }\n    __typename\n  }\n  searchMeta {\n    ...SearchMetadata\n    __typename\n  }\n  sorters {\n    option {\n      ...SorterFields\n      __typename\n    }\n    __typename\n  }\n  zeroResultsSection {\n    ...ZeroResultsSection\n    __typename\n  }\n  rocketmilesSearchUuid\n  previousSearches {\n    ...PreviousSearches\n    __typename\n  }\n  merchComponents {\n    ...MerchRegionIrene\n    __typename\n  }\n  wishlistData {\n    numProperties\n    __typename\n  }\n  seoThemes {\n    id\n    caption\n    __typename\n  }\n  gridViewPreference\n  advancedSearchWidget {\n    title\n    legalDisclaimer\n    description\n    placeholder\n    ctaText\n    helperText\n    __typename\n  }\n  visualFiltersGroups {\n    ...VisualFiltersGroup\n    __typename\n  }\n  __typename\n}\n\nfragment ReviewSummary on SearchResultProperty {\n  personalizedSummary {\n    summary\n    reviewsCount\n    segment\n    languageCode\n    __typename\n  }\n  __typename\n}\n\nfragment BasicPropertyData on SearchResultProperty {\n  acceptsWalletCredit\n  basicPropertyData {\n    accommodationTypeId\n    id\n    isTestProperty\n    location {\n      address\n      city\n      countryCode\n      latitude\n      longitude\n      __typename\n    }\n    pageName\n    ufi\n    photos {\n      main {\n        highResUrl {\n          relativeUrl\n          __typename\n        }\n        lowResUrl {\n          relativeUrl\n          __typename\n        }\n        highResJpegUrl {\n          relativeUrl\n          __typename\n        }\n        lowResJpegUrl {\n          relativeUrl\n          __typename\n        }\n        tags {\n          id\n          __typename\n        }\n        __typename\n      }\n      __typename\n    }\n    reviewScore: reviews {\n      score: totalScore\n      reviewCount: reviewsCount\n      totalScoreTextTag {\n        translation\n        __typename\n      }\n      showScore\n      secondaryScore\n      secondaryTextTag {\n        translation\n        tag\n        __typename\n      }\n      showSecondaryScore\n      __typename\n    }\n    externalReviewScore: externalReviews {\n      score: totalScore\n      reviewCount: reviewsCount\n      showScore\n      totalScoreTextTag {\n        translation\n        __typename\n      }\n      __typename\n    }\n    starRating {\n      value\n      symbol\n      caption {\n        translation\n        __typename\n      }\n      tocLink {\n        translation\n        __typename\n      }\n      showAdditionalInfoIcon\n      __typename\n    }\n    isClosed\n    paymentConfig {\n      installments {\n        minPriceFormatted\n        maxAcceptCount\n        __typename\n      }\n      __typename\n    }\n    __typename\n  }\n  badges {\n    caption {\n      translation\n      __typename\n    }\n    closedFacilities {\n      startDate\n      endDate\n      __typename\n    }\n    __typename\n  }\n  customBadges {\n    showSkiToDoor\n    showBhTravelCreditBadge\n    showOnlineCheckinBadge\n    __typename\n  }\n  description {\n    text\n    __typename\n  }\n  displayName {\n    text\n    translationTag {\n      translation\n      __typename\n    }\n    __typename\n  }\n  geniusInfo {\n    benefitsCommunication {\n      header {\n        title\n        __typename\n      }\n      items {\n        title\n        __typename\n      }\n      __typename\n    }\n    geniusBenefits\n    geniusBenefitsData {\n      hotelCardHasFreeBreakfast\n      hotelCardHasFreeRoomUpgrade\n      sortedBenefits\n      __typename\n    }\n    showGeniusRateBadge\n    __typename\n  }\n  location {\n    displayLocation\n    mainDistance\n    mainDistanceDescription\n    publicTransportDistanceDescription\n    skiLiftDistance\n    beachDistance\n    nearbyBeachNames\n    beachWalkingTime\n    geoDistanceMeters\n    isCentrallyLocated\n    isWithinBestLocationScoreArea\n    popularFreeDistrictName\n    nearbyUsNaturalParkText\n    __typename\n  }\n  mealPlanIncluded {\n    mealPlanType\n    text\n    __typename\n  }\n  persuasion {\n    autoextended\n    geniusRateAvailable\n    highlighted\n    preferred\n    preferredPlus\n    showNativeAdLabel\n    nativeAdId\n    nativeAdsCpc\n    nativeAdsTracking\n    sponsoredAdsData {\n      isDsaCompliant\n      legalEntityName\n      designType\n      __typename\n    }\n    __typename\n  }\n  policies {\n    showFreeCancellation\n    showNoPrepayment\n    showPetsAllowedForFree\n    enableJapaneseUsersSpecialCase\n    __typename\n  }\n  ribbon {\n    ribbonType\n    text\n    __typename\n  }\n  recommendedDate {\n    checkin\n    checkout\n    lengthOfStay\n    __typename\n  }\n  showGeniusLoginMessage\n  hostTraderLabel\n  soldOutInfo {\n    isSoldOut\n    messages {\n      text\n      __typename\n    }\n    alternativeDatesMessages {\n      text\n      __typename\n    }\n    __typename\n  }\n  nbWishlists\n  nonMatchingFlexibleFilterOptions {\n    label\n    __typename\n  }\n  visibilityBoosterEnabled\n  showAdLabel\n  isNewlyOpened\n  propertySustainability {\n    isSustainable\n    certifications {\n      name\n      __typename\n    }\n    __typename\n  }\n  seoThemes {\n    caption\n    __typename\n  }\n  relocationMode {\n    distanceToCityCenterKm\n    distanceToCityCenterMiles\n    distanceToOriginalHotelKm\n    distanceToOriginalHotelMiles\n    phoneNumber\n    __typename\n  }\n  bundleRatesAvailable\n  __typename\n}\n\nfragment Banner on Banner {\n  name\n  type\n  isDismissible\n  showAfterDismissedDuration\n  position\n  requestAlternativeDates\n  merchId\n  title {\n    text\n    __typename\n  }\n  imageUrl\n  paragraphs {\n    text\n    __typename\n  }\n  metadata {\n    key\n    value\n    __typename\n  }\n  pendingReviewInfo {\n    propertyPhoto {\n      lowResUrl {\n        relativeUrl\n        __typename\n      }\n      lowResJpegUrl {\n        relativeUrl\n        __typename\n      }\n      __typename\n    }\n    propertyName\n    urlAccessCode\n    __typename\n  }\n  nbDeals\n  primaryAction {\n    text {\n      text\n      __typename\n    }\n    action {\n      name\n      context {\n        key\n        value\n        __typename\n      }\n      __typename\n    }\n    __typename\n  }\n  secondaryAction {\n    text {\n      text\n      __typename\n    }\n    action {\n      name\n      context {\n        key\n        value\n        __typename\n      }\n      __typename\n    }\n    __typename\n  }\n  iconName\n  flexibleFilterOptions {\n    optionId\n    filterName\n    __typename\n  }\n  trackOnView {\n    type\n    experimentHash\n    value\n    __typename\n  }\n  dateFlexQueryOptions {\n    text {\n      text\n      __typename\n    }\n    action {\n      name\n      context {\n        key\n        value\n        __typename\n      }\n      __typename\n    }\n    isApplied\n    __typename\n  }\n  __typename\n}\n\nfragment Carousel on Carousel {\n  aggregatedCountsByFilterId\n  carouselId\n  position\n  contentType\n  hotelId\n  name\n  soldoutProperties\n  priority\n  themeId\n  title {\n    text\n    __typename\n  }\n  description {\n    text\n    __typename\n  }\n  sponsoredCarouselData {\n    logoUrl\n    auctionId\n    hotelIds\n    __typename\n  }\n  slides {\n    captionText {\n      text\n      __typename\n    }\n    name\n    photoUrl\n    subtitle {\n      text\n      __typename\n    }\n    type\n    title {\n      text\n      __typename\n    }\n    action {\n      context {\n        key\n        value\n        __typename\n      }\n      __typename\n    }\n    __typename\n  }\n  __typename\n}\n\nfragment DestinationLocation on DestinationLocation {\n  name {\n    text\n    __typename\n  }\n  inName {\n    text\n    __typename\n  }\n  countryCode\n  ufi\n  __typename\n}\n\nfragment FilterData on Filter {\n  trackOnView {\n    type\n    experimentHash\n    value\n    __typename\n  }\n  trackOnClick {\n    type\n    experimentHash\n    value\n    __typename\n  }\n  name\n  field\n  category\n  filterStyle\n  title {\n    text\n    textContentContainer\n    translationTag {\n      translation\n      __typename\n    }\n    __typename\n  }\n  subtitle\n  options {\n    parentId\n    genericId\n    trackOnView {\n      type\n      experimentHash\n      value\n      __typename\n    }\n    trackOnClick {\n      type\n      experimentHash\n      value\n      __typename\n    }\n    trackOnSelect {\n      type\n      experimentHash\n      value\n      __typename\n    }\n    trackOnDeSelect {\n      type\n      experimentHash\n      value\n      __typename\n    }\n    trackOnViewPopular {\n      type\n      experimentHash\n      value\n      __typename\n    }\n    trackOnClickPopular {\n      type\n      experimentHash\n      value\n      __typename\n    }\n    trackOnSelectPopular {\n      type\n      experimentHash\n      value\n      __typename\n    }\n    trackOnDeSelectPopular {\n      type\n      experimentHash\n      value\n      __typename\n    }\n    ...FilterOption\n    __typename\n  }\n  filterLayout {\n    isCollapsable\n    collapsedCount\n    __typename\n  }\n  stepperOptions {\n    min\n    max\n    default\n    selected\n    title {\n      text\n      translationTag {\n        translation\n        __typename\n      }\n      __typename\n    }\n    field\n    labels {\n      text\n      translationTag {\n        translation\n        __typename\n      }\n      __typename\n    }\n    trackOnView {\n      type\n      experimentHash\n      value\n      __typename\n    }\n    trackOnClick {\n      type\n      experimentHash\n      value\n      __typename\n    }\n    trackOnSelect {\n      type\n      experimentHash\n      value\n      __typename\n    }\n    trackOnDeSelect {\n      type\n      experimentHash\n      value\n      __typename\n    }\n    trackOnClickDecrease {\n      type\n      experimentHash\n      value\n      __typename\n    }\n    trackOnClickIncrease {\n      type\n      experimentHash\n      value\n      __typename\n    }\n    trackOnDecrease {\n      type\n      experimentHash\n      value\n      __typename\n    }\n    trackOnIncrease {\n      type\n      experimentHash\n      value\n      __typename\n    }\n    __typename\n  }\n  sliderOptions {\n    min\n    max\n    minSelected\n    maxSelected\n    minPriceStep\n    minSelectedFormatted\n    currency\n    histogram\n    selectedRange {\n      translation\n      __typename\n    }\n    __typename\n  }\n  distanceToPoiData {\n    options {\n      text\n      value\n      isDefault\n      __typename\n    }\n    poiNotFound\n    poiPlaceholder\n    poiHelper\n    isSelected\n    selectedOptionValue\n    selectedPlaceId {\n      numValue\n      stringValue\n      __typename\n    }\n    selectedPoiType {\n      destType\n      source\n      __typename\n    }\n    selectedPoiText\n    selectedPoiLatitude\n    selectedPoiLongitude\n    __typename\n  }\n  __typename\n}\n\nfragment FilterOption on Option {\n  optionId: id\n  count\n  selected\n  urlId\n  source\n  field\n  additionalLabel {\n    text\n    translationTag {\n      translation\n      __typename\n    }\n    __typename\n  }\n  value {\n    text\n    translationTag {\n      translation\n      __typename\n    }\n    __typename\n  }\n  starRating {\n    value\n    symbol\n    caption {\n      translation\n      __typename\n    }\n    showAdditionalInfoIcon\n    __typename\n  }\n  __typename\n}\n\nfragment LandingPageBreadcrumb on LandingPageBreadcrumb {\n  destType\n  name\n  urlParts\n  __typename\n}\n\nfragment MatchingUnitConfigurations on SearchResultProperty {\n  matchingUnitConfigurations {\n    commonConfiguration {\n      name\n      unitId\n      bedConfigurations {\n        beds {\n          count\n          type\n          __typename\n        }\n        nbAllBeds\n        __typename\n      }\n      nbAllBeds\n      nbBathrooms\n      nbBedrooms\n      nbKitchens\n      nbLivingrooms\n      nbUnits\n      unitTypeNames {\n        translation\n        __typename\n      }\n      localizedArea {\n        localizedArea\n        unit\n        __typename\n      }\n      __typename\n    }\n    unitConfigurations {\n      name\n      unitId\n      bedConfigurations {\n        beds {\n          count\n          type\n          __typename\n        }\n        nbAllBeds\n        __typename\n      }\n      apartmentRooms {\n        config {\n          roomId: id\n          roomType\n          bedTypeId\n          bedCount: count\n          __typename\n        }\n        roomName: tag {\n          tag\n          translation\n          __typename\n        }\n        __typename\n      }\n      nbAllBeds\n      nbBathrooms\n      nbBedrooms\n      nbKitchens\n      nbLivingrooms\n      nbUnits\n      unitTypeNames {\n        translation\n        __typename\n      }\n      localizedArea {\n        localizedArea\n        unit\n        __typename\n      }\n      unitTypeId\n      __typename\n    }\n    __typename\n  }\n  __typename\n}\n\nfragment NeedsProfileNeeds on SearchResultProperty {\n  needsProfileNeeds {\n    entity {\n      name\n      id\n      type\n      __typename\n    }\n    __typename\n  }\n  __typename\n}\n\nfragment PropertyBlocks on SearchResultProperty {\n  blocks {\n    blockId {\n      roomId\n      occupancy\n      policyGroupId\n      packageId\n      mealPlanId\n      bundleId\n      __typename\n    }\n    finalPrice {\n      amount\n      currency\n      __typename\n    }\n    originalPrice {\n      amount\n      currency\n      __typename\n    }\n    onlyXLeftMessage {\n      tag\n      variables {\n        key\n        value\n        __typename\n      }\n      translation\n      __typename\n    }\n    freeCancellationUntil\n    hasCrib\n    blockMatchTags {\n      childStaysForFree\n      freeStayChildrenAges\n      __typename\n    }\n    thirdPartyInventoryContext {\n      isTpiBlock\n      __typename\n    }\n    bundle @include(if: $includeBundle) {\n      highlightedText\n      generatedName\n      __typename\n    }\n    mealPlanIncluded {\n      mealPlanType\n      text\n      __typename\n    }\n    __typename\n  }\n  __typename\n}\n\nfragment PriceDisplayInfoIrene on PriceDisplayInfoIrene {\n  badges {\n    name {\n      translation\n      __typename\n    }\n    tooltip {\n      translation\n      __typename\n    }\n    style\n    identifier\n    __typename\n  }\n  chargesInfo {\n    translation\n    __typename\n  }\n  displayPrice {\n    copy {\n      translation\n      __typename\n    }\n    amountPerStay {\n      amount\n      amountRounded\n      amountUnformatted\n      currency\n      __typename\n    }\n    amountPerStayHotelCurr {\n      amount\n      amountRounded\n      amountUnformatted\n      currency\n      __typename\n    }\n    __typename\n  }\n  averagePricePerNight {\n    amount\n    amountRounded\n    amountUnformatted\n    currency\n    __typename\n  }\n  priceBeforeDiscount {\n    copy {\n      translation\n      __typename\n    }\n    amountPerStay {\n      amount\n      amountRounded\n      amountUnformatted\n      currency\n      __typename\n    }\n    __typename\n  }\n  rewards {\n    rewardsList {\n      termsAndConditions\n      amountPerStay {\n        amount\n        amountRounded\n        amountUnformatted\n        currency\n        __typename\n      }\n      breakdown {\n        productType\n        amountPerStay {\n          amount\n          amountRounded\n          amountUnformatted\n          currency\n          __typename\n        }\n        __typename\n      }\n      __typename\n    }\n    rewardsAggregated {\n      amountPerStay {\n        amount\n        amountRounded\n        amountUnformatted\n        currency\n        __typename\n      }\n      copy {\n        translation\n        __typename\n      }\n      __typename\n    }\n    __typename\n  }\n  useRoundedAmount\n  discounts {\n    amount {\n      amount\n      amountRounded\n      amountUnformatted\n      currency\n      __typename\n    }\n    name {\n      translation\n      __typename\n    }\n    description {\n      translation\n      __typename\n    }\n    itemType\n    productId\n    __typename\n  }\n  excludedCharges {\n    excludeChargesAggregated {\n      copy {\n        translation\n        __typename\n      }\n      amountPerStay {\n        amount\n        amountRounded\n        amountUnformatted\n        currency\n        __typename\n      }\n      __typename\n    }\n    excludeChargesList {\n      chargeMode\n      chargeInclusion\n      chargeType\n      amountPerStay {\n        amount\n        amountRounded\n        amountUnformatted\n        currency\n        __typename\n      }\n      __typename\n    }\n    __typename\n  }\n  taxExceptions {\n    shortDescription {\n      translation\n      __typename\n    }\n    longDescription {\n      translation\n      __typename\n    }\n    __typename\n  }\n  displayConfig {\n    key\n    value\n    __typename\n  }\n  serverTranslations {\n    key\n    value\n    __typename\n  }\n  __typename\n}\n\nfragment BookerExperienceData on SearchResultProperty {\n  bookerExperienceContentUIComponentProps {\n    ... on BookerExperienceContentLoyaltyBadgeListProps {\n      badges {\n        amount\n        variant\n        key\n        title\n        hidePopover\n        popover\n        tncMessage\n        tncUrl\n        logoSrc\n        logoAlt\n        foregroundColorLight\n        backgroundColorLight\n        foregroundColorDark\n        backGroundColorDark\n        __typename\n      }\n      __typename\n    }\n    ... on BookerExperienceContentFinancialBadgeProps {\n      paymentMethod\n      backgroundColor\n      hideAccepted\n      __typename\n    }\n    __typename\n  }\n  __typename\n}\n\nfragment TopPhotos on SearchResultProperty {\n  topPhotos {\n    highResUrl {\n      relativeUrl\n      __typename\n    }\n    lowResUrl {\n      relativeUrl\n      __typename\n    }\n    highResJpegUrl {\n      relativeUrl\n      __typename\n    }\n    lowResJpegUrl {\n      relativeUrl\n      __typename\n    }\n    __typename\n  }\n  __typename\n}\n\nfragment CardLabels on SearchResultProperty {\n  cardLabels {\n    label {\n      text\n      __typename\n    }\n    style\n    __typename\n  }\n  __typename\n}\n\nfragment PersonalizedPhotos on SearchResultProperty {\n  personalizedPhotos {\n    highResUrl {\n      relativeUrl\n      __typename\n    }\n    lowResUrl {\n      relativeUrl\n      __typename\n    }\n    highResJpegUrl {\n      relativeUrl\n      __typename\n    }\n    lowResJpegUrl {\n      relativeUrl\n      __typename\n    }\n    __typename\n  }\n  __typename\n}\n\nfragment SearchMetadata on SearchMeta {\n  availabilityInfo {\n    hasLowAvailability\n    unavailabilityPercent\n    totalAvailableNotAutoextended\n    totalAutoextendedAvailable\n    __typename\n  }\n  boundingBoxes {\n    swLat\n    swLon\n    neLat\n    neLon\n    type\n    __typename\n  }\n  childrenAges\n  dates {\n    checkin\n    checkout\n    lengthOfStayInDays\n    __typename\n  }\n  destId\n  destType\n  guessedLocation {\n    destId\n    destType\n    destName\n    __typename\n  }\n  maxLengthOfStayInDays\n  nbRooms\n  nbAdults\n  nbChildren\n  userHasSelectedFilters\n  customerValueStatus\n  isAffiliateBookingOwned\n  affiliatePartnerChannelId\n  affiliateVerticalType\n  geniusLevel\n  __typename\n}\n\nfragment SearchResultsBreadcrumb on SearchResultsBreadcrumb {\n  destId\n  destType\n  name\n  __typename\n}\n\nfragment SorterFields on SorterOption {\n  type: name\n  captionTranslationTag {\n    translation\n    __typename\n  }\n  tooltipTranslationTag {\n    translation\n    __typename\n  }\n  isSelected: selected\n  __typename\n}\n\nfragment TripTypesData on TripTypes {\n  beach {\n    isBeachUfi\n    isEnabledBeachUfi\n    __typename\n  }\n  ski {\n    isSkiExperience\n    isSkiScaleUfi\n    __typename\n  }\n  __typename\n}\n\nfragment ZeroResultsSection on ZeroResultsSection {\n  title {\n    text\n    __typename\n  }\n  primaryAction {\n    text {\n      text\n      __typename\n    }\n    action {\n      name\n      __typename\n    }\n    __typename\n  }\n  paragraphs {\n    text\n    __typename\n  }\n  type\n  __typename\n}\n\nfragment PreviousSearches on PreviousSearch {\n  childrenAges\n  __typename\n}\n\nfragment MerchRegionIrene on MerchComponentsResultIrene {\n  regions {\n    id\n    components {\n      ... on PromotionalBannerIrene {\n        promotionalBannerCampaignId\n        contentArea {\n          title {\n            ... on PromotionalBannerSimpleTitleIrene {\n              value\n              __typename\n            }\n            __typename\n          }\n          subTitle {\n            ... on PromotionalBannerSimpleSubTitleIrene {\n              value\n              __typename\n            }\n            __typename\n          }\n          caption {\n            ... on PromotionalBannerSimpleCaptionIrene {\n              value\n              __typename\n            }\n            ... on PromotionalBannerCountdownCaptionIrene {\n              campaignEnd\n              __typename\n            }\n            __typename\n          }\n          buttons {\n            variant\n            cta {\n              ariaLabel\n              text\n              targetLanding {\n                ... on OpenContextSheet {\n                  sheet {\n                    ... on WebContextSheet {\n                      title\n                      body {\n                        items {\n                          ... on ContextSheetTextItem {\n                            text\n                            __typename\n                          }\n                          ... on ContextSheetList {\n                            items {\n                              text\n                              __typename\n                            }\n                            __typename\n                          }\n                          __typename\n                        }\n                        __typename\n                      }\n                      buttons {\n                        variant\n                        cta {\n                          text\n                          ariaLabel\n                          targetLanding {\n                            ... on DirectLinkLanding {\n                              urlPath\n                              queryParams {\n                                name\n                                value\n                                __typename\n                              }\n                              __typename\n                            }\n                            ... on LoginLanding {\n                              stub\n                              __typename\n                            }\n                            ... on DeeplinkLanding {\n                              urlPath\n                              queryParams {\n                                name\n                                value\n                                __typename\n                              }\n                              __typename\n                            }\n                            ... on ResolvedLinkLanding {\n                              url\n                              __typename\n                            }\n                            __typename\n                          }\n                          __typename\n                        }\n                        __typename\n                      }\n                      __typename\n                    }\n                    __typename\n                  }\n                  __typename\n                }\n                ... on SearchResultsLandingIrene {\n                  destType\n                  destId\n                  checkin\n                  checkout\n                  nrAdults\n                  nrChildren\n                  childrenAges\n                  nrRooms\n                  filters {\n                    name\n                    value\n                    __typename\n                  }\n                  __typename\n                }\n                ... on DirectLinkLandingIrene {\n                  urlPath\n                  queryParams {\n                    name\n                    value\n                    __typename\n                  }\n                  __typename\n                }\n                ... on LoginLandingIrene {\n                  stub\n                  __typename\n                }\n                ... on DeeplinkLandingIrene {\n                  urlPath\n                  queryParams {\n                    name\n                    value\n                    __typename\n                  }\n                  __typename\n                }\n                ... on SorterLandingIrene {\n                  sorterName\n                  __typename\n                }\n                __typename\n              }\n              __typename\n            }\n            __typename\n          }\n          __typename\n        }\n        designVariant {\n          ... on DesktopPromotionalFullBleedImageIrene {\n            image: image {\n              id\n              url(width: 1628, height: 304)\n              alt\n              overlayGradient\n              primaryColorHex\n              __typename\n            }\n            colorScheme\n            signature\n            __typename\n          }\n          ... on DesktopPromotionalImageLeftIrene {\n            imageOpt: image {\n              id\n              url(width: 248, height: 248)\n              alt\n              overlayGradient\n              primaryColorHex\n              __typename\n            }\n            colorScheme\n            signature\n            __typename\n          }\n          ... on DesktopPromotionalImageRightIrene {\n            imageOpt: image {\n              id\n              url(width: 248, height: 248)\n              alt\n              overlayGradient\n              primaryColorHex\n              __typename\n            }\n            colorScheme\n            signature\n            __typename\n          }\n          ... on MdotPromotionalFullBleedImageIrene {\n            image: image {\n              id\n              url(width: 718, height: 284)\n              alt\n              overlayGradient\n              primaryColorHex\n              __typename\n            }\n            colorScheme\n            signature\n            __typename\n          }\n          ... on MdotPromotionalImageLeftIrene {\n            imageOpt: image {\n              id\n              url(width: 128, height: 128)\n              alt\n              overlayGradient\n              primaryColorHex\n              __typename\n            }\n            colorScheme\n            signature\n            __typename\n          }\n          ... on MdotPromotionalImageRightIrene {\n            imageOpt: image {\n              id\n              url(width: 128, height: 128)\n              alt\n              overlayGradient\n              primaryColorHex\n              __typename\n            }\n            colorScheme\n            signature\n            __typename\n          }\n          ... on MdotPromotionalIllustrationLeftIrene {\n            imageOpt: image {\n              id\n              url(width: 200, height: 200)\n              alt\n              overlayGradient\n              primaryColorHex\n              __typename\n            }\n            colorScheme\n            signature\n            __typename\n          }\n          ... on MdotPromotionalIllustrationRightIrene {\n            imageOpt: image {\n              id\n              url(width: 200, height: 200)\n              alt\n              overlayGradient\n              primaryColorHex\n              __typename\n            }\n            colorScheme\n            signature\n            __typename\n          }\n          ... on MdotPromotionalImageTopIrene {\n            colorScheme\n            signature\n            __typename\n          }\n          __typename\n        }\n        __typename\n      }\n      ... on MerchCarouselIrene @include(if: $carouselLowCodeExp) {\n        carouselCampaignId\n        __typename\n      }\n      __typename\n    }\n    __typename\n  }\n  __typename\n}\n\nfragment VisualFiltersGroup on VisualFiltersGroup {\n  groupId: id\n  position\n  title {\n    text\n    __typename\n  }\n  visualFilters {\n    title {\n      text\n      __typename\n    }\n    description {\n      text\n      __typename\n    }\n    photoUrl\n    action {\n      name\n      context {\n        key\n        value\n        __typename\n      }\n      __typename\n    }\n    __typename\n  }\n  __typename\n}\n\nfragment PropertyUspBadges on SearchResultProperty {\n  propertyUspBadges {\n    name\n    translatedName\n    facilityId\n    __typename\n  }\n  __typename\n}\n',
            }

            response = requests.post(base_url, params=params, cookies=self.cookies, headers=self.headers, json=json_data, timeout=10)
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
    print(Crawler().search_hotels("北京", '2026-04-11', '2026-04-12'))