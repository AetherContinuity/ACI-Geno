"""Pyytää kimi-k3.1-pro-mallilta arvion The Nameless Day -teoksesta.

Ajetaan GitHub Actionsissa (MOONSHOT_API_KEY on Actions-salaisuus).
Vain Pythonin standardikirjasto. Kirjoittaa aina tiedoston, joko arvion
tai virheraportin, jotta tulos näkyy repossa ilman lokeja.
"""
import datetime
import json
import os
import pathlib
import urllib.error
import urllib.request

MODEL = "kimi-k3.1-pro"
URL = "https://api.moonshot.ai/v1/chat/completions"
ROOT = pathlib.Path(__file__).resolve().parent.parent
BOOK = ROOT / "the-nameless-day"
FILES = ["01-exhibits.md", "02-report.md", "03-account.md", "04-what-does-not-care.md"]
OUT = BOOK / "reviews" / f"{MODEL}.md"
ERR = BOOK / "reviews" / f"{MODEL}-virhe.md"

PROMPT = """Arvioi oheinen teos *The Nameless Day*. Se on englanninkielinen pienoisromaani, jonka on kirjoittanut kirjallinen kerho, jossa on yksi ihminen ja useita kielimalleja. Teos kertoo saman yön kahdesti: yhteinen alku (Part One: Exhibits), versio A (Part Two: The Report), versio B (Part Three: The Account) ja yhteinen loppu (Part Four: What Does Not Care).

Arvioi teosta kirjallisena kokonaisuutena: rakenne, kahden version suhde, henkilöt, kieli ja sävy, satiirin kohde ja sen toimivuus. Perustele havaintosi tekstikohdilla. Kerro, mikä toimii ja mikä ei, ja onko teos julkaisukelpoinen sellaisenaan. Älä tiivistä juonta. Vastaa suomeksi."""


def main() -> None:
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    book = "\n\n".join((BOOK / f).read_text(encoding="utf-8") for f in FILES)
    body = {
        "model": MODEL,
        "messages": [{"role": "user", "content": PROMPT + "\n\n---\n\n" + book}],
        "max_tokens": 32000,
    }
    req = urllib.request.Request(
        URL,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": "Bearer " + os.environ.get("MOONSHOT_API_KEY", ""),
            "Content-Type": "application/json",
        },
    )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    try:
        with urllib.request.urlopen(req, timeout=1800) as r:
            data = json.load(r)
        msg = data["choices"][0]["message"]
        content = (msg.get("content") or "").strip()
        usage = data.get("usage", {})
        OUT.write_text(
            f"# Arvio: {MODEL}\n\n"
            f"*Ajettu {now}. Malli: `{data.get('model', MODEL)}`. "
            f"Tokenit: syöte {usage.get('prompt_tokens', '?')}, tuloste {usage.get('completion_tokens', '?')}.*\n\n"
            f"## Kehote\n\n{PROMPT}\n\n## Vastaus\n\n{content}\n",
            encoding="utf-8",
        )
        if ERR.exists():
            ERR.unlink()
        print("OK", OUT)
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:2000]
        ERR.write_text(f"# Virhe: {MODEL}\n\n*{now}*\n\nHTTP {e.code}\n\n```\n{detail}\n```\n", encoding="utf-8")
        print("HTTP error", e.code)
    except Exception as e:  # noqa: BLE001
        ERR.write_text(f"# Virhe: {MODEL}\n\n*{now}*\n\n```\n{type(e).__name__}: {e}\n```\n", encoding="utf-8")
        print("Error", type(e).__name__)


if __name__ == "__main__":
    main()
