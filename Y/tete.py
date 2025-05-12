import streamlit as st
import pandas as pd
import numpy as np
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import plotly.express as px

# 페이지 설정
st.set_page_config(page_title="스팀게임분석 서비스", layout="wide")

# 더미 데이터
tags = ["Indie", "MOBA"]

titles = {
    "Indie": [
        {"title": "엘든 링", "app_id": 1245620, "link": "https://store.steampowered.com/app/1245620", "rating": 9.2, "tags": ["오픈월드", "Indie"], "positive_keywords": ["몰입감", "그래픽", "스토리"], "negative_keywords": ["난이도 높음", "버그"], "reviews": ["몰입감이 정말 대단해요!", "난이도가 너무 높아서 힘들어요."], "category": "트렌딩"},
        {"title": "시티즈: 스카이라인", "app_id": 255710, "link": "https://store.steampowered.com/app/255710", "rating": 8.5, "tags": ["도시 건설", "Indie"], "positive_keywords": ["자유도", "디테일", "창의적"], "negative_keywords": ["최적화", "복잡함"], "reviews": ["자유도가 높아서 좋아요!", "최적화가 좀 아쉽네요."], "category": "핫"},
        {"title": "더 심즈 4", "app_id": 1222670, "link": "https://store.steampowered.com/app/1222670", "rating": 8.0, "tags": ["생활 시뮬", "Indie"], "positive_keywords": ["창의적", "다양성"], "negative_keywords": ["DLC 많음", "버그"], "reviews": ["창의적인 플레이가 가능해요!", "DLC가 너무 많아요."], "category": "트렌딩"},
        {"title": "레드 데드 리뎀션 2", "app_id": 1174180, "link": "https://store.steampowered.com/app/1174180", "rating": 9.3, "tags": ["오픈월드", "Indie"], "positive_keywords": ["스토리", "그래픽", "몰입감"], "negative_keywords": ["최적화", "긴 플레이타임"], "reviews": ["스토리가 정말 감동적이에요!", "최적화가 아쉽네요."], "category": "핫"}
    ],
    "MOBA": [
        {"title": "위쳐 3", "app_id": 292030, "link": "https://store.steampowered.com/app/292030", "rating": 9.5, "tags": ["스토리", "MOBA"], "positive_keywords": ["스토리", "퀘스트", "연출"], "negative_keywords": ["버그", "최적화"], "reviews": ["스토리가 정말 감동적이에요!", "가끔 버그가 있어요."], "category": "핫"},
        {"title": "카운터 스트라이크 2", "app_id": 730, "link": "https://store.steampowered.com/app/730", "rating": 8.8, "tags": ["슈팅", "MOBA"], "positive_keywords": ["빠른 템포", "경쟁적", "밸런스"], "negative_keywords": ["치터", "서버 문제"], "reviews": ["빠른 템포가 재미있어요!", "치터가 너무 많아요."], "category": "트렌딩"},
        {"title": "발로란트", "app_id": 123456, "link": "https://playvalorant.com", "rating": 8.5, "tags": ["슈팅", "MOBA"], "positive_keywords": ["전략적", "그래픽"], "negative_keywords": ["매칭 문제", "밸런스"], "reviews": ["전략적인 플레이가 재미있어요!", "매칭이 너무 오래 걸려요."], "category": "핫"},
        {"title": "문명 VI", "app_id": 289070, "link": "https://store.steampowered.com/app/289070", "rating": 9.0, "tags": ["턴제", "MOBA"], "positive_keywords": ["전략적", "몰입감", "다양성"], "negative_keywords": ["긴 플레이타임", "복잡함"], "reviews": ["전략적으로 깊이 있는 게임이에요!", "플레이타임이 너무 길어요."], "category": "핫"},
        {"title": "스타크래프트 II", "app_id": 123457, "link": "https://starcraft2.com", "rating": 8.7, "tags": ["RTS", "MOBA"], "positive_keywords": ["경쟁적", "밸런스"], "negative_keywords": ["난이도 높음", "초보 어려움"], "reviews": ["경쟁적인 재미가 최고예요!", "초보자가 하기에 너무 어려워요."], "category": "트렌딩"},
        {"title": "젤다의 전설: 야생의 숨결", "app_id": 123458, "link": "https://www.nintendo.com", "rating": 9.7, "tags": ["오픈월드", "MOBA"], "positive_keywords": ["탐험", "자유도", "그래픽"], "negative_keywords": ["난이도 높음"], "reviews": ["탐험의 재미가 최고예요!", "난이도가 좀 높아요."], "category": "트렌딩"}
    ]
}

