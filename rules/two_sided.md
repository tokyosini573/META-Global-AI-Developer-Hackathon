# 양면 시장 출시 규칙 (two_sided v1)

이 파일은 월드 엔진이 양면 시장 앱(데이팅·차량 호출·숙박·배달·가사 서비스처럼 두 집단이 서로를 찾아야 가치가 생기는 앱)의 출시를 시뮬레이션할 때 쓰는 기계적 규칙 모음이다. 근거는 `backtest/rule_set_cases.md`의 규칙용 사례 8개(Tinder, Coffee Meets Bagel, Lulu, Uber, Lyft, Airbnb, DoorDash, Homejoy)뿐이다. 다른 앱 사례나 웹 검색은 쓰지 않았고, 일반 교과서 지식(네트워크 효과, Bass 확산, 콜드 스타트, 가격)만 틀로 빌렸다. 숫자 범위는 사례에서 직접 계산했거나, 사례가 말해 주지 않으면 `note: prior, not from cases`로 표시했다. 이 파일은 백테스트를 돌리기 전에 git 커밋으로 고정한다. 고정한 뒤에 바꾸면 무엇을, 왜, 어떤 백테스트 결과를 본 뒤에 바꿨는지 README에 기록해야 한다.

공통 표기
- `active_j`: 날짜 t에 활성인 사람 j (1 또는 0). `d_ij`: 두 사람 사이 거리(km).
- `n_i = Σ_j K(d_ij)·active_j·[j가 i의 반대편]`, `K(d) = exp(−d/λ)`.
- 하루 성사 확률 `P_i = 1 − (1 − q)^{n_i}` (매치, 탑승, 예약, 주문을 모두 "성사"라고 부른다).
- `σ`, `logit`: 보정 훅 `p′ = σ(logit(p) + b)`.
- 성장률 환산: 기간 T 동안 배수 g → 일간 상대 성장률 `r = ln(g)/T`.

---

### 1. 한 지역에 촘촘하게 모아야 첫 성사가 빨리 나온다 (지역 밀도 문턱)

```yaml
id: local_density_threshold
mechanism: 가까운 반대편 활성 사용자 수 n_i가 문턱을 넘어야 하루 성사 확률이 의미 있게 올라가므로, 같은 인원이면 좁은 지역에 몰아 넣은 출시가 첫 성사와 재방문을 더 빨리 만든다.
applies_when:
  - 성사가 물리적 거리에 묶이는 앱 (만남, 탑승, 배달, 방문 서비스, 숙박 호스트-게스트 도시 단위)
  - 출시 첫 90일, 사용자가 아직 수천 명 이하인 콜드 스타트 구간
formula: |
  n_i(t) = Σ_j exp(−d_ij/λ) · active_j(t)   # 반대편만 합산
  P_i(t) = 1 − (1 − q)^{n_i(t)}
  # 콜드 스타트 이탈: 첫 성사 전 하루 이탈 위험이 n_i가 작을수록 커진다
  h_i(t) = h_base · (1 + γ · 1[아직 첫 성사 없음 ∧ t − install_i > T_wait])
  # 보정: 지역별 평균 성사율을 벤치마크에 맞출 때 b는 전 지역 공통 하나만 쓴다
  #       (지역마다 따로 맞추면 밀도 효과가 사라진다)
parameters:
  lambda_km:
    range: [1, 10]
    unit: km
    note: "사례의 씨앗 지역 크기에서 잡음. 캠퍼스(USC, 플로리다 두 대학)는 반경 1~3km, DoorDash의 팔로알토·스탠퍼드·멘로파크·로스알토스·마운틴뷰 묶음은 지름 약 10~15km. 측정값이 아니라 지역 크기 추정."
  seed_side_size:
    range: [50, 300]
    unit: 명 또는 공급자 수 (첫 지역의 출시 시점 씨앗)
    note: "Tinder 지인 약 300명 문자, DoorDash 식당 50곳, Lyft +4개월 드라이버 약 200명, DoorDash 드라이버 4명→30명. 단위가 섞여 있어 크기 감만 준다."
  seed_area_penetration_15mo:
    range: [0.10, 0.25]
    unit: 씨앗 지역 가구/사람 중 한 번 이상 써 본 비율 (+15개월)
    note: "DoorDash '지역 가구 6곳 중 1곳'(≈0.17, 회사 주장) 한 점뿐이라 양쪽으로 넓힘."
  T_wait:
    range: [3, 14]
    unit: 일
    note: "prior, not from cases. 사례에 첫 성사까지 기다리는 시간 자료 없음."
  gamma:
    range: [0.5, 3.0]
    unit: 배수 (기본 이탈 위험 대비 추가분)
    note: "prior, not from cases."
predicts:
  - "같은 설치 수에서 씨앗 지역 반경이 작은(밀도가 높은) 계획이 첫 성사까지 걸리는 중앙값 일수가 더 짧다."
  - "같은 설치 수에서 밀도가 높은 계획이 30일 시점 활성 비율이 더 높다."
  - "여러 곳에 흩어 뿌린 계획은 설치 수가 같아도 첫 성사 없이 이탈하는 사람 비율이 더 높다."
evidence:
  - {case: Tinder, fact: "USC 지인 약 300명 문자로 시작, 2012-09-29 앱 있어야 입장하는 파티", date: "2012-08~09", source_url: "https://techcrunch.com/2014/07/09/whitney-wolfe-vs-tinder/", strength: strong}
  - {case: DoorDash, fact: "팔로알토 일대 한 지역에서 시작, 사우스베이에만 18개월, +15개월에 지역 가구 6곳 중 1곳 주문 경험", date: "2013-02 ~ 2014-05-22", source_url: "https://techcrunch.com/2014/05/22/doordash-17-3m-sequoia", strength: strong}
  - {case: Uber, fact: "+8개월까지 유료 탑승 수만 건이 전부 SF", date: "2011-02-14", source_url: "https://techcrunch.com/?p=275062", strength: strong}
  - {case: Lyft, fact: "SF 단독으로 약 8개월, +4개월 드라이버 약 200명", date: "2012-09-17", source_url: "https://techcrunch.com/2012/09/17/lyfts-focus-on-community-and-the-story-behind-the-pink-mustache/", strength: strong}
  - {case: Airbnb, fact: "YC 기간 뉴욕 한 도시에 집중", date: "2009-01~02", source_url: "https://paulgraham.com/airbnbs.html", strength: strong}
counter_evidence:
  - {case: Lulu, fact: "두 캠퍼스 초대제로 촘촘하게 시작했지만 실패. 밀도는 필요조건일 뿐 충분조건이 아님", date: "2013-01 ~ 2016-02", source_url: "https://techcrunch.com/?p=751260", strength: strong}
  - {case: Coffee Meets Bagel, fact: "뉴욕에서 시작했지만 한 달 만에 보스턴 추가(도시 순서는 Wikipedia 경유)하고도 독립 유지", date: "2012-05", source_url: "https://techcrunch.com/2012/04/17/coffee-meets-bagel-turns-online-dating-into-a-daily-deal/", strength: weak}
confidence: high
```

