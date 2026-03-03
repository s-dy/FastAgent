import json
import time
from pathlib import Path
import requests
from tqdm import tqdm


def get_china_all_city() -> list:
    url = "https://geo.datav.aliyun.com/areas_v3/bound/100000_full_city.json"
    r = requests.get(url)
    # with open('../100000_full_city.json', 'w') as f:
    #     f.write(json.dumps(r.json(), indent=2, ensure_ascii=False))
    features = r.json()['features']
    result = []
    for feature in features:
        name = feature['properties']['name']
        if not name:
            continue
        result.append(name)

    return result


def send_request(prefixQuery:str) -> list[dict]:
    cookies = {
        'bkng_sso_session': 'e30',
        'cnfunco': '1',
        'cnfunco_guest': 'psVersion%3D2',
        'pcm_personalization_disabled': '0',
        'cors_js': '1',
        'BJS': '-',
        'OptanonAlertBoxClosed': '2026-03-02T07:12:14.049Z',
        'pcm_consent': 'consentedAt%3D2026-03-02T07%3A12%3A20.062Z%26countryCode%3DCN%26expiresAt%3D2026-08-29T07%3A12%3A20.062Z%26implicit%3Dfalse%26regulation%3Dpipl%26legacyRegulation%3Dgdpr%26consentId%3D5c76ed83-20f0-436f-9ef5-ff5725635ffc%26analytical%3Dfalse%26marketing%3Dfalse',
        'pcm_pac': '%5B%22f08c1512e8b788370b9d9a5205671084f4a35ae845efbdd37418b40f60997abc%22%2C6%5D',
        'header_signin_prompt': '1',
        'bk_nav_search': '%7B%22u%22%3A%22https%3A%2F%2Fwww.booking.com%2Fsearchresults.zh-cn.html%3Fss%3D%25E6%259C%259D%25E9%2598%25B3%25E5%258C%25BA%252C%2B%25E5%258C%2597%25E4%25BA%25AC%252C%2B%25E5%258C%2597%25E4%25BA%25AC%25E5%259C%25B0%25E5%258C%25BA%252C%2B%25E4%25B8%25AD%25E5%259B%25BD%26label%3Dgog235jc-10CAMoMTjcA0grWANoMYgBAZgBM7gBB8gBDNgBA-gBAfgBAYgCAagCAbgCxYuVzQbAAgHSAiQxZjg4NWFkMy1kZGM5LTRjYzQtYWVkZC1hNWJhYThhZWZhNTXYAgHgAgE%26aid%3D357003%26lang%3Dzh-cn%26sb%3D1%26src_elem%3Dsb%26src%3Dindex%26dest_id%3D1718%26dest_type%3Ddistrict%26group_adults%3D2%26no_rooms%3D1%26group_children%3D0%22%2C%22t%22%3A1772442220397%2C%22p%22%3A%22searchResults%22%7D',
        'OptanonConsent': 'implicitConsentCountry=GDPR&implicitConsentDate=1772435461329&isGpcEnabled=0&datestamp=Mon+Mar+02+2026+17%3A07%3A22+GMT%2B0800+(%E4%B8%AD%E5%9B%BD%E6%A0%87%E5%87%86%E6%97%B6%E9%97%B4)&version=202501.2.0&browserGpcFlag=0&isIABGlobal=false&hosts=&consentId=60811722-b388-4a30-a163-b478eac7041d&interactionCount=1&isAnonUser=1&landingPath=NotLandingPage&groups=C0001%3A1%2CC0002%3A0%2CC0004%3A0&AwaitingReconsent=false&backfilled_at=1772435535886&backfilled_seed=1&geolocation=CN%3BBJ',
        'bkng_sso_ses': 'eyJib29raW5nX2dsb2JhbCI6W3siaCI6Ii9MSk1SZ3luakoxZ3lGR1IvWTZkSFNjUjdHL1NMcytpZDBFdHUxcU50VjQiLCJhIjoxfV19',
        'bkng_sso_auth': 'CAIQi4nT0gIaeFC7xzF9vPxTfNuTQHmGxM8+tTmOWHbdbZ6vS/TCQ1TAqx02K7O0x99qKLlPNp2msqRZGKRCzA5nmCewFFRZFmaxEthG74n+YeoQaQf5nAaZcFy+PcFQAhy2Ub5F5wJSkvB3PlzUg71v58l038SOk3LL8vS/7+F/aA==',
        'aws-waf-token': 'd16f5cc2-3f98-436e-ad5e-bb516dab27bd:AgoAp05ABn8aAAAA:eW/4oCvEX1AQm7t9+UdLV62hRXoa4AQtIptDWNoJnx8FRuf6Jk2qsCNp02/pcGhzLjM9P3qplHbXiAOFebxOG09bI5v9gyKe2ND6779ut4RPnpUu3fZgZpNPMkvc8OFoYkAXR+ogJg6ecjS0ZGXLDTsnjrdKSEs71zbR//ASJHOugVpIojivrwMKtnbPGehoUCtB6osjgCtJY9QeEbWNJ8eIHSN7pK2ZLBQGLpaVBZDWtMF3lw6EWkJpsDrtpneUhsE=',
        'bkng': '11UmFuZG9tSVYkc2RlIyh9YXSgTtYpR%2F1WOjMvuuinviG8gHdo8mjxkaaXMkH9admRuAkfH4aJNXFWJWUdt5MsF%2BPFvs0itJjWDz%2Bv8UA1ER53ovLGJvuCT3k4AnSHo%2FOzB4%2BV6RMFuGr2i%2FsuVCV0ud5q2HfJ9jnTnmPzpNaGprxwwW6DZ58aU5YzGHAs5yGJ1KzpSVjc2ovejZ1SPrqkSQ%3D%3D',
    }

    headers = {
        'accept': '*/*',
        'accept-language': 'zh-CN,zh;q=0.9',
        'apollographql-client-name': 'b-lp-web-mfe',
        'apollographql-client-version': 'NASUYTCA',
        'cache-control': 'no-cache',
        'content-type': 'application/json',
        'ect': '4g',
        'origin': 'https://www.booking.com',
        'pragma': 'no-cache',
        'priority': 'u=1, i',
        'referer': 'https://www.booking.com/region/cn/beijing.zh-cn.html?label=gog235jc-10CAMoMTjcA0grWANoMYgBAZgBM7gBB8gBDNgBA-gBAfgBAYgCAagCAbgCxYuVzQbAAgHSAiQxZjg4NWFkMy1kZGM5LTRjYzQtYWVkZC1hNWJhYThhZWZhNTXYAgHgAgE&aid=357003',
        'sec-ch-ua': '"Not(A:Brand";v="8", "Chromium";v="144", "Google Chrome";v="144"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36',
        'x-booking-context-action': 'runway_internal_action',
        'x-booking-context-action-name': 'runway_internal_action',
        'x-booking-context-aid': '357003',
        'x-booking-csrf-token': 'eyJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJjb250ZXh0LWVucmljaG1lbnQtYXBpIiwic3ViIjoiY3NyZi10b2tlbiIsImlhdCI6MTc3MjQ0MjQ0MiwiZXhwIjoxNzcyNTI4ODQyfQ.PAAwL5Z_4XSzO0DR86OJ-_KWToMhORLKVYojAW8XGfnEVym1-9O131PQGtA52dvrxnh1bYSXdUaU5PkNI8bleQ',
        'x-booking-et-serialized-state': 'EdungUYLFjqZ486KmI63gl0PTsi_ah0Tedn64hZ2ytSnoV6lkxH77ZR0XNlWHYhk8',
        'x-booking-pageview-id': '4650402573b402a8',
        'x-booking-site-type-id': '1',
        'x-booking-topic': 'capla_browser_b-lp-web-mfe',
        # 'cookie': 'bkng_sso_session=e30; cnfunco=1; cnfunco_guest=psVersion%3D2; pcm_personalization_disabled=0; cors_js=1; BJS=-; OptanonAlertBoxClosed=2026-03-02T07:12:14.049Z; pcm_consent=consentedAt%3D2026-03-02T07%3A12%3A20.062Z%26countryCode%3DCN%26expiresAt%3D2026-08-29T07%3A12%3A20.062Z%26implicit%3Dfalse%26regulation%3Dpipl%26legacyRegulation%3Dgdpr%26consentId%3D5c76ed83-20f0-436f-9ef5-ff5725635ffc%26analytical%3Dfalse%26marketing%3Dfalse; pcm_pac=%5B%22f08c1512e8b788370b9d9a5205671084f4a35ae845efbdd37418b40f60997abc%22%2C6%5D; header_signin_prompt=1; bk_nav_search=%7B%22u%22%3A%22https%3A%2F%2Fwww.booking.com%2Fsearchresults.zh-cn.html%3Fss%3D%25E6%259C%259D%25E9%2598%25B3%25E5%258C%25BA%252C%2B%25E5%258C%2597%25E4%25BA%25AC%252C%2B%25E5%258C%2597%25E4%25BA%25AC%25E5%259C%25B0%25E5%258C%25BA%252C%2B%25E4%25B8%25AD%25E5%259B%25BD%26label%3Dgog235jc-10CAMoMTjcA0grWANoMYgBAZgBM7gBB8gBDNgBA-gBAfgBAYgCAagCAbgCxYuVzQbAAgHSAiQxZjg4NWFkMy1kZGM5LTRjYzQtYWVkZC1hNWJhYThhZWZhNTXYAgHgAgE%26aid%3D357003%26lang%3Dzh-cn%26sb%3D1%26src_elem%3Dsb%26src%3Dindex%26dest_id%3D1718%26dest_type%3Ddistrict%26group_adults%3D2%26no_rooms%3D1%26group_children%3D0%22%2C%22t%22%3A1772442220397%2C%22p%22%3A%22searchResults%22%7D; OptanonConsent=implicitConsentCountry=GDPR&implicitConsentDate=1772435461329&isGpcEnabled=0&datestamp=Mon+Mar+02+2026+17%3A07%3A22+GMT%2B0800+(%E4%B8%AD%E5%9B%BD%E6%A0%87%E5%87%86%E6%97%B6%E9%97%B4)&version=202501.2.0&browserGpcFlag=0&isIABGlobal=false&hosts=&consentId=60811722-b388-4a30-a163-b478eac7041d&interactionCount=1&isAnonUser=1&landingPath=NotLandingPage&groups=C0001%3A1%2CC0002%3A0%2CC0004%3A0&AwaitingReconsent=false&backfilled_at=1772435535886&backfilled_seed=1&geolocation=CN%3BBJ; bkng_sso_ses=eyJib29raW5nX2dsb2JhbCI6W3siaCI6Ii9MSk1SZ3luakoxZ3lGR1IvWTZkSFNjUjdHL1NMcytpZDBFdHUxcU50VjQiLCJhIjoxfV19; bkng_sso_auth=CAIQi4nT0gIaeFC7xzF9vPxTfNuTQHmGxM8+tTmOWHbdbZ6vS/TCQ1TAqx02K7O0x99qKLlPNp2msqRZGKRCzA5nmCewFFRZFmaxEthG74n+YeoQaQf5nAaZcFy+PcFQAhy2Ub5F5wJSkvB3PlzUg71v58l038SOk3LL8vS/7+F/aA==; aws-waf-token=d16f5cc2-3f98-436e-ad5e-bb516dab27bd:AgoAp05ABn8aAAAA:eW/4oCvEX1AQm7t9+UdLV62hRXoa4AQtIptDWNoJnx8FRuf6Jk2qsCNp02/pcGhzLjM9P3qplHbXiAOFebxOG09bI5v9gyKe2ND6779ut4RPnpUu3fZgZpNPMkvc8OFoYkAXR+ogJg6ecjS0ZGXLDTsnjrdKSEs71zbR//ASJHOugVpIojivrwMKtnbPGehoUCtB6osjgCtJY9QeEbWNJ8eIHSN7pK2ZLBQGLpaVBZDWtMF3lw6EWkJpsDrtpneUhsE=; bkng=11UmFuZG9tSVYkc2RlIyh9YXSgTtYpR%2F1WOjMvuuinviG8gHdo8mjxkaaXMkH9admRuAkfH4aJNXFWJWUdt5MsF%2BPFvs0itJjWDz%2Bv8UA1ER53ovLGJvuCT3k4AnSHo%2FOzB4%2BV6RMFuGr2i%2FsuVCV0ud5q2HfJ9jnTnmPzpNaGprxwwW6DZ58aU5YzGHAs5yGJ1KzpSVjc2ovejZ1SPrqkSQ%3D%3D',
    }

    params = {
        'label': 'gog235jc-10CAMoMTjcA0grWANoMYgBAZgBM7gBB8gBDNgBA-gBAfgBAYgCAagCAbgCxYuVzQbAAgHSAiQxZjg4NWFkMy1kZGM5LTRjYzQtYWVkZC1hNWJhYThhZWZhNTXYAgHgAgE',
        'aid': '357003',
        'lang': 'zh-cn',
    }

    json_data = {
        'operationName': 'AutoComplete',
        'variables': {
            'input': {
                'prefixQuery': prefixQuery,
                'nbSuggestions': 5,
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

    response = requests.post('https://www.booking.com/dml/graphql', params=params, cookies=cookies, headers=headers,json=json_data)

    results = response.json()['data']['autoCompleteSuggestions']['results']
    city_info = []
    if results:
        for item in results:
            destination = item['destination']
            dest_type = destination['destType']
            countryCode = destination['countryCode']
            # 排除非中国
            if countryCode != "cn":
                continue
            if dest_type not in ['CITY', 'DISTRICT']:
                continue
            city_info.append({
                'dest_id': destination['destId'],
                'dest_type': destination['destType'],
                'title': item['displayInfo']['title'],
                'subTitle': item['displayInfo']['subTitle']
            })
    return city_info


def build_city_dest_id(city_list: list):
    file_path = Path('city.json')
    file_path.touch(exist_ok=True)

    existing_dest_ids = set()
    with file_path.open('r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                existing_dest_ids.add(record['dest_id'])
            except (json.JSONDecodeError, KeyError):
                continue

    with file_path.open('a', encoding='utf-8') as f:
        for city in tqdm(city_list):
            time.sleep(1)
            try:
                info = send_request(city)
            except Exception as error:
                print(f"请求 '{city}' 失败: {error}")
                continue
            if not info:
                continue
            for item in info:
                dest_id = item['dest_id']
                if dest_id in existing_dest_ids:
                    continue
                existing_dest_ids.add(dest_id)
                f.write(json.dumps(item, ensure_ascii=False) + '\n')
        f.flush()

    with file_path.open('r', encoding='utf-8') as f:
        result = '[\n' + ','.join(f.readlines()) + ']'

    with file_path.open('w', encoding='utf-8') as f:
        f.write(result)


if __name__ == '__main__':
    city_list = get_china_all_city()
    build_city_dest_id(city_list)
