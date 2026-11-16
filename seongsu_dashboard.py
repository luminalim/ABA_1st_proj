"""성수동 커피 상권 통합 대시보드
데이터: 성수_카페_통합패널.csv (서울시 상권분석서비스 2021~2025, 성수 4개 행정동 합계)
실행: streamlit run seongsu_dashboard.py  (스크립트와 같은 폴더에 CSV를 둘 것)
"""
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="성수동 커피 상권 대시보드", page_icon="☕", layout="wide")
DATA = Path(__file__).parent / "성수_카페_통합패널.csv"
FC_YEARS = list(range(2026, 2032))


@st.cache_data
def load_panel(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, encoding="utf-8-sig")


def annual_table(p: pd.DataFrame) -> pd.DataFrame:
    """연간 집계: 평균 점포 수, 개폐업, 매출, 점포당 연매출"""
    s = p.dropna(subset=["점포수"]).groupby("연도").agg(
        평균점포수=("점포수", "mean"), 개업=("개업", "sum"), 폐업=("폐업", "sum"),
        매출_억원=("매출_억원", "sum"))
    s["순증"] = s["개업"] - s["폐업"]
    s["점포당_연매출_만원"] = s["매출_억원"] * 10000 / s["평균점포수"]
    return s


def scenario(base_stores: float, base_ps: float, store_g: float, ps_g: float) -> pd.DataFrame:
    """연간 점포 수 × 점포당 연매출 = 매출(억 원), 2025년 기준에서 6년 전망"""
    rows, st_n, ps = [], base_stores, base_ps
    for y in FC_YEARS:
        st_n *= 1 + store_g
        ps *= 1 + ps_g
        rows.append({"연도": y, "점포수": st_n, "점포당_만원": ps, "매출_억원": st_n * ps / 10000})
    return pd.DataFrame(rows)


panel = load_panel(DATA) if DATA.exists() else None
st.title("☕ 성수동 커피 상권 대시보드 (2021~2031)")
st.caption("서울시 상권분석서비스 2021~2025 · 4개 행정동 합계 · 매출은 카드 결제 기준 추정치")

if panel is None:
    st.error(f"'{DATA.name}' 파일을 찾을 수 없습니다. 스크립트와 같은 폴더에 두세요.")
    st.stop()

ann = annual_table(panel)
last = ann.iloc[-1]
prev = ann.iloc[-2]
c1, c2, c3, c4 = st.columns(4)
c1.metric("2025 연 매출", f"{last['매출_억원']:.0f} 억 원", f"{(last['매출_억원']/prev['매출_억원']-1)*100:+.1f}%")
c2.metric("2025 평균 점포 수", f"{last['평균점포수']:.0f} 곳", f"{(last['평균점포수']/ann.iloc[0]['평균점포수']-1)*100:+.0f}% (2021 대비)")
c3.metric("2025 점포당 연매출", f"{last['점포당_연매출_만원']/10000:.2f} 억 원", f"{(last['점포당_연매출_만원']/prev['점포당_연매출_만원']-1)*100:+.1f}%")
c4.metric("2025 순증 점포", f"{int(last['순증'])} 곳", f"개업 {int(last['개업'])} · 폐업 {int(last['폐업'])}")

tab1, tab2, tab3, tab4 = st.tabs(["📈 분기 현황", "🏪 개폐업", "🔮 시나리오 시뮬레이터", "📝 기준과 한계"])