성공한 다섯 사례는 모두 캠퍼스, 한 도시, 한 동네처럼 좁은 곳에서 시작했다. 엔진에서는 거리 커널로 "내 근처에 반대편이 몇 명 살아 있나"를 세고, 그 수가 작으면 첫 성사가 늦어지고 그 사이에 사람들이 떠난다. 다만 Lulu는 같은 방식으로 시작하고도 실패했다. 그래서 이 규칙은 "밀도 없이는 안 된다"까지만 말하고, "밀도만 있으면 된다"고는 말하지 않는다.

### 2. 첫 도시가 자리 잡기 전에 도시를 늘리면 도시마다 밀도가 얇아진다 (확장 속도)

```yaml
id: expansion_pace_dilution
mechanism: 새 도시는 매번 콜드 스타트를 다시 겪으므로, 예산·운영 인력·씨앗 사용자를 여러 도시에 나누면 도시당 n_i가 문턱 아래로 떨어져 전체 설치는 늘어도 성사와 재방문은 줄어든다.
applies_when:
  - 계획에 'open city X on day d' 이벤트가 둘 이상 있다
  - 도시 사이 거리가 λ보다 훨씬 커서 도시끼리 n_i를 나눠 갖지 못한다
formula: |
  # 도시 c의 씨앗과 광고 예산은 열린 도시 수 C(t)로 나눈다
  seed_c = S_total / C(t),  budget_c = B_total / C(t)
  reach_c = 1 − exp(−k · F_c),  F_c ∝ budget_c          # 광고 포화 훅
  # 도시별 유동성 L_c(t) = 지난 7일 성사 수 / 지난 7일 활성 수
  # 게이트(좋은 계획의 모양): L_{c-1}(t) ≥ L* 일 때만 다음 도시를 연다
  # 운영 부담: 동시에 갓 연 도시(개설 90일 미만) 수 C_new 만큼 서비스 품질 q가 깎인다
  q_c' = σ(logit(q_c) − δ · max(0, C_new − 1))
parameters:
  months_to_second_city_success:
    range: [1, 18]
    unit: 개월 (출시 → 두 번째 도시)
    note: "Coffee Meets Bagel 약 1(⚠️ Wikipedia), Airbnb 약 5(덴버 행사 → 뉴욕), Lyft 약 8, Uber 약 11, DoorDash 18 이상. 성공·애매 사례의 실제 범위 그대로."
  cities_at_12mo_success:
    range: [1, 4]
    unit: 도시 수 (+12개월)
    note: "Uber 2(SF·뉴욕), Lyft 4(+12), DoorDash 1 지역, Coffee Meets Bagel 약 3~4(⚠️). 비교: Homejoy +10개월에 26개."
  cities_at_12mo_failure_reference:
    range: [20, 30]
    unit: 도시 수
    note: "Homejoy +10개월 26개, +14개월 30개 시장. 실패 사례 한 점이라 '이 정도면 위험' 기준으로만 쓴다."
  L_star:
    range: [0.05, 0.30]
    unit: 주간 활성 1명당 주간 성사 수
    note: "prior, not from cases. 사례에 도시별 유동성 숫자가 없음."
  delta:
    range: [0.0, 0.5]
    unit: logit 감점 / 추가 신규 도시 1개
    note: "prior, not from cases. 0이면 운영 부담 효과를 끈다."
predicts:
  - "같은 예산에서 90일 안에 도시를 더 많이 여는 계획은 누적 설치가 같거나 더 많아도, 도시당 활성 1명당 성사 수와 30일 잔존율이 더 낮다."
  - "첫 도시의 유동성이 L*를 넘은 뒤 두 번째 도시를 여는 계획이, 날짜만 보고 동시에 여는 계획보다 90일 활성 사용자가 더 많다."
evidence:
  - {case: Uber, fact: "SF 약 11개월 뒤 뉴욕(2011-05), 이후 시애틀·시카고·보스턴·파리, +18개월 6개 도시", date: "2010-06 ~ 2011-12", source_url: "https://www.uber.com/en-FR/blog/paris/were-going-global-with-big-funding", strength: strong}
  - {case: Lyft, fact: "SF 약 8개월 뒤 LA(2013-01-31), +12개월 4개 도시, +14개월 6개 도시", date: "2013-01 ~ 2013-07", source_url: "https://techcrunch.com/2013/05/23/lyft-a16z", strength: strong}
  - {case: DoorDash, fact: "사우스베이 18개월 뒤에야 LA·보스턴·시카고, SF는 2015-01", date: "2015-01-27", source_url: "https://techcrunch.com/2015/01/27/doordash-sf/", strength: strong}
  - {case: Homejoy, fact: "6개월 남짓에 1개 → 26개 도시, +14개월 30개 시장, 2015-07-31 종료", date: "2013-08-18 ~ 2015-07-31", source_url: "https://techcrunch.com/2013/08/18/homejoy-behind-the-scenes/", strength: strong}
  - {case: Coffee Meets Bagel, fact: "프로모 첫 데이트 선물을 뉴욕 밖에서는 확장 속도 때문에 뺌 (확장이 도시당 투입을 줄인다는 직접 예)", date: "2012~2013", source_url: "https://techcrunch.com/2013/08/22/coffee-meets-bagel-launches-iphone-app-nationally/", strength: strong}
counter_evidence:
  - {case: Coffee Meets Bagel, fact: "한 달 만에 두 번째 도시를 열고도 실패하지 않음(결과는 애매)", date: "2012-05", source_url: "https://techcrunch.com/2012/09/26/daily-dating-site-coffee-meets-bagel-lands-600k-from-lightbank-match-com-co-founder/", strength: weak}
  - {case: Lyft, fact: "+22개월에 24개 도시로 빠르게 늘었지만 성공. 빠른 확장 자체가 아니라 '자리 잡기 전' 확장이 문제라는 해석과 맞지만, 사례만으로는 두 해석을 가르지 못함", date: "2014-03", source_url: "https://www.nbcnews.com/news/amp/wbna54636501", strength: weak}
  - {case: Homejoy, fact: "Homejoy 실패 원인이 확장 속도인지는 사례 파일이 말하지 않음. 예약·매출이 공개된 적 없어 도시당 밀도를 확인할 수 없음", date: "2015-07", source_url: "https://techcrunch.com/2015/07/17/homejoy-is-shutting-down-at-the-end-of-the-month/", strength: weak}
confidence: medium
```