# 용어 정리 더미 데이터
glossary = {
    "태그": "게임에 붙어있는 태그로, 개발사가 지정한 태그가 아닌 유저가 지정한 태그입니다. 유저들이 전반적으로 해당 게임에 대해 어떻게 인지하고 있는지를 나타냅니다. 장르적 태그(예: Indie, MOBA), 그래픽에 관한 태그(예: 그래픽), 게임 피처에 관한 태그(예: 오픈월드, 전략적) 등이 있으며, 분류 예정입니다.",
    "리뷰 키워드": "유저가 남긴 리뷰에서 추출한 키워드로, 특정 게임에 대해 유저들이 장단점으로 인지하는 부분을 나타냅니다.",
    "태그 분포": "특정 태그를 가진 타이틀들이 그 외에 어떤 태그를 가지고 있는지를 보여줍니다. 예를 들어, 'Indie + MOBA' 태그를 가진 타이틀 내에서 태그들이 어떻게 분포되어 있는지 확인할 수 있습니다. 태그를 점점 좁혀가며 원하는 영역을 살펴보는 용도로 사용됩니다.",
    "태그 내 리뷰 키워드 분포": "정해진 태그들을 모두 가지고 있는 타이틀들에 대한 리뷰 키워드의 분포를 나타냅니다. 예를 들어, '전투 시스템'이 높은 값을 가지면 해당 태그 조합에서 유저들이 전투 시스템에 만족하고 있음을 의미합니다.",
    "리뷰 키워드 내 타이틀 분포": "특정 리뷰 키워드를 가진 타이틀들을 모두 보여줍니다. 단, 해당 리뷰 키워드에 대한 점수가 높은 순서대로 정렬됩니다. 태그로 추가 필터링이 가능합니다.",
    "타이틀 상세": "특정 타이틀에 대한 상세 정보를 보여줍니다. 포함되는 정보는 다음과 같습니다:\n1. 타이틀 및 태그\n2. 타이틀 리뷰 키워드 점수 및 분포\n3. 유사 타이틀"
}

# 워드 클라우드 색상 함수
def color_func(word, font_size, position, orientation, random_state=None, **kwargs):
    if word in positive_keywords_set:
        return "green"
    elif word in negative_keywords_set:
        return "red"
    return "black"

# 사이드바 메뉴 선택
st.sidebar.subheader("전체 메뉴")
if "show_menu" not in st.session_state:
    st.session_state["show_menu"] = False

if "selected_menu" not in st.session_state:
    st.session_state["selected_menu"] = "홈 대시보드"
selected_menu = st.session_state["selected_menu"]

toggle_label = "메뉴 닫기" if st.session_state["show_menu"] else "메뉴 열기"
if st.sidebar.button(toggle_label, key="menu_toggle"):
    st.session_state["show_menu"] = not st.session_state["show_menu"]
    st.rerun()

if st.session_state["show_menu"]:
    menu_options = ["홈 대시보드", "태그나 유저 리뷰 키워드 키워드", "유저 리뷰 키워드 내 타이틀 분포", "타이틀 상세"]
    for option in menu_options:
        if st.sidebar.button(option, key=option):
            st.session_state["selected_menu"] = option
            if option == "태그나 유저 리뷰 키워드 키워드":
                st.session_state["selected_tag"] = None
            st.rerun()

st.sidebar.subheader("용어 설명")
if st.sidebar.button("용어 정리", key="glossary"):
    st.session_state["selected_menu"] = "용어 정리 (팝업)"
    selected_menu = "용어 정리 (팝업)"

# 장르 선택
st.subheader("장르 선택")
col1, col2, col3, col4 = st.columns(4)
with col1:
    tag1 = st.selectbox("태그 드롭다운 1", tags, index=tags.index("Indie"), key="tag1")
with col2:
    tag2 = st.selectbox("태그 드롭다운 2", ["없음"] + tags, index=tags.index("MOBA") + 1, key="tag2")
