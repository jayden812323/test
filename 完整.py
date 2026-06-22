import pandas as pd
import re

df = pd.read_parquet(r"C:/Users/88691/Downloads/練習/脆熱議all.parquet.gzip")

def parse_part(part):
    """判斷是普通詞還是近似搜尋，回傳 re pattern"""
    if "/" in part:
        segments = part.split("/")
        if len(segments) == 3:
            word_a = segments[0].strip()
            n_raw = segments[1].strip()
            word_b = segments[2].strip()
            n = int(n_raw.replace("n", "").replace("N", ""))
            return (
                f"(?:{word_a}).{{0,{n}}}(?:{word_b})"
                f"|(?:{word_b}).{{0,{n}}}(?:{word_a})"
            )
        else:
            return re.escape(part)
    else:
        escaped = re.escape(part)
        if re.fullmatch(r"[A-Za-z0-9]+", part):
            return rf"\b{escaped}\b"
        else:
            return escaped


def parse_bracket_or(part):
    """處理括號：去掉括號，用 ; 切開做分組OR，回傳 re pattern"""
    inner = part[1:-1]
    sub_segments = [p.strip() for p in inner.split(";")]
    return "|".join(parse_part(s) for s in sub_segments)


def parse_and_term(term):
    """解析「&」層級（AND），每一段可能是括號或一般詞"""
    and_parts = [p.strip() for p in term.split("&") if p.strip()]
    mask = pd.Series([True] * len(df), index=df.index)
    for part in and_parts:
        if part.startswith("(") and part.endswith(")"):
            pattern = parse_bracket_or(part)
        else:
            pattern = parse_part(part)
        mask = mask & df["title"].str.contains(pattern, na=False, regex=True)
    return mask


def parse_not_segment(segment):
    """解析「-」層級（NOT），第一段包含、其餘排除（可多組）"""
    parts = [p.strip() for p in segment.split("-") if p.strip()]
    include_term = parts[0]
    exclude_terms = parts[1:]

    mask = parse_and_term(include_term)

    for ex in exclude_terms:
        mask_exclude = parse_and_term(ex)
        mask = mask & ~mask_exclude

    return mask


def parse_full_expression(user_input):
    """最外層：用 + 切分（OR），每段丟進 parse_not_segment"""
    or_parts = [p.strip() for p in user_input.split("+") if p.strip()]
    mask = pd.Series([False] * len(df), index=df.index)
    for part in or_parts:
        mask_part = parse_not_segment(part)
        mask = mask | mask_part
    return mask


# ── 主迴圈 ──────────────────────────────────────────────────
while True:
    user_input = input(">>> ").strip()
    if not user_input:
        print("⚠️  輸入不可為空，請重新輸入。")
        continue

    mask = parse_full_expression(user_input)
    result = df[mask]

    print(f"\n篩選結果：{len(result)} 筆")

    pd.set_option("display.max_colwidth", None)
    print(result[["title", "comment_count"]].head(10).to_string(index=False))
    break