성공 사례들은 두 번째 도시를 열기까지 대개 8~18개월을 기다렸고, 실패한 Homejoy는 열 달 만에 26개 도시를 열었다. 엔진은 도시마다 씨앗과 예산을 나눠 주고 도시마다 콜드 스타트를 다시 시키므로, 너무 빨리 넓히면 도시마다 얇아지는 결과가 저절로 나온다. Homejoy 한 건이 실패 쪽 근거의 전부라서 확신도는 중간이다.

### 3. 씨앗 무리와 행사가 양쪽을 같은 시간·같은 장소에 모은다 (씨앗과 행사 펄스)

```yaml
id: seed_cohort_event_pulse
mechanism: 창업자 인맥이나 큰 행사처럼 양쪽이 같은 날 같은 곳에 모이는 계기는 active_j를 한꺼번에 올려 n_i를 문턱 위로 밀어 올리지만, 행사 뒤 밀도가 유지되지 않으면 펄스는 그대로 꺼진다.
applies_when:
  - 계획에 출시일 행사, 캠퍼스 파티, 큰 지역 행사(공급 부족이 생기는 날) 같은 일회성 이벤트가 있다
  - 또는 출시 첫날 특정 무리(지인, 동아리, 한 건물)에 집중 초대를 보낸다
formula: |
  # 행사일 d_e, 참석자 집합 E (반경 r_e 안, 양쪽 모두)
  install_prob_j(d_e) = σ(logit(p_install_j) + b_event)        # j ∈ E
  # 행사 뒤 Bass의 혁신 계수 p를 짧게 올린다
  p(t) = p_0 + Δp · exp(−(t − d_e)/τ_event) · 1[t ≥ d_e]
  # 공급 부족 행사(숙소·차량이 모자란 날)는 수요 쪽 q를 그날만 올린다
  q(d_e) = q · m_shortage
parameters:
  seed_invites:
    range: [100, 300]
    unit: 명
    note: "Tinder 지인 약 300명 문자, Lulu 경품 조건 '남성 300명 먼저 평가'. 사례 규모 그대로."
  event_supply_adds_per_day:
    range: [50, 100]
    unit: 행사 기간 하루 신규 공급 등록 수
    note: "Airbnb 덴버 전당대회 기간 하루 신규 등록 50~100개(✅). 한 행사 한 점."
  event_demand_served:
    range: [600, 600]
    unit: 행사 1회에서 성사된 수요 쪽 사람 수 (하한)
    note: "Airbnb '600명 이상이 숙소 찾음'. 규모 감만 주는 하한값. 시뮬레이션 인구 1,000~2,000명에 쓸 때는 비율로 줄여 쓴다."
  tau_event:
    range: [3, 21]
    unit: 일
    note: "prior, not from cases. 행사 효과가 얼마나 오래가는지 사례가 말하지 않음."
  m_shortage:
    range: [1.0, 3.0]
    unit: 배수
    note: "prior, not from cases. 호텔 매진 같은 공급 부족일에만."
predicts:
  - "출시 행사가 있는 계획은 행사일 전후 설치·첫 성사가 계단처럼 뛴다."
  - "행사 뒤 30일 활성은 행사 반경 안의 밀도가 문턱(local_density_threshold)을 넘었을 때만 유지되고, 아니면 행사 없는 계획 수준으로 돌아간다."
evidence:
  - {case: Tinder, fact: "지인 약 300명 문자 → 2012-09-29 앱 있어야 입장하는 파티", date: "2012-09-29", source_url: "https://techcrunch.com/2014/07/09/whitney-wolfe-vs-tinder/", strength: strong}
  - {case: Airbnb, fact: "호텔이 매진된 덴버 민주당 전당대회에 맞춰 재출시, 600명 이상 숙소 찾음, 하루 신규 등록 50~100개", date: "2008-08-11", source_url: "https://techcrunch.com/2008/08/11/airbed-and-breakfast-takes-pad-crashing-to-a-whole-new-level/", strength: strong}
  - {case: Lulu, fact: "경품 콘테스트와 캠퍼스 에이전트로 첫 달 6만 다운로드 이상, 리뷰 14만 (회사 주장)", date: "2013-02-05", source_url: "https://techcrunch.com/?p=751260", strength: weak}
counter_evidence:
  - {case: Airbnb, fact: "행사 뒤에도 바로 자리 잡지 못하고 약 6개월 뒤 뉴욕에 집중하고 나서야 '라면 수익'. 행사 펄스만으로는 유지되지 않음", date: "2009-02-22", source_url: "https://paulgraham.com/airbnbs.html", strength: strong}
  - {case: Lulu, fact: "강한 초기 펄스를 만들고도 실패", date: "2016-02-09", source_url: "https://techcrunch.com/?p=1274326", strength: strong}
confidence: medium
```

Tinder 파티와 Airbnb 전당대회는 양쪽을 한날한시에 한곳에 모아 첫 성사를 한꺼번에 만들었다. 엔진에서는 행사가 그날 설치와 입소문 계수를 잠깐 올려 준다. 하지만 두 반대 사례가 보여 주듯 행사 효과는 사라지므로, 행사 뒤에도 밀도가 남아 있어야 성장으로 이어진다.

### 4. 초기에 손으로 공급 품질을 끌어올리면 성사율이 오른다 (수작업 공급 품질)

