import re, colorsys, os, time

EXCLUDE = ["hero", "lux-slide", "lux-info", "lux-name", "lux-kicker", "lux-rule", "lux-price",
           "lux-specs", "lux-actions", "lux-btn", "lux-arrow", "lux-count", "lux-bar", "lux-img",
           "lux-stage", "card-photo", "photo-arrow", "photo-dot", "photo-count", "lightbox"]
BTNISH = ["btn", "button", "submit", "gold", "cta", "badge", "pill", "tag", "chip", "-open", "tf-star"]
BG = {"background", "background-color", "background-image"}
TEXT = {"color", "fill", "stroke", "caret-color"}
PUBLIC_TEMPLATES = ["index.html", "cars.html", "car_detail.html", "sell_car.html", "swap_car.html", "_nav.html", "base.html"]

COLOR = re.compile(
    r'rgba?\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*(?:,\s*[\d.]+\s*)?\)'
    r'|#(?:[0-9a-fA-F]{6}|[0-9a-fA-F]{3})(?![0-9a-fA-F\w])'
    r'|(?<![\w#-])(?:white|black)(?![\w-])', re.I)


def excluded(s):
    for x in EXCLUDE:
        if x in s:
            if x == "hero" and "cars-hero" in s and s.replace("cars-hero", "").find("hero") == -1:
                continue
            return True
    return False


def parse(tok):
    t = tok.strip().lower()
    if t.startswith("rgb"):
        nums = re.findall(r"[\d.]+", t)
        r, g, b = [int(float(x)) for x in nums[:3]]
        a = float(nums[3]) if len(nums) > 3 else None
    elif t.startswith("#"):
        hx = t[1:]
        if len(hx) == 3:
            hx = "".join(c * 2 for c in hx)
        r, g, b = int(hx[0:2], 16), int(hx[2:4], 16), int(hx[4:6], 16)
        a = None
    elif t == "white":
        r, g, b, a = 255, 255, 255, None
    else:
        r, g, b, a = 0, 0, 0, None
    return r, g, b, a


def is_accent(r, g, b):
    h, l, s = colorsys.rgb_to_hls(r / 255.0, g / 255.0, b / 255.0)
    return s > 0.22 and 0.14 < l < 0.86


def fmt(r, g, b, a):
    if a is None:
        return "#%02x%02x%02x" % (r, g, b)
    return "rgba(%d,%d,%d,%s)" % (r, g, b, ("%.3f" % a).rstrip("0").rstrip("."))


def convert_color(tok, mode, keep_dark_text):
    r, g, b, a = parse(tok)
    if a is not None and a == 0:
        return tok
    if mode == "shadow":
        return fmt(r, g, b, (a if a is not None else 1.0) * 0.4)
    h, l, s = colorsys.rgb_to_hls(r / 255.0, g / 255.0, b / 255.0)
    if is_accent(r, g, b):
        if mode == "text" and l > 0.45:
            l, s = 0.36, min(s, 0.7)
        else:
            return tok
    else:
        if mode == "text":
            if l < 0.3 and keep_dark_text:
                return tok
            nl = 1 - l
            if nl > 0.3:
                nl = 0.3 + (nl - 0.3) * 0.5
            l = nl
        else:
            l = 0.99 - 0.98 * l
    r2, g2, b2 = colorsys.hls_to_rgb(h, l, s)
    return fmt(int(round(r2 * 255)), int(round(g2 * 255)), int(round(b2 * 255)), a)


def mode_of(prop):
    p = prop.lower()
    if p.startswith("--"):
        return "shadow" if "shadow" in p else "bg"
    if p in ("box-shadow", "text-shadow"):
        return "shadow"
    if p in TEXT:
        return "text"
    if p in BG or p.startswith("border") or p.startswith("outline"):
        return "bg"
    return None


def split_sel(sel):
    parts, depth, cur = [], 0, ""
    for ch in sel:
        if ch in "([":
            depth += 1
        elif ch in ")]":
            depth -= 1
        if ch == "," and depth == 0:
            parts.append(cur.strip())
            cur = ""
        else:
            cur += ch
    if cur.strip():
        parts.append(cur.strip())
    return parts


def prefix(s):
    L = 'html[data-theme="light"]'
    if s.startswith(":root"):
        return L + s[5:]
    if re.match(r"^html(?![\w-])", s):
        return L + s[4:]
    return L + " " + s


def convert_rule(sel, body):
    parts = [s for s in split_sel(sel) if not excluded(s)]
    if not parts:
        return ""
    items = []
    for x in body.split(";"):
        if ":" in x:
            prop, _, val = x.partition(":")
            items.append((prop.strip(), val.strip()))
    accent_bg = False
    for prop, val in items:
        if mode_of(prop) == "bg" and not prop.startswith("--"):
            for m in COLOR.finditer(val):
                r, g, b, a = parse(m.group(0))
                if is_accent(r, g, b) and (a is None or a >= 0.6):
                    accent_bg = True
    btnish = any(t in s for s in parts for t in BTNISH)
    keep_dark = accent_bg or btnish
    out = []
    for prop, val in items:
        imp = "!important" in val
        core = val.replace("!important", "").strip()
        if prop.lower() == "color-scheme" and "dark" in core:
            new = core.replace("dark", "light")
        else:
            mode = mode_of(prop)
            if not mode:
                continue
            new = COLOR.sub(lambda m: convert_color(m.group(0), mode, keep_dark), core)
        if new != core:
            out.append("%s:%s%s" % (prop, new, " !important" if imp else ""))
    if not out:
        return ""
    return ",".join(prefix(s) for s in parts) + "{" + ";".join(out) + "}"