with col3:
    tag3 = st.selectbox("태그 드롭다운 3", ["없음"] + tags, index=0, key="tag3")
with col4:
    tag4 = st.selectbox("태그 드롭다운 4", ["없음"] + tags, index=0, key="tag4")

# 다중 태그 필터링 로직
selected_tags = [tag1]
if tag2 != "없음":
    selected_tags.append(tag2)
if tag3 != "없음":
    selected_tags.append(tag3)
if tag4 != "없음":
    selected_tags.append(tag4)

# 두 개 이상의 태그가 선택되었는지 확인
if len(selected_tags) < 2:
    st.warning("두 개 이상의 태그를 선택해야 대시보드가 표시됩니다.")
else:
    # 선택된 태그에 따라 필터링된 타이틀 리스트
    filtered_titles = []
    for tag in selected_tags:
        if tag in titles:
            filtered_titles.extend(titles[tag])

    # 메인 제목
    st.markdown("<h1 style='text-align: center;'>스팀게임분석 서비스</h1>", unsafe_allow_html=True)

    # 메뉴에 따라 다른 프레임 렌더링
    if selected_menu == "홈 대시보드":
        if filtered_titles:
            

            col5, col6, col7 = st.columns([1, 1, 1])

            with col5:
                st.subheader("인기 게임의 태그 분포")
                all_tags = []
                for title in filtered_titles:
                    all_tags.extend(title["tags"])
                tag_counts = pd.Series(all_tags).value_counts()
                if not tag_counts.empty:
                    tag_cloud = WordCloud(width=400, height=200, background_color="white").generate_from_frequencies(tag_counts)
                    plt.figure(figsize=(5, 3))
                    plt.imshow(tag_cloud, interpolation="bilinear")
                    plt.axis("off")
                    st.pyplot(plt)
                else:
                    st.write("태그 데이터가 없습니다.")

            with col6:
                st.subheader("Trending Game")
                trending_titles = [title for title in filtered_titles if title["category"] == "트렌딩"]
                df_trending = pd.DataFrame(trending_titles)

                search_term = st.text_input("제목 또는 App ID로 검색 (트렌딩)", "")
                if search_term:
                    df_trending = df_trending[
                        df_trending["title"].str.contains(search_term, case=False, na=False) |
                        df_trending["app_id"].astype(str).str.contains(search_term, na=False)
                    ]

                selected_trending = st.dataframe(
                    df_trending[["title", "app_id", "link", "rating", "tags", "positive_keywords", "negative_keywords"]],
                    column_config={
                        "title": "타이틀",
                        "app_id": "App ID",
                        "link": st.column_config.LinkColumn("링크"),
                        "rating": "점수",
                        "tags": "태그",
                        "positive_keywords": "긍정 키워드",
                        "negative_keywords": "부정 키워드"
                    },
                    height=200,
                    use_container_width=True,
                    selection_mode="single-row",
                    on_select="rerun"
                )

                if st.button("상세정보 (Trending)", key="trending_detail"):
                    selected_rows = selected_trending.selection["rows"]
                    if selected_rows:
                        selected_title = df_trending.iloc[selected_rows[0]]
                        st.session_state["selected_title"] = selected_title
                        st.session_state["selected_menu"] = "타이틀 상세"
                        st.rerun()
                    else:
                        st.warning("타이틀을 선택해 주세요.")

            with col7:
                st.subheader("Hot Game")
                hot_titles = [title for title in filtered_titles if title["category"] == "핫"]
                df_hot = pd.DataFrame(hot_titles)

                search_term_hot = st.text_input("제목 또는 App ID로 검색 (핫)", "")
                if search_term_hot:
                    df_hot = df_hot[
                        df_hot["title"].str.contains(search_term_hot, case=False, na=False) |
                        df_hot["app_id"].astype(str).str.contains(search_term_hot, na=False)
                    ]

                selected_hot = st.dataframe(
                    df_hot[["title", "app_id", "link", "rating", "tags", "positive_keywords", "negative_keywords"]],
                    column_config={
                        "title": "타이틀",
                        "app_id": "App ID",
                        "link": st.column_config.LinkColumn("링크"),
                        "rating": "점수",
                        "tags": "태그",
                        "positive_keywords": "긍정 키워드",
                        "negative_keywords": "부정 키워드"
                    },
                    height=200,
                    use_container_width=True,
                    selection_mode="single-row",
                    on_select="rerun"
                )

                if st.button("상세정보 (Hot)", key="hot_detail"):
                    selected_rows = selected_hot.selection["rows"]
                    if selected_rows:
                        selected_title = df_hot.iloc[selected_rows[0]]
                        st.session_state["selected_title"] = selected_title
                        st.session_state["selected_menu"] = "타이틀 상세"
                        st.rerun()
                    else:
                        st.warning("타이틀을 선택해 주세요.")

            st.markdown("---")
            col8, col9 = st.columns([1, 1])

            with col8:
                st.subheader("차트 제목: 태그 분류에 따른 각 영역별 바 차트")
                chart_data = pd.DataFrame({
                    "태그": tags,
                    "작품 수": [len(titles.get(tag, [])) for tag in tags]
                })
                st.bar_chart(chart_data.set_index("태그"))

            with col9:
                st.subheader("선택한 장르에 대한 타이틀 리스트 및 유저 리뷰 키워드 분포")
                tag_titles = filtered_titles
                
                if tag_titles:
                    df_tag_titles = pd.DataFrame(tag_titles)
                    st.write("**선택한 장르의 타이틀 리스트**:")
                    selected_tag_title = st.dataframe(
                        df_tag_titles[["title", "app_id", "rating", "tags"]],
                        column_config={
                            "title": "타이틀",
                            "app_id": "App ID",
                            "rating": "점수",
                            "tags": "태그"
                        },
                        height=200,
                        use_container_width=True,
                        selection_mode="single-row",
                        on_select="rerun"
                    )
                    
                    if st.button("선택한 장르 내 유저 리뷰 키워드 분포 바로 가기", key="keyword_dist_all"):
                        st.session_state["selected_tag"] = None
                        st.session_state["selected_menu"] = "태그나 유저 리뷰 키워드 키워드"
                        st.rerun()
                else:
                    st.write("선택한 장르에 해당하는 타이틀이 없습니다.")

    elif selected_menu == "태그나 유저 리뷰 키워드 키워드":
        plt.rcParams['font.family'] = 'Malgun Gothic'
        plt.rcParams['axes.unicode_minus'] = False

        selected_tag = st.session_state.get("selected_tag", None)
        if selected_tag:
            st.subheader(f"태그: {selected_tag} - 리뷰 키워드 분석")
            tag_titles = [title for title in filtered_titles if selected_tag in title["tags"]]
        else:
            st.subheader("전체 리뷰 키워드 분석")
            tag_titles = filtered_titles

        if not tag_titles:
            st.warning(f"선택된 태그 '{selected_tag}'에 해당하는 타이틀이 없습니다.")
        else:
            all_positive_keywords = []
            all_negative_keywords = []
            for title in tag_titles:
                all_positive_keywords.extend(title["positive_keywords"])
                all_negative_keywords.extend(title["negative_keywords"])

            if not all_positive_keywords and not all_negative_keywords:
                st.warning(f"선택된 태그 '{selected_tag}'에 해당하는 리뷰 키워드가 없습니다.")
            else:
                global positive_keywords_set, negative_keywords_set
                positive_keywords_set = set(all_positive_keywords)
                negative_keywords_set = set(all_negative_keywords)

                all_keywords = all_positive_keywords + all_negative_keywords
                keyword_counts = pd.Series(all_keywords).value_counts()

                keyword_df = pd.DataFrame({
                    "키워드": keyword_counts.index,
                    "빈도": keyword_counts.values,
                    "유형": ["긍정" if kw in positive_keywords_set and kw not in negative_keywords_set else "부정" for kw in keyword_counts.index]
                })

                st.write("### 키워드 필터링")
                filter_option = st.multiselect(
                    "유형 선택",
                    options=["긍정", "부정"],
                    default=["긍정", "부정"]
                )

                filtered_df = keyword_df[keyword_df["유형"].isin(filter_option)]

                col10, col11 = st.columns(2)

                with col10:
                    st.markdown("### 리뷰 전체에 대한 워드 클라우드")
                    if not filtered_df.empty:
                        filtered_counts = filtered_df.set_index("키워드")["빈도"].to_dict()
                        wordcloud = WordCloud(
                            width=500,
                            height=300,
                            background_color="white",
                            color_func=color_func,
                            font_path="C:/Windows/Fonts/malgun.ttf"
                        ).generate_from_frequencies(filtered_counts)
                        plt.figure(figsize=(6, 4))
                        plt.imshow(wordcloud, interpolation="bilinear")
                        plt.axis("off")
                        st.pyplot(plt)
                    else:
                        st.write("워드 클라우드를 생성할 키워드가 없습니다.")

                with col11:
                    st.markdown("### 키워드 데이터 표")
                    if not filtered_df.empty:
                        st.dataframe(
                            filtered_df.style.format({"빈도": "{:.0f}"}),
                            height=300,
                            use_container_width=True
                        )
                    else:
                        st.write("표시할 키워드 데이터가 없습니다.")

                st.markdown("### 키워드 버블 차트")
                if not filtered_df.empty:
                    fig = px.scatter(
                        filtered_df,
                        x="키워드",
                        y="유형",
                        size="빈도",
                        color="유형",
                        color_discrete_map={"긍정": "green", "부정": "red"},
                        hover_data=["빈도"],
                        size_max=60,
                        title="키워드 빈도 분석"
                    )
                    fig.update_layout(
                        xaxis_title="키워드",
                        yaxis_title="유형",
                        height=400,
                        width=1000
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.write("표시할 키워드 데이터가 없습니다.")

                col_left, col_right = st.columns([3, 1])
                with col_right:
                    if st.button("각 리뷰 타이틀 분포 보기", key="to_title_distribution"):
                        st.session_state["selected_menu"] = "유저 리뷰 키워드 내 타이틀 분포"
                        st.rerun()

    elif selected_menu == "유저 리뷰 키워드 내 타이틀 분포":
        st.subheader("리뷰 키워드 내 타이틀 분포")

        # 전체 키워드 목록 생성
        all_positive_keywords = []
        all_negative_keywords = []
        for title in filtered_titles:
            all_positive_keywords.extend(title["positive_keywords"])
            all_negative_keywords.extend(title["negative_keywords"])
        unique_keywords = list(set(all_positive_keywords + all_negative_keywords))

        # 긍정/부정 키워드 분리
        positive_keywords_set = set(all_positive_keywords)
        negative_keywords_set = set(all_negative_keywords)

        # 카테고리 선택
        st.write("### 키워드 유형 선택")
        type_category = st.multiselect(
            "유형 카테고리",
            options=["전체", "긍정", "부정"],
            default=["전체"]
        )

        st.write("### 키워드 선택")
        selected_keywords = st.multiselect(
            "리뷰 키워드 선택",
            options=unique_keywords,
            default=[]
        )

        keyword_titles = []
        if "전체" in type_category and not selected_keywords:
            # [전체]만 선택되고 키워드 선택이 없으면 전체 데이터
            keyword_titles = [
                {
                    "title": title["title"],
                    "app_id": title["app_id"],
                    "link": title["link"],
                    "rating": title["rating"],
                    "tags": title["tags"],
                    "positive_keywords": title["positive_keywords"],
                    "negative_keywords": title["negative_keywords"],
                    "keyword_score": len(title["positive_keywords"]) + len(title["negative_keywords"])
                } for title in filtered_titles
            ]
        else:
            # 유형 필터링
            for title in filtered_titles:
                relevant_keywords = []
                if "전체" in type_category or ("긍정" in type_category and "부정" in type_category):
                    relevant_keywords = title["positive_keywords"] + title["negative_keywords"]
                elif "긍정" in type_category:
                    relevant_keywords = title["positive_keywords"]
                elif "부정" in type_category:
                    relevant_keywords = title["negative_keywords"]

                # 선택된 키워드가 모두 포함되어 있는지 확인
                if selected_keywords:
                    if all(kw in relevant_keywords for kw in selected_keywords):
                        keyword_count = sum(relevant_keywords.count(kw) for kw in selected_keywords)
                        keyword_titles.append({
                            "title": title["title"],
                            "app_id": title["app_id"],
                            "link": title["link"],
                            "rating": title["rating"],
                            "tags": title["tags"],
                            "positive_keywords": title["positive_keywords"],
                            "negative_keywords": title["negative_keywords"],
                            "keyword_score": keyword_count
                        })
                else:
                    # 키워드 선택이 없으면 유형만 적용
                    keyword_count = len(relevant_keywords)
                    if keyword_count > 0:
                        keyword_titles.append({
                            "title": title["title"],
                            "app_id": title["app_id"],
                            "link": title["link"],
                            "rating": title["rating"],
                            "tags": title["tags"],
                            "positive_keywords": title["positive_keywords"],
                            "negative_keywords": title["negative_keywords"],
                            "keyword_score": keyword_count
                        })

        if not keyword_titles:
            st.warning(f"선택된 조건 '{', '.join(type_category)}'와 키워드 '{', '.join(selected_keywords)}'에 해당하는 타이틀이 없습니다.")
        else:
            sorted_titles = sorted(keyword_titles, key=lambda x: x["keyword_score"], reverse=True)
            df = pd.DataFrame(sorted_titles)

            st.subheader(f"'{', '.join(type_category)}' 유형 및 '{', '.join(selected_keywords)}' 키워드를 포함한 타이틀 목록")
            selected_title_df = st.dataframe(
                df[["title", "app_id", "link", "rating", "tags", "positive_keywords", "negative_keywords", "keyword_score"]],
                column_config={
                    "title": "타이틀",
                    "app_id": "App ID",
                    "link": st.column_config.LinkColumn("링크"),
                    "rating": "점수",
                    "tags": "태그",
                    "positive_keywords": "긍정 키워드",
                    "negative_keywords": "부정 키워드",
                    "keyword_score": "키워드 점수"
                },
                height=300,
                use_container_width=True,
                selection_mode="single-row",
                on_select="rerun"
            )

            if st.button("상세정보"):
                selected_rows = selected_title_df.selection["rows"]
                if selected_rows:
                    selected_title = df.iloc[selected_rows[0]]
                    st.session_state["selected_title"] = selected_title.to_dict()
                    st.session_state["selected_menu"] = "타이틀 상세"
                    st.rerun()
                else:
                    st.warning("타이틀을 선택해 주세요.")

    elif selected_menu == "타이틀 상세":
        title_info = st.session_state.get("selected_title", filtered_titles[0] if filtered_titles else None)
        if title_info:
            st.subheader("타이틀 상세")
            st.markdown(f"#### {title_info['title']} 상세 (App ID: {title_info['app_id']})")
            st.write(f"- **링크**: [{title_info['link']}]({title_info['link']})")
            st.write(f"- **점수**: {title_info['rating']}")
            st.write(f"- **태그**: {', '.join(title_info['tags'])}")
            st.write(f"- **주요 키워드 (긍정)**: {', '.join(title_info['positive_keywords'])}")
            st.write(f"- **주요 키워드 (부정)**: {', '.join(title_info['negative_keywords'])}")
            st.write("실제 리뷰 텍스트 원문:")
            for review in title_info["reviews"]:
                st.write(f"- {review}")

            st.subheader("리뷰 키워드 워드 클라우드")
            col7, col8 = st.columns(2)
            with col7:
                st.write("긍정 키워드 워드 클라우드")
                if title_info["positive_keywords"]:
                    positive_cloud = WordCloud(width=400, height=200, background_color="white").generate(" ".join(title_info["positive_keywords"]))
                    plt.figure(figsize=(5, 3))
                    plt.imshow(positive_cloud, interpolation="bilinear")
                    plt.axis("off")
                    st.pyplot(plt)
                else:
                    st.write("긍정 키워드가 없습니다.")
            with col8:
                st.write("부정 키워드 워드 클라우드")
                if title_info["negative_keywords"]:
                    negative_cloud = WordCloud(width=400, height=200, background_color="white").generate(" ".join(title_info["negative_keywords"]))
                    plt.figure(figsize=(5, 3))
                    plt.imshow(negative_cloud, interpolation="bilinear")
                    plt.axis("off")
                    st.pyplot(plt)
                else:
                    st.write("부정 키워드가 없습니다.")
        else:
            st.write("타이틀을 선택해 주세요.")

    elif selected_menu == "용어 정리 (팝업)":
        with st.expander("용어 정리 (클릭하여 열기)", expanded=True):
            st.subheader("용어 정리")
            selected_term = st.selectbox("용어를 선택하세요", list(glossary.keys()))
            st.markdown(f"**{selected_term}**: {glossary[selected_term]}")