```yaml
id: manual_supply_quality
mechanism: 출시 초기에 창업자가 직접 공급 쪽 품질(사진, 배달, 응대)을 챙기면 노출 1회당 성사 확률 q가 올라가 적은 인원으로도 성사가 나오지만, 이 효과는 운영자가 직접 손댈 수 있는 지역과 기간에만 있다.
applies_when:
  - 공급 쪽 품질이 사용자마다 크게 다르고 수요 쪽이 그 품질을 보고 고른다 (숙소 사진, 배달 신뢰도, 프로필 품질)
  - 계획에 '창업자/운영팀 직접 개입' 같은 수작업 항목이 있고, 대상이 한두 지역에 한정된다
formula: |
  # 개입 대상 공급자 s ∈ M (운영자가 직접 손댈 수 있는 수 M_cap 이하)
  q_s' = σ(logit(q_s) + b_quality)          # s ∈ M
  # 개입 가능 수는 지역 수에 반비례 (expansion_pace_dilution 과 연결)
  M_cap_c = M_total / C(t)
parameters:
  weekly_revenue_multiplier_during_intervention:
    range: [1.6, 2.0]
    unit: 주간 배수
    note: "Airbnb 뉴욕 호스트 방문·전문 사진 기간 주간 수수료 수입 $460 → $897(×1.95) → $1,428(×1.59). 두 주 두 점이고 다른 원인과 섞여 있어 b_quality 를 직접 주지는 않는다."
  founder_handled_transactions:
    range: [100, 200]
    unit: 건
    note: "DoorDash 첫 200건을 창업자 4명이 직접 배달. 운영자가 직접 처리할 수 있는 규모 감."
  b_quality:
    range: [0.0, 1.0]
    unit: logit 가산
    note: "prior, not from cases. 위 배수와 모순되지 않는 넓은 범위. 0이면 효과를 끈다."
predicts:
  - "공급 쪽 직접 개입이 있는 계획은 같은 공급자 수에서 첫 30일 성사 수가 더 많다."
  - "개입 대상 지역을 넓힐수록 공급자 1명당 개입 효과가 줄어든다."
evidence:
  - {case: Airbnb, fact: "YC 기간 뉴욕 호스트를 직접 찾아가 전문 사진 촬영, 주간 수수료 수입 $460 → $897 → $1,428, 2009-02-22 '라면 수익'", date: "2009-01 ~ 2009-02", source_url: "https://paulgraham.com/airbnbs.html", strength: strong}
  - {case: DoorDash, fact: "하루 만에 사이트 제작, 첫 200건 창업자 직접 배달, 여름 동안 주문 10배", date: "2013-02 ~ 2013-09", source_url: "https://stanforddaily.com/2013/09/23/alumni-founded-startup-caters-to-palo-alto-mountain-view-food-deliveries/", strength: strong}
counter_evidence:
  - {case: Airbnb, fact: "수입 증가가 사진 때문인지, 뉴욕 집중·계절·YC 자체 때문인지 사례가 가르지 못함", date: "2009-02", source_url: "https://paulgraham.com/airbnbs.html", strength: weak}
confidence: low
```

Airbnb는 뉴욕 호스트를 직접 찾아가 사진을 찍었고, 그 몇 주 동안 수입이 매주 1.6~2배 늘었다. DoorDash는 첫 200건을 창업자가 직접 배달했다. 엔진에서는 운영자가 손댄 공급자의 성사 확률을 조금 올린다. 원인이 섞여 있어 효과 크기는 prior로만 둔다.

### 5. 입소문 성장 속도는 사례에서 잰 범위 안에서 정한다 (Bass q 보정)

```yaml
id: wom_growth_rate_band
mechanism: 초기 구간(N ≪ M)에서 Bass 확산의 상대 성장률은 대략 q이므로, 사례가 공개한 월간·주간 성장률을 일간 q로 바꾼 범위를 입소문 계수의 상한 띠로 쓰고, 성장률이 높다는 것만으로 성공을 예측하지 않는다.
applies_when:
  - 모든 양면 시장 실행 (Bass 훅을 쓰는 한 항상)
  - 특히 두 계획의 입소문 계수를 따로 고를 때, 둘 다 이 띠 안에 있어야 한다
formula: |
  dN/dt = (p + q · N/M) · (M − N)
  # 초기 근사: (dN/dt)/N ≈ q · (1 − N/M) + p · M/N  →  N ≪ M 이고 p 항이 작으면 ≈ q
  # 사례 성장률 g(기간 T) → r = ln(g)/T  를 q_eff 로 둔다
  # 입소문은 성사를 겪은 사람만 퍼뜨린다 (밀도 규칙과 연결)
  q_i = q_eff · 1[i 가 최근 30일 안에 성사 1회 이상]
parameters:
  q_eff_daily:
    range: [0.008, 0.026]
    unit: 1/일
    note: "사례 성장률을 r = ln(g)/T 로 환산. Tinder 하루 매치 350만(+14) → 1,000만(+18), 약 120일: 0.0087. Uber 월 34%: 0.0098. Lyft 주간 탑승 1.4만 → 3만, 약 2개월: 0.0125. Coffee Meets Bagel 월 +50%(+5): 0.0135. DoorDash 주 20%(+7): 0.026, 여름 주문 10배(약 90일): 0.026. 지표가 사용자·탑승·주문·매치로 섞였고, 유료 마케팅과 p 항도 섞여 있다. 공개한 쪽이 성공·투자 유치 기업이라 상한 쪽으로 치우쳤다고 본다."
  growth_multiple_90d_implied:
    range: [2.0, 10.4]
    unit: 90일 배수 (= exp(q_eff·90))
    note: "위 q_eff 범위에서 계산. 엔진 결과가 이 띠를 크게 벗어나면 보정을 의심한다."
  failure_growth_reference:
    range: [0.003, 0.03]
    unit: 1/일
    note: "Homejoy '월 두 자릿수 성장'(월 10% 이상 → 0.003 이상). 상한은 알 수 없어 성공 띠 상한을 그대로 씀. 실패 사례도 성장률이 띠 안에 있었다는 뜻."
  p_innovation_daily:
    range: [0.0001, 0.003]
    unit: 1/일
    note: "prior, not from cases. 사례에 광고·언론 효과를 분리한 숫자가 없음."
predicts:
  - "엔진이 낸 90일 성장 배수는 두 계획 모두 약 2~10배 띠 안에 든다. 밖으로 나가면 보정 실패로 본다."
  - "입소문 계수가 같다면, 성사를 겪은 사람이 더 많은 계획(밀도가 높은 계획)이 90일 설치가 더 많다."
evidence:
  - {case: Tinder, fact: "하루 매치 350만(2013-10-31) → 500만(2013-12) → 1,000만(2014-02-28)", date: "2013-10-31 ~ 2014-02-28", source_url: "https://siliconrepublic.com/?p=319667", strength: weak}
  - {case: Uber, fact: "+18개월 월 34% 이상 성장 (회사 주장)", date: "2011-12-06", source_url: "https://www.uber.com/en-FR/blog/paris/were-going-global-with-big-funding", strength: weak}
  - {case: Lyft, fact: "주간 탑승 1.4만 → 3만 (2개월)", date: "2013-05-23", source_url: "https://techcrunch.com/2013/05/23/lyft-a16z", strength: strong}
  - {case: Coffee Meets Bagel, fact: "+5개월 월 +50%, 주로 입소문", date: "2012-09-26", source_url: "https://techcrunch.com/2012/09/26/daily-dating-site-coffee-meets-bagel-lands-600k-from-lightbank-match-com-co-founder/", strength: strong}
  - {case: DoorDash, fact: "주 20% 이상 성장, 여름 동안 주문 10배", date: "2013-09-30", source_url: "https://www.ycombinator.com/blog/doordasy-yc-s13-raises-2-dollars-dot-4m-to-improve-food-delivery-growing-over-20-percent-weekly/", strength: strong}
counter_evidence:
  - {case: Homejoy, fact: "+14개월 '월 두 자릿수 성장'이었지만 약 2년 뒤 종료. 성장률은 생존을 가르지 못함", date: "2013-12-05", source_url: "https://techcrunch.com/2013/12/05/homejoy-38-m/", strength: strong}
  - {case: Coffee Meets Bagel, fact: "+5개월 월 +50%였지만 +16개월 사용자 약 8만으로 결과 애매. 초기 고성장이 지속되지 않을 수 있음", date: "2013-08-22", source_url: "https://techcrunch.com/2013/08/22/coffee-meets-bagel-launches-iphone-app-nationally/", strength: strong}
confidence: medium
```

