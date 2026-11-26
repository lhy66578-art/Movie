import streamlit as st
import requests
import pandas as pd
import re
from bs4 import BeautifulSoup


# 1. 기본 화면 설정
st.set_page_config(
    page_title="대한민국 영화 흥행 분석",
    layout="wide"
)

st.title("대한민국 영화 흥행 기록 분석")
st.write("위키백과에서 영화 흥행 데이터를 수집하고 분석합니다.")


# 2. 웹페이지 가져오기
def get_html(url):
    headers = {
        "User-Agent": "Python Class Practice Bot (Educational Use)"
    }

    response = requests.get(
        url,
        headers=headers,
        timeout=10
    )

    # HTTP 오류 확인
    response.raise_for_status()

    return response.text


# 3. 조건에 맞는 표 찾기
def find_movie_table(html):
    soup = BeautifulSoup(html, "html.parser")

    # wikitable 클래스를 가진 표만 검색
    tables = soup.find_all("table", class_="wikitable")

    for table in tables:
        first_row = table.find("tr")

        if first_row is None:
            continue

        # 첫 번째 행의 제목 칸(th) 확인
        headers = first_row.find_all("th", recursive=False)

        header_names = [
            re.sub(r"\s+", "", th.get_text(strip=True))
            for th in headers
        ]

        # 관객수와 감독이 모두 있는 첫 번째 표 선택
        if "관객수" in header_names and "감독" in header_names:
            return table

    return None


# 4. 표에서 데이터 추출하기
def extract_data(table):
    data = []

    # 첫 번째 행에서 열 이름 가져오기
    first_row = table.find("tr")
    headers = [
        re.sub(r"\s+", " ", th.get_text(strip=True))
        for th in first_row.find_all("th", recursive=False)
    ]

    # 나머지 행에서 영화 정보 가져오기
    rows = table.find_all("tr")[1:]

    for row in rows:
        cells = row.find_all("td", recursive=False)

        # 열 개수가 맞지 않는 행은 건너뛰기
        if len(cells) != len(headers):
            continue

        row_data = []

        for cell in cells:
            # 각주 번호 제거
            for sup in cell.find_all("sup"):
                sup.decompose()

            # 셀 안의 텍스트 추출
            value = cell.get_text(" ", strip=True)
            row_data.append(value)

        data.append(row_data)

    # DataFrame 생성
    return pd.DataFrame(data, columns=headers)


# 5. 데이터 정제하기
def clean_data(df):
    # 위키백과 표의 제목 열 이름을 확인
    title_column = "제목" if "제목" in df.columns else None

    # 제목에서 《》 제거
    if title_column:
        df["제목"] = (
            df["제목"]
            .astype(str)
            .str.replace("《", "", regex=False)
            .str.replace("》", "", regex=False)
        )

    # 관객수를 숫자로 변환
    if "관객수" in df.columns:
        df["관객수"] = (
            df["관객수"]
            .astype(str)
            .str.replace(",", "", regex=False)
            .str.replace(r"[^0-9]", "", regex=True)
        )
        df["관객수"] = pd.to_numeric(df["관객수"], errors="coerce")

    # 개봉일에서 연도와 월 추출
    if "개봉일" in df.columns:
        date_text = df["개봉일"].astype(str)

        df["개봉연도"] = pd.to_numeric(
            date_text.str.extract(r"(\d{4})")[0],
            errors="coerce"
        )

        df["개봉월"] = pd.to_numeric(
            date_text.str.extract(r"\d{4}[-./년]\s*(\d{1,2})")[0],
            errors="coerce"
        )

    # 관객수 값이 없는 행 제거
    df = df.dropna(subset=["관객수"])

    # 관객수 기준 내림차순 정렬
    df = df.sort_values(
        by="관객수",
        ascending=False
    ).reset_index(drop=True)

    return df


# 6. 주요 통계 계산하기
def calculate_statistics(df):
    # 천만 관객 이상 영화 수 계산
    ten_million_count = len(df[df["관객수"] >= 10_000_000])

    # 관객수가 가장 많은 영화 찾기
    first_movie = df.loc[df["관객수"].idxmax()]
    first_title = first_movie["제목"] if "제목" in df.columns else "제목 열 없음"
    first_audience = int(first_movie["관객수"])

    return ten_million_count, first_title, first_audience


# 7. 분석 결과 화면에 표시하기
def show_analysis(df):
    ten_million_count, first_title, first_audience = calculate_statistics(df)

    st.subheader("주요 흥행 지표")

    col1, col2, col3 = st.columns(3)
    col1.metric("천만 관객 영화 수", f"{ten_million_count}편")
    col2.metric("역대 관객수 1위", first_title)
    col3.metric("1위 관객수", f"{first_audience:,}명")

    st.divider()

    # 전체 데이터 표 표시
    st.subheader("영화 흥행 기록 표")
    st.dataframe(df, use_container_width=True)

    st.divider()

    # 관객수 상위 10편 가로 막대 차트
    st.subheader("관객수 상위 10편")
    if "제목" in df.columns:
        top10 = df.head(10).set_index("제목")[["관객수"]]
        st.bar_chart(top10, horizontal=True)
    else:
        st.warning("제목 열이 없어 상위 10편 차트를 표시할 수 없습니다.")

    st.divider()

    # 개봉연도별 영화 편수 막대 차트
    st.subheader("개봉연도별 영화 편수")
    if "개봉연도" in df.columns:
        year_count = (
            df.dropna(subset=["개봉연도"])
            .groupby("개봉연도")
            .size()
            .reset_index(name="영화 편수")
        )
        year_count["개봉연도"] = year_count["개봉연도"].astype(int).astype(str)
        year_count = year_count.set_index("개봉연도")
        st.bar_chart(year_count)
    else:
        st.warning("개봉일 열이 없어 연도별 차트를 표시할 수 없습니다.")


# 8. 사용자 입력 및 실행
default_url = "https://ko.wikipedia.org/wiki/대한민국의_영화_흥행_기록"

url = st.text_input(
    "위키백과 주소를 입력하세요.",
    value=default_url
)

if st.button("데이터 수집 및 분석"):
    try:
        with st.spinner("영화 데이터를 수집하고 있습니다..."):
            # 웹페이지 요청
            html = get_html(url)

            # 조건에 맞는 표 검색
            table = find_movie_table(html)

            if table is None:
                st.error("조건에 맞는 영화 표를 찾을 수 없습니다.")
            else:
                # 표에서 데이터 추출 및 정제
                df = extract_data(table)
                df = clean_data(df)

                if df.empty:
                    st.error("분석할 영화 데이터가 없습니다.")
                else:
                    st.success("데이터 수집 및 분석 완료!")
                    show_analysis(df)

    except requests.exceptions.ConnectionError:
        st.error("인터넷 연결에 실패했습니다.")

    except requests.exceptions.Timeout:
        st.error("서버 응답 시간이 초과되었습니다.")

    except requests.exceptions.HTTPError as e:
        st.error(f"HTTP 오류가 발생했습니다: {e}")

    except requests.exceptions.RequestException as e:
        st.error(f"웹페이지 요청 오류: {e}")

    except Exception as e:
        st.error(f"프로그램 실행 중 오류가 발생했습니다: {e}")