def process(css):
    out, i, n = [], 0, len(css)
    while i < n:
        j = css.find("{", i)
        if j == -1:
            break
        prelude = css[i:j].strip()
        depth, k = 1, j + 1
        while k < n and depth:
            if css[k] == "{":
                depth += 1
            elif css[k] == "}":
                depth -= 1
            k += 1
        body = css[j + 1:k - 1]
        i = k
        if prelude.startswith("@media") or prelude.startswith("@supports"):
            inner = process(body)
            if inner.strip():
                out.append(prelude + "{" + inner + "}")
        elif prelude.startswith("@"):
            continue
        else:
            r = convert_rule(prelude, body)
            if r:
                out.append(r)
    return "\n".join(out)


def clean(css):
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    css = re.sub(r"@(import|charset)[^;]*;", "", css)
    css = re.sub(r"\{\{.*?\}\}|\{%.*?%\}", "x", css, flags=re.S)
    return css


def inline_rules():
    seen, out = set(), []
    for name in PUBLIC_TEMPLATES:
        p = os.path.join("templates", name)
        if not os.path.exists(p):
            continue
        t = open(p, encoding="utf-8").read()
        for style in re.findall(r'style="([^"]*)"', t):
            if "{{" in style or "{%" in style:
                continue
            for decl in style.split(";"):
                if ":" not in decl:
                    continue
                prop, _, val = decl.partition(":")
                prop, val = prop.strip().lower(), val.strip()
                if "'" in val or "\\" in val or not val:
                    continue
                if prop == "color":
                    mode = "text"
                elif prop in ("background", "background-color") or prop.startswith("border"):
                    mode = "bg"
                else:
                    continue
                new = COLOR.sub(lambda m: convert_color(m.group(0), mode, True), val)
                if new == val or (prop, val) in seen:
                    continue
                seen.add((prop, val))
                for sp in ("", " "):
                    out.append('html[data-theme="light"] [style*="%s:%s%s"]{%s:%s !important}' % (prop, sp, val, prop, new))
    return "\n".join(out)


MANUAL = """
html[data-theme="light"]{color-scheme:light}
html[data-theme="light"] body{background:#f6f4f0;color:#17171b}
html[data-theme="light"] .card,html[data-theme="light"] .testi-card,html[data-theme="light"] .testi-form,
html[data-theme="light"] .lux-thumb,html[data-theme="light"] .price-card,html[data-theme="light"] .auction-panel,
html[data-theme="light"] body.page-cars .card,
html[data-theme="light"] .cp-card,html[data-theme="light"] .cp-form-wrap,html[data-theme="light"] .sv-card,html[data-theme="light"] .sv-step,html[data-theme="light"] .ab-story,html[data-theme="light"] .tp-stats,html[data-theme="light"] .tp-empty{background:#fff}
html[data-theme="light"] :where(h1,h2,h3,h4,h5,h6):not(:where([class*="hero"]:not(.cars-hero) *,.lux-stage *,.lux-info *)){color:#17171b}
html[data-theme="light"] .brand,html[data-theme="light"] .topbar .brand,html[data-theme="light"] .site-nav .brand{color:#17171b}
html[data-theme="light"] .brand em{color:#9a7a3a}
html[data-theme="light"] .lux-more .lux-btn.ghost{background:transparent;color:#17171b;border-color:#17171b;backdrop-filter:none}
html[data-theme="light"] .lux-more .lux-btn.ghost:hover{background:#c9a96e;color:#0a0a0b;border-color:#c9a96e}
html[data-theme="light"] .lux-thumb.active{box-shadow:0 0 0 1px #c9a96e,0 10px 24px rgba(201,169,110,.25)}
html[data-theme="light"] .theme-toggle{color:#8a6a2e}
html[data-theme="light"] .theme-toggle:hover{background:#c9a96e;color:#0a0a0b}
"""


def main():
    css = clean(open("static/css/style.css", encoding="utf-8").read())
    for name in PUBLIC_TEMPLATES:
        p = os.path.join("templates", name)
        if os.path.exists(p):
            t = open(p, encoding="utf-8").read()
            for blk in re.findall(r"<style[^>]*>(.*?)</style>", t, flags=re.S):
                css += "\n" + clean(blk)
    gen = process(css)
    inl = inline_rules()
    head = "/* Light theme - generated by build_light_theme.py from style.css. Re-run it after CSS changes. */\n"
    open("static/css/light-theme.css", "w", encoding="utf-8").write(head + gen + "\n" + inl + "\n" + MANUAL)
    ts = str(int(time.time()))
    p = "templates/_nav.html"
    if os.path.exists(p):
        t = open(p, encoding="utf-8").read()
        t2 = re.sub(r"(light-theme\.css'\) \}\}\?v=)\d+", lambda m: m.group(1) + ts, t)
        if t2 != t:
            open(p, "w", encoding="utf-8").write(t2)
    print("light theme: %d rules + %d inline-style rules -> static/css/light-theme.css" % (gen.count("}\n") + 1, inl.count("\n") + (1 if inl else 0)))
    # diagnostics
    nvars = len(re.findall(r"--[\w-]+\s*:\s*(?:#|rgb)", css))
    print("css variables with colours found:", nvars)
    shown = 0
    for m in re.finditer(r"([^{}]*\.brand[^{}]*)\{([^{}]*)\}", css):
        if "color" in m.group(2) and shown < 4:
            print("  brand rule:", m.group(1).strip()[:60], "{", m.group(2).strip()[:110], "}")
            shown += 1


if __name__ == "__main__":
    main()