사례가 공개한 성장률을 하루 단위로 바꾸면 0.8%~2.6%/일, 즉 90일에 약 2~10배다. 엔진의 입소문 계수는 이 띠 안에서만 고르고, 성사를 겪은 사람만 입소문을 내게 해서 밀도 규칙과 이어 둔다. Homejoy도 빨리 자랐으므로 성장률 자체는 승패 판정에 쓰지 않는다.

### 6. 하루 노출 수 × 노출당 성사율이 성사량을 정한다 (노출 처리량)

```yaml
id: exposure_throughput
mechanism: 하루 성사 수는 사람마다 하루에 보는 반대편 후보 수(노출)와 노출 1회당 성사 확률의 곱이므로, 노출을 적게 주는 큐레이션 설계는 재방문율은 높아도 성사 총량과 입소문 재료가 적고, 노출을 많이 주는 설계는 노출당 성사율이 낮아도 총량이 크다(단, 근처 후보 풀이 바닥나지 않을 때).
applies_when:
  - 사용자가 후보를 하나씩 보고 고르는 매칭형 앱 (데이팅, 공급자 선택형 마켓)
  - 두 계획이 하루 노출 상한이나 추천 방식에서 다를 때
formula: |
  pool_i(t) = n_i(t)                                # 밀도 규칙의 근처 반대편 수
  E_i(t) = min(E_cap, pool_i(t) − seen_i(t))       # 이미 본 후보는 빼서 풀이 바닥난다
  P_i(t) = 1 − (1 − q_e)^{E_i(t)}                   # 노출 1회 = 시도 1회
  # 열람(앱을 여는지)은 LLM 선택을 보정해 정한다
  open_i(t) ~ Bernoulli(σ(logit(p_open_i) + b_open)),  mean = open_rate
parameters:
  q_e_swipe:
    range: [0.010, 0.014]
    unit: 매치 / 노출(스와이프) 1회
    note: "Tinder 하루 스와이프 3.5억에 매치 350만 = 1.0%(+14), 7.5억에 1,000만 = 1.33%(+18). CEO 발언이라 weak. 대량 노출형 설계에 쓴다."
  q_e_curated:
    range: [0.03, 0.06]
    unit: 직접 연결 / 소개 1회
    note: "Coffee Meets Bagel 소개 10만 건 이상에 직접 연결 약 6,000 → 6% 이하. 분모가 하한이라 아래로 넓힘. 하루 1명 큐레이션 설계에 쓴다."
  E_cap_curated:
    range: [1, 1]
    unit: 노출 / 일
    note: "Coffee Meets Bagel 하루 한 명(정오)."
  E_cap_swipe:
    range: [20, 200]
    unit: 노출 / 일
    note: "prior, not from cases. Tinder 숫자는 총량뿐이고 사용자 수가 공개되지 않아 1인당 스와이프를 계산할 수 없음."
  open_rate_curated:
    range: [0.60, 0.75]
    unit: 하루 열람 비율
    note: "Coffee Meets Bagel '매일 확인 70%'(+5). 한 점이라 양쪽으로 조금 넓힘."
predicts:
  - "근처 후보 풀이 충분하면(n_i ≫ E_cap), 노출 상한이 높은 계획이 90일 누적 성사가 더 많다."
  - "노출 상한이 낮은 계획은 하루 열람률이 더 높다."
  - "근처 후보 풀이 작으면(밀도가 낮으면) 노출 상한을 높여도 성사가 늘지 않고 seen_i 가 풀을 다 써서 이탈이 늘어난다."
evidence:
  - {case: Tinder, fact: "하루 스와이프 3.5억, 매치 350만", date: "2013-10-31", source_url: "https://www.globaldatinginsights.com/mobile/31102013-tinder-sees-350m-swipes-day-ceo-sean-rad-hints-future-plans/", strength: weak}
  - {case: Tinder, fact: "하루 스와이프 7.5억, 매치 1,000만, 누적 매치 약 10억 (회사 주장)", date: "2014-02-28", source_url: "https://siliconrepublic.com/?p=319667", strength: weak}
  - {case: Coffee Meets Bagel, fact: "하루 한 명, 소개 10만 건 이상, 직접 연결 약 6,000, 매일 확인 70%", date: "2012-09-26", source_url: "https://techcrunch.com/2012/09/26/daily-dating-site-coffee-meets-bagel-lands-600k-from-lightbank-match-com-co-founder/", strength: strong}
  - {case: Coffee Meets Bagel, fact: "+16개월 사용자 약 8만, 매치 150만 이상 (매치 정의가 '직접 연결'과 다를 수 있음)", date: "2013-08-22", source_url: "https://techcrunch.com/2013/08/22/coffee-meets-bagel-launches-iphone-app-nationally/", strength: strong}
counter_evidence:
  - {case: Coffee Meets Bagel, fact: "두 앱의 차이는 노출 설계 말고도 출시 방식·가격·플랫폼(웹 → 앱)이 모두 달라, 성사량 차이를 노출 설계 하나로 돌릴 수 없음", date: "2012~2014", source_url: "https://techcrunch.com/2013/08/22/coffee-meets-bagel-launches-iphone-app-nationally/", strength: weak}
confidence: medium
```

