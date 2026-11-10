# change.py
# 易經六十四卦繪圖程式庫（輕量版，不依賴 matplotlib）
# 字串規則（由上到下）："111111"=乾，"000000"=坤
# 1=陽爻，0=陰爻
# 卦名預設繁體中文
#
# 特殊標記語法（可在文字中嵌入）：
#   [[111111]]          → 畫出該 binary 的卦象
#   [[乾]] / [[坤]]      → 以卦名畫出
#   [[1]] ~ [[64]]       → 以文王序號畫出
#   [[u:111111]]         → 只顯示 Unicode 字元 ䷀
#   [[t:111111]]         → 只顯示文字版（ASCII）
#   [[s:111111]]         → SVG 版

"""
易經卦象輕量繪圖模組
====================

繪圖：
  draw(binary, target_div=..., method="html"|"svg"|"unicode")
  draw_multiple([...], target_div=...)
  print_hexagram(binary)

標記渲染（重點新功能）：
  render_markup(text, target_div=None)
      把文字中的 [[...]] 標記轉成卦象 HTML

查詢：
  get_name / from_king_wen / unicode_char / list_all
"""

from __future__ import annotations
from typing import Optional, Tuple, Dict, List
import re

# ------------------------------------------------------------
# 文王卦序（binary 由上到下，卦名繁體）
# ------------------------------------------------------------
KING_WEN: Dict[int, Tuple[str, str, str, str]] = {
    1:  ("111111", "乾", "乾為天", "Qian"),
    2:  ("000000", "坤", "坤為地", "Kun"),
    3:  ("010001", "屯", "水雷屯", "Zhun"),
    4:  ("100010", "蒙", "山水蒙", "Meng"),
    5:  ("010111", "需", "水天需", "Xu"),
    6:  ("111010", "訟", "天水訟", "Song"),
    7:  ("000010", "師", "地水師", "Shi"),
    8:  ("010000", "比", "水地比", "Bi"),
    9:  ("110111", "小畜", "風天小畜", "Xiao Chu"),
    10: ("111011", "履", "天澤履", "Lu"),
    11: ("000111", "泰", "地天泰", "Tai"),
    12: ("111000", "否", "天地否", "Pi"),
    13: ("111101", "同人", "天火同人", "Tong Ren"),
    14: ("101111", "大有", "火天大有", "Da You"),
    15: ("000100", "謙", "地山謙", "Qian"),
    16: ("001000", "豫", "雷地豫", "Yu"),
    17: ("011001", "隨", "澤雷隨", "Sui"),
    18: ("100110", "蠱", "山風蠱", "Gu"),
    19: ("000011", "臨", "地澤臨", "Lin"),
    20: ("110000", "觀", "風地觀", "Guan"),
    21: ("101001", "噬嗑", "火雷噬嗑", "Shi Ke"),
    22: ("100101", "賁", "山火賁", "Bi"),
    23: ("100000", "剝", "山地剝", "Bo"),
    24: ("000001", "復", "地雷復", "Fu"),
    25: ("111001", "無妄", "天雷無妄", "Wu Wang"),
    26: ("100111", "大畜", "山天大畜", "Da Chu"),
    27: ("100001", "頤", "山雷頤", "Yi"),
    28: ("011110", "大過", "澤風大過", "Da Guo"),
    29: ("010010", "坎", "坎為水", "Kan"),
    30: ("101101", "離", "離為火", "Li"),
    31: ("011100", "咸", "澤山咸", "Xian"),
    32: ("001110", "恆", "雷風恆", "Heng"),
    33: ("111100", "遯", "天山遯", "Dun"),
    34: ("001111", "大壯", "雷天大壯", "Da Zhuang"),
    35: ("101000", "晉", "火地晉", "Jin"),
    36: ("000101", "明夷", "地火明夷", "Ming Yi"),
    37: ("110101", "家人", "風火家人", "Jia Ren"),
    38: ("101011", "睽", "火澤睽", "Kui"),
    39: ("010100", "蹇", "水山蹇", "Jian"),
    40: ("001010", "解", "雷水解", "Xie"),
    41: ("100011", "損", "山澤損", "Sun"),
    42: ("110001", "益", "風雷益", "Yi"),
    43: ("011111", "夬", "澤天夬", "Guai"),
    44: ("111110", "姤", "天風姤", "Gou"),
    45: ("011000", "萃", "澤地萃", "Cui"),
    46: ("000110", "升", "地風升", "Sheng"),
    47: ("011010", "困", "澤水困", "Kun"),
    48: ("010110", "井", "水風井", "Jing"),
    49: ("011101", "革", "澤火革", "Ge"),
    50: ("101110", "鼎", "火風鼎", "Ding"),
    51: ("001001", "震", "震為雷", "Zhen"),
    52: ("100100", "艮", "艮為山", "Gen"),
    53: ("110100", "漸", "風山漸", "Jian"),
    54: ("001011", "歸妹", "雷澤歸妹", "Gui Mei"),
    55: ("001101", "豐", "雷火豐", "Feng"),
    56: ("101100", "旅", "火山旅", "Lu"),
    57: ("110110", "巽", "巽為風", "Xun"),
    58: ("011011", "兌", "兌為澤", "Dui"),
    59: ("110010", "渙", "風水渙", "Huan"),
    60: ("010011", "節", "水澤節", "Jie"),
    61: ("110011", "中孚", "風澤中孚", "Zhong Fu"),
    62: ("001100", "小過", "雷山小過", "Xiao Guo"),
    63: ("010101", "既濟", "水火既濟", "Ji Ji"),
    64: ("101010", "未濟", "火水未濟", "Wei Ji"),
}