with tab1:
    q = panel.dropna(subset=["점포수"])
    fig = go.Figure()
    fig.add_bar(x=q["분기"], y=q["매출_억원"], name="분기 매출(억 원)", marker_color="#4C72B0")
    fig.add_scatter(x=q["분기"], y=q["점포수"], name="점포 수", yaxis="y2", mode="lines+markers",
                    line_color="#DD8452")
    fig.update_layout(yaxis=dict(title="억 원"), yaxis2=dict(title="점포 수", overlaying="y", side="right"),
                      legend=dict(orientation="h", y=-0.2), height=420)
    st.plotly_chart(fig, use_container_width=True)
    left, right = st.columns(2)
    right.plotly_chart(go.Figure(go.Scatter(x=q["분기"], y=q["점포당_매출_만원"], mode="lines+markers",
                                            line_color="#DD8452")).update_layout(
        title="점포당 분기 매출 (만 원)", height=320), use_container_width=True)
    left.plotly_chart(go.Figure(go.Scatter(x=panel["분기"], y=panel["유동인구_4개동"], mode="lines",
                                           line_color="#4C72B0")).update_layout(
        title="유동인구 (4개 동 합계, 2021~2026 Q1)", height=320), use_container_width=True)

with tab2:
    fig = go.Figure()
    fig.add_bar(x=ann.index.astype(str), y=ann["개업"], name="개업", marker_color="#4C72B0")
    fig.add_bar(x=ann.index.astype(str), y=ann["폐업"], name="폐업", marker_color="#DD8452")
    fig.update_layout(barmode="group", height=380, legend=dict(orientation="h", y=-0.2))
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(ann.round(1).rename(columns={"매출_억원": "매출(억 원)"}), use_container_width=True)

with tab3:
    st.markdown("2025년 평균 점포 수와 점포당 연매출을 출발점으로, 증감률을 바꿔 가며 2031년까지 매출을 봅니다.")
    base_ps = float(last["점포당_연매출_만원"])
    default_ps_g = float(last["점포당_연매출_만원"] / prev["점포당_연매출_만원"] - 1) * 100
    a, b = st.columns(2)
    store_g = a.slider("연간 점포 수 증감률 (%)", -5.0, 5.0, 0.0, 0.5) / 100
    ps_g = b.slider("연간 점포당 매출 증가율 (%)", -5.0, 8.0, round(default_ps_g, 1), 0.1) / 100
    sc = scenario(float(last["평균점포수"]), base_ps, store_g, ps_g)
    base = scenario(float(last["평균점포수"]), base_ps, 0.0, default_ps_g / 100)
    down = scenario(float(last["평균점포수"]), base_ps, -0.01, 0.0)
    fig = go.Figure()
    fig.add_scatter(x=base["연도"], y=base["매출_억원"], name="기준 (점포 유지, 점포당 +3.4%)", mode="lines+markers")
    fig.add_scatter(x=down["연도"], y=down["매출_억원"], name="하방 (점포 -1%/년, 점포당 유지)", mode="lines+markers",
                    line=dict(dash="dash"))
    fig.add_scatter(x=sc["연도"], y=sc["매출_억원"], name="사용자 설정", mode="lines+markers",
                    line=dict(color="#DD8452", width=3))
    fig.update_layout(height=420, yaxis_title="매출 (억 원)", legend=dict(orientation="h", y=-0.2))
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(sc.round(1), use_container_width=True, hide_index=True)

with tab4:
    st.markdown("""
- **기준 시점**: 점포·매출 2025년 4분기까지, 유동인구 2026년 1분기까지. 2026년 2분기 이후 점포 자료는 반영되지 않았습니다.
- **매출**: 카드 결제 기준 추정치이며, 현금 거래와 실제 회계 매출은 포함되지 않습니다.
- **점포 수 기준**: 상권분석 점포 수(커피-음료 업종, 분기 말)입니다. 인허가 데이터 기반 영업중 카페 수(성수동 227곳)와 정의가 다릅니다.
- **모델 검증**: 2025년 백테스트에서 추세 모델과 구조 모델은 모두 연 오차 +2.1%로 같은 결과였고, 단순 기준선은 -2.0%였습니다.
- **시나리오**: 구조 가정(점포 수 × 점포당 매출)이며 적합된 모델이 아닙니다. 통계적 신뢰구간이 아니므로 범위로 해석합니다.
- **제외 항목**: 임대료 변화, 인구·소비 변화, 대형 행사 효과.
""")