스와이프형은 노출 1회당 매치가 1% 남짓이고, 하루 한 명 큐레이션형은 소개 1회당 연결이 6% 정도다. 대신 큐레이션형은 하루에 한 번만 보여 주므로 총량이 작다. 엔진은 "하루에 몇 명을 보여 주나 × 한 명당 성사 확률"로 성사 수를 내고, 근처 후보가 바닥나면 노출을 늘려도 소용없게 만든다.

### 7. 참여 자체에 돈을 받는 시점은 밀도가 생긴 뒤여야 한다 (과금 시점)

```yaml
id: monetization_timing
mechanism: 거래마다 붙는 수수료는 성사가 일어날 때만 걷히므로 첫날부터 붙여도 밀도를 해치지 않지만, 참여 자체를 막는 유료 장벽(구독, 열람 제한)은 문턱 이전에 활성 수를 줄여 n_i와 입소문을 함께 깎으며, 장벽을 넘어 돈을 내는 사람은 활성의 몇 %에 그친다.
applies_when:
  - 계획에 pricing 이벤트(paywall, free trial 종료, 수수료 시작)가 있다
  - 과금 방식을 '참여 과금(access)'과 '거래 과금(transaction)'으로 나눌 수 있다
formula: |
  # 참여 과금 이벤트 day d_pw 이후, 무료로 남지 않은 사람의 활동 확률을 깎는다
  active_prob_i' = σ(logit(active_prob_i) − b_paywall)    # 비결제자, t ≥ d_pw
  pay_i ~ Bernoulli(σ(logit(p_pay_i) + b_pay)),  b_pay 는 평균이 payer_share 가 되게 푼다
  # 거래 과금: 성사 1건마다 take_rate · price 만큼 매출, 활동 확률은 건드리지 않는다
  # (가격이 수요 쪽 성사 확률 q 에 주는 영향은 LLM 선택 + 보정으로만 반영)
parameters:
  payer_share_freemium:
    range: [0.03, 0.05]
    unit: 활성 사용자 중 결제자 비율
    note: "Coffee Meets Bagel beans 구매 3~5%(+16). 처음부터 프리미엄이었던 한 사례."
  free_months_before_access_paywall_success:
    range: [0, 31]
    unit: 개월
    note: "Tinder 약 2.5년(2012-08 → 2015-03-02 Tinder Plus) 무료, Coffee Meets Bagel 0개월(처음부터 프리미엄, 결과 애매). 범위가 넓은 것이 정직한 답."
  b_paywall:
    range: [0.0, 1.5]
    unit: logit 감점
    note: "prior, not from cases. 장벽이 활성에 주는 효과를 분리한 숫자가 사례에 없음."
predicts:
  - "참여 과금을 90일 안에 켜는 계획은 켜지 않는 계획보다 90일 활성과 누적 성사가 적고, 매출은 많다."
  - "거래 과금만 쓰는 계획은 수수료율이 같으면 과금 시작 시점이 활성 사용자 곡선을 거의 바꾸지 않는다."
  - "참여 과금 계획의 결제자는 활성 사용자의 약 3~5% 근처로 보정된다."
evidence:
  - {case: Tinder, fact: "약 2.5년 무료, 첫 유료 상품 2015-03-02 ($9.99, 30세 이상 $19.99)", date: "2015-03-02", source_url: "https://fortune.com/2015/03/02/tinder-plus-cost", strength: strong}
  - {case: Coffee Meets Bagel, fact: "처음부터 프리미엄(beans 획득·구매), beans 구매 3~5%, +16개월 사용자 약 8만", date: "2013-08-22", source_url: "https://techcrunch.com/2013/08/22/coffee-meets-bagel-launches-iphone-app-nationally/", strength: strong}
  - {case: DoorDash, fact: "첫날부터 배달비 $6, 최소 주문 없음, 식당 수수료 — 거래 과금을 처음부터 붙이고 성장", date: "2013-02", source_url: "https://techcrunch.com/2013/07/26/y-combinator-backed-doordash-delivers-food-quickly-in-south-bay-hopes-to-expand-beyond-food/", strength: strong}
  - {case: Uber, fact: "처음부터 유료 탑승(프리미엄 블랙카), +18개월 라이더 1인 월 $100 이상 (회사 주장)", date: "2011-12-06", source_url: "https://www.uber.com/en-FR/blog/paris/were-going-global-with-big-funding", strength: weak}
  - {case: Airbnb, fact: "초기부터 거래 수수료 수입이 있었음(주간 $460 → $1,428). 수수료율은 사례에 없음", date: "2009-02", source_url: "https://paulgraham.com/airbnbs.html", strength: strong}
counter_evidence:
  - {case: Lulu, fact: "출시 때 수익 모델이 아예 없었고 실패. '무료로 오래 두면 된다'는 방향만으로는 생존을 설명하지 못함", date: "2013-01 ~ 2016-02", source_url: "https://techcrunch.com/?p=751260", strength: strong}
  - {case: Coffee Meets Bagel, fact: "처음부터 프리미엄이었는데도 실패하지 않고 독립 유지. 참여 과금 효과가 결정적이라는 근거는 없음", date: "2018-05", source_url: "https://techcrunch.com/2013/08/22/coffee-meets-bagel-launches-iphone-app-nationally/", strength: weak}
confidence: low
```

거래가 일어날 때만 돈을 받는 앱(DoorDash, Uber, Airbnb)은 첫날부터 돈을 받고도 컸다. 참여 자체에 값을 매기는 앱에서는 Tinder가 2.5년 무료였고, 처음부터 유료 아이템을 판 Coffee Meets Bagel은 결제자가 3~5%였다. 효과 크기는 사례가 말해 주지 않아서 방향과 결제자 비율만 고정하고 나머지는 prior로 둔다.

### 8. 할인으로 데려온 수요는 정가로 돌아오지 않는다 (보조금 의존 수요) — 실패 설명