_BINARY_TO_INFO = {v[0]: (k, v[1], v[2], v[3]) for k, v in KING_WEN.items()}
_NAME_TO_BINARY: Dict[str, str] = {}
for _b, _zh, _alias, _en in KING_WEN.values():
    _NAME_TO_BINARY[_zh] = _b
    _NAME_TO_BINARY[_alias] = _b
    # 也支援去掉「為天」等的簡稱已在 _zh

_UNICODE_HEX = {i: chr(0x4DC0 + i - 1) for i in range(1, 65)}

TRIGRAMS = {
    "111": ("乾", "Qian"), "110": ("兌", "Dui"), "101": ("離", "Li"),
    "100": ("震", "Zhen"), "011": ("巽", "Xun"), "010": ("坎", "Kan"),
    "001": ("艮", "Gen"), "000": ("坤", "Kun"),
}


def _validate(binary: str) -> str:
    s = str(binary).strip().replace(" ", "")
    if len(s) != 6 or any(c not in "01" for c in s):
        raise ValueError(f"需為 6 位 0/1 字串（由上到下），收到：{binary!r}")
    return s


def get_name(binary: str, lang: str = "zh") -> str:
    s = _validate(binary)
    if s in _BINARY_TO_INFO:
        n, zh, alias, en = _BINARY_TO_INFO[s]
        return f"{n}. {en}" if lang == "en" else f"{n}. {zh}（{alias}）"
    up = TRIGRAMS.get(s[:3], ("？", "?"))
    lo = TRIGRAMS.get(s[3:], ("？", "?"))
    return f"{up[1]}-{lo[1]}" if lang == "en" else f"{up[0]}{lo[0]}"


def from_king_wen(n: int) -> str:
    if n not in KING_WEN:
        raise ValueError("文王卦序須為 1 到 64 的整數")
    return KING_WEN[n][0]


def from_name(name: str) -> str:
    """以繁體卦名或別名取得 binary。例如 from_name('乾') / from_name('乾為天')"""
    name = name.strip()
    if name in _NAME_TO_BINARY:
        return _NAME_TO_BINARY[name]
    # 容許「第N卦」或純數字
    if name.isdigit():
        return from_king_wen(int(name))
    raise ValueError(f"找不到卦名：{name!r}")


def unicode_char(binary: str) -> str:
    s = _validate(binary)
    if s in _BINARY_TO_INFO:
        return _UNICODE_HEX[_BINARY_TO_INFO[s][0]]
    return "？"


def list_all(lang: str = "zh") -> None:
    print("序號 | binary(上→下) | 卦名 | Unicode")
    print("-" * 46)
    for n in range(1, 65):
        b, zh, alias, en = KING_WEN[n]
        name = en if lang == "en" else f"{zh}（{alias}）"
        print(f"{n:2d} | {b} | {name} | {_UNICODE_HEX[n]}")


def print_hexagram(binary: str, show_name: bool = True, lang: str = "zh") -> None:
    s = _validate(binary)
    if show_name:
        print(get_name(s, lang=lang))
        print()
    labels = ["6", "5", "4", "3", "2", "1"] if lang == "en" else ["上", "五", "四", "三", "二", "初"]
    for i, bit in enumerate(s):
        line = "-------" if bit == "1" else "--  --"
        print(f"  {line}   {labels[i]}")