```yaml
id: subsidy_dependent_demand
mechanism: 첫 거래를 크게 깎아 주면 첫 거래 수는 빨리 늘지만, 할인으로 들어온 사람의 정가 재구매 확률은 낮고 공급 쪽 보수와 할인을 빼면 거래당 남는 몫이 음수가 될 수 있어, 겉으로는 성장하면서 속으로는 돈이 새는 구조가 된다.
applies_when:
  - 계획에 첫 거래 할인, 무료 체험 거래, 크레딧 같은 subsidy 이벤트가 있다
  - 거래당 플랫폼 몫(take rate)이 작고 공급 쪽 보수가 가격의 큰 부분인 서비스
formula: |
  # 할인 경유 첫 거래 여부 promo_i
  p_repeat_i' = σ(logit(p_repeat_i) − b_promo · promo_i)      # 정가 재구매
  margin_tx = take_rate · price − discount_tx                  # 거래당 플랫폼 몫
  contribution(t) = Σ_tx margin_tx                             # 누적 공헌이익
  # 보고 지표: 첫 거래 수와 함께 '정가 2회차 거래 비율'과 contribution 을 반드시 낸다
parameters:
  take_rate:
    range: [0.20, 0.40]
    unit: 가격 대비 플랫폼 몫
    note: "Homejoy 시간당 $20, 클리너 보수 $12~15 → (20−15)/20 = 0.25 ~ (20−12)/20 = 0.40. Lyft 기부액의 20%(⚠️ 2014 자료)."
  first_tx_discount:
    range: [0.5, 0.8]
    unit: 정가 대비 할인율
    note: "Homejoy 첫 청소 $19, 정가 약 $85 → 약 0.78 (⚠️ 2차 출처뿐). 아래쪽은 prior."
  promo_share_of_bookings:
    range: [0.5, 0.75]
    unit: 전체 예약 중 할인 경유 비율 (실패 기준점)
    note: "Homejoy '예약 75%가 할인 경유' (⚠️ 2차 출처뿐). 아래쪽은 prior."
  b_promo:
    range: [0.0, 1.5]
    unit: logit 감점
    note: "prior, not from cases. 할인 경유 고객의 재구매율 숫자는 사례에 없음."
predicts:
  - "첫 거래 할인이 더 깊은 계획은 30일 첫 거래 수가 더 많다."
  - "같은 계획은 90일 시점 '정가 2회차 거래 비율'이 더 낮다."
  - "take_rate 가 할인율보다 작으면 할인이 깊은 계획의 90일 contribution 이 더 낮다 (음수일 수 있음)."
evidence:
  - {case: Homejoy, fact: "시간당 $20, 클리너 보수 시간당 $12~15", date: "2012~2013", source_url: "https://techcrunch.com/2013/08/18/homejoy-behind-the-scenes/", strength: strong}
  - {case: Homejoy, fact: "첫 청소 $19 프로모(정가 약 $85), 예약 75%가 할인 경유 — 2차 출처뿐", date: "2018 (회고)", source_url: "https://d3.harvard.edu/platform-digit/submission/homejoys-not-so-joyous-demise/", strength: weak}
  - {case: Homejoy, fact: "누적 투자 $4,000만, 30개 시장인데 예약 건수·매출 공개 없음, 2015-07-31 종료", date: "2013-12-05 ~ 2015-07-31", source_url: "https://techcrunch.com/2015/07/17/homejoy-is-shutting-down-at-the-end-of-the-month/", strength: strong}
  - {case: Lyft, fact: "플랫폼 몫이 기부액의 20% (2014 자료)", date: "2014", source_url: "none (case file gives no URL for this fact)", strength: weak}
counter_evidence:
  - {case: Uber, fact: "무료 탑승·추천 크레딧은 마케팅 블로그뿐이라 확인 불가. 성공 사례에서 보조금 효과를 확인하거나 반박할 자료가 없음", date: "2010~2011", source_url: "https://techcrunch.com/2010/07/05/ubercab-takes-the-hassle-out-of-booking-a-car-service/", strength: weak}
  - {case: Homejoy, fact: "종료 원인이 할인 구조였다는 직접 근거는 사례 파일에 없음 (인용된 Forbes 기사는 열지 못함)", date: "2015-07-23", source_url: "https://d3.harvard.edu/platform-digit/submission/homejoys-not-so-joyous-demise/", strength: weak}
confidence: low
```

Homejoy는 가격의 60~75%를 청소하는 사람에게 줬기 때문에, 2차 출처 말대로 첫 청소를 80% 가까이 깎았다면 거래마다 손해였을 것이다. 엔진은 할인 경유 고객의 정가 재구매를 따로 세고 거래당 남는 몫을 합산해서, "많이 팔았는데 남은 게 없다"는 결과가 숫자로 드러나게 한다. 핵심 숫자가 2차 출처뿐이라 확신도는 낮다.

### 9. 화제성 설치는 반복 거래가 없으면 활성으로 남지 않는다 (설치와 활성의 분리) — 실패 설명

```yaml
id: novelty_installs_without_repeat_loop
mechanism: 언론·화제성이 만든 설치는 Bass의 p 펄스처럼 빠르게 쌓이지만, 핵심 행동이 양쪽 사이 반복 거래(다시 만나기, 다시 타기, 다시 주문하기)로 이어지지 않으면 이탈 위험이 높게 유지되어 누적 설치와 활성 사용자가 크게 벌어진다.
applies_when:
  - 핵심 행동이 한쪽의 일방적 행동(평가, 열람, 구경)이고 반대편과의 반복 성사가 약한 앱
  - 계획이 언론·바이럴·콘테스트로 첫 달 설치를 크게 만드는 데 의존한다
  - 결과 비교 지표를 정할 때 (항상: 누적 설치가 아니라 활성·반복 거래로 판정)
formula: |
  # 누적 설치 N 과 활성 A 를 분리한다
  dA/dt = installs(t) − Σ_i h_i(t) · active_i
  # 반복 가치 v_i = 최근 30일 반대편과의 성사 수
  h_i(t) = h_novelty · exp(−t_since_install/τ_nov) + h_floor · exp(−β · v_i)
  # 판정 지표: A(90), 반복 거래 사용자 수, 그리고 A(90)/N(90)
parameters:
  downloads_month1:
    range: [60000, 60000]
    unit: 다운로드 (하한, 실제 시장)
    note: "Lulu 첫 달 6만 이상 (회사 주장). 시뮬레이션 인구에 쓸 때는 비율로 바꿔 쓴다. 화제성 설치가 얼마나 빨리 쌓일 수 있는지의 기준점."
  active_to_cumulative_ratio:
    range: [0.05, 0.5]
    unit: 활성 / 누적 설치
    note: "prior, not from cases. Lulu는 다운로드·가입 600만이 '활성 아님'이라고만 하고 활성 수를 주지 않음. 넓게 둔다."
  tau_nov:
    range: [7, 45]
    unit: 일
    note: "prior, not from cases."
  beta:
    range: [0.2, 2.0]
    unit: 1 / 성사 1회
    note: "prior, not from cases. 성사를 겪을수록 이탈이 줄어드는 정도."
predicts:
  - "화제성으로 첫 달 설치를 키운 계획은 30일 누적 설치에서 앞서도, 반복 성사가 적으면 90일 활성에서는 뒤질 수 있다."
  - "같은 설치 수에서 사용자 1명당 반대편과의 반복 성사가 많은 계획이 90일 활성/누적 비율이 더 높다."
evidence:
  - {case: Lulu, fact: "첫 달 6만 다운로드 이상, 리뷰 14만 (회사 주장)", date: "2013-02-05", source_url: "https://techcrunch.com/?p=751260", strength: weak}
  - {case: Lulu, fact: "+7개월 사용자 100만, 리뷰 요청 남성 50만 (창업자 주장)", date: "2013-08-22", source_url: "https://www.thedailybeast.com/meet-lulu-an-app-that-lets-girls-rate-guys-anonymously/", strength: weak}
  - {case: Lulu, fact: "인수 시 다운로드·가입 600만('활성 아님'), 원래 앱 중단, 출시 때 수익 모델 없음", date: "2016-02-09", source_url: "https://techcrunch.com/?p=1274326", strength: strong}
  - {case: Tinder, fact: "성공 사례는 사용자 수보다 하루 매치(반복 성사) 숫자를 공개 — 매치 350만 → 1,000만", date: "2013-10-31 ~ 2014-02-28", source_url: "https://siliconrepublic.com/?p=319667", strength: weak}
counter_evidence:
  - {case: Lulu, fact: "남성 50만 명이 스스로 리뷰를 요청했다는 것은 평가받는 쪽도 일부 참여했다는 뜻. 반복 루프가 '없었다'고 단정할 근거는 사례 파일에 없음", date: "2013-08-22", source_url: "https://www.thedailybeast.com/meet-lulu-an-app-that-lets-girls-rate-guys-anonymously/", strength: weak}
confidence: low
```

Lulu는 첫 달 6만, 일곱 달 만에 100만 명을 모았지만, 3년 뒤에는 600만 다운로드가 "활성 아님"이라는 말과 함께 앱이 닫혔다. 엔진은 누적 설치와 활성 사용자를 따로 세고, 반대편과 다시 성사되는 사람만 이탈 위험이 줄어들게 만든다. 승패도 설치가 아니라 90일 활성과 반복 거래로 판정한다.

---

## 근거가 약하거나 뽑지 않은 것

- **획득 채널 자료가 거의 없다.** 8개 사례 어디에도 광고비, 고객 획득 비용(CAC), 채널별 설치 수가 없다. 그래서 광고 포화 훅 `reach = 1 − e^(−kF)`의 `k`는 사례에서 정할 수 없고, 전부 prior다. 두 계획이 광고 예산만 다를 때 엔진의 판정은 이 파일의 근거 밖이다.
- **잔존·이탈 곡선 숫자가 하나도 없다.** 생존 곡선과 이탈 위험 파라미터(`h_base`, `gamma`, `h_novelty`, `beta` 등)는 모두 prior다. 사례가 주는 건 "매일 확인 70%"(Coffee Meets Bagel) 한 점과 Lulu의 "활성 아님"이라는 말뿐이다.
- **추천 크레딧·무료 탑승 같은 추천 보상은 뽑지 않았다.** Uber는 마케팅 블로그뿐이고, Lyft는 확인하지 못했다고 적혀 있다.
- **규제 충격은 뽑지 않았다.** Uber의 2010-10 중지명령과 개명은 ⚠️이고, 그 뒤 성장에 준 영향이 사례에 없다.
- **가격 수준(고급 대 저가)의 방향은 정하지 않았다.** 프리미엄 블랙카(Uber)와 기부 가격(Lyft)이 둘 다 성공해서 방향을 고를 수 없다. 택시 대비 가격 배수도 출처마다 1.5~2배, 약 20%, 약 50%로 다르다.
- **브랜딩(핑크 콧수염 등)과 교차 게시(Craigslist, 시점 불명 ⚠️)는 뽑지 않았다.** 효과를 잴 숫자가 없다.
- **투자 유치는 원인으로 쓰지 않았다.** 대부분 사례에서 투자는 성장의 결과로 함께 보도되고, 실패한 Homejoy도 $4,000만을 받았다.
- **초대제·한정 공개(Lulu 초대제, 미국 스토어 한정)의 효과는 따로 뽑지 않았다.** 이 방식을 쓴 사례가 실패한 Lulu 하나라 방향을 정할 수 없다.
- **표본 편향.** 성공 6개, 애매 1개, 실패 2개이고, 숫자 대부분이 회사·CEO 발언이다. 성장률 띠(`wom_growth_rate_band`)는 상한 쪽으로 치우쳤을 가능성이 크다. 실패 쪽 규칙(8, 9번)은 각각 사례 하나에 기대고 있어, 실패 원인을 이 파일이 맞게 짚었는지는 사례만으로 확인할 수 없다.
- **날짜 충돌.** Tinder 출시(2012-08 대 2012-09), Lyft 출시(2012-05 대 2012-06), DoorDash(2013-02 대 2013-01), Homejoy 출시 월이 출처마다 다르다. 개월 수로 만든 범위(`months_to_second_city_success` 등)는 ±1개월 오차를 품고 있다.
- **지표 정의가 섞였다.** "매치", "직접 연결", "탑승", "주문", "사용자"가 사례마다 다르고 Coffee Meets Bagel 안에서도 "직접 연결 6,000"과 "매치 150만"의 정의가 다를 수 있다. 노출당 성사율(`q_e_*`)은 정의 차이만큼 불확실하다.
- **12~18개월 구간의 숫자가 빈 사례가 있다.** Lulu(+7 이후 +37까지 없음), Homejoy(예약·매출 공개 없음), Airbnb(+6 이후 +27까지 없음). 이 구간 백테스트에서 이 세 사례에 기댄 규칙은 검증력이 약하다.