# ------------------------------------------------------------
# HTML / SVG
# ------------------------------------------------------------
def _html_lines(binary: str, title: str, width: int = 160) -> str:
    s = _validate(binary)
    rows = []
    for bit in s:
        if bit == "1":
            rows.append(
                '<div style="height:12px;margin:7px 0;background:#222;border-radius:2px;"></div>'
            )
        else:
            rows.append(
                '<div style="height:12px;margin:7px 0;display:flex;justify-content:space-between;">'
                '<div style="width:42%;background:#222;border-radius:2px;"></div>'
                '<div style="width:42%;background:#222;border-radius:2px;"></div></div>'
            )
    body = "\n".join(rows)
    return (
        f'<div style="display:inline-block;vertical-align:top;width:{width}px;'
        f'margin:8px;padding:12px 16px;background:#faf8f0;border:1px solid #ddd;'
        f'border-radius:8px;font-family:\'Noto Sans TC\',\'Microsoft JhengHei\',sans-serif;'
        f'text-align:center;">'
        f'<div style="font-weight:bold;margin-bottom:10px;color:#222;">{title}</div>'
        f'{body}</div>'
    )


def _svg_lines(binary: str, title: str, width: int = 180, height: int = 270) -> str:
    s = _validate(binary)
    line_h, gap, top = 14, 18, 42
    left, right, gap_x = 20, width - 20, 12
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'style="background:#faf8f0;border-radius:8px;display:inline-block;margin:8px;vertical-align:top;">',
        f'<text x="{width//2}" y="26" text-anchor="middle" '
        f'font-family="Noto Sans TC, Microsoft JhengHei, sans-serif" '
        f'font-size="14" font-weight="bold" fill="#222">{title}</text>',
    ]
    for i, bit in enumerate(s):
        y = top + i * (line_h + gap)
        if bit == "1":
            parts.append(
                f'<rect x="{left}" y="{y}" width="{right-left}" height="{line_h}" rx="2" fill="#222"/>'
            )
        else:
            w = (right - left - gap_x) // 2
            parts.append(f'<rect x="{left}" y="{y}" width="{w}" height="{line_h}" rx="2" fill="#222"/>')
            parts.append(
                f'<rect x="{left+w+gap_x}" y="{y}" width="{w}" height="{line_h}" rx="2" fill="#222"/>'
            )
    parts.append("</svg>")
    return "\n".join(parts)


def _text_block(binary: str, title: str) -> str:
    """文字版包成 <pre>，方便嵌在 HTML 中。"""
    s = _validate(binary)
    lines = [title, ""]
    labels = ["上", "五", "四", "三", "二", "初"]
    for i, bit in enumerate(s):
        line = "-------" if bit == "1" else "--  --"
        lines.append(f"  {line}   {labels[i]}")
    body = "\n".join(lines)
    return (
        f'<pre style="display:inline-block;vertical-align:top;margin:8px;padding:12px;'
        f'background:#faf8f0;border:1px solid #ddd;border-radius:8px;'
        f'font-family:monospace;font-size:14px;line-height:1.4;">{body}</pre>'
    )


def _inject(html: str, target_div: str, clear: bool = True) -> None:
    from js import document  # type: ignore
    el = document.getElementById(target_div)
    if el is None:
        raise ValueError(f"找不到 id 為「{target_div}」的元素")
    if clear:
        el.innerHTML = ""
    el.insertAdjacentHTML("beforeend", html)


# ------------------------------------------------------------
# 公開繪圖 API
# ------------------------------------------------------------
def draw(
    binary: str,
    target_div: Optional[str] = None,
    title: Optional[str] = None,
    method: str = "html",
    lang: str = "zh",
    clear: bool = True,
    width: int = 160,
) -> str:
    s = _validate(binary)
    if title is None:
        title = get_name(s, lang=lang)

    if method == "unicode":
        ch = unicode_char(s)
        html = (
            f'<div style="display:inline-block;vertical-align:top;text-align:center;'
            f'font-size:64px;line-height:1.2;padding:12px;margin:8px;font-family:serif;">'
            f'{ch}<div style="font-size:13px;margin-top:6px;'
            f'font-family:\'Noto Sans TC\',\'Microsoft JhengHei\',sans-serif;">{title}</div></div>'
        )
    elif method == "svg":
        html = _svg_lines(s, title, width=max(width, 160))
    elif method == "text":
        html = _text_block(s, title)
    else:
        html = _html_lines(s, title, width=width)

    if target_div is not None:
        try:
            _inject(html, target_div, clear=clear)
        except Exception as e:
            print(f"[change] 注入失敗：{e}")
            print_hexagram(s, lang=lang)
    return html


def draw_multiple(
    binaries: List[str],
    target_div: Optional[str] = None,
    method: str = "html",
    lang: str = "zh",
    clear: bool = True,
    width: int = 130,
) -> str:
    items = [draw(b, target_div=None, method=method, lang=lang, width=width) for b in binaries]
    html = (
        '<div style="display:flex;flex-wrap:wrap;gap:8px;justify-content:center;'
        'align-items:flex-start;padding:8px;">'
        + "".join(items) + "</div>"
    )
    if target_div is not None:
        try:
            _inject(html, target_div, clear=clear)
        except Exception as e:
            print(f"[change] 注入失敗：{e}")
            for b in binaries:
                print_hexagram(b, lang=lang)
                print()
    return html


def qian(target_div: Optional[str] = None, **kw):
    return draw("111111", target_div=target_div, **kw)


def kun(target_div: Optional[str] = None, **kw):
    return draw("000000", target_div=target_div, **kw)


# ------------------------------------------------------------
# 特殊標記解析與渲染（核心新功能）
# ------------------------------------------------------------
# 支援的標記格式：
#   [[111111]]           binary
#   [[乾]] [[坤]]         卦名
#   [[1]] ... [[64]]     文王序號
#   [[u:111111]]         強制 unicode
#   [[s:乾]]             強制 svg
#   [[t:坤]]             強制 text
#   [[h:010001]]         強制 html（預設）
#
# 標記可出現在任意文字中，render_markup 會保留其餘文字並替換標記。

_MARK_RE = re.compile(
    r"\[\[\s*(?:([usth])\s*:\s*)?([^\[\]]+?)\s*\]\]",
    re.UNICODE,
)


def _resolve_token(token: str) -> str:
    """把標記內容轉成 binary 字串。"""
    token = token.strip()
    # 6 位 0/1
    if len(token) == 6 and all(c in "01" for c in token):
        return token
    # 純數字 1~64
    if token.isdigit():
        n = int(token)
        if 1 <= n <= 64:
            return from_king_wen(n)
    # 卦名 / 別名
    if token in _NAME_TO_BINARY:
        return _NAME_TO_BINARY[token]
    raise ValueError(f"無法解析標記內容：{token!r}")


def render_markup(
    text: str,
    target_div: Optional[str] = None,
    default_method: str = "html",
    lang: str = "zh",
    clear: bool = True,
    width: int = 140,
) -> str:
    """
    把文字中的 [[...]] 標記轉成卦象，其餘文字原樣保留。

    參數
    ----
    text : 含標記的字串
    target_div : 若提供，把最終 HTML 注入該 div
    default_method : 未指定前綴時的預設繪法（html/svg/unicode/text）
    lang : 卦名語言
    clear : 注入前是否清空 div
    width : 單一卦象寬度

    回傳
    ----
    完整 HTML 字串（含一般文字與卦象）
    """
    method_map = {
        "u": "unicode",
        "s": "svg",
        "t": "text",
        "h": "html",
        None: default_method,
    }

    parts: List[str] = []
    last = 0
    for m in _MARK_RE.finditer(text):
        # 前面的普通文字（跳脫 HTML）
        plain = text[last:m.start()]
        if plain:
            # 簡單換行轉 <br>
            esc = (
                plain.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace("\n", "<br>\n")
            )
            parts.append(esc)

        prefix = m.group(1)  # u/s/t/h or None
        token = m.group(2)
        method = method_map.get(prefix, default_method)

        try:
            binary = _resolve_token(token)
            parts.append(
                draw(binary, target_div=None, method=method, lang=lang, width=width)
            )
        except Exception as e:
            # 解析失敗時保留原標記並加錯誤提示
            parts.append(
                f'<span style="color:#c00;font-family:monospace;">'
                f'[[{token}]] (錯誤：{e})</span>'
            )
        last = m.end()

    # 結尾普通文字
    tail = text[last:]
    if tail:
        esc = (
            tail.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace("\n", "<br>\n")
        )
        parts.append(esc)

    html = (
        '<div style="font-family:\'Noto Sans TC\',\'Microsoft JhengHei\',sans-serif;'
        'line-height:1.6;padding:8px;">'
        + "".join(parts)
        + "</div>"
    )

    if target_div is not None:
        try:
            _inject(html, target_div, clear=clear)
        except Exception as e:
            print(f"[change] 注入失敗：{e}")
            # 退回純文字輸出
            print(text)
    return html


def demo(target_div: Optional[str] = None):
    print("=== 文字版 ===")
    print_hexagram("111111")
    print()
    sample = """今日得卦：[[乾]]，對應 [[111111]]。
若用 Unicode：[[u:乾]]
若用文字版：[[t:坤]]
文王第 63 卦：[[63]]"""
    print("=== 標記渲染示範 ===")
    print(sample)
    print()
    render_markup(sample, target_div=target_div, default_method="html")


if __name__ == "__main__":
    demo